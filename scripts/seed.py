"""Seed script: Event types, gym vertical pack, demo org, business, locations, arms, and objective."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from typing import Any
from uuid import UUID, uuid4

import yaml
from sqlalchemy import text

from src.engine.api.auth import hash_api_key
from src.engine.db.session import admin_session, tenant_session

EVENT_TYPES_SEED = [
    ("ad.impression", "exposure", None),
    ("ad.click", "engagement", None),
    ("page.view", "engagement", None),
    ("form.submitted", "conversion", "lead"),
    ("message.inbound", "engagement", None),
    ("message.outbound", "engagement", None),
    ("message.delivered", "engagement", None),
    ("message.read", "engagement", None),
    ("trial.booked", "conversion", "trial_booked"),
    ("trial.attended", "conversion", "trial_attended"),
    ("trial.no_show", "engagement", None),
    ("visit.checkin", "engagement", None),
    ("membership.purchased", "revenue", "member"),
    ("payment.received", "revenue", None),
    ("membership.renewed", "revenue", None),
    ("membership.cancelled", "system", None),
    ("consent.granted", "system", None),
    ("consent.withdrawn", "system", None),
    ("frontdesk.source_reported", "system", None),
    ("system.decision_made", "system", None),
]


def seed_database() -> dict[str, Any]:
    """Populates all required base data and returns demo entity identifiers."""
    pack_file = Path(__file__).parent.parent / "packs" / "gym" / "pack.yaml"
    pack_data = yaml.safe_load(pack_file.read_text(encoding="utf-8"))

    org_id = uuid4()
    user_id = uuid4()
    pack_id = uuid4()
    biz_id = uuid4()

    with admin_session() as session:
        # 1. Seed Event Types
        for key, category, stage_key in EVENT_TYPES_SEED:
            session.execute(
                text("""
                    INSERT INTO event_types (key, category, stage_key, schema)
                    VALUES (:k, :cat, :stg, '{}'::jsonb)
                    ON CONFLICT (key) DO UPDATE
                    SET category = EXCLUDED.category, stage_key = EXCLUDED.stage_key
                """),
                {"k": key, "cat": category, "stg": stage_key},
            )

        # 2. Seed Vertical Pack
        session.execute(
            text("""
                INSERT INTO vertical_packs (id, slug, version, name, config, created_at)
                VALUES (:id, :slug, :v, :name, :config, now())
                ON CONFLICT (slug, version) DO UPDATE
                SET name = EXCLUDED.name, config = EXCLUDED.config
            """),
            {
                "id": str(pack_id),
                "slug": pack_data["slug"],
                "v": pack_data["version"],
                "name": pack_data["name"],
                "config": json.dumps(pack_data),
            },
        )
        # Fetch persisted pack_id
        pack_row = session.execute(
            text("SELECT id FROM vertical_packs WHERE slug = :s AND version = :v"),
            {"s": pack_data["slug"], "v": pack_data["version"]},
        ).fetchone()
        pack_id = UUID(str(pack_row[0]))

        # 3. Seed Organization & User
        session.execute(
            text(
                "INSERT INTO organizations (id, name, kind) VALUES (:id, 'Apex Fitness Enterprises', 'direct')"
            ),
            {"id": str(org_id)},
        )
        session.execute(
            text(
                "INSERT INTO users (id, email, name) VALUES (:id, 'admin@apexfitness.com', 'Alex Mercer')"
            ),
            {"id": str(user_id)},
        )

        # 4. Seed Business (IronFit Gyms)
        brand_profile = {
            "name": "IronFit Gyms",
            "usps": "State-of-the-art strength zones, Olympic lifting platforms, certified coaches, open 6am-10pm daily.",
            "branches": [
                {"name": "Indiranagar", "address": "100ft Road, Indiranagar, Bengaluru"},
                {"name": "Koramangala", "address": "80ft Road, 4th Block, Koramangala, Bengaluru"},
                {"name": "Whitefield", "address": "ITPL Main Road, Whitefield, Bengaluru"},
            ],
            "price_list": {
                "monthly": 350000,  # 3500 INR in minor paise
                "quarterly": 900000,  # 9000 INR
                "annual": 2400000,  # 24000 INR
            },
            "trial_offer": "Free 7-Day Workout & Coach Trial",
        }

        session.execute(
            text("""
                INSERT INTO businesses (id, org_id, vertical_pack_id, name, timezone, currency, brand_profile, status)
                VALUES (:id, :org_id, :pack_id, 'IronFit Gyms', 'Asia/Kolkata', 'INR', :bp, 'active')
            """),
            {
                "id": str(biz_id),
                "org_id": str(org_id),
                "pack_id": str(pack_id),
                "bp": json.dumps(brand_profile),
            },
        )

        session.execute(
            text(
                "INSERT INTO business_members (business_id, user_id, role) VALUES (:b, :u, 'owner')"
            ),
            {"b": str(biz_id), "u": str(user_id)},
        )

        # 5. Seed 3 Locations
        locations_data = [
            ("Indiranagar Branch", "Bengaluru", "south_india", 12.9784, 77.6408, 5000, 150),
            ("Koramangala Branch", "Bengaluru", "south_india", 12.9352, 77.6245, 5000, 180),
            ("Whitefield Branch", "Bengaluru", "south_india", 12.9698, 77.7500, 6000, 200),
        ]
        location_ids = []
        for name, city, region, lat, lng, catchment, cap in locations_data:
            loc_id = uuid4()
            session.execute(
                text("""
                    INSERT INTO locations (id, business_id, name, city, region_key, lat, lng, catchment_m, capacity_per_day)
                    VALUES (:id, :b, :name, :city, :reg, :lat, :lng, :catch, :cap)
                """),
                {
                    "id": str(loc_id),
                    "b": str(biz_id),
                    "name": name,
                    "city": city,
                    "reg": region,
                    "lat": lat,
                    "lng": lng,
                    "catch": catchment,
                    "cap": cap,
                },
            )
            location_ids.append(loc_id)

        # 6. Seed Ingestion API Key
        raw_key = "ironfit_demo_key_9823487214908234"
        key_prefix = raw_key[:8]
        key_hash = hash_api_key(raw_key)
        session.execute(
            text("""
                INSERT INTO api_keys (id, business_id, key_prefix, key_hash, name, created_at)
                VALUES (gen_random_uuid(), :b, :prefix, :hash, 'Default Ingest Key', now())
            """),
            {"b": str(biz_id), "prefix": key_prefix, "hash": key_hash},
        )

    # 7. Seed Business Funnel Stages, Decision Points, and Arms under tenant session
    with tenant_session(biz_id) as t_session:
        # Funnel stages
        for stage in pack_data["funnel_stages"]:
            t_session.execute(
                text("""
                    INSERT INTO funnel_stages (
                        id, business_id, key, label, ordinal, reward_weight, is_revenue_stage, expected_lag_days
                    )
                    VALUES (
                        gen_random_uuid(), :b, :key, :label, :ord, :w, :rev, :lag
                    )
                    ON CONFLICT (business_id, key) DO UPDATE
                    SET reward_weight = EXCLUDED.reward_weight
                """),
                {
                    "b": str(biz_id),
                    "key": stage["key"],
                    "label": stage["label"],
                    "ord": stage["ordinal"],
                    "w": stage["reward_weight"],
                    "rev": stage["is_revenue_stage"],
                    "lag": stage["expected_lag_days"],
                },
            )

        # Decision points
        dp_map = {}
        for dp in pack_data["decision_points"]:
            dp_id = uuid4()
            t_session.execute(
                text("""
                    INSERT INTO decision_points (id, business_id, key, description, algorithm, reward_window_days)
                    VALUES (:id, :b, :key, :desc, :algo, :window)
                    ON CONFLICT (business_id, key) DO UPDATE
                    SET description = EXCLUDED.description
                """),
                {
                    "id": str(dp_id),
                    "b": str(biz_id),
                    "key": dp["key"],
                    "desc": dp["description"],
                    "algo": dp["algorithm"],
                    "window": dp["reward_window_days"],
                },
            )
            # Re-query id
            row = t_session.execute(
                text("SELECT id FROM decision_points WHERE business_id = :b AND key = :k"),
                {"b": str(biz_id), "k": dp["key"]},
            ).fetchone()
            dp_map[dp["key"]] = UUID(str(row[0]))

        # Autonomy policies (Default all at L1 per BUILD.md 6.2)
        for kind in (
            "send_message",
            "create_campaign",
            "change_budget",
            "pause_campaign",
            "publish_post",
        ):
            t_session.execute(
                text("""
                    INSERT INTO autonomy_policies (id, business_id, action_kind, autonomy_level, caps, effective_from)
                    VALUES (
                        gen_random_uuid(), :b, :kind, 1,
                        '{"daily_spend_minor": 10000000, "max_budget_change_pct": 20, "daily_sends": 200}'::jsonb,
                        now()
                    )
                    ON CONFLICT (business_id, action_kind, effective_from) DO NOTHING
                """),
                {"b": str(biz_id), "kind": kind},
            )

        # Seed initial arms for ad_hook and offer
        arms_to_seed = [
            ("ad_hook", "Strength & High Intensity Focus", "ad_hook:strength_focus"),
            ("ad_hook", "Weight Loss & Transformation", "ad_hook:weight_loss"),
            ("ad_hook", "Friendly Community & Fitness Vibe", "ad_hook:community_vibe"),
            ("offer", "1-Day Free Day Pass", "offer:free_trial_1d"),
            ("offer", "7-Day Unlimited Free Workout Trial", "offer:free_trial_7d"),
            ("offer", "Flat 20% Off Annual Membership", "offer:flat_discount_20"),
            ("lead_first_reply", "Supportive Coach Persona", "lead_first_reply:friendly_coach"),
            ("lead_first_reply", "Direct Calendar Scheduler", "lead_first_reply:direct_scheduler"),
            ("followup_script", "Gentle Workout Check-in", "followup_script:gentle_nudge"),
            ("followup_script", "Class Schedule Preview", "followup_script:schedule_preview"),
        ]

        for dp_key, label, sig in arms_to_seed:
            if dp_key in dp_map:
                t_session.execute(
                    text("""
                        INSERT INTO arms (id, business_id, decision_point_id, label, signature, status)
                        VALUES (gen_random_uuid(), :b, :dp_id, :label, :sig, 'active')
                    """),
                    {
                        "b": str(biz_id),
                        "dp_id": str(dp_map[dp_key]),
                        "label": label,
                        "sig": sig,
                    },
                )

        # Reward model (v1)
        t_session.execute(
            text("""
                INSERT INTO reward_models (id, business_id, version, proxy_weights, calibration)
                VALUES (
                    gen_random_uuid(), :b, 1,
                    '{"lead": 0.5, "trial_booked": 1.0, "trial_attended": 3.0, "member": 10.0, "active_90d": 25.0}'::jsonb,
                    '{"lead": 0.2, "trial_booked": 0.4, "trial_attended": 0.7, "member": 1.0}'::jsonb
                )
            """),
            {"b": str(biz_id)},
        )

        # Seed Objective (120 paid gym memberships per month across 3 branches, CAC under INR 1,500)
        member_stage = t_session.execute(
            text("SELECT id FROM funnel_stages WHERE business_id = :b AND key = 'member'"),
            {"b": str(biz_id)},
        ).fetchone()
        member_stage_id = UUID(str(member_stage[0])) if member_stage else None

        t_session.execute(
            text("""
                INSERT INTO objectives (
                    id, business_id, statement, target_stage, target_value,
                    period, budget_minor, constraints, status, created_at
                )
                VALUES (
                    gen_random_uuid(), :b,
                    '120 paid gym memberships per month across 3 branches, CAC under INR 1,500',
                    :stg_id, 120,
                    daterange(current_date, (current_date + interval '30 days')::date, '[]'),
                    18000000, -- 1,80,000 INR (120 * 1500) in minor units
                    '{"max_cac_minor": 150000, "channels": ["meta_ads", "whatsapp", "google_gbp"]}'::jsonb,
                    'active', now()
                )
            """),
            {"b": str(biz_id), "stg_id": str(member_stage_id) if member_stage_id else None},
        )

    return {
        "organization_id": str(org_id),
        "business_id": str(biz_id),
        "user_id": str(user_id),
        "location_ids": [str(lid) for lid in location_ids],
        "api_key": raw_key,
    }


if __name__ == "__main__":
    print("Seeding database...")
    result = seed_database()
    print("Seed complete!")
    print(f"Business ID: {result['business_id']}")
    print(f"API Key:     {result['api_key']}")
