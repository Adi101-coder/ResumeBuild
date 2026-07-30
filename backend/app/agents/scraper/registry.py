from __future__ import annotations

import logging

from app.agents.scraper.sources import (
    GlassdoorScraper,
    IndeedScraper,
    LinkedInScraper,
    ZipRecruiterScraper,
)

logger = logging.getLogger("app.scraper.registry")

SOURCE_CATALOG = {
    "indeed": {"name": "Indeed", "auth": "none (RSS)", "status": "active"},
    "ziprecruiter": {"name": "ZipRecruiter", "auth": "none", "status": "active"},
    "linkedin": {
        "name": "LinkedIn",
        "auth": "optional session cookie",
        "status": "active",
    },
    "glassdoor": {
        "name": "Glassdoor",
        "auth": "optional session cookie",
        "status": "active",
    },
}


def build_scrapers() -> list:
    scrapers = [
        IndeedScraper(),
        ZipRecruiterScraper(),
        LinkedInScraper(),
        GlassdoorScraper(),
    ]
    logger.info("Initialized %d job board adapters (Indeed, ZipRecruiter, LinkedIn, Glassdoor)", len(scrapers))
    return scrapers


def get_source_status() -> list[dict]:
    scrapers = build_scrapers()
    active = {s.source_name for s in scrapers}
    result = []
    for key, meta in SOURCE_CATALOG.items():
        result.append({**meta, "key": key, "enabled": key in active})
    return result
