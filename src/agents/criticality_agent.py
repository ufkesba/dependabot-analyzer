"""
Criticality Agent - Assesses vulnerability risk based on service criticality.

This agent loads service criticality configuration and adjusts vulnerability
priorities based on the service's business impact, data sensitivity, and exposure.
"""
import os
import yaml
from typing import Optional
from pathlib import Path
from rich.console import Console

from ..models.criticality import (
    ServiceCriticality,
    CriticalityAssessment,
    CriticalityLevel,
    DataClassification,
    ExposureLevel,
    BusinessImpact
)
from .deep_analyzer import AnalysisReport
from .false_positive_checker import FalsePositiveCheck

console = Console()

CRITICALITY_CONFIG_FILENAME = ".criticality.yaml"


class CriticalityAgent:
    """
    Agent that evaluates vulnerability risk in context of service criticality.
    
    Loads .criticality.yaml configs from service directories and combines
    them with vulnerability analysis to produce final risk assessments.
    """

    def __init__(self, repo_path: Optional[str] = None, verbose: bool = False):
        """
        Args:
            repo_path: Local path to repository root (for loading configs)
            verbose: Show detailed agent activity
        """
        self.repo_path = repo_path
        self.verbose = verbose
        self._config_cache = {}  # Cache loaded configs

    def _load_criticality_config(self, service_path: str) -> Optional[ServiceCriticality]:
        """
        Load criticality configuration for a service directory.

        Args:
            service_path: Path to service directory (e.g., "services/payment-api")

        Returns:
            ServiceCriticality config if found, None otherwise
        """
        # Check cache first
        if service_path in self._config_cache:
            return self._config_cache[service_path]

        if not self.repo_path:
            return None

        config_path = Path(self.repo_path) / service_path / CRITICALITY_CONFIG_FILENAME

        if not config_path.exists():
            if self.verbose:
                console.print(f"[dim]No criticality config found at {config_path}[/dim]")
            self._config_cache[service_path] = None
            return None

        try:
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)

            config = ServiceCriticality(**config_data)
            self._config_cache[service_path] = config

            if self.verbose:
                console.print(f"[green]✓ Loaded criticality config for {config.service_name}[/green]")

            return config

        except Exception as e:
            if self.verbose:
                console.print(f"[yellow]Warning: Failed to load config at {config_path}: {str(e)}[/yellow]")
            self._config_cache[service_path] = None
            return None

    def _calculate_base_risk_score(
        self,
        report: AnalysisReport,
        fp_check: Optional[FalsePositiveCheck]
    ) -> float:
        """
        Calculate base risk score from vulnerability analysis (1-10 scale).

        Args:
            report: Analysis report from DeepAnalyzer
            fp_check: False positive check result (if available)

        Returns:
            Risk score from 1 (lowest) to 10 (highest)
        """
        # Start with exploitability
        if not report.is_exploitable:
            return 2.0  # Low baseline for non-exploitable

        # If false positive checker downgraded it
        if fp_check and fp_check.is_false_positive:
            return 3.0

        # Map priority to base scores
        priority_scores = {
            "critical": 9.0,
            "high": 7.0,
            "medium": 5.0,
            "low": 3.0
        }
        base_score = priority_scores.get(report.priority.lower(), 5.0)

        # Adjust for confidence
        confidence_adjustments = {
            "high": 0.0,
            "medium": -1.0,
            "low": -2.0
        }
        base_score += confidence_adjustments.get(report.confidence.lower(), 0.0)

        # Clamp to 1-10 range
        return max(1.0, min(10.0, base_score))

    def _calculate_criticality_multiplier(
        self,
        service_config: Optional[ServiceCriticality]
    ) -> float:
        """
        Calculate risk multiplier based on service criticality (0.5 - 3.0).

        Args:
            service_config: Service criticality configuration

        Returns:
            Multiplier value
        """
        if not service_config:
            return 1.0  # No config = no adjustment

        multiplier = 1.0

        # Criticality level (base multiplier)
        criticality_multipliers = {
            CriticalityLevel.LOW: 0.7,
            CriticalityLevel.MEDIUM: 1.0,
            CriticalityLevel.HIGH: 1.5,
            CriticalityLevel.CRITICAL: 2.0
        }
        multiplier = criticality_multipliers.get(
            service_config.criticality_level,
            1.0
        )

        # Data classification
        if service_config.data_classification in [
            DataClassification.PHI,
            DataClassification.FINANCIAL,
            DataClassification.PII
        ]:
            multiplier += 0.5

        # Exposure
        if service_config.exposure == ExposureLevel.PUBLIC:
            multiplier += 0.5
        elif service_config.exposure == ExposureLevel.EXTERNAL:
            multiplier += 0.3

        # Business impact
        if service_config.business_impact == BusinessImpact.CRITICAL:
            multiplier += 0.5
        elif service_config.business_impact == BusinessImpact.SIGNIFICANT:
            multiplier += 0.3

        # User facing
        if service_config.user_facing:
            multiplier += 0.2

        # Compliance requirements
        if service_config.compliance_requirements:
            multiplier += 0.2

        # Clamp to reasonable range
        return max(0.5, min(3.0, multiplier))

    def _determine_adjusted_priority(
        self,
        original_priority: str,
        final_risk_score: float
    ) -> str:
        """
        Determine adjusted priority based on final risk score.

        Args:
            original_priority: Original priority from vulnerability analysis
            final_risk_score: Combined risk score (1-10)

        Returns:
            Adjusted priority string
        """
        if final_risk_score >= 9.0:
            return "critical"
        elif final_risk_score >= 7.0:
            return "high"
        elif final_risk_score >= 4.5:
            return "medium"
        else:
            return "low"

    def _identify_risk_factors(
        self,
        service_config: Optional[ServiceCriticality],
        report: AnalysisReport
    ) -> list[str]:
        """
        Identify specific risk factors for this assessment.

        Args:
            service_config: Service criticality configuration
            report: Vulnerability analysis report

        Returns:
            List of risk factor descriptions
        """
        factors = []

        if not service_config:
            return ["No service criticality configuration"]

        # Service-level factors
        if service_config.exposure == ExposureLevel.PUBLIC:
            factors.append("Publicly exposed service")
        elif service_config.exposure == ExposureLevel.EXTERNAL:
            factors.append("Externally accessible service")

        if service_config.data_classification in [
            DataClassification.PHI,
            DataClassification.FINANCIAL,
            DataClassification.PII
        ]:
            factors.append(f"Handles sensitive data ({service_config.data_classification.value})")

        if service_config.user_facing:
            factors.append("User-facing service")

        if service_config.business_impact in [
            BusinessImpact.CRITICAL,
            BusinessImpact.SIGNIFICANT
        ]:
            factors.append(f"High business impact ({service_config.business_impact.value})")

        if service_config.compliance_requirements:
            factors.append(f"Compliance requirements: {', '.join(service_config.compliance_requirements)}")

        # Vulnerability-level factors
        if report.is_exploitable:
            factors.append("Vulnerability confirmed exploitable")

        if report.confidence == "high":
            factors.append("High confidence in exploitability assessment")

        return factors

    def _generate_response_time_recommendation(
        self,
        adjusted_priority: str,
        service_config: Optional[ServiceCriticality]
    ) -> str:
        """
        Generate recommended response timeframe.

        Args:
            adjusted_priority: The adjusted priority level
            service_config: Service criticality configuration

        Returns:
            Recommended response time string
        """
        # Base recommendations
        response_times = {
            "critical": "Immediate (within hours)",
            "high": "24-48 hours",
            "medium": "1 week",
            "low": "Next maintenance window"
        }

        base_time = response_times.get(adjusted_priority, "1 week")

        # Accelerate for compliance requirements
        if service_config and service_config.compliance_requirements:
            if adjusted_priority in ["critical", "high"]:
                return "Immediate (compliance-driven)"

        return base_time

    def _build_assessment_reasoning(
        self,
        base_risk: float,
        multiplier: float,
        final_risk: float,
        service_config: Optional[ServiceCriticality],
        original_priority: str,
        adjusted_priority: str
    ) -> str:
        """
        Build human-readable reasoning for the assessment.

        Args:
            base_risk: Base risk score
            multiplier: Criticality multiplier
            final_risk: Final risk score
            service_config: Service criticality config
            original_priority: Original priority
            adjusted_priority: Adjusted priority

        Returns:
            Reasoning text
        """
        reasoning_parts = []

        reasoning_parts.append(
            f"Base vulnerability risk score: {base_risk:.1f}/10 (priority: {original_priority})"
        )

        if service_config:
            reasoning_parts.append(
                f"Service criticality multiplier: {multiplier:.2f}x "
                f"(level: {service_config.criticality_level.value})"
            )
        else:
            reasoning_parts.append("No service criticality configuration found - using default multiplier")

        reasoning_parts.append(
            f"Final risk score: {final_risk:.1f}/10 (adjusted priority: {adjusted_priority})"
        )

        if adjusted_priority != original_priority:
            reasoning_parts.append(
                f"Priority adjusted from {original_priority} to {adjusted_priority} based on service criticality"
            )

        return "\n".join(reasoning_parts)

    async def assess(
        self,
        manifest_path: str,
        report: AnalysisReport,
        fp_check: Optional[FalsePositiveCheck] = None
    ) -> CriticalityAssessment:
        """
        Assess vulnerability risk considering service criticality.

        Args:
            manifest_path: Path to manifest file (e.g., "services/payment-api/package.json")
            report: Vulnerability analysis report
            fp_check: False positive check result (optional)

        Returns:
            CriticalityAssessment with adjusted risk and priority
        """
        # Extract service path from manifest path
        service_path = os.path.dirname(manifest_path) if manifest_path else ""

        if self.verbose:
            console.print(f"\n[cyan]Assessing criticality for service at: {service_path or '(root)'}[/cyan]")

        # Load service criticality config
        service_config = self._load_criticality_config(service_path)

        # Calculate risk scores
        base_risk_score = self._calculate_base_risk_score(report, fp_check)
        criticality_multiplier = self._calculate_criticality_multiplier(service_config)
        final_risk_score = base_risk_score * criticality_multiplier

        # Clamp final score
        final_risk_score = max(1.0, min(10.0, final_risk_score))

        # Determine adjusted priority
        original_priority = report.priority
        adjusted_priority = self._determine_adjusted_priority(original_priority, final_risk_score)

        # Identify risk factors
        risk_factors = self._identify_risk_factors(service_config, report)

        # Generate recommendations
        recommended_response_time = self._generate_response_time_recommendation(
            adjusted_priority,
            service_config
        )

        # Build reasoning
        assessment_reasoning = self._build_assessment_reasoning(
            base_risk_score,
            criticality_multiplier,
            final_risk_score,
            service_config,
            original_priority,
            adjusted_priority
        )

        assessment = CriticalityAssessment(
            service_path=service_path,
            service_criticality=service_config,
            base_risk_score=base_risk_score,
            criticality_multiplier=criticality_multiplier,
            final_risk_score=final_risk_score,
            original_priority=original_priority,
            adjusted_priority=adjusted_priority,
            risk_factors=risk_factors,
            assessment_reasoning=assessment_reasoning,
            recommended_response_time=recommended_response_time
        )

        if self.verbose:
            console.print(f"[green]✓ Risk assessment complete: {adjusted_priority} priority (score: {final_risk_score:.1f}/10)[/green]")
            if adjusted_priority != original_priority:
                console.print(f"[yellow]Priority adjusted from {original_priority} → {adjusted_priority}[/yellow]")

        return assessment
