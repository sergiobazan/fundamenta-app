import os
from contextlib import asynccontextmanager
from threading import Event, Thread
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Query, Response, status
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.auth import current_user_dependency
from app.auth import router as auth_router
from app.cited_summaries import fetch_cited_summary
from app.company_analysis import (
    AnalysisNotSupportedError,
    AnalysisQuotaError,
    get_catalog_company,
    get_company_analysis,
    list_catalog_companies,
    request_company_analysis,
)
from app.config import get_settings, get_upload_dir
from app.db import connect
from app.document_search import search_source_fragments
from app.narrative_comparisons import fetch_narrative_comparison

NoteTopic = Literal[
    "debt",
    "segments",
    "capex_assets",
    "impairment",
    "provisions_closure",
    "contingencies",
    "related_parties",
    "estimates",
    "subsequent_events",
    "other",
]


class CompanyAnalysisRequest(BaseModel):
    fiscal_year: int | None = Field(default=None, ge=2000, le=2100)
    scope: Literal["individual", "consolidated"] | None = None


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # `app.runtime` prepara producción antes de ejecutar Uvicorn. Este respaldo hace
    # que `uvicorn app.main:app --reload` también aplique migraciones y bootstrap.
    if os.environ.get("FUNDAMENTA_DATABASE_PREPARED") != "1":
        from app.runtime import prepare_database

        prepare_database("api")
    from app.company_analysis import run_analysis_worker
    from app.config import get_settings

    settings = get_settings()
    stop_event = Event()
    worker = None
    if settings.analysis_worker_enabled:
        worker = Thread(
            target=run_analysis_worker,
            args=(stop_event, settings),
            name="company-analysis-worker",
            daemon=True,
        )
        worker.start()
    try:
        yield
    finally:
        stop_event.set()
        if worker is not None:
            worker.join(timeout=min(settings.analysis_worker_poll_seconds + 1, 10))


app = FastAPI(title="Fundamenta API", version="0.3.0", lifespan=lifespan)
app.include_router(auth_router)

upload_dir = get_upload_dir()
upload_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads/avatars", StaticFiles(directory=upload_dir), name="avatars")


@app.get("/health")
def health() -> dict[str, str]:
    with connect() as connection, connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()
    return {"status": "ok"}


@app.get("/companies")
def companies() -> list[dict]:
    with connect() as connection:
        return list_catalog_companies(connection)


@app.get("/companies/{smv_rpj}")
def company_detail(smv_rpj: str) -> dict:
    with connect() as connection:
        company = get_catalog_company(connection, smv_rpj)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


@app.get("/companies/{smv_rpj}/analysis")
def company_analysis_status(smv_rpj: str) -> dict:
    with connect() as connection:
        analysis = get_company_analysis(connection, smv_rpj)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Company not found")
    return analysis


@app.post("/companies/{smv_rpj}/analysis")
def create_company_analysis(
    smv_rpj: str,
    payload: CompanyAnalysisRequest,
    response: Response,
    user: dict = current_user_dependency,
) -> dict:
    settings = get_settings()
    try:
        with connect() as connection:
            analysis, deduplicated = request_company_analysis(
                connection,
                smv_rpj=smv_rpj,
                user_id=user["id"],
                fiscal_year=payload.fiscal_year or settings.company_analysis_fiscal_year,
                scope=payload.scope,
                max_attempts=settings.analysis_worker_max_attempts,
                active_jobs_per_user=settings.analysis_active_jobs_per_user,
            )
            connection.commit()
    except AnalysisNotSupportedError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except AnalysisQuotaError as error:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(error)
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error
    response.status_code = status.HTTP_200_OK if deduplicated else status.HTTP_202_ACCEPTED
    return {**analysis, "deduplicated": deduplicated}


