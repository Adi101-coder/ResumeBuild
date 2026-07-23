from __future__ import annotations

import logging

from app.agents.scraper.base import ArbeitnowScraper, GreenhouseBoardScraper, RemoteOKScraper
from app.agents.scraper.sources import (
    AshbyScraper,
    CareerPageRSSScraper,
    LeverScraper,
    LinkedInScraper,
    RedditJobsScraper,
    TwitterJobsScraper,
    WellfoundScraper,
    YCJobsScraper,
)
from app.config import settings

logger = logging.getLogger("app.scraper.registry")

# Human-readable source catalog for UI + docs
SOURCE_CATALOG = {
    "remoteok": {"name": "RemoteOK", "auth": "none", "status": "active"},
    "arbeitnow": {"name": "Arbeitnow", "auth": "none", "status": "active"},
    "greenhouse": {"name": "Greenhouse", "auth": "board slugs", "status": "configurable"},
    "lever": {"name": "Lever", "auth": "company slugs", "status": "configurable"},
    "ashby": {"name": "Ashby", "auth": "board names", "status": "configurable"},
    "yc": {"name": "YC Jobs", "auth": "none", "status": "active"},
    "reddit": {"name": "Reddit", "auth": "none", "status": "active"},
    "wellfound": {"name": "Wellfound", "auth": "API token", "status": "needs_credentials"},
    "linkedin": {"name": "LinkedIn", "auth": "OAuth/session", "status": "needs_credentials"},
    "twitter": {"name": "Twitter/X", "auth": "Bearer token", "status": "needs_credentials"},
    "career_page": {"name": "Career Pages", "auth": "RSS URLs", "status": "configurable"},
}


def _parse_pairs(raw: str) -> list[tuple[str, str]]:
    """Parse 'company:slug,acme:jobs' or plain 'stripe,netflix'."""
    pairs: list[tuple[str, str]] = []
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if ":" in chunk:
            company, slug = chunk.split(":", 1)
            pairs.append((company.strip(), slug.strip()))
        else:
            pairs.append((chunk, chunk))
    return pairs


def build_scrapers() -> list:
    scrapers = [
        RemoteOKScraper(),
        ArbeitnowScraper(),
        YCJobsScraper(),
        RedditJobsScraper(),
        WellfoundScraper(),
        LinkedInScraper(),
        TwitterJobsScraper(),
    ]

    for company, token in _parse_pairs(settings.greenhouse_boards):
        scrapers.append(GreenhouseBoardScraper(token))

    for company, slug in _parse_pairs(settings.lever_companies):
        scrapers.append(LeverScraper(slug))

    for company, board in _parse_pairs(settings.ashby_boards):
        scrapers.append(AshbyScraper(board))

    for company, url in _parse_pairs(settings.career_page_feeds):
        scrapers.append(CareerPageRSSScraper(url, company=company))

    logger.info("Initialized %d job source adapters", len(scrapers))
    return scrapers


def get_source_status() -> list[dict]:
    scrapers = build_scrapers()
    active = {s.source_name for s in scrapers}
    result = []
    for key, meta in SOURCE_CATALOG.items():
        result.append({**meta, "key": key, "enabled": key in active})
    return result
