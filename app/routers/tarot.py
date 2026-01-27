from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.concurrency import run_in_threadpool
from app.models import (
    InterpretRequest, SuggestRequest, SuggestResponse, 
    HistoryResponse, SuccessResponse, ErrorResponse,
    InterpretationRecord, UserResponse,
    FollowupRequest, FollowupResponse
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
import re
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tarot", tags=["tarot"])

def _save_interpretation_sync(user_id: str, request: InterpretRequest, full_text: str):
    """
    Sync function to save interpretation and reduce quota
    """
    # Create a new session for this background task
    db = SessionLocal()
    try:
        # Handle demo user fallback ID
        if user_id == "demo-user-id":
            logger.info(f"Mapping 'demo-user-id' to actual demo UUID for storage")
            user_id = "00000000-0000-0000-0000-000000000000"

        logger.info(f"Saving interpretation for user {user_id}")
        
        # Serialize cards to list of dicts for JSON column
        cards_data = []
        for c in request.cards:
            if hasattr(c, 'model_dump'):
                cards_data.append(c.model_dump())
            else:
                cards_data.append(c.dict())
        
        record = TarotInterpretation(
            user_id=user_id,
            question=request.question,
            spread_type=request.spread.id,
            cards=cards_data, 
            interpretation=full_text,
            created_at=datetime.now()
        )
        
        db.add(record)
        db.flush()
        db.commit()
        
        # Update quota within the same transaction if possible, or separately
        # To ensure consistency, we should try to do it here.
        
        try:
            # We pass the db session to reduce_quota. 
            # Note: reduce_quota commits inside. If we want atomic, we should change reduce_quota 
            # or handle commit here. For now, let's trust reduce_quota logic but we need to commit record first 
            # or add it to session and let reduce_quota commit it?
            # reduce_quota calls db.commit(). So if we add record to db, it will be committed there too.
            
            quota_success = QuotaService.reduce_quota(user_id, db)
            if not quota_success:
                logger.warning(f"Quota reduction returned False for user {user_id} after saving interpretation")
            else:
                logger.info(f"Interpretation saved and quota updated for user {user_id}")
                
        except Exception as qe:
            logger.error(f"Failed to reduce quota for user {user_id}: {qe}")
            # If quota fails, we still try to commit the interpretation?
            # reduce_quota does rollback on error.
            # If reduce_quota failed/rolled back, 'record' might be detached or not committed.
            # Let's try to commit explicitly if reduce_quota didn't commit successfully?
            # Actually reduce_quota commits on success.
            pass

        # If reduce_quota wasn't called (e.g. VIP logic inside it returns True without commit if no change needed?)
        # Let's check implementation of reduce_quota.
        # reduce_quota commits if it changes something. If VIP, it returns True but might not commit?
        # Let's ensure we commit the interpretation record regardless.
        
        try:
             db.commit()
        except Exception:
             # It might have been already committed
             db.rollback()
            
    except Exception as e:
        logger.error(f"Failed to save interpretation: {e}")
        db.rollback()
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
    try:
        async for chunk in stream_tarot_interpretation(messages):
            full_text += chunk
            yield chunk
    except Exception as e:
        logger.error(f"Stream generation error for user {user_id}: {e}")
        # yield f"\n[Error: {str(e)}]" # Optional: inform user
    finally:
        # Save after streaming (successful or interrupted)
        if full_text:
            logger.info(f"Stream finished/interrupted. Saving interpretation for user {user_id} (len={len(full_text)})...")
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

@router.post("/followup", response_model=SuccessResponse)
async def followup(request: FollowupRequest):
    """
    追问推荐接口：
    输入：牌阵、选的牌、用户的问题、AI解读内容、追问数
    输出：针对当前AI解读内容，用户下一个可能想问的具体问题列表
    """
    cards_info = []
    for i, card in enumerate(request.cards):
        pos_name = request.spread.positions[i].name if i < len(request.spread.positions) else f"位置 {i+1}"
        status = "逆位" if getattr(card, "isReversed", False) else "正位"
        meaning = card.reversedMeaning if getattr(card, "isReversed", False) else card.meaning
        cards_info.append(f"{i+1}. {pos_name} - {card.name}（{status}）: {meaning}")
    cards_desc = "\n".join(cards_info)

    lang_instruction = {
        "cn": "请生成用户可能的下一个具体问题，语气友好，避免重复当前解读。",
        "en": "Generate likely next specific questions. Be friendly and avoid repeating the current interpretation.",
        "jp": "次にユーザーが質問しそうな具体的な質問を生成してください。丁寧に、現在の解釈の繰り返しは避けてください。"
    }.get(request.lang, "请生成用户可能的下一个具体问题，语气友好，避免重复当前解读。")

    prompt = f"""
    背景：
    - 用户问题：{request.question}
    - 牌阵：{request.spread.name} - {request.spread.description}
    - 抽到的牌：
    {cards_desc}

    当前AI解读内容：
    {request.interpretation}

    任务：
    {lang_instruction}
    数量：{request.followupCount or settings.TAROT_FOLLOWUP_COUNT} 个
    要求：每个问题都应具体、可执行，涵盖情感、行动、风险与时机等不同维度；避免泛泛而谈。
    输出：仅输出问题列表，每行一个问题，不要多余说明。
    """

    messages = [
        {"role": "system", "content": settings.TAROT_SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ]

    text = ""
    try:
        async for chunk in stream_tarot_interpretation(messages):
            text += chunk
    except Exception as e:
        logger.error(f"Followup LLM call failed: {e}")
        text = ""

    fallback_map = {
        "cn": [
            "如果选择A方案，短期内我需要做哪些具体准备？",
            "这段关系中我应该如何设定边界来保护自己？",
            "当前最大的风险点是什么，我可以如何预防？"
        ],
        "en": [
            "If I choose plan A, what concrete steps should I take next?",
            "How can I set healthy boundaries in this relationship to protect myself?",
            "What is the biggest risk right now and how can I mitigate it?"
        ],
        "jp": [
            "A案を選ぶ場合、直近で何を具体的に準備すべきですか？",
            "この関係で自分を守るために、どのように境界線を設定すべきですか？",
            "今最も大きなリスクは何で、どう対処できますか？"
        ]
    }

    questions: list[str] = []

    if text.strip():
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for line in lines:
            cleaned = re.sub(r"^[0-9０-９\.\-\)\s\u2022]+", "", line)
            if cleaned:
                questions.append(cleaned)

    if not questions:
        questions = fallback_map.get(request.lang, fallback_map["cn"])

    questions = questions[: max(1, request.followupCount)]

    return SuccessResponse(data=FollowupResponse(questions=questions))
@router.get("/history", response_model=SuccessResponse)
def history(userId: str, current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    if userId != current_user.id and not current_user.isDemo:
        raise HTTPException(status_code=403, detail="Forbidden")
        
    try:
        items = db.query(TarotInterpretation).filter(TarotInterpretation.user_id == userId).order_by(TarotInterpretation.created_at.desc()).limit(20).all()
            
        records = []
        for item in items:
            # cards is stored as JSON (list/dict) in DB, but InterpretationRecord expects JSON string
            cards_str = json.dumps(item.cards) if item.cards else "[]"
            
            records.append(InterpretationRecord(
                id=str(item.id),
                userId=str(item.user_id),
                question=item.question,
                spreadType=item.spread_type,
                cards=cards_str,
                interpretation=item.interpretation,
                createdAt=item.created_at.isoformat() if item.created_at else None
            ))
                
        return SuccessResponse(data=HistoryResponse(interpretations=records))
    except Exception as e:
        logger.error(f"Error in history endpoint: {str(e)}", exc_info=True)
        return ErrorResponse(success=False, error={"code": "DATABASE_ERROR", "message": str(e)})
