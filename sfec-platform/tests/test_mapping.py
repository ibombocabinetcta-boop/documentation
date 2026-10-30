import pytest

from app.mapping import MappingError, build_payload
from tests.conftest import CENT, VAT18, bundle, line


def test_exempt_service_invoice():
    p = build_payload(bundle())
    assert p["invoice_type"] == "salesInvoice" and p["invoice_id"] == "INV/2026/00001"
    assert p["recipient_type"] == "business" and p["recipient_niu"] == "M0000000000000001"
    assert p["is_recipient_taxable"] is True
    assert p["subtotal"] == p["total_exempt_amount"] == p["total_amount"] == p["amount_due"] == 1910000
    assert p["total_tax_amount"] == 0 and p["electronic_stamp_duty"] == 0
    assert p["delivery_address"] == "Zone industrielle, Pointe-Noire"
    item = p["items"][0]
    assert item["tax_rate"] == "0" and item["type"] == "service" and item["discount_amount"] == 0


def test_vat18_with_line_discount_matches_doc_example():
    # Exemple de la doc SFEC : 6 x 720, remise 1000 → HT 3320, TVA 597.6
    b = bundle(decimals=2, amount_total=3917.6,
               lines=[line("iPhone 16 Pro", 6, 720, 3320, 3917.6, [VAT18], "consu")])
    p = build_payload(b)
    item = p["items"][0]
    assert item == {**item, "subtotal": 3320, "discount_amount": 1000, "tax_amount": 597.6,
                    "net_amount": 3917.6, "tax_rate": "18", "type": "product"}
    assert p["total_tax_t_amount"] == 597.6 and p["total_line_discount_amount"] == 1000


def test_centimes_additionnels_go_to_additional_cent_tax():
    # HT 585000, TVA 105300, centimes 5% de la TVA = 5265 (exemple de la doc)
    b = bundle(amount_total=695565, lines=[line("Ordinateur", 1, 585000, 585000, 695565, [VAT18, CENT])])
    p = build_payload(b)
    assert p["items"][0]["tax_amount"] == 105300 and p["items"][0]["total_amount"] == 690300
    assert p["additional_cent_tax"] == 5265 and p["total_amount"] == 695565


def test_total_mismatch_is_refused_locally():
    with pytest.raises(MappingError, match="arrondi"):
        build_payload(bundle(amount_total=1910001))


def test_unknown_vat_rate_refused():
    tax = {"name": "TVA 10%", "amount": 10.0, "amount_type": "percent"}
    with pytest.raises(MappingError, match="10"):
        build_payload(bundle(lines=[line("x", 1, 100, 100, 110, [tax])], amount_total=110))


def test_credit_notes():
    p = build_payload(bundle(move_type="out_refund", reversed_entry="INV/2026/00001"))
    assert p["invoice_type"] == "creditNote" and p["reference_invoice_id"] == "INV/2026/00001"
    p = build_payload(bundle(move_type="out_refund", ref="ACOMPTE-17"))
    assert p["invoice_type"] == "creditNoteOnAccount" and p["reference_invoice_id"] == "ACOMPTE-17"


def test_recipient_types():
    b = bundle()
    b["partner"].update(is_company=False, vat=None)
    assert build_payload(b)["recipient_type"] == "individual"
    b["partner"]["country_code"] = "FR"
    assert build_payload(b)["recipient_type"] == "foreign"
    b["partner"].update(country_code="CG", tags=["Administration"])
    assert build_payload(b)["recipient_type"] == "government"
