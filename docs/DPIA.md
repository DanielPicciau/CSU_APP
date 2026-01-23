# Data Protection Impact Assessment (DPIA)
## CSU Tracker - Health Symptom Tracking Application

**Document Version:** 1.0  
**Assessment Date:** January 22, 2026  
**Assessor:** Data Protection Officer  
**Next Review Date:** January 22, 2027  
**Status:** APPROVED

---

## 1. EXECUTIVE SUMMARY

### 1.1 Project Overview

CSU Tracker is a web-based Progressive Web Application (PWA) designed to help individuals with Chronic Spontaneous Urticaria (CSU) track their daily symptoms using the standardised UAS7 (Urticaria Activity Score 7) system.

### 1.2 DPIA Requirement

This DPIA is **mandatory** under GDPR Article 35 because the processing:

- Involves **special category data** (health data) on a large scale
- Uses **systematic monitoring** of individuals (daily symptom tracking)
- Involves **vulnerable data subjects** (individuals with chronic health conditions)

### 1.3 Summary of Findings

| Risk Area | Inherent Risk | Residual Risk | Status |
|-----------|---------------|---------------|--------|
| Data collection | Medium | Low | ✅ Mitigated |
| Data storage | High | Low | ✅ Mitigated |
| Data access | High | Low | ✅ Mitigated |
| Data sharing | Medium | Low | ✅ Mitigated |
| Data retention | Medium | Low | ✅ Mitigated |
| Individual rights | Medium | Low | ✅ Mitigated |
| Security breach | High | Medium | ✅ Acceptable |

### 1.4 Approval

| Role | Name | Signature | Date |
|------|------|-----------|------|
| DPO | [Name] | _____________ | ___/___/2026 |
| Controller | [Name] | _____________ | ___/___/2026 |

---

## 2. PROCESSING DESCRIPTION

### 2.1 Nature of Processing

| Aspect | Description |
|--------|-------------|
| **Purpose** | Enable individuals to track CSU symptoms and generate reports for personal use and healthcare provider consultations |
| **Legal basis** | Explicit consent (GDPR Article 9(2)(a)) for health data; Contract (Article 6(1)(b)) for service provision |
| **Processing operations** | Collection, recording, storage, retrieval, use, erasure |
| **Data sources** | Direct input from data subjects only |
| **Recipients** | Data subject only (unless explicitly shared) |

### 2.2 Scope of Processing

| Element | Details |
|---------|---------|
| **Data subjects** | Individuals with CSU (adults, potentially including vulnerable persons) |
| **Geographic scope** | United Kingdom (primary), EU/EEA, global |
| **Volume** | Estimated 1,000 - 50,000 users |
| **Frequency** | Daily data entry encouraged |
| **Duration** | Indefinite until user deletion |

### 2.3 Data Categories Processed

#### 2.3.1 Standard Personal Data

| Category | Data Elements | Purpose | Retention |
|----------|--------------|---------|-----------|
| Account data | Email address | Authentication, communication | Until account deletion |
| Identity data | First name, last name | Personalisation (optional) | Until account deletion |
| Profile data | Date of birth, age, gender | Context for health tracking | Until account deletion |
| Preference data | Timezone, display preferences | User experience | Until account deletion |

#### 2.3.2 Special Category Data (Health Data)

| Category | Data Elements | Purpose | Retention |
|----------|--------------|---------|-----------|
| Symptom scores | UAS7 scores (0-42), itch severity, hive count | Primary tracking function | Until account deletion |
| Quality of life | Sleep impact, daily activities impact, mood | Holistic health view | Until account deletion |
| Medical context | CSU diagnosis status | Contextual understanding | Until account deletion |
| Medication data | Medication names, types, dosages, frequencies | Correlation analysis | Until account deletion |
| Personal notes | Free-text health observations | Personal record keeping | Until account deletion |

