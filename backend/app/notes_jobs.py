from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from psycopg import Connection

from app.config import Settings
from app.db import connect
from app.notes import NoteSourceConfig, download_pdf, store_note_document


def monthly_slot(now: datetime, timezone_name: str) -> str:
    local_now = now.astimezone(ZoneInfo(timezone_name))
    return local_now.strftime("%Y-%m")


def monthly_sync_due(now: datetime, *, day: int, hour: int, timezone_name: str) -> bool:
    local_now = now.astimezone(ZoneInfo(timezone_name))
    return local_now.day >= day and local_now.hour >= hour


def retry_delay(attempts: int) -> timedelta:
    return timedelta(minutes=min(5 * (2 ** max(attempts - 1, 0)), 60))


def register_note_sources(
    connection: Connection, sources: tuple[NoteSourceConfig, ...]
) -> list[dict[str, Any]]:
    registered: list[dict[str, Any]] = []
    with connection.cursor() as cursor:
        for source in sources:
            cursor.execute("SELECT id FROM companies WHERE smv_rpj = %s", (source.company_rpj,))
            company = cursor.fetchone()
            if company is None:
                raise ValueError(f"No existe la empresa RPJ {source.company_rpj}")
            cursor.execute(
                """
                INSERT INTO note_sources (
                    company_id, source_key, fiscal_year, period_code, scope,
                    language_code, document_name, source_url, identity_tokens
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (source_key) DO UPDATE SET
                    company_id = EXCLUDED.company_id,
                    fiscal_year = EXCLUDED.fiscal_year,
                    period_code = EXCLUDED.period_code,
                    scope = EXCLUDED.scope,
                    language_code = EXCLUDED.language_code,
                    document_name = EXCLUDED.document_name,
                    source_url = EXCLUDED.source_url,
                    identity_tokens = EXCLUDED.identity_tokens,
                    enabled = TRUE,
                    updated_at = NOW()
                RETURNING id, source_key
                """,
                (
                    company["id"],
                    source.source_key,
                    source.fiscal_year,
                    source.period_code,
                    source.scope,
                    source.language_code,
                    source.document_name,
                    source.source_url,
                    json.dumps(source.identity_tokens),
                ),
            )
            registered.append(cursor.fetchone())
    return registered


def enqueue_monthly_jobs(
    connection: Connection,
    *,
    slot: str,
    trigger_type: str,
    max_attempts: int,
) -> int:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO ingestion_jobs (
                job_type, note_source_id, dedupe_key, trigger_type, max_attempts
            )
            SELECT
                'notes_sync', ns.id, 'notes:' || ns.source_key || ':' || %s,
                %s, %s
            FROM note_sources ns
            WHERE ns.enabled
            ON CONFLICT (dedupe_key) DO NOTHING
            """,
            (slot, trigger_type, max_attempts),
        )
        return cursor.rowcount


def recover_stale_jobs(connection: Connection) -> int:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE ingestion_jobs
            SET status = 'retrying', next_retry_at = NOW(), updated_at = NOW(),
                error_message = 'El worker se reinició durante la ejecución anterior'
            WHERE job_type = 'notes_sync'
              AND status = 'running'
              AND started_at < NOW() - INTERVAL '15 minutes'
            """
        )
        return cursor.rowcount


def claim_next_job(connection: Connection) -> dict[str, Any] | None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            WITH candidate AS (
                SELECT id
                FROM ingestion_jobs
                WHERE job_type = 'notes_sync'
                  AND status IN ('queued', 'retrying')
                  AND scheduled_for <= NOW()
                  AND (next_retry_at IS NULL OR next_retry_at <= NOW())
                ORDER BY scheduled_for, id
                FOR UPDATE SKIP LOCKED
                LIMIT 1
            )
            UPDATE ingestion_jobs job
            SET status = 'running', attempts = attempts + 1,
                started_at = NOW(), updated_at = NOW(), error_message = NULL
            FROM candidate
            WHERE job.id = candidate.id
            RETURNING job.*
            """
        )
        return cursor.fetchone()


def get_job_source(connection: Connection, note_source_id: int) -> dict[str, Any]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT ns.*, c.smv_rpj
            FROM note_sources ns
            JOIN companies c ON c.id = ns.company_id
            WHERE ns.id = %s AND ns.enabled
            """,
            (note_source_id,),
        )
        source = cursor.fetchone()
    if source is None:
        raise ValueError("La fuente de notas no existe o está deshabilitada")
    return source


def mark_job_completed(connection: Connection, job_id: int, result: dict[str, Any]) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE ingestion_jobs
            SET status = 'completed', completed_at = NOW(), next_retry_at = NULL,
                result = %s::jsonb, updated_at = NOW()
            WHERE id = %s
            """,
            (json.dumps(result), job_id),
        )


def mark_job_failed(connection: Connection, job: dict[str, Any], error: Exception) -> None:
    exhausted = job["attempts"] >= job["max_attempts"]
    next_retry_at = None
    if not exhausted:
        next_retry_at = datetime.now(UTC) + retry_delay(job["attempts"])
    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE ingestion_jobs
            SET status = %s, next_retry_at = %s, completed_at = %s,
                error_message = %s, updated_at = NOW()
            WHERE id = %s
            """,
            (
                "failed" if exhausted else "retrying",
                next_retry_at,
                datetime.now(UTC) if exhausted else None,
                str(error)[:1000],
                job["id"],
            ),
        )


def process_next_job(settings: Settings) -> dict[str, Any] | None:
    with connect() as connection:
        job = claim_next_job(connection)
        connection.commit()
    if job is None:
        return None

    try:
        with connect() as connection:
            source = get_job_source(connection, job["note_source_id"])
        pdf_bytes = download_pdf(
            source["source_url"],
            timeout_seconds=settings.notes_http_timeout_seconds,
            max_bytes=settings.notes_max_pdf_bytes,
        )
        with connect() as connection:
            result = store_note_document(connection, source=source, pdf_bytes=pdf_bytes)
            mark_job_completed(connection, job["id"], result)
            connection.commit()
        return {"job_id": job["id"], "source_key": source["source_key"], **result}
    except Exception as error:
        with connect() as connection:
            mark_job_failed(connection, job, error)
            connection.commit()
        raise
