"""Opt-in isolated PostgreSQL tests; never use the application's DATABASE_URL."""

import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import psycopg
import pytest
from app import notes_reports as reports
from app.auth import current_user
from app.config import Settings
from app.migrations import discover_migrations
from fastapi import FastAPI
from fastapi.testclient import TestClient
from psycopg import sql
from psycopg.rows import dict_row

pytestmark = pytest.mark.skipif(
    not os.environ.get("NOTES_REPORT_TEST_DATABASE_URL"),
    reason="Requires an explicit local test database",
)


@pytest.fixture
def database(monkeypatch):
    dsn = os.environ["NOTES_REPORT_TEST_DATABASE_URL"]
    schema = "notes_report_test_" + uuid.uuid4().hex
    with psycopg.connect(dsn, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))

    def connection():
        return psycopg.connect(dsn, options=f"-c search_path={schema}", row_factory=dict_row)

    try:
        with connection() as conn:
            directory = Path(__file__).resolve().parents[2] / "infra/postgres/init"
            for migration in discover_migrations(directory):
                conn.execute(migration.sql)
            conn.execute("""INSERT INTO companies (smv_rpj,legal_name) VALUES ('TEST','Empresa');
                INSERT INTO app_users (email,password_hash,full_name)
                VALUES ('test@example.test','not-a-password','Test');
                INSERT INTO note_sources (company_id,source_key,fiscal_year,scope,
                    document_name,source_url) VALUES
                    (1,'test',2025,'consolidated','Notas','https://www.smv.gob.pe/test.pdf');
                INSERT INTO note_documents (note_source_id,company_id,fiscal_year,period_code,
                    scope,version,document_name,source_url,source_sha256,file_size_bytes,
                    page_count,notes_count,extraction_status) VALUES
                    (1,1,2025,'A','consolidated',1,'Notas','https://www.smv.gob.pe/test.pdf',
                    repeat('a',64),100,10,1,'extracted');
                INSERT INTO financial_notes (note_document_id,note_number,original_title,
                    topic,start_page,end_page,content_text) VALUES
                    (1,1,'Contingencias','contingencies',5,5,'Procesos pendientes');
                INSERT INTO source_fragments (company_id,note_document_id,financial_note_id,
                    fragment_order,page_number,heading_text,content_text) VALUES
                    (1,1,1,0,5,'Contingencias','La compañía mantiene procesos pendientes.');""")
        monkeypatch.setattr(reports, "connect", connection)
        settings = Settings(_env_file=None, nvidia_api_key="test-only")
        monkeypatch.setattr(reports, "get_settings", lambda: settings)
        yield connection, settings
    finally:
        with psycopg.connect(dsn, autocommit=True) as admin:
            admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


def request():
    return reports.request_report("TEST", reports.ReportRequest(year=2025), {"id": 1})


def test_concurrent_requests_share_one_job_and_completed_result(database, monkeypatch):
    connection, settings = database
    with ThreadPoolExecutor(max_workers=2) as pool:
        rows = list(pool.map(lambda _: request(), range(2)))
    assert rows[0]["report"]["id"] == rows[1]["report"]["id"]
    calls = []

    async def generate(*args):
        calls.append(1)
        return {"findings": [], "limitations": ["No hay evidencia suficiente"]}

    monkeypatch.setattr(reports, "generate", generate)
    with ThreadPoolExecutor(max_workers=2) as pool:
        claimed = list(pool.map(lambda _: reports.process_next_report(settings), range(2)))
    assert sorted(claimed) == [False, True]
    assert len(calls) == 1
    assert request()["report"]["status"] == "completed"
    assert reports.get_report("TEST", 2025, "consolidated", {"id": 1})["stale"] is False
    with connection() as conn:
        conn.execute("UPDATE source_fragments SET content_text=content_text || ' Actualizado.'")
    assert reports.get_report("TEST", 2025, "consolidated", {"id": 1})["stale"] is True
    assert request()["report"]["id"] != rows[0]["report"]["id"]


def test_retry_exhaustion_and_interrupted_job_recovery(database, monkeypatch):
    connection, settings = database
    request()

    async def fail(*args):
        raise TimeoutError()

    monkeypatch.setattr(reports, "generate", fail)
    for attempt in range(3):
        assert reports.process_next_report(settings)
        with connection() as conn:
            row = conn.execute("SELECT * FROM notes_reports").fetchone()
            assert row["status"] == ("failed" if attempt == 2 else "retrying")
            conn.execute("UPDATE notes_reports SET next_attempt_at=NOW()")
    assert not reports.process_next_report(settings)
    request()
    with connection() as conn:
        conn.execute("""UPDATE notes_reports SET status='running', attempts=1,
                     started_at=NOW()-INTERVAL '16 minutes'""")
    assert reports.process_next_report(settings)
    with connection() as conn:
        assert conn.execute("SELECT attempts FROM notes_reports").fetchone()["attempts"] == 2


def test_routes_require_authentication(database):
    app = FastAPI()
    app.include_router(reports.router)
    client = TestClient(app)
    assert (
        client.get("/companies/TEST/notes-report?year=2025&scope=consolidated").status_code == 401
    )
    assert client.post("/companies/TEST/notes-report", json={"year": 2025}).status_code == 401
    app.dependency_overrides[current_user] = lambda: {"id": 1}
    assert client.post("/companies/TEST/notes-report", json={"year": 2025}).status_code == 202
    assert (
        client.get("/companies/TEST/notes-report?year=2025&scope=consolidated").status_code == 200
    )
