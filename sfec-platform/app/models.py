from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base

PENDING, CERTIFIED, REJECTED, ERROR = "pending", "certified", "rejected", "error"


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True)
    odoo_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    number: Mapped[str] = mapped_column(String(64), index=True)
    invoice_type: Mapped[str] = mapped_column(String(32), default="salesInvoice")
    partner_name: Mapped[str] = mapped_column(String(255), default="")
    invoice_date: Mapped[str] = mapped_column(String(10), default="")
    currency: Mapped[str] = mapped_column(String(8), default="XAF")
    amount_total: Mapped[float] = mapped_column(Float, default=0)
    # Corps exact envoyé (ou à envoyer) au SFEC
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    status: Mapped[str] = mapped_column(String(16), default=PENDING, index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str] = mapped_column(Text, default="")
    written_back: Mapped[bool] = mapped_column(default=False)

    signature: Mapped[str] = mapped_column(String(64), default="")
    short_signature: Mapped[str] = mapped_column(String(20), default="")
    qr_code: Mapped[str] = mapped_column(Text, default="")
    certified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "odoo_id": self.odoo_id, "number": self.number,
            "invoice_type": self.invoice_type, "partner_name": self.partner_name,
            "invoice_date": self.invoice_date, "currency": self.currency,
            "amount_total": self.amount_total, "status": self.status,
            "attempts": self.attempts, "error": self.error,
            "signature": self.signature, "short_signature": self.short_signature,
            "certified_at": self.certified_at.isoformat() if self.certified_at else None,
            "written_back": self.written_back,
        }
