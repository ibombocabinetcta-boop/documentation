"""Conversion d'une facture Odoo en corps de requête SFEC (POST /api/v1/invoices).

Référence : https://docs.sfec.gouv.cg/api/certify
"""
from .config import settings

VAT_RATES = (0, 5, 18)


class MappingError(Exception):
    """La facture Odoo ne peut pas être convertie : à corriger dans Odoo avant envoi."""


def _iso(date: str | None) -> str | None:
    return f"{date}T00:00:00Z" if date else None


def recipient_type(partner: dict) -> str:
    if partner.get("country_code") and partner["country_code"] != "CG":
        return "foreign"
    tag = settings.sfec_government_tag.lower()
    if tag and tag in (t.lower() for t in partner.get("tags", [])):
        return "government"
    return "business" if partner.get("is_company") else "individual"


def _invoice_type(bundle: dict) -> tuple[str, str | None]:
    if bundle["move_type"] == "out_invoice":
        return "salesInvoice", None
    if bundle.get("reversed_entry"):
        return "creditNote", bundle["reversed_entry"]
    return "creditNoteOnAccount", bundle.get("ref") or bundle["number"]


def _is_cent_tax(tax: dict) -> bool:
    kw = settings.sfec_cent_tax_keyword.lower()
    return bool(kw) and kw in tax["name"].lower()


def _item(line: dict, d: int) -> tuple[dict, int, float]:
    """Retourne (article SFEC, taux de TVA, centimes additionnels de la ligne)."""
    vat = [t for t in line["taxes"] if not _is_cent_tax(t)]
    cent = [t for t in line["taxes"] if _is_cent_tax(t)]
    if len(vat) > 1 or any(t["amount_type"] != "percent" for t in vat):
        raise MappingError(f"Ligne « {line['description']} » : une seule TVA en pourcentage est acceptée.")
    rate = vat[0]["amount"] if vat else 0
    if rate not in VAT_RATES:
        raise MappingError(f"Ligne « {line['description']} » : taux de TVA {rate} % non reconnu par le SFEC (0, 5 ou 18).")

    subtotal = round(line["subtotal"], d)
    if cent:
        tax = round(subtotal * rate / 100, d)
        cent_amount = round(line["total"] - subtotal - tax, d)
    else:
        tax, cent_amount = round(line["total"] - subtotal, d), 0.0
    discount = max(round(line["quantity"] * line["price_unit"] - subtotal, d), 0.0)
    item = {
        "designation": line["description"].strip()[:255] or "Article",
        "type": "service" if line["product_type"] in ("service", None) else "product",
        "unit_price": line["price_unit"],
        "quantity": line["quantity"],
        "subtotal": subtotal,
        "discount_amount": discount,
        "amount_after_discount": subtotal,
        "tax_rate": str(int(rate)),
        "tax_amount": tax,
        "net_amount": round(subtotal + tax, d),
        "total_amount": round(subtotal + tax, d),
    }
    return item, int(rate), cent_amount


def build_payload(bundle: dict) -> dict:
    d = bundle["decimals"]
    if not bundle["lines"]:
        raise MappingError("Facture sans ligne d'article.")

    items, sub, vat_t, vat_r, exempt, cent, line_disc = [], 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
    for line in bundle["lines"]:
        item, rate, c = _item(line, d)
        items.append(item)
        sub += item["subtotal"]
        line_disc += item["discount_amount"]
        cent += c
        if rate == 18:
            vat_t += item["tax_amount"]
        elif rate == 5:
            vat_r += item["tax_amount"]
        else:
            exempt += item["subtotal"]
    total = round(sub + vat_t + vat_r + cent, d)

    if abs(total - bundle["amount_total"]) > 10 ** -d / 2 + 1e-9:
        raise MappingError(
            f"Total recalculé ({total}) différent du total Odoo ({bundle['amount_total']}). "
            "Activez l'arrondi « par ligne » dans Comptabilité > Configuration > Paramètres, "
            "ou vérifiez les taxes de la facture.")

    p = bundle["partner"]
    rtype = recipient_type(p)
    itype, reference = _invoice_type(bundle)
    payload = {
        "invoice_id": bundle["number"],
        "invoice_type": itype,
        "reference_invoice_id": reference,
        "invoice_subject": bundle.get("ref") or bundle.get("invoice_origin") or None,
        "invoice_due_date": _iso(bundle.get("invoice_date_due")),
        "recipient_type": rtype,
        "recipient_name": p.get("name") or None,
        "recipient_niu": p.get("vat") or None,
        "recipient_rccm": p.get("company_registry") or None,
        "recipient_address": p.get("address") or None,
        "recipient_phone": p.get("phone") or None,
        "recipient_email": p.get("email") or None,
        "is_recipient_taxable": rtype in ("business", "government"),
        "delivery_address": (bundle.get("delivery_address") or "")[:255] or None,
        "transaction_location": settings.sfec_transaction_location or None,
        "subtotal": round(sub, d),
        "total_tax_t_amount": round(vat_t, d),
        "total_tax_r_amount": round(vat_r, d),
        "total_exempt_amount": round(exempt, d),
        "total_tax_amount": round(vat_t + vat_r, d),
        "discount_amount": 0,
        "total_line_discount_amount": round(line_disc, d),
        "additional_cent_tax": round(cent, d),
        "electronic_stamp_duty": 0,
        "total_amount": total,
        "amount_due": total,
        "currency": bundle["currency"],
        "items": items,
    }
    if settings.sfec_taxpayer_niu:
        payload["taxpayer_niu"] = settings.sfec_taxpayer_niu
    return payload
