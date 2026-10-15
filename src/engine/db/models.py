"""SQLAlchemy 2.0 Table definitions matching core schema verbatim."""

from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    MetaData,
    Numeric,
    PrimaryKeyConstraint,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

metadata = MetaData()

organizations = Table(
    "organizations",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()),
    Column("name", Text, nullable=False),
    Column("kind", Text, nullable=False, server_default="direct"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

users = Table(
    "users",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()),
    Column("email", Text, unique=True, nullable=False),
    Column("name", Text),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

vertical_packs = Table(
    "vertical_packs",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()),
    Column("slug", Text, nullable=False),
    Column("version", Integer, nullable=False, server_default="1"),
    Column("name", Text, nullable=False),
    Column("config", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("slug", "version"),
)

businesses = Table(
    "businesses",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()),
    Column("org_id", UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False),
    Column("vertical_pack_id", UUID(as_uuid=True), ForeignKey("vertical_packs.id"), nullable=False),
    Column("name", Text, nullable=False),
    Column("timezone", Text, nullable=False, server_default="Asia/Kolkata"),
    Column("currency", String(3), nullable=False, server_default="INR"),
    Column("brand_profile", JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    Column("status", Text, nullable=False, server_default="active"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

business_members = Table(
    "business_members",
    metadata,
    Column(
        "business_id",
        UUID(as_uuid=True),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id"), nullable=False),
    Column("role", Text, nullable=False),
    PrimaryKeyConstraint("business_id", "user_id"),
)

locations = Table(
    "locations",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()),
    Column(
        "business_id",
        UUID(as_uuid=True),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("name", Text, nullable=False),
    Column("city", Text),
    Column("region_key", Text),
    Column("lat", Numeric(9, 6)),
    Column("lng", Numeric(9, 6)),
    Column("catchment_m", Integer, server_default="5000"),
    Column("capacity_per_day", Integer),
    Column("external_refs", JSONB, nullable=False, server_default=text("'{}'::jsonb")),
)

funnel_stages = Table(
    "funnel_stages",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()),
    Column(
        "business_id",
        UUID(as_uuid=True),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("key", Text, nullable=False),
    Column("label", Text, nullable=False),
    Column("ordinal", Integer, nullable=False),
    Column("reward_weight", Numeric(10, 4), nullable=False, server_default="0"),
    Column("is_revenue_stage", Boolean, nullable=False, server_default="false"),
    Column("expected_lag_days", Integer, nullable=False, server_default="0"),
    UniqueConstraint("business_id", "key"),
    UniqueConstraint("business_id", "ordinal"),
)

objectives = Table(
    "objectives",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()),
    Column(
        "business_id",
        UUID(as_uuid=True),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("location_id", UUID(as_uuid=True), ForeignKey("locations.id")),
    Column("statement", Text, nullable=False),
    Column("target_stage", UUID(as_uuid=True), ForeignKey("funnel_stages.id")),
    Column("target_value", Numeric, nullable=False),
    Column("budget_minor", BigInteger, nullable=False),
    Column("constraints", JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    Column("status", Text, nullable=False, server_default="active"),
    Column("created_by", UUID(as_uuid=True), ForeignKey("users.id")),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

contacts = Table(
    "contacts",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()),
    Column(
        "business_id",
        UUID(as_uuid=True),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("location_id", UUID(as_uuid=True), ForeignKey("locations.id")),
    Column("kind", Text, nullable=False, server_default="person"),
    Column("first_source", Text),
    Column("segment_key", Text),
    Column("status", Text, nullable=False, server_default="lead"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("erased_at", DateTime(timezone=True)),
)

contact_pii = Table(
    "contact_pii",
    metadata,
    Column(
        "contact_id",
        UUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("business_id", UUID(as_uuid=True), nullable=False),
    Column("full_name_enc", LargeBinary),
    Column("phone_enc", LargeBinary),
    Column("email_enc", LargeBinary),
    Column("extra_enc", LargeBinary),
)

contact_identifiers = Table(
    "contact_identifiers",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()),
    Column("business_id", UUID(as_uuid=True), nullable=False),
    Column(
        "contact_id",
        UUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("type", Text, nullable=False),
    Column("value_hash", LargeBinary, nullable=False),
    Column("verified", Boolean, nullable=False, server_default="false"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("business_id", "type", "value_hash"),
)

identity_links = Table(
    "identity_links",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()),
    Column("business_id", UUID(as_uuid=True), nullable=False),
    Column("anonymous_id", Text, nullable=False),
    Column(
        "contact_id",
        UUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("method", Text, nullable=False),
    Column("confidence", Numeric(4, 3), nullable=False),
    Column("linked_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("business_id", "anonymous_id", "contact_id"),
)

consents = Table(
    "consents",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()),
    Column("business_id", UUID(as_uuid=True), nullable=False),
    Column(
        "contact_id",
        UUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("channel", Text, nullable=False),
    Column("purpose", Text, nullable=False, server_default="marketing"),
    Column("status", Text, nullable=False),
    Column("source", Text, nullable=False),
    Column("evidence", JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    Column("occurred_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

suppressions = Table(
    "suppressions",
    metadata,
    Column("business_id", UUID(as_uuid=True), nullable=False),
    Column("channel", Text, nullable=False),
    Column("value_hash", LargeBinary, nullable=False),
    Column("reason", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    PrimaryKeyConstraint("business_id", "channel", "value_hash"),
)

connector_accounts = Table(
    "connector_accounts",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()),
    Column(
        "business_id",
        UUID(as_uuid=True),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("provider", Text, nullable=False),
    Column("external_account_id", Text, nullable=False),
    Column("credentials_ref", Text, nullable=False),
    Column("scopes", ARRAY(Text)),
    Column("status", Text, nullable=False, server_default="active"),
    Column("last_sync_at", DateTime(timezone=True)),
    UniqueConstraint("business_id", "provider", "external_account_id"),
)

assets = Table(
    "assets",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()),
    Column(
        "business_id",
        UUID(as_uuid=True),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("kind", Text, nullable=False),
    Column("title", Text),
    Column("content", JSONB, nullable=False),
    Column("features", JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    Column("generated_by", Text, nullable=False, server_default="agent"),
    Column("parent_asset_id", UUID(as_uuid=True), ForeignKey("assets.id")),
    Column("brand_check", JSONB),
    Column("status", Text, nullable=False, server_default="draft"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

agent_runs = Table(
    "agent_runs",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()),
    Column(
        "business_id",
        UUID(as_uuid=True),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("agent", Text, nullable=False),
    Column("trigger", Text, nullable=False),
    Column("objective_id", UUID(as_uuid=True), ForeignKey("objectives.id")),
    Column("model", Text),
    Column("started_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("finished_at", DateTime(timezone=True)),
    Column("status", Text, nullable=False, server_default="running"),
    Column("tokens_in", Integer),
    Column("tokens_out", Integer),
    Column("cost_minor", BigInteger),
    Column("trace_uri", Text),
)

campaigns = Table(
    "campaigns",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()),
    Column(
        "business_id",
        UUID(as_uuid=True),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("objective_id", UUID(as_uuid=True), ForeignKey("objectives.id")),
    Column("location_id", UUID(as_uuid=True), ForeignKey("locations.id")),
    Column("channel", Text, nullable=False),
    Column("name", Text, nullable=False),
    Column("hypothesis", Text),
    Column("status", Text, nullable=False, server_default="draft"),
    Column("budget_minor", BigInteger, nullable=False, server_default="0"),
    Column("starts_at", DateTime(timezone=True)),
    Column("ends_at", DateTime(timezone=True)),
    Column("external_ref", Text),
    Column("created_by_run", UUID(as_uuid=True), ForeignKey("agent_runs.id")),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

tracking_links = Table(
    "tracking_links",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()),
    Column(
        "business_id",
        UUID(as_uuid=True),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("campaign_id", UUID(as_uuid=True), ForeignKey("campaigns.id")),
    Column("asset_id", UUID(as_uuid=True), ForeignKey("assets.id")),
    Column("location_id", UUID(as_uuid=True), ForeignKey("locations.id")),
    Column("code", Text, nullable=False, unique=True),
    Column("kind", Text, nullable=False),
    Column("destination", Text),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

spend_ledger = Table(
    "spend_ledger",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()),
    Column(
        "business_id",
        UUID(as_uuid=True),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("campaign_id", UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False),
    Column("day", DateTime, nullable=False),
    Column("amount_minor", BigInteger, nullable=False),
    Column("source", Text, nullable=False, server_default="platform_api"),
    Column("reported_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("campaign_id", "day", "source"),
)

actions = Table(
    "actions",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()),
    Column(
        "business_id",
        UUID(as_uuid=True),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("run_id", UUID(as_uuid=True), ForeignKey("agent_runs.id")),
    Column("kind", Text, nullable=False),
    Column("payload", JSONB, nullable=False),
    Column("risk_tier", Integer, nullable=False, server_default="1"),
    Column("requires_approval", Boolean, nullable=False, server_default="true"),
    Column("status", Text, nullable=False, server_default="proposed"),
    Column("reasoning", Text),
    Column("policy_results", JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    Column("idempotency_key", Text, nullable=False),
    Column("proposed_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("executed_at", DateTime(timezone=True)),
    Column("external_ref", Text),
    Column("error", Text),
    UniqueConstraint("business_id", "idempotency_key"),
)

approvals = Table(
    "approvals",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()),
    Column("business_id", UUID(as_uuid=True), nullable=False),
    Column(
        "action_id",
        UUID(as_uuid=True),
        ForeignKey("actions.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("approver_id", UUID(as_uuid=True), ForeignKey("users.id"), nullable=False),
    Column("decision", Text, nullable=False),
    Column("comment", Text),
    Column("edited_payload", JSONB),
    Column("decided_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

autonomy_policies = Table(
    "autonomy_policies",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()),
    Column(
        "business_id",
        UUID(as_uuid=True),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("action_kind", Text, nullable=False),
    Column("autonomy_level", Integer, nullable=False, server_default="1"),
    Column("caps", JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    Column("effective_from", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("business_id", "action_kind", "effective_from"),
)

kill_switches = Table(
    "kill_switches",
    metadata,
    Column(
        "business_id",
        UUID(as_uuid=True),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("scope", Text, nullable=False, server_default="all"),
    Column("engaged", Boolean, nullable=False, server_default="false"),
    Column("engaged_by", UUID(as_uuid=True), ForeignKey("users.id")),
    Column("reason", Text),
    Column("changed_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    PrimaryKeyConstraint("business_id", "scope"),
)

audit_log = Table(
    "audit_log",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("business_id", UUID(as_uuid=True)),
    Column("actor_kind", Text, nullable=False),
    Column("actor_id", Text),
    Column("action", Text, nullable=False),
    Column("entity_type", Text),
    Column("entity_id", Text),
    Column("diff", JSONB),
    Column("at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

decision_points = Table(
    "decision_points",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()),
    Column("key", Text, nullable=False),
    Column("business_id", UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE")),
    Column("description", Text),
    Column("context_schema", JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    Column("algorithm", Text, nullable=False, server_default="thompson_beta"),
    Column("reward_window_days", Integer, nullable=False, server_default="14"),
)

arms = Table(
    "arms",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()),
    Column(
        "business_id",
        UUID(as_uuid=True),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "decision_point_id", UUID(as_uuid=True), ForeignKey("decision_points.id"), nullable=False
    ),
    Column("asset_id", UUID(as_uuid=True), ForeignKey("assets.id")),
    Column("label", Text, nullable=False),
    Column("signature", Text, nullable=False),
    Column("params", JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    Column("status", Text, nullable=False, server_default="candidate"),
    Column("created_by", Text, nullable=False, server_default="agent"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

decisions = Table(
    "decisions",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()),
    Column(
        "business_id",
        UUID(as_uuid=True),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "decision_point_id", UUID(as_uuid=True), ForeignKey("decision_points.id"), nullable=False
    ),
    Column("chosen_arm_id", UUID(as_uuid=True), ForeignKey("arms.id"), nullable=False),
    Column("candidate_arm_ids", ARRAY(UUID(as_uuid=True)), nullable=False),
    Column("propensity", Numeric(8, 7), nullable=False),
    Column("explored", Boolean, nullable=False),
    Column("policy_version", Text, nullable=False),
    Column("context", JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    Column("contact_id", UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="SET NULL")),
    Column("campaign_id", UUID(as_uuid=True), ForeignKey("campaigns.id")),
    Column("run_id", UUID(as_uuid=True), ForeignKey("agent_runs.id")),
    Column("action_id", UUID(as_uuid=True), ForeignKey("actions.id")),
    Column("decided_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    # Added via migration 0002
    Column("stats_applied_reward", Numeric(12, 4), nullable=False, server_default="0"),
    Column("stats_counted", Boolean, nullable=False, server_default="false"),
)

rewards = Table(
    "rewards",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()),
    Column("business_id", UUID(as_uuid=True), nullable=False),
    Column(
        "decision_id",
        UUID(as_uuid=True),
        ForeignKey("decisions.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("kind", Text, nullable=False),
    Column("value", Numeric(12, 4), nullable=False),
    Column("components", JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    Column("reward_model_id", UUID(as_uuid=True)),
    Column("is_final", Boolean, nullable=False, server_default="false"),
    Column("observed_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

arm_stats = Table(
    "arm_stats",
    metadata,
    Column("arm_id", UUID(as_uuid=True), ForeignKey("arms.id", ondelete="CASCADE"), nullable=False),
    Column("business_id", UUID(as_uuid=True), nullable=False),
    Column("segment_key", Text, nullable=False, server_default="all"),
    Column("alpha", Numeric(14, 4), nullable=False, server_default="1"),
    Column("beta", Numeric(14, 4), nullable=False, server_default="1"),
    Column("n", Integer, nullable=False, server_default="0"),
    Column("reward_sum", Numeric(16, 4), nullable=False, server_default="0"),
    Column("reward_m2", Numeric(18, 6), nullable=False, server_default="0"),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    PrimaryKeyConstraint("arm_id", "segment_key"),
)

reward_models = Table(
    "reward_models",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()),
    Column("business_id", UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE")),
    Column("version", Integer, nullable=False),
    Column("proxy_weights", JSONB, nullable=False),
    Column("calibration", JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    Column("metrics", JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    Column("trained_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

priors = Table(
    "priors",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()),
    Column("scope_level", Text, nullable=False),
    Column("scope_key", Text, nullable=False),
    Column("decision_key", Text, nullable=False),
    Column("arm_signature", Text, nullable=False),
    Column("alpha", Numeric(14, 4), nullable=False),
    Column("beta", Numeric(14, 4), nullable=False),
    Column("effective_n", Numeric(14, 2), nullable=False),
    Column("contributing_tenants", Integer, nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("scope_level", "scope_key", "decision_key", "arm_signature"),
)

playbook_insights = Table(
    "playbook_insights",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()),
    Column(
        "business_id",
        UUID(as_uuid=True),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("statement", Text, nullable=False),
    Column("evidence", JSONB, nullable=False),
    Column("confidence", Numeric(4, 3), nullable=False),
    Column("status", Text, nullable=False, server_default="hypothesis"),
    Column("run_id", UUID(as_uuid=True), ForeignKey("agent_runs.id")),
    Column("superseded_by", UUID(as_uuid=True), ForeignKey("playbook_insights.id")),
    Column("expires_at", DateTime(timezone=True)),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

conversations = Table(
    "conversations",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()),
    Column(
        "business_id",
        UUID(as_uuid=True),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "contact_id",
        UUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("channel", Text, nullable=False),
    Column("status", Text, nullable=False, server_default="open"),
    Column("first_inbound_at", DateTime(timezone=True)),
    Column("first_response_at", DateTime(timezone=True)),
    Column("handed_off_to", UUID(as_uuid=True), ForeignKey("users.id")),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

messages = Table(
    "messages",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()),
    Column("business_id", UUID(as_uuid=True), nullable=False),
    Column(
        "conversation_id",
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("direction", Text, nullable=False),
    Column("sender_kind", Text, nullable=False),
    Column("body_enc", LargeBinary),
    Column("template_id", UUID(as_uuid=True), ForeignKey("assets.id")),
    Column("decision_id", UUID(as_uuid=True), ForeignKey("decisions.id")),
    Column("external_id", Text),
    Column("sent_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("delivered_at", DateTime(timezone=True)),
    Column("read_at", DateTime(timezone=True)),
)

event_types = Table(
    "event_types",
    metadata,
    Column("key", Text, primary_key=True),
    Column("category", Text, nullable=False),
    Column("stage_key", Text),
    Column("schema", JSONB, nullable=False, server_default=text("'{}'::jsonb")),
)

events = Table(
    "events",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()),
    Column("business_id", UUID(as_uuid=True), nullable=False),
    Column("event_type", Text, ForeignKey("event_types.key"), nullable=False),
    Column("occurred_at", DateTime(timezone=True), primary_key=True, nullable=False),
    Column("recorded_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("contact_id", UUID(as_uuid=True)),
    Column("anonymous_id", Text),
    Column("location_id", UUID(as_uuid=True)),
    Column("campaign_id", UUID(as_uuid=True)),
    Column("asset_id", UUID(as_uuid=True)),
    Column("decision_id", UUID(as_uuid=True)),
    Column("tracking_code", Text),
    Column("source", Text, nullable=False),
    Column("properties", JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    Column("value_minor", BigInteger),
    Column("idempotency_key", Text, nullable=False),
)

contact_stage_history = Table(
    "contact_stage_history",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()),
    Column("business_id", UUID(as_uuid=True), nullable=False),
    Column(
        "contact_id",
        UUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("stage_id", UUID(as_uuid=True), ForeignKey("funnel_stages.id"), nullable=False),
    Column("entered_at", DateTime(timezone=True), nullable=False),
    Column("source_event_id", UUID(as_uuid=True)),
    UniqueConstraint("contact_id", "stage_id"),
)

conversions = Table(
    "conversions",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()),
    Column(
        "business_id",
        UUID(as_uuid=True),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "contact_id",
        UUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("stage_id", UUID(as_uuid=True), ForeignKey("funnel_stages.id"), nullable=False),
    Column("occurred_at", DateTime(timezone=True), nullable=False),
    Column("value_minor", BigInteger, nullable=False, server_default="0"),
    Column("verified", Boolean, nullable=False, server_default="false"),
    Column("verified_by", Text),
    Column("source_event_id", UUID(as_uuid=True)),
    UniqueConstraint("contact_id", "stage_id"),
)

attributions = Table(
    "attributions",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()),
    Column("business_id", UUID(as_uuid=True), nullable=False),
    Column(
        "conversion_id",
        UUID(as_uuid=True),
        ForeignKey("conversions.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("touch_event_id", UUID(as_uuid=True), nullable=False),
    Column("campaign_id", UUID(as_uuid=True), ForeignKey("campaigns.id")),
    Column("asset_id", UUID(as_uuid=True), ForeignKey("assets.id")),
    Column("decision_id", UUID(as_uuid=True), ForeignKey("decisions.id")),
    Column("model", Text, nullable=False),
    Column("credit", Numeric(5, 4), nullable=False),
    Column("match_method", Text, nullable=False),
    Column("confidence", Numeric(4, 3), nullable=False),
    Column("computed_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("conversion_id", "touch_event_id", "model"),
)

api_keys = Table(
    "api_keys",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()),
    Column(
        "business_id",
        UUID(as_uuid=True),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("key_prefix", Text, nullable=False),
    Column("key_hash", Text, nullable=False),
    Column("name", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("revoked_at", DateTime(timezone=True)),
)
