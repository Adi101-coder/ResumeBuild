import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import create_engine, text

from app.config import settings
from app.database.postgres import reset_postgres_sequences

engine = create_engine(settings.database_url, pool_pre_ping=True)
reset_postgres_sequences(engine)
print("Sequences reset on", settings.database_url.split("@")[-1])

with engine.connect() as c:
    for t in ["candidates", "resumes", "jobs", "job_matches", "applications"]:
        mx = c.execute(text(f"SELECT MAX(id) FROM {t}")).scalar_one()
        seq = c.execute(text(f"SELECT last_value FROM {t}_id_seq")).scalar_one()
        print(f"{t}: max_id={mx} seq_next={seq}")
