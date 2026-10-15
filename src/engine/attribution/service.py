"""Attribution service executing multi-touch attribution queries and updates."""

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.engine.domain.attribution import TouchEvent, compute_attribution


def compute_and_store_attribution(
    session: Session,
    business_id: UUID,
    conversion_id: UUID,
    models: Sequence[str] = ("last_touch", "first_touch", "position"),
    click_lookback_days: int = 30,
    impression_lookback_days: int = 7,
) -> int:
    """
    Finds candidate touches for a conversion and computes/stores attributions.
    Recomputable and idempotent: replaces existing rows for (conversion_id, model).
    Returns count of attribution records written.
    """
    # 1. Fetch conversion details
    conv_row = session.execute(
        text("""
            SELECT contact_id, occurred_at FROM conversions
            WHERE business_id = :biz_id AND id = :c_id
        """),
        {"biz_id": str(business_id), "c_id": str(conversion_id)},
    ).fetchone()

    if not conv_row:
        return 0

    contact_id = UUID(str(conv_row[0]))
    conv_time: datetime = conv_row[1]

    # 2. Fetch anonymous IDs linked to this contact
    anon_rows = session.execute(
        text("""
            SELECT anonymous_id, confidence, method FROM identity_links
            WHERE business_id = :biz_id AND contact_id = :c_id
        """),
        {"biz_id": str(business_id), "c_id": str(contact_id)},
    ).fetchall()

    anon_map = {r[0]: (float(r[1]), str(r[2])) for r in anon_rows}

    # 3. Query candidate touch events for the contact and associated anonymous IDs
    events_query = text("""
        SELECT id, event_type, occurred_at, campaign_id, asset_id, decision_id,
               tracking_code, anonymous_id
        FROM events
        WHERE business_id = :biz_id
          AND occurred_at <= :conv_time
          AND (contact_id = :c_id OR anonymous_id = ANY(:anon_ids))
          AND event_type IN ('ad.click', 'form.submitted', 'message.inbound', 'ad.impression')
        ORDER BY occurred_at ASC
    """)

    event_rows = session.execute(
        events_query,
        {
            "biz_id": str(business_id),
            "conv_time": conv_time,
            "c_id": str(contact_id),
            "anon_ids": list(anon_map.keys()) if anon_map else [""],
        },
    ).fetchall()

    touches: list[TouchEvent] = []
    for r in event_rows:
        ev_id = UUID(str(r[0]))
        ev_type = str(r[1])
        ev_occurred: datetime = r[2]
        camp_id = UUID(str(r[3])) if r[3] else None
        ast_id = UUID(str(r[4])) if r[4] else None
        dec_id = UUID(str(r[5])) if r[5] else None
        trk_code = str(r[6]) if r[6] else None
        anon_id = str(r[7]) if r[7] else None

        # Determine match method and confidence
        if trk_code:
            match_method = "tracking_code"
            confidence = 1.0
        elif anon_id and anon_id in anon_map:
            conf, method = anon_map[anon_id]
            match_method = f"identity_link:{method}"
            confidence = conf
        else:
            match_method = "contact_direct"
            confidence = 1.0

        touches.append(
            TouchEvent(
                event_id=ev_id,
                event_type=ev_type,
                occurred_at=ev_occurred,
                campaign_id=camp_id,
                asset_id=ast_id,
                decision_id=dec_id,
                tracking_code=trk_code,
                match_method=match_method,
                confidence=confidence,
            )
        )

    records_written = 0

    for model_name in models:
        # Atomic replace: delete existing rows for this conversion and model
        session.execute(
            text("""
                DELETE FROM attributions
                WHERE business_id = :biz_id AND conversion_id = :c_id AND model = :m
            """),
            {"biz_id": str(business_id), "c_id": str(conversion_id), "m": model_name},
        )

        credits = compute_attribution(
            touches=touches,
            conversion_time=conv_time,
            model=model_name,
            click_lookback_days=click_lookback_days,
            impression_lookback_days=impression_lookback_days,
        )

        for credit in credits:
            session.execute(
                text("""
                    INSERT INTO attributions (
                        id, business_id, conversion_id, touch_event_id,
                        campaign_id, asset_id, decision_id, model,
                        credit, match_method, confidence, computed_at
                    )
                    VALUES (
                        :id, :biz_id, :conv_id, :touch_id,
                        :camp_id, :asset_id, :dec_id, :model,
                        :credit, :match_method, :confidence, now()
                    )
                """),
                {
                    "id": str(uuid4()),
                    "biz_id": str(business_id),
                    "conv_id": str(conversion_id),
                    "touch_id": str(credit.touch_event_id),
                    "camp_id": str(credit.campaign_id) if credit.campaign_id else None,
                    "asset_id": str(credit.asset_id) if credit.asset_id else None,
                    "dec_id": str(credit.decision_id) if credit.decision_id else None,
                    "model": credit.model,
                    "credit": credit.credit,
                    "match_method": credit.match_method,
                    "confidence": credit.confidence,
                },
            )
            records_written += 1

    return records_written
