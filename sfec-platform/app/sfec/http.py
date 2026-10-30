"""Connecteur de l'API SFEC « ERP en ligne ».

Référence : https://docs.sfec.gouv.cg/api/certify et https://docs.sfec.gouv.cg/api/invoices
"""
from datetime import datetime
from urllib.parse import quote

import httpx

from .base import CertificationResult, SfecAuthError, SfecRejected, SfecUnavailable

BASE_URLS = {
    "sandbox": "https://sandbox.api.sfec.gouv.cg",
    "production": "https://api.sfec.gouv.cg",
}


def _message(r: httpx.Response) -> str:
    try:
        d = r.json()
    except ValueError:
        return f"HTTP {r.status_code}: {r.text[:300]}"
    if d.get("errors"):
        return "; ".join(f"{e.get('field')}: {e.get('code')} — {e.get('message')}" for e in d["errors"])
    return f"HTTP {r.status_code}: {d.get('message') or d.get('error') or r.text[:300]}"


def _date(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


class HttpSfecClient:
    def __init__(self, base_url: str, api_key: str, timeout: int = 30,
                 transport: httpx.BaseTransport | None = None) -> None:
        if not api_key:
            raise SfecAuthError("SFEC_API_KEY n'est pas configurée.")
        self.client = httpx.Client(
            base_url=base_url, timeout=timeout, transport=transport,
            headers={"X-API-Key": api_key, "Accept": "application/json"})

    def _check(self, r: httpx.Response) -> None:
        if r.status_code == 401:
            raise SfecAuthError(f"Clé API SFEC refusée — {_message(r)}")
        if r.status_code == 429 or r.status_code >= 500:
            raise SfecUnavailable(_message(r))
        if r.status_code >= 400:
            raise SfecRejected(_message(r))

    def certify(self, payload: dict) -> CertificationResult:
        try:
            r = self.client.post("/api/v1/invoices", json=payload)
        except httpx.TransportError as e:
            raise SfecUnavailable(str(e)) from e
        if r.status_code == 409:
            # Numéro déjà certifié (ex. : réponse perdue lors d'un envoi précédent) : on récupère la certification.
            existing = self.get_invoice(payload["invoice_id"])
            if existing and existing.get("certification_signature"):
                return CertificationResult(
                    existing["certification_signature"], existing["certification_short_signature"] or "",
                    existing["certification_qr_code"] or "", _date(existing["certification_date"]))
        self._check(r)
        d = r.json()
        return CertificationResult(d["signature"], d["short_signature"], d["qr_code"],
                                   _date(d["certification_date"]))

    def get_invoice(self, number: str) -> dict | None:
        try:
            r = self.client.get(f"/api/v1/invoices/{quote(number, safe='')}")
        except httpx.TransportError as e:
            raise SfecUnavailable(str(e)) from e
        if r.status_code == 404:
            return None
        self._check(r)
        return r.json()
