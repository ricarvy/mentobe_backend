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
from datetime import datetime

router = APIRouter(prefix="/tarot", tags=["tarot"])

async def save_interpretation(user_id: str, request: InterpretRequest, full_text: str):
    # Save to DB
    try:
        cards_json = json.dumps([c.dict() for c in request.cards])
        
        record = {
            "user_id": user_id,
            "question": request.question,
            "spread_type": request.spread.id,
            "cards": cards_json,
            "interpretation": full_text,
            "created_at": datetime.now().isoformat()
        }
        
        supabase.table("interpretations").insert(record).execute()
        
        # Update quota
        today = datetime.now().strftime("%Y-%m-%d")
        # Check if quota record exists
        q_res = supabase.table("daily_quotas").select("*").eq("user_id", user_id).eq("date", today).execute()
        if q_res.data:
            current_count = q_res.data[0]["count"]
            supabase.table("daily_quotas").update({"count": current_count + 1}).eq("id", q_res.data[0]["id"]).execute()
        else:
            supabase.table("daily_quotas").insert({"user_id": user_id, "date": today, "count": 1}).execute()
            
    except Exception as e:
        print(f"Failed to save interpretation: {e}")

async def fake_llm_stream(user_id: str, request: InterpretRequest):
    # Simulate thinking and streaming
    full_text = ""
    
    # Mock response
    response_text = f"""
    Based on your question "{request.question}" and the cards drawn...
    
    1. **{request.cards[0].name}**: This card represents...
    
    Overall, the situation looks promising.
    """
    
    lines = response_text.split('\n')
    for line in lines:
        chunk = line + "\n"
        full_text += chunk
        yield chunk
        await asyncio.sleep(0.1) # Simulate delay
        
    # Save after streaming
    # Note: In a real generator, we might need to offload this or ensure it runs. 
    # Calling an async function here works.
    await save_interpretation(user_id, request, full_text)

@router.post("/interpret")
async def interpret(request: InterpretRequest, current_user: UserResponse = Depends(get_current_user)):
    # 1. Check Quota
    if not current_user.unlimitedQuota:
        today = datetime.now().strftime("%Y-%m-%d")
        q_res = supabase.table("daily_quotas").select("*").eq("user_id", current_user.id).eq("date", today).execute()
        used = 0
        if q_res.data:
            used = q_res.data[0]["count"]
        
        if used >= 3: # Limit 3
             return ErrorResponse(success=False, error={"code": "QUOTA_EXCEEDED", "message": "Daily quota exceeded"})

    # 2. Stream Response
    return StreamingResponse(fake_llm_stream(current_user.id, request), media_type="text/event-stream")

@router.post("/suggest", response_model=SuccessResponse)
async def suggest(request: SuggestRequest):
    # Mock suggestion
    suggestion = f"Consider exploring more about {request.cards[0].name}..."
    return SuccessResponse(data=SuggestResponse(suggestion=suggestion))

@router.get("/history", response_model=SuccessResponse)
async def history(userId: str, current_user: UserResponse = Depends(get_current_user)):
    if userId != current_user.id and not current_user.isDemo:
        # Strict check
        pass
        
    try:
        response = supabase.table("interpretations").select("*").eq("user_id", current_user.id).order("created_at", desc=True).limit(20).execute()
        
        records = []
        for item in response.data:
            records.append(InterpretationRecord(
                id=str(item["id"]),
                userId=item["user_id"],
                question=item["question"],
                spreadType=item["spread_type"],
                cards=item["cards"] if isinstance(item["cards"], str) else json.dumps(item["cards"]),
                interpretation=item["interpretation"],
                createdAt=item["created_at"]
            ))
            
        return SuccessResponse(data=HistoryResponse(interpretations=records))
    except Exception as e:
        return ErrorResponse(success=False, error={"code": "INTERNAL_ERROR", "message": str(e)})
