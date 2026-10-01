"""User administration: shared lock, explicit projections, append-only audit."""

from datetime import date, datetime, timedelta
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Query
from pydantic import ConfigDict

from app.admin import RetryRequest, admin_dependency, audit
from app.db import connect

router = APIRouter(prefix="/admin", tags=["admin"])
Page = Annotated[int, Query(ge=1, le=100000)]
FIELDS = (
    "id,email,full_name,is_admin,is_active,created_at,updated_at,"
    "last_login_at,suspended_at,suspension_reason"
)


def window(start: date | None, end: date | None):
    today = datetime.now(ZoneInfo("America/Lima")).date()
    end = end or today
    start = start or end - timedelta(days=29)
    if start > end or (end - start).days > 366:
        raise HTTPException(422, "El periodo debe ser válido y de hasta 367 días")
    tz = ZoneInfo("America/Lima")
    return datetime.combine(start, datetime.min.time(), tz), datetime.combine(
        end + timedelta(days=1), datetime.min.time(), tz
    )


def lock_admins(connection):
    connection.execute("SELECT pg_advisory_xact_lock(hashtext('user-admin-access'))")


def protect_last_admin(connection, target, *, active, admin):
    if target["is_admin"] and target["is_active"] and not (active and admin):
        count = connection.execute(
            "SELECT COUNT(*) AS n FROM app_users WHERE is_admin AND is_active"
        ).fetchone()["n"]
        if count <= 1:
            raise HTTPException(409, "Debe permanecer al menos un administrador activo")


def require_live_admin(connection, user):
    actor = connection.execute(
        "SELECT is_admin,is_active FROM app_users WHERE id=%s", (user["id"],)
    ).fetchone()
    if not actor or not actor["is_admin"] or not actor["is_active"]:
        raise HTTPException(403, "El permiso administrativo ya no está activo")


def log_view(connection, user, target, action):
    audit(
        connection,
        user={"id": user["id"], "label": user["email"]},
        action=action,
        reason="Consulta administrativa de cuenta",
        details={"user_id": target},
        target_user_id=target,
    )


@router.get("/users")
def list_users(
    user: dict = admin_dependency,
    q: Annotated[str, Query(max_length=100)] = "",
    role: Literal["admin", "user"] | None = None,
    status: Literal["active", "suspended"] | None = None,
    page: Page = 1,
    start: date | None = None,
    end: date | None = None,
    created_from: date | None = None,
    created_to: date | None = None,
    active_only: bool = False,
    sort: Literal["created", "activity", "name"] = "created",
):
    lo, hi = window(start, end)
    clauses = []
    values = []
    if q.strip():
        pattern = (
            "%" + q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        )
        clauses.append("(u.email ILIKE %s OR u.full_name ILIKE %s)")
        values.extend([pattern, pattern])
    if role:
        clauses.append("u.is_admin=%s")
        values.append(role == "admin")
    if status:
        clauses.append("u.is_active=%s")
        values.append(status == "active")
    if created_from:
        clauses.append("u.created_at>=%s")
        values.append(window(created_from, created_from)[0])
    if created_to:
        clauses.append("u.created_at<%s")
        values.append(window(created_to, created_to)[1])
    if active_only:
        clauses.append(
            "EXISTS(SELECT 1 FROM user_activity_feed f WHERE f.user_id=u.id "
            "AND f.actor_type='human' AND f.created_at>=%s AND f.created_at<%s)"
        )
        values.extend([lo, hi])
    where = "WHERE " + " AND ".join(clauses) if clauses else ""
    order = {
        "created": "u.created_at DESC,u.id DESC",
        "activity": "last_activity_at DESC NULLS LAST,u.id DESC",
        "name": "u.full_name,u.id",
    }[sort]
    fields = ",".join("u." + f for f in FIELDS.split(","))
    with connect() as c:
        total = c.execute(f"SELECT COUNT(*) AS n FROM app_users u {where}", values).fetchone()["n"]
        rows = c.execute(
            f"""SELECT {fields},
            (SELECT MAX(created_at) FROM user_activity_feed f WHERE f.user_id=u.id
             AND f.actor_type='human') AS last_activity_at,
            (SELECT COUNT(*) FROM user_activity_feed f WHERE f.user_id=u.id
             AND f.action IN ('analysis.request','report.request') AND f.created_at>=%s
             AND f.created_at<%s) AS requests
            FROM app_users u {where} ORDER BY {order} LIMIT 25 OFFSET %s""",
            [lo, hi, *values, (page - 1) * 25],
        ).fetchall()
        coverage = c.execute("SELECT started_at FROM activity_tracking WHERE id=1").fetchone()
    return {
        "users": rows,
        "total": total,
        "page_size": 25,
        "tracking_started_at": coverage["started_at"],
    }


@router.get("/users/{user_id}")
def get_user(user_id: int, user: dict = admin_dependency):
    with connect() as c:
        account = c.execute(f"SELECT {FIELDS} FROM app_users WHERE id=%s", (user_id,)).fetchone()
        if not account:
            raise HTTPException(404, "Usuario no encontrado")
        log_view(c, user, user_id, "user.inspect")
    return {"user": account}


