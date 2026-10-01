from unittest.mock import MagicMock

import pytest
from app import admin
from app.auth import ProfileUpdateRequest, RegisterRequest, current_user
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(admin.router)
    return TestClient(app)


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/admin/analysis-jobs"),
        ("get", "/admin/analysis-jobs/5"),
        ("get", "/admin/analysis-jobs/5/events"),
        ("post", "/admin/analysis-jobs/5/retry"),
    ],
)
def test_every_admin_endpoint_requires_authenticated_admin(client, monkeypatch, method, path):
    connect = MagicMock(side_effect=AssertionError("Must not open the DB without permission"))
    monkeypatch.setattr(admin, "connect", connect)
    request = getattr(client, method)
    kwargs = {"json": {"reason": "Documento corregido"}} if method == "post" else {}
    assert request(path, **kwargs).status_code == 401
    client.app.dependency_overrides[current_user] = lambda: {"id": 1, "is_admin": False}
    assert request(path, **kwargs).status_code == 403
    connect.assert_not_called()


def test_public_account_payloads_cannot_assign_admin():
    register = RegisterRequest(
        email="ordinary@example.com",
        full_name="Usuario normal",
        password="test-password-only",
        is_admin=True,
    )
    profile = ProfileUpdateRequest(full_name="Usuario normal", is_admin=True)
    assert "is_admin" not in register.model_dump()
    assert "is_admin" not in profile.model_dump()


def test_admin_role_is_checked_on_each_request(client, monkeypatch):
    current = {"id": 1, "is_admin": True}
    client.app.dependency_overrides[current_user] = lambda: current
    listing = MagicMock()
    conn = listing.return_value.__enter__.return_value
    conn.execute.return_value.fetchone.return_value = {"n": 0}
    conn.execute.return_value.fetchall.return_value = []
    monkeypatch.setattr(admin, "connect", listing)
    assert client.get("/admin/analysis-jobs").status_code == 200
    current["is_admin"] = False
    assert client.get("/admin/analysis-jobs").status_code == 403
    assert listing.call_count == 1


@pytest.mark.parametrize("reason", ["", "          ", "corto", "a" * 501])
def test_retry_requires_meaningful_bounded_reason(client, reason, monkeypatch):
    client.app.dependency_overrides[current_user] = lambda: {"id": 1, "is_admin": True}
    connect = MagicMock()
    monkeypatch.setattr(admin, "connect", connect)
    assert client.post("/admin/analysis-jobs/5/retry", json={"reason": reason}).status_code == 422
    connect.assert_not_called()


@pytest.mark.parametrize("state", ["running", "queued", "retrying", "completed"])
def test_cannot_retry_active_or_completed_jobs(state, monkeypatch):
    connection = MagicMock()
    connection.execute.return_value.fetchone.side_effect = [
        {"smv_rpj": "B20010", "fiscal_year": 2025, "company_id": 10},
        {"support_level": "full"},
        {"status": state},
    ]
    context = MagicMock()
    context.__enter__.return_value = connection
    monkeypatch.setattr(admin, "connect", lambda: context)
    with pytest.raises(HTTPException) as exc:
        admin.retry_job(
            5,
            admin.RetryRequest(reason="Corrección de documento"),
            {"id": 1, "email": "admin@example.test"},
        )
    assert exc.value.status_code == 409
    connection.commit.assert_not_called()
    assert all(c.args[0].lstrip().startswith("SELECT") for c in connection.execute.call_args_list)
