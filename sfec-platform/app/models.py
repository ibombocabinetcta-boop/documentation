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
    partner_name: Mapped[str] = mapped_column(String(255), default="")
    partner_tax_id: Mapped[str] = mapped_column(String(64), default="")
    invoice_date: Mapped[str] = mapped_column(String(10), default="")
    currency: Mapped[str] = mapped_column(String(8), default="XAF")
    amount_untaxed: Mapped[float] = mapped_column(Float, default=0)
    amount_tax: Mapped[float] = mapped_column(Float, default=0)
    amount_total: Mapped[float] = mapped_column(Float, default=0)
    lines: Mapped[list] = mapped_column(JSON, default=list)

    status: Mapped[str] = mapped_column(String(16), default=PENDING, index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str] = mapped_column(Text, default="")
    written_back: Mapped[bool] = mapped_column(default=False)

    sfec_uid: Mapped[str] = mapped_column(String(128), default="")
    sfec_qr: Mapped[str] = mapped_column(Text, default="")
    sfec_signature: Mapped[str] = mapped_column(Text, default="")
    certified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "odoo_id": self.odoo_id, "number": self.number,
            "partner_name": self.partner_name, "partner_tax_id": self.partner_tax_id,
            "invoice_date": self.invoice_date, "currency": self.currency,
            "amount_untaxed": self.amount_untaxed, "amount_tax": self.amount_tax,
            "amount_total": self.amount_total, "status": self.status,
            "attempts": self.attempts, "error": self.error,
            "sfec_uid": self.sfec_uid, "sfec_qr": self.sfec_qr,
            "certified_at": self.certified_at.isoformat() if self.certified_at else None,
            "written_back": self.written_back,
        }
