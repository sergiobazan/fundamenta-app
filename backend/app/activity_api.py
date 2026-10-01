from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.activity import record_activity
from app.auth import current_user_dependency
from app.db import connection_scope

router = APIRouter()


class NavigationEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_key: UUID
    action: Literal[
        "company.view", "period.change", "source.open", "comparison.view", "search.view"
    ]
    company_rpj: str | None = Field(default=None, pattern=r"^[A-Za-z0-9]{1,20}$")
    fiscal_year: int | None = Field(default=None, ge=2000, le=2100)
    scope: Literal["individual", "consolidated"] | None = None


@router.post("/activity", status_code=204)
def navigation_event(payload: NavigationEvent, user: dict = current_user_dependency):
    with connection_scope() as connection:
        connection.execute(
            "SELECT pg_advisory_xact_lock(hashtext(%s))", (f"navigation:{user['id']}",)
        )
        if connection.execute(
            "SELECT id FROM user_activity_events WHERE event_key=%s", (payload.event_key,)
        ).fetchone():
            return
        count = connection.execute(
            "SELECT COUNT(*) AS n FROM user_activity_events "
            "WHERE user_id=%s AND outcome='observed' "
            "AND created_at>NOW()-INTERVAL '1 minute'",
            (user["id"],),
        ).fetchone()["n"]
        if count >= 60:
            raise HTTPException(429, "Límite de eventos de navegación alcanzado")
        if (
            payload.company_rpj
            and not connection.execute(
                "SELECT id FROM companies WHERE smv_rpj=%s", (payload.company_rpj,)
            ).fetchone()
        ):
            raise HTTPException(422, "Empresa no encontrada")
        record_activity(connection, user_id=user["id"], outcome="observed", **payload.model_dump())
