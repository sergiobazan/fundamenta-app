from __future__ import annotations

import argparse
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.cited_summaries import sync_cited_summaries
from app.config import (
    Settings,
    get_bootstrap_events_path,
    get_notes_sources_path,
    get_settings,
)
from app.db import connect
from app.events import import_events
from app.ingestion import filter_company_rows, store_statement
from app.metrics import calculate_and_store_metrics
from app.migrations import run_migrations
from app.narrative_comparisons import sync_narrative_comparisons
from app.notes import NoteSourceConfig, load_note_sources
from app.notes_jobs import (
    enqueue_monthly_jobs,
    monthly_slot,
    process_next_job,
    register_note_sources,
)
from app.smv.client import SmvClient

logger = logging.getLogger("fundamenta.bootstrap")
BOOTSTRAP_LOCK_NAME = "fundamenta_initial_data_bootstrap"
COMPANY_RPJS = ("B20003", "A20032", "CM0001", "B20041")
STATEMENT_TYPES = ("balance_sheet", "income_statement", "cash_flow")


def is_bootstrap_complete(
    status: dict[str, Any], *, expected_events: int, expected_note_sources: int
) -> bool:
    return (
        status["companies"] == len(COMPANY_RPJS)
        and status["filings"] == len(COMPANY_RPJS) * len(STATEMENT_TYPES)
        and status["facts"] >= len(COMPANY_RPJS) * 150
        and status["computed_metrics"] == len(COMPANY_RPJS) * 15
        and status["unavailable_metrics"] == 0
        and status["failed_validations"] == 0
        and status["events"] >= expected_events
        and status["note_documents"] >= expected_note_sources
        and status["notes"] >= expected_note_sources * 5
    )


def _load_json_list(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"El archivo debe contener una lista JSON: {path}")
    return payload


def bootstrap_status(expected_events: int, expected_note_sources: int) -> dict[str, Any]:
    with connect() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM companies WHERE smv_rpj = ANY(%s)) AS companies,
                (SELECT COUNT(*) FROM filings f JOIN companies c ON c.id = f.company_id
                    WHERE c.smv_rpj = ANY(%s) AND f.fiscal_year = 2025
                      AND f.period_code = 'A' AND f.scope = 'consolidated'
                      AND f.statement_type = ANY(%s)) AS filings,
                (SELECT COUNT(*) FROM financial_facts ff JOIN filings f ON f.id = ff.filing_id
                    JOIN companies c ON c.id = f.company_id
                    WHERE c.smv_rpj = ANY(%s) AND f.fiscal_year = 2025
                      AND f.period_code = 'A' AND f.scope = 'consolidated') AS facts,
                (SELECT COUNT(*) FROM metric_values mv JOIN companies c ON c.id = mv.company_id
                    WHERE c.smv_rpj = ANY(%s) AND mv.fiscal_year = 2025
                      AND mv.period_code = 'A' AND mv.scope = 'consolidated'
                      AND mv.status = 'computed') AS computed_metrics,
                (SELECT COUNT(*) FROM metric_values mv JOIN companies c ON c.id = mv.company_id
                    WHERE c.smv_rpj = ANY(%s) AND mv.fiscal_year = 2025
                      AND mv.period_code = 'A' AND mv.scope = 'consolidated'
                      AND mv.status = 'not_available') AS unavailable_metrics,
                (SELECT COUNT(*) FROM validation_results vr JOIN filings f ON f.id = vr.filing_id
                    JOIN companies c ON c.id = f.company_id
                    WHERE c.smv_rpj = ANY(%s) AND f.fiscal_year = 2025
                      AND f.period_code = 'A' AND f.scope = 'consolidated'
                      AND vr.status = 'failed') AS failed_validations,
                (SELECT COUNT(*) FROM corporate_events ce JOIN companies c
                    ON c.id = ce.company_id
                    WHERE c.smv_rpj = ANY(%s) AND ce.is_current) AS events,
                (SELECT COUNT(*) FROM note_documents nd JOIN companies c
                    ON c.id = nd.company_id
                    WHERE c.smv_rpj = ANY(%s) AND nd.is_current) AS note_documents,
                (SELECT COUNT(*) FROM financial_notes fn JOIN note_documents nd
                    ON nd.id = fn.note_document_id JOIN companies c
                    ON c.id = nd.company_id
                    WHERE c.smv_rpj = ANY(%s) AND nd.is_current) AS notes
            """,
            (
                list(COMPANY_RPJS),
                list(COMPANY_RPJS),
                list(STATEMENT_TYPES),
                list(COMPANY_RPJS),
                list(COMPANY_RPJS),
                list(COMPANY_RPJS),
                list(COMPANY_RPJS),
                list(COMPANY_RPJS),
                list(COMPANY_RPJS),
                list(COMPANY_RPJS),
            ),
        )
        status = dict(cursor.fetchone())

    status["complete"] = is_bootstrap_complete(
        status,
        expected_events=expected_events,
        expected_note_sources=expected_note_sources,
    )
    return status


def ingest_initial_statements(
    settings: Settings, note_sources: tuple[NoteSourceConfig, ...]
) -> list[dict[str, Any]]:
    source_urls = {
        source.company_rpj: source.source_url
        for source in note_sources
        if source.fiscal_year == 2025
        and source.period_code == "A"
        and source.scope == "consolidated"
    }
    missing_urls = sorted(set(COMPANY_RPJS) - source_urls.keys())
    if missing_urls:
        raise ValueError(f"Faltan fuentes de escala para: {', '.join(missing_urls)}")

    client = SmvClient(settings.smv_base_url, settings.smv_timeout_seconds)
    results: list[dict[str, Any]] = []
    for statement_type in STATEMENT_TYPES:
        logger.info("Descargando %s 2025 consolidado desde la SMV", statement_type)
        response = client.fetch_statement(
            statement_type=statement_type,
            fiscal_year=2025,
            period_code="A",
            scope_code="C",
        )
        with connect() as connection:
            for company_rpj in COMPANY_RPJS:
                result = store_statement(
                    connection=connection,
                    response=response,
                    rows=filter_company_rows(response.rows, company_rpj),
                    statement_type=statement_type,
                    fiscal_year=2025,
                    period_code="A",
                    scope_code="C",
                    reported_scale="thousands",
                    scale_source_url=source_urls[company_rpj],
                )
                results.append({"company_rpj": company_rpj, "statement": statement_type, **result})
            connection.commit()
    return results


def calculate_initial_metrics() -> list[dict[str, Any]]:
    results = []
    for company_rpj in COMPANY_RPJS:
        with connect() as connection:
            result = calculate_and_store_metrics(
                connection=connection,
                smv_rpj=company_rpj,
                fiscal_year=2025,
                period_code="A",
                scope="consolidated",
            )
            connection.commit()
        results.append({"company_rpj": company_rpj, **result})
    return results


def import_initial_events(payloads: list[dict[str, Any]]) -> dict[str, Any]:
    with connect() as connection:
        result = import_events(connection, payloads)
        connection.commit()
    return result


def sync_initial_notes(
    settings: Settings, note_sources: tuple[NoteSourceConfig, ...]
) -> list[dict[str, Any]]:
    slot = monthly_slot(datetime.now(UTC), settings.notes_sync_timezone)
    with connect() as connection:
        register_note_sources(connection, note_sources)
        enqueue_monthly_jobs(
            connection,
            slot=slot,
            trigger_type="startup",
            max_attempts=settings.notes_worker_max_attempts,
        )
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE ingestion_jobs
                SET status = 'queued', attempts = 0, scheduled_for = NOW(),
                    next_retry_at = NULL, completed_at = NULL,
                    error_message = NULL, updated_at = NOW()
                WHERE dedupe_key LIKE %s AND status IN ('failed', 'retrying')
                """,
                (f"notes:%:{slot}",),
            )
        connection.commit()

    results: list[dict[str, Any]] = []
    while True:
        result = process_next_job(settings)
        if result is None:
            break
        results.append(result)
    return results


