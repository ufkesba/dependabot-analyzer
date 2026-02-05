# Criticality Agent Design Rationale

This document addresses the design decisions made for the criticality-based service prioritization agent.

## Problem Statement

> I am thinking about adding an agent that makes a determination based on the criticality of a given service. I want to have this analyze a repository with a structure that has a microservice directory with each under it like:
> 
> Microservice/<1>
> Microservice/<2>
> ...
> 
> I feel like each one I should add a yaml file that has info about its criticality. Like if it's just a documentation sites service, it'd probably lower priority than something that would process financial data or health data, or if it's externally facing then it's higher priority.

## Design Decisions

### 1. What to Track for Each Service

After analyzing the problem, we identified these key dimensions of service criticality:

#### Core Attributes (Required)

**`criticality_level`** (low/medium/high/critical)
- *Why*: Provides a simple, high-level classification that teams already understand
- *Impact*: Base multiplier for risk calculation (0.7x - 2.0x)

**`data_classification`** (public/internal/confidential/pii/phi/financial)
- *Why*: Data sensitivity is a primary risk factor in security vulnerabilities
- *Example*: Financial data breach has higher impact than public data leak
- *Impact*: +0.5x multiplier for sensitive data types

**`exposure`** (internal/external/public)
- *Why*: Attack surface directly correlates with exploitation likelihood
- *Example*: Public API vs VPN-only service
- *Impact*: +0.3x to +0.5x based on accessibility

**`business_impact`** (minimal/moderate/significant/critical)
- *Why*: Captures operational and revenue impact of service failure
- *Example*: Payment processing down vs docs site down
- *Impact*: +0.3x to +0.5x based on severity

#### Supporting Attributes

**`user_facing`** (boolean)
- *Why*: Direct user interaction means higher visibility and customer impact
- *Impact*: +0.2x multiplier

**`compliance_requirements`** (list)
- *Why*: Regulatory obligations (PCI-DSS, HIPAA, GDPR) mandate faster response
- *Impact*: +0.2x multiplier + accelerated response times

**`sla_tier`** (string)
- *Why*: Availability commitments indicate service importance
- *Impact*: Informational (used in reasoning)

**`critical_dependencies`** (list)
- *Why*: Documents impact radius and dependency chains
- *Impact*: Informational (potential future use in graph analysis)

### 2. Where the Agent Sits in the Flow

**Decision: After False Positive Check (Phase 4)**

```
Phase 1: Code Pattern Search
    ↓
Phase 2: Deep Analysis (with Reflection)
    ↓
Phase 3: False Positive Check
    ↓
Phase 4: Criticality Assessment ← NEW
    ↓
Final Report
```

#### Why This Placement?

**✅ Advantages:**
1. **Acts on validated findings**: Only adjusts priorities after confirming exploitability
2. **Context-rich input**: Has full vulnerability analysis to inform decisions
3. **Clean separation**: Security analysis remains objective; criticality adds business context
4. **Optional enhancement**: Can be disabled without breaking core analysis
5. **Final prioritization**: Last chance to adjust before presenting to users

**❌ Considered Alternatives:**

**Parallel to Deep Analysis:**
- Con: Would need to run on all alerts, even non-exploitable ones
- Con: Might influence security analysis (should be objective)

**Before Deep Analysis:**
- Con: Could bias the security assessment
- Con: Wasted effort on vulnerabilities that turn out to be false positives

**Replace Reflection Agent:**
- Con: Reflection focuses on analysis quality, criticality on business context
- Con: Two different concerns that shouldn't be conflated

### 3. Risk Calculation Formula

**Formula:**
```
final_risk_score = base_vulnerability_risk × criticality_multiplier
adjusted_priority = map_score_to_priority(final_risk_score)
```

**Base Vulnerability Risk (1-10):**
- Derived from: exploitability, original priority, confidence, FP status
- Example: High priority + exploitable + high confidence = 7.0

**Criticality Multiplier (0.5 - 3.0):**
- Start with base from criticality_level
- Add factors for sensitive data, exposure, impact, etc.
- Clamp to reasonable range to prevent extreme values

**Why This Approach:**
1. **Multiplicative, not additive**: Severity and criticality compound
2. **Bounded**: Prevents unreasonable scores (no 50x multipliers)
3. **Transparent**: Easy to explain and debug
4. **Tunable**: Can adjust factor weights based on organizational needs

### 4. Configuration File Structure

**Decision: `.criticality.yaml` in service directories**

```
microservices/
├── payment-service/
│   ├── .criticality.yaml  ← Config here
│   ├── package.json
│   └── src/
```

#### Why This Structure?

