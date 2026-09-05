from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from threading import Event
from typing import Any

from psycopg import Connection

from app.cited_summaries import sync_cited_summaries
from app.config import Settings
from app.db import connect
from app.ingestion import filter_company_rows, store_statement
from app.metrics import calculate_and_store_metrics
from app.narrative_comparisons import sync_narrative_comparisons
from app.normalization import normalize_text
from app.notes import download_pdf, store_note_document
from app.smv.client import SmvClient, SmvResponse

logger = logging.getLogger("fundamenta.company-analysis")

STATEMENT_TYPES = ("balance_sheet", "income_statement", "cash_flow")
ANALYSIS_STEPS = ("statements", "metrics", "documents", "summaries")
ACTIVE_JOB_STATUSES = ("queued", "running", "retrying")
KNOWN_MINING_RPJS = frozenset(
    {"B20003", "A20032", "CM0001", "B20041", "CM0006", "B20010", "B20026", "CM0004"}
)
FINANCIAL_HINTS = (
    "banco",
    "bank",
    "seguro",
    "asegur",
    "financiera",
    "afp",
    "fondo de inversion",
    "fondo mutuo",
)
MINING_HINTS = ("miner", "mining", "extraccion de minerales", "metalif")


class AnalysisNotSupportedError(ValueError):
    pass


class AnalysisQuotaError(ValueError):
    pass


class AnalysisReviewRequiredError(RuntimeError):
    pass


def classify_support(company: dict[str, Any]) -> str:
    rpj = str(company.get("smv_rpj") or company.get("RPJ") or "").strip()
    ciiu = str(company.get("ciiu") or company.get("CIIU") or "").strip()
    searchable = normalize_text(
        " ".join(
            str(company.get(key) or "")
            for key in (
                "legal_name",
                "NombreEmpresa",
                "company_type",
                "TipoEmpresa",
                "sector",
                "TipoSector",
            )
        )
    ).lower()
    if rpj in KNOWN_MINING_RPJS or ciiu.startswith(("07", "08")):
        return "full"
    if any(hint in searchable for hint in MINING_HINTS):
        return "full"
    if ciiu.startswith(("64", "65", "66")) or any(
        hint in searchable for hint in FINANCIAL_HINTS
    ):
        return "unsupported"
    return "basic"


def merge_catalog_rows(
    responses: list[tuple[str, SmvResponse]],
) -> list[dict[str, Any]]:
    companies: dict[str, dict[str, Any]] = {}
    for scope, response in responses:
        for row in response.rows:
            rpj = str(row.get("RPJ") or "").strip()
            legal_name = " ".join(str(row.get("NombreEmpresa") or "").split())
            if not rpj or not legal_name:
                continue
            company = companies.setdefault(
                rpj,
                {
                    "smv_rpj": rpj,
                    "ruc": row.get("RUC"),
                    "legal_name": legal_name,
                    "company_type": row.get("TipoEmpresa"),
                    "sector": row.get("TipoSector"),
                    "ciiu": row.get("CIIU"),
                    "available_scopes": set(),
                },
            )
            company["available_scopes"].add(scope)

    result: list[dict[str, Any]] = []
    for company in companies.values():
        scopes = company.pop("available_scopes")
        company["available_scopes"] = sorted(
            scopes, key=lambda item: (item != "consolidated", item)
        )
        company["preferred_scope"] = (
            "consolidated" if "consolidated" in scopes else "individual"
        )
        company["support_level"] = classify_support(company)
        result.append(company)
    return sorted(result, key=lambda item: normalize_text(item["legal_name"]).lower())


