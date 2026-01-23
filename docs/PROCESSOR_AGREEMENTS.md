# CSU Tracker - Third-Party Processor Agreements

**Document Version:** 1.0  
**Effective Date:** January 22, 2026  
**Last Review:** January 22, 2026  
**Next Review:** January 22, 2027  
**Document Owner:** Data Protection Officer  
**Classification:** Internal - Confidential

---

## 1. INTRODUCTION

### 1.1 Purpose

This document outlines the third-party data processors used by CSU Tracker, the data shared with each processor, and the contractual safeguards in place to ensure GDPR compliance.

### 1.2 Legal Basis

Under GDPR Article 28, when using data processors, the controller must:

1. Use only processors providing sufficient guarantees
2. Have a written contract in place
3. Ensure the contract includes mandatory provisions
4. Conduct due diligence on processors

---

## 2. PROCESSOR REGISTER

### 2.1 Summary of Processors

| Processor | Service | Data Shared | Location | Adequacy |
|-----------|---------|-------------|----------|----------|
| PythonAnywhere Ltd | Web Hosting | All application data (encrypted) | UK/EU | UK GDPR applies |
| Stripe Inc | Payment Processing | Email, subscription data | USA | EU-US DPF + SCCs |
| Redis Labs | Caching | Session tokens only | EU | UK GDPR applies |
| Email Provider | Transactional Email | Email addresses | [TBD] | [TBD] |

---

## 3. PROCESSOR DETAILS

### 3.1 PythonAnywhere Ltd (Web Hosting)

#### Overview

| Field | Details |
|-------|---------|
| **Company** | PythonAnywhere LLP |
| **Service** | Web application hosting, database hosting |
| **Website** | https://www.pythonanywhere.com |
| **Headquarters** | United Kingdom |
| **Data Location** | EU/UK data centres |

#### Data Processed

| Data Category | Purpose | Encrypted |
|---------------|---------|-----------|
| All user data | Application hosting | Yes (sensitive fields) |
| Database contents | Storage | Yes (at rest and in transit) |
| Logs | Debugging, security | IP addresses only |

#### Security Measures

- ✅ Data centre security (ISO 27001)
- ✅ Encrypted connections (HTTPS/TLS)
- ✅ Regular security updates
- ✅ Access controls and authentication
- ✅ Backup and disaster recovery

#### Contractual Status

| Requirement | Status | Document |
|-------------|--------|----------|
| Data Processing Agreement | ✅ | Standard ToS includes DPA |
| GDPR Article 28 provisions | ✅ | Included in DPA |
| Sub-processor list | ✅ | Available on request |
| Security attestations | ✅ | Available on request |

#### Due Diligence

- [x] Review of security practices
- [x] Review of Terms of Service
- [x] Confirmation of UK/EU data storage
- [x] Verification of GDPR compliance statement

#### Actions Required

- [ ] Request formal Data Processing Agreement if not already signed
- [ ] Annual review of security attestations

---

### 3.2 Stripe Inc (Payment Processing)

#### Overview

| Field | Details |
|-------|---------|
| **Company** | Stripe, Inc |
| **Service** | Payment processing for subscriptions |
| **Website** | https://stripe.com |
| **Headquarters** | San Francisco, USA |
| **EU Entity** | Stripe Payments Europe, Ltd (Ireland) |

#### Data Processed

| Data Category | Purpose | Notes |
|---------------|---------|-------|
| Email address | Customer identification | Required for Stripe customer |
| Subscription status | Billing management | Synced via webhooks |
| Payment methods | Process payments | Stored by Stripe only |

**Note:** CSU Tracker does NOT store payment card details. All payment data is processed directly by Stripe.

#### Security Measures

- ✅ PCI-DSS Level 1 certified
- ✅ SOC 1 and SOC 2 certified
- ✅ Encryption at rest and in transit
- ✅ Strong authentication
- ✅ Fraud detection

#### International Transfer Safeguards

| Mechanism | Status | Details |
|-----------|--------|---------|
| EU-US Data Privacy Framework | ✅ | Stripe is certified |
| Standard Contractual Clauses | ✅ | Included in DPA |
| EU Representative | ✅ | Stripe Payments Europe, Ltd |

#### Contractual Status

