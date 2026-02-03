from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.db_models import User
from app.services.quota import QuotaService
from app.services.llm import stream_palm_analysis
import logging
import os

router = APIRouter(tags=["palm"])
logger = logging.getLogger(__name__)

PROMPT_FILE = "palm_prompt"

def get_palm_prompt():
    if os.path.exists(PROMPT_FILE):
        with open(PROMPT_FILE, "r", encoding="utf-8") as f:
            return f.read()
    return "Please analyze this palm image."

@router.post("/palm/analyze")
async def analyze_palm(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Analyze palm image and return streaming response.
    Consumes 1 quota per request.
    """
    logger.info(f"Palm analysis request from user {current_user.id}")

    # Check file type
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image"
        )

    # Check quota
    quota_res = QuotaService.get_user_quota(current_user.id, db)
    if quota_res.remaining <= 0 and quota_res.total != "Unlimited":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Quota exceeded"
        )

    # Read image content
    try:
        image_bytes = await file.read()
    except Exception as e:
        logger.error(f"Failed to read uploaded file: {e}")
        raise HTTPException(status_code=500, detail="Failed to read file")

    # Deduct quota
    # We deduct before processing. If processing fails, quota is lost (standard simpler implementation).
    # To be nicer, we could deduct after success, but streaming makes "success" ambiguous.
    # Given "每次识别消耗一个quota", deducting on start is fair.
    if quota_res.total != "Unlimited":
        if not QuotaService.reduce_quota(current_user.id, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Quota exceeded during deduction"
            )

    # Get prompt
    prompt = get_palm_prompt()

    # Stream response
    return StreamingResponse(
        stream_palm_analysis(image_bytes, prompt),
        media_type="text/event-stream"
    )