def sync_company_catalog(settings: Settings) -> dict[str, Any]:
    client = SmvClient(settings.smv_base_url, settings.smv_timeout_seconds)
    responses = [
        (
            scope,
            client.fetch_statement(
                statement_type="balance_sheet",
                fiscal_year=settings.company_analysis_fiscal_year,
                period_code="A",
                scope_code=scope_code,
            ),
        )
        for scope, scope_code in (("consolidated", "C"), ("individual", "I"))
    ]
    catalog = merge_catalog_rows(responses)
    with connect() as connection, connection.cursor() as cursor:
        for company in catalog:
            cursor.execute(
                """
                INSERT INTO companies (smv_rpj, ruc, legal_name, company_type, sector, ciiu)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (smv_rpj) DO UPDATE SET
                    ruc = EXCLUDED.ruc,
                    legal_name = EXCLUDED.legal_name,
                    company_type = EXCLUDED.company_type,
                    sector = EXCLUDED.sector,
                    ciiu = EXCLUDED.ciiu,
                    updated_at = NOW()
                RETURNING id
                """,
                (
                    company["smv_rpj"],
                    company["ruc"],
                    company["legal_name"],
                    company["company_type"],
                    company["sector"],
                    company["ciiu"],
                ),
            )
            company_id = cursor.fetchone()["id"]
            initial_status = (
                "unsupported" if company["support_level"] == "unsupported" else "not_analyzed"
            )
            cursor.execute(
                """
                INSERT INTO company_coverage (
                    company_id, support_level, analysis_status, preferred_scope,
                    available_scopes, latest_fiscal_year
                ) VALUES (%s, %s, %s, %s, %s::jsonb, %s)
                ON CONFLICT (company_id) DO UPDATE SET
                    support_level = EXCLUDED.support_level,
                    analysis_status = CASE
                        WHEN company_coverage.analysis_status IN (
                            'available', 'partial', 'queued', 'processing',
                            'review_required', 'failed'
                        ) THEN company_coverage.analysis_status
                        ELSE EXCLUDED.analysis_status
                    END,
                    preferred_scope = CASE
                        WHEN company_coverage.preferred_scope IS NOT NULL
                             AND EXCLUDED.available_scopes ? company_coverage.preferred_scope
                            THEN company_coverage.preferred_scope
                        ELSE EXCLUDED.preferred_scope
                    END,
                    available_scopes = EXCLUDED.available_scopes,
                    latest_fiscal_year = COALESCE(
                        company_coverage.latest_fiscal_year, EXCLUDED.latest_fiscal_year
                    ),
                    updated_at = NOW()
                """,
                (
                    company_id,
                    company["support_level"],
                    initial_status,
                    company["preferred_scope"],
                    json.dumps(company["available_scopes"]),
                    settings.company_analysis_fiscal_year,
                ),
            )
        connection.commit()
    return {
        "fiscal_year": settings.company_analysis_fiscal_year,
        "companies": len(catalog),
        "full": sum(item["support_level"] == "full" for item in catalog),
        "basic": sum(item["support_level"] == "basic" for item in catalog),
        "unsupported": sum(item["support_level"] == "unsupported" for item in catalog),
    }


def _company_select(where_clause: str) -> str:
    return f"""
        SELECT
            c.smv_rpj, c.ruc, c.legal_name, c.company_type, c.sector, c.ciiu,
            c.updated_at,
            COALESCE(cc.support_level, 'basic') AS support_level,
            COALESCE(cc.analysis_status, 'not_analyzed') AS analysis_status,
            cc.preferred_scope,
            COALESCE(cc.available_scopes, '[]'::jsonb) AS available_scopes,
            cc.latest_fiscal_year,
            COALESCE(cc.completed_steps, '[]'::jsonb) AS completed_steps,
            COALESCE(cc.validation_tier, 'automatic') AS validation_tier,
            cc.last_error, cc.last_requested_at, cc.last_completed_at,
            COALESCE(filing_stats.filings_count, 0) AS filings_count,
            COALESCE(filing_stats.failed_validations, 0) AS failed_validations,
            COALESCE(metric_stats.metrics_count, 0) > 0 AS has_analysis,
            latest_job.id AS job_id,
            latest_job.status AS job_status,
            latest_job.current_step AS job_current_step,
            latest_job.progress AS job_progress
        FROM companies c
        LEFT JOIN company_coverage cc ON cc.company_id = c.id
        LEFT JOIN LATERAL (
            SELECT
                COUNT(DISTINCT f.id)::integer AS filings_count,
                COUNT(vr.id) FILTER (WHERE vr.status = 'failed')::integer
                    AS failed_validations
            FROM filings f
            LEFT JOIN validation_results vr ON vr.filing_id = f.id
            WHERE f.company_id = c.id
              AND (cc.latest_fiscal_year IS NULL OR f.fiscal_year = cc.latest_fiscal_year)
              AND (cc.preferred_scope IS NULL OR f.scope = cc.preferred_scope)
        ) filing_stats ON TRUE
        LEFT JOIN LATERAL (
            SELECT COUNT(*)::integer AS metrics_count
            FROM metric_values mv
            WHERE mv.company_id = c.id
              AND (cc.latest_fiscal_year IS NULL OR mv.fiscal_year = cc.latest_fiscal_year)
              AND (cc.preferred_scope IS NULL OR mv.scope = cc.preferred_scope)
        ) metric_stats ON TRUE
        LEFT JOIN LATERAL (
            SELECT aj.id, aj.status, aj.current_step, aj.progress
            FROM analysis_jobs aj
            WHERE aj.company_id = c.id
            ORDER BY (aj.status IN ('queued', 'running', 'retrying')) DESC, aj.created_at DESC
            LIMIT 1
        ) latest_job ON TRUE
        {where_clause}
    """