| Requirement | Status | Document |
|-------------|--------|----------|
| Data Processing Agreement | ✅ | [Stripe DPA](https://stripe.com/legal/dpa) |
| GDPR Article 28 provisions | ✅ | Included in DPA |
| SCCs for transfers | ✅ | Included in DPA |
| Sub-processor list | ✅ | [Stripe Sub-processors](https://stripe.com/legal/service-providers) |

#### Due Diligence

- [x] Review of Stripe DPA
- [x] Verification of PCI-DSS compliance
- [x] Review of EU-US DPF certification
- [x] Review of security documentation

#### Actions Required

- [ ] Annual review of Stripe compliance certifications
- [ ] Monitor EU-US DPF status for any changes

---

### 3.3 Redis Labs (Caching Service)

#### Overview

| Field | Details |
|-------|---------|
| **Company** | Redis Ltd |
| **Service** | In-memory caching (Redis Cloud) |
| **Website** | https://redis.io |
| **Data Location** | EU (configurable) |

#### Data Processed

| Data Category | Purpose | Retention |
|---------------|---------|-----------|
| Session tokens | User session management | Session duration |
| Rate limit counters | Security rate limiting | Minutes to hours |
| Cache keys | Performance optimisation | Short-term |

**Note:** NO personal data or health data is cached. Only ephemeral operational data.

#### Security Measures

- ✅ Encryption in transit (TLS)
- ✅ Access authentication
- ✅ Network isolation
- ✅ SOC 2 Type II certified

#### Contractual Status

| Requirement | Status | Document |
|-------------|--------|----------|
| Data Processing Agreement | ✅ | Standard Cloud DPA |
| GDPR Article 28 provisions | ✅ | Included in DPA |
| Data location guarantee | ✅ | EU region selected |

#### Due Diligence

- [x] Review of service terms
- [x] Confirmation of EU data location
- [x] Review of security documentation

#### Actions Required

- [ ] Ensure EU region is configured
- [ ] Annual review of compliance status

---

### 3.4 Email Service Provider

#### Overview

| Field | Details |
|-------|---------|
| **Company** | [Insert Provider - e.g., SendGrid, Mailgun, AWS SES] |
| **Service** | Transactional email delivery |
| **Data Location** | [TBD - ensure EU/UK or adequate safeguards] |

#### Data Processed

| Data Category | Purpose | Retention |
|---------------|---------|-----------|
| Email addresses | Email delivery | As per provider policy |
| Email content | Password reset, notifications | Transient |

**Note:** Email content does NOT contain health data. Only:
- Password reset links
- Account notifications
- Reminder prompts (no health details)

#### Security Measures Required

- ✅ TLS encryption for email transmission
- ✅ DKIM/SPF/DMARC configured
- ✅ Access controls
- ✅ Data processing agreement

#### Contractual Status

| Requirement | Status | Document |
|-------------|--------|----------|
| Data Processing Agreement | ⚠️ TBD | [Pending provider selection] |
| GDPR Article 28 provisions | ⚠️ TBD | [Pending review] |
| International transfer safeguards | ⚠️ TBD | [If non-EU provider] |

#### Actions Required

- [ ] **Confirm email provider selection**
- [ ] **Sign Data Processing Agreement**
- [ ] **Review and document security measures**
- [ ] **If US provider: verify EU-US DPF or SCCs**

---

## 4. ARTICLE 28 COMPLIANCE CHECKLIST

For each processor, the following Article 28 requirements must be satisfied:

### 4.1 Required Contract Provisions

| Provision | PythonAnywhere | Stripe | Redis | Email |
|-----------|----------------|--------|-------|-------|
| Subject matter and duration | ✅ | ✅ | ✅ | ⚠️ |
| Nature and purpose | ✅ | ✅ | ✅ | ⚠️ |
| Type of personal data | ✅ | ✅ | ✅ | ⚠️ |
| Categories of data subjects | ✅ | ✅ | ✅ | ⚠️ |
| Controller obligations and rights | ✅ | ✅ | ✅ | ⚠️ |
| Process only on instructions | ✅ | ✅ | ✅ | ⚠️ |
| Confidentiality obligations | ✅ | ✅ | ✅ | ⚠️ |
| Security measures | ✅ | ✅ | ✅ | ⚠️ |
| Sub-processor rules | ✅ | ✅ | ✅ | ⚠️ |
| Assist with data subject rights | ✅ | ✅ | ✅ | ⚠️ |
| Assist with DPIA | ✅ | ✅ | ✅ | ⚠️ |
| Delete/return data | ✅ | ✅ | ✅ | ⚠️ |
| Audit rights | ✅ | ✅ | ✅ | ⚠️ |

### 4.2 International Transfer Assessment

| Processor | Location | Adequacy Decision | Transfer Mechanism |
|-----------|----------|-------------------|-------------------|
| PythonAnywhere | UK | N/A (domestic) | None required |
| Stripe | USA | No (USA) | EU-US DPF + SCCs |
| Redis | EU | N/A (EEA) | None required |
| Email Provider | TBD | TBD | TBD |

---

## 5. SUB-PROCESSOR MANAGEMENT

### 5.1 Sub-Processor Approval Process

1. Processor notifies CSU Tracker of new sub-processor
2. DPO reviews sub-processor details
3. DPO assesses data protection implications
4. Approval or objection within 30 days
5. Documentation updated

### 5.2 Sub-Processor Notification

| Processor | Notification Method | Our Right to Object |
|-----------|---------------------|---------------------|
| PythonAnywhere | Updated list on website | Standard terms |
| Stripe | Email notification | 30-day objection period |
| Redis | Updated list on website | Standard terms |

### 5.3 Key Sub-Processors

#### Stripe Sub-Processors (Critical)

| Sub-Processor | Service | Location |
|---------------|---------|----------|
| Amazon Web Services | Cloud infrastructure | Global (EU available) |
| Google Cloud Platform | Cloud infrastructure | Global (EU available) |
| Various payment networks | Payment processing | Global |

Full list: https://stripe.com/legal/service-providers

---

## 6. PROCESSOR DUE DILIGENCE

### 6.1 Initial Due Diligence Checklist

Before engaging any new processor:

```
□ Review privacy policy and terms of service
□ Obtain and review Data Processing Agreement
□ Verify GDPR compliance statement
□ Check for relevant certifications (ISO 27001, SOC 2)
□ Confirm data location and any international transfers
□ Review security measures and documentation
□ Assess sub-processor management
□ Verify breach notification procedures
□ Check data retention and deletion capabilities
□ DPO approval
```

### 6.2 Annual Review Checklist

For each existing processor:

```
□ Verify DPA is still current
□ Check for any changes to terms
□ Review any new sub-processors
□ Verify continued certification status
□ Review any security incidents
□ Assess ongoing necessity of processing
□ Update internal documentation
□ DPO sign-off
```

---

## 7. PROCESSOR INCIDENT MANAGEMENT

### 7.1 Breach Notification Requirements

Each processor is required to notify us of breaches:

| Processor | Notification Time | Contact Method |
|-----------|-------------------|----------------|
| PythonAnywhere | Without undue delay | Email to account holder |
| Stripe | 72 hours | Email notification |
| Redis | Without undue delay | Email notification |

### 7.2 Our Response Process

1. Receive breach notification from processor
2. Assess impact on our data subjects
3. Determine if ICO notification required
4. Determine if user notification required
5. Coordinate response with processor
6. Document incident

---

## 8. DATA SUBJECT RIGHTS

### 8.1 Processor Assistance Obligations

Each processor must assist with:

| Right | PythonAnywhere | Stripe | Redis |
|-------|----------------|--------|-------|
| Access | ✅ On request | ✅ Via API | N/A (no PII) |
| Deletion | ✅ On request | ✅ Via API | ✅ Automatic expiry |
| Portability | ✅ Data export | ✅ Via API | N/A |
| Rectification | ✅ On request | ✅ Via API | N/A |

---

## 9. REVIEW AND AUDIT

### 9.1 Review Schedule

| Processor | Review Frequency | Next Review |
|-----------|------------------|-------------|
| PythonAnywhere | Annual | January 2027 |
| Stripe | Annual | January 2027 |
| Redis | Annual | January 2027 |
| Email Provider | Annual | [After selection] |

### 9.2 Audit Rights

We reserve the right to:

- Request security documentation
- Request compliance certifications
- Conduct audits (or appoint auditors)
- Receive breach notifications
- Terminate for compliance failures

---

## 10. ACTIONS AND FOLLOW-UP

### 10.1 Immediate Actions Required

| Priority | Action | Owner | Due Date |
|----------|--------|-------|----------|
| HIGH | Confirm email provider and sign DPA | DPO | [30 days] |
| MEDIUM | Request formal DPA from PythonAnywhere | DPO | [60 days] |
| LOW | Set up annual review calendar | DPO | [30 days] |

### 10.2 Annual Actions

| Month | Action |
|-------|--------|
| January | Annual processor review |
| January | Update this document |
| Ongoing | Monitor processor communications |
| As needed | Review sub-processor changes |

---

## 11. DOCUMENT CONTROL

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 22/01/2026 | DPO | Initial document |

---

## 12. APPENDICES

### Appendix A: Data Processing Agreement Template

For any new processors without their own DPA, use the ICO template:
https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/accountability-and-governance/contracts-between-controllers-and-processors/

### Appendix B: Processor Contact Register

| Processor | Primary Contact | Email | Phone |
|-----------|-----------------|-------|-------|
| PythonAnywhere | Support | support@pythonanywhere.com | N/A |
| Stripe | Support | support@stripe.com | N/A |
| Redis | Support | support@redis.io | N/A |
| Email Provider | TBD | TBD | TBD |

### Appendix C: Reference Documents

- Stripe DPA: https://stripe.com/legal/dpa
- Stripe Sub-processors: https://stripe.com/legal/service-providers
- PythonAnywhere Terms: https://www.pythonanywhere.com/terms/
- Redis Cloud Terms: https://redis.io/legal/cloud-tos/

---

**END OF DOCUMENT**
