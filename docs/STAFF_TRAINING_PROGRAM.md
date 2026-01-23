# CSU Tracker Staff Training Program

## Data Protection & Security Awareness Training

**Document Version:** 1.0  
**Last Updated:** January 2025  
**Document Owner:** Data Protection Officer  
**Review Frequency:** Annual  

---

## 1. Introduction

This document outlines the mandatory data protection and security training program for all staff involved in the development, operation, and maintenance of CSU Tracker. As a health data application processing special category data under GDPR Article 9, maintaining high standards of data protection awareness is critical.

### 1.1 Training Objectives

Upon completion of this training program, staff will be able to:

1. Understand the legal requirements of UK GDPR and Data Protection Act 2018
2. Recognize and properly handle special category (health) data
3. Identify security threats and respond appropriately
4. Follow correct procedures for data subject requests
5. Report data breaches promptly and correctly
6. Apply privacy by design principles in their work

### 1.2 Who Must Complete Training

| Role | Initial Training | Refresher Frequency |
|------|-----------------|---------------------|
| Developers | Within 2 weeks of joining | Annual |
| System Administrators | Within 2 weeks of joining | Annual |
| Support Staff | Before handling user data | Annual |
| Management | Within 1 month of joining | Annual |
| Contractors | Before project commencement | Per project |

---

## 2. Core Training Modules

### Module 1: Data Protection Fundamentals (2 hours)

#### 1.1 Legal Framework Overview

**UK GDPR Key Principles:**

| Principle | Meaning | Our Application |
|-----------|---------|-----------------|
| **Lawfulness, Fairness, Transparency** | Process data legally and openly | Explicit consent for health data |
| **Purpose Limitation** | Use data only for specified purposes | Only symptom tracking, never marketing |
| **Data Minimisation** | Collect only what's needed | Minimal profile data required |
| **Accuracy** | Keep data accurate and up to date | User can edit entries anytime |
| **Storage Limitation** | Don't keep data longer than needed | Clear retention policy: active use + 7 years |
| **Integrity and Confidentiality** | Keep data secure | Encryption at rest and in transit |
| **Accountability** | Demonstrate compliance | Audit logs, this documentation |

#### 1.2 Special Category Data

CSU Tracker processes **health data** which is special category data under GDPR Article 9.

**Why this matters:**
- Higher protection standards required
- Explicit consent required (not just legitimate interest)
- Data breach notification is more urgent
- Stricter access controls required
- Regular auditing of access is mandatory

**What constitutes health data in CSU Tracker:**
- Symptom entries (itch score, hive count)
- Diagnosis information
- Medication records
- Treatment notes
- UAS7 scores

#### 1.3 Lawful Basis for Processing

Our lawful basis for processing health data:

| Data Type | Lawful Basis | Article |
|-----------|--------------|---------|
| Health data | Explicit consent | GDPR Art. 9(2)(a) |
| Account data | Contract performance | GDPR Art. 6(1)(b) |
| Security logs | Legitimate interests | GDPR Art. 6(1)(f) |
| Legal compliance | Legal obligation | GDPR Art. 6(1)(c) |

---

### Module 2: Security Awareness (2 hours)

#### 2.1 Common Security Threats

**Phishing Attacks:**
- Never click links in unexpected emails
- Verify sender email addresses carefully
- Report suspicious emails to security team
- Never enter credentials after clicking email links

**Social Engineering:**
- Never share passwords or access credentials
- Verify identity before providing information
- Be suspicious of urgent requests
- Follow verification procedures for all requests

**Malware:**
- Keep all software updated
- Only install approved software
- Don't connect unknown USB devices
- Report unusual system behavior

#### 2.2 Password & Access Security

**Password Requirements:**
- Minimum 12 characters
- Mix of uppercase, lowercase, numbers, symbols
- Never reuse passwords across systems
- Use password manager (approved: 1Password, Bitwarden)
- Never share passwords

**Multi-Factor Authentication:**
- MFA is mandatory for:
  - Production server access
  - Admin panel access
  - Code repository access
  - Cloud service consoles
- Use authenticator apps (not SMS where possible)

**Access Control:**
- Request minimum necessary permissions
- Report when access is no longer needed
- Never share login sessions
- Lock workstation when away (even briefly)

#### 2.3 Secure Development Practices

**For Developers:**

```
✅ DO:
- Use parameterized queries (prevent SQL injection)
- Validate all user input
- Use secure password hashing (Argon2id)
- Encrypt sensitive data at rest
- Use HTTPS for all connections
- Follow principle of least privilege
- Review code for security issues

❌ DON'T:
- Store secrets in code or version control
- Log sensitive data (passwords, health info)
- Disable security features for convenience
- Use hardcoded credentials
- Trust user input without validation
- Expose detailed error messages to users
```

---

### Module 3: Data Subject Rights (1.5 hours)

