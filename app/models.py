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
    vipLevel: Optional[int] = 0
    vipExpireAt: Optional[Union[datetime, str]] = None
    accessToken: Optional[str] = None
    loginToken: Optional[str] = None

class SocialLoginRequest(BaseModel):
    token: str

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

class TarotCategoryBase(BaseModel):
    slug: str
    name: str
    name_en: Optional[str] = None
    name_jp: Optional[str] = None
    description: Optional[str] = None
    description_en: Optional[str] = None
    description_jp: Optional[str] = None
    sort_order: Optional[int] = 0

class TarotCategoryCreate(TarotCategoryBase):
    pass

class TarotCategoryUpdate(BaseModel):
    slug: Optional[str] = None
    name: Optional[str] = None
    name_en: Optional[str] = None
    name_jp: Optional[str] = None
    description: Optional[str] = None
    description_en: Optional[str] = None
    description_jp: Optional[str] = None
    sort_order: Optional[int] = None

class TarotCategoryResponse(TarotCategoryBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class TarotSpreadBase(BaseModel):
    category_id: int
    name: str
    name_en: Optional[str] = None
    name_jp: Optional[str] = None
    description: Optional[str] = None
    description_en: Optional[str] = None
    description_jp: Optional[str] = None
    card_count: Optional[int] = 1
    permission: Optional[str] = "Free"
    positions: Optional[List[Dict[str, Any]]] = None # To accept list of dicts for update
    sort_order: Optional[int] = 0

class TarotSpreadCreate(TarotSpreadBase):
    pass

class TarotSpreadUpdate(BaseModel):
    category_id: Optional[int] = None
    name: Optional[str] = None
    name_en: Optional[str] = None
    name_jp: Optional[str] = None
    description: Optional[str] = None
    description_en: Optional[str] = None
    description_jp: Optional[str] = None
    card_count: Optional[int] = None
    permission: Optional[str] = None
    positions: Optional[List[Dict[str, Any]]] = None
    sort_order: Optional[int] = None

class TarotSpreadPositionResponse(BaseModel):
    id: int
    spread_id: int
    position_index: int
    name: str
    name_en: Optional[str] = None
    name_jp: Optional[str] = None
    description: Optional[str] = None
    description_en: Optional[str] = None
    description_jp: Optional[str] = None

    class Config:
        from_attributes = True

class TarotSpreadResponse(TarotSpreadBase):
    id: int
    positions: List[TarotSpreadPositionResponse] = []
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class TarotCategoryWithSpreadsResponse(TarotCategoryResponse):
    spreads: List[TarotSpreadResponse] = []

    class Config:
        from_attributes = True

class InterpretRequest(BaseModel):
    cards: List[TarotCard]
    question: Optional[str] = None
    spread: Optional[Spread] = None
    lang: str = "cn"
    stream: bool = True

class SuggestRequest(BaseModel):
    question: str
    interpretation: str
    lang: str = "cn"

class SuggestResponse(BaseModel):
    suggestion: str

class FollowupRequest(BaseModel):
    cards: List[TarotCard]
    question: str
    interpretation: str
    spread: Optional[Spread] = None
    count: Optional[int] = None
    lang: str = "cn"

class FollowupResponse(BaseModel):
    questions: List[str]

class InterpretationRecord(BaseModel):
    id: str
    userId: str
    question: Optional[str]
    spreadType: Optional[str]
    cards: Optional[str]
    interpretation: Optional[str]
    createdAt: Optional[str]

    class Config:
        from_attributes = True

class HistoryResponse(BaseModel):
    interpretations: List[InterpretationRecord]

class SharerInfo(BaseModel):
    username: str
    avatar: Optional[str] = None

class ShareInterpretationData(BaseModel):
    id: str
    question: str
    spreadType: str
    cards: str
    interpretation: str
    createdAt: datetime
    sharerInfo: SharerInfo

class CreateCheckoutSessionRequest(BaseModel):
    price_id: str
    success_url: str
    cancel_url: str
    user_id: str
    user_email: str

class CheckoutSessionResponse(BaseModel):
    sessionId: str
    url: str

class CancelSubscriptionRequest(BaseModel):
    subscription_id: Optional[str] = None
    reason: Optional[str] = None

class QuotaResponse(BaseModel):
    remaining: int
    used: int
    total: Union[str, int]
    isDemo: bool
