from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from sentineltrade import services
from sentineltrade.api import app
from conftest import PASSWORD, PIN, make_user


@pytest.fixture
def client():
    return TestClient(app)


def login(client, email, password=PASSWORD):
    first = client.post("/api/auth/login", json={"email": email, "password": password})
    assert first.status_code == 200, first.text
    body = first.json()
    second = client.post("/api/auth/verify-mfa",
                         json={"challenge_id": body["challenge_id"], "code": body["debug_code"]})
    assert second.status_code == 200, second.text
    return {"Authorization": f"Bearer {second.json()['access_token']}"}


def order_payload(**overrides):
    payload = {"symbol": "PETR4", "side": "BUY", "quantity": 10, "idempotency_key": "api-chave-0001", "pin": PIN}
    payload.update(overrides)
    return payload


def test_health(client):
    assert client.get("/health").json() == {"status": "ok", "mode": "simulated"}


def test_protected_routes_require_authentication(client):
    assert client.get("/api/portfolio").status_code == 401
    assert client.get("/api/portfolio", headers={"Authorization": "Bearer invalido"}).status_code == 401


def test_register_and_duplicate_email(client):
    payload = {"name": "Maria Silva", "email": "Maria@Teste.local", "password": "Senha-Forte-1", "pin": "4321"}
    created = client.post("/api/investors", json=payload)
    assert created.status_code == 201
    assert created.json()["email"] == "maria@teste.local"
    assert client.post("/api/investors", json=payload).status_code == 400


def test_login_with_wrong_password(client, investor):
    response = client.post("/api/auth/login", json={"email": investor.email, "password": "errada"})
    assert response.status_code == 400


def test_debug_code_is_omitted_outside_development(client, investor, monkeypatch):
    monkeypatch.setattr(services, "settings", replace(services.settings, app_env="production"))
    body = client.post("/api/auth/login", json={"email": investor.email, "password": PASSWORD}).json()
    assert "challenge_id" in body
    assert "debug_code" not in body


def test_investor_cannot_read_audit_but_auditor_can(client, db, investor):
    make_user(db, email="auditor@teste.local", role="AUDITOR")
    assert client.get("/api/audit", headers=login(client, investor.email)).status_code == 403
    assert client.get("/api/audit", headers=login(client, "auditor@teste.local")).status_code == 200


def test_order_lifecycle_through_api(client, db, investor, asset, market_open):
    make_user(db, email="admin@teste.local", role="ADMIN", balance="0")
    investor_headers = login(client, investor.email)
    admin_headers = login(client, "admin@teste.local")

    created = client.post("/api/orders", json=order_payload(), headers=investor_headers)
    assert created.status_code == 201, created.text
    order = created.json()
    assert order["status"] == "SENT"

    # Mesma chave de idempotência devolve a mesma ordem.
    again = client.post("/api/orders", json=order_payload(), headers=investor_headers)
    assert again.json()["id"] == order["id"]

    # Investidor não pode simular retorno da corretora.
    forbidden = client.post(f"/api/orders/{order['id']}/broker-update",
                            json={"status": "FILLED", "filled_quantity": 10}, headers=investor_headers)
    assert forbidden.status_code == 403

    filled = client.post(f"/api/orders/{order['id']}/broker-update",
                         json={"status": "FILLED", "filled_quantity": 10}, headers=admin_headers)
    assert filled.status_code == 200, filled.text
    assert filled.json()["status"] == "FILLED"

    portfolio = client.get("/api/portfolio", headers=investor_headers).json()
    assert portfolio["balance"].startswith("99615")
    assert portfolio["positions"][0]["symbol"] == "PETR4"
    assert portfolio["positions"][0]["quantity"] == 10

    assert len(client.get("/api/history", headers=investor_headers).json()) == 1
    assert client.get("/api/notifications", headers=investor_headers).json()


def test_broker_update_rejects_unknown_status(client, db, investor, asset, market_open):
    make_user(db, email="admin@teste.local", role="ADMIN", balance="0")
    order = client.post("/api/orders", json=order_payload(), headers=login(client, investor.email)).json()
    response = client.post(f"/api/orders/{order['id']}/broker-update",
                           json={"status": "XYZ", "filled_quantity": 0},
                           headers=login(client, "admin@teste.local"))
    assert response.status_code == 422


def test_other_investor_cannot_see_or_cancel_order(client, db, investor, asset, market_open):
    make_user(db, email="outro@teste.local")
    order = client.post("/api/orders", json=order_payload(), headers=login(client, investor.email)).json()
    other = login(client, "outro@teste.local")
    assert client.get(f"/api/orders/{order['id']}", headers=other).status_code == 404
    assert client.post(f"/api/orders/{order['id']}/cancel", headers=other).status_code == 404


def test_owner_can_cancel_and_balance_is_restored(client, db, investor, asset, market_open):
    headers = login(client, investor.email)
    order = client.post("/api/orders", json=order_payload(), headers=headers).json()
    cancelled = client.post(f"/api/orders/{order['id']}/cancel", headers=headers)
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "CANCELLED"
    assert client.get("/api/portfolio", headers=headers).json()["balance"].startswith("100000")


def test_risk_limits_validation(client, db, investor):
    make_user(db, email="admin@teste.local", role="ADMIN", balance="0")
    headers = login(client, "admin@teste.local")
    url = f"/api/admin/investors/{investor.id}/risk-limits"
    bad = client.patch(url, json={"daily_order_limit": "1000", "daily_exposure_limit": "500"}, headers=headers)
    assert bad.status_code == 422
    good = client.patch(url, json={"daily_order_limit": "1000", "daily_exposure_limit": "5000"}, headers=headers)
    assert good.status_code == 200
