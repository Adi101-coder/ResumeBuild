"""Normalize scraped job dicts before DB insert."""

from __future__ import annotations

from app.database.models import Job


def _as_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    if value is None:
        return default
    return bool(value)


def _as_str(value: object, max_len: int) -> str:
    if value is None:
        text = ""
    elif isinstance(value, bool):
        text = "remote" if value else ""
    else:
        text = str(value)
    return text.strip()[:max_len]


def _as_skills(value: object) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [_as_str(item, 128) for item in value if _as_str(item, 128)]
    return [_as_str(value, 128)] if _as_str(value, 128) else []


def normalize_job_item(item: dict) -> dict:
    """Coerce scraper output to match Job column types and length limits."""
    remote_raw = item.get("remote_type", item.get("remote", ""))
    return {
        "title": _as_str(item.get("title"), 512),
        "company": _as_str(item.get("company"), 512),
        "location": _as_str(item.get("location"), 255),
        "salary": _as_str(item.get("salary"), 128),
        "experience_required": _as_str(item.get("experience_required"), 128),
        "skills": _as_skills(item.get("skills")),
        "description": _as_str(item.get("description"), 50_000),
        "apply_url": _as_str(item.get("apply_url"), 1024),
        "application_type": _as_str(item.get("application_type") or "external", 64),
        "easy_apply": _as_bool(item.get("easy_apply"), False),
        "remote_type": _as_str(remote_raw, 64),
        "visa_required": _as_bool(item.get("visa_required"), False),
        "source": _as_str(item.get("source") or "manual", 64),
        "posted_at": item.get("posted_at"),
    }


def prepare_job_row(item: dict, dedup_hash: str) -> Job:
    payload = normalize_job_item(item)
    return Job(**payload, dedup_hash=dedup_hash[:64])
