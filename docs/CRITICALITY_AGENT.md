# Criticality Agent

The Criticality Agent enhances Dependabot vulnerability analysis by adjusting risk assessments based on service-specific context like data sensitivity, exposure, and business impact.

## Overview

Not all vulnerabilities are equal. A critical vulnerability in a documentation site has different real-world risk than the same vulnerability in a payment processing service. The Criticality Agent:

1. **Loads service metadata** from `.criticality.yaml` configuration files
2. **Calculates risk multipliers** based on service attributes
3. **Adjusts priority levels** to reflect actual business risk
4. **Provides context-aware recommendations** for response timeframes

## Architecture

### Workflow Integration

The Criticality Agent runs as **Phase 4** in the analysis pipeline:

```
Phase 1: Code Pattern Search
    ↓
Phase 2: Deep Analysis (with Reflection Loop)
    ↓
Phase 3: False Positive Check
    ↓
Phase 4: Criticality Assessment ← NEW
    ↓
Final Report
```

### Inputs

- **Vulnerability Analysis Report** (from Deep Analyzer)
- **False Positive Check** (if exploitable)
- **Service Criticality Config** (from `.criticality.yaml`)

### Outputs

- **Adjusted Risk Score** (1-10 scale)
- **Adjusted Priority** (critical/high/medium/low)
- **Risk Factors** (specific concerns identified)
- **Response Time Recommendation** (immediate, 24-48h, 1 week, etc.)

## Configuration

### File Location

Place `.criticality.yaml` files in service directories:

```
microservices/
├── payment-service/
│   ├── .criticality.yaml     ← Configuration here
│   ├── package.json
│   └── src/
├── docs-site/
│   ├── .criticality.yaml     ← Configuration here
│   ├── package.json
│   └── src/
└── user-api/
    ├── .criticality.yaml     ← Configuration here
    ├── package.json
    └── src/
```

The agent automatically discovers configs based on the `manifest_path` from Dependabot alerts.

### Schema

```yaml
# Required: Service identifier
service_name: "payment-service"

# Overall criticality: low, medium, high, critical
criticality_level: critical

# Data sensitivity: public, internal, confidential, pii, phi, financial
data_classification: financial

# Access level: internal, external, public
exposure: external

# Business impact: minimal, moderate, significant, critical
business_impact: critical

# User-facing service
user_facing: true

# Compliance requirements (GDPR, HIPAA, PCI-DSS, SOC2, CCPA, etc.)
compliance_requirements:
  - PCI-DSS
  - SOC2

# SLA tier (optional)
sla_tier: "99.99%"

# Critical dependencies (optional)
critical_dependencies:
  - auth-service
  - fraud-detection-service

# Description (optional)
description: "Handles payment processing and transactions"
```

### Field Descriptions

| Field | Values | Impact on Risk | Description |
|-------|--------|----------------|-------------|
| `criticality_level` | low, medium, high, critical | **Base multiplier** | Overall service criticality |
| `data_classification` | public, internal, confidential, pii, phi, financial | **+0.5 for sensitive** | Highest data sensitivity level |
| `exposure` | internal, external, public | **+0.3 to +0.5** | Attack surface and accessibility |
| `business_impact` | minimal, moderate, significant, critical | **+0.3 to +0.5** | Impact of service failure |
| `user_facing` | true/false | **+0.2** | Direct user interaction |
| `compliance_requirements` | List of frameworks | **+0.2 if any** | Regulatory obligations |
| `sla_tier` | e.g., "99.99%" | Informational | Service availability requirements |
| `critical_dependencies` | List of services | Informational | Dependency graph context |

## Risk Calculation

### Base Risk Score (1-10)

Derived from vulnerability analysis:

- **Exploitability**: Is the vulnerability actually exploitable in this codebase?
- **Original Priority**: critical=9, high=7, medium=5, low=3
- **Confidence**: Adjusts score based on analysis certainty
- **False Positive Status**: Downgraded if flagged as FP

### Criticality Multiplier (0.5 - 3.0x)

Calculated from service attributes:

```
Base Multiplier (from criticality_level):
  - low: 0.7x
  - medium: 1.0x
  - high: 1.5x
  - critical: 2.0x

Additional Factors:
  + PHI/Financial/PII data: +0.5
  + Public exposure: +0.5
  + External exposure: +0.3
  + Critical business impact: +0.5
  + Significant business impact: +0.3
  + User facing: +0.2
  + Compliance requirements: +0.2
```

### Final Risk Score

```
final_risk_score = base_risk_score × criticality_multiplier
(clamped to 1-10 range)
```

### Priority Adjustment

| Final Risk Score | Adjusted Priority |
|------------------|-------------------|
| ≥ 9.0 | Critical |
| ≥ 7.0 | High |
| ≥ 4.5 | Medium |
| < 4.5 | Low |

## Examples

### Example 1: Payment Service - Escalated Priority

