from __future__ import annotations

import asyncio
import logging

from sqlalchemy.orm import Session

from app.agents.scraper.registry import SOURCE_CATALOG, build_scrapers
from app.database.models import Candidate, Job
from app.schemas.profile import CandidateProfile
from app.services.deduplication import job_dedup_hash
from app.services.job_normalize import prepare_job_row
from app.services.pipeline_log import step, step_done, step_fail
from app.services.profile_queries import build_search_queries

logger = logging.getLogger("app.discovery")

SCRAPER_TIMEOUT_SEC = 30.0
JOBS_PER_SOURCE = 50
JOBS_AFTER_FILTER = 35


def _select_jobs_for_profile(jobs: list[dict], queries: list[str], limit: int) -> list[dict]:
    """Prefer jobs matching profile queries; still return broader pool if matches are sparse."""
    if not jobs:
        return []
    if not queries:
        return jobs[:limit]

    matched: list[dict] = []
    rest: list[dict] = []
    for job in jobs:
        haystack = " ".join(
            [
                str(job.get("title", "")),
                str(job.get("description", "")),
                str(job.get("company", "")),
                " ".join(str(s) for s in (job.get("skills") or [])),
            ]
        ).lower()
        if any(q.lower() in haystack for q in queries):
            matched.append(job)
        else:
            rest.append(job)

    combined = matched + rest
    return combined[:limit]


async def _fetch_from_scraper(scraper, queries: list[str], location_hint: str) -> list[dict]:
    """One profile-based search per job board."""
    primary_query = queries[0] if queries else "software engineer"
    raw = await scraper.fetch_jobs(
        query=primary_query,
        location=location_hint,
        limit=JOBS_PER_SOURCE,
    )
    return _select_jobs_for_profile(raw, queries, limit=JOBS_AFTER_FILTER)


async def _scrape_one(scraper, queries: list[str], location_hint: str) -> tuple[str, list[dict], str | None]:
    source = scraper.source_name
    label = getattr(scraper, "board_token", None) or getattr(scraper, "company_slug", None) or source
    step(f"SCRAPE_{source.upper()}", target=label)
    try:
        batch = await asyncio.wait_for(
            _fetch_from_scraper(scraper, queries, location_hint),
            timeout=SCRAPER_TIMEOUT_SEC,
        )
        step_done(f"SCRAPE_{source.upper()}", target=label, jobs=len(batch))
        return source, batch, None
    except asyncio.TimeoutError:
        msg = f"timed out after {SCRAPER_TIMEOUT_SEC}s"
        step_fail(f"SCRAPE_{source.upper()}", msg)
        logger.warning("Source %s (%s) timed out", source, label)
        return source, [], msg
    except Exception as exc:
        msg = str(exc) or repr(exc)
        step_fail(f"SCRAPE_{source.upper()}", msg)
        logger.exception("Source %s (%s) failed", source, label)
        return source, [], msg


async def discover_jobs_for_candidate(db: Session, candidate_id: int) -> dict:
    step("DISCOVERY_START", candidate_id=candidate_id)

    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        step_fail("DISCOVERY_START", "candidate not found")
        raise ValueError("Candidate not found")

    profile = CandidateProfile.model_validate(candidate.profile_json)
    queries = build_search_queries(profile.model_dump())
    location_hint = profile.location or ""

    step("BUILD_QUERIES", count=len(queries), queries=",".join(queries[:8]))
    scrapers = build_scrapers()
    step(
        "INIT_SOURCES",
        total_sources=len(scrapers),
        mode="parallel",
        max_wait_sec=SCRAPER_TIMEOUT_SEC,
    )

    results = await asyncio.gather(
        *[_scrape_one(scraper, queries, location_hint) for scraper in scrapers]
    )

    scraped: list[dict] = []
    source_stats: dict[str, dict] = {}

    for source, batch, error in results:
        stats = source_stats.setdefault(source, {"fetched": 0, "errors": 0})
        stats["fetched"] += len(batch)
        if error:
            stats["errors"] += 1
        scraped.extend(batch)

    step("DEDUPLICATE_AND_STORE", raw_jobs=len(scraped))
    created = 0
    skipped = 0
    seen_hashes: set[str] = set()
    candidates: list[tuple[dict, str]] = []

    for item in scraped:
        dedup_hash = job_dedup_hash(item["company"], item["title"], item["location"])
        if dedup_hash in seen_hashes:
            skipped += 1
            continue
        seen_hashes.add(dedup_hash)
        candidates.append((item, dedup_hash))

    existing_hashes: set[str] = set()
    if candidates:
        hash_list = [dedup_hash for _, dedup_hash in candidates]
        existing_hashes = {
            row[0] for row in db.query(Job.dedup_hash).filter(Job.dedup_hash.in_(hash_list)).all()
        }

    for item, dedup_hash in candidates:
        if dedup_hash in existing_hashes:
            skipped += 1
            continue
        try:
            db.add(prepare_job_row(item, dedup_hash))
            created += 1
        except Exception as exc:
            logger.warning("Skipped job %s @ %s: %s", item.get("title"), item.get("company"), exc)
            skipped += 1

    db.commit()
    total_jobs = db.query(Job).count()

    step_done(
        "DISCOVERY_COMPLETE",
        created=created,
        skipped=skipped,
        total_jobs=total_jobs,
        sources=len(source_stats),
    )

    return {
        "candidate_id": candidate_id,
        "search_queries": queries,
        "scraped": len(scraped),
        "created": created,
        "skipped_duplicates": skipped,
        "total_jobs_in_db": total_jobs,
        "sources": source_stats,
        "source_catalog": SOURCE_CATALOG,
    }
