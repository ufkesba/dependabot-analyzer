"""Alert and analysis database models."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, Integer, Float, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Alert(Base):
    """Dependabot security alert model."""
    
    __tablename__ = "alerts"
    
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
    github_alert_number: Mapped[int] = mapped_column(Integer, nullable=False)
    package_name: Mapped[str] = mapped_column(String(255), nullable=False)
    package_ecosystem: Mapped[str] = mapped_column(String(50), nullable=False)  # npm, pip, maven, etc.
    severity: Mapped[str] = mapped_column(String(20), nullable=False)  # critical, high, medium, low
    state: Mapped[str] = mapped_column(String(20), default="open")  # open, dismissed, fixed
    vulnerable_version_range: Mapped[str | None] = mapped_column(String(255), nullable=True)
    patched_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    github_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dismissed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dismissed_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    fixed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
    repository = relationship("Repository", back_populates="alerts")
    vulnerability = relationship("Vulnerability", back_populates="alert", uselist=False, cascade="all, delete-orphan")
    analyses = relationship("AlertAnalysis", back_populates="alert", cascade="all, delete-orphan")
    workflows = relationship("AnalysisWorkflow", back_populates="alert", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Alert {self.package_name} ({self.severity})>"


class Vulnerability(Base):
    """Vulnerability details for an alert."""
    
    __tablename__ = "vulnerabilities"
    
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    alert_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("alerts.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )
    cve_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    ghsa_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str | None] = mapped_column(String(20), nullable=True)
    cvss_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    cvss_vector: Mapped[str | None] = mapped_column(String(100), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    references: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array as string
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    
    # Relationships
    alert = relationship("Alert", back_populates="vulnerability")
    
    def __repr__(self) -> str:
        return f"<Vulnerability {self.cve_id or self.ghsa_id}>"


class AlertAnalysis(Base):
    """LLM analysis results for an alert."""
    
    __tablename__ = "alert_analyses"
    
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    alert_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("alerts.id", ondelete="CASCADE"),
        nullable=False
    )
    llm_config_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    llm_provider: Mapped[str] = mapped_column(String(50), nullable=False)
    llm_model: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, processing, completed, failed
    analysis_result: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    raw_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    processing_time_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    analyzed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    
    # Relationships
    alert = relationship("Alert", back_populates="analyses")
    
    def __repr__(self) -> str:
        return f"<AlertAnalysis {self.id} ({self.status})>"
