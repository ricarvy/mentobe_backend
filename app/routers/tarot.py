from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.concurrency import run_in_threadpool
from app.models import (
    InterpretRequest, SuggestRequest, SuggestResponse, 
    HistoryResponse, SuccessResponse, ErrorResponse,
    InterpretationRecord, UserResponse
)
from app.dependencies import get_current_user
# from app.database import supabase # Removed
from app.database import SessionLocal, get_db
from sqlalchemy.orm import Session
from app.db_models import TarotInterpretation
from app.config import settings
from app.services.llm import stream_tarot_interpretation
from app.services.quota import QuotaService
import asyncio
import json
import uuid
import logging
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tarot", tags=["tarot"])

def _save_interpretation_sync(user_id: str, request: InterpretRequest, full_text: str):
    """
    Sync function to save interpretation and reduce quota
    """
    db = SessionLocal()
    try:
        logger.info(f"Saving interpretation for user {user_id}")
        cards_json = json.dumps([c.dict() for c in request.cards])
        
        record = TarotInterpretation(
            user_id=user_id,
            question=request.question,
            spread_type=request.spread.id,
            cards=cards_json, # JSONB handles string? Or dict? SQLAlchemy JSONB expects dict/list usually.
            # If using psycopg2, passing list/dict is fine. json.dumps returns string.
            # If column is JSONB, pass the object directly.
            interpretation=full_text,
            created_at=datetime.now()
        )
        # JSONB column expects python object, not string.
        record.cards = [c.dict() for c in request.cards]
        
        db.add(record)
        db.commit() # Commit to get ID? Not needed for quota.
        
        # Update quota
        try:
            success = QuotaService.reduce_quota(user_id, db)
            if not success:
                logger.warning(f"Quota reduction returned False for user {user_id} after saving interpretation")
        except Exception as qe:
            logger.error(f"Failed to reduce quota for user {user_id}: {qe}")
            
        logger.info(f"Interpretation saved and quota updated for user {user_id}")
            
    except Exception as e:
        logger.error(f"Failed to save interpretation: {e}")
        print(f"Failed to save interpretation: {e}")
    finally:
        db.close()

async def save_interpretation(user_id: str, request: InterpretRequest, full_text: str):
    await run_in_threadpool(_save_interpretation_sync, user_id, request, full_text)

async def generate_interpretation_stream(user_id: str, request: InterpretRequest):
    """
    生成 Prompt 并调用真实 LLM 获取解读
    """
    # Construct the prompt based on the request
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
    
    lang_instruction = {
        "cn": "请使用中文进行解读。请确保各个段落之间保留1-2行的空行，以保持排版清晰。",
        "en": "Please provide the interpretation in English. Ensure there are 1-2 empty lines between paragraphs for clear formatting.",
        "jp": "日本語で解釈を提供してください。段落の間には1〜2行の空白行を入れて、読みやすくしてください。"
    }.get(request.lang, "请使用中文进行解读。请确保各个段落之间保留1-2行的空行，以保持排版清晰。")

    user_prompt = f"""
    用户问题: {request.question}
    牌阵: {request.spread.name} - {request.spread.description}
    语言要求: {lang_instruction}
    
    抽出的牌:
    {cards_desc}
    """
    
    messages = [
        {"role": "system", "content": settings.TAROT_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]
    
    logger.info(f"Calling LLM for user {user_id}")

    full_text = ""
    async for chunk in stream_tarot_interpretation(messages):
        full_text += chunk
        yield chunk
        
    # Save after streaming
    logger.info(f"Interpretation result for user {user_id} completed. Length: {len(full_text)}")
    await save_interpretation(user_id, request, full_text)

@router.post("/interpret")
async def interpret(request: InterpretRequest, current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    塔罗牌解读接口
    1. 检查用户今日配额
    2. 如果有配额，调用 LLM 生成流式响应
    """
    logger.info(f"Received interpret request from user {current_user.id}")
    
    # 1. Check Quota
    if not current_user.unlimitedQuota:
        quota_info = QuotaService.get_user_quota(current_user.id, db)
        if quota_info.remaining <= 0:
             logger.warning(f"User {current_user.id} exceeded daily quota")
             return ErrorResponse(success=False, error={"code": "QUOTA_EXCEEDED", "message": "今日额度已用完"})

    # 2. Stream Response
    logger.info(f"Starting stream for user {current_user.id}")
    return StreamingResponse(generate_interpretation_stream(current_user.id, request), media_type="text/event-stream")

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
    suggestions_map = {
        "cn": "基于您的工作发展问题，我建议您可以继续探索以下方向：\n\n1. 职业技能提升\n2. 扩展人脉网络\n3. 寻找导师指导\n\n鼓励您持续探索！",
        "en": "Based on your question, I suggest you explore the following areas:\n\n1. Skill Development\n2. Networking\n3. Mentorship\n\nKeep exploring!",
        "jp": "あなたの質問に基づいて、以下の分野を探求することをお勧めします：\n\n1. スキルアップ\n2. 人脈作り\n3. メンターを探す\n\n探求を続けましょう！"
    }
    suggestion = suggestions_map.get(request.lang, suggestions_map["cn"])
    return SuccessResponse(data=SuggestResponse(suggestion=suggestion))

@router.get("/history", response_model=SuccessResponse)
def history(userId: str, current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    if userId != current_user.id and not current_user.isDemo:
        raise HTTPException(status_code=403, detail="Forbidden")
        
    try:
        items = db.query(TarotInterpretation).filter(TarotInterpretation.user_id == userId).order_by(TarotInterpretation.created_at.desc()).limit(20).all()
            
        records = []
        for item in items:
            records.append(InterpretationRecord(
                id=item.id,
                userId=str(item.user_id),
                question=item.question,
                spreadType=item.spread_type,
                cards=item.cards,
                interpretation=item.interpretation,
                createdAt=item.created_at.isoformat() if item.created_at else None
            ))
                
        return SuccessResponse(data=HistoryResponse(interpretations=records))
    except Exception as e:
        return ErrorResponse(success=False, error={"code": "DATABASE_ERROR", "message": str(e)})
