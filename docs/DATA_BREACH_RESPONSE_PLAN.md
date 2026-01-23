# CSU Tracker - Data Breach Response Plan

**Document Version:** 1.0  
**Effective Date:** January 22, 2026  
**Last Review:** January 22, 2026  
**Next Review:** July 22, 2026  
**Document Owner:** Data Protection Officer  
**Classification:** Internal - Confidential

---

## 1. PURPOSE AND SCOPE

### 1.1 Purpose

This Data Breach Response Plan establishes procedures for detecting, responding to, and recovering from personal data breaches in compliance with:

- UK Data Protection Act 2018
- UK GDPR (as retained EU law)
- ICO (Information Commissioner's Office) guidance

### 1.2 Scope

This plan covers all personal data processed by CSU Tracker, including:

- User account data (email addresses)
- Health data (symptom scores, medication information, quality of life data)
- Profile data (name, date of birth, gender)
- Technical data (session tokens, MFA secrets)

### 1.3 Definition of Personal Data Breach

A personal data breach is a breach of security leading to the accidental or unlawful:

- **Destruction** of personal data
- **Loss** of personal data
- **Alteration** of personal data
- **Unauthorised disclosure** of personal data
- **Unauthorised access** to personal data

---

## 2. BREACH RESPONSE TEAM

### 2.1 Core Team Members

| Role | Responsibility | Contact |
|------|----------------|---------|
| **Data Protection Officer (DPO)** | Overall breach management, ICO liaison | privacy@csutracker.com |
| **Technical Lead** | Technical investigation, containment | tech@csutracker.com |
| **Communications Lead** | User and stakeholder communications | support@csutracker.com |
| **Legal Advisor** | Legal implications, regulatory compliance | legal@csutracker.com |

### 2.2 Escalation Matrix

| Severity | First Response | Escalation |
|----------|----------------|------------|
| Critical | Immediate | DPO + All team members |
| High | Within 1 hour | DPO + Technical Lead |
| Medium | Within 4 hours | Technical Lead |
| Low | Within 24 hours | Technical Lead |

---

## 3. BREACH CLASSIFICATION

### 3.1 Severity Levels

#### CRITICAL - Immediate Response Required
- Confirmed breach involving health data
- Breach affecting 100+ users
- Ongoing active attack
- Encryption keys compromised
- Database fully exposed

#### HIGH - Urgent Response Required
- Confirmed breach involving personal data (non-health)
- Breach affecting 10-99 users
- Potential health data exposure (unconfirmed)
- Authentication system compromised

#### MEDIUM - Priority Response Required
- Breach affecting 1-9 users
- Personal data sent to wrong recipient
- Unauthorised internal access detected
- Potential data exposure (contained)

#### LOW - Standard Response Required
- Near-miss incidents
- Policy violations without data exposure
- Failed attack attempts
- Minor configuration issues

### 3.2 Data Sensitivity Classification

| Data Type | Sensitivity | Notification Requirement |
|-----------|-------------|-------------------------|
| Health data (scores, medications, notes) | HIGH | Mandatory notification |
| Identity data (DOB, gender) | HIGH | Mandatory notification |
| Account data (email, password hash) | MEDIUM | Case-by-case assessment |
| Technical data (session tokens) | LOW | Generally not required |

---

## 4. BREACH RESPONSE PHASES

### Phase 1: DETECTION (0-1 hours)

#### 4.1.1 Detection Sources

- Security monitoring alerts (logs, SIEM)
- User reports
- Staff observations
- Third-party notifications
- Automated security tools

#### 4.1.2 Initial Assessment Checklist

```
□ What type of data is involved?
□ How many individuals are affected?
□ Is the breach ongoing or contained?
□ What is the potential harm to individuals?
□ Who discovered the breach and when?
□ Has any data left our systems?
```

#### 4.1.3 Immediate Actions

1. **Document** the incident in the breach log
2. **Preserve** all evidence (do not delete logs)
3. **Assess** if the breach is ongoing
4. **Escalate** to appropriate team members
5. **Start** the 72-hour notification clock

### Phase 2: CONTAINMENT (1-4 hours)

#### 4.2.1 Technical Containment Actions

| Scenario | Containment Action |
|----------|-------------------|
| Compromised credentials | Force password reset, invalidate sessions |
| Malware detected | Isolate affected systems |
| Unauthorised access | Revoke access, block IP addresses |
| Data exfiltration | Block network egress, isolate database |
| Vulnerable software | Apply emergency patch or disable feature |

#### 4.2.2 Containment Checklist

```
□ Stop the breach from continuing
□ Prevent further unauthorised access
□ Preserve evidence for investigation
□ Document all actions taken
□ Avoid destroying evidence
□ Consider whether to involve law enforcement
```

### Phase 3: ASSESSMENT (4-24 hours)

#### 4.3.1 Risk Assessment Matrix

| Factor | Low Risk | Medium Risk | High Risk |
|--------|----------|-------------|-----------|
| Data type | Email only | Name, DOB | Health data |
| Volume | 1-10 users | 11-100 users | 100+ users |
| Encryption | Fully encrypted | Partially encrypted | Unencrypted |
| Reversibility | Can be reversed | Partially reversible | Irreversible |
| Malicious intent | Accidental | Unknown | Confirmed malicious |

#### 4.3.2 Harm Assessment

Consider potential harm to affected individuals:

- **Physical harm** (unlikely for this application)
- **Psychological distress** (health data is sensitive)
- **Financial loss** (if payment data involved)
- **Reputational damage** (health conditions are private)
- **Discrimination** (based on health status)
- **Identity theft** (if identity data exposed)

#### 4.3.3 Documentation Requirements

Record the following in the breach register:

1. Date and time of breach detection
2. Date and time breach occurred (if known)
3. Nature of the breach
4. Categories of data affected
5. Approximate number of individuals affected
6. Name and contact of DPO
7. Likely consequences
8. Measures taken to address the breach

### Phase 4: NOTIFICATION (24-72 hours)

#### 4.4.1 ICO Notification Criteria

**Notify the ICO within 72 hours if:**

- The breach is likely to result in a risk to individuals' rights and freedoms

**Do NOT need to notify ICO if:**

- The breach is unlikely to result in a risk (e.g., encrypted data with secure keys)

#### 4.4.2 ICO Notification Template

```
PERSONAL DATA BREACH NOTIFICATION TO THE ICO

1. ORGANISATION DETAILS
   Organisation name: CSU Tracker
   ICO registration number: [INSERT]
   Contact: Data Protection Officer
   Email: privacy@csutracker.com
   Phone: [INSERT]

2. BREACH DETAILS
   Date/time breach discovered: [DATE/TIME]
   Date/time breach occurred: [DATE/TIME or "Unknown"]
   
3. NATURE OF BREACH
   □ Confidentiality breach (unauthorised disclosure)
   □ Integrity breach (unauthorised alteration)
   □ Availability breach (loss of access)
   
   Description: [DETAILED DESCRIPTION]

4. DATA CATEGORIES AFFECTED
   □ Basic identifiers (email)
   □ Identity data (name, DOB, gender)
   □ Health data (symptom scores, medications)
   □ Authentication data (password hashes)
   
5. INDIVIDUALS AFFECTED
   Number of individuals: [NUMBER]
   Categories of individuals: Application users
   
6. LIKELY CONSEQUENCES
   [DESCRIBE POTENTIAL HARM]
   
7. MEASURES TAKEN
   [LIST CONTAINMENT AND REMEDIATION ACTIONS]
   
8. COMMUNICATION TO INDIVIDUALS
   □ Have been notified
   □ Will be notified (date: [DATE])
   □ Will not be notified (reason: [REASON])
```

#### 4.4.3 User Notification Criteria

**Notify affected users without undue delay if:**

- The breach is likely to result in a HIGH risk to their rights and freedoms

#### 4.4.4 User Notification Template

```
Subject: Important Security Notice - CSU Tracker

Dear [USER],

We are writing to inform you of a data security incident that may 
affect your CSU Tracker account.

WHAT HAPPENED
[Clear, plain-language description of the incident]

WHAT DATA WAS AFFECTED
[List specific data types affected for this user]

WHAT WE ARE DOING
[List of actions taken to address the breach]

WHAT YOU CAN DO
1. Change your password immediately: [LINK]
2. Enable two-factor authentication: [LINK]
3. Be alert for suspicious emails or messages
4. [Any other specific recommendations]

CONTACT US
If you have questions, please contact our Data Protection Officer:
Email: privacy@csutracker.com

We sincerely apologise for any concern this may cause.

The CSU Tracker Team
```

### Phase 5: REMEDIATION (72 hours - 2 weeks)

#### 4.5.1 Technical Remediation

```
□ Patch vulnerable systems
□ Strengthen access controls
□ Enhance monitoring
□ Review security configurations
□ Update security policies
□ Implement additional security measures
```

#### 4.5.2 Process Remediation

```
□ Review and update incident response procedures
□ Conduct staff awareness training
□ Update risk assessments
□ Review third-party security
□ Update data protection policies
```

### Phase 6: POST-INCIDENT REVIEW (2-4 weeks)

#### 4.6.1 Post-Incident Review Checklist

```
□ Conduct root cause analysis
□ Document lessons learned
□ Update breach response plan
□ Share findings with relevant staff
□ Update risk register
□ Consider external audit
□ Report to senior management
□ Close incident in breach register
```

#### 4.6.2 Post-Incident Report Template

```
POST-INCIDENT REVIEW REPORT

1. INCIDENT SUMMARY
   - Incident ID: [ID]
   - Date range: [START] to [END]
   - Severity: [LEVEL]
   
2. TIMELINE OF EVENTS
   [Chronological list of key events]
   
3. ROOT CAUSE ANALYSIS
   [Analysis of what caused the breach]
   
4. EFFECTIVENESS OF RESPONSE
   [Assessment of how well the plan worked]
   
5. LESSONS LEARNED
   [Key takeaways from the incident]
   
6. RECOMMENDATIONS
   [Actions to prevent recurrence]
   
7. ACTION ITEMS
   [Specific tasks with owners and deadlines]
```

---

## 5. BREACH REGISTER

### 5.1 Register Requirements

Maintain a register of ALL personal data breaches, including:

- Those reported to the ICO
- Those NOT reported to the ICO (with reasons)

### 5.2 Register Template

| Field | Description |
|-------|-------------|
| Incident ID | Unique identifier |
| Date Discovered | When breach was detected |
| Date Occurred | When breach happened (if known) |
| Reporter | Who reported the breach |
| Description | Nature of the breach |
| Data Categories | Types of data affected |
| Individuals Affected | Number and categories |
| Severity | Critical/High/Medium/Low |
| ICO Notified | Yes/No + date |
| Users Notified | Yes/No + date |
| Containment Actions | Steps taken |
| Root Cause | Why it happened |
| Remediation | How it was fixed |
| Lessons Learned | Key takeaways |
| Status | Open/Closed |
| Closed Date | When incident was closed |

---

## 6. CONTACT INFORMATION

### 6.1 Internal Contacts

| Role | Email | Phone |
|------|-------|-------|
| Data Protection Officer | privacy@csutracker.com | [TBD] |
| Technical Lead | tech@csutracker.com | [TBD] |
| Support Lead | support@csutracker.com | [TBD] |

### 6.2 External Contacts

| Organisation | Purpose | Contact |
|--------------|---------|---------|
| ICO | Breach reporting | https://ico.org.uk/make-a-complaint/data-protection-complaints/data-protection-complaints/ |
| ICO Helpline | Guidance | 0303 123 1113 |
| Cyber Essentials | Certification body | [If applicable] |
| Legal Counsel | Legal advice | [TBD] |
| Cyber Insurance | Claims | [If applicable] |

---

## 7. TESTING AND MAINTENANCE

### 7.1 Plan Testing

- **Annual tabletop exercise**: Simulate breach scenario with response team
- **Quarterly review**: Review and update contact information
- **Post-incident review**: Update plan after any real breach

### 7.2 Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 22/01/2026 | DPO | Initial version |

---

## 8. APPENDICES

### Appendix A: Quick Reference Card

```
┌─────────────────────────────────────────────────────────────┐
│              DATA BREACH QUICK REFERENCE                     │
├─────────────────────────────────────────────────────────────┤
│  1. DON'T PANIC - Follow this plan                          │
│  2. PRESERVE EVIDENCE - Don't delete anything               │
│  3. CONTAIN - Stop the breach from continuing               │
│  4. DOCUMENT - Record everything you do                     │
│  5. ESCALATE - Contact DPO: privacy@csutracker.com          │
│  6. 72 HOURS - ICO notification deadline starts now         │
├─────────────────────────────────────────────────────────────┤
│  SEVERITY GUIDE:                                            │
│  CRITICAL: Health data, 100+ users, active attack           │
│  HIGH: Personal data, 10-99 users, auth compromise          │
│  MEDIUM: 1-9 users, misdirected data                        │
│  LOW: Near-miss, failed attacks                             │
└─────────────────────────────────────────────────────────────┘
```

### Appendix B: Evidence Preservation Checklist

```
□ Take screenshots of affected systems
□ Export relevant log files
□ Record timestamps in UTC
□ Document network connections
□ Preserve email headers if relevant
□ Do NOT modify, delete, or "clean up" anything
□ Create forensic copies if possible
□ Maintain chain of custody for evidence
```

### Appendix C: Communication Templates

See Section 4.4.4 for user notification template.

---

**END OF DOCUMENT**
