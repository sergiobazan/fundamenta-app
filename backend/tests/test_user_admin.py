import pytest
from app import activity_api, user_admin
from app.auth import current_user
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/admin/users"),
        ("get", "/admin/users/2"),
        ("get", "/admin/users/2/activity"),
        ("post", "/admin/users/2/access"),
        ("get", "/admin/summary"),
        ("get", "/admin/audit"),
    ],
)
def test_every_user_admin_endpoint_enforces_permissions(method, path, monkeypatch):
    app = FastAPI()
    app.include_router(user_admin.router)

    def fail():
        raise AssertionError("No DB access without permission")

    monkeypatch.setattr(user_admin, "connect", fail)
    with TestClient(app) as client:
        fn = getattr(client, method)
        body = (
            {"json": {"action": "suspend", "reason": "Prueba de autorización"}}
            if method == "post"
            else {}
        )
        assert fn(path, **body).status_code == 401
        app.dependency_overrides[current_user] = lambda: {"id": 2, "is_admin": False}
        assert fn(path, **body).status_code == 403


def test_navigation_cannot_spoof_actor_or_inject_content():
    app = FastAPI()
    app.include_router(activity_api.router)
    app.dependency_overrides[current_user] = lambda: {"id": 2}
    with TestClient(app) as client:
        payload = {
            "event_key": "af85c75d-d548-488a-8f4c-a3e0739c6b77",
            "action": "company.view",
            "user_id": 1,
            "prompt": "SECRET",
        }
        assert client.post("/activity", json=payload).status_code == 422


def test_bad_window_rejected():
    from datetime import date

    from fastapi import HTTPException

    with pytest.raises(HTTPException):
        user_admin.window(date(2026, 5, 1), date(2026, 4, 1))
