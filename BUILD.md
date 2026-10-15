# BUILD.md: Autonomous Marketing Engine (v1)

You are a coding agent building this system. Read this whole file before writing code. Follow the phases in order. Do not skip acceptance criteria. Where this file is silent, choose the simplest option that satisfies the rules in section 1, and record the choice in `DECISIONS.md`.

The database design is already done: `marketing_engine_schema.sql` (provided alongside this file) is the source of truth. Treat it as migration `0001`.

---

## 0. What we are building

A multi-tenant platform where a business states an objective (for example "120 paid gym memberships per month across 3 branches, CAC under INR 1,500"). Autonomous agents then find consented leads, respond to them, run campaigns, and onboard and retain members. Every autonomous choice is logged with its probability, rewards are computed from real downstream outcomes, and the system shifts effort toward what works.

**v1 scope:** one vertical (`gym`), real multi-tenancy in the data layer, WhatsApp + Meta Ads + email connectors, five agents (lead-response, planner, ads, analyst, retention-lite), a governance layer, a minimal dashboard, and a market simulator that proves the learning loop works.

**Non-goals for v1** (do not build): LinkedIn/Instagram scraping, cold outreach to private individuals, a self-serve signup flow, billing, a mobile app, any vertical other than gym, fine-tuning or RL training of models.

---

## 1. Ground rules (apply to every task)

1. **Dry-run by default.** `DRY_RUN=true` unless explicitly overridden. In dry-run, connectors log what they would do and return fake success. Real sends additionally require `LIVE_SENDS=true` and an autonomy policy permitting the action. Never send a real message or spend real money in tests.
2. **Schema is law.** Do not edit `0001`. All changes go in new numbered Alembic migrations, each listed in `DECISIONS.md` with a reason.
3. **Events are immutable.** Never UPDATE or DELETE rows in `events`. Corrections are new events.
4. **Every autonomous choice goes through `decide()`** (section 5) and writes a `decisions` row with a valid propensity. No agent may pick among options any other way.
5. **Every agent side-effect goes through the action pipeline** (section 6). Agents write `actions` rows; only the executor performs them after policy checks.
6. **Idempotency everywhere.** Every webhook handler, ingest endpoint, job, and action uses an idempotency key. Replaying any input twice must produce no duplicate effect. Test this.
7. **No PII outside `contact_pii` and `messages.body_enc`.** Never log PII. Hash identifiers with the per-tenant key (`contact_identifiers.value_hash`).
8. **Tenant isolation is enforced by RLS**, not just by `WHERE` clauses. Application code sets `app.business_id` per request and per job via `SET LOCAL`.
9. **Money is `bigint` minor units.** No floats for currency anywhere.
10. **Secrets never enter the DB or the repo.** `connector_accounts.credentials_ref` points to a secret store interface; implement a local-file/env backend for dev.
11. **Time:** store UTC, `timestamptz` everywhere. Business-local logic (quiet hours, daily caps) uses `businesses.timezone`.
12. **Every phase ends green:** lint, type-check, all tests passing, and the phase's acceptance criteria demonstrated by an automated test or a script in `scripts/`.

---

## 2. Stack (decided, do not relitigate)

| Concern | Choice |
|---|---|
| Language | Python 3.12, fully type-hinted, `mypy --strict` on `src/` |
| API | FastAPI + Pydantic v2 |
| DB | PostgreSQL 16 + pgvector, accessed via SQLAlchemy 2.0 (Core for hot paths, ORM optional) |
| Migrations | Alembic; `0001` executes `marketing_engine_schema.sql` verbatim |
| Jobs / scheduling | Procrastinate (Postgres-backed queue). No Redis, no Celery |
| LLM | Anthropic SDK behind an `LLMClient` protocol; model name from `LLM_MODEL` env; fake client for tests |
| Math | numpy, scipy |
| HTTP client | httpx |
| Tests | pytest, pytest-asyncio, hypothesis (property tests), testcontainers-postgres |
| Lint/format | ruff, mypy |
| Dashboard | Next.js (App Router) + TypeScript + Tailwind, talks only to the FastAPI API |
| Local infra | `docker-compose.yml`: postgres, api, worker, dashboard |
| CI | GitHub Actions: lint, types, tests with a postgres service |

### Repo layout