**Scenario**: Medium severity vulnerability in payment processing service

```yaml
# services/payment-api/.criticality.yaml
service_name: payment-api
criticality_level: critical
data_classification: financial
exposure: external
business_impact: critical
user_facing: true
compliance_requirements: [PCI-DSS, SOC2]
```

**Calculation**:
- Base Risk: 5.0 (medium priority vulnerability)
- Multiplier: 2.0 (critical) + 0.5 (financial) + 0.3 (external) + 0.5 (critical impact) + 0.2 (user facing) + 0.2 (compliance) = 3.7x
- Final Risk: 5.0 × 3.7 = 10.0 (clamped)
- **Priority Adjusted**: medium → **critical**
- **Response Time**: Immediate (compliance-driven)

### Example 2: Documentation Site - Maintained Priority

**Scenario**: High severity vulnerability in docs site

```yaml
# docs/.criticality.yaml
service_name: docs-site
criticality_level: low
data_classification: public
exposure: public
business_impact: minimal
user_facing: true
compliance_requirements: []
```

**Calculation**:
- Base Risk: 7.0 (high priority vulnerability)
- Multiplier: 0.7 (low) + 0.5 (public) + 0.2 (user facing) = 1.4x
- Final Risk: 7.0 × 1.4 = 9.8
- **Priority**: high → **critical** (still elevated due to base score)
- **Response Time**: 24-48 hours

### Example 3: Internal Tool - Downgraded Priority

**Scenario**: High severity vulnerability in internal admin dashboard

```yaml
# internal/admin/.criticality.yaml
service_name: internal-admin
criticality_level: medium
data_classification: confidential
exposure: internal
business_impact: moderate
user_facing: false
compliance_requirements: [SOC2]
```

**Calculation**:
- Base Risk: 7.0 (high priority vulnerability)
- Multiplier: 1.0 (medium) + 0.2 (compliance) = 1.2x
- Final Risk: 7.0 × 1.2 = 8.4
- **Priority**: high → **high** (maintained)
- **Response Time**: 24-48 hours

## Usage

### Command Line

Analyze with local repository for criticality configs:

```bash
# Analyze all alerts with criticality assessment
python main.py analyze owner/repo \
  --repo-path /path/to/local/repo \
  --verbose

# Analyze specific alert
python main.py analyze-alert owner/repo 42 \
  --repo-path /path/to/local/repo \
  --verbose
```

### Programmatic

```python
from src.orchestrator import DependabotAnalyzer

analyzer = DependabotAnalyzer(
    repo="owner/repo",
    github_token="ghp_...",
    repo_path="/path/to/local/repo",  # Enable criticality assessment
    verbose=True
)

await analyzer.run()

# Access criticality assessment from state
for state in analyzer.analysis_states:
    if state.criticality_assessment:
        print(f"Service: {state.criticality_assessment.service_path}")
        print(f"Final Risk: {state.criticality_assessment.final_risk_score}/10")
        print(f"Priority: {state.criticality_assessment.adjusted_priority}")
```

## Monorepo Support

The Criticality Agent integrates seamlessly with the existing monorepo detection:

- Alerts for `services/payment-api/package.json` → loads `services/payment-api/.criticality.yaml`
- Alerts for root `package.json` → loads `./.criticality.yaml`
- Missing config → no adjustment (multiplier = 1.0x)

## Best Practices

### Configuration Strategy

1. **Start with critical services**: Focus on payment, auth, PII-handling services first
2. **Template consistency**: Use templates for similar service types
3. **Regular reviews**: Update configs when service roles change
4. **Document rationale**: Use `description` field to explain criticality decisions

### Priority Calibration

- **Critical**: Revenue-impacting, handles financial/PHI data, public-facing
- **High**: Customer-facing, PII data, external exposure
- **Medium**: Internal tools, confidential data, internal-only
- **Low**: Dev tools, docs, no sensitive data

### Compliance Mapping

Common compliance requirements by service type:

- **Payment**: PCI-DSS, SOC2, regional (GDPR, CCPA)
- **Healthcare**: HIPAA, HITECH, SOC2
- **User data**: GDPR, CCPA, PIPEDA
- **General**: SOC2, ISO 27001

## Limitations

- **No config = no adjustment**: Services without `.criticality.yaml` use default multiplier (1.0x)
- **Manual configuration**: Configs must be created and maintained manually
- **No cross-service analysis**: Doesn't automatically infer criticality from dependency graphs
- **Static assessment**: Doesn't consider runtime context or traffic patterns

## Future Enhancements

Potential improvements:

1. **Auto-discovery**: Infer criticality from codebase patterns, API routes, data models
2. **Dependency analysis**: Factor in criticality of downstream services
3. **Historical context**: Learn from past incidents and vulnerability responses
4. **Dynamic weighting**: Adjust multipliers based on actual usage patterns
5. **Team routing**: Automatically assign alerts to appropriate teams based on criticality
