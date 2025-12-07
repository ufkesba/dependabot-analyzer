"""Repository database model."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Repository(Base):
    """GitHub repository model."""
    
    __tablename__ = "repositories"
    
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    github_repo_id: Mapped[int] = mapped_column(Integer, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)  # e.g., "owner/repo"
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    is_private: Mapped[bool] = mapped_column(Boolean, default=False)
    is_monitored: Mapped[bool] = mapped_column(Boolean, default=True)
    primary_language: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sync_status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, syncing, completed, failed
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    alert_count: Mapped[int] = mapped_column(Integer, default=0)
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
    user = relationship("User", back_populates="repositories")
    alerts = relationship("Alert", back_populates="repository", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Repository {self.full_name}>"


class SyncJob(Base):
    """Repository sync job tracking."""
    
    __tablename__ = "sync_jobs"
    
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    repository_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, running, completed, failed
    job_type: Mapped[str] = mapped_column(String(50), default="full_sync")  # full_sync, alert_sync
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    alerts_processed: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    
    def __repr__(self) -> str:
        return f"<SyncJob {self.id} for repo {self.repository_id}>"
