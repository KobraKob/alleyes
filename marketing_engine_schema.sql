-- =====================================================================
-- AUTONOMOUS MARKETING ENGINE: CORE SCHEMA (PostgreSQL 15+)
-- Multi-tenant, event-sourced, bandit-ready, privacy-aware.
--
-- Design rules:
--  1. Events are immutable. State is derived, never edited in place.
--  2. Every autonomous choice is logged as a DECISION with its propensity
--     (probability of being chosen), so we can do off-policy evaluation.
--  3. Rewards attach to decisions and arrive late. Provisional (proxy)
--     rewards are later superseded by realized rewards.
--  4. PII lives in one place (contact_pii) so erasure (DPDP) is one delete.
--  5. Cross-tenant learning flows only through the `priors` table:
--     aggregated parameters, k-anonymity enforced, no raw tenant data.
--  6. Money is stored in minor units (paise) as bigint. Never floats.
--  7. Every tenant table carries business_id and is protected by RLS.
-- =====================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS citext;

-- ---------------------------------------------------------------------
-- 1. TENANCY & USERS
-- ---------------------------------------------------------------------
CREATE TABLE organizations (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name        text NOT NULL,
  kind        text NOT NULL DEFAULT 'direct' CHECK (kind IN ('agency','direct')),
  created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE users (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email       citext UNIQUE NOT NULL,
  name        text,
  created_at  timestamptz NOT NULL DEFAULT now()
);

-- A "pack" encodes a vertical: funnel template, reward defaults, compliance rules.
CREATE TABLE vertical_packs (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  slug        text NOT NULL,                 -- 'gym', 'dental', 'd2c', 'b2b_saas'
  version     int  NOT NULL DEFAULT 1,
  name        text NOT NULL,
  config      jsonb NOT NULL,                -- funnel template, channels, compliance, default priors
  created_at  timestamptz NOT NULL DEFAULT now(),
  UNIQUE (slug, version)
);

-- A business is the tenant. Everything below hangs off business_id.
CREATE TABLE businesses (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id           uuid NOT NULL REFERENCES organizations(id),
  vertical_pack_id uuid NOT NULL REFERENCES vertical_packs(id),
  name             text NOT NULL,
  timezone         text NOT NULL DEFAULT 'Asia/Kolkata',
  currency         char(3) NOT NULL DEFAULT 'INR',
  brand_profile    jsonb NOT NULL DEFAULT '{}',   -- tone, USPs, banned claims, price list
  status           text NOT NULL DEFAULT 'active' CHECK (status IN ('onboarding','active','paused','churned')),
  created_at       timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE business_members (
  business_id uuid NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
  user_id     uuid NOT NULL REFERENCES users(id),
  role        text NOT NULL CHECK (role IN ('owner','manager','approver','viewer')),
  PRIMARY KEY (business_id, user_id)
);

-- Branches / outlets / clinics. Lets one tenant (3 gyms) share learning across locations.
CREATE TABLE locations (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id      uuid NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
  name             text NOT NULL,
  city             text,
  region_key       text,                         -- used as scope key for regional priors
  lat              numeric(9,6),
  lng              numeric(9,6),
  catchment_m      int DEFAULT 5000,
  capacity_per_day int,                          -- constraint for the planner
  external_refs    jsonb NOT NULL DEFAULT '{}'
);

-- ---------------------------------------------------------------------
-- 2. FUNNEL & OBJECTIVES (the funnel is DATA, not code)
-- ---------------------------------------------------------------------
CREATE TABLE funnel_stages (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id       uuid NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
  key               text NOT NULL,               -- 'lead','trial_booked','trial_attended','member','active_90d'
  label             text NOT NULL,
  ordinal           int  NOT NULL,
  reward_weight     numeric(10,4) NOT NULL DEFAULT 0,   -- contribution to the reward signal
  is_revenue_stage  boolean NOT NULL DEFAULT false,
  expected_lag_days int NOT NULL DEFAULT 0,      -- typical delay from first touch
  UNIQUE (business_id, key),
  UNIQUE (business_id, ordinal)
);

CREATE TABLE objectives (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id   uuid NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
  location_id   uuid REFERENCES locations(id),
  statement     text NOT NULL,                   -- human-readable goal
  target_stage  uuid REFERENCES funnel_stages(id),
  target_value  numeric NOT NULL,                -- e.g. 120 memberships
  period        daterange NOT NULL,
  budget_minor  bigint NOT NULL,
  constraints   jsonb NOT NULL DEFAULT '{}',     -- {"max_cac_minor": 150000, "channels": [...]}
  status        text NOT NULL DEFAULT 'active' CHECK (status IN ('draft','active','achieved','abandoned')),
  created_by    uuid REFERENCES users(id),
  created_at    timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- 3. CONTACTS, IDENTITY, CONSENT (privacy-first)
-- ---------------------------------------------------------------------
CREATE TABLE contacts (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id   uuid NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
  location_id   uuid REFERENCES locations(id),
  kind          text NOT NULL DEFAULT 'person' CHECK (kind IN ('person','company')),
  first_source  text,                            -- channel of first touch
  segment_key   text,                            -- coarse, non-PII segment e.g. 'f_25_34_near_b2'
  status        text NOT NULL DEFAULT 'lead',
  created_at    timestamptz NOT NULL DEFAULT now(),
  erased_at     timestamptz                      -- set when PII is erased; row stays for analytics
);

-- All direct PII is here and nowhere else. Erasure = delete rows here + identifiers.
CREATE TABLE contact_pii (
  contact_id   uuid PRIMARY KEY REFERENCES contacts(id) ON DELETE CASCADE,
  business_id  uuid NOT NULL,
  full_name_enc bytea,
  phone_enc     bytea,
  email_enc     bytea,
  extra_enc     bytea
);

-- Hashed identifiers for dedupe and identity resolution without exposing PII.
CREATE TABLE contact_identifiers (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id uuid NOT NULL,
  contact_id  uuid NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
  type        text NOT NULL CHECK (type IN ('phone','email','whatsapp_id','ig_handle','device','cookie','crm_id')),
  value_hash  bytea NOT NULL,                    -- HMAC-SHA256 with per-tenant key
  verified    boolean NOT NULL DEFAULT false,
  created_at  timestamptz NOT NULL DEFAULT now(),
  UNIQUE (business_id, type, value_hash)
);

-- Anonymous visitor -> known contact edges, with how sure we are.
CREATE TABLE identity_links (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id  uuid NOT NULL,
  anonymous_id text NOT NULL,
  contact_id   uuid NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
  method       text NOT NULL,                    -- 'form_submit','whatsapp_click','phone_match','frontdesk'
  confidence   numeric(4,3) NOT NULL CHECK (confidence BETWEEN 0 AND 1),
  linked_at    timestamptz NOT NULL DEFAULT now(),
  UNIQUE (business_id, anonymous_id, contact_id)
);

-- Append-only consent ledger. Current state = latest row per (contact, channel, purpose).
CREATE TABLE consents (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id uuid NOT NULL,
  contact_id  uuid NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
  channel     text NOT NULL CHECK (channel IN ('whatsapp','email','sms','call')),
  purpose     text NOT NULL DEFAULT 'marketing',
  status      text NOT NULL CHECK (status IN ('granted','withdrawn')),
  source      text NOT NULL,                     -- 'lead_form','whatsapp_optin','frontdesk','stop_keyword'
  evidence    jsonb NOT NULL DEFAULT '{}',       -- form id, timestamp, text shown, IP
  occurred_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE suppressions (
  business_id uuid NOT NULL,
  channel     text NOT NULL,
  value_hash  bytea NOT NULL,
  reason      text NOT NULL,                     -- 'opt_out','complaint','dnd_registry','bounced'
  created_at  timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (business_id, channel, value_hash)
);

-- ---------------------------------------------------------------------
-- 4. CAMPAIGNS, ASSETS, TRACKING
-- ---------------------------------------------------------------------
CREATE TABLE connector_accounts (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id         uuid NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
  provider            text NOT NULL,             -- 'meta','google_ads','gbp','whatsapp','ses','shopify'
  external_account_id text NOT NULL,
  credentials_ref     text NOT NULL,             -- pointer into a secrets manager. NEVER store tokens here.
  scopes              text[],
  status              text NOT NULL DEFAULT 'active',
  last_sync_at        timestamptz,
  UNIQUE (business_id, provider, external_account_id)
);

CREATE TABLE assets (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id     uuid NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
  kind            text NOT NULL,                 -- 'ad_creative','email','wa_template','reel_script','landing_page'
  title           text,
  content         jsonb NOT NULL,
  features        jsonb NOT NULL DEFAULT '{}',   -- tagged attributes: hook_type, offer_type, tone, has_face
  embedding       vector(1536),
  generated_by    text NOT NULL DEFAULT 'agent', -- 'agent' | 'human'
  parent_asset_id uuid REFERENCES assets(id),    -- lineage for iterative improvement
  brand_check     jsonb,                         -- policy/brand validation result
  status          text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','approved','live','retired','rejected')),
  created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE campaigns (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id   uuid NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
  objective_id  uuid REFERENCES objectives(id),
  location_id   uuid REFERENCES locations(id),
  channel       text NOT NULL,
  name          text NOT NULL,
  hypothesis    text,                            -- why the agent thinks this will work
  status        text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','pending_approval','live','paused','ended')),
  budget_minor  bigint NOT NULL DEFAULT 0,
  starts_at     timestamptz,
  ends_at       timestamptz,
  external_ref  text,                            -- id on Meta/Google/etc.
  created_by_run uuid,                           -- FK added after agent_runs
  created_at    timestamptz NOT NULL DEFAULT now()
);

-- Every QR code, trial link, call number, and WhatsApp deep link maps to a campaign.
CREATE TABLE tracking_links (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id uuid NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
  campaign_id uuid REFERENCES campaigns(id),
  asset_id    uuid REFERENCES assets(id),
  location_id uuid REFERENCES locations(id),
  code        text NOT NULL UNIQUE,              -- short code embedded in URL/QR/WA message
  kind        text NOT NULL CHECK (kind IN ('url','qr','phone','whatsapp','coupon','frontdesk_code')),
  destination text,
  created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE spend_ledger (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id uuid NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
  campaign_id uuid NOT NULL REFERENCES campaigns(id),
  day         date NOT NULL,
  amount_minor bigint NOT NULL CHECK (amount_minor >= 0),
  source      text NOT NULL DEFAULT 'platform_api',
  reported_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (campaign_id, day, source)
);

-- ---------------------------------------------------------------------
-- 5. GOVERNANCE (agents, actions, approvals) - defined before decisions
-- ---------------------------------------------------------------------
CREATE TABLE agent_runs (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id  uuid NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
  agent        text NOT NULL,                    -- 'planner','ads','lead_response','analyst',...
  trigger      text NOT NULL,                    -- 'schedule','event','human','agent'
  objective_id uuid REFERENCES objectives(id),
  model        text,
  started_at   timestamptz NOT NULL DEFAULT now(),
  finished_at  timestamptz,
  status       text NOT NULL DEFAULT 'running' CHECK (status IN ('running','succeeded','failed','cancelled')),
  tokens_in    int,
  tokens_out   int,
  cost_minor   bigint,
  trace_uri    text                              -- full prompt/tool trace stored in object storage
);
ALTER TABLE campaigns ADD CONSTRAINT campaigns_run_fk FOREIGN KEY (created_by_run) REFERENCES agent_runs(id);

-- Everything an agent wants to DO goes through here first.
CREATE TABLE actions (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id      uuid NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
  run_id           uuid REFERENCES agent_runs(id),
  kind             text NOT NULL,                -- 'send_message','publish_post','create_campaign','change_budget','pause_campaign'
  payload          jsonb NOT NULL,
  risk_tier        smallint NOT NULL DEFAULT 1 CHECK (risk_tier BETWEEN 1 AND 3),
  requires_approval boolean NOT NULL DEFAULT true,
  status           text NOT NULL DEFAULT 'proposed'
                   CHECK (status IN ('proposed','approved','rejected','executed','failed','rolled_back')),
  reasoning        text,                         -- the agent's explanation, shown to humans
  policy_results   jsonb NOT NULL DEFAULT '{}',  -- caps, consent, brand, claims checks
  idempotency_key  text NOT NULL,
  proposed_at      timestamptz NOT NULL DEFAULT now(),
  executed_at      timestamptz,
  external_ref     text,
  error            text,
  UNIQUE (business_id, idempotency_key)
);

CREATE TABLE approvals (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id uuid NOT NULL,
  action_id   uuid NOT NULL REFERENCES actions(id) ON DELETE CASCADE,
  approver_id uuid NOT NULL REFERENCES users(id),
  decision    text NOT NULL CHECK (decision IN ('approved','rejected','edited')),
  comment     text,
  edited_payload jsonb,                          -- human edits are training signal
  decided_at  timestamptz NOT NULL DEFAULT now()
);

-- What each action type may do autonomously, per business.
CREATE TABLE autonomy_policies (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id    uuid NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
  action_kind    text NOT NULL,
  autonomy_level smallint NOT NULL DEFAULT 1 CHECK (autonomy_level BETWEEN 1 AND 3),
  caps           jsonb NOT NULL DEFAULT '{}',    -- {"daily_spend_minor":..., "max_budget_change_pct":20, "daily_sends":200}
  effective_from timestamptz NOT NULL DEFAULT now(),
  UNIQUE (business_id, action_kind, effective_from)
);

CREATE TABLE kill_switches (
  business_id uuid NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
  scope       text NOT NULL DEFAULT 'all',       -- 'all' or a channel/action_kind
  engaged     boolean NOT NULL DEFAULT false,
  engaged_by  uuid REFERENCES users(id),
  reason      text,
  changed_at  timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (business_id, scope)
);

CREATE TABLE audit_log (
  id          bigserial PRIMARY KEY,
  business_id uuid,
  actor_kind  text NOT NULL,                     -- 'user','agent','system'
  actor_id    text,
  action      text NOT NULL,
  entity_type text,
  entity_id   text,
  diff        jsonb,
  at          timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- 6. LEARNING LAYER: decisions, rewards, arms, priors, playbook
-- ---------------------------------------------------------------------
-- A decision point is a repeatable choice the system optimizes.
CREATE TABLE decision_points (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  key               text NOT NULL,               -- 'ad_hook','offer','send_time','followup_script','audience'
  business_id       uuid REFERENCES businesses(id) ON DELETE CASCADE,  -- NULL = global template
  description       text,
  context_schema    jsonb NOT NULL DEFAULT '{}', -- which context features the policy may use
  algorithm         text NOT NULL DEFAULT 'thompson_beta'
                    CHECK (algorithm IN ('thompson_beta','thompson_gaussian','linear_ts','epsilon_greedy')),
  reward_window_days int NOT NULL DEFAULT 14,    -- how long to wait before treating reward as final
  UNIQUE NULLS NOT DISTINCT (business_id, key)
);

-- An arm is one option: a specific hook, offer, subject line, send slot...
CREATE TABLE arms (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id       uuid NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
  decision_point_id uuid NOT NULL REFERENCES decision_points(id),
  asset_id          uuid REFERENCES assets(id),
  label             text NOT NULL,
  signature         text NOT NULL,               -- canonical, tenant-neutral key e.g. 'offer:free_trial_7d'
                                                 -- links arms to cross-tenant priors
  params            jsonb NOT NULL DEFAULT '{}',
  status            text NOT NULL DEFAULT 'candidate' CHECK (status IN ('candidate','active','retired')),
  created_by        text NOT NULL DEFAULT 'agent',
  created_at        timestamptz NOT NULL DEFAULT now()
);

-- THE KEY TABLE. One row per autonomous choice, with the propensity logged.
-- Without propensity you cannot evaluate new policies offline.
CREATE TABLE decisions (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id       uuid NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
  decision_point_id uuid NOT NULL REFERENCES decision_points(id),
  chosen_arm_id     uuid NOT NULL REFERENCES arms(id),
  candidate_arm_ids uuid[] NOT NULL,             -- the arms that were available
  propensity        numeric(8,7) NOT NULL CHECK (propensity > 0 AND propensity <= 1),
  explored          boolean NOT NULL,            -- true if not the greedy choice
  policy_version    text NOT NULL,
  context           jsonb NOT NULL DEFAULT '{}', -- features at decision time (frozen)
  contact_id        uuid REFERENCES contacts(id) ON DELETE SET NULL,
  campaign_id       uuid REFERENCES campaigns(id),
  run_id            uuid REFERENCES agent_runs(id),
  action_id         uuid REFERENCES actions(id),
  decided_at        timestamptz NOT NULL DEFAULT now()
);

-- Rewards arrive in stages: provisional proxy first, realized later.
CREATE TABLE rewards (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id  uuid NOT NULL,
  decision_id  uuid NOT NULL REFERENCES decisions(id) ON DELETE CASCADE,
  kind         text NOT NULL CHECK (kind IN ('proxy','realized')),
  value        numeric(12,4) NOT NULL,           -- normalized reward, typically 0..1
  components   jsonb NOT NULL DEFAULT '{}',      -- {"trial_attended":3,"member":10}
  reward_model_id uuid,                          -- which calibration produced a proxy
  is_final     boolean NOT NULL DEFAULT false,
  observed_at  timestamptz NOT NULL DEFAULT now()
);

-- Posterior state per arm per segment (the "live" bandit).
CREATE TABLE arm_stats (
  arm_id       uuid NOT NULL REFERENCES arms(id) ON DELETE CASCADE,
  business_id  uuid NOT NULL,
  segment_key  text NOT NULL DEFAULT 'all',
  alpha        numeric(14,4) NOT NULL DEFAULT 1,  -- Beta posterior (successes + prior)
  beta         numeric(14,4) NOT NULL DEFAULT 1,  -- Beta posterior (failures + prior)
  n            int NOT NULL DEFAULT 0,
  reward_sum   numeric(16,4) NOT NULL DEFAULT 0,
  reward_m2    numeric(18,6) NOT NULL DEFAULT 0,  -- for Gaussian variants (Welford)
  updated_at   timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (arm_id, segment_key)
);

CREATE TABLE reward_models (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id   uuid REFERENCES businesses(id) ON DELETE CASCADE,  -- NULL = vertical default
  version       int NOT NULL,
  proxy_weights jsonb NOT NULL,                  -- stage -> weight actually used
  calibration   jsonb NOT NULL DEFAULT '{}',     -- P(member | trial_attended) etc., learned
  metrics       jsonb NOT NULL DEFAULT '{}',
  trained_at    timestamptz NOT NULL DEFAULT now(),
  UNIQUE NULLS NOT DISTINCT (business_id, version)
);

-- CROSS-TENANT PRIORS. Aggregated parameters only; no business_id, no raw rows.
-- k-anonymity: a prior may only be published if enough tenants contributed.
CREATE TABLE priors (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  scope_level         text NOT NULL CHECK (scope_level IN ('global','vertical','region','segment')),
  scope_key           text NOT NULL,             -- 'gym', 'gym:bengaluru', 'gym:bengaluru:f_25_34'
  decision_key        text NOT NULL,
  arm_signature       text NOT NULL,
  alpha               numeric(14,4) NOT NULL,
  beta                numeric(14,4) NOT NULL,
  effective_n         numeric(14,2) NOT NULL,    -- capped so priors never overwhelm local data
  contributing_tenants int NOT NULL CHECK (contributing_tenants >= 5),
  updated_at          timestamptz NOT NULL DEFAULT now(),
  UNIQUE (scope_level, scope_key, decision_key, arm_signature)
);

-- Qualitative learnings written by the analyst agent, with evidence attached.
CREATE TABLE playbook_insights (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id   uuid NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
  statement     text NOT NULL,                   -- "7-day trial + class schedule beats discounts for women 25-34"
  evidence      jsonb NOT NULL,                  -- {"decision_ids":[...],"n":412,"lift":0.31,"ci":[0.12,0.49]}
  confidence    numeric(4,3) NOT NULL CHECK (confidence BETWEEN 0 AND 1),
  status        text NOT NULL DEFAULT 'hypothesis'
                CHECK (status IN ('hypothesis','supported','refuted','stale')),
  embedding     vector(1536),
  run_id        uuid REFERENCES agent_runs(id),
  superseded_by uuid REFERENCES playbook_insights(id),
  expires_at    timestamptz,                     -- insights decay; re-test before trusting forever
  created_at    timestamptz NOT NULL DEFAULT now()
);

-- Strategy-level (slow loop) experiments that bandits do not cover.
CREATE TABLE experiments (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id uuid NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
  hypothesis  text NOT NULL,
  design      jsonb NOT NULL,                    -- arms, allocation, holdout, success metric
  status      text NOT NULL DEFAULT 'planned' CHECK (status IN ('planned','running','concluded','aborted')),
  result      jsonb,
  starts_at   timestamptz,
  ends_at     timestamptz
);

-- ---------------------------------------------------------------------
-- 7. CONVERSATIONS
-- ---------------------------------------------------------------------
CREATE TABLE conversations (
  id                     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id            uuid NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
  contact_id             uuid NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
  channel                text NOT NULL,
  status                 text NOT NULL DEFAULT 'open' CHECK (status IN ('open','waiting','handed_off','closed')),
  first_inbound_at       timestamptz,
  first_response_at      timestamptz,
  first_response_seconds int GENERATED ALWAYS AS
      (CASE WHEN first_response_at IS NOT NULL AND first_inbound_at IS NOT NULL
            THEN EXTRACT(EPOCH FROM (first_response_at - first_inbound_at))::int END) STORED,
  handed_off_to          uuid REFERENCES users(id),
  created_at             timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE messages (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id     uuid NOT NULL,
  conversation_id uuid NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  direction       text NOT NULL CHECK (direction IN ('inbound','outbound')),
  sender_kind     text NOT NULL CHECK (sender_kind IN ('contact','agent','human')),
  body_enc        bytea,                         -- message text encrypted (may contain PII)
  template_id     uuid REFERENCES assets(id),
  decision_id     uuid REFERENCES decisions(id), -- links a message to the choice that produced it
  external_id     text,
  sent_at         timestamptz NOT NULL DEFAULT now(),
  delivered_at    timestamptz,
  read_at         timestamptz
);

-- ---------------------------------------------------------------------
-- 8. THE EVENT LOG (immutable, partitioned by time)
-- ---------------------------------------------------------------------
CREATE TABLE event_types (
  key          text PRIMARY KEY,                 -- 'ad.impression','form.submitted','trial.booked','visit.checkin','payment.received'
  category     text NOT NULL CHECK (category IN ('exposure','engagement','conversion','revenue','system')),
  stage_key    text,                             -- if this event moves a contact into a funnel stage
  schema       jsonb NOT NULL DEFAULT '{}'
);

CREATE TABLE events (
  id              uuid NOT NULL DEFAULT gen_random_uuid(),
  business_id     uuid NOT NULL,
  event_type      text NOT NULL REFERENCES event_types(key),
  occurred_at     timestamptz NOT NULL,          -- when it happened in the real world
  recorded_at     timestamptz NOT NULL DEFAULT now(), -- when we learned of it (late data is normal)
  contact_id      uuid,
  anonymous_id    text,
  location_id     uuid,
  campaign_id     uuid,
  asset_id        uuid,
  decision_id     uuid,
  tracking_code   text,
  source          text NOT NULL,                 -- 'meta_api','whatsapp_webhook','frontdesk','crm_sync','system'
  properties      jsonb NOT NULL DEFAULT '{}',
  value_minor     bigint,
  idempotency_key text NOT NULL,
  PRIMARY KEY (id, occurred_at),
  UNIQUE (business_id, idempotency_key, occurred_at)
) PARTITION BY RANGE (occurred_at);

-- Create monthly partitions with pg_partman in production. Example:
CREATE TABLE events_2026_10 PARTITION OF events
  FOR VALUES FROM ('2026-10-01') TO ('2026-11-01');

CREATE INDEX events_contact_idx  ON events (business_id, contact_id, occurred_at DESC);
CREATE INDEX events_campaign_idx ON events (business_id, campaign_id, occurred_at DESC);
CREATE INDEX events_type_idx     ON events (business_id, event_type, occurred_at DESC);
CREATE INDEX events_anon_idx     ON events (business_id, anonymous_id) WHERE anonymous_id IS NOT NULL;
CREATE INDEX events_code_idx     ON events (tracking_code) WHERE tracking_code IS NOT NULL;

-- ---------------------------------------------------------------------
-- 9. FUNNEL STATE & ATTRIBUTION (derived from events)
-- ---------------------------------------------------------------------
-- Stage history per contact. A contact can only advance; regressions (churn) are separate events.
CREATE TABLE contact_stage_history (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id uuid NOT NULL,
  contact_id  uuid NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
  stage_id    uuid NOT NULL REFERENCES funnel_stages(id),
  entered_at  timestamptz NOT NULL,
  source_event_id uuid,                          -- the event that caused it (no FK: partitioned table)
  UNIQUE (contact_id, stage_id)
);

CREATE TABLE conversions (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id     uuid NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
  contact_id      uuid NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
  stage_id        uuid NOT NULL REFERENCES funnel_stages(id),
  occurred_at     timestamptz NOT NULL,
  value_minor     bigint NOT NULL DEFAULT 0,
  verified        boolean NOT NULL DEFAULT false,
  verified_by     text,                          -- 'crm_sync','frontdesk','payment_gateway'
  source_event_id uuid,
  UNIQUE (contact_id, stage_id)
);

-- Credit assignment. Multiple models can coexist so we can compare them.
CREATE TABLE attributions (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id    uuid NOT NULL,
  conversion_id  uuid NOT NULL REFERENCES conversions(id) ON DELETE CASCADE,
  touch_event_id uuid NOT NULL,                  -- no FK: events is partitioned
  campaign_id    uuid REFERENCES campaigns(id),
  asset_id       uuid REFERENCES assets(id),
  decision_id    uuid REFERENCES decisions(id),
  model          text NOT NULL,                  -- 'last_touch','first_touch','position','data_driven_v1'
  credit         numeric(5,4) NOT NULL CHECK (credit BETWEEN 0 AND 1),
  match_method   text NOT NULL,                  -- 'tracking_code','identity_link','probabilistic','frontdesk_self_report'
  confidence     numeric(4,3) NOT NULL,
  computed_at    timestamptz NOT NULL DEFAULT now(),
  UNIQUE (conversion_id, touch_event_id, model)
);

-- ---------------------------------------------------------------------
-- 10. VIEWS
-- ---------------------------------------------------------------------
CREATE VIEW v_consent_current AS
SELECT DISTINCT ON (contact_id, channel, purpose)
       business_id, contact_id, channel, purpose, status, occurred_at
FROM consents
ORDER BY contact_id, channel, purpose, occurred_at DESC;

CREATE VIEW v_contact_stage AS
SELECT DISTINCT ON (h.contact_id)
       h.business_id, h.contact_id, s.key AS stage_key, s.ordinal, h.entered_at
FROM contact_stage_history h
JOIN funnel_stages s ON s.id = h.stage_id
ORDER BY h.contact_id, s.ordinal DESC;

CREATE VIEW v_campaign_funnel AS
SELECT a.business_id, a.campaign_id, fs.key AS stage_key,
       COUNT(DISTINCT cv.contact_id)           AS contacts,
       SUM(cv.value_minor * a.credit)          AS credited_value_minor,
       SUM(fs.reward_weight * a.credit)        AS credited_reward
FROM attributions a
JOIN conversions   cv ON cv.id = a.conversion_id
JOIN funnel_stages fs ON fs.id = cv.stage_id
WHERE a.model = 'last_touch'                     -- switch per business as the attribution model matures
GROUP BY a.business_id, a.campaign_id, fs.key;

-- The headline metric: retention-weighted reward per rupee spent.
CREATE VIEW v_campaign_reward_per_rupee AS
WITH r AS (SELECT campaign_id, SUM(credited_reward) AS reward
           FROM v_campaign_funnel GROUP BY campaign_id),
     s AS (SELECT campaign_id, SUM(amount_minor) AS spend_minor
           FROM spend_ledger GROUP BY campaign_id)
SELECT c.business_id, c.id AS campaign_id, c.name,
       COALESCE(r.reward, 0)        AS reward,
       COALESCE(s.spend_minor, 0)   AS spend_minor,
       CASE WHEN COALESCE(s.spend_minor, 0) > 0
            THEN COALESCE(r.reward, 0) / (s.spend_minor / 100.0) END AS reward_per_rupee
FROM campaigns c
LEFT JOIN r ON r.campaign_id = c.id
LEFT JOIN s ON s.campaign_id = c.id;

-- ---------------------------------------------------------------------
-- 11. ROW-LEVEL SECURITY (tenant isolation)
-- The app sets: SET app.business_id = '<uuid>' per request/job.
-- `priors` has no business_id and is readable only by the learning service role.
-- ---------------------------------------------------------------------
DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY[
    'locations','funnel_stages','objectives','contacts','contact_pii','contact_identifiers',
    'identity_links','consents','suppressions','connector_accounts','assets','campaigns',
    'tracking_links','spend_ledger','agent_runs','actions','approvals','autonomy_policies',
    'kill_switches','decision_points','arms','decisions','rewards','arm_stats','reward_models',
    'playbook_insights','experiments','conversations','messages','events',
    'contact_stage_history','conversions','attributions'
  ] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', t);
    EXECUTE format(
      'CREATE POLICY tenant_isolation ON %I USING (business_id = current_setting(''app.business_id'', true)::uuid)',
      t);
  END LOOP;
END $$;

-- ---------------------------------------------------------------------
-- 12. GUARDRAIL: hard-block sends to anyone without current consent
-- (enforced again in application code; the DB is the last line of defence)
-- ---------------------------------------------------------------------
CREATE FUNCTION assert_consent(p_contact uuid, p_channel text) RETURNS void AS $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM v_consent_current
    WHERE contact_id = p_contact AND channel = p_channel
      AND purpose = 'marketing' AND status = 'granted'
  ) THEN
    RAISE EXCEPTION 'No valid marketing consent for contact % on %', p_contact, p_channel;
  END IF;
END $$ LANGUAGE plpgsql STABLE;