**✅ Advantages:**
1. **Co-located with code**: Lives alongside the service it describes
2. **Version controlled**: Changes tracked with code changes
3. **Discoverable**: Analyzer finds it automatically via manifest path
4. **Standard naming**: `.criticality.yaml` is clear and consistent
5. **Monorepo friendly**: Works with existing monorepo detection

**❌ Considered Alternatives:**

**Central configuration file:**
- Con: Doesn't scale well to large monorepos
- Con: Requires separate maintenance from code
- Con: Harder to discover which services have configs

**Database-backed:**
- Con: Adds external dependency
- Con: Harder for developers to update
- Con: Not version controlled

**Infer from code:**
- Con: Too unreliable (false positives/negatives)
- Con: Can't capture human judgment on business impact
- Con: Requires complex ML/heuristics

### 5. Graceful Degradation

**Decision: Missing configs don't break analysis**

If `.criticality.yaml` is not found:
- Multiplier = 1.0 (no adjustment)
- Analysis continues normally
- Warning logged but not surfaced as error

#### Why?

1. **Gradual adoption**: Can add configs service-by-service
2. **Backward compatible**: Works on repos without any configs
3. **No false sense of security**: Better than guessing criticality

### 6. Monorepo Integration

**Decision: Leverage existing manifest path scoping**

The existing monorepo support already scopes searches to service directories:
- Alert for `services/payment/package.json` → searches `services/payment/`
- Criticality agent uses the same path to find `services/payment/.criticality.yaml`

#### Why?

1. **Consistency**: Matches existing code analyzer behavior
2. **Zero additional work**: Monorepo detection already implemented
3. **Correct by construction**: Can't accidentally load wrong config

## Real-World Examples

### Example 1: Payment Service Escalation

**Scenario**: Medium severity XSS in payment processing service

```yaml
criticality_level: critical
data_classification: financial
exposure: external
business_impact: critical
compliance_requirements: [PCI-DSS]
```

**Result**: Medium → Critical (3.0x multiplier, 10.0 final score)

**Reasoning**: Even "medium" vulnerabilities in payment systems deserve immediate attention due to:
- Financial data exposure risk
- PCI-DSS compliance requirements
- Revenue impact
- Customer trust

### Example 2: Docs Site Maintained Priority

**Scenario**: High severity RCE in documentation site

```yaml
criticality_level: low
data_classification: public
exposure: public
business_impact: minimal
```

**Result**: High → Critical (1.4x multiplier, 9.8 final score)

**Reasoning**: While docs are low-criticality, RCE is still RCE. The vulnerability severity dominates, but response time might be more relaxed.

### Example 3: Internal Tool Appropriate Priority

**Scenario**: Low severity dependency in internal admin tool

```yaml
criticality_level: medium
data_classification: confidential
exposure: internal
business_impact: moderate
```

**Result**: Low → Low (1.2x multiplier, 2.4 final score)

**Reasoning**: Low severity vuln in internal tool stays low priority. Limited exposure and moderate impact don't warrant escalation.

## Comparison to Alternatives

### Manual Prioritization
- **Pro**: Human judgment, full context
- **Con**: Doesn't scale, inconsistent, slow
- **Verdict**: Criticality agent automates what teams already do manually

### CVSS Score Only
- **Pro**: Standardized, widely understood
- **Con**: No business context, too generic
- **Verdict**: Criticality agent adds the missing business dimension

### Static Rules Engine
- **Pro**: Simple, deterministic
- **Con**: Brittle, hard to maintain rules
- **Verdict**: Criticality agent is more flexible with configs

### ML-Based Classification
- **Pro**: Could learn from patterns
- **Con**: Requires training data, explainability issues, overengineered
- **Verdict**: Simple multipliers are more transparent and sufficient

## Future Enhancements

### Phase 2 Possibilities

1. **Auto-discovery**: Infer criticality from code patterns (API endpoints, DB models)
2. **Dependency graph analysis**: Factor in critical dependencies automatically
3. **Historical learning**: Adjust based on past incident response patterns
4. **Team routing**: Auto-assign alerts to teams based on service ownership
5. **Dynamic weighting**: Adjust multipliers based on traffic patterns, revenue contribution

### Why Not Now?

- **YAGNI**: Start simple, add complexity only when proven necessary
- **Validation**: Need to see how teams use basic version first
- **Data requirements**: ML features need training data we don't have yet

## Conclusion

The Criticality Agent fills a critical gap in vulnerability prioritization by adding business context to technical severity assessments. The design prioritizes:

1. **Simplicity**: YAML configs, multiplicative scoring
2. **Transparency**: Clear formula, explainable decisions
3. **Flexibility**: Works with or without configs
4. **Integration**: Fits naturally into existing workflow

This approach balances sophistication with maintainability, providing immediate value while leaving room for future enhancements.