def list_catalog_companies(connection: Connection) -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute(_company_select("ORDER BY c.legal_name"))
        return list(cursor.fetchall())


def get_catalog_company(connection: Connection, smv_rpj: str) -> dict[str, Any] | None:
    with connection.cursor() as cursor:
        cursor.execute(_company_select("WHERE c.smv_rpj = %s"), (smv_rpj,))
        return cursor.fetchone()


def _job_steps(connection: Connection, job_id: int | None) -> list[dict[str, Any]]:
    if job_id is None:
        return []
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT step_code, step_order, status, started_at, completed_at,
                   details, error_message
            FROM analysis_job_steps
            WHERE job_id = %s
            ORDER BY step_order
            """,
            (job_id,),
        )
        return list(cursor.fetchall())


def get_company_analysis(connection: Connection, smv_rpj: str) -> dict[str, Any] | None:
    company = get_catalog_company(connection, smv_rpj)
    if company is None:
        return None
    job_id = company.pop("job_id")
    job_status = company.pop("job_status")
    job_current_step = company.pop("job_current_step")
    job_progress = company.pop("job_progress")
    job = None
    if job_id is not None:
        job = {
            "id": job_id,
            "status": job_status,
            "current_step": job_current_step,
            "progress": job_progress,
            "steps": _job_steps(connection, job_id),
        }
    return {"company": company, "job": job}


def request_company_analysis(
    connection: Connection,
    *,
    smv_rpj: str,
    user_id: int,
    fiscal_year: int,
    scope: str | None,
    max_attempts: int,
    active_jobs_per_user: int,
) -> tuple[dict[str, Any], bool]:
    lock_key = f"company-analysis:{smv_rpj}:{fiscal_year}"
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (lock_key,))
        cursor.execute(
            """
            SELECT c.id, cc.support_level, cc.preferred_scope, cc.available_scopes
            FROM companies c
            JOIN company_coverage cc ON cc.company_id = c.id
            WHERE c.smv_rpj = %s
            FOR UPDATE OF cc
            """,
            (smv_rpj,),
        )
        company = cursor.fetchone()
        if company is None:
            raise ValueError("La empresa no existe en el catálogo sincronizado")
        if company["support_level"] == "unsupported":
            raise AnalysisNotSupportedError(
                "El sector de esta empresa todavía no es compatible con el análisis automático"
            )

        selected_scope = scope or company["preferred_scope"]
        available_scopes = company["available_scopes"] or []
        if selected_scope not in ("individual", "consolidated"):
            raise ValueError("La empresa no tiene un alcance financiero disponible")
        if available_scopes and selected_scope not in available_scopes:
            raise ValueError("El alcance solicitado no está disponible para esta empresa")

        cursor.execute(
            """
            SELECT id
            FROM analysis_jobs
            WHERE company_id = %s AND fiscal_year = %s AND period_code = 'A'
              AND scope = %s AND status IN ('queued', 'running', 'retrying')
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (company["id"], fiscal_year, selected_scope),
        )
        active = cursor.fetchone()
        if active is not None:
            result = get_company_analysis(connection, smv_rpj)
            assert result is not None
            return result, True

        cursor.execute(
            """
            SELECT COUNT(*) AS active_jobs
            FROM analysis_jobs
            WHERE requested_by = %s AND status IN ('queued', 'running', 'retrying')
            """,
            (user_id,),
        )
        if cursor.fetchone()["active_jobs"] >= active_jobs_per_user:
            raise AnalysisQuotaError(
                "Alcanzaste el límite de análisis simultáneos; espera a que termine uno"
            )

        cursor.execute(
            """
            INSERT INTO analysis_jobs (
                company_id, requested_by, fiscal_year, period_code, scope,
                trigger_type, max_attempts
            ) VALUES (%s, %s, %s, 'A', %s, 'user', %s)
            RETURNING id
            """,
            (company["id"], user_id, fiscal_year, selected_scope, max_attempts),
        )
        job_id = cursor.fetchone()["id"]
        for order, step in enumerate(ANALYSIS_STEPS, start=1):
            cursor.execute(
                """
                INSERT INTO analysis_job_steps (job_id, step_code, step_order)
                VALUES (%s, %s, %s)
                """,
                (job_id, step, order),
            )
        cursor.execute(
            """
            UPDATE company_coverage
            SET analysis_status = 'queued', preferred_scope = %s,
                latest_fiscal_year = %s, last_requested_at = NOW(),
                last_error = NULL, updated_at = NOW()
            WHERE company_id = %s
            """,
            (selected_scope, fiscal_year, company["id"]),
        )

    result = get_company_analysis(connection, smv_rpj)
    assert result is not None
    return result, False


