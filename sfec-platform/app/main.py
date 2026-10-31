import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import scheduler, service
from .config import settings
from .db import Base, engine, get_db
from .models import CERTIFIED, Invoice
from .odoo import OdooClient
from .sfec import get_sfec_client
from .sfec.base import SfecAuthError


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    stop = None
    if settings.sync_interval_minutes > 0:
        stop = scheduler.start(settings.sync_interval_minutes, OdooClient, get_sfec_client)
    yield
    if stop:
        stop.set()


app = FastAPI(title="Plateforme de connexion SFEC", lifespan=lifespan)
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
basic = HTTPBasic(auto_error=False)


def _eq(a: str, b: str) -> bool:
    return secrets.compare_digest(a.encode(), b.encode())


def require_auth(creds: HTTPBasicCredentials | None = Depends(basic), x_api_key: str = Header(default="")):
    if settings.platform_api_key and x_api_key and _eq(x_api_key, settings.platform_api_key):
        return
    if settings.admin_password:
        if creds and _eq(creds.username, settings.admin_user) and _eq(creds.password, settings.admin_password):
            return
        raise HTTPException(401, "Authentification requise", headers={"WWW-Authenticate": 'Basic realm="SFEC"'})
    if settings.sfec_mode != "mock":
        raise HTTPException(503, "Définissez ADMIN_PASSWORD avant d'utiliser la plateforme.")


def get_odoo():
    return OdooClient()


def get_sfec():
    try:
        return get_sfec_client()
    except (SfecAuthError, ValueError) as e:
        raise HTTPException(500, str(e))


@app.get("/health")
def health():
    return {"ok": True, "sfec_mode": settings.sfec_mode}


@app.get("/", response_class=HTMLResponse, dependencies=[Depends(require_auth)])
def dashboard(request: Request, db: Session = Depends(get_db)):
    counts = dict(db.execute(select(Invoice.status, func.count()).group_by(Invoice.status)).all())
    invoices = db.scalars(select(Invoice).order_by(Invoice.id.desc()).limit(200)).all()
    return templates.TemplateResponse(request, "index.html", {
        "counts": counts, "invoices": invoices, "mode": settings.sfec_mode,
        "interval": settings.sync_interval_minutes, "last_run": scheduler.last_run})


@app.get("/api/invoices", dependencies=[Depends(require_auth)])
def list_invoices(status: str | None = None, db: Session = Depends(get_db)):
    q = select(Invoice).order_by(Invoice.id.desc()).limit(500)
    if status:
        q = q.where(Invoice.status == status)
    return [i.to_dict() for i in db.scalars(q)]


@app.get("/api/invoices/{invoice_id}", dependencies=[Depends(require_auth)])
def get_invoice(invoice_id: int, db: Session = Depends(get_db)):
    inv = db.get(Invoice, invoice_id) or _404()
    return {**inv.to_dict(), "payload": inv.payload, "qr_code": inv.qr_code}


@app.post("/api/sync", dependencies=[Depends(require_auth)])
def sync():
    """Importe depuis Odoo puis certifie tout ce qui est en attente."""
    try:
        return scheduler.run_once(get_odoo, get_sfec_client)
    except scheduler.SyncBusy as e:
        raise HTTPException(409, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(502, f"Synchronisation échouée : {e}")


@app.post("/api/invoices/{invoice_id}/retry", dependencies=[Depends(require_auth)])
def retry(invoice_id: int, db: Session = Depends(get_db), odoo=Depends(get_odoo), sfec=Depends(get_sfec)):
    """Relit la facture dans Odoo (après correction) et la renvoie au SFEC."""
    inv = db.get(Invoice, invoice_id) or _404()
    try:
        if inv.status != CERTIFIED:
            service.refresh_from_odoo(db, inv, odoo)
        return service.certify_invoice(db, inv, sfec, odoo).to_dict()
    except SfecAuthError as e:
        raise HTTPException(502, str(e))
    except LookupError as e:
        raise HTTPException(404, str(e))


def _404():
    raise HTTPException(404, "Facture introuvable")
