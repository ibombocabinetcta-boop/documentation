"""Connecteur HTTP vers l'API réelle du SFEC.

⚠️ À ADAPTER : les chemins, le format du corps et les noms des champs de réponse
ci-dessous sont des PLACEHOLDERS en attente de la documentation officielle du SFEC.
"""
from datetime import datetime, timezone

import httpx

from ..config import settings
from .base import CertificationResult, SfecRejected, SfecUnavailable

CERTIFY_PATH = "/invoices"  # TODO: endpoint réel


class HttpSfecClient:
    def __init__(self) -> None:
        if not settings.sfec_base_url:
            raise RuntimeError("SFEC_BASE_URL n'est pas configuré.")
        self.client = httpx.Client(
            base_url=settings.sfec_base_url,
            timeout=settings.sfec_timeout,
            headers={"Authorization": f"Bearer {settings.sfec_api_token}"},  # TODO: auth réelle
        )

    def certify(self, payload: dict) -> CertificationResult:
        try:
            r = self.client.post(CERTIFY_PATH, json=payload)
        except httpx.TransportError as e:
            raise SfecUnavailable(str(e)) from e
        if r.status_code >= 500 or r.status_code == 429:
            raise SfecUnavailable(f"SFEC HTTP {r.status_code}")
        if r.status_code >= 400:
            raise SfecRejected(f"SFEC HTTP {r.status_code}: {r.text[:500]}")
        d = r.json()
        # TODO: mapper les vrais noms de champs
        return CertificationResult(
            uid=str(d["uid"]), qr_code=d.get("qr_code", ""), signature=d.get("signature", ""),
            certified_at=datetime.now(timezone.utc),
        )
