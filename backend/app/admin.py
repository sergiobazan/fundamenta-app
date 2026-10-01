"""Restricted operations for the persistent company-analysis queue."""

import argparse
import json
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from app.auth import current_user_dependency, normalize_email
from app.config import get_settings
from app.db import connect

router = APIRouter(prefix="/admin", tags=["admin"])
JobStatus = Literal["queued", "running", "retrying", "completed", "review_required", "failed"]


def require_admin(user: dict = current_user_dependency) -> dict:
    if not user.get("is_admin", False):
        raise HTTPException(403, "Acceso reservado a administradores")
    return user


admin_dependency = Depends(require_admin)


class RetryRequest(BaseModel):
    reason: str = Field(min_length=10, max_length=500)

    @field_validator("reason", mode="before")
    @classmethod
    def trim_reason(cls, value):
        return value.strip() if isinstance(value, str) else value


def audit(connection, *, user, action, reason, job_id=None, details=None, target_user_id=None):
    connection.execute(
        """INSERT INTO admin_audit_events
           (actor_id, actor_label, action, job_id, reason, details, target_user_id)
           VALUES (%s,%s,%s,%s,%s,%s::jsonb,%s)""",
        (
            user.get("id"),
            user["label"],
            action,
            job_id,
            reason,
            json.dumps(details or {}),
            target_user_id,
        ),
    )


@router.get("/analysis-jobs")
def list_jobs(
    user: dict = admin_dependency,
    status: JobStatus | None = None,
    q: Annotated[str, Query(max_length=100)] = "",
    page: Annotated[int, Query(ge=1)] = 1,
):
    clauses, values = [], []
    if status:
        clauses.append("j.status=%s")
        values.append(status)
    if q.strip():
        clauses.append("(c.smv_rpj ILIKE %s OR c.legal_name ILIKE %s)")
        escaped = q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = "%" + escaped + "%"
        values.extend([pattern, pattern])
    where = "WHERE " + " AND ".join(clauses) if clauses else ""
    with connect() as connection:
        total = connection.execute(
            f"SELECT COUNT(*) AS n FROM analysis_jobs j JOIN companies c "
            f"ON c.id=j.company_id {where}",
            values,
        ).fetchone()["n"]
        jobs = connection.execute(
            f"""SELECT j.*, c.smv_rpj, c.legal_name,
                EXTRACT(EPOCH FROM (COALESCE(j.completed_at,NOW())-j.started_at))
                    AS duration_seconds
                FROM analysis_jobs j JOIN companies c ON c.id=j.company_id
                {where} ORDER BY j.created_at DESC, j.id DESC LIMIT 25 OFFSET %s""",
            [*values, (page - 1) * 25],
        ).fetchall()
        counts = connection.execute(
            "SELECT status, COUNT(*) AS count FROM analysis_jobs GROUP BY status"
        ).fetchall()
    return {
        "jobs": jobs,
        "total": total,
        "page": page,
        "page_size": 25,
        "counts": {r["status"]: r["count"] for r in counts},
    }


@router.get("/analysis-jobs/{job_id}")
def get_job(job_id: int, user: dict = admin_dependency):
    with connect() as connection:
        job = connection.execute(
            """SELECT j.*, c.smv_rpj, c.legal_name, u.full_name AS requested_by_name,
               EXTRACT(EPOCH FROM (COALESCE(j.completed_at,NOW())-j.started_at))
                    AS duration_seconds
               FROM analysis_jobs j JOIN companies c ON c.id=j.company_id
               LEFT JOIN app_users u ON u.id=j.requested_by WHERE j.id=%s""",
            (job_id,),
        ).fetchone()
        if job is None:
            raise HTTPException(404, "Trabajo no encontrado")
        steps = connection.execute(
            """SELECT *, EXTRACT(EPOCH FROM (COALESCE(completed_at,NOW())-started_at))
                AS duration_seconds FROM analysis_job_steps
                WHERE job_id=%s ORDER BY step_order""",
            (job_id,),
        ).fetchall()
        events = connection.execute(
            "SELECT * FROM analysis_job_events WHERE job_id=%s ORDER BY id DESC LIMIT 100",
            (job_id,),
        ).fetchall()
        actions = connection.execute(
            "SELECT * FROM admin_audit_events WHERE job_id=%s ORDER BY id DESC LIMIT 100",
            (job_id,),
        ).fetchall()
    return {"job": job, "steps": steps, "events": events, "actions": actions}


@router.get("/analysis-jobs/{job_id}/events")
def get_events(
    job_id: int,
    user: dict = admin_dependency,
    before: Annotated[int | None, Query(gt=0)] = None,
):
    with connect() as connection:
        events = connection.execute(
            """SELECT * FROM analysis_job_events WHERE job_id=%s
               AND (%s::bigint IS NULL OR id<%s) ORDER BY id DESC LIMIT 100""",
            (job_id, before, before),
        ).fetchall()
    return {"events": events}


