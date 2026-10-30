"""Contrat du connecteur SFEC.

Toute la plateforme ne dépend que de `SfecClient`. Quand la documentation officielle
sera disponible, seul `http.py` doit être adapté.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


class SfecRejected(Exception):
    """La facture a été refusée par le SFEC (erreur de données : ne pas réessayer telle quelle)."""


class SfecUnavailable(Exception):
    """Erreur transitoire (réseau, 5xx) : la facture sera renvoyée plus tard."""


@dataclass
class CertificationResult:
    uid: str
    qr_code: str
    signature: str
    certified_at: datetime


class SfecClient(Protocol):
    def certify(self, payload: dict) -> CertificationResult: ...
