# CSU Tracker - Data Processing Register

**Document Version:** 1.0  
**Last Updated:** January 22, 2026  
**Document Owner:** Data Protection Officer  
**Classification:** Internal

---

## 1. OVERVIEW

This register documents all personal data processing activities carried out by CSU Tracker in accordance with GDPR Article 30 (Records of Processing Activities).

### 1.1 Data Controller Information

| Field | Details |
|-------|---------|
| **Organisation Name** | CSU Tracker |
| **Registration Number** | [Insert Company/ICO Registration] |
| **Address** | [Insert Registered Address] |
| **DPO Contact** | privacy@csutracker.com |
| **ICO Registration Number** | [Insert if applicable] |

---

## 2. PROCESSING ACTIVITY REGISTER

### Activity 1: User Account Management

| Field | Details |
|-------|---------|
| **Activity ID** | PA-001 |
| **Processing Activity** | User Account Registration and Management |
| **Purpose** | Authenticate users and provide access to the Service |
| **Legal Basis** | Contract (Article 6(1)(b)) |
| **Data Categories** | Email address, password hash, account status, login timestamps |
| **Data Subjects** | Registered users |
| **Data Source** | Direct input from data subject |
| **Recipients** | Internal systems only |
| **Third Countries** | None |
| **Retention Period** | Until account deletion + 30 days grace period |
| **Security Measures** | Argon2id password hashing, encrypted storage, audit logging |
| **Automated Decision Making** | None |

---

### Activity 2: User Profile Management

| Field | Details |
|-------|---------|
| **Activity ID** | PA-002 |
| **Processing Activity** | User Profile and Preferences |
| **Purpose** | Personalise user experience and store preferences |
| **Legal Basis** | Consent (Article 6(1)(a)) for optional fields; Contract (Article 6(1)(b)) for required fields |
| **Data Categories** | Display name, timezone, date format, score preferences, onboarding status |
| **Special Category Data** | None in this activity |
| **Data Subjects** | Registered users |
| **Data Source** | Direct input from data subject |
| **Recipients** | Internal systems only |
| **Third Countries** | None |
| **Retention Period** | Until account deletion |
| **Security Measures** | Encrypted storage for name fields |
| **Automated Decision Making** | None |

---

### Activity 3: Health Data - Personal Information

| Field | Details |
|-------|---------|
| **Activity ID** | PA-003 |
| **Processing Activity** | Collection of Personal Health Context |
| **Purpose** | Provide context for symptom tracking |
| **Legal Basis** | Explicit Consent (Article 9(2)(a)) for special category data |
| **Data Categories** | Date of birth, age, gender |
| **Special Category Data** | Gender (potentially sensitive) |
| **Data Subjects** | Registered users who provide optional data |
| **Data Source** | Direct input from data subject |
| **Recipients** | Data subject only |
| **Third Countries** | None |
| **Retention Period** | Until account deletion |
| **Security Measures** | Fernet (AES-128) encryption at rest |
| **Automated Decision Making** | None |

---

### Activity 4: Health Data - CSU Diagnosis Status

| Field | Details |
|-------|---------|
| **Activity ID** | PA-004 |
| **Processing Activity** | Recording CSU Diagnosis Status |
| **Purpose** | Contextual understanding for symptom tracking |
| **Legal Basis** | Explicit Consent (Article 9(2)(a)) |
| **Data Categories** | CSU diagnosis status (yes/no/unsure) |
| **Special Category Data** | Health data - diagnosis status |
| **Data Subjects** | Registered users who provide optional data |
| **Data Source** | Direct input from data subject |
| **Recipients** | Data subject only |
| **Third Countries** | None |
| **Retention Period** | Until account deletion |
| **Security Measures** | Fernet (AES-128) encryption at rest |
| **Automated Decision Making** | None |

---

### Activity 5: Health Data - Medication Information