@router.post("/analysis-jobs/{job_id}/retry", status_code=202)
def retry_job(job_id: int, payload: RetryRequest, user: dict = admin_dependency):
    with connect() as connection:
        original = connection.execute(
            """SELECT j.*, c.smv_rpj FROM analysis_jobs j
               JOIN companies c ON c.id=j.company_id WHERE j.id=%s""",
            (job_id,),
        ).fetchone()
        if original is None:
            raise HTTPException(404, "Trabajo no encontrado")
        # Same lock order as ordinary requests: advisory lock, coverage, job.
        connection.execute(
            "SELECT pg_advisory_xact_lock(hashtext(%s))",
            (f"company-analysis:{original['smv_rpj']}:{original['fiscal_year']}",),
        )
        coverage = connection.execute(
            "SELECT * FROM company_coverage WHERE company_id=%s FOR UPDATE",
            (original["company_id"],),
        ).fetchone()
        if not coverage or coverage["support_level"] == "unsupported":
            raise HTTPException(409, "Empresa no compatible con el análisis automático")
        job = connection.execute(
            "SELECT * FROM analysis_jobs WHERE id=%s FOR UPDATE",
            (job_id,),
        ).fetchone()
        if job["status"] not in ("failed", "review_required"):
            raise HTTPException(409, "Solo se pueden reintentar trabajos fallidos o en revisión")
        newer_or_active = connection.execute(
            """SELECT id FROM analysis_jobs WHERE company_id=%s AND fiscal_year=%s
               AND period_code=%s AND scope=%s AND id<>%s
               AND (id>%s OR status IN ('queued','running','retrying')) LIMIT 1""",
            (
                job["company_id"],
                job["fiscal_year"],
                job["period_code"],
                job["scope"],
                job_id,
                job_id,
            ),
        ).fetchone()
        if newer_or_active:
            raise HTTPException(409, "Existe un trabajo posterior o activo para este periodo")
        pending = connection.execute(
            """SELECT step_code FROM analysis_job_steps WHERE job_id=%s
               AND status<>'completed' ORDER BY step_order LIMIT 1""",
            (job_id,),
        ).fetchone()
        if not pending:
            raise HTTPException(409, "No hay etapas pendientes que reintentar")
        code = pending["step_code"]
        progress = {"statements": 0, "metrics": 40, "documents": 65, "summaries": 85}[code]
        budget = get_settings().analysis_worker_max_attempts
        connection.execute(
            """UPDATE analysis_jobs SET status='queued', max_attempts=attempts+%s,
               next_retry_at=NULL, scheduled_for=NOW(), started_at=NULL, completed_at=NULL,
               error_message=NULL, current_step=%s, progress=%s, updated_at=NOW()
               WHERE id=%s""",
            (budget, code, progress, job_id),
        )
        connection.execute(
            """UPDATE analysis_job_steps SET status='pending', started_at=NULL,
               completed_at=NULL, error_message=NULL, details='{}'::jsonb, updated_at=NOW()
               WHERE job_id=%s AND status<>'completed'""",
            (job_id,),
        )
        connection.execute(
            """UPDATE company_coverage SET analysis_status='queued', last_error=NULL,
               last_requested_at=NOW(), updated_at=NOW() WHERE company_id=%s""",
            (job["company_id"],),
        )
        audit(
            connection,
            user={"id": user["id"], "label": user["email"]},
            action="analysis.retry",
            job_id=job_id,
            reason=payload.reason,
            details={
                "previous_status": job["status"],
                "attempts": job["attempts"],
                "additional_attempts": budget,
                "resume_step": code,
            },
        )
        connection.commit()
    return {"job_id": job_id, "status": "queued", "resume_step": code}


def set_admin_role(email: str, enabled: bool, reason: str):
    """Operator CLI only. Public registration/profile endpoints cannot grant roles."""
    from app.user_admin import lock_admins, protect_last_admin

    with connect() as connection:
        lock_admins(connection)
        user = connection.execute(
            "SELECT id, is_admin, is_active FROM app_users WHERE email=%s FOR UPDATE",
            (normalize_email(email),),
        ).fetchone()
        if user is None:
            raise ValueError("El usuario debe registrarse antes de asignar el rol")
        protect_last_admin(connection, user, active=user["is_active"], admin=enabled)
        connection.execute(
            "UPDATE app_users SET is_admin=%s, updated_at=NOW() WHERE id=%s",
            (enabled, user["id"]),
        )
        audit(
            connection,
            user={"label": "operator-cli"},
            action="admin.role",
            target_user_id=user["id"],
            reason=reason,
            details={"user_id": user["id"], "previous": user["is_admin"], "is_admin": enabled},
        )
        connection.commit()


def main():
    parser = argparse.ArgumentParser(description="Asignación de acceso administrativo")
    parser.add_argument("action", choices=["grant", "revoke"])
    parser.add_argument("--email", required=True)
    parser.add_argument("--reason", required=True)
    args = parser.parse_args()
    reason = RetryRequest(reason=args.reason).reason
    set_admin_role(args.email, args.action == "grant", reason)
    print("Rol actualizado y acción registrada.")


if __name__ == "__main__":
    main()
