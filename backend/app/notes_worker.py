from __future__ import annotations

import argparse
import logging
import signal
import time
from datetime import UTC, datetime

from app.company_analysis import process_next_analysis_job, recover_stale_analysis_jobs
from app.config import get_notes_sources_path, get_settings
from app.db import connect
from app.notes import load_note_sources
from app.notes_jobs import (
    enqueue_monthly_jobs,
    monthly_slot,
    monthly_sync_due,
    process_next_job,
    recover_stale_jobs,
    register_note_sources,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("fundamenta.notes-worker")
running = True


def _stop_worker(_signum: int, _frame: object) -> None:
    global running
    running = False


def initialize() -> int:
    settings = get_settings()
    sources = load_note_sources(get_notes_sources_path())
    now = datetime.now(UTC)
    with connect() as connection:
        register_note_sources(connection, sources)
        recovered = recover_stale_jobs(connection)
        recovered_analyses = recover_stale_analysis_jobs(connection)
        queued = 0
        if settings.notes_sync_on_start:
            queued = enqueue_monthly_jobs(
                connection,
                slot=monthly_slot(now, settings.notes_sync_timezone),
                trigger_type="startup",
                max_attempts=settings.notes_worker_max_attempts,
            )
        connection.commit()
    logger.info(
        "Fuentes=%s, notas recuperadas=%s, análisis recuperados=%s, encolados=%s",
        len(sources),
        recovered,
        recovered_analyses,
        queued,
    )
    return queued


def enqueue_if_due(now: datetime) -> int:
    settings = get_settings()
    if not monthly_sync_due(
        now,
        day=settings.notes_sync_day,
        hour=settings.notes_sync_hour,
        timezone_name=settings.notes_sync_timezone,
    ):
        return 0
    with connect() as connection:
        queued = enqueue_monthly_jobs(
            connection,
            slot=monthly_slot(now, settings.notes_sync_timezone),
            trigger_type="monthly",
            max_attempts=settings.notes_worker_max_attempts,
        )
        connection.commit()
    return queued


def sync_available_jobs() -> list[dict[str, object]]:
    settings = get_settings()
    initialize()
    results: list[dict[str, object]] = []
    while True:
        result = process_next_job(settings)
        if result is None:
            return results
        results.append(result)


def run(*, once: bool = False) -> None:
    settings = get_settings()
    initialize()
    while running:
        enqueue_if_due(datetime.now(UTC))
        try:
            analysis = process_next_analysis_job(settings)
            if analysis:
                logger.info("Análisis procesado: %s", analysis)
                continue
            result = process_next_job(settings)
            if result:
                logger.info("Notas sincronizadas: %s", result)
                continue
        except Exception:
            logger.exception("Falló una sincronización de notas; se reintentará según la cola")
        if once:
            break
        time.sleep(settings.notes_worker_poll_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(description="Worker automático de notas financieras")
    parser.add_argument("--once", action="store_true", help="Ejecuta un ciclo para validación")
    args = parser.parse_args()
    signal.signal(signal.SIGTERM, _stop_worker)
    signal.signal(signal.SIGINT, _stop_worker)
    run(once=args.once)


if __name__ == "__main__":
    main()