def recover_stale_analysis_jobs(connection: Connection) -> int:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE analysis_jobs
            SET status = 'retrying', next_retry_at = NOW(), updated_at = NOW(),
                error_message = 'El worker se reinició durante la ejecución anterior'
            WHERE status = 'running'
              AND updated_at < NOW() - INTERVAL '30 minutes'
            """
        )
        return cursor.rowcount


def _claim_next_job(connection: Connection) -> dict[str, Any] | None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            WITH candidate AS (
                SELECT id
                FROM analysis_jobs
                WHERE status IN ('queued', 'retrying')
                  AND scheduled_for <= NOW()
                  AND (next_retry_at IS NULL OR next_retry_at <= NOW())
                ORDER BY scheduled_for, id
                FOR UPDATE SKIP LOCKED
                LIMIT 1
            )
            UPDATE analysis_jobs job
            SET status = 'running', attempts = attempts + 1, started_at = NOW(),
                next_retry_at = NULL, updated_at = NOW(), error_message = NULL
            FROM candidate
            WHERE job.id = candidate.id
            RETURNING job.*
            """
        )
        job = cursor.fetchone()
        if job is None:
            return None
        cursor.execute(
            """
            UPDATE company_coverage
            SET analysis_status = 'processing', last_error = NULL, updated_at = NOW()
            WHERE company_id = %s
            """,
            (job["company_id"],),
        )
        cursor.execute(
            """
            SELECT c.smv_rpj, c.legal_name, cc.support_level
            FROM companies c
            JOIN company_coverage cc ON cc.company_id = c.id
            WHERE c.id = %s
            """,
            (job["company_id"],),
        )
        job.update(cursor.fetchone())
        return job


def _step_status(connection: Connection, job_id: int, step_code: str) -> str:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT status FROM analysis_job_steps WHERE job_id = %s AND step_code = %s",
            (job_id, step_code),
        )
        return cursor.fetchone()["status"]


