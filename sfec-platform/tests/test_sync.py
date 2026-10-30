import pytest

from app import service
from app.models import CERTIFIED, PENDING, REJECTED, Invoice
from app.sfec.base import SfecAuthError, SfecUnavailable
from app.sfec.mock import MockSfecClient
from tests.conftest import bundle


class FakeOdoo:
    def __init__(self, bundles):
        self.bundles, self.posted, self.fail = {b["odoo_id"]: b for b in bundles}, [], False

    def fetch_new(self, limit, exclude_ids, from_date):
        return [b for i, b in self.bundles.items() if i not in exclude_ids][:limit]

    def fetch_by_ids(self, ids):
        return [self.bundles[i] for i in ids if i in self.bundles]

    def post_certification(self, odoo_id, body, qr_png_b64, filename):
        if self.fail:
            raise RuntimeError("odoo down")
        assert qr_png_b64 and filename.endswith(".png") and "/" not in filename
        self.posted.append(odoo_id)


def test_full_flow_and_idempotence(db):
    odoo = FakeOdoo([bundle(1), bundle(2)])
    assert service.sync_from_odoo(db, odoo) == 2
    assert service.sync_from_odoo(db, odoo) == 0
    service.certify_pending(db, MockSfecClient(), odoo)
    invs = db.query(Invoice).all()
    assert all(i.status == CERTIFIED and len(i.signature) == 64 and len(i.short_signature) == 20 for i in invs)
    assert odoo.posted == [1, 2]


def test_mapping_error_then_fixed_in_odoo(db):
    odoo = FakeOdoo([bundle(1, amount_total=5)])  # total incohérent
    service.sync_from_odoo(db, odoo)
    inv = db.query(Invoice).one()
    assert inv.status == REJECTED and "arrondi" in inv.error and inv.payload is None
    odoo.bundles[1] = bundle(1)  # corrigée dans Odoo
    service.refresh_from_odoo(db, inv, odoo)
    service.certify_invoice(db, inv, MockSfecClient(), odoo)
    assert inv.status == CERTIFIED


def test_sfec_rejection(db):
    b = bundle(1)
    b["partner"]["vat"] = "123"
    odoo = FakeOdoo([b])
    service.sync_from_odoo(db, odoo)
    service.certify_pending(db, MockSfecClient(), odoo)
    inv = db.query(Invoice).one()
    assert inv.status == REJECTED and "recipient_niu" in inv.error


def test_transient_error_stays_pending(db):
    class Down:
        def certify(self, p):
            raise SfecUnavailable("timeout")
    odoo = FakeOdoo([bundle(1)])
    service.sync_from_odoo(db, odoo)
    service.certify_pending(db, Down(), odoo)
    inv = db.query(Invoice).one()
    assert inv.status == PENDING and inv.attempts == 1


def test_auth_error_stops_batch_without_counting(db):
    class BadKey:
        def certify(self, p):
            raise SfecAuthError("401")
    odoo = FakeOdoo([bundle(1), bundle(2)])
    service.sync_from_odoo(db, odoo)
    with pytest.raises(SfecAuthError):
        service.certify_pending(db, BadKey(), odoo)
    assert all(i.status == PENDING and i.attempts == 0 for i in db.query(Invoice))


def test_writeback_retried_without_recertifying(db):
    odoo = FakeOdoo([bundle(1)])
    odoo.fail = True
    sfec = MockSfecClient()
    service.sync_from_odoo(db, odoo)
    service.certify_pending(db, sfec, odoo)
    inv = db.query(Invoice).one()
    assert inv.status == CERTIFIED and not inv.written_back
    odoo.fail = False
    service.certify_pending(db, sfec, odoo)  # le mock lèverait un doublon si on recertifiait
    assert inv.written_back and odoo.posted == [1]


def test_history_guard_outside_mock(db, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "sfec_mode", "sandbox")
    monkeypatch.setattr(settings, "sync_from_date", "")
    with pytest.raises(ValueError, match="SYNC_FROM_DATE"):
        service.sync_from_odoo(db, FakeOdoo([bundle(1)]))
