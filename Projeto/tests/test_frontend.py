import pytest
from fastapi.testclient import TestClient

from sentineltrade.api import app
from conftest import make_user, PASSWORD
from test_api import login


@pytest.fixture
def client():
    return TestClient(app)


def test_home_serves_frontend(client):
    res = client.get("/")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/html")
    assert "SentinelTrade" in res.text
    assert "default-src 'self'" in res.headers["content-security-policy"]


@pytest.mark.parametrize("path,kind", [("/static/app.js", "javascript"), ("/static/style.css", "css")])
def test_static_assets_are_served(client, path, kind):
    res = client.get(path)
    assert res.status_code == 200
    assert kind in res.headers["content-type"]


def test_static_path_traversal_is_blocked(client):
    assert client.get("/static/../api.py").status_code == 404
    assert client.get("/static/%2e%2e/api.py").status_code == 404


def test_assets_expose_id_for_admin_screens(client, db, asset):
    make_user(db)
    headers = login(client, "investidor@teste.local", PASSWORD)
    items = client.get("/api/assets", headers=headers).json()
    assert items[0]["id"] == asset.id
    assert items[0]["symbol"] == "PETR4"
