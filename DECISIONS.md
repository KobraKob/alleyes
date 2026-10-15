# DECISIONS.md: Autonomous Marketing Engine Architectural & Technical Choices

This document logs all non-obvious design choices, rationale, and justifications made during implementation.

## D-001: Migration 0002 Pending Decisions Index
- **Specification Query:** `BUILD.md` specified `CREATE INDEX decisions_pending_idx ON decisions (business_id, decided_at) WHERE stats_counted = false OR true;` and directed replacing the predicate with a useful one.
- **Decision:** Defined index with `WHERE stats_counted = false`.
- **Rationale:** The stats updater queries uncounted decisions to update arm counts. Adding `OR true` makes it an unconstrained table scan index. A partial index with `WHERE stats_counted = false` stays small and allows fast index scans for pending updates.

## D-002: Ingestion API Keys (Migration 0003)
- **Specification Requirement:** Section 4, P1.1 mandates API key auth per business with hashed keys stored in the database.
- **Decision:** Created table `api_keys` in migration `0003`:
  - Columns: `id` (uuid), `business_id` (uuid references businesses), `key_prefix` (varchar(8) for fast lookup), `key_hash` (text, argon2id hash), `name` (text), `created_at` (timestamptz), `revoked_at` (timestamptz nullable).
- **Rationale:** Storing a prefix allows O(1) lookup of candidates before Argon2 verification, avoiding expensive scans while retaining cryptographically secure hashing.

## D-003: PII Encryption Format
- **Decision:** AES-256-GCM using a 12-byte cryptographically secure random nonce prepended to ciphertext with the 16-byte authentication tag appended: `nonce (12B) || ciphertext || tag (16B)`.
- **Tenant HMAC Derivation:** Per-tenant HMAC key derived via HKDF-SHA256 using master secret as input key material, business UUID bytes as salt, and ASCII `"tenant-hmac-v1"` as info.
- **Rationale:** Provides authenticated encryption preventing bit-flipping attacks, with zero cross-tenant key re-use.

## D-004: Event Partition Manager Defaults
- **Decision:** The partition manager maintains a rolling window containing the current month and the next 3 months, plus a fallback `events_default` partition.
- **Rationale:** Protects against unexpected clock skew or historical backfilling while ensuring hot queries hit bounded monthly partition tables.

## D-005: Decoupled Domain Architecture
- **Decision:** All bandit algorithms (Thompson Sampling with Beta/Gaussian posteriors, probability matching with $\epsilon$-exploration), attribution models (First Touch, Last Touch, Position 40/20/40), reward scaling, Off-Policy Evaluation (IPS, SNIPS, Bootstrap CI), and policy validation rules are written as pure functions with zero I/O dependencies.
- **Rationale:** Enables deterministic property-based testing (Hypothesis), 100% reproducible simulation runs, and complete auditability without side effects.
