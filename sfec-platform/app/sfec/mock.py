"""Simulateur local du SFEC pour développer et tester sans accès à l'API réelle."""
import hashlib
import json
from datetime import datetime, timezone

from .base import CertificationResult, SfecRejected


class MockSfecClient:
    def certify(self, payload: dict) -> CertificationResult:
        if not payload.get("number"):
            raise SfecRejected("Numéro de facture manquant")
        if payload.get("total", 0) <= 0:
            raise SfecRejected("Montant total invalide")
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        return CertificationResult(
            uid=f"MOCK-{digest[:16].upper()}",
            qr_code=f"MOCK-QR:{digest[:32]}",
            signature=digest,
            certified_at=datetime.now(timezone.utc),
        )
