"""Contrat du connecteur SFEC. Toute la plateforme ne dépend que de `SfecClient`."""
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


class SfecRejected(Exception):
    """Refus du SFEC sur les données (400, 404, 409) : corriger la facture avant de renvoyer."""


class SfecUnavailable(Exception):
    """Erreur transitoire (réseau, 429, 5xx) : la facture sera renvoyée plus tard."""


class SfecAuthError(SfecUnavailable):
    """Clé API absente, invalide ou inactive (401) : on interrompt tout le lot."""


@dataclass
class CertificationResult:
    signature: str
    short_signature: str
    qr_code: str  # data URI PNG en base64
    certified_at: datetime


class SfecClient(Protocol):
    def certify(self, payload: dict) -> CertificationResult: ...