def sync_note_analyses() -> dict[str, Any]:
    """Actualiza derivados aunque los PDF no hayan cambiado en este ciclo."""
    with connect() as connection:
        summaries = sync_cited_summaries(connection)
        comparisons = sync_narrative_comparisons(connection)
        connection.commit()
    return {"summaries": summaries, "comparisons": comparisons}


def run_bootstrap(*, force: bool = False) -> dict[str, Any]:
    settings = get_settings()
    migrations = run_migrations()
    note_sources = load_note_sources(get_notes_sources_path())
    event_payloads = _load_json_list(get_bootstrap_events_path())

    with connect() as lock_connection:
        with lock_connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_lock(hashtext(%s))", (BOOTSTRAP_LOCK_NAME,))
        lock_connection.commit()
        try:
            before = bootstrap_status(len(event_payloads), len(note_sources))
            existing_note_analyses = sync_note_analyses()
            if before["complete"] and not force:
                return {
                    "status": "already_complete",
                    "migrations": migrations,
                    "before": before,
                    "after": before,
                    "note_analyses": existing_note_analyses,
                }

            statements = ingest_initial_statements(settings, note_sources)
            metrics = calculate_initial_metrics()
            events = import_initial_events(event_payloads)
            notes = sync_initial_notes(settings, note_sources)
            note_analyses = sync_note_analyses()
            after = bootstrap_status(len(event_payloads), len(note_sources))
            if not after["complete"]:
                raise RuntimeError(f"La verificación final del bootstrap falló: {after}")
            return {
                "status": "completed",
                "migrations": migrations,
                "before": before,
                "after": after,
                "loaded": {
                    "statements": len(statements),
                    "metrics": metrics,
                    "events": events,
                    "notes": notes,
                    "note_analyses": note_analyses,
                },
            }
        finally:
            with lock_connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_unlock(hashtext(%s))", (BOOTSTRAP_LOCK_NAME,))
            lock_connection.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Inicializa datos reales del MVP")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Actualiza todas las fuentes aunque el corte inicial esté completo",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    result = run_bootstrap(force=args.force)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
