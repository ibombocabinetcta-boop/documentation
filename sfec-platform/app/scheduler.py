"""Synchronisation Odoo -> SFEC, manuelle ou périodique, jamais deux en parallèle."""
import logging
import threading
from datetime import datetime, timezone

from . import service
from .db import SessionLocal

log = logging.getLogger("sfec.sync")
_lock = threading.Lock()
last_run: dict = {}


class SyncBusy(Exception):
    pass


def run_once(odoo_factory, sfec_factory) -> dict:
    if not _lock.acquire(blocking=False):
        raise SyncBusy("Une synchronisation est déjà en cours.")
    try:
        with SessionLocal() as db:
            odoo = odoo_factory()
            imported = service.sync_from_odoo(db, odoo)
            result = {"imported": imported, **service.certify_pending(db, sfec_factory(), odoo)}
        last_run.update(at=datetime.now(timezone.utc), result=result, error="")
        return result
    except Exception as e:
        last_run.update(at=datetime.now(timezone.utc), result=None, error=str(e))
        raise
    finally:
        _lock.release()


def start(interval_minutes: int, odoo_factory, sfec_factory) -> threading.Event:
    stop = threading.Event()

    def loop():
        while not stop.wait(interval_minutes * 60):
            try:
                log.info("Synchronisation automatique : %s", run_once(odoo_factory, sfec_factory))
            except SyncBusy:
                pass
            except Exception:
                log.exception("Synchronisation automatique échouée")

    threading.Thread(target=loop, name="sfec-sync", daemon=True).start()
    return stop
