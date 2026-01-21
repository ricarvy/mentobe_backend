from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Any, Union, Dict
from datetime import datetime

# Common Response Models
class BaseResponse(BaseModel):
    success: bool
    message: Optional[str] = None

class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[str] = None

class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail

class SuccessResponse(BaseResponse):
    success: bool = True
    data: Optional[Any] = None

# Auth Models
class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    isActive: bool
    isDemo: Optional[bool] = False
    unlimitedQuota: Optional[bool] = False

# Tarot Models
class TarotCard(BaseModel):
    id: int
    name: str
    nameEn: Optional[str] = None
    meaning: Optional[str] = None
    reversedMeaning: Optional[str] = None
    image: Optional[str] = None
    imageUrl: Optional[str] = None
    nameJa: Optional[str] = None
    keywords: Optional[List[str]] = None
    suit: Optional[str] = None
    number: Optional[int] = None
    isReversed: bool = False

class SpreadPosition(BaseModel):
    id: str
    name: str
    description: str

class Spread(BaseModel):
    id: str
    name: str
    description: str
    positions: List[SpreadPosition]

class InterpretRequest(BaseModel):
    userId: str
    question: str
    spread: Spread
    cards: List[TarotCard]
    lang: str = "cn" # cn, en, jp

class InterpretationRecord(BaseModel):
    id: str
    userId: str
    question: str
    spreadType: str
    cards: str # JSON string
    interpretation: str
    createdAt: datetime

class SuggestRequest(BaseModel):
    question: str
    cards: List[TarotCard]
    interpretation: str
    lang: str = "cn" # cn, en, jp

class SuggestResponse(BaseModel):
    suggestion: str

class HistoryResponse(BaseModel):
    interpretations: List[InterpretationRecord]

# Quota
class QuotaResponse(BaseModel):
    remaining: int
    used: int
    total: Union[int, str]
    isDemo: bool

# Stripe Models
class CreateCheckoutSessionRequest(BaseModel):
    price_id: str = Field(..., alias="priceId")
    user_id: str = Field(..., alias="userId")
    user_email: EmailStr = Field(..., alias="userEmail")
    success_url: str = Field(..., alias="successUrl")
    cancel_url: str = Field(..., alias="cancelUrl")

    class Config:
        populate_by_name = True

class CheckoutSessionResponse(BaseModel):
    session_id: str = Field(..., alias="sessionId")
    url: str
