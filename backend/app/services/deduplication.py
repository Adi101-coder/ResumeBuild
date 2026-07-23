from __future__ import annotations

import hashlib
import re
from difflib import SequenceMatcher


def normalize_text(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    return re.sub(r"\s+", " ", value)


def job_dedup_hash(company: str, title: str, location: str) -> str:
    payload = f"{normalize_text(company)}|{normalize_text(title)}|{normalize_text(location)}"
    return hashlib.sha256(payload.encode()).hexdigest()


def description_similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, normalize_text(a), normalize_text(b)).ratio()
