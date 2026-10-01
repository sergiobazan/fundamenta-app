"""Real transactions and concurrent account changes in an isolated schema."""

import os
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from uuid import uuid4

import pytest
from app import activity_api, auth, user_admin
from app.activity import record_activity
from app.auth import hash_session_token
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from test_admin_db import database  # noqa: F401

pytestmark = [
    pytest.mark.usefixtures("database"),
    pytest.mark.skipif(
        not os.environ.get("ADMIN_TEST_DATABASE_URL"), reason="Requires explicit test PostgreSQL"
    ),
]


@pytest.fixture
def accounts(database, monkeypatch):  # noqa: F811
    with database() as c:
        c.execute(
            "INSERT INTO app_users(email,password_hash,full_name) VALUES "
            "('normal@example.com',%s,'Normal')",
            (auth.password_hasher.hash("test-password-123"),),
        )
        c.execute(
            "INSERT INTO auth_sessions(user_id,token_hash,expires_at) "
            "VALUES (2,%s,NOW()+INTERVAL '1 day')",
            (hash_session_token("old-session"),),
        )

    @contextmanager
    def scope():
        with database() as c:
            yield c

    monkeypatch.setattr(user_admin, "connect", database)
    monkeypatch.setattr(auth, "connection_scope", scope)
    monkeypatch.setattr(activity_api, "connection_scope", scope)
    return database


ADMIN = {"id": 1, "email": "admin@example.test", "is_admin": True}


def change(id, action):
    return user_admin.change_access(
        id, user_admin.AccessChange(action=action, reason="Cambio administrativo de prueba"), ADMIN
    )


def test_suspend_blocks_existing_sessions_and_login_reactivate_requires_new_login(accounts):
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="old-session")
    assert auth.current_user(credentials)["id"] == 2
    assert change(2, "suspend")["revoked_sessions"] == 1
    with pytest.raises(HTTPException) as exc:
        auth.current_user(credentials)
    assert exc.value.status_code == 401
    login = auth.LoginRequest(email="normal@example.com", password="test-password-123")
    with pytest.raises(HTTPException) as exc:
        auth.login(login)
    assert exc.value.status_code == 403
    change(2, "reactivate")
    with pytest.raises(HTTPException):
        auth.current_user(credentials)
    token = auth.login(login)["session_token"]
    assert (
        auth.current_user(HTTPAuthorizationCredentials(scheme="Bearer", credentials=token))["id"]
        == 2
    )
    change(2, "revoke_sessions")
    with pytest.raises(HTTPException):
        auth.current_user(HTTPAuthorizationCredentials(scheme="Bearer", credentials=token))
    assert auth.login(login)["session_token"]


def test_last_admin_protected_in_api_and_cli(accounts):
    for action in ("suspend", "revoke_admin"):
        with pytest.raises(HTTPException) as exc:
            change(1, action)
        assert exc.value.status_code == 409
    from app import admin

    with pytest.raises(HTTPException):
        admin.set_admin_role("admin@example.test", False, "Prueba protección")
    change(2, "grant_admin")
    change(2, "revoke_admin")


def test_concurrent_self_revocations_leave_one_admin(accounts):
    change(2, "grant_admin")

    def revoke(id):
        try:
            user_admin.change_access(
                id,
                user_admin.AccessChange(
                    action="revoke_admin", reason="Revocación concurrente de prueba"
                ),
                {"id": id, "email": f"admin{id}@example.test", "is_admin": True},
            )
            return 200
        except HTTPException as exc:
            return exc.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(revoke, [1, 2])) == [200, 409]
    with accounts() as c:
        assert (
            c.execute(
                "SELECT COUNT(*) AS n FROM app_users WHERE is_admin AND is_active"
            ).fetchone()["n"]
            == 1
        )


def test_audit_failure_rolls_back_account_and_sessions(accounts, monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr(user_admin, "audit", fail)
    with pytest.raises(RuntimeError):
        change(2, "suspend")
    with accounts() as c:
        assert c.execute("SELECT is_active FROM app_users WHERE id=2").fetchone()["is_active"]
        assert (
            c.execute("SELECT revoked_at FROM auth_sessions WHERE user_id=2").fetchone()[
                "revoked_at"
            ]
            is None
        )


def test_events_deduplicate_without_fabricating_legacy_usage_and_exclude_secrets(accounts):
    key = uuid4()
    with accounts() as c:
        for _ in range(2):
            record_activity(
                c, user_id=2, action="company.view", event_key=key, company_rpj="B20010"
            )
    result = user_admin.user_activity(2, ADMIN)
    assert sum(e["action"] == "company.view" for e in result["events"]) == 1
    assert sum(e["action"] == "account.register" for e in result["events"]) == 1
    assert not any(e["action"] == "auth.login" for e in result["events"])
    listing = user_admin.list_users(ADMIN, q="normal")
    assert listing["total"] == 1
    assert listing["users"][0]["last_login_at"] is None
    assert "password_hash" not in listing["users"][0]
    assert user_admin.summary(ADMIN)["users_with_activity"] == 2
    with accounts() as c:
        record_activity(
            c,
            user_id=1,
            action="analysis.request",
            outcome="created",
            resource_type="analysis",
            resource_id=1,
        )
    with accounts() as c:
        assert (
            c.execute(
                "SELECT COUNT(*) AS n FROM user_activity_feed WHERE action='analysis.request'"
            ).fetchone()["n"]
            == 1
        )
    user_admin.get_user(2, ADMIN)
    with accounts() as c:
        assert (
            c.execute(
                "SELECT target_user_id FROM admin_audit_events WHERE action='user.inspect'"
            ).fetchone()["target_user_id"]
            == 2
        )


def test_new_auth_actions_are_recorded(accounts):
    auth.register(
        auth.RegisterRequest(
            email="new@example.com", full_name="New Account", password="safe-password-123"
        )
    )
    token = auth.login(auth.LoginRequest(email="new@example.com", password="safe-password-123"))[
        "session_token"
    ]
    auth.logout(HTTPAuthorizationCredentials(scheme="Bearer", credentials=token))
    with accounts() as c:
        rows = c.execute("SELECT action FROM user_activity_events ORDER BY id").fetchall()
    assert [r["action"] for r in rows] == [
        "account.register",
        "auth.login",
        "auth.login",
        "auth.logout",
    ]


def test_navigation_replay_and_rate_limit_are_bounded(accounts):
    key = uuid4()
    payload = activity_api.NavigationEvent(
        event_key=key, action="company.view", company_rpj="B20010"
    )
    activity_api.navigation_event(payload, {"id": 2})
    activity_api.navigation_event(payload, {"id": 2})
    with accounts() as c:
        assert c.execute("SELECT COUNT(*) AS n FROM user_activity_events").fetchone()["n"] == 1
        for _ in range(59):
            record_activity(c, user_id=2, action="company.view", outcome="observed")
    with pytest.raises(HTTPException) as exc:
        activity_api.navigation_event(
            activity_api.NavigationEvent(
                event_key=uuid4(), action="company.view", company_rpj="B20010"
            ),
            {"id": 2},
        )
    assert exc.value.status_code == 429


def test_administrative_reads_are_audited_without_changing_usage_pages(accounts):
    before = user_admin.user_activity(2, ADMIN)
    user_admin.get_user(2, ADMIN)
    after = user_admin.user_activity(2, ADMIN)
    assert before["total"] == after["total"]
    assert before["events"] == after["events"]
    assert len(user_admin.audit_events(ADMIN)["events"]) == 3