```
.
├── BUILD.md
├── DECISIONS.md              # you maintain: every choice not specified here
├── DEVIATIONS.md             # you maintain: anything that differs from this file, with reason
├── marketing_engine_schema.sql
├── docker-compose.yml
├── pyproject.toml
├── alembic/versions/
├── prompts/                  # versioned prompt files (one per agent/task), never inline in code
├── packs/gym/pack.yaml       # vertical pack source, loaded into vertical_packs.config
├── scripts/                  # seed, simulate, demo
├── src/engine/
│   ├── config.py
│   ├── db/                   # session, RLS context, repositories
│   ├── domain/               # pure logic, no I/O (bandits, attribution, rewards, policy)
│   ├── ingest/               # event + webhook ingestion
│   ├── identity/             # contacts, PII crypto, identity resolution, consent
│   ├── attribution/
│   ├── learning/             # decide(), reward calc, stats updater, priors job, OPE
│   ├── governance/           # policy engine, actions, approvals, kill switch, audit
│   ├── connectors/           # base protocol + whatsapp, meta_ads, email, fake
│   ├── agents/               # runtime + lead_response, planner, ads, analyst, retention
│   ├── llm/                  # client protocol, anthropic impl, fake, tracing
│   ├── api/                  # FastAPI routers
│   └── jobs/                 # procrastinate tasks + schedules
├── dashboard/
└── tests/ (unit/, integration/, simulation/)
```

### Environment variables (`.env.example` must list all)