def _start_step(connection: Connection, job_id: int, step_code: str, progress: int) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE analysis_job_steps
            SET status = 'running', started_at = NOW(), completed_at = NULL,
                error_message = NULL, updated_at = NOW()
            WHERE job_id = %s AND step_code = %s
            """,
            (job_id, step_code),
        )
        cursor.execute(
            """
            UPDATE analysis_jobs
            SET current_step = %s, progress = %s, updated_at = NOW()
            WHERE id = %s
            """,
            (step_code, progress, job_id),
        )


def _finish_step(
    connection: Connection,
    job: dict[str, Any],
    step_code: str,
    *,
    details: dict[str, Any],
    skipped: bool = False,
    progress: int,
) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE analysis_job_steps
            SET status = %s, completed_at = NOW(), details = %s::jsonb,
                error_message = NULL, updated_at = NOW()
            WHERE job_id = %s AND step_code = %s
            """,
            ("skipped" if skipped else "completed", json.dumps(details), job["id"], step_code),
        )
        cursor.execute(
            """
            UPDATE analysis_jobs SET progress = %s, updated_at = NOW() WHERE id = %s
            """,
            (progress, job["id"]),
        )
        if not skipped:
            cursor.execute(
                """
                UPDATE company_coverage
                SET completed_steps = CASE
                        WHEN completed_steps @> %s::jsonb THEN completed_steps
                        ELSE completed_steps || %s::jsonb
                    END,
                    analysis_status = 'partial', latest_fiscal_year = %s,
                    preferred_scope = %s, updated_at = NOW()
                WHERE company_id = %s
                """,
                (
                    json.dumps([step_code]),
                    json.dumps([step_code]),
                    job["fiscal_year"],
                    job["scope"],
                    job["company_id"],
                ),
            )


def _scale_context(
    connection: Connection, job: dict[str, Any], statement_type: str, payload_sha256: str
) -> tuple[str, str | None]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT reported_scale, scale_source_url
            FROM filings JOIN source_fetches sf ON sf.id = filings.source_fetch_id
            WHERE company_id = %s AND fiscal_year = %s AND period_code = %s
              AND scope = %s AND statement_type = %s AND reported_scale <> 'unknown'
              AND sf.payload_sha256 = %s
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            (job["company_id"], job["fiscal_year"], job["period_code"], job["scope"],
             statement_type, payload_sha256),
        )
        filing = cursor.fetchone()
        if filing is not None:
            return filing["reported_scale"], filing["scale_source_url"]
    return "unknown", None


def _process_statements(settings: Settings, job: dict[str, Any]) -> dict[str, Any]:
    client = SmvClient(settings.smv_base_url, settings.smv_timeout_seconds)
    scope_code = "C" if job["scope"] == "consolidated" else "I"
    stored: list[dict[str, Any]] = []
    for statement_type in STATEMENT_TYPES:
        response = client.fetch_statement(
            statement_type=statement_type,
            fiscal_year=job["fiscal_year"],
            period_code=job["period_code"],
            scope_code=scope_code,
        )
        rows = filter_company_rows(response.rows, job["smv_rpj"])
        with connect() as connection:
            reported_scale, scale_source_url = _scale_context(
                connection, job, statement_type, response.payload_sha256
            )
            result = store_statement(
                connection=connection,
                response=response,
                rows=rows,
                statement_type=statement_type,
                fiscal_year=job["fiscal_year"],
                period_code=job["period_code"],
                scope_code=scope_code,
                reported_scale=reported_scale,
                scale_source_url=scale_source_url,
            )
            connection.commit()
        stored.append({"statement_type": statement_type, **result})

    failed = [
        validation
        for statement in stored
        for validation in statement["validations"]
        if validation["status"] == "failed"
    ]
    if failed:
        raise AnalysisReviewRequiredError(
            f"{len(failed)} validaciones críticas requieren revisión"
        )
    return {"statements": len(stored), "facts": sum(item["facts"] for item in stored)}


def _process_metrics(job: dict[str, Any]) -> dict[str, Any]:
    with connect() as connection:
        result = calculate_and_store_metrics(
            connection=connection,
            smv_rpj=job["smv_rpj"],
            fiscal_year=job["fiscal_year"],
            period_code=job["period_code"],
            scope=job["scope"],
        )
        connection.commit()
    if result["computed"] == 0:
        raise AnalysisReviewRequiredError(
            "No fue posible calcular una métrica compatible con los conceptos disponibles"
        )
    return {"computed": result["computed"], "not_available": result["not_available"]}


