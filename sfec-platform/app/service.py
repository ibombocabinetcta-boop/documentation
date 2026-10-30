import html

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .models import CERTIFIED, ERROR, PENDING, REJECTED, Invoice
from .odoo import OdooGateway
from .sfec.base import SfecClient, SfecRejected, SfecUnavailable


def build_payload(inv: Invoice) -> dict:
    """Représentation neutre de la facture envoyée au SFEC (à ajuster selon sa spécification)."""
    return {
        "number": inv.number, "date": inv.invoice_date, "currency": inv.currency,
        "customer": {"name": inv.partner_name, "tax_id": inv.partner_tax_id},
        "untaxed": inv.amount_untaxed, "tax": inv.amount_tax, "total": inv.amount_total,
        "lines": inv.lines,
    }


def sync_from_odoo(db: Session, odoo: OdooGateway) -> int:
    """Importe les factures validées d'Odoo pas encore connues. Idempotent."""
    known = list(db.scalars(select(Invoice.odoo_id)))
    rows = odoo.fetch_posted_invoices(settings.sync_batch_size, known)
    for r in rows:
        db.add(Invoice(**r))
    db.commit()
    return len(rows)


def certify_invoice(db: Session, inv: Invoice, sfec: SfecClient, odoo: OdooGateway) -> Invoice:
    if inv.status == CERTIFIED:
        return inv
    inv.attempts += 1
    try:
        res = sfec.certify(build_payload(inv))
    except SfecRejected as e:
        inv.status, inv.error = REJECTED, str(e)
    except SfecUnavailable as e:
        inv.status = ERROR if inv.attempts >= settings.max_attempts else PENDING
        inv.error = str(e)
    else:
        inv.status, inv.error = CERTIFIED, ""
        inv.sfec_uid, inv.sfec_qr, inv.sfec_signature = res.uid, res.qr_code, res.signature
        inv.certified_at = res.certified_at
    db.commit()
    if inv.status == CERTIFIED:
        write_back(db, inv, odoo)
    return inv


def write_back(db: Session, inv: Invoice, odoo: OdooGateway) -> None:
    """Réécrit le résultat dans le chatter d'Odoo. Réessayé plus tard en cas d'échec."""
    if inv.written_back:
        return
    body = (f"<b>Facture certifiée SFEC</b><br/>UID : {html.escape(inv.sfec_uid)}<br/>"
            f"Date : {inv.certified_at:%Y-%m-%d %H:%M} UTC<br/>QR : {html.escape(inv.sfec_qr)}")
    try:
        odoo.post_certification(inv.odoo_id, body)
        inv.written_back = True
    except Exception as e:  # la certification reste valide ; on réessaiera
        inv.error = f"Écriture Odoo échouée : {e}"
    db.commit()


def certify_pending(db: Session, sfec: SfecClient, odoo: OdooGateway) -> dict:
    pending = list(db.scalars(select(Invoice).where(Invoice.status == PENDING).order_by(Invoice.id)))
    for inv in pending:
        certify_invoice(db, inv, sfec, odoo)
    for inv in db.scalars(select(Invoice).where(Invoice.status == CERTIFIED, Invoice.written_back.is_(False))):
        write_back(db, inv, odoo)
    return {"processed": len(pending)}