`DATABASE_URL`, `APP_ROLE_URL` (non-owner role, RLS enforced), `LEARNING_ROLE_URL` (BYPASSRLS, priors job only), `DRY_RUN`, `LIVE_SENDS`, `LLM_MODEL`, `ANTHROPIC_API_KEY`, `PII_ENCRYPTION_KEY` (32-byte base64), `TENANT_HMAC_MASTER_KEY`, `WHATSAPP_VERIFY_TOKEN`, `WHATSAPP_APP_SECRET`, `META_APP_ID`, `META_APP_SECRET`, `SES_REGION`, `JWT_SECRET`, `TRACE_STORE_URI` (file:// or s3://).

---

## 3. Phase 0: Foundations

**Tasks**
- P0.1 Scaffold repo per layout, tooling, CI, docker-compose, `.env.example`.
- P0.2 Alembic `0001` runs the provided schema verbatim. Add migration `0002` (below).
- P0.3 Create DB roles: `migrator` (owner), `app_user` (no BYPASSRLS, subject to FORCE RLS), `learning_svc` (BYPASSRLS, granted SELECT on needed tables and INSERT/UPDATE on `priors` only).
- P0.4 `db/session.py`: a `tenant_session(business_id)` context manager that opens a transaction and runs `SET LOCAL app.business_id = ...`. Refuse to run queries on tenant tables without it.
- P0.5 Event partition manager: a job that ensures partitions exist for the current month and the next 3, plus a `events_default` partition so inserts never fail.
- P0.6 Seed script: event types, the `gym` vertical pack, one demo organization/business/3 locations.
- P0.7 Load `packs/gym/pack.yaml` into `vertical_packs`, and a function that instantiates a business's `funnel_stages`, `decision_points`, `reward_models` (v1) from its pack.

**Migration `0002` (required additions)**
```sql
ALTER TABLE decisions ADD COLUMN stats_applied_reward numeric(12,4) NOT NULL DEFAULT 0;
ALTER TABLE decisions ADD COLUMN stats_counted boolean NOT NULL DEFAULT false;
CREATE INDEX decisions_pending_idx ON decisions (business_id, decided_at) WHERE stats_counted = false OR true;
CREATE INDEX rewards_decision_idx ON rewards (decision_id, observed_at DESC);
CREATE INDEX actions_status_idx ON actions (business_id, status, proposed_at);
CREATE INDEX messages_conv_idx ON messages (conversation_id, sent_at);
CREATE INDEX conversions_biz_idx ON conversions (business_id, occurred_at DESC);
```
(Replace the `decisions_pending_idx` predicate with whatever is actually useful; justify in DECISIONS.md.)

**Seed event types** (category, stage_key): `ad.impression`, `ad.click`, `page.view`, `form.submitted` (conversion, lead), `message.inbound`, `message.outbound`, `message.delivered`, `message.read`, `trial.booked` (conversion, trial_booked), `trial.attended` (conversion, trial_attended), `trial.no_show`, `visit.checkin`, `membership.purchased` (revenue, member), `payment.received` (revenue), `membership.renewed`, `membership.cancelled`, `consent.granted`, `consent.withdrawn`, `frontdesk.source_reported`, `system.decision_made`.

**Gym pack defaults (`packs/gym/pack.yaml`)**
- Stages and reward weights: `lead 0.5`, `trial_booked 1`, `trial_attended 3`, `member 10`, `active_90d 25`.
- Decision points: `ad_hook`, `offer`, `audience`, `send_time`, `followup_script`, `lead_first_reply`.
- Channels: `meta_ads`, `google_gbp`, `whatsapp`, `email`.
- Compliance: banned claim patterns (guaranteed results, "lose X kg in Y days", medical cure claims), quiet hours 21:00-09:00 local, WhatsApp requires opt-in.
- Seed priors for cold start (as pack data, not in the `priors` table, see 5.6).

**Acceptance**
- `docker compose up` yields a working DB; migrations apply from empty; seed creates demo business.
- **RLS test:** as `app_user` with `app.business_id=A`, every tenant table returns zero rows belonging to B, and INSERT with B's id is rejected. This must be a parametrized test over every table in the RLS list.
- Partition job creates partitions idempotently.

---

## 4. Phase 1: Ingestion, identity, consent, funnel

**Tasks**
- P1.1 **Event ingestion:** `POST /v1/events` (batch up to 500). Validates against `event_types`, requires `idempotency_key`, writes with `ON CONFLICT DO NOTHING`, returns per-item status. Auth via per-business API key (hashed in DB; add table in migration `0003`).
- P1.2 **PII service:** AES-256-GCM encrypt/decrypt for `contact_pii` and `messages.body_enc`; HMAC-SHA256 hashing with a per-tenant key derived from `TENANT_HMAC_MASTER_KEY` via HKDF(business_id). Phone numbers normalized to E.164 (default region IN) before hashing.
- P1.3 **Contact upsert:** by identifier hash; merging two contacts when one identifier links them (keep the older, re-point children, write a `contact.merged` system event; never delete event history).
- P1.4 **Identity resolution:** `identity_links` from anonymous_id to contact on form submit, WhatsApp click-to-chat code, and front-desk entry.
- P1.5 **Consent:** ledger writes, `v_consent_current` reads, STOP-keyword handling on inbound messages (configurable multilingual list: stop, unsubscribe, cancel, no more, plus Hindi/Kannada transliterations), automatic `suppressions` entry and `consent.withdrawn` event. Wire `assert_consent()` usage into the send path.
- P1.6 **Funnel derivation:** a worker that consumes new events and writes `contact_stage_history` and `conversions` according to `event_types.stage_key`. Stages only advance. `active_90d` is produced by a daily job: members with `visit.checkin` in the 30 days before day 90 and no `membership.cancelled`.
- P1.7 **Lead capture endpoints:** `POST /v1/leads` (form submission with explicit consent checkbox payload stored in `consents.evidence`), and the WhatsApp webhook (`GET` verify, `POST` receive; verify the `X-Hub-Signature-256` against `WHATSAPP_APP_SECRET`; deduplicate by message id).
- P1.8 **Tracking links:** `POST /v1/tracking-links` generating short codes (8 chars, unambiguous alphabet); public redirect route `GET /t/{code}` that logs `ad.click` with `tracking_code` and sets an `anonymous_id` cookie; QR PNG endpoint; WhatsApp deep link builder embedding the code in prefilled text.
- P1.9 **Front-desk source entry:** `POST /v1/frontdesk/events` for walk-ins: phone, "how did you hear about us", optional tracking code, creating `frontdesk.source_reported`, `trial.attended`, `membership.purchased` events.
- P1.10 **Erasure:** `DELETE /v1/contacts/{id}/pii`: delete `contact_pii`, `contact_identifiers`, `identity_links`, and message bodies for that contact; set `contacts.erased_at`; keep pseudonymous events. Write an audit entry.

**Acceptance**
- Replaying the same 500-event batch twice inserts 500 rows total.
- Webhook with a bad signature returns 401 and writes nothing.
- A lead who texts STOP is suppressed; any subsequent `send_message` action for them is blocked.
- Erasure leaves zero PII (test greps all columns of all tables for the test phone/email in plaintext and in ciphertext round-trip).
- End-to-end test: tracking link click -> form submit -> identity link -> `trial.booked` -> `membership.purchased` yields correct `contact_stage_history` and `conversions` rows.

---

## 5. Phase 2: Attribution, spend, and the learning engine

### 5.1 Attribution (`attribution/`, pure logic in `domain/attribution.py`)

For each new `conversion`, find candidate touch events for the contact (including via `identity_links` for anonymous events), then compute credit under each enabled model.

- **Touch types:** `ad.click`, `form.submitted`, `message.inbound`, `ad.impression`.
- **Lookback:** click-type 30 days, impression 7 days (configurable per business).
- **Match priority** (record in `match_method` and `confidence`):
  1. `tracking_code` (confidence 1.0)
  2. `identity_link` (confidence = link confidence)
  3. `frontdesk_self_report` (0.7) mapped from the stated source to a campaign by `tracking_links` or by a per-business source mapping table
  4. `probabilistic` geo/time match (0.3). **Implement but disabled by default** behind a flag.
- **Models to implement:** `last_touch`, `first_touch`, `position` (40/20/40). Credits per conversion sum to 1.0 (property test).
- Attribution is **recomputable**: running the job again for the same conversion replaces rows for that `(conversion_id, model)` atomically.
- Link `decision_id` from the touch event onto `attributions.decision_id` when present.

### 5.2 Spend ingestion
Connector `get_spend(day_range)` -> `spend_ledger` upserts keyed on `(campaign_id, day, source)`. A daily job per connected ad account; re-pulls the last 3 days each run because platforms revise spend.

### 5.3 Reward computation (`learning/rewards.py`)

For each decision, `reward = clip( Σ over attributed conversions ( stage.reward_weight × attribution.credit ) / max_stage_weight , 0, 1 )`.

- Only conversions attributed to that decision (via `attributions.decision_id`, or via the message/campaign linkage for message-level decisions within the decision point's `reward_window_days`).
- **Proxy vs realized:** a daily job writes `rewards` rows of kind `proxy` for open decisions, using the active `reward_models` version (weights, optionally calibrated: replace the raw stage weight with `weight × P(final success | stage)` once at least 100 resolved cases exist; store the calibration table in `reward_models.calibration`).
- When a decision's window closes, write a `realized` row with `is_final=true`.
- `rewards.value` rows are **cumulative snapshots**. The stats updater (5.5) applies **deltas**.

### 5.4 Decide API (`learning/decide.py`), the one entry point for choices

```python
def decide(
    session, *, business_id, decision_key: str, candidate_arm_ids: list[UUID],
    context: dict, contact_id: UUID | None = None, campaign_id: UUID | None = None,
    run_id: UUID | None = None, rng: np.random.Generator | None = None,
) -> Decision: ...
```

Algorithm (probability matching with an exploration floor, so the logged propensity is **exact**):
1. Pick segment key from context (`segment_key` if an `arm_stats` row exists for it with n ≥ 30 for every candidate, else `'all'`).
2. Load `(alpha, beta)` per candidate arm (create with warm-start priors if missing, see 5.6).
3. Draw `M=2000` posterior samples per arm; `p_i` = fraction of draws in which arm *i* is the maximum.
4. Mix with uniform: `p'_i = (1 - ε)·p_i + ε/K`, with `ε = 0.05` (configurable per decision point).
5. **Sample the chosen arm from the categorical distribution `p'`.** Store `propensity = p'_chosen`, `explored = (chosen != argmax p)`, the full `candidate_arm_ids`, frozen `context`, and `policy_version` (a string identifying algorithm + params + code version).
6. Insert the `decisions` row and return it.

Properties to test:
- Propensities over candidates sum to 1.
- With equal posteriors, allocation is approximately uniform; with one dominant arm, it receives about `(1-ε)+ε/K` of traffic.
- Same `rng` seed -> same decision (determinism for tests).

### 5.5 Stats updater (`learning/updater.py`), runs every 15 minutes

For each decision with a new reward row:
- `delta = latest_cumulative_value − decisions.stats_applied_reward`.
- If `stats_counted = false`: `n += 1`, `stats_counted = true`.
- Beta update with fractional reward: `alpha += delta` when `delta > 0`; when the first application is `r`, also `beta += (1 − r)`. When a later snapshot raises the value from `r0` to `r1`, apply `alpha += (r1 − r0)` and `beta −= (r1 − r0)` (floor `beta` at a small positive value).
- Update both the `'all'` row and the decision's `segment_key` row in `arm_stats`.
- Apply **time discounting** nightly: multiply `(alpha − 1)` and `(beta − 1)` by `0.995` per day to handle non-stationarity.
- Set `decisions.stats_applied_reward` to the new cumulative value. Make this one transaction per batch; safe to rerun.

### 5.6 Priors and warm starts

Two distinct mechanisms. **Do not conflate them.**

- **Within a business (across locations):** new `arm_stats` rows for a segment/location are initialized from the business's `'all'` row: `alpha0 = 1 + n0·mean`, `beta0 = 1 + n0·(1−mean)` with `n0 = 10`.
- **Cross-tenant (`priors` table):** nightly `learning_svc` job aggregates per `(scope, decision_key, arm_signature)`. A prior is **written only if contributing tenants ≥ 5** (the table's CHECK enforces it). Cap `effective_n` at 20. Output contains only aggregate parameters.
- **Single-tenant reality:** with fewer than 5 tenants the `priors` table stays empty, which is correct. Cold-start priors then come from `packs/gym/pack.yaml` (a hand-set `{arm_signature: {mean, strength}}` map). `decide()` resolves priors in this order: business `'all'` stats -> `priors` row -> pack seed prior -> uniform `Beta(1,1)`.

### 5.7 Off-policy evaluation (`learning/ope.py`)
Implement IPS and self-normalized IPS over `decisions` + final `rewards`, with a bootstrap confidence interval. Function: `evaluate_policy(candidate_policy_fn, decision_key, since) -> {value, ci_low, ci_high, effective_sample_size}`. Used by the analyst to report whether a proposed policy change would likely beat the current one. Unit-test on synthetic logged data with known ground truth.

### 5.8 Analyst insights (`agents/analyst.py` uses these)
`playbook_insights` rows are produced only from computed statistics (lift, CI, n from arm_stats/OPE). The LLM writes the wording; **it may not introduce numbers that are not in the evidence payload.** Validate: every numeric token in the statement must appear in `evidence` (or be rejected and regenerated once). Default `status='hypothesis'`; promote to `supported` only when the CI excludes zero lift with n ≥ 100 per arm. Set `expires_at` = +90 days.

**Acceptance (Phase 2)**
- Attribution credits sum to 1.0 per conversion/model (hypothesis property test, 200 examples).
- Recomputing attribution is idempotent.
- `decide()` determinism, sum-to-one, and allocation tests pass.
- Updater is idempotent: running it twice leaves `arm_stats` unchanged after the first run.
- The **simulator test (section 10)** passes its regret thresholds.

---

## 6. Phase 3: Governance (build before any real agent)

### 6.1 Action pipeline (`governance/`)
Agents call `propose_action(kind, payload, reasoning, risk_tier, idempotency_key)`, which inserts `actions(status='proposed')`. The **executor** (a worker) processes actions in this order, writing results into `policy_results` and an `audit_log` row at each step:

1. **Kill switch** (`kill_switches`, scope `all` or channel/kind) -> reject.
2. **Consent** (for sends): `assert_consent` and `suppressions` check -> reject.
3. **Quiet hours** in business timezone -> delay (reschedule), not reject.
4. **Channel rate caps** from `autonomy_policies.caps` (`daily_sends`, per-contact weekly send limit default 3) -> delay or reject.
5. **Spend caps:** daily and monthly; for `change_budget`, `max_budget_change_pct` (default 20% per action, no more than 1 change per campaign per 24h) -> reject.
6. **Claims check:** regex blocklist from the pack (deterministic) first; then an LLM brand/claims judge as a second pass (`prompts/claims_judge.md`) which can only add rejections, never override a blocklist hit. Store the judge output in `policy_results`.
7. **WhatsApp window rule:** free-form text only within 24 hours of the contact's last inbound message; otherwise require an approved template asset.
8. **Autonomy decision:** `autonomy_policies.autonomy_level` for that action kind: L1 -> always requires approval; L2 -> auto-approve if risk_tier = 1 and all checks passed; L3 -> auto-approve within caps. `requires_approval` and the resulting status must be explainable from stored `policy_results`.
9. **Execute** via the connector (honouring `DRY_RUN`/`LIVE_SENDS`), store `external_ref`, set `executed`. On failure: `failed` + `error`, with retry (3 attempts, exponential backoff) only for retryable errors. `rolled_back` supported for `pause_campaign`/`change_budget` via inverse actions.

### 6.2 Approvals
- `GET /v1/actions?status=proposed` (approval queue), `POST /v1/actions/{id}/approve|reject|edit`. Edit stores `approvals.edited_payload` and executes the edited payload.
- Default policy at business creation: **all action kinds at L1.**

### 6.3 Other
- `POST /v1/kill-switch` engage/release; engaging immediately blocks the executor and cancels queued sends. Test that a send queued before engagement is not executed after.
- `audit_log` is append-only: add triggers that raise on UPDATE/DELETE.
- Every agent run is recorded in `agent_runs` with token counts and a `trace_uri` pointing at the full trace (prompts, tool calls, outputs) in the trace store. Implement `llm/tracing.py` wrapping every LLM call.

**Acceptance**
- A table-driven test covers each policy rule with accept and reject cases, plus an ordering test (a kill switch beats everything).
- A send to a withdrawn-consent contact is blocked even when the action is manually approved.
- Budget increase over the cap is rejected; within the cap at L1 waits for approval; at L3 executes.
- Mutating `audit_log` raises.

---

## 7. Phase 4: Connectors

Define in `connectors/base.py`:

```python
class Connector(Protocol):
    provider: str
    def send_message(self, account, to, content, *, template: str | None) -> SendResult: ...
    def create_campaign(self, account, spec) -> ExternalRef: ...      # created PAUSED
    def set_budget(self, account, ref, amount_minor) -> None: ...
    def set_status(self, account, ref, status) -> None: ...
    def get_spend(self, account, day_from, day_to) -> list[SpendRow]: ...
    def get_results(self, account, ref, day_from, day_to) -> ResultRow: ...
```
(Not every connector implements every method; unsupported methods raise `NotSupported`.)

- **P4.1 `fake` connector** (deterministic, in-memory, used in all tests and in dry-run).
- **P4.2 WhatsApp Cloud API:** send text and template messages, receive webhooks, track `delivered/read` statuses into `messages` and events. Respect 24-hour rule (enforced upstream, double-checked here).
- **P4.3 Meta Marketing API:** create campaigns/ad sets/ads **in PAUSED status only**, update budgets, pull daily spend and results. Campaign objective mapped to lead generation with a click-to-WhatsApp destination carrying the tracking code. Geo-target by `locations.lat/lng` + `catchment_m`.
- **P4.4 Email (SES):** send via verified domain, handle bounce/complaint notifications into `suppressions`, include a one-click unsubscribe header and link.
- **P4.5 Google Business Profile (read-only in v1):** pull reviews into `events` (`review.received`) so the research/analyst agents can mine them. Add `review.received` to event types.

Each real connector ships with: request/response fixtures recorded from the provider docs, contract tests against the fake HTTP server (use `respx`), and a README listing the credentials and approvals required (for example WhatsApp business verification, Meta app review) **so the human knows what to set up**.

**Acceptance:** contract tests pass for each connector; in dry-run mode no outbound HTTP calls are made (assert with `respx` that none occur).

---

## 8. Phase 5: Agents

### 8.0 Agent runtime (`agents/base.py`)
`Agent.run(ctx) -> RunResult` wraps: create `agent_runs` row, set the tenant context, give the agent only these capabilities: read repositories (read-only), `decide()`, `propose_action()`, `llm.complete()`. **No direct connector access.** Every LLM call is traced. Enforce a per-run token budget and a wall-clock timeout; mark the run `failed` on exceed.

LLM contract: structured outputs via tool-use/JSON schema; validate with Pydantic; on validation failure retry once with the error message, then fail the run. All prompts live in `prompts/<agent>/<name>.md` with a version header, loaded by name; log the prompt version in the trace.

### 8.1 Lead-response agent (highest priority)
- **Trigger:** new inbound message or form lead event.
- **SLA:** first response proposed within 60 seconds of the trigger (measure and store `first_response_seconds`).
- **Behaviour:** (1) classify intent (price, schedule, trial, location, complaint, other); (2) generate a reply grounded **only** in `businesses.brand_profile` facts (prices, timings, branch addresses, trial offer). If the answer is not in the facts, say a human will follow up, and create a handoff; (3) choose the `lead_first_reply` arm via `decide()` (arms = reply styles/offers); (4) qualify goal and preferred time in at most 3 turns; (5) offer a trial slot; on acceptance emit `trial.booked`.
- **Handoff triggers:** complaint, medical/injury question, price negotiation beyond the pack's rules, explicit "talk to a person", 2 failed LLM validations. Handoff sets `conversations.status='handed_off'` and notifies the assigned user.
- Follow-up sequence for non-responders: `followup_script` decisions at +1 day and +3 days, max 2 follow-ups, never in quiet hours; STOP always wins.
- All sends go through `propose_action('send_message', ...)`.

### 8.2 Planner agent
- **Trigger:** weekly schedule, and on objective create/change.
- **Output (as `actions` + rows, never direct):** a weekly plan: proposed campaigns (`create_campaign` actions, status `pending_approval`), each with a hypothesis, budget, locations, candidate arms for hook/offer/audience; budget split across locations proportional to capacity gap and recent reward-per-rupee, with 15% always reserved for exploration.
- Must read: last 4 weeks of `v_campaign_reward_per_rupee`, active `playbook_insights` (status supported or hypothesis, not expired), objective progress, and `locations.capacity_per_day`.
- Must stay within `objectives.budget_minor` and `constraints.max_cac_minor`: the plan is invalid otherwise (validated in code, not by the LLM).

### 8.3 Ads agent
- Turns approved campaigns into connector calls (`create_campaign` PAUSED -> human or policy activates).
- Generates N creative variants per campaign as `assets` (kind `ad_creative`) with tagged `features`, runs the brand/claims check, and registers each as an arm under `ad_hook`/`offer`.
- Daily optimization: for live campaigns, calls `decide()` over active arms to set traffic/budget weights; proposes `change_budget` and `pause_campaign` actions (pause an arm only if its posterior probability of being the best < 2% and n ≥ 200).

### 8.4 Analyst agent
- **Weekly:** produce a plain-language report: spend, funnel by stage and by location, CAC, retention-weighted reward per rupee, top/bottom arms with credible intervals, speed-to-lead stats, and what changed since last week. Numbers come from SQL; the LLM only narrates (apply the same numeric-token validation as 5.8).
- Create/refresh `playbook_insights` (5.8). Mark contradicted insights `refuted`; mark expired ones `stale`.
- Run OPE for any proposed policy change and include the result.

### 8.5 Retention-lite agent
- **Triggers (daily):** new member welcome (day 0), day-3 check-in, no-visit-in-10-days nudge, trial no-show recovery within 2 hours.
- Each message type is a `decision` (script variants). Outcome reward = visit within 7 days of the message, via `visit.checkin` events, so retention also feeds the learning loop.
- Max 1 retention message per member per 3 days.

**Acceptance (Phase 5)**
- With the fake LLM and fake connectors, an integration test runs: inbound WhatsApp lead -> reply proposed < 60 s (simulated clock) -> trial booked -> membership purchased -> reward computed -> `arm_stats` updated.
- Planner output that violates the budget or CAC constraint is rejected in code (test with a deliberately violating fake LLM).
- Analyst rejects a statement containing a number absent from its evidence (test).
- No agent test ever hits the network (assert).

---

## 9. Phase 6: API and dashboard

### API (all under `/v1`, JWT auth for users, API key for ingestion)
`/businesses`, `/locations`, `/objectives`, `/campaigns`, `/assets`, `/actions` (+ approve/reject/edit), `/kill-switch`, `/reports/weekly`, `/reports/campaigns`, `/insights`, `/decisions/{id}` (full explanation: candidates, propensities, context, reward history), `/events`, `/leads`, `/frontdesk/events`, `/tracking-links`, plus webhooks. Generate OpenAPI and commit it.

### Dashboard (Next.js, four screens only)
1. **Approval queue:** pending actions with the agent's reasoning, policy results, approve/reject/edit.
2. **Performance:** funnel by location and campaign, spend, CAC, reward per rupee, trend.
3. **Learning:** per decision point, arm allocation over time and posterior intervals; playbook insights with evidence and confidence.
4. **Control:** objective editor, autonomy levels per action kind, caps, kill switch (big red button), recent audit log.

Keep it plain. No design system work. Every number links to its underlying query or record.

**Acceptance:** Playwright smoke test: log in, approve an action, see it executed (dry-run) in the audit log, engage the kill switch.

---

## 10. Simulation (mandatory; this proves the loop works)

Build `tests/simulation/` and `scripts/simulate.py`: a synthetic gym market feeding the real code paths (real `decide()`, real updater, real attribution), with the fake connectors.

**World model**
- 6 hooks × 4 offers (24 arm combinations, or treat hook and offer as two decision points), each with a hidden true "member conversion" rate (some arms near-identical, a clear best, a few harmful), plus segment effects (e.g. women 25-34 respond better to class-schedule offers).
- Funnel stochastic with realistic lags: lead -> trial booked (0-2 days), attended (2-7 days), member (up to 14 days), active_90d (90 days, simulated by clock jump).
- Lead volume 100-300/month, noise, a mid-run **regime shift** (one arm's true rate collapses at day 60) to test the discount.

**Required results (assert in CI, fixed seeds, 20 seeds each)**
- Cumulative regret of the bandit policy is at least **30% lower** than uniform random assignment after 2,000 leads (median across seeds).
- After 2,000 leads, the best arm gets at least **40%** of traffic (median).
- After the regime shift, allocation to the collapsed arm falls below 10% within 300 further leads (median).
- Warm-start with a correct prior reduces regret over the first 200 leads vs cold start; a **wrong** prior with the effective-n cap does not prevent recovery within 500 leads.
- OPE estimate of the logged policy value is within the bootstrap CI of the simulator's true value in ≥ 90% of seeds.
- Replay the entire simulation twice with the same seed -> identical final `arm_stats`.

Produce `reports/simulation.md` with plots (regret curves, allocation over time) as an artefact.

---

## 11. Security and compliance checklist (implement; the human verifies legally)

- Webhook signature verification on every inbound webhook; reject stale timestamps.
- Rate limiting on public endpoints (`/t/{code}`, `/v1/leads`, webhooks).
- Per-business API keys hashed (argon2); rotation endpoint.
- Dependency audit in CI (`pip-audit`, `npm audit`).
- Structured logs with PII redaction filter; test that phone/email patterns never appear in logs.
- Data retention config per business (default: messages 12 months, events 36 months), with a job that enforces it.
- Consent evidence stored for every opt-in; consent withdrawn within 1 minute of a STOP message.
- Document in `COMPLIANCE.md` what the system does for: DPDP Act 2023 (consent, erasure, purpose limitation), TRAI commercial-communication rules, and WhatsApp Business policies. Add a prominent note that this is engineering documentation and **not legal advice** and must be reviewed by a lawyer before production use. Do not add any scraping or bulk unsolicited messaging features.

---

## 12. Definition of done (whole project)

- [ ] `docker compose up` + `make seed` + `make demo` runs the full flow on a laptop in dry-run.
- [ ] All tests green: unit, integration, RLS, simulation. `mypy --strict`, `ruff` clean. CI green.
- [ ] Every item in the phase acceptance sections is demonstrated by a named test.
- [ ] `README.md`: setup, architecture diagram, how to add a vertical pack, how to add a connector.
- [ ] `DECISIONS.md`, `DEVIATIONS.md`, `COMPLIANCE.md`, `reports/simulation.md` present.
- [ ] Connector READMEs list the real-world accounts/approvals the human must obtain.

---

## 13. When you finish, report back with

1. A phase-by-phase checklist of what is done and what is not.
2. **Every deviation** from this file and why (`DEVIATIONS.md`).
3. Test results: counts, and the simulation numbers against the thresholds in section 10.
4. Known limitations, shortcuts, and anything you are unsure is correct.
5. Questions that need a human decision.
6. The exact commands to run the demo.

Be candid. A listed shortcut is useful; a hidden one is a defect.