| Field | Details |
|-------|---------|
| **Activity ID** | PA-005 |
| **Processing Activity** | Recording User Medication Context |
| **Purpose** | Enable correlation between treatments and symptoms |
| **Legal Basis** | Explicit Consent (Article 9(2)(a)) |
| **Data Categories** | Medication names, types, dosages, frequencies, injection dates |
| **Special Category Data** | Health data - treatment information |
| **Data Subjects** | Registered users who provide optional data |
| **Data Source** | Direct input from data subject |
| **Recipients** | Data subject only |
| **Third Countries** | None |
| **Retention Period** | Until account deletion |
| **Security Measures** | Model-level privacy (admin cannot view), database encryption |
| **Automated Decision Making** | None |

---

### Activity 6: Health Data - Daily Symptom Tracking

| Field | Details |
|-------|---------|
| **Activity ID** | PA-006 |
| **Processing Activity** | Daily CSU Symptom Score Recording |
| **Purpose** | Core service - track UAS7 symptom scores |
| **Legal Basis** | Explicit Consent (Article 9(2)(a)); Contract (Article 6(1)(b)) |
| **Data Categories** | Daily scores (0-6), itch severity, hive count, antihistamine usage |
| **Special Category Data** | Health data - symptom severity |
| **Data Subjects** | Registered users |
| **Data Source** | Direct input from data subject |
| **Recipients** | Data subject only (unless explicitly shared) |
| **Third Countries** | None |
| **Retention Period** | Until account deletion |
| **Security Measures** | User-scoped access, audit logging |
| **Automated Decision Making** | None |

---

### Activity 7: Health Data - Quality of Life Assessment

| Field | Details |
|-------|---------|
| **Activity ID** | PA-007 |
| **Processing Activity** | Quality of Life Impact Recording |
| **Purpose** | Holistic health impact tracking |
| **Legal Basis** | Explicit Consent (Article 9(2)(a)) |
| **Data Categories** | Sleep impact, daily activities impact, appearance impact, mood impact |
| **Special Category Data** | Health data - quality of life metrics |
| **Data Subjects** | Registered users who provide optional data |
| **Data Source** | Direct input from data subject |
| **Recipients** | Data subject only |
| **Third Countries** | None |
| **Retention Period** | Until account deletion |
| **Security Measures** | User-scoped access, audit logging |
| **Automated Decision Making** | None |

---

### Activity 8: Health Data - Personal Notes

| Field | Details |
|-------|---------|
| **Activity ID** | PA-008 |
| **Processing Activity** | Free-Text Health Observations |
| **Purpose** | Personal record keeping and correlation |
| **Legal Basis** | Explicit Consent (Article 9(2)(a)) |
| **Data Categories** | Free-text notes about symptoms, triggers, observations |
| **Special Category Data** | Health data - personal health observations |
| **Data Subjects** | Registered users who provide optional data |
| **Data Source** | Direct input from data subject |
| **Recipients** | Data subject only |
| **Third Countries** | None |
| **Retention Period** | Until account deletion |
| **Security Measures** | Fernet (AES-128) encryption at rest |
| **Automated Decision Making** | None |

---

### Activity 9: Authentication Security - MFA

| Field | Details |
|-------|---------|
| **Activity ID** | PA-009 |
| **Processing Activity** | Two-Factor Authentication |
| **Purpose** | Enhanced account security |
| **Legal Basis** | Contract (Article 6(1)(b)); Legitimate Interest (Article 6(1)(f)) for security |
| **Data Categories** | TOTP secret, MFA enabled status, last used timestamp |
| **Special Category Data** | None |
| **Data Subjects** | Users who enable MFA |
| **Data Source** | System-generated |
| **Recipients** | Internal systems only |
| **Third Countries** | None |
| **Retention Period** | Until MFA disabled or account deletion |
| **Security Measures** | Fernet encryption of TOTP secret |
| **Automated Decision Making** | None |

---

### Activity 10: Password Reset

| Field | Details |
|-------|---------|
| **Activity ID** | PA-010 |
| **Processing Activity** | Password Reset Token Management |
| **Purpose** | Enable secure password recovery |
| **Legal Basis** | Contract (Article 6(1)(b)) |
| **Data Categories** | Hashed reset token, request IP, user agent, expiry time |
| **Special Category Data** | None |
| **Data Subjects** | Users requesting password reset |
| **Data Source** | System-generated token; direct input (email) |
| **Recipients** | Internal systems; user via email |
| **Third Countries** | None (email may transit) |
| **Retention Period** | Token expires after 30 minutes |
| **Security Measures** | Token stored as hash, single-use, time-limited |
| **Automated Decision Making** | None |