def _process_documents(settings: Settings, job: dict[str, Any]) -> dict[str, Any]:
    from app.document_scale import verify_company_scales

    with connect() as connection:
        scale_result = verify_company_scales(connection, job, settings)
        if scale_result["verified"]:
            calculate_and_store_metrics(
                connection, job["smv_rpj"], job["fiscal_year"],
                job["period_code"], job["scope"],
            )
        connection.commit()
    with connect() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT ns.*, c.smv_rpj
            FROM note_sources ns
            JOIN companies c ON c.id = ns.company_id
            WHERE ns.company_id = %s AND ns.period_code = %s AND ns.scope = %s
              AND ns.fiscal_year IN (%s, %s) AND ns.enabled
            ORDER BY ns.fiscal_year DESC
            """,
            (
                job["company_id"],
                job["period_code"],
                job["scope"],
                job["fiscal_year"],
                job["fiscal_year"] - 1,
            ),
        )
        sources = list(cursor.fetchall())
    if not sources:
        return {"available": False, "reason": "No existe una fuente documental verificada",
                "scale_verification": scale_result}

    documents = []
    for source in sources:
        pdf_bytes = download_pdf(
            source["source_url"],
            timeout_seconds=settings.notes_http_timeout_seconds,
            max_bytes=settings.notes_max_pdf_bytes,
        )
        with connect() as connection:
            result = store_note_document(connection, source=source, pdf_bytes=pdf_bytes)
            connection.commit()
        documents.append({"fiscal_year": source["fiscal_year"], **result})
    return {"available": True, "documents": documents, "scale_verification": scale_result}


def _process_summaries() -> dict[str, Any]:
    with connect() as connection:
        summaries = sync_cited_summaries(connection)
        comparisons = sync_narrative_comparisons(connection)
        connection.commit()
    return {"summaries": summaries, "comparisons": comparisons}


def _mark_review_required(
    connection: Connection, job: dict[str, Any], message: str, result: dict[str, Any]
) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE analysis_jobs
            SET status = 'review_required', completed_at = NOW(), error_message = %s,
                result = %s::jsonb, updated_at = NOW()
            WHERE id = %s
            """,
            (message[:1000], json.dumps(result), job["id"]),
        )
        cursor.execute(
            """
            UPDATE company_coverage
            SET analysis_status = 'review_required', last_error = %s,
                last_completed_at = NOW(), updated_at = NOW()
            WHERE company_id = %s
            """,
            (message[:1000], job["company_id"]),
        )


def _mark_completed(
    connection: Connection,
    job: dict[str, Any],
    result: dict[str, Any],
    *,
    documents_available: bool,
) -> None:
    coverage_status = "available" if documents_available else "partial"
    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE analysis_jobs
            SET status = 'completed', current_step = 'complete', progress = 100,
                completed_at = NOW(), error_message = NULL, result = %s::jsonb,
                updated_at = NOW()
            WHERE id = %s
            """,
            (json.dumps(result), job["id"]),
        )
        cursor.execute(
            """
            UPDATE company_coverage
            SET analysis_status = %s, last_error = NULL, last_completed_at = NOW(),
                updated_at = NOW()
            WHERE company_id = %s
            """,
            (coverage_status, job["company_id"]),
        )


def _retry_delay(attempts: int) -> timedelta:
    return timedelta(minutes=min(2 ** max(attempts - 1, 0), 30))


def _mark_failed(connection: Connection, job: dict[str, Any], error: Exception) -> str:
    exhausted = job["attempts"] >= job["max_attempts"]
    status = "failed" if exhausted else "retrying"
    next_retry_at = None if exhausted else datetime.now(UTC) + _retry_delay(job["attempts"])
    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE analysis_jobs
            SET status = %s, next_retry_at = %s, completed_at = %s,
                error_message = %s, updated_at = NOW()
            WHERE id = %s
            """,
            (
                status,
                next_retry_at,
                datetime.now(UTC) if exhausted else None,
                str(error)[:1000],
                job["id"],
            ),
        )
        cursor.execute(
            """
            UPDATE analysis_job_steps
            SET status = 'failed', error_message = %s, completed_at = NOW(), updated_at = NOW()
            WHERE job_id = %s AND status = 'running'
            """,
            (str(error)[:1000], job["id"]),
        )
        cursor.execute(
            """
            UPDATE company_coverage
            SET analysis_status = %s, last_error = %s, updated_at = NOW()
            WHERE company_id = %s
            """,
            ("failed" if exhausted else "queued", str(error)[:1000], job["company_id"]),
        )
    return status


