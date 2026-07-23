"""Derive job search queries from a candidate profile (any industry)."""

from __future__ import annotations

import re


GENERIC_ROLE_TERMS = (
    "analyst",
    "manager",
    "specialist",
    "coordinator",
    "associate",
    "executive",
    "consultant",
    "representative",
)


def _clean_term(value: str) -> str:
    value = re.sub(r"\s+", " ", value.strip())
    return value[:80]


def build_search_queries(profile: dict, max_queries: int = 10) -> list[str]:
    """Build diverse search terms from roles, experience, skills — not tech-only."""
    queries: list[str] = []

    for role in profile.get("preferred_roles") or []:
        term = _clean_term(str(role))
        if len(term) > 2:
            queries.append(term)

    for exp in profile.get("experience") or []:
        role = _clean_term(str(exp.get("role", "")))
        if len(role) > 2:
            queries.append(role)

    for edu in profile.get("education") or []:
        field = _clean_term(str(edu.get("field", "")))
        degree = _clean_term(str(edu.get("degree", "")))
        if len(field) > 2:
            queries.append(field)
        if degree and len(degree) > 2:
            queries.append(degree)

    for skill in (profile.get("skills") or [])[:5]:
        term = _clean_term(str(skill))
        if len(term) > 2:
            queries.append(term)

    for keyword in (profile.get("keywords") or [])[:5]:
        term = _clean_term(str(keyword))
        if len(term) > 2:
            queries.append(term)

    if profile.get("summary"):
        summary_words = [
            w for w in re.findall(r"[A-Za-z]{4,}", profile["summary"]) if w.lower() not in {"with", "that", "this", "have", "years"}
        ]
        if summary_words:
            queries.append(" ".join(summary_words[:3]))

    if not queries:
        queries.extend(GENERIC_ROLE_TERMS)

    seen: set[str] = set()
    unique: list[str] = []
    for q in queries:
        key = q.lower()
        if key not in seen:
            seen.add(key)
            unique.append(q)

    return unique[:max_queries]
