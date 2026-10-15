# COMPLIANCE.md: Privacy, Telecom & Messaging Regulatory Standards

> [!CAUTION]
> **LEGAL NOTICE**: This document represents technical engineering documentation of technical controls implemented in software. It is **NOT LEGAL ADVICE**. All compliance measures, policies, and workflows must be formally reviewed and approved by certified legal counsel in the relevant jurisdiction prior to production deployment or live communications.

---

## 1. Digital Personal Data Protection Act, 2023 (DPDP Act - India)

The system implements strict privacy-by-design architecture to adhere to DPDP requirements:

### 1.1 Consent Lifecycle & Verification (`consents` table)
- **Explicit Notice & Consent**: Consent is required before any outbound communication is scheduled or dispatched. Consent is captured with complete evidence: timestamp, source, IP address, text presented, and channel specification.
- **Purpose Limitation**: Consents are recorded with explicit purpose tags (e.g. `'marketing'`). Channels cannot send messages for unconsented purposes.
- **Easy Withdrawal**: Receipt of universal opt-out keywords (`STOP`, `UNSUBSCRIBE`, `CANCEL`, `NO MORE`, and transliterated Hindi/Kannada equivalents) automatically updates the append-only consent ledger to `withdrawn` status and writes an immediate entry to `suppressions`.
- **Database Guardrail**: `assert_consent(contact_id, channel)` raises an uncatchable database exception if current marketing consent is absent or withdrawn.

### 1.2 Data Principal Rights: Erasure (`DELETE /v1/contacts/{id}/pii`)
- **Single-Location PII Architecture**: All direct PII resides solely in `contact_pii` (encrypted) and `contact_identifiers` (HMAC hashed).
- **Hard Erasure**: Upon erasure request, `contact_pii`, `contact_identifiers`, `identity_links`, and message body payloads are permanently deleted from database storage.
- **Pseudonymization**: Non-PII behavioral and aggregate statistical data (`contacts`, `events`, `conversions`) are retained for historical auditability and bandit attribution with `contacts.erased_at` flagged.
- **Immutable Audit**: An append-only record is entered in `audit_log`.

### 1.3 Encryption & Tenant Isolation
- **Storage Encryption**: Symmetric AES-256-GCM encryption with cryptographically random IVs for all customer-identifying fields (`full_name_enc`, `phone_enc`, `email_enc`).
- **Tenant-Specific HMAC**: Hashed identifiers use HKDF-derived keys unique to each tenant UUID (`business_id`). Cross-tenant rainbow attacks are mathematically impossible.
- **Row-Level Security (RLS)**: Enforced at the database engine level via `SET LOCAL app.business_id`.

---

## 2. TRAI Commercial Communications Regulations (TCCCPR - India)

- **Quiet Hours Enforcement**: No promotional messages may be sent between 21:00 and 09:00 local business time. The action pipeline automatically delays and reschedules messages scheduled inside quiet hours.
- **Frequency Capping**: Default policy limits outbound communications to at most 3 messages per contact per week, and respects business-level daily message send caps.
- **Opt-Out Processing SLA**: Unsubscribe requests are registered instantaneously in `suppressions` (sub-second execution), halting all queued or future outbound pipelines.

---

## 3. WhatsApp Business Platform Policy & 24-Hour Messaging Window

- **Customer Care Window (24-Hour Rule)**: Free-form text messages are permitted strictly within 24 hours of the contact's most recent inbound message.
- **Pre-Approved Templates**: Outside the 24-hour window, the action executor rejects free-form text and strictly requires approved Meta-registered template assets.
- **Opt-In Mandate**: Outbound WhatsApp communications require demonstrable affirmative opt-in with explicit notice.
- **Prohibited Conduct**: Scraped numbers, unsolicited bulk messaging, cold lists, and deceptive promotions are strictly forbidden by code design.
