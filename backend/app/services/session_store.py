"""Persist Playwright login sessions (cookies) in the database — never passwords."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.database.models import PlatformSession

logger = logging.getLogger("app.session_store")

PLATFORMS = ("linkedin", "indeed", "ziprecruiter", "glassdoor")


def get_session(db: Session, candidate_id: int, platform: str) -> dict | None:
    row = (
        db.query(PlatformSession)
        .filter(
            PlatformSession.candidate_id == candidate_id,
            PlatformSession.platform == platform,
        )
        .first()
    )
    if not row or not row.storage_state:
        return None
    return row.storage_state


def save_session(db: Session, candidate_id: int, platform: str, storage_state: dict) -> None:
    row = (
        db.query(PlatformSession)
        .filter(
            PlatformSession.candidate_id == candidate_id,
            PlatformSession.platform == platform,
        )
        .first()
    )
    if row:
        row.storage_state = storage_state
        row.updated_at = datetime.utcnow()
    else:
        row = PlatformSession(
            candidate_id=candidate_id,
            platform=platform,
            storage_state=storage_state,
        )
        db.add(row)
    db.commit()
    logger.info("Saved %s session for candidate_id=%s", platform, candidate_id)


def save_session_from_file(db: Session, candidate_id: int, platform: str, path: Path) -> None:
    if not path.exists():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    save_session(db, candidate_id, platform, data)


def export_session_to_file(db: Session, candidate_id: int, platform: str, path: Path) -> bool:
    state = get_session(db, candidate_id, platform)
    if not state:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state), encoding="utf-8")
    return True


def list_sessions(db: Session, candidate_id: int) -> list[dict]:
    rows = db.query(PlatformSession).filter(PlatformSession.candidate_id == candidate_id).all()
    by_platform = {r.platform: r for r in rows}
    result = []
    for platform in PLATFORMS:
        row = by_platform.get(platform)
        result.append(
            {
                "platform": platform,
                "logged_in": row is not None and bool(row.storage_state),
                "updated_at": row.updated_at.isoformat() if row else None,
            }
        )
    return result