### 2.4 Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         DATA SUBJECT                             │
│                    (CSU Patient / User)                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ (1) Registration & consent
                              │ (2) Daily symptom entry
                              │ (3) Profile updates
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      CSU TRACKER APPLICATION                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Web UI    │  │   REST API  │  │   Background Tasks      │  │
│  │  (Django)   │  │   (DRF)     │  │   (Celery)              │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    SECURITY LAYER                            ││
│  │  • Fernet encryption (AES-128) for sensitive fields          ││
│  │  • Argon2id password hashing                                 ││
│  │  • TOTP-based MFA                                            ││
│  │  • Rate limiting                                             ││
│  │  • Audit logging                                             ││
│  └─────────────────────────────────────────────────────────────┘│
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    DATABASE (PostgreSQL)                     ││
│  │  • Encrypted fields: name, DOB, gender, diagnosis, notes     ││
│  │  • Standard fields: email, scores, timestamps                ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ (4) Optional exports
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     DATA SUBJECT OUTPUTS                         │
│  • CSV/PDF exports for personal use                              │
│  • Reports for healthcare providers                              │
└─────────────────────────────────────────────────────────────────┘
```

### 2.5 Third-Party Processors

| Processor | Service | Data Shared | Location | Safeguards |
|-----------|---------|-------------|----------|------------|
| PythonAnywhere Ltd | Web hosting | All data (encrypted) | UK/EU | Standard DPA |
| Stripe Inc | Payment processing | Email, subscription status | US (EU-US DPF) | SCCs + DPF |
| Redis Labs | Caching | Session tokens only | EU | Standard DPA |

---

## 3. NECESSITY AND PROPORTIONALITY

### 3.1 Lawful Basis Assessment

#### For Standard Personal Data (Article 6)

| Basis | Applicable | Justification |
|-------|------------|---------------|
| **Consent (a)** | ✅ | Optional features (analytics) |
| **Contract (b)** | ✅ | Core service delivery |
| Legitimate interest (f) | ❌ | Not relied upon |

#### For Special Category Data (Article 9)

| Basis | Applicable | Justification |
|-------|------------|---------------|
| **Explicit consent (a)** | ✅ | Primary basis for health data |
| Health/social care (h) | ❌ | Not a healthcare provider |

### 3.2 Necessity Analysis

| Data Element | Necessary? | Justification |
|--------------|------------|---------------|
| Email | ✅ Yes | Authentication, password recovery |
| Name | ⚠️ Optional | Personalisation only |
| DOB/Age | ⚠️ Optional | Contextual health data |
| Gender | ⚠️ Optional | Contextual health data |
| Symptom scores | ✅ Yes | Core purpose of application |
| QoL data | ⚠️ Optional | Enhanced tracking |
| Medications | ⚠️ Optional | Correlation analysis |
| Notes | ⚠️ Optional | Personal observations |

**Conclusion:** Only email and symptom scores are strictly necessary. All other data is optional and clearly marked as such in the user interface.

### 3.3 Proportionality Analysis

| Principle | Assessment | Score |
|-----------|------------|-------|
| **Adequacy** | Data collected is sufficient for the stated purpose | ✅ |
| **Relevance** | All data elements relate to symptom tracking | ✅ |
| **Limitation** | Optional fields clearly marked; minimal required data | ✅ |
| **Accuracy** | Users can edit all their data | ✅ |
| **Storage limitation** | Clear retention policy; deletion available | ✅ |

### 3.4 Data Subject Rights Implementation

| Right | Implemented | Mechanism |
|-------|-------------|-----------|
| Right to be informed | ✅ | Privacy policy, onboarding |
| Right of access | ✅ | Data export (CSV/PDF) |
| Right to rectification | ✅ | Profile editing, entry editing |
| Right to erasure | ✅ | Account deletion feature |
| Right to restrict | ✅ | Account pause feature |
| Right to portability | ✅ | CSV export |
| Right to object | ✅ | Analytics opt-out |
| Rights re: automated decisions | N/A | No automated decision-making |

---

## 4. RISK IDENTIFICATION AND ASSESSMENT

### 4.1 Risk Assessment Methodology

**Likelihood Scale:**
- 1 = Rare (less than 1% chance)
- 2 = Unlikely (1-10% chance)
- 3 = Possible (10-50% chance)
- 4 = Likely (50-90% chance)
- 5 = Almost Certain (>90% chance)

**Impact Scale:**
- 1 = Negligible (minor inconvenience)
- 2 = Minor (some distress, easily remedied)
- 3 = Moderate (significant distress or harm)
- 4 = Major (serious harm, difficult to remedy)
- 5 = Severe (catastrophic, irreversible harm)

**Risk Rating:** Likelihood × Impact

| Rating | Level | Action Required |
|--------|-------|-----------------|
| 1-4 | Low | Accept with monitoring |
| 5-9 | Medium | Implement controls |
| 10-15 | High | Prioritise mitigation |
| 16-25 | Critical | Immediate action |

### 4.2 Risk Register

#### Risk 1: Unauthorised Access to Health Data

| Attribute | Assessment |
|-----------|------------|
| **Description** | Attackers gain access to user health data |
| **Source** | External attackers, insider threats |
| **Impact** | Disclosure of sensitive health information, psychological distress, potential discrimination |
| **Likelihood (inherent)** | 3 (Possible) |
| **Impact** | 5 (Severe) |
| **Inherent Risk** | 15 (High) |

**Controls:**
- ✅ Fernet encryption at rest for sensitive fields
- ✅ Argon2id password hashing
- ✅ MFA available (mandatory for admin)
- ✅ Rate limiting on authentication
- ✅ Account lockout after failed attempts
- ✅ Session rotation and invalidation
- ✅ HTTPS enforcement with HSTS
- ✅ Security headers (CSP, X-Frame-Options, etc.)

**Residual Risk:** Likelihood 1 × Impact 5 = **5 (Medium) ✅ Acceptable**

---

#### Risk 2: Data Breach via Application Vulnerability

| Attribute | Assessment |
|-----------|------------|
| **Description** | Security vulnerability exploited to extract data |
| **Source** | SQL injection, XSS, CSRF, other OWASP Top 10 |
| **Impact** | Mass data exposure |
| **Likelihood (inherent)** | 3 (Possible) |
| **Impact** | 5 (Severe) |
| **Inherent Risk** | 15 (High) |

**Controls:**
- ✅ Django ORM (parameterised queries)
- ✅ CSRF protection on all forms
- ✅ Content Security Policy
- ✅ Input validation and sanitisation
- ✅ XSS prevention (dangerous pattern blocking)
- ✅ Path traversal prevention
- ✅ Request size limits
- ✅ Dependency security scanning

**Residual Risk:** Likelihood 1 × Impact 5 = **5 (Medium) ✅ Acceptable**

---

#### Risk 3: Insider Threat (Admin Access)

| Attribute | Assessment |
|-----------|------------|
| **Description** | Authorised staff access and misuse health data |
| **Source** | Admin users, developers |
| **Impact** | Breach of trust, legal liability |
| **Likelihood (inherent)** | 2 (Unlikely) |
| **Impact** | 5 (Severe) |
| **Inherent Risk** | 10 (High) |

**Controls:**
- ✅ Admin interface blocks all health data viewing
- ✅ MFA mandatory for all admin users
- ✅ Comprehensive audit logging
- ✅ Principle of least privilege
- ✅ Session invalidation on privilege changes
- ✅ Database encryption prevents direct data access

**Residual Risk:** Likelihood 1 × Impact 4 = **4 (Low) ✅ Acceptable**

---

#### Risk 4: Accidental Data Loss

| Attribute | Assessment |
|-----------|------------|
| **Description** | User data accidentally deleted or corrupted |
| **Source** | System failures, human error |
| **Impact** | Loss of health tracking history |
| **Likelihood (inherent)** | 2 (Unlikely) |
| **Impact** | 3 (Moderate) |
| **Inherent Risk** | 6 (Medium) |

**Controls:**
- ✅ Automated encrypted backups (premium feature)
- ✅ 30-day deletion grace period
- ✅ Database replication (hosting provider)
- ✅ User can export data at any time

**Residual Risk:** Likelihood 1 × Impact 2 = **2 (Low) ✅ Acceptable**

---

#### Risk 5: Third-Party Data Breach

| Attribute | Assessment |
|-----------|------------|
| **Description** | Hosting provider or sub-processor compromised |
| **Source** | Third-party security failure |
| **Impact** | Encrypted data potentially exposed |
| **Likelihood (inherent)** | 2 (Unlikely) |
| **Impact** | 4 (Major) |
| **Inherent Risk** | 8 (Medium) |

**Controls:**
- ✅ All sensitive data encrypted before storage
- ✅ Encryption keys stored separately from data
- ✅ Processor agreements with security requirements
- ✅ Minimal data shared with processors

**Residual Risk:** Likelihood 1 × Impact 2 = **2 (Low) ✅ Acceptable**

---

#### Risk 6: Excessive Data Retention

| Attribute | Assessment |
|-----------|------------|
| **Description** | Data kept longer than necessary |
| **Source** | Policy failure, system error |
| **Impact** | Non-compliance, increased breach impact |
| **Likelihood (inherent)** | 3 (Possible) |
| **Impact** | 2 (Minor) |
| **Inherent Risk** | 6 (Medium) |

**Controls:**
- ✅ Clear retention policy documented
- ✅ Automated account purging after 30 days of deletion request
- ✅ Inactive account policy (7 years)
- ✅ User can delete account immediately

**Residual Risk:** Likelihood 1 × Impact 2 = **2 (Low) ✅ Acceptable**

---

#### Risk 7: Consent Validity Issues

| Attribute | Assessment |
|-----------|------------|
| **Description** | Consent not freely given, specific, informed, or unambiguous |
| **Source** | Unclear consent mechanisms |
| **Impact** | Legal non-compliance, processing without lawful basis |
| **Likelihood (inherent)** | 2 (Unlikely) |
| **Impact** | 3 (Moderate) |
| **Inherent Risk** | 6 (Medium) |

**Controls:**
- ✅ Explicit consent step in onboarding
- ✅ Consent timestamp recorded
- ✅ Plain language privacy policy
- ✅ Separate consent for optional analytics
- ✅ Easy withdrawal mechanism (delete account)

**Residual Risk:** Likelihood 1 × Impact 2 = **2 (Low) ✅ Acceptable**

---

### 4.3 Risk Summary Matrix

```
Impact ↑
   5 │     │     │  R1 │     │     │
     │     │  R2 │     │     │     │
   4 │     │  R3 │  R5 │     │     │
     │     │     │     │     │     │
   3 │     │  R7 │     │     │     │
     │     │     │     │     │     │
   2 │  R4 │  R6 │     │     │     │
     │     │     │     │     │     │
   1 │     │     │     │     │     │
     └─────┴─────┴─────┴─────┴─────┘
       1     2     3     4     5   → Likelihood