#### 3.1 Overview of Rights

Users of CSU Tracker have the following rights:

| Right | Description | Response Time |
|-------|-------------|---------------|
| **Access** | Obtain copy of their data | 1 month |
| **Rectification** | Correct inaccurate data | 1 month |
| **Erasure** | Delete their data | 1 month |
| **Portability** | Export data in machine-readable format | 1 month |
| **Restriction** | Pause processing (account pause) | 1 month |
| **Object** | Object to processing | 1 month |
| **Withdraw Consent** | Remove consent for processing | Immediate |

#### 3.2 Handling Data Subject Requests

**Step-by-Step Process:**

1. **Receive Request**
   - Log the request immediately
   - Note date received (starts 1-month clock)
   - Forward to DPO if not already sent there

2. **Verify Identity**
   - Request verification if not from authenticated session
   - Use approved verification methods only
   - Document verification process

3. **Assess Request**
   - Determine which right is being exercised
   - Check if any exemptions apply
   - Escalate complex cases to DPO

4. **Fulfill Request**
   - Complete within 1 month
   - Document all actions taken
   - Provide clear response to user

5. **Close and Log**
   - Record completion in DSR log
   - Store records for 3 years
   - Report metrics to DPO

#### 3.3 Self-Service Features

Most rights are handled automatically through the app:

| Right | Self-Service Feature |
|-------|---------------------|
| Access | Export Data (PDF/CSV) |
| Erasure | Delete Account |
| Restriction | Pause Account |
| Portability | Export Data (JSON) |
| Rectification | Edit Profile/Entries |

**When to escalate:**
- User can't access their account
- Technical issues preventing self-service
- User disputes something in their data
- Request involves third parties
- Complex or unusual requests

---

### Module 4: Incident Response (1.5 hours)

#### 4.1 What Is a Data Breach?

A data breach is any security incident where personal data is:
- **Accessed** by unauthorized persons
- **Disclosed** to unauthorized recipients
- **Lost** without backup recovery
- **Altered** without authorization
- **Destroyed** improperly

**Examples in CSU Tracker context:**

| Scenario | Is it a breach? |
|----------|----------------|
| User forgets password | ❌ No |
| Developer accidentally views user data during debugging | ⚠️ Potential - assess |
| Unauthorized access to database | ✅ Yes |
| Lost laptop with cached user data | ✅ Yes |
| User shares their own data | ❌ No (their choice) |
| Phishing attack obtains admin credentials | ✅ Yes |
| System outage making data unavailable | ⚠️ Possible - assess |

#### 4.2 Breach Reporting Procedure

**If you suspect or discover a breach:**

```
┌─────────────────────────────────────────────────────────────┐
│  1. STOP - Don't try to fix it yourself                     │
│                                                             │
│  2. PRESERVE - Don't delete logs or evidence                │
│                                                             │
│  3. REPORT - Contact security team IMMEDIATELY              │
│     📧 security@csutracker.com                              │
│     📞 Emergency: [PHONE NUMBER]                            │
│                                                             │
│  4. DOCUMENT - Note what you observed and when              │
│                                                             │
│  5. WAIT - Await instructions, don't discuss externally     │
└─────────────────────────────────────────────────────────────┘
```

**Required Information for Report:**
- What happened (describe what you observed)
- When you noticed it
- What data may be affected
- How many users may be affected
- Any actions already taken
- Your contact details

**Timeline Requirements:**
- Internal report: Within 1 hour of discovery
- ICO notification (if required): Within 72 hours
- User notification (if required): Without undue delay

#### 4.3 Common Mistakes to Avoid

❌ **Don't:**
- Assume someone else reported it
- Try to cover up or minimize
- Discuss on public channels
- Delete potential evidence
- Notify users without authorization
- Speak to media without approval

✅ **Do:**
- Report immediately, even if uncertain
- Be honest and thorough
- Follow official procedures
- Cooperate with investigation
- Maintain confidentiality

---

### Module 5: Privacy by Design (1 hour)

#### 5.1 Core Principles

When developing new features, apply these principles:

| Principle | Application |
|-----------|-------------|
| **Proactive not Reactive** | Build in privacy from the start |
| **Privacy as Default** | Minimum data collection by default |
| **Privacy Embedded** | Privacy is core functionality, not add-on |
| **Full Functionality** | Privacy doesn't reduce features |
| **End-to-End Security** | Data protected throughout lifecycle |
| **Visibility and Transparency** | Users understand what happens |
| **Respect for User Privacy** | User interests are paramount |

#### 5.2 Privacy Checklist for New Features

Before deploying any new feature, verify:

```
□ What personal data does this feature collect?
□ Is all collected data necessary for the feature?
□ Have we updated the privacy notice if needed?
□ Is data encrypted in transit and at rest?
□ Who can access this data?
□ How long will data be retained?
□ Can users delete this data?
□ Has the feature been security tested?
□ Has the DPO reviewed for DPIA requirements?
□ Are audit logs capturing relevant events?
```

