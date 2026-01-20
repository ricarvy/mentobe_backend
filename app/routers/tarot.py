from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from app.models import (
    InterpretRequest, SuggestRequest, SuggestResponse, 
    HistoryResponse, SuccessResponse, ErrorResponse,
    InterpretationRecord, UserResponse
)
from app.dependencies import get_current_user
from app.database import supabase
from app.config import settings
import asyncio
import json
import uuid
import logging
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tarot", tags=["tarot"])

async def save_interpretation(user_id: str, request: InterpretRequest, full_text: str):
    """
    保存解读结果到数据库，并更新用户今日配额
    """
    # Save to DB
    try:
        logger.info(f"Saving interpretation for user {user_id}")
        cards_json = json.dumps([c.dict() for c in request.cards])
        
        record = {
            "user_id": user_id,
            "question": request.question,
            "spread_type": request.spread.id,
            "cards": cards_json,
            "interpretation": full_text,
            "created_at": datetime.now().isoformat()
        }
        
        supabase.table("tarot_interpretations").insert(record).execute()
        
        # Update quota
        today = datetime.now().strftime("%Y-%m-%d")
        # Check if quota record exists
        q_res = supabase.table("daily_quotas").select("*").eq("user_id", user_id).eq("date", today).execute()
        if q_res.data:
            current_count = q_res.data[0]["count"]
            supabase.table("daily_quotas").update({"count": current_count + 1}).eq("id", q_res.data[0]["id"]).execute()
        else:
            supabase.table("daily_quotas").insert({"user_id": user_id, "date": today, "count": 1}).execute()
            
        logger.info(f"Interpretation saved and quota updated for user {user_id}")
            
    except Exception as e:
        logger.error(f"Failed to save interpretation: {e}")
        print(f"Failed to save interpretation: {e}")

async def fake_llm_stream(user_id: str, request: InterpretRequest):
    """
    模拟 LLM 流式输出，构建 Prompt 并生成解读
    """
    # Construct the prompt based on the request
    # This aligns with the "System Prompt" requirement implied in backend.md
    
    cards_info = []
    for i, card in enumerate(request.cards):
        position_name = f"位置 {i+1}"
        position_desc = ""
        if i < len(request.spread.positions):
            position_name = request.spread.positions[i].name
            position_desc = request.spread.positions[i].description
        
        card_status = "逆位" if card.isReversed else "正位"
        card_meaning = card.reversedMeaning if card.isReversed else card.meaning
        
        card_desc = f"{i+1}. {position_name} ({position_desc})\n   牌面: {card.name} ({card_status})\n   含义: {card_meaning}"
        cards_info.append(card_desc)
    
    cards_desc = "\n\n".join(cards_info)
    
    # Log detailed cards info
    logger.info(f"Cards drawn for user {user_id}:\n{cards_desc}")
    
    prompt = f"""
    {settings.TAROT_SYSTEM_PROMPT}
    
    用户问题: {request.question}
    牌阵: {request.spread.name} - {request.spread.description}
    
    抽出的牌:
    {cards_desc}
    """
    
    logger.info(f"Generated prompt for user {user_id}: {prompt[:100]}...") # Log first 100 chars

    # Simulate thinking and streaming (Mock for now as per current state, but structure is ready for real LLM)
    full_text = ""
    
    # Mock response to match backend.md example style more closely
    # 这里的 mock response 也可以稍微汉化一下，或者保留 structure
    response_text = f"""
    基于您的问题 "{request.question}" 和抽出的牌面...
    
    1. **{request.cards[0].name}**: 这张牌代表...
    
    总体来看，情况...
    """
    
    lines = response_text.split('\n')
    for line in lines:
        chunk = line + "\n"
        full_text += chunk
        yield chunk
        await asyncio.sleep(0.1) # Simulate delay
        
    # Save after streaming
    logger.info(f"Interpretation result for user {user_id}:\n{full_text}")
    await save_interpretation(user_id, request, full_text)

@router.post("/interpret")
async def interpret(request: InterpretRequest, current_user: UserResponse = Depends(get_current_user)):
    """
    塔罗牌解读接口
    1. 检查用户今日配额
    2. 如果有配额，调用 LLM (模拟) 生成流式响应
    """
    logger.info(f"Received interpret request from user {current_user.id}")
    
    # 1. Check Quota
    if not current_user.unlimitedQuota:
        today = datetime.now().strftime("%Y-%m-%d")
        q_res = supabase.table("daily_quotas").select("*").eq("user_id", current_user.id).eq("date", today).execute()
        used = 0
        if q_res.data:
            used = q_res.data[0]["count"]
        
        if used >= 3: # Limit 3
             logger.warning(f"User {current_user.id} exceeded daily quota")
             return ErrorResponse(success=False, error={"code": "QUOTA_EXCEEDED", "message": "今日额度已用完"})

    # 2. Stream Response
    logger.info(f"Starting stream for user {current_user.id}")
    return StreamingResponse(fake_llm_stream(current_user.id, request), media_type="text/event-stream")

@router.post("/suggest", response_model=SuccessResponse)
async def suggest(request: SuggestRequest):
    # TODO: Implement actual LLM call for suggestions
    # For now, we mock it but with a structure that matches the requirement
    
    # Construct prompt for LLM
    prompt = f"""
    You are a Tarot advisor.
    
    Based on the user's question: "{request.question}"
    And the tarot interpretation provided:
    {request.interpretation}
    
    Please suggest 3-4 specific follow-up areas for exploration or actions.
    Format the output clearly.
    """
    
    # Mock response
    suggestion = f"基于您的工作发展问题，我建议您可以继续探索以下方向：\n\n1. 职业技能提升\n2. 扩展人脉网络\n3. 寻找导师指导\n\n鼓励您持续探索！"
    return SuccessResponse(data=SuggestResponse(suggestion=suggestion))

@router.get("/history", response_model=SuccessResponse)
async def history(userId: str, current_user: UserResponse = Depends(get_current_user)):
    if userId != current_user.id and not current_user.isDemo:
        raise HTTPException(status_code=403, detail="Forbidden")
        
    try:
        response = supabase.table("tarot_interpretations")\
            .select("*")\
            .eq("user_id", userId)\
            .order("created_at", desc=True)\
            .limit(20)\
            .execute()
            
        records = []
        if response.data:
            for item in response.data:
                records.append(InterpretationRecord(
                    id=item["id"],
                    userId=item["user_id"],
                    question=item["question"],
                    spreadType=item["spread_type"],
                    cards=item["cards"],
                    interpretation=item["interpretation"],
                    createdAt=item["created_at"]
                ))
                
        return SuccessResponse(data=HistoryResponse(interpretations=records))
    except Exception as e:
        return ErrorResponse(success=False, error={"code": "DATABASE_ERROR", "message": str(e)})
