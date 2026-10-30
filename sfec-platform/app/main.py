from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import service
from .config import settings
from .db import Base, engine, get_db
from .models import ERROR, Invoice
from .odoo import OdooClient
from .sfec import get_sfec_client

Base.metadata.create_all(engine)
app = FastAPI(title="Plateforme de connexion SFEC")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def get_odoo():
    return OdooClient()


def get_sfec():
    return get_sfec_client()


def require_key(x_api_key: str = Header(default="")):
    if settings.platform_api_key and x_api_key != settings.platform_api_key:
        raise HTTPException(401, "Clé API invalide")


@app.get("/health")
def health():
    return {"ok": True, "sfec_mode": settings.sfec_mode}


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    counts = dict(db.execute(select(Invoice.status, func.count()).group_by(Invoice.status)).all())
    invoices = db.scalars(select(Invoice).order_by(Invoice.id.desc()).limit(200)).all()
    return templates.TemplateResponse(request, "index.html", {
        "counts": counts, "invoices": invoices, "mode": settings.sfec_mode,
        "protected": bool(settings.platform_api_key)})


@app.get("/api/invoices", dependencies=[Depends(require_key)])
def list_invoices(status: str | None = None, db: Session = Depends(get_db)):
    q = select(Invoice).order_by(Invoice.id.desc()).limit(500)
    if status:
        q = q.where(Invoice.status == status)
    return [i.to_dict() for i in db.scalars(q)]


@app.post("/api/sync", dependencies=[Depends(require_key)])
def sync(db: Session = Depends(get_db), odoo=Depends(get_odoo), sfec=Depends(get_sfec)):
    """Importe depuis Odoo puis certifie tout ce qui est en attente."""
    try:
        imported = service.sync_from_odoo(db, odoo)
    except Exception as e:
        raise HTTPException(502, f"Odoo inaccessible : {e}")
    return {"imported": imported, **service.certify_pending(db, sfec, odoo)}


@app.post("/api/invoices/{invoice_id}/retry", dependencies=[Depends(require_key)])
def retry(invoice_id: int, db: Session = Depends(get_db), odoo=Depends(get_odoo), sfec=Depends(get_sfec)):
    inv = db.get(Invoice, invoice_id)
    if not inv:
        raise HTTPException(404, "Facture introuvable")
    if inv.status in ("rejected", ERROR):
        inv.status, inv.attempts = "pending", 0
    return service.certify_invoice(db, inv, sfec, odoo).to_dict()
