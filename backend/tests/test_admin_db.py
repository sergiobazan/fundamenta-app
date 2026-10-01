"""Opt-in transaction/concurrency checks on an explicit isolated PostgreSQL database."""

import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import psycopg
import pytest
from app import admin
from app.company_analysis import _claim_next_job
from app.migrations import discover_migrations
from fastapi import HTTPException
from psycopg import sql
from psycopg.rows import dict_row

pytestmark = pytest.mark.skipif(
    not os.environ.get("ADMIN_TEST_DATABASE_URL"),
    reason="Requires an explicit test PostgreSQL",
)


@pytest.fixture
def database(monkeypatch):
    dsn = os.environ["ADMIN_TEST_DATABASE_URL"]
    schema = "admin_test_" + uuid.uuid4().hex
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))

    def connect():
        return psycopg.connect(dsn, options=f"-c search_path={schema}", row_factory=dict_row)

    try:
        with connect() as conn:
            for migration in discover_migrations(
                Path(__file__).resolve().parents[2] / "infra/postgres/init"
            ):
                conn.execute(migration.sql)
            conn.execute("""
                INSERT INTO app_users(email,password_hash,full_name,is_admin)
                VALUES ('admin@example.test','not-a-password','Admin',TRUE);
                INSERT INTO companies(smv_rpj,legal_name) VALUES ('B20010','Nexa Test');
                INSERT INTO company_coverage(company_id,support_level,analysis_status)
                VALUES (1,'full','failed');
                INSERT INTO analysis_jobs(company_id,requested_by,fiscal_year,scope,
                    status,current_step,progress,attempts,max_attempts,error_message)
                VALUES (1,1,2025,'individual','failed','documents',75,3,3,'Timeout anterior');
                INSERT INTO analysis_job_steps(job_id,step_code,step_order,status,
                    started_at,completed_at,details)
                VALUES (1,'statements',1,'completed',NOW()-INTERVAL '5 minutes',
                    NOW()-INTERVAL '4 minutes','{"safe":true}'),
                    (1,'metrics',2,'completed',NOW()-INTERVAL '4 minutes',
                    NOW()-INTERVAL '3 minutes','{"safe":true}'),
                    (1,'documents',3,'failed',NOW()-INTERVAL '3 minutes',NOW(),
                    '{"activity":"Extrayendo notas"}'),
                    (1,'summaries',4,'pending',NULL,NULL,'{}');
            """)
        monkeypatch.setattr(admin, "connect", connect)
        yield connect
    finally:
        with psycopg.connect(dsn, autocommit=True) as conn:
            conn.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


def retry():
    return admin.retry_job(
        1,
        admin.RetryRequest(reason="Se corrigió la lectura duplicada"),
        {"id": 1, "email": "admin@example.test"},
    )


def test_retry_preserves_safe_steps_history_and_worker_budget(database):
    with database() as conn:
        before = conn.execute(
            "SELECT * FROM analysis_job_steps WHERE status='completed' ORDER BY step_order"
        ).fetchall()
    result = retry()
    assert result["resume_step"] == "documents"
    with database() as conn:
        after = conn.execute(
            "SELECT * FROM analysis_job_steps WHERE status='completed' ORDER BY step_order"
        ).fetchall()
        assert before == after
        job = conn.execute("SELECT * FROM analysis_jobs").fetchone()
        assert job["attempts"] == 3 and job["max_attempts"] == 6
        assert job["status"] == "queued"
        assert conn.execute("SELECT COUNT(*) AS n FROM admin_audit_events").fetchone()["n"] == 1
        assert (
            conn.execute(
                "SELECT COUNT(*) AS n FROM analysis_job_events "
                "WHERE snapshot->>'error_message'='Timeout anterior'"
            ).fetchone()["n"]
            == 1
        )
        claimed = _claim_next_job(conn)
        assert claimed["attempts"] == 4 and claimed["status"] == "running"
    detail = admin.get_job(1, {})
    assert detail["actions"][0]["reason"] == "Se corrigió la lectura duplicada"
    assert detail["events"]


def test_two_concurrent_retries_schedule_only_one_cycle(database):
    def attempt():
        try:
            retry()
            return 202
        except HTTPException as error:
            return error.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(lambda _: attempt(), range(2))) == [202, 409]
    with database() as conn:
        assert (
            conn.execute("SELECT max_attempts FROM analysis_jobs").fetchone()["max_attempts"] == 6
        )
        assert conn.execute("SELECT COUNT(*) AS n FROM admin_audit_events").fetchone()["n"] == 1


def test_newer_job_prevents_retrying_old_results(database):
    with database() as conn:
        conn.execute("""INSERT INTO analysis_jobs(company_id,fiscal_year,scope,status)
                     VALUES (1,2025,'individual','completed')""")
    with pytest.raises(HTTPException) as exc:
        retry()
    assert exc.value.status_code == 409


def test_audit_failure_rolls_back_retry(database, monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr(admin, "audit", fail)
    with pytest.raises(RuntimeError):
        retry()
    with database() as conn:
        job = conn.execute("SELECT * FROM analysis_jobs").fetchone()
        assert job["status"] == "failed" and job["max_attempts"] == 3


def test_role_changes_are_audited_and_do_not_create_accounts(database):
    with database() as conn:
        conn.execute(
            "INSERT INTO app_users(email,password_hash,full_name,is_admin) "
            "VALUES ('backup@example.test','unused','Backup',TRUE)"
        )
    admin.set_admin_role("admin@example.test", False, "Revocación de acceso de prueba")
    with database() as conn:
        assert (
            conn.execute("SELECT is_admin FROM app_users WHERE id=1").fetchone()["is_admin"]
            is False
        )
        assert (
            conn.execute("SELECT action FROM admin_audit_events").fetchone()["action"]
            == "admin.role"
        )
    with pytest.raises(ValueError):
        admin.set_admin_role("unknown@example.test", True, "Cuenta que no existe todavía")
