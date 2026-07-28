import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.agents.scraper.base import RemoteOKScraper
from app.database.models import Job
from app.database.session import get_db
from app.schemas.job import JobCreate, JobResponse
from app.services.deduplication import job_dedup_hash
from app.services.job_discovery import discover_jobs_for_candidate

logger = logging.getLogger("app.jobs")
router = APIRouter(prefix="/jobs", tags=["jobs"])

@router.post("", response_model=JobResponse)
def create_job(payload: JobCreate, db: Session = Depends(get_db)):
    dedup_hash = job_dedup_hash(payload.company, payload.title, payload.location)
    existing = db.query(Job).filter(Job.dedup_hash == dedup_hash).first()
    if existing:
        logger.info("Duplicate job skipped: %s @ %s", payload.title, payload.company)
        return existing
    job = Job(
        **payload.model_dump(),
        dedup_hash=dedup_hash,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    logger.info("Job created: id=%s %s @ %s", job.id, job.title, job.company)
    return job

@router.get("", response_model=list[JobResponse])
def list_jobs(
    db: Session = Depends(get_db),
    limit: int = Query(default=50, le=200),
    source: str | None = None,
):
    query = db.query(Job).order_by(Job.created_at.desc())
    if source:
        query = query.filter(Job.source == source)
    return query.limit(limit).all()


@router.post("/seed", response_model=dict)
def seed_sample_jobs(db: Session = Depends(get_db)):
    from app.services.seed import seed_jobs

    created = seed_jobs(db)
    logger.info("Seeded %d sample jobs", created)
    return {"created": created}

@router.get("/sources")
def list_job_sources():
    from app.agents.scraper.registry import get_source_status

    return {"sources": get_source_status()}


@router.post("/discover/{candidate_id}")
async def discover_jobs(candidate_id: int, db: Session = Depends(get_db)):
    from app.database.models import Candidate

    if not db.get(Candidate, candidate_id):
        raise HTTPException(status_code=404, detail="Candidate not found.")
    try:
        result = await discover_jobs_for_candidate(db, candidate_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        logger.exception("Discovery failed for candidate_id=%s", candidate_id)
        raise HTTPException(status_code=500, detail=f"Job discovery failed: {exc}") from exc
    logger.info("Discovery complete: %s", result)
    return result


@router.post("/scrape/remoteok", response_model=list[JobResponse])
async def scrape_remoteok(
    query: str = Query(default=""),
    db: Session = Depends(get_db),
):
    scraper = RemoteOKScraper()
    logger.info("Scraping RemoteOK with query=%r", query or "(all)")
    scraped = await scraper.fetch_jobs(query=query, limit=50)
    logger.info("RemoteOK returned %d jobs", len(scraped))
    created: list[Job] = []

    for item in scraped:
        dedup_hash = job_dedup_hash(item["company"], item["title"], item["location"])
        if db.query(Job).filter(Job.dedup_hash == dedup_hash).first():
            continue
        job = Job(**item, dedup_hash=dedup_hash)
        db.add(job)
        created.append(job)

    db.commit()
    for job in created:
        db.refresh(job)
    logger.info("Stored %d new jobs from RemoteOK", len(created))
    return created

@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job
