from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "ResumeBuild"
    debug: bool = True
    log_level: str = "DEBUG"
    sql_echo: bool = True

    database_url: str = "sqlite:///./resumebuild.db"
    redis_url: str = "redis://localhost:6379/0"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    storage_path: Path = BASE_DIR / "storage"
    templates_path: Path = BASE_DIR / "templates"
    vector_index_path: Path = BASE_DIR / "storage" / "faiss_index"

    match_threshold: float = 75.0
    top_jobs_limit: int = 50

    cors_origins: list[str] = ["http://localhost:3000"]

    # Job source configuration (comma-separated)
    greenhouse_boards: str = "stripe,figma,airbnb"
    lever_companies: str = "netflix,palantir"
    ashby_boards: str = ""
    career_page_feeds: str = ""
    wellfound_api_token: str = ""
    linkedin_access_token: str = ""
    twitter_bearer_token: str = ""


settings = Settings()

settings.storage_path.mkdir(parents=True, exist_ok=True)
(settings.storage_path / "resumes").mkdir(parents=True, exist_ok=True)
(settings.storage_path / "generated").mkdir(parents=True, exist_ok=True)
settings.vector_index_path.mkdir(parents=True, exist_ok=True)
