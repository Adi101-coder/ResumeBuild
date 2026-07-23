import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import applications, events, jobs, matching, resumes
from app.config import settings
from app.database.models import Base
from app.database.session import engine
from app.logging_config import setup_logging
from app.middleware.request_logging import RequestLoggingMiddleware

setup_logging(settings.log_level)
logger = logging.getLogger("app.main")

app = FastAPI(title=settings.app_name, debug=settings.debug)

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    logger.info("Starting %s", settings.app_name)
    logger.info("Database: %s", settings.database_url.split("@")[-1])
    logger.info("Storage: %s", settings.storage_path)
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ready")


@app.on_event("shutdown")
def on_shutdown() -> None:
    logger.info("Shutting down %s", settings.app_name)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "app": settings.app_name,
        "api_version": 2,
        "routes": [
            "/api/jobs/discover/{candidate_id}",
            "/api/applications/candidate/{candidate_id}",
            "/api/events/client",
        ],
    }


app.include_router(events.router, prefix="/api")
app.include_router(resumes.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(matching.router, prefix="/api")
app.include_router(applications.router, prefix="/api")
