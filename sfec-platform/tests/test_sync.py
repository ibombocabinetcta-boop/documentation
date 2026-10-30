import os

os.environ["DATABASE_URL"] = "sqlite://"

import pytest
from sqlalchemy.pool import StaticPool
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import service
from app.db import Base
from app.models import CERTIFIED, PENDING, REJECTED, Invoice
from app.sfec.base import SfecUnavailable
from app.sfec.mock import MockSfecClient


class FakeOdoo:
    def __init__(self, rows):
        self.rows, self.posted, self.fail = rows, [], False

    def fetch_posted_invoices(self, limit, exclude_ids):
        return [r for r in self.rows if r["odoo_id"] not in exclude_ids][:limit]

    def post_certification(self, odoo_id, body):
        if self.fail:
            raise RuntimeError("odoo down")
        self.posted.append(odoo_id)


def row(i, total=100.0):
    return {"odoo_id": i, "number": f"INV/{i}", "amount_total": total, "amount_untaxed": total,
            "amount_tax": 0, "lines": [], "currency": "XAF"}


@pytest.fixture
def db():
    eng = create_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(eng)
    with sessionmaker(bind=eng, expire_on_commit=False)() as s:
        yield s


def test_full_flow_and_idempotence(db):
    odoo = FakeOdoo([row(1), row(2)])
    assert service.sync_from_odoo(db, odoo) == 2
    assert service.sync_from_odoo(db, odoo) == 0
    service.certify_pending(db, MockSfecClient(), odoo)
    assert all(i.status == CERTIFIED and i.sfec_uid for i in db.query(Invoice))
    assert odoo.posted == [1, 2]


def test_rejected_invoice(db):
    odoo = FakeOdoo([row(1, total=0)])
    service.sync_from_odoo(db, odoo)
    service.certify_pending(db, MockSfecClient(), odoo)
    assert db.query(Invoice).one().status == REJECTED


def test_transient_error_stays_pending(db):
    class Down:
        def certify(self, p):
            raise SfecUnavailable("timeout")
    odoo = FakeOdoo([row(1)])
    service.sync_from_odoo(db, odoo)
    service.certify_pending(db, Down(), odoo)
    inv = db.query(Invoice).one()
    assert inv.status == PENDING and inv.attempts == 1


def test_writeback_retried_without_recertifying(db):
    odoo = FakeOdoo([row(1)])
    odoo.fail = True
    service.sync_from_odoo(db, odoo)
    service.certify_pending(db, MockSfecClient(), odoo)
    inv = db.query(Invoice).one()
    assert inv.status == CERTIFIED and not inv.written_back
    uid = inv.sfec_uid
    odoo.fail = False
    service.certify_pending(db, MockSfecClient(), odoo)
    assert inv.written_back and inv.sfec_uid == uid and odoo.posted == [1]
