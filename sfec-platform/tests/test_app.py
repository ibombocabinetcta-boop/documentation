import base64

import pytest
from fastapi.testclient import TestClient

from app import scheduler
from app.config import settings
from app.db import SessionLocal
from app.main import app
from app.models import CERTIFIED, Invoice
from app.sfec.mock import MockSfecClient
from tests.conftest import bundle
from tests.test_sync import FakeOdoo


def basic(user, pwd):
    return {"Authorization": "Basic " + base64.b64encode(f"{user}:{pwd}".encode()).decode()}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(settings, "admin_password", "s3cret")
    monkeypatch.setattr(settings, "platform_api_key", "machine-key")
    with TestClient(app) as c:
        yield c


def test_health_is_public(client):
    assert client.get("/health").status_code == 200


def test_dashboard_requires_password(client):
    assert client.get("/").status_code == 401
    assert client.get("/", headers=basic("admin", "wrong")).status_code == 401
    assert client.get("/", headers=basic("admin", "s3cret")).status_code == 200


def test_api_key_for_machines(client):
    assert client.get("/api/invoices", headers={"X-API-Key": "machine-key"}).status_code == 200
    assert client.get("/api/invoices", headers={"X-API-Key": "bad"}).status_code == 401


def test_no_password_outside_mock_is_refused(monkeypatch):
    monkeypatch.setattr(settings, "admin_password", "")
    monkeypatch.setattr(settings, "sfec_mode", "sandbox")
    with TestClient(app) as c:
        assert c.get("/").status_code == 503


def test_scheduler_run_once_and_lock(client):
    odoo, sfec = FakeOdoo([bundle(901)]), MockSfecClient()
    assert scheduler.run_once(lambda: odoo, lambda: sfec) == {"imported": 1, "processed": 1}
    with SessionLocal() as db:
        assert db.query(Invoice).filter_by(odoo_id=901).one().status == CERTIFIED
    assert scheduler.last_run["error"] == ""
    scheduler._lock.acquire()
    try:
        with pytest.raises(scheduler.SyncBusy):
            scheduler.run_once(lambda: odoo, lambda: sfec)
    finally:
        scheduler._lock.release()
    page = client.get("/", headers=basic("admin", "s3cret")).text
    assert "1 importée(s)" in page