Legend: Risk positions AFTER controls applied
```

---

## 5. MEASURES TO ADDRESS RISKS

### 5.1 Technical Measures

| Category | Measure | Status |
|----------|---------|--------|
| **Encryption** | Fernet (AES-128) for sensitive fields | ✅ Implemented |
| **Encryption** | HTTPS with HSTS | ✅ Implemented |
| **Encryption** | TLS 1.2+ for all connections | ✅ Implemented |
| **Authentication** | Argon2id password hashing | ✅ Implemented |
| **Authentication** | 12+ character password requirement | ✅ Implemented |
| **Authentication** | HIBP breach checking | ✅ Implemented |
| **Authentication** | TOTP-based MFA | ✅ Implemented |
| **Access control** | Role-based access | ✅ Implemented |
| **Access control** | Admin health data blocking | ✅ Implemented |
| **Access control** | User-scoped data queries | ✅ Implemented |
| **Monitoring** | Comprehensive audit logging | ✅ Implemented |
| **Monitoring** | Security event logging | ✅ Implemented |
| **Protection** | Rate limiting | ✅ Implemented |
| **Protection** | Account lockout | ✅ Implemented |
| **Protection** | Bot detection | ✅ Implemented |
| **Protection** | Security headers | ✅ Implemented |

### 5.2 Organisational Measures

| Category | Measure | Status |
|----------|---------|--------|
| **Governance** | DPO appointed | ✅ Implemented |
| **Governance** | Data breach response plan | ✅ Documented |
| **Governance** | Data processing register | ✅ Documented |
| **Training** | Staff security awareness | ✅ Documented |
| **Contracts** | Processor agreements | ✅ In place |
| **Policy** | Privacy policy | ✅ Published |
| **Policy** | Data retention policy | ✅ Documented |

### 5.3 Individual Rights Measures

| Right | Measure | Status |
|-------|---------|--------|
| Information | Privacy policy, onboarding consent | ✅ Implemented |
| Access | Data export (CSV, PDF) | ✅ Implemented |
| Rectification | Profile and entry editing | ✅ Implemented |
| Erasure | Account deletion with grace period | ✅ Implemented |
| Restriction | Account pause feature | ✅ Implemented |
| Portability | CSV export in standard format | ✅ Implemented |
| Object | Analytics opt-out | ✅ Implemented |

---

## 6. ICO CONSULTATION

### 6.1 Consultation Requirement

Under GDPR Article 36, prior consultation with the ICO is required if:

> "...processing would result in a high risk in the absence of measures taken by the controller to mitigate the risk."

### 6.2 Consultation Assessment

| Criterion | Assessment |
|-----------|------------|
| High risks identified? | Yes (health data processing) |
| Risks mitigated to acceptable level? | Yes (see Section 4) |
| Residual high risks remain? | No |

**Conclusion:** ICO consultation is **NOT required** because all identified high risks have been reduced to an acceptable level through the implemented technical and organisational measures.

---

## 7. INTEGRATION WITH DATA PROTECTION

### 7.1 Privacy by Design Compliance

| Principle | Implementation |
|-----------|----------------|
| Proactive not reactive | Security controls built-in from design |
| Privacy as default | Minimal data collection, encryption by default |
| Privacy embedded | Security layer in application architecture |
| Full functionality | Security without compromising user experience |
| End-to-end security | Encryption at rest and in transit |
| Visibility and transparency | Comprehensive privacy policy, audit logs |
| User-centric | User controls for all data |

### 7.2 Data Protection Principles Compliance

| Principle | Measure |
|-----------|---------|
| Lawfulness, fairness, transparency | Explicit consent, clear privacy policy |
| Purpose limitation | Data used only for symptom tracking |
| Data minimisation | Optional fields, minimal required data |
| Accuracy | User can edit all data |
| Storage limitation | Retention policy, deletion features |
| Integrity and confidentiality | Encryption, access controls, security measures |
| Accountability | DPO, audit logs, documentation |

---

## 8. MONITORING AND REVIEW

### 8.1 Ongoing Monitoring

| Activity | Frequency | Responsibility |
|----------|-----------|----------------|
| Security log review | Weekly | Technical Lead |
| Audit log review | Monthly | DPO |
| Vulnerability scanning | Quarterly | Technical Lead |
| Penetration testing | Annually | External provider |
| DPIA review | Annually | DPO |

### 8.2 Trigger Events for DPIA Update

- Significant changes to data processing
- New data categories collected
- New third-party processors
- Security incidents
- Changes to legal requirements
- User complaints

---

## 9. APPROVAL AND SIGN-OFF

### 9.1 Assessment Outcome

Based on this DPIA, the identified risks have been reduced to an acceptable level through the implementation of technical and organisational measures. The processing may proceed.

### 9.2 Conditions

The processing is approved subject to:

1. Continued implementation of all identified controls
2. Annual DPIA review
3. Immediate review following any security incident
4. Notification to DPO of any significant processing changes

### 9.3 Sign-off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Data Protection Officer | ________________ | ________________ | ___/___/2026 |
| Data Controller Representative | ________________ | ________________ | ___/___/2026 |
| Technical Lead | ________________ | ________________ | ___/___/2026 |

---

## 10. DOCUMENT CONTROL

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 22/01/2026 | DPO | Initial DPIA |

---

**END OF DOCUMENT**
