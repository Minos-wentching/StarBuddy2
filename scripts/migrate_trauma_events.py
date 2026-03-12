"""
Phase B migration script:
- Backfill trauma_events_* from legacy memory_orbs_* in User.settings.ifs_onboarding
- Keep dual-write compatibility fields in sync

Usage:
  python scripts/migrate_trauma_events.py
  python scripts/migrate_trauma_events.py --dry-run
"""

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
import sys

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine, text

from backend.api_config import config


def to_sync_database_url(database_url: str) -> str:
    if "+aiosqlite" in database_url:
        return database_url.replace("+aiosqlite", "+pysqlite")
    if database_url.startswith("sqlite:///"):
        return database_url
    if "+asyncpg" in database_url:
        return database_url.replace("+asyncpg", "+psycopg")
    if "+asyncmy" in database_url:
        return database_url.replace("+asyncmy", "+pymysql")
    return database_url


def ensure_dict_settings(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            return {}
    return {}


def clamp(value: Any, minimum: float = 0.0, maximum: float = 1.0) -> float:
    try:
        num = float(value)
    except Exception:
        return minimum
    return max(minimum, min(maximum, num))


def normalize_legacy_orb(raw: dict[str, Any], index: int, default_source: str) -> dict[str, Any]:
    now_iso = datetime.utcnow().isoformat()
    intensity_raw = raw.get("intensity", 0.58)
    intensity = clamp(float(intensity_raw) / 10.0) if isinstance(intensity_raw, (int, float)) and float(intensity_raw) > 1 else clamp(intensity_raw)

    title = str(raw.get("title") or raw.get("trigger_event") or raw.get("triggerEvent") or "未命名事件").strip()
    trigger_event = str(raw.get("trigger_event") or raw.get("triggerEvent") or title).strip()
    trauma_event = str(raw.get("trauma_event") or raw.get("trauma_text") or raw.get("traumaText") or trigger_event).strip()

    return {
        "event_id": str(raw.get("event_id") or raw.get("id") or f"event_{index + 1}"),
        "title": title,
        "trigger_event": trigger_event,
        "trauma_event": trauma_event,
        "intensity": intensity,
        "persona_hint": str(raw.get("persona_hint") or raw.get("personaHint") or ("firefighters" if intensity >= 0.72 else "exiles")),
        "source_type": str(raw.get("source_type") or raw.get("sourceType") or default_source),
        "created_at": str(raw.get("created_at") or raw.get("createdAt") or now_iso),
        "updated_at": str(raw.get("updated_at") or raw.get("updatedAt") or now_iso),
        "event_rank": int(raw.get("event_rank") or raw.get("orb_rank") or raw.get("orbRank") or (index + 1)),
    }


def event_to_legacy_orb(event: dict[str, Any], index: int) -> dict[str, Any]:
    return {
        "id": str(event.get("event_id") or f"orb_{index + 1}"),
        "title": str(event.get("title") or "未命名记忆"),
        "trigger_event": str(event.get("trigger_event") or ""),
        "trauma_text": str(event.get("trauma_event") or ""),
        "intensity": event.get("intensity", 0.58),
        "persona_hint": str(event.get("persona_hint") or "exiles"),
        "source_type": str(event.get("source_type") or "onboarding_fixed"),
        "created_at": str(event.get("created_at") or ""),
        "orb_rank": int(event.get("event_rank") or (index + 1)),
    }


def normalize_event(raw: dict[str, Any], index: int, default_source: str) -> dict[str, Any]:
    # Accept both trauma-event shape and legacy orb shape
    return normalize_legacy_orb({
        "id": raw.get("event_id") or raw.get("id"),
        "title": raw.get("title"),
        "trigger_event": raw.get("trigger_event") or raw.get("triggerEvent"),
        "trauma_text": raw.get("trauma_event") or raw.get("trauma_text") or raw.get("traumaText"),
        "intensity": raw.get("intensity", 0.58),
        "persona_hint": raw.get("persona_hint") or raw.get("personaHint"),
        "source_type": raw.get("source_type") or raw.get("sourceType") or default_source,
        "created_at": raw.get("created_at") or raw.get("createdAt"),
        "updated_at": raw.get("updated_at") or raw.get("updatedAt"),
        "orb_rank": raw.get("event_rank") or raw.get("orb_rank") or raw.get("orbRank"),
    }, index, default_source)


def migrate_user_settings(dry_run: bool = False) -> tuple[int, int]:
    database_url = to_sync_database_url(config.DATABASE_URL)
    engine = create_engine(database_url)

    with engine.begin() as conn:
        rows = conn.execute(text("SELECT id, settings FROM users")).all()

        scanned = 0
        changed = 0

        for row in rows:
            user_id = row[0]
            settings = ensure_dict_settings(row[1])
            scanned += 1

            onboarding = settings.get("ifs_onboarding", {})
            if not isinstance(onboarding, dict):
                continue

            fixed_new = onboarding.get("trauma_events_fixed", [])
            custom_new = onboarding.get("trauma_events_custom", [])
            fixed_old = onboarding.get("memory_orbs_fixed", [])
            custom_old = onboarding.get("memory_orbs_custom", [])

            fixed_events = []
            custom_events = []

            if isinstance(fixed_new, list) and fixed_new:
                fixed_events = [normalize_event(item if isinstance(item, dict) else {}, i, "onboarding_fixed") for i, item in enumerate(fixed_new)]
            elif isinstance(fixed_old, list) and fixed_old:
                fixed_events = [normalize_event(item if isinstance(item, dict) else {}, i, "onboarding_fixed") for i, item in enumerate(fixed_old)]

            if isinstance(custom_new, list) and custom_new:
                custom_events = [normalize_event(item if isinstance(item, dict) else {}, i, "custom") for i, item in enumerate(custom_new)]
            elif isinstance(custom_old, list) and custom_old:
                custom_events = [normalize_event(item if isinstance(item, dict) else {}, i, "custom") for i, item in enumerate(custom_old)]

            initialized = bool(onboarding.get("trauma_events_initialized") or onboarding.get("memory_orbs_initialized"))

            next_onboarding = dict(onboarding)
            next_onboarding["trauma_events_fixed"] = fixed_events
            next_onboarding["trauma_events_custom"] = custom_events
            next_onboarding["trauma_events_initialized"] = initialized
            next_onboarding["memory_orbs_fixed"] = [event_to_legacy_orb(event, i) for i, event in enumerate(fixed_events)]
            next_onboarding["memory_orbs_custom"] = [event_to_legacy_orb(event, i) for i, event in enumerate(custom_events)]
            next_onboarding["memory_orbs_initialized"] = initialized

            if next_onboarding != onboarding:
                changed += 1
                settings["ifs_onboarding"] = next_onboarding
                if not dry_run:
                    conn.execute(
                        text("UPDATE users SET settings = :settings WHERE id = :user_id"),
                        {"settings": json.dumps(settings, ensure_ascii=False), "user_id": user_id},
                    )

        if dry_run:
            conn.rollback()

        return scanned, changed


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill trauma_events from legacy memory_orbs")
    parser.add_argument("--dry-run", action="store_true", help="Scan and report only, without writing")
    args = parser.parse_args()

    scanned, changed = migrate_user_settings(dry_run=args.dry_run)
    mode = "DRY-RUN" if args.dry_run else "APPLY"
    print(f"[trauma-events-migration] mode={mode} scanned={scanned} changed={changed}")


if __name__ == "__main__":
    main()
