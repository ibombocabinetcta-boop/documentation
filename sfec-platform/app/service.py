import html

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .mapping import MappingError, build_payload
from .models import CERTIFIED, ERROR, PENDING, REJECTED, Invoice
from .odoo import OdooGateway
from .sfec.base import SfecAuthError, SfecClient, SfecRejected, SfecUnavailable


def apply_bundle(inv: Invoice, bundle: dict) -> Invoice:
    """(Re)construit le corps SFEC à partir des données Odoo."""
    inv.odoo_id, inv.number = bundle["odoo_id"], bundle["number"]
    inv.partner_name, inv.invoice_date = bundle["partner"]["name"], bundle["invoice_date"]
    inv.currency, inv.amount_total = bundle["currency"], bundle["amount_total"]
    try:
        inv.payload = build_payload(bundle)
        inv.invoice_type = inv.payload["invoice_type"]
        inv.status, inv.error = PENDING, ""
    except MappingError as e:
        inv.payload, inv.status, inv.error = None, REJECTED, str(e)
    return inv


def sync_from_odoo(db: Session, odoo: OdooGateway) -> int:
    """Importe les factures validées d'Odoo pas encore connues. Idempotent."""
    if settings.sfec_mode != "mock" and not settings.sync_from_date:
        raise ValueError("Définissez SYNC_FROM_DATE pour ne pas envoyer l'historique au SFEC.")
    known = list(db.scalars(select(Invoice.odoo_id)))
    bundles = odoo.fetch_new(settings.sync_batch_size, known, settings.sync_from_date)
    for b in bundles:
        db.add(apply_bundle(Invoice(), b))
    db.commit()
    return len(bundles)


def refresh_from_odoo(db: Session, inv: Invoice, odoo: OdooGateway) -> Invoice:
    """Relit la facture dans Odoo (après correction) et la remet en attente."""
    bundles = odoo.fetch_by_ids([inv.odoo_id])
    if not bundles:
        raise LookupError("Facture introuvable dans Odoo.")
    apply_bundle(inv, bundles[0])
    inv.attempts = 0
    db.commit()
    return inv


def certify_invoice(db: Session, inv: Invoice, sfec: SfecClient, odoo: OdooGateway) -> Invoice:
    if inv.status != PENDING or not inv.payload:
        return inv
    try:
        res = sfec.certify(inv.payload)
    except SfecAuthError:
        raise
    except SfecRejected as e:
        inv.attempts += 1
        inv.status, inv.error = REJECTED, str(e)
    except SfecUnavailable as e:
        inv.attempts += 1
        inv.status = ERROR if inv.attempts >= settings.max_attempts else PENDING
        inv.error = str(e)
    else:
        inv.attempts += 1
        inv.status, inv.error = CERTIFIED, ""
        inv.signature, inv.short_signature = res.signature, res.short_signature
        inv.qr_code, inv.certified_at = res.qr_code, res.certified_at
    db.commit()
    if inv.status == CERTIFIED:
        write_back(db, inv, odoo)
    return inv


def write_back(db: Session, inv: Invoice, odoo: OdooGateway) -> None:
    """Dépose la certification dans le chatter Odoo. Réessayé plus tard en cas d'échec."""
    if inv.written_back:
        return
    body = (f"<b>Facture certifiée SFEC</b><br/>"
            f"Signature : <b>{html.escape(inv.short_signature)}</b><br/>"
            f"Date : {inv.certified_at:%d/%m/%Y %H:%M:%S} UTC<br/>"
            f"<small>Signature complète : {html.escape(inv.signature)}</small>")
    qr_b64 = inv.qr_code.split(",", 1)[1] if inv.qr_code.startswith("data:") else ""
    try:
        odoo.post_certification(inv.odoo_id, body, qr_b64, f"QR-SFEC-{inv.number.replace('/', '-')}.png")
        inv.written_back = True
    except Exception as e:  # la certification reste valide ; on réessaiera
        inv.error = f"Écriture Odoo échouée : {e}"
    db.commit()


def certify_pending(db: Session, sfec: SfecClient, odoo: OdooGateway) -> dict:
    pending = list(db.scalars(select(Invoice).where(Invoice.status == PENDING).order_by(Invoice.odoo_id)))
    for inv in pending:
        certify_invoice(db, inv, sfec, odoo)
    for inv in db.scalars(select(Invoice).where(Invoice.status == CERTIFIED, Invoice.written_back.is_(False))):
        write_back(db, inv, odoo)
    return {"processed": len(pending)}
