"""
Data models for service criticality configuration and assessment.
"""
from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field


class CriticalityLevel(str, Enum):
    """Overall criticality level of a service"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DataClassification(str, Enum):
    """Classification of data handled by the service"""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    PII = "pii"  # Personally Identifiable Information
    PHI = "phi"  # Protected Health Information
    FINANCIAL = "financial"


class ExposureLevel(str, Enum):
    """How the service is exposed"""
    INTERNAL = "internal"  # Only internal services can access
    EXTERNAL = "external"  # Accessible from internet with auth
    PUBLIC = "public"  # Publicly accessible


class BusinessImpact(str, Enum):
    """Impact of service downtime on business"""
    MINIMAL = "minimal"
    MODERATE = "moderate"
    SIGNIFICANT = "significant"
    CRITICAL = "critical"


class ServiceCriticality(BaseModel):
    """
    Configuration defining criticality attributes of a microservice.
    
    This is loaded from .criticality.yaml files in service directories.
    """
    service_name: str = Field(..., description="Name of the service")
    criticality_level: CriticalityLevel = Field(
        default=CriticalityLevel.MEDIUM,
        description="Overall criticality rating"
    )
    data_classification: DataClassification = Field(
        default=DataClassification.INTERNAL,
        description="Highest classification of data this service handles"
    )
    exposure: ExposureLevel = Field(
        default=ExposureLevel.INTERNAL,
        description="How the service is exposed"
    )
    business_impact: BusinessImpact = Field(
        default=BusinessImpact.MODERATE,
        description="Impact on business operations if service fails"
    )
    user_facing: bool = Field(
        default=False,
        description="Whether service directly serves end users"
    )
    compliance_requirements: List[str] = Field(
        default_factory=list,
        description="Compliance frameworks (GDPR, HIPAA, PCI-DSS, SOC2, etc.)"
    )
    sla_tier: Optional[str] = Field(
        default=None,
        description="Availability SLA (e.g., '99.9%', '99.99%')"
    )
    critical_dependencies: List[str] = Field(
        default_factory=list,
        description="Other critical services this depends on"
    )
    description: Optional[str] = Field(
        default=None,
        description="Human-readable description of the service"
    )


class CriticalityAssessment(BaseModel):
    """
    Assessment output that combines vulnerability analysis with service criticality.
    """
    service_path: str = Field(..., description="Path to the service directory")
    service_criticality: Optional[ServiceCriticality] = Field(
        default=None,
        description="Criticality config if found"
    )
    
    # Risk scoring (1-10 scale)
    base_risk_score: float = Field(..., description="Base risk from vulnerability analysis")
    criticality_multiplier: float = Field(..., description="Multiplier based on service criticality")
    final_risk_score: float = Field(..., description="Combined risk score")
    
    # Priority adjustment
    original_priority: str = Field(..., description="Priority from vulnerability analysis")
    adjusted_priority: str = Field(..., description="Priority adjusted for service criticality")
    
    # Risk factors
    risk_factors: List[str] = Field(
        default_factory=list,
        description="List of risk-elevating factors identified"
    )
    
    # Reasoning
    assessment_reasoning: str = Field(..., description="Explanation of risk assessment")
    recommended_response_time: Optional[str] = Field(
        default=None,
        description="Suggested timeframe for addressing (e.g., 'immediate', '24h', '1 week')"
    )