@app.get("/events")
def corporate_events(
    company_rpj: str | None = Query(default=None),
    category: Literal[
        "dividends",
        "management",
        "meetings",
        "debt",
        "operations",
        "litigation",
        "production",
        "other",
    ]
    | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
) -> list[dict]:
    conditions = ["ce.is_current"]
    parameters: list[object] = []
    if company_rpj:
        conditions.append("c.smv_rpj = %s")
        parameters.append(company_rpj)
    if category:
        conditions.append("ce.category = %s")
        parameters.append(category)
    parameters.append(limit)

    with connect() as connection, connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT
                ce.id, c.smv_rpj, c.legal_name, ce.source_provider,
                ce.external_id, ce.version, ce.category, ce.title, ce.summary,
                ce.published_at, ce.effective_date, ce.source_url,
                ce.source_document_name, ce.source_sha256, ce.retrieved_at
            FROM corporate_events ce
            JOIN companies c ON c.id = ce.company_id
            WHERE {' AND '.join(conditions)}
            ORDER BY ce.published_at DESC, ce.id DESC
            LIMIT %s
            """,
            parameters,
        )
        return list(cursor.fetchall())


@app.get("/search/fragments")
def document_fragments(
    q: Annotated[str, Query(min_length=2, max_length=100)],
    company_rpj: Annotated[str | None, Query(max_length=30)] = None,
    topic: Annotated[NoteTopic | None, Query()] = None,
    year: int | None = Query(default=None, ge=2000, le=2100),
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
) -> dict:
    query = " ".join(q.split())
    if len(query) < 2:
        raise HTTPException(status_code=422, detail="Search query is too short")
    with connect() as connection:
        return search_source_fragments(
            connection,
            query=query,
            company_rpj=company_rpj,
            topic=topic,
            fiscal_year=year,
            limit=limit,
            offset=offset,
        )


@app.get("/companies/{smv_rpj}/filings")
def company_filings(smv_rpj: str) -> list[dict]:
    with connect() as connection, connection.cursor() as cursor:
        cursor.execute("SELECT id FROM companies WHERE smv_rpj = %s", (smv_rpj,))
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Company not found")

        cursor.execute(
            """
            SELECT
                f.statement_type,
                f.fiscal_year,
                f.period_code,
                f.scope,
                f.currency_code,
                f.reported_scale,
                f.scale_source_url,
                f.updated_at,
                (SELECT COUNT(*) FROM financial_facts ff WHERE ff.filing_id = f.id) AS facts,
                (SELECT COUNT(*) FROM financial_facts ff
                    WHERE ff.filing_id = f.id AND ff.normalization_status = 'mapped'
                ) AS mapped_facts,
                (SELECT COUNT(*) FROM validation_results vr
                    WHERE vr.filing_id = f.id AND vr.status = 'failed'
                ) AS failed_validations
            FROM filings f
            JOIN companies c ON c.id = f.company_id
            WHERE c.smv_rpj = %s
            ORDER BY f.fiscal_year DESC, f.period_code DESC, f.statement_type
            """,
            (smv_rpj,),
        )
        return list(cursor.fetchall())


@app.get("/companies/{smv_rpj}/notes")
def financial_notes(
    smv_rpj: str,
    year: int,
    period: Literal["A", "1", "2", "3", "4"] = "A",
    scope: Literal["individual", "consolidated"] = "consolidated",
    topic: Annotated[NoteTopic | None, Query()] = None,
    priority_only: bool = False,
    q: Annotated[str | None, Query(max_length=100)] = None,
) -> dict:
    with connect() as connection, connection.cursor() as cursor:
        cursor.execute("SELECT id FROM companies WHERE smv_rpj = %s", (smv_rpj,))
        company = cursor.fetchone()
        if company is None:
            raise HTTPException(status_code=404, detail="Company not found")

        cursor.execute(
            """
            SELECT
                nd.id, nd.fiscal_year, nd.period_code, nd.scope, nd.version,
                nd.document_name, nd.source_url, nd.source_sha256,
                nd.page_count, nd.notes_count, nd.extraction_status,
                nd.retrieved_at, ns.last_checked_at
            FROM note_documents nd
            JOIN note_sources ns ON ns.id = nd.note_source_id
            WHERE nd.company_id = %s
              AND nd.fiscal_year = %s
              AND nd.period_code = %s
              AND nd.scope = %s
              AND nd.is_current
            """,
            (company["id"], year, period, scope),
        )
        document = cursor.fetchone()
        if document is None:
            raise HTTPException(status_code=404, detail="Financial notes not found")

        conditions = ["fn.note_document_id = %s"]
        parameters: list[object] = [document["id"]]
        if topic:
            conditions.append("fn.topic = %s")
            parameters.append(topic)
        if priority_only:
            conditions.append("fn.is_priority")
        if q and q.strip():
            conditions.append("(fn.original_title ILIKE %s OR fn.content_text ILIKE %s)")
            search = f"%{q.strip()}%"
            parameters.extend([search, search])

        cursor.execute(
            f"""
            SELECT
                fn.id, fn.note_number, fn.original_title, fn.topic, fn.is_priority,
                fn.start_page, fn.end_page, fn.extraction_status,
                LEFT(REGEXP_REPLACE(fn.content_text, E'[\\n\\r]+', ' ', 'g'), 320) AS excerpt
            FROM financial_notes fn
            WHERE {' AND '.join(conditions)}
            ORDER BY fn.note_number
            """,
            parameters,
        )
        notes = list(cursor.fetchall())
        cursor.execute(
            """
            SELECT job.status, job.attempts, job.completed_at, job.error_message
            FROM ingestion_jobs job
            JOIN note_sources ns ON ns.id = job.note_source_id
            WHERE ns.company_id = %s
              AND ns.fiscal_year = %s
              AND ns.period_code = %s
              AND ns.scope = %s
            ORDER BY job.created_at DESC
            LIMIT 1
            """,
            (company["id"], year, period, scope),
        )
        sync = cursor.fetchone()

    document.pop("id")
    return {"document": document, "notes": notes, "sync": sync}


@app.get("/companies/{smv_rpj}/note-comparisons")
def note_period_comparison(
    smv_rpj: str,
    current_year: int = Query(ge=2001, le=2100),
    previous_year: int = Query(ge=2000, le=2099),
    period: Literal["A", "1", "2", "3", "4"] = "A",
    scope: Literal["individual", "consolidated"] = "consolidated",
    topic: Annotated[NoteTopic | None, Query()] = None,
    priority_only: bool = False,
) -> dict:
    if previous_year != current_year - 1:
        raise HTTPException(
            status_code=422,
            detail="La comparación narrativa requiere períodos consecutivos",
        )
    with connect() as connection:
        comparison = fetch_narrative_comparison(
            connection,
            company_rpj=smv_rpj,
            current_year=current_year,
            previous_year=previous_year,
            period_code=period,
            scope=scope,
        )
    if comparison is None:
        raise HTTPException(status_code=404, detail="Narrative comparison not found")

    items = comparison["items"]
    if topic:
        items = [
            item
            for item in items
            if (item["current"] and item["current"]["topic"] == topic)
            or (item["previous"] and item["previous"]["topic"] == topic)
        ]
    if priority_only:
        items = [item for item in items if item["is_priority"]]
    comparison["items"] = items
    comparison["visible_items"] = len(items)
    return comparison


@app.get("/companies/{smv_rpj}/notes/{note_number}")
def financial_note_detail(
    smv_rpj: str,
    note_number: int,
    year: int,
    period: Literal["A", "1", "2", "3", "4"] = "A",
    scope: Literal["individual", "consolidated"] = "consolidated",
) -> dict:
    with connect() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                fn.id, fn.note_number, fn.original_title, fn.topic, fn.is_priority,
                fn.start_page, fn.end_page, fn.content_text, fn.extraction_status,
                nd.document_name, nd.source_url, nd.source_sha256, nd.version,
                nd.fiscal_year, nd.period_code, nd.scope, nd.retrieved_at,
                c.legal_name, c.smv_rpj
            FROM financial_notes fn
            JOIN note_documents nd ON nd.id = fn.note_document_id
            JOIN companies c ON c.id = nd.company_id
            WHERE c.smv_rpj = %s
              AND nd.fiscal_year = %s
              AND nd.period_code = %s
              AND nd.scope = %s
              AND nd.is_current
              AND fn.note_number = %s
            """,
            (smv_rpj, year, period, scope, note_number),
        )
        note = cursor.fetchone()
        if note is None:
            raise HTTPException(status_code=404, detail="Financial note not found")
        note_id = note.pop("id")
        cursor.execute(
            """
            SELECT page_number, section_order, content_text
            FROM note_sections
            WHERE financial_note_id = %s
            ORDER BY page_number, section_order
            """,
            (note_id,),
        )
        sections = list(cursor.fetchall())
        summary = fetch_cited_summary(connection, note_id)
    return {"note": note, "sections": sections, "summary": summary}


