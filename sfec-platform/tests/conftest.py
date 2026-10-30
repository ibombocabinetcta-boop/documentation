import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SFEC_MODE"] = "mock"

import pytest

VAT18 = {"name": "TVA 18%", "amount": 18.0, "amount_type": "percent"}
EXEMPT = {"name": "Exonéré 0%", "amount": 0.0, "amount_type": "percent"}
CENT = {"name": "Centimes additionnels", "amount": 0.9, "amount_type": "percent"}


def line(desc, qty, pu, subtotal, total, taxes, ptype="service"):
    return {"description": desc, "quantity": qty, "price_unit": pu, "subtotal": subtotal,
            "total": total, "product_type": ptype, "taxes": taxes}


def bundle(odoo_id=1, **kw):
    """Facture de prestation exonérée de 1 910 000 XAF (données fictives)."""
    b = {
        "odoo_id": odoo_id, "number": f"INV/2026/{odoo_id:05d}", "move_type": "out_invoice",
        "invoice_date": "2026-10-25", "invoice_date_due": None, "currency": "XAF", "decimals": 0,
        "amount_total": 1910000.0, "ref": None, "invoice_origin": None, "reversed_entry": None,
        "partner": {"name": "Client Test SA", "vat": "M0000000000000001", "is_company": True,
                    "phone": "+242 06 000 00 00", "email": "contact@client-test.cg",
                    "address": "1 avenue Exemple, Pointe-Noire, Congo", "country_code": "CG",
                    "company_registry": None, "tags": []},
        "delivery_address": "Zone industrielle, Pointe-Noire",
        "lines": [line("Prestation de maintenance", 1, 1910000, 1910000, 1910000, [EXEMPT])],
    }
    b.update(kw)
    return b


@pytest.fixture
def db():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from app.db import Base
    eng = create_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(eng)
    with sessionmaker(bind=eng, expire_on_commit=False)() as s:
        yield s
