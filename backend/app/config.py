from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql://future:future@localhost:5432/future"
    smv_base_url: str = "https://www.smv.gob.pe/ws_od_eeff/WebServiceInfoFinanciera.asmx"
    smv_timeout_seconds: float = 120
    session_ttl_days: int = 30
    upload_dir: str = "data/avatars"
    notes_sources_file: str = "backend/data/notes/sources.json"
    notes_sync_on_start: bool = True
    notes_sync_day: int = 1
    notes_sync_hour: int = 6
    notes_sync_timezone: str = "America/Lima"
    notes_worker_poll_seconds: float = 30
    notes_http_timeout_seconds: float = 120
    notes_max_pdf_bytes: int = 30_000_000
    notes_worker_max_attempts: int = 3
    notes_sync_in_api_on_start: bool = False
    migrations_dir: str = "infra/postgres/init"
    bootstrap_events_file: str = "backend/data/events/official_events_2026.json"
    bootstrap_on_start: bool = True
    company_catalog_sync_on_start: bool = True
    company_analysis_fiscal_year: int = 2025
    analysis_worker_enabled: bool = True
    analysis_worker_poll_seconds: float = 5
    analysis_worker_max_attempts: int = 3
    analysis_active_jobs_per_user: int = 3

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_upload_dir() -> Path:
    configured = Path(get_settings().upload_dir)
    if configured.is_absolute():
        return configured
    project_root = Path(__file__).resolve().parents[2]
    return project_root / configured


def get_notes_sources_path() -> Path:
    configured = Path(get_settings().notes_sources_file)
    if configured.is_absolute():
        return configured
    project_root = Path(__file__).resolve().parents[2]
    return project_root / configured


def get_migrations_dir() -> Path:
    configured = Path(get_settings().migrations_dir)
    if configured.is_absolute():
        return configured
    project_root = Path(__file__).resolve().parents[2]
    return project_root / configured


def get_bootstrap_events_path() -> Path:
    configured = Path(get_settings().bootstrap_events_file)
    if configured.is_absolute():
        return configured
    project_root = Path(__file__).resolve().parents[2]
    return project_root / configured