@app.get("/companies/{smv_rpj}/statements/{statement_type}")
def financial_statement(
    smv_rpj: str,
    statement_type: Literal["balance_sheet", "income_statement", "cash_flow"],
    year: int,
    period: Literal["A", "1", "2", "3", "4"] = "A",
    scope: Literal["individual", "consolidated"] = "consolidated",
    normalized_only: bool = Query(default=False),
) -> dict:
    with connect() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                f.id, c.smv_rpj, c.legal_name, f.statement_type, f.fiscal_year,
                f.period_code, f.scope, f.currency_code, f.currency_raw,
                f.reported_scale, f.scale_source_url, f.updated_at,
                s.provider, s.endpoint, s.operation, s.retrieved_at, s.payload_sha256
            FROM filings f
            JOIN companies c ON c.id = f.company_id
            JOIN source_fetches s ON s.id = f.source_fetch_id
            WHERE c.smv_rpj = %s
              AND f.statement_type = %s
              AND f.fiscal_year = %s
              AND f.period_code = %s
              AND f.scope = %s
            """,
            (smv_rpj, statement_type, year, period, scope),
        )
        filing = cursor.fetchone()
        if filing is None:
            raise HTTPException(status_code=404, detail="Financial statement not found")

        facts_query = """
            SELECT
                account_code, original_label, normalized_concept, current_amount,
                comparative_amount, value_kind, fact_scale, normalization_status
            FROM financial_facts
            WHERE filing_id = %s
        """
        if normalized_only:
            facts_query += " AND normalized_concept IS NOT NULL"
        facts_query += " ORDER BY id"
        cursor.execute(facts_query, (filing["id"],))
        facts = list(cursor.fetchall())

        cursor.execute(
            """
            SELECT rule_code, status, details, checked_at
            FROM validation_results
            WHERE filing_id = %s
            ORDER BY rule_code
            """,
            (filing["id"],),
        )
        validations = list(cursor.fetchall())

    filing.pop("id")
    return {"filing": filing, "facts": facts, "validations": validations}


@app.get("/companies/{smv_rpj}/summary")
def financial_summary(
    smv_rpj: str,
    year: int,
    period: Literal["A", "1", "2", "3", "4"] = "A",
    scope: Literal["individual", "consolidated"] = "consolidated",
) -> dict:
    with connect() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT smv_rpj, ruc, legal_name, company_type, sector, ciiu
            FROM companies
            WHERE smv_rpj = %s
            """,
            (smv_rpj,),
        )
        company = cursor.fetchone()
        if company is None:
            raise HTTPException(status_code=404, detail="Company not found")

        cursor.execute(
            """
            SELECT
                mv.metric_code, md.display_name, md.description, md.value_kind,
                md.formula_expression, mv.formula_version, mv.status, mv.value,
                mv.currency_code, mv.value_scale, mv.reason, mv.inputs,
                mv.calculated_at
            FROM metric_values mv
            JOIN metric_definitions md ON md.code = mv.metric_code
             AND md.formula_version = mv.formula_version
            WHERE mv.company_id = (
                SELECT id FROM companies WHERE smv_rpj = %s
            )
              AND mv.fiscal_year = %s
              AND mv.period_code = %s
              AND mv.scope = %s
            ORDER BY mv.metric_code
            """,
            (smv_rpj, year, period, scope),
        )
        metrics = list(cursor.fetchall())
        if not metrics:
            raise HTTPException(status_code=404, detail="Financial metrics not found")

    from app.metrics import comparative_metric

    for metric in metrics:
        metric["comparative"] = comparative_metric(metric)
    return {
        "company": company,
        "period": {"year": year, "period_code": period, "scope": scope},
        "metrics": metrics,
    }
