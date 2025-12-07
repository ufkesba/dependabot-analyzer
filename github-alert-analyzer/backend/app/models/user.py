"""User database model."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class User(Base):
    """User account model."""
    
    __tablename__ = "users"
    
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    subscription_tier: Mapped[str] = mapped_column(String(50), default="free")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    
    # Relationships
    oauth_connections = relationship("OAuthConnection", back_populates="user", cascade="all, delete-orphan")
    llm_configurations = relationship("LLMConfiguration", back_populates="user", cascade="all, delete-orphan")
    repositories = relationship("Repository", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<User {self.email}>"


class OAuthConnection(Base):
    """OAuth connection for external providers."""
    
    __tablename__ = "oauth_connections"
    
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)  # 'github', 'google'
    provider_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    access_token: Mapped[str] = mapped_column(String(500), nullable=False)  # Should be encrypted
    refresh_token: Mapped[str | None] = mapped_column(String(500), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scopes: Mapped[str | None] = mapped_column(String(500), nullable=True)  # Comma-separated
    profile_data: Mapped[str | None] = mapped_column(String(2000), nullable=True)  # JSON string
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    
    # Relationships
    user = relationship("User", back_populates="oauth_connections")
    
    def __repr__(self) -> str:
        return f"<OAuthConnection {self.provider} for user {self.user_id}>"


class LLMConfiguration(Base):
    """LLM provider configuration per user."""
    
    __tablename__ = "llm_configurations"
    
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)  # 'openai', 'anthropic', 'azure'
    api_key: Mapped[str] = mapped_column(String(500), nullable=False)  # Should be encrypted
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    max_tokens: Mapped[int] = mapped_column(default=4096)
    temperature: Mapped[float] = mapped_column(default=0.7)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    
    # Relationships
    user = relationship("User", back_populates="llm_configurations")
    
    def __repr__(self) -> str:
        return f"<LLMConfiguration {self.provider}/{self.model_name}>"
