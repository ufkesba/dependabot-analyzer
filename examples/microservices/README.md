# Microservice Criticality Configuration Examples

This directory contains example `.criticality.yaml` configuration files for different types of microservices. Use these as templates for your own services.

## Quick Start

1. **Copy** the example that best matches your service type
2. **Customize** the values for your specific service
3. **Place** the `.criticality.yaml` file in your service directory
4. **Run** analysis with `--repo-path` to enable criticality assessment

```bash
python main.py analyze owner/repo --repo-path /path/to/repo --verbose
```

## Example Configurations

### Payment Service (Critical Priority)

**File:** `payment-service.criticality.yaml`

**Use Case:** Financial transaction processing, payment gateway integration

**Key Attributes:**
- Criticality: `critical` - Revenue-impacting, business-critical
- Data: `financial` - Handles credit cards, banking information
- Exposure: `external` - Internet-accessible API
- Compliance: PCI-DSS, SOC2, GDPR

**Risk Multiplier:** ~3.0x (highest)

**Typical Priority Adjustments:**
- Medium → Critical
- High → Critical  
- Low → Medium

---

### User API (High Priority)

**File:** `user-api.criticality.yaml`

**Use Case:** User account management, profile data, authentication

**Key Attributes:**
- Criticality: `high` - Customer-facing, identity management
- Data: `pii` - Personally identifiable information
- Exposure: `external` - Accessible with authentication
- Compliance: GDPR, CCPA, SOC2

**Risk Multiplier:** ~1.7x

**Typical Priority Adjustments:**
- Medium → High
- High → Critical
- Low → Medium

---

### Internal Admin (Medium Priority)

**File:** `internal-admin.criticality.yaml`

**Use Case:** Internal operations dashboard, admin tools

**Key Attributes:**
- Criticality: `medium` - Internal tooling, ops support
- Data: `confidential` - Business data, configurations
- Exposure: `internal` - VPN/internal network only
- Compliance: SOC2

**Risk Multiplier:** ~1.2x

**Typical Priority Adjustments:**
- High → High (unchanged, slight increase)
- Medium → Medium (unchanged)
- Low → Low (unchanged)

---

### Documentation Site (Low Priority)

**File:** `docs-site.criticality.yaml`

**Use Case:** Public documentation, help center, static content

**Key Attributes:**
- Criticality: `low` - Non-critical, read-only content
- Data: `public` - No sensitive information
- Exposure: `public` - Fully public access
- Compliance: None

**Risk Multiplier:** ~0.7-1.4x (depends on base severity)

**Typical Priority Adjustments:**
- Critical → Critical (unchanged, but lower score)
- High → High or Critical (public exposure matters)
- Medium → Medium
- Low → Low

---

## Field Reference

### Required Fields

- **service_name**: Identifier for the service (string)

### Core Attributes

- **criticality_level**: `low`, `medium`, `high`, `critical`
  - Base risk multiplier for the service
  
- **data_classification**: Type of data handled
  - `public` - Public information, no confidentiality
  - `internal` - Internal business data
  - `confidential` - Confidential business information
  - `pii` - Personally Identifiable Information
  - `phi` - Protected Health Information (HIPAA)
  - `financial` - Financial/payment data

- **exposure**: How the service is accessed
  - `internal` - VPN or internal network only
  - `external` - Internet-accessible with authentication
  - `public` - Publicly accessible without auth

- **business_impact**: Effect of service downtime
  - `minimal` - Little to no business impact
  - `moderate` - Some workflows affected
  - `significant` - Major workflows impacted
  - `critical` - Revenue loss, compliance violations

### Additional Fields

- **user_facing**: `true`/`false` - Direct user interaction
- **compliance_requirements**: List of frameworks
  - Common: `PCI-DSS`, `HIPAA`, `GDPR`, `CCPA`, `SOC2`, `ISO27001`
- **sla_tier**: Availability target (e.g., `"99.99%"`)
- **critical_dependencies**: List of services this depends on
- **description**: Human-readable explanation

## Risk Calculation

The final risk score is calculated as:

```
final_risk = base_vulnerability_risk × criticality_multiplier
```

**Base Multipliers by Criticality Level:**
- `critical`: 2.0x
- `high`: 1.5x
- `medium`: 1.0x
- `low`: 0.7x

**Additional Factors (additive):**
- PHI/Financial/PII data: +0.5x
- Public exposure: +0.5x
- External exposure: +0.3x
- Critical business impact: +0.5x
- Significant business impact: +0.3x
- User-facing: +0.2x
- Has compliance requirements: +0.2x

**Example:**
```yaml
# This configuration:
criticality_level: critical      # 2.0x base
data_classification: financial   # +0.5x
exposure: external               # +0.3x
business_impact: critical        # +0.5x
user_facing: true                # +0.2x
compliance_requirements: [PCI-DSS]  # +0.2x

# Results in: 2.0 + 0.5 + 0.3 + 0.5 + 0.2 + 0.2 = 3.7x multiplier
# (clamped to max 3.0x)
```

## Priority Mapping

| Final Risk Score | Priority |
|------------------|----------|
| ≥ 9.0 | Critical |
| ≥ 7.0 | High |
| ≥ 4.5 | Medium |
| < 4.5 | Low |

## Best Practices

### 1. Start with High-Value Services

Begin by creating configs for:
- Payment/billing systems
- Authentication services
- Services handling PII/PHI/financial data
- Public-facing APIs

### 2. Use Templates

Create organizational templates for common service patterns:
- `templates/payment-service.yaml`
- `templates/api-service.yaml`
- `templates/internal-tool.yaml`
- `templates/public-website.yaml`

### 3. Keep Configs Updated

Review and update when:
- Service role changes (becomes user-facing, handles new data types)
- New compliance requirements apply
- Business criticality changes
- Exposure level changes (new public endpoint, moved to VPN)

### 4. Document Decisions

Use the `description` field to explain:
- Why the criticality level was chosen
- What makes this service high/low priority
- Special considerations for security

### 5. Version Control

Store configs in your repository alongside code:
```
services/
├── payment-api/
│   ├── .criticality.yaml  ← Version controlled with code
│   ├── src/
│   └── package.json
```

## Troubleshooting

**Q: Configs not being loaded?**

Ensure:
1. File is named exactly `.criticality.yaml` (with leading dot)
2. File is in the same directory as the manifest (`package.json`, `requirements.txt`, etc.)
3. Running with `--repo-path` parameter pointing to repo root
4. YAML syntax is valid (use `yamllint` to check)

**Q: Multiplier seems wrong?**

Check:
- Multipliers are clamped between 0.5x and 3.0x
- Multiple factors stack additively
- Base risk score comes from vulnerability analysis first

**Q: Priority not changing?**

- For very low base scores, even high multipliers may not change priority
- For very high base scores, low multipliers may still result in high priority
- This is intentional - criticality modulates but doesn't override severe vulnerabilities

## Resources

- [Full Documentation](../../docs/CRITICALITY_AGENT.md)
- [Agent Implementation](../../src/agents/criticality_agent.py)
- [Data Models](../../src/models/criticality.py)