---

### Activity 11: Push Notifications

| Field | Details |
|-------|---------|
| **Activity ID** | PA-011 |
| **Processing Activity** | Web Push Notification Delivery |
| **Purpose** | Send daily reminder notifications |
| **Legal Basis** | Consent (Article 6(1)(a)) |
| **Data Categories** | Push subscription endpoint, encryption keys, user agent, preferences |
| **Special Category Data** | None |
| **Data Subjects** | Users who enable notifications |
| **Data Source** | Browser-generated subscription |
| **Recipients** | Push service providers (browser vendors) |
| **Third Countries** | Potentially (push service endpoints) |
| **Retention Period** | Until subscription revoked or account deletion |
| **Security Measures** | End-to-end encrypted push |
| **Automated Decision Making** | None |

---

### Activity 12: Subscription and Payment Processing

| Field | Details |
|-------|---------|
| **Activity ID** | PA-012 |
| **Processing Activity** | Premium Subscription Management |
| **Purpose** | Process payments and manage premium access |
| **Legal Basis** | Contract (Article 6(1)(b)) |
| **Data Categories** | Stripe customer ID, subscription ID, status, billing dates |
| **Special Category Data** | None |
| **Data Subjects** | Premium subscribers |
| **Data Source** | Direct input; Stripe webhooks |
| **Recipients** | Stripe Inc (payment processor) |
| **Third Countries** | USA (Stripe) - covered by EU-US DPF and SCCs |
| **Retention Period** | Until subscription cancellation + legal retention requirements |
| **Security Measures** | Payment data not stored locally; Stripe PCI-DSS compliant |
| **Automated Decision Making** | None |

---

### Activity 13: Data Export

| Field | Details |
|-------|---------|
| **Activity ID** | PA-013 |
| **Processing Activity** | User Data Export (Subject Access) |
| **Purpose** | Enable data portability and access rights |
| **Legal Basis** | Legal Obligation (Article 6(1)(c)) - GDPR rights |
| **Data Categories** | All user data in exportable format |
| **Special Category Data** | All health data included in exports |
| **Data Subjects** | Users requesting export |
| **Data Source** | Internal database |
| **Recipients** | Data subject only (downloaded file) |
| **Third Countries** | None |
| **Retention Period** | Export generated on-demand; not retained |
| **Security Measures** | Authenticated access only; encrypted in transit |
| **Automated Decision Making** | None |

---

### Activity 14: Encrypted Cloud Backups

| Field | Details |
|-------|---------|
| **Activity ID** | PA-014 |
| **Processing Activity** | Automated User Data Backups |
| **Purpose** | Data recovery and protection |
| **Legal Basis** | Contract (Article 6(1)(b)); Legitimate Interest (Article 6(1)(f)) |
| **Data Categories** | All user data in encrypted snapshot |
| **Special Category Data** | Health data included but encrypted |
| **Data Subjects** | Premium subscribers with backup feature |
| **Data Source** | Internal database |
| **Recipients** | Cloud storage provider |
| **Third Countries** | Depends on hosting configuration |
| **Retention Period** | Configurable; default 30 days |
| **Security Measures** | Fernet encryption before storage |
| **Automated Decision Making** | None |

---

### Activity 15: Audit Logging

| Field | Details |
|-------|---------|
| **Activity ID** | PA-015 |
| **Processing Activity** | Security and Compliance Audit Logging |
| **Purpose** | Security monitoring, incident investigation, compliance |
| **Legal Basis** | Legitimate Interest (Article 6(1)(f)) |
| **Data Categories** | User ID, action type, timestamp, IP address (hashed), user agent, resource accessed |
| **Special Category Data** | None (references only, not health data content) |
| **Data Subjects** | All users |
| **Data Source** | System-generated |
| **Recipients** | Internal security team only |
| **Third Countries** | None |
| **Retention Period** | 1 year (security logs); 7 years (compliance logs) |
| **Security Measures** | Append-only logs, access restricted, log rotation |
| **Automated Decision Making** | None |

