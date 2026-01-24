from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Date, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import uuid

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, index=True)
    username = Column(String(255), nullable=True)
    password = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    quota = Column(Integer, default=3)
    vip_level = Column(Integer, default=0)
    vip_expire_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    payments = relationship("Payment", back_populates="user")
    daily_quotas = relationship("DailyQuota", back_populates="user")
    interpretations = relationship("TarotInterpretation", back_populates="user")

class AdminUser(Base):
    __tablename__ = "admin_users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(255), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    role = Column(String(50), default="admin")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"))
    stripe_session_id = Column(String(255), nullable=True)
    amount_total = Column(Integer, nullable=True)
    currency = Column(String(10), nullable=True)
    status = Column(String(50), nullable=True)
    price_id = Column(String(255), nullable=True)
    vip_level = Column(Integer, nullable=True)
    vip_duration = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="payments")

class DailyQuota(Base):
    __tablename__ = "daily_quotas"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"))
    date = Column(Date, nullable=False)
    count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="daily_quotas")

class TarotInterpretation(Base):
    __tablename__ = "tarot_interpretations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"))
    question = Column(Text, nullable=True)
    spread_type = Column(String(50), nullable=True)
    cards = Column(JSON, nullable=True)
    interpretation = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="interpretations")
