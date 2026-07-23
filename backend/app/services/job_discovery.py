from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.agents.scraper.registry import SOURCE_CATALOG, build_scrapers
from app.database.models import Candidate, Job
from app.schemas.profile import CandidateProfile
from app.services.deduplication import job_dedup_hash
from app.services.pipeline_log import step, step_done, step_fail
from app.services.profile_queries import build_search_queries

logger = logging.getLogger("app.discovery")


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
    step("INIT_SOURCES", total_sources=len(scrapers))

    scraped: list[dict] = []
    source_stats: dict[str, dict] = {}

    for scraper in scrapers:
        source = scraper.source_name
        source_stats.setdefault(source, {"fetched": 0, "errors": 0})
        try:
            step(f"SCRAPE_{source.upper()}", query="profile+broad")
            batch: list[dict] = []
            for query in queries[:6]:
                batch.extend(await scraper.fetch_jobs(query=query, location=location_hint, limit=15))
            batch.extend(await scraper.fetch_jobs(query="", location=location_hint, limit=20))
            source_stats[source]["fetched"] = len(batch)
            scraped.extend(batch)
            step_done(f"SCRAPE_{source.upper()}", jobs=len(batch))
        except Exception as exc:
            source_stats[source]["errors"] = 1
            step_fail(f"SCRAPE_{source.upper()}", str(exc))
            logger.exception("Source %s failed", source)

    step("DEDUPLICATE_AND_STORE", raw_jobs=len(scraped))
    created = 0
    skipped = 0
    seen_hashes: set[str] = set()
    for item in scraped:
        dedup_hash = job_dedup_hash(item["company"], item["title"], item["location"])
        if dedup_hash in seen_hashes:
            skipped += 1
            continue
        seen_hashes.add(dedup_hash)
        if db.query(Job).filter(Job.dedup_hash == dedup_hash).first():
            skipped += 1
            continue
        db.add(Job(**item, dedup_hash=dedup_hash))
        created += 1

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
