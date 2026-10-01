"""Minimal activity contract: no free-form content, credentials or client actor IDs."""

from uuid import uuid4


def record_activity(
    connection,
    *,
    user_id,
    action,
    outcome="success",
    resource_type=None,
    resource_id=None,
    company_rpj=None,
    fiscal_year=None,
    scope=None,
    event_key=None,
):
    with connection.cursor() as cursor:
        cursor.execute(
            """INSERT INTO user_activity_events
            (event_key,user_id,action,outcome,resource_type,resource_id,company_rpj,fiscal_year,scope)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(event_key) DO NOTHING""",
            (
                event_key or uuid4(),
                user_id,
                action,
                outcome,
                resource_type,
                str(resource_id) if resource_id is not None else None,
                company_rpj,
                fiscal_year,
                scope,
            ),
        )