#### 5.3 Data Minimization Examples

**Good Practice:**

| Feature | Minimized Approach |
|---------|-------------------|
| User profile | Email only required, name optional |
| Symptom tracking | Date + scores only, detailed notes optional |
| Push notifications | Device token stored, not device info |
| Analytics | Aggregated data, no individual tracking |

---

## 3. Role-Specific Training

### 3.1 Developer-Specific Training

**Additional Topics:**
- Secure coding standards (OWASP Top 10)
- Code review security checklist
- Dependency vulnerability scanning
- Secret management best practices
- Security testing procedures

**Practical Exercises:**
- SQL injection prevention lab
- XSS prevention lab
- Authentication implementation review
- Encryption implementation review

### 3.2 System Administrator Training

**Additional Topics:**
- Access control management
- Log monitoring and analysis
- Incident detection procedures
- Backup and recovery testing
- Patch management procedures

**Practical Exercises:**
- Simulated breach detection
- Access review procedures
- Backup restoration testing

### 3.3 Support Staff Training

**Additional Topics:**
- Identity verification procedures
- Handling data subject requests
- Recognizing social engineering
- Escalation procedures
- Dealing with distressed users

**Practical Exercises:**
- DSR handling simulation
- Phishing identification tests
- Difficult conversation role-play

---

## 4. Training Assessment

### 4.1 Completion Requirements

To pass each module:
- Score at least 80% on knowledge assessment
- Complete all practical exercises (where applicable)
- Sign acknowledgment of policies

### 4.2 Sample Assessment Questions

**Module 1 - Data Protection:**

1. What type of data does CSU Tracker primarily process?
   - [ ] Financial data
   - [x] Health (special category) data
   - [ ] Criminal records
   - [ ] Genetic data

2. Under GDPR, how long do we have to respond to a data subject access request?
   - [ ] 7 days
   - [ ] 14 days
   - [x] 1 month
   - [ ] 3 months

**Module 2 - Security:**

3. Which of these is acceptable password practice?
   - [ ] Using the same password for work and personal
   - [ ] Sharing password with trusted colleague
   - [x] Using a unique 16-character password with MFA
   - [ ] Writing password on sticky note near monitor

**Module 4 - Incident Response:**

4. You discover what might be a data breach at 5pm Friday. What should you do?
   - [ ] Wait until Monday to report
   - [ ] Try to investigate and fix it yourself
   - [x] Report immediately to security team
   - [ ] Email the DPO and go home

### 4.3 Certification

Upon successful completion:
- Certificate of completion issued
- Record added to training database
- Reminder set for next annual refresher

---

## 5. Training Schedule

### 5.1 Annual Training Calendar

| Month | Activity |
|-------|----------|
| January | Annual refresher training (all staff) |
| March | Phishing simulation exercise |
| June | Incident response drill |
| September | Privacy by design workshop (developers) |
| November | Data subject rights refresher |

### 5.2 New Starter Onboarding

| Week | Training |
|------|----------|
| 1 | Modules 1 & 2 (Data Protection & Security) |
| 2 | Modules 3 & 4 (Data Rights & Incident Response) |
| 3 | Module 5 (Privacy by Design) + Role-specific |
| 4 | Assessment and certification |

---

## 6. Resources and Support

### 6.1 Key Contacts

| Role | Contact |
|------|---------|
| Data Protection Officer | dpo@csutracker.com |
| Security Team | security@csutracker.com |
| IT Support | support@csutracker.com |
| Emergency Breach Line | [PHONE NUMBER] |

### 6.2 Reference Documents

- UK GDPR Full Text: legislation.gov.uk
- ICO Guidance: ico.org.uk
- CSU Tracker Privacy Policy
- Data Breach Response Plan
- Data Processing Register
- DPIA Document

### 6.3 Further Learning

**Recommended External Training:**
- ICO Free Online Training
- NCSC Cyber Security Awareness
- IAPP CIPP/E Certification (for those seeking specialization)

---

## 7. Policy Acknowledgment

All staff must sign this acknowledgment after completing training:

---

**TRAINING COMPLETION ACKNOWLEDGMENT**

I, _________________________ (print name), confirm that:

1. I have completed the CSU Tracker Data Protection and Security Training
2. I understand my responsibilities for protecting personal data
3. I understand the procedures for reporting security incidents
4. I will comply with all data protection policies
5. I understand that failure to comply may result in disciplinary action

Signature: _________________________

Date: _________________________

Training Completed: _________________________

Line Manager: _________________________

---

*This document will be reviewed annually by the Data Protection Officer. Any changes to data protection legislation or organizational practices will trigger an immediate review and update of training materials.*