def process_next_analysis_job(settings: Settings) -> dict[str, Any] | None:
    with connect() as connection:
        recovered = recover_stale_analysis_jobs(connection)
        job = _claim_next_job(connection)
        connection.commit()
    if recovered:
        logger.info("Trabajos de análisis recuperados: %s", recovered)
    if job is None:
        return None

    result: dict[str, Any] = {}
    documents_available = False
    try:
        with connect() as connection:
            if _step_status(connection, job["id"], "statements") != "completed":
                _start_step(connection, job["id"], "statements", 5)
                connection.commit()
                details = _process_statements(settings, job)
                _finish_step(
                    connection, job, "statements", details=details, progress=40
                )
                connection.commit()
                result["statements"] = details

            if _step_status(connection, job["id"], "metrics") != "completed":
                _start_step(connection, job["id"], "metrics", 45)
                connection.commit()
                details = _process_metrics(job)
                _finish_step(connection, job, "metrics", details=details, progress=65)
                connection.commit()
                result["metrics"] = details

            document_status = _step_status(connection, job["id"], "documents")
            if document_status not in ("completed", "skipped"):
                _start_step(connection, job["id"], "documents", 70)
                connection.commit()
                details = _process_documents(settings, job)
                documents_available = bool(details["available"])
                _finish_step(
                    connection,
                    job,
                    "documents",
                    details=details,
                    skipped=not documents_available,
                    progress=85,
                )
                connection.commit()
                result["documents"] = details
            else:
                documents_available = document_status == "completed"

            summary_status = _step_status(connection, job["id"], "summaries")
            if summary_status not in ("completed", "skipped"):
                _start_step(connection, job["id"], "summaries", 90)
                connection.commit()
                if documents_available:
                    details = _process_summaries()
                    _finish_step(
                        connection, job, "summaries", details=details, progress=100
                    )
                else:
                    details = {"reason": "La etapa documental todavía no está disponible"}
                    _finish_step(
                        connection,
                        job,
                        "summaries",
                        details=details,
                        skipped=True,
                        progress=100,
                    )
                connection.commit()
                result["summaries"] = details

            if job["support_level"] == "full" and not documents_available:
                _mark_review_required(
                    connection,
                    job,
                    (
                        "Los estados y métricas están disponibles, pero falta verificar "
                        "la fuente de notas"
                    ),
                    result,
                )
                connection.commit()
                return {"job_id": job["id"], "status": "review_required", **result}

            _mark_completed(
                connection,
                job,
                result,
                documents_available=documents_available,
            )
            connection.commit()
        return {"job_id": job["id"], "status": "completed", **result}
    except AnalysisReviewRequiredError as error:
        with connect() as connection:
            _mark_review_required(connection, job, str(error), result)
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE analysis_job_steps
                    SET status = 'failed', error_message = %s, completed_at = NOW(),
                        updated_at = NOW()
                    WHERE job_id = %s AND status = 'running'
                    """,
                    (str(error)[:1000], job["id"]),
                )
            connection.commit()
        return {"job_id": job["id"], "status": "review_required", "error": str(error)}
    except Exception as error:
        logger.exception("Falló el análisis de %s", job["smv_rpj"])
        with connect() as connection:
            status = _mark_failed(connection, job, error)
            connection.commit()
        return {"job_id": job["id"], "status": status, "error": str(error)}


def run_analysis_worker(stop_event: Event, settings: Settings) -> None:
    try:
        with connect() as connection:
            recovered = recover_stale_analysis_jobs(connection)
            connection.commit()
        if recovered:
            logger.info("Trabajos de análisis recuperados: %s", recovered)
    except Exception:
        logger.exception("No se pudo ejecutar la recuperación inicial de análisis")
    while not stop_event.is_set():
        try:
            result = process_next_analysis_job(settings)
            if result is not None:
                logger.info("Trabajo de análisis procesado: %s", result)
                continue
        except Exception:
            logger.exception("El worker de análisis continuará después de un error")
        stop_event.wait(settings.analysis_worker_poll_seconds)
