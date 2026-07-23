from app.data.sample_jobs import SAMPLE_JOBS
from app.database.models import Job
from app.services.deduplication import job_dedup_hash


def seed_jobs(db) -> int:
    created = 0
    for item in SAMPLE_JOBS:
        dedup_hash = job_dedup_hash(item["company"], item["title"], item["location"])
        if db.query(Job).filter(Job.dedup_hash == dedup_hash).first():
            continue
        db.add(Job(**item, dedup_hash=dedup_hash))
        created += 1
    db.commit()
    return created