@router.get("/users/{user_id}/activity")
def user_activity(
    user_id: int,
    user: dict = admin_dependency,
    page: Page = 1,
    start: date | None = None,
    end: date | None = None,
    action: Annotated[str, Query(max_length=50)] = "",
    company: Annotated[str, Query(max_length=20)] = "",
    outcome: Annotated[str, Query(max_length=40)] = "",
    actor_type: Literal["human", "system", "admin"] | None = None,
):
    lo, hi = window(start, end)
    clauses = ["user_id=%s", "created_at>=%s", "created_at<%s"]
    values = [user_id, lo, hi]
    for key, value in [
        ("action", action),
        ("company_rpj", company),
        ("outcome", outcome),
        ("actor_type", actor_type),
    ]:
        if value:
            clauses.append(key + "=%s")
            values.append(value)
    where = " AND ".join(clauses)
    with connect() as c:
        if not c.execute("SELECT id FROM app_users WHERE id=%s", (user_id,)).fetchone():
            raise HTTPException(404, "Usuario no encontrado")
        total = c.execute(
            f"SELECT COUNT(*) AS n FROM user_activity_feed WHERE {where}", values
        ).fetchone()["n"]
        events = c.execute(
            f"SELECT * FROM user_activity_feed WHERE {where} "
            "ORDER BY created_at DESC,event_id DESC LIMIT 25 OFFSET %s",
            [*values, (page - 1) * 25],
        ).fetchall()
        coverage = c.execute("SELECT started_at FROM activity_tracking WHERE id=1").fetchone()
        log_view(c, user, user_id, "user.activity.inspect")
    return {
        "events": events,
        "total": total,
        "page_size": 25,
        "tracking_started_at": coverage["started_at"],
    }


class AccessChange(RetryRequest):
    model_config = ConfigDict(extra="forbid")
    action: Literal["suspend", "reactivate", "revoke_sessions", "grant_admin", "revoke_admin"]


@router.post("/users/{user_id}/access")
def change_access(user_id: int, payload: AccessChange, user: dict = admin_dependency):
    with connect() as c:
        lock_admins(c)
        require_live_admin(c, user)
        target = c.execute(
            f"SELECT {FIELDS} FROM app_users WHERE id=%s FOR UPDATE", (user_id,)
        ).fetchone()
        if not target:
            raise HTTPException(404, "Usuario no encontrado")
        active = target["is_active"]
        admin = target["is_admin"]
        if payload.action == "suspend":
            active = False
        if payload.action == "reactivate":
            active = True
        if payload.action == "grant_admin":
            admin = True
        if payload.action == "revoke_admin":
            admin = False
        protect_last_admin(c, target, active=active, admin=admin)
        c.execute(
            """UPDATE app_users SET is_active=%s,is_admin=%s,updated_at=NOW(),
            suspended_at=CASE WHEN %s THEN NULL ELSE COALESCE(suspended_at,NOW()) END,
            suspension_reason=CASE WHEN %s THEN NULL ELSE %s END WHERE id=%s""",
            (active, admin, active, active, payload.reason, user_id),
        )
        sessions = 0
        if payload.action in ("suspend", "revoke_sessions"):
            sessions = c.execute(
                "UPDATE auth_sessions SET revoked_at=NOW() WHERE user_id=%s AND revoked_at IS NULL",
                (user_id,),
            ).rowcount
        audit(
            c,
            user={"id": user["id"], "label": user["email"]},
            action="user." + payload.action,
            reason=payload.reason,
            details={
                "user_id": user_id,
                "before": {"is_active": target["is_active"], "is_admin": target["is_admin"]},
                "after": {"is_active": active, "is_admin": admin},
                "revoked_sessions": sessions,
            },
            target_user_id=user_id,
        )
        account = c.execute(f"SELECT {FIELDS} FROM app_users WHERE id=%s", (user_id,)).fetchone()
    return {"user": account, "revoked_sessions": sessions}


@router.get("/audit")
def audit_events(
    user: dict = admin_dependency,
    page: Page = 1,
    start: date | None = None,
    end: date | None = None,
):
    lo, hi = window(start, end)
    with connect() as c:
        total = c.execute(
            "SELECT COUNT(*) AS n FROM admin_audit_events "
            "WHERE created_at >= %s AND created_at < %s",
            (lo, hi),
        ).fetchone()["n"]
        rows = c.execute(
            "SELECT * FROM admin_audit_events WHERE created_at >= %s "
            "AND created_at < %s ORDER BY id DESC LIMIT 25 OFFSET %s",
            (lo, hi, (page - 1) * 25),
        ).fetchall()
    return {"events": rows, "total": total, "page_size": 25}


@router.get("/summary")
def summary(user: dict = admin_dependency, start: date | None = None, end: date | None = None):
    lo, hi = window(start, end)
    with connect() as c:
        counts = c.execute(
            """SELECT COUNT(*) AS total_users,
            COUNT(*) FILTER(WHERE is_active) AS active_users,
            COUNT(*) FILTER(WHERE NOT is_active) AS suspended_users,
            COUNT(*) FILTER(WHERE created_at>=%s AND created_at<%s) AS registrations
            FROM app_users""",
            (lo, hi),
        ).fetchone()
        usage = c.execute(
            """SELECT COUNT(DISTINCT user_id) FILTER(WHERE actor_type='human')
            AS users_with_activity,
            COUNT(*) FILTER(WHERE action='analysis.request') AS analysis_requests,
            COUNT(*) FILTER(WHERE action='report.request') AS report_requests,
            COUNT(*) FILTER(WHERE actor_type='system' AND outcome='failed') AS failures
            FROM user_activity_feed WHERE created_at>=%s AND created_at<%s""",
            (lo, hi),
        ).fetchone()
        recent = c.execute(
            "SELECT * FROM user_activity_feed WHERE created_at>=%s "
            "AND created_at<%s ORDER BY created_at DESC,event_id DESC LIMIT 20",
            (lo, hi),
        ).fetchall()
        coverage = c.execute("SELECT started_at FROM activity_tracking WHERE id=1").fetchone()
    return {
        **counts,
        **usage,
        "recent": recent,
        "tracking_started_at": coverage["started_at"],
        "start": lo,
        "end_exclusive": hi,
    }
