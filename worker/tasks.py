"""Background worker tasks for scraping, matching, and application workflows."""

from celery import Celery

from app.config import settings

celery_app = Celery("resumebuild", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.task_routes = {
    "worker.tasks.scrape_jobs": {"queue": "scraping"},
    "worker.tasks.run_matching": {"queue": "matching"},
}


@celery_app.task(name="worker.tasks.scrape_jobs")
def scrape_jobs(source: str = "indeed", query: str = "engineer") -> dict:
    """Placeholder for async job scraping pipeline."""
    return {"source": source, "query": query, "status": "queued"}


@celery_app.task(name="worker.tasks.run_matching")
def run_matching(candidate_id: int) -> dict:
    """Placeholder for async matching pipeline."""
    return {"candidate_id": candidate_id, "status": "queued"}
