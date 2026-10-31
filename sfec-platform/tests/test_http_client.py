import httpx
import pytest

from app.sfec.base import SfecAuthError, SfecRejected, SfecUnavailable
from app.sfec.http import HttpSfecClient

SIG = "a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90"
OK = {"certification_number": SIG, "signature": SIG, "short_signature": "A1B2C3D4E5F60718293A",
      "identifier": "A1B2C3D4E5F60718293A", "invoice_number": "INV/1",
      "certification_date": "2026-07-28T14:33:35Z", "qr_code": "data:image/png;base64,iVBOR"}


def client(handler):
    return HttpSfecClient("https://sandbox.api.sfec.gouv.cg", "k", transport=httpx.MockTransport(handler))


def test_success_and_headers():
    def h(req):
        assert req.url.path == "/api/v1/invoices" and req.headers["X-API-Key"] == "k"
        return httpx.Response(201, json=OK)
    r = client(h).certify({"invoice_id": "INV/1"})
    assert r.signature == SIG and r.short_signature == "A1B2C3D4E5F60718293A"
    assert r.certified_at.year == 2026 and r.qr_code.startswith("data:image/png")


def test_validation_errors_are_readable():
    body = {"error": "Validation failed", "warnings": [],
            "errors": [{"field": "recipient_name", "code": "REQUIRED", "message": "recipient_name is required"}]}
    with pytest.raises(SfecRejected, match="recipient_name: REQUIRED"):
        client(lambda r: httpx.Response(400, json=body)).certify({"invoice_id": "X"})


def test_409_recovers_existing_certification():
    def h(req):
        if req.method == "POST":
            return httpx.Response(409, json={"message": "invoice with the same invoice number already exists"})
        assert req.url.raw_path == b"/api/v1/invoices/INV%2F1"
        return httpx.Response(200, json={"certification_signature": SIG,
                                         "certification_short_signature": "A1B2C3D4E5F60718293A",
                                         "certification_qr_code": "data:x", "certification_date": "2026-07-28T14:33:35.609Z"})
    assert client(h).certify({"invoice_id": "INV/1"}).signature == SIG


def test_409_not_found_is_rejection():
    def h(req):
        if req.method == "POST":
            return httpx.Response(409, json={"message": "referenced invoice already has a credit note"})
        return httpx.Response(404, json={"message": "invoice not found"})
    with pytest.raises(SfecRejected, match="credit note"):
        client(h).certify({"invoice_id": "AV/1"})


@pytest.mark.parametrize("code,exc", [(401, SfecAuthError), (429, SfecUnavailable), (500, SfecUnavailable)])
def test_error_classes(code, exc):
    with pytest.raises(exc):
        client(lambda r: httpx.Response(code, json={"message": "x"})).certify({"invoice_id": "X"})
