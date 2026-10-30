"""Simulateur local du SFEC : reproduit la forme des réponses de l'API réelle, sans valeur légale."""
import hashlib
import json
from datetime import datetime, timezone

from .base import CertificationResult, SfecRejected

# PNG 1x1 transparent
_PNG = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="


class MockSfecClient:
    def __init__(self) -> None:
        self.seen: set[str] = set()

    def certify(self, payload: dict) -> CertificationResult:
        for f in ("invoice_id", "invoice_type", "recipient_type", "currency"):
            if not payload.get(f):
                raise SfecRejected(f"{f}: REQUIRED")
        if not payload.get("items"):
            raise SfecRejected("items: REQUIRED")
        if payload["recipient_type"] in ("business", "government"):
            niu = payload.get("recipient_niu") or ""
            if not 16 <= len(niu) <= 17:
                raise SfecRejected("recipient_niu: INVALID_LENGTH (16 ou 17 caractères)")
        if payload["invoice_id"] in self.seen:
            raise SfecRejected("invoice with the same invoice number already exists")
        self.seen.add(payload["invoice_id"])
        sig = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        return CertificationResult(sig, sig[:20].upper(), f"data:image/png;base64,{_PNG}",
                                   datetime.now(timezone.utc))
