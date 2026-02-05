#!/usr/bin/env python
"""Test script to validate the criticality agent functionality"""
import asyncio
import tempfile
import os
from pathlib import Path

from src.agents.criticality_agent import CriticalityAgent
from src.agents.deep_analyzer import AnalysisReport
from src.models.criticality import (
    ServiceCriticality,
    CriticalityLevel,
    DataClassification,
    ExposureLevel,
    BusinessImpact
)


async def test_criticality_agent():
    """Test the criticality agent with various scenarios"""
    
    print("=" * 70)
    print("Testing Criticality Agent")
    print("=" * 70)
    
    # Create a temporary directory structure with configs
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create service directories with configs
        services = {
            "payment-service": {
                "service_name": "payment-service",
                "criticality_level": "critical",
                "data_classification": "financial",
                "exposure": "external",
                "business_impact": "critical",
                "user_facing": True,
                "compliance_requirements": ["PCI-DSS", "SOC2"],
                "sla_tier": "99.99%"
            },
            "docs-site": {
                "service_name": "docs-site",
                "criticality_level": "low",
                "data_classification": "public",
                "exposure": "public",
                "business_impact": "minimal",
                "user_facing": True,
                "compliance_requirements": []
            },
            "internal-admin": {
                "service_name": "internal-admin",
                "criticality_level": "medium",
                "data_classification": "confidential",
                "exposure": "internal",
                "business_impact": "moderate",
                "user_facing": False,
                "compliance_requirements": ["SOC2"]
            }
        }
        
        # Write config files
        for service_name, config in services.items():
            service_path = Path(tmpdir) / service_name
            service_path.mkdir()
            
            import yaml
            config_file = service_path / ".criticality.yaml"
            with open(config_file, 'w') as f:
                yaml.dump(config, f)
        
        # Create criticality agent
        agent = CriticalityAgent(repo_path=tmpdir, verbose=True)
        
        # Test scenarios
        test_cases = [
            {
                "name": "Payment Service - Medium Vuln → Should Escalate",
                "manifest_path": "payment-service/package.json",
                "report": AnalysisReport(
                    alert_number=1,
                    package="express",
                    vulnerability_id="GHSA-xxxx-yyyy-zzzz",
                    is_exploitable=True,
                    confidence="high",
                    reasoning="Test reasoning",
                    impact_assessment="Test impact",
                    code_paths_affected=["src/app.js"],
                    recommended_action="Upgrade",
                    priority="medium"
                )
            },
            {
                "name": "Docs Site - High Vuln → Should Stay High/Critical",
                "manifest_path": "docs-site/package.json",
                "report": AnalysisReport(
                    alert_number=2,
                    package="lodash",
                    vulnerability_id="GHSA-aaaa-bbbb-cccc",
                    is_exploitable=True,
                    confidence="high",
                    reasoning="Test reasoning",
                    impact_assessment="Test impact",
                    code_paths_affected=["src/utils.js"],
                    recommended_action="Upgrade",
                    priority="high"
                )
            },
            {
                "name": "Internal Admin - Low Vuln → Should Stay Low",
                "manifest_path": "internal-admin/package.json",
                "report": AnalysisReport(
                    alert_number=3,
                    package="debug",
                    vulnerability_id="GHSA-dddd-eeee-ffff",
                    is_exploitable=False,
                    confidence="medium",
                    reasoning="Test reasoning",
                    impact_assessment="Test impact",
                    code_paths_affected=["src/debug.js"],
                    recommended_action="Monitor",
                    priority="low"
                )
            },
            {
                "name": "No Config - Should Use Default Multiplier",
                "manifest_path": "unknown-service/package.json",
                "report": AnalysisReport(
                    alert_number=4,
                    package="axios",
                    vulnerability_id="GHSA-gggg-hhhh-iiii",
                    is_exploitable=True,
                    confidence="medium",
                    reasoning="Test reasoning",
                    impact_assessment="Test impact",
                    code_paths_affected=["src/api.js"],
                    recommended_action="Upgrade",
                    priority="medium"
                )
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n{'=' * 70}")
            print(f"Test Case {i}: {test_case['name']}")
            print(f"{'=' * 70}")
            
            assessment = await agent.assess(
                manifest_path=test_case['manifest_path'],
                report=test_case['report'],
                fp_check=None
            )
            
            print(f"\n📊 Results:")
            print(f"  Service Path: {assessment.service_path}")
            print(f"  Has Config: {'Yes' if assessment.service_criticality else 'No'}")
            if assessment.service_criticality:
                print(f"  Criticality Level: {assessment.service_criticality.criticality_level.value}")
                print(f"  Data Classification: {assessment.service_criticality.data_classification.value}")
                print(f"  Exposure: {assessment.service_criticality.exposure.value}")
            print(f"\n  Base Risk Score: {assessment.base_risk_score:.1f}/10")
            print(f"  Criticality Multiplier: {assessment.criticality_multiplier:.2f}x")
            print(f"  Final Risk Score: {assessment.final_risk_score:.1f}/10")
            print(f"\n  Priority: {assessment.original_priority} → {assessment.adjusted_priority}")
            print(f"  Response Time: {assessment.recommended_response_time}")
            
            if assessment.risk_factors:
                print(f"\n  Risk Factors:")
                for factor in assessment.risk_factors:
                    print(f"    • {factor}")
            
            print(f"\n  Reasoning:")
            for line in assessment.assessment_reasoning.split('\n'):
                print(f"    {line}")
        
        print(f"\n{'=' * 70}")
        print("✅ All test cases completed successfully!")
        print(f"{'=' * 70}")


if __name__ == "__main__":
    asyncio.run(test_criticality_agent())
