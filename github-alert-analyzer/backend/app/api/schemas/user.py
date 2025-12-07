"""Pydantic schemas for user-related data."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    """Schema for creating a new user."""
    password: str = Field(..., min_length=8, max_length=100)


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str


class UserResponse(UserBase):
    """Schema for user response."""
    id: str
    is_active: bool
    is_verified: bool
    subscription_tier: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """Schema for updating user."""
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None


class TokenResponse(BaseModel):
    """Schema for token response."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class LLMConfigBase(BaseModel):
    """Base LLM configuration schema."""
    provider: str = Field(..., pattern="^(openai|anthropic|azure)$")
    model_name: str
    max_tokens: int = 4096
    temperature: float = Field(default=0.7, ge=0, le=2)
    is_default: bool = False


class LLMConfigCreate(LLMConfigBase):
    """Schema for creating LLM configuration."""
    api_key: str = Field(..., min_length=10)


class LLMConfigResponse(LLMConfigBase):
    """Schema for LLM configuration response."""
    id: str
    created_at: datetime
    # Note: api_key is not included for security
    
    class Config:
        from_attributes = True


class LLMConfigUpdate(BaseModel):
    """Schema for updating LLM configuration."""
    model_name: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = Field(default=None, ge=0, le=2)
    is_default: Optional[bool] = None
