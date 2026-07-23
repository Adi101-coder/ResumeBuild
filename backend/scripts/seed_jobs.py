"""CLI helper: python -m scripts.seed_jobs"""

from app.database.session import SessionLocal
from app.services.seed import seed_jobs

if __name__ == "__main__":
    db = SessionLocal()
    count = seed_jobs(db)
    print(f"Seeded {count} jobs.")