---

### Activity 16: Analytics (Optional)

| Field | Details |
|-------|---------|
| **Activity ID** | PA-016 |
| **Processing Activity** | Anonymous Usage Analytics |
| **Purpose** | Service improvement and usage understanding |
| **Legal Basis** | Consent (Article 6(1)(a)) |
| **Data Categories** | Feature usage patterns (anonymised), page views |
| **Special Category Data** | None (fully anonymised) |
| **Data Subjects** | Users who opt-in to analytics |
| **Data Source** | Application usage |
| **Recipients** | Internal analytics only |
| **Third Countries** | None |
| **Retention Period** | Aggregated data retained indefinitely; raw data 90 days |
| **Security Measures** | Data anonymised before processing |
| **Automated Decision Making** | None |

---

### Activity 17: Sharing and Access Grants

| Field | Details |
|-------|---------|
| **Activity ID** | PA-017 |
| **Processing Activity** | Third-Party Data Sharing (User-Initiated) |
| **Purpose** | Enable users to share reports with healthcare providers |
| **Legal Basis** | Consent (Article 6(1)(a)) - user-initiated sharing |
| **Data Categories** | Shared report content, recipient email, access token, permissions |
| **Special Category Data** | Health data if included in shared report |
| **Data Subjects** | Users who initiate sharing; Recipients |
| **Data Source** | User-defined sharing configuration |
| **Recipients** | User-designated contacts (healthcare providers, carers) |
| **Third Countries** | Potentially (depends on recipient location) |
| **Retention Period** | Until sharing revoked or expiry |
| **Security Measures** | Time-limited tokens, revocable access, audit logging |
| **Automated Decision Making** | None |

---

## 3. DATA FLOW SUMMARY

```
┌─────────────────────────────────────────────────────────────────────┐
│                         DATA SUBJECTS                                │
│                                                                      │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│   │   Account    │    │    Health    │    │     Preferences      │  │
│   │    Data      │    │    Data      │    │                      │  │
│   └──────┬───────┘    └──────┬───────┘    └──────────┬───────────┘  │
└──────────┼───────────────────┼───────────────────────┼──────────────┘
           │                   │                       │
           ▼                   ▼                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        CSU TRACKER                                   │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                     SECURITY LAYER                              │ │
│  │  • Fernet Encryption     • Rate Limiting                        │ │
│  │  • Argon2id Hashing      • Audit Logging                        │ │
│  │  • MFA                   • Session Management                   │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                              │                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                       DATABASE                                  │ │
│  │  PA-001 to PA-017: All processing activities                    │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
           │                   │                       │
           ▼                   ▼                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      THIRD PARTIES                                   │
│                                                                      │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│   │    Stripe    │    │   Hosting    │    │   User-Designated    │  │
│   │  (Payments)  │    │  Provider    │    │     Recipients       │  │
│   └──────────────┘    └──────────────┘    └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 4. RETENTION SCHEDULE

| Data Category | Retention Period | Basis | Deletion Method |
|---------------|------------------|-------|-----------------|
| Account data | Until deletion + 30 days | Contractual | Cascade delete |
| Profile data | Until deletion | Contractual | Cascade delete |
| Health data | Until deletion | Consent | Cascade delete |
| Symptom scores | Until deletion | Consent/Contract | Cascade delete |
| MFA secrets | Until disabled or deletion | Contractual | Cascade delete |
| Password reset tokens | 30 minutes | Operational | Automatic expiry |
| Push subscriptions | Until revoked or deletion | Consent | Manual/Cascade |
| Audit logs | 1-7 years | Legal obligation | Log rotation |
| Backups | 30 days (configurable) | Contractual | Automated cleanup |
| Sharing tokens | Until revoked or expiry | Consent | Manual/Automatic |

---

## 5. DOCUMENT CONTROL

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 22/01/2026 | DPO | Initial register |

---

**END OF DOCUMENT**
