"""Client de l'API externe d'Odoo (XML-RPC), compatible Odoo Online.

Odoo Online n'accepte pas de module personnalisé : on lit les factures et avoirs clients
validés, et on dépose le résultat de la certification (message + QR code en pièce jointe)
dans le chatter de la facture. Aucun champ personnalisé n'est requis.
"""
import xmlrpc.client
from typing import Protocol

from .config import settings


class OdooGateway(Protocol):
    def fetch_new(self, limit: int, exclude_ids: list[int], from_date: str) -> list[dict]: ...
    def fetch_by_ids(self, ids: list[int]) -> list[dict]: ...
    def post_certification(self, odoo_id: int, body: str, qr_png_b64: str, filename: str) -> None: ...


MOVE_FIELDS = ["name", "move_type", "partner_id", "partner_shipping_id", "invoice_date",
               "invoice_date_due", "currency_id", "amount_total", "invoice_line_ids",
               "reversed_entry_id", "ref", "invoice_origin"]
PARTNER_FIELDS = ["name", "vat", "is_company", "phone", "email", "street", "street2", "zip",
                  "city", "country_id", "country_code", "category_id", "company_registry"]
LINE_FIELDS = ["name", "quantity", "price_unit", "price_subtotal", "price_total", "display_type",
               "tax_ids", "product_id"]


def _address(p: dict) -> str:
    city = " ".join(filter(None, [p.get("zip"), p.get("city")]))
    country = p["country_id"][1] if p.get("country_id") else ""
    return ", ".join(filter(None, [p.get("street"), p.get("street2"), city, country]))


class OdooClient:
    def __init__(self) -> None:
        self.url = settings.odoo_url.rstrip("/")
        self.db, self.login, self.key = settings.odoo_db, settings.odoo_login, settings.odoo_api_key
        self._uid: int | None = None

    def _call(self, model: str, method: str, args: list, kwargs: dict | None = None):
        if self._uid is None:
            common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")
            self._uid = common.authenticate(self.db, self.login, self.key, {})
            if not self._uid:
                raise PermissionError("Authentification Odoo refusée (vérifiez login / clé API / base).")
        obj = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object", allow_none=True)
        return obj.execute_kw(self.db, self._uid, self.key, model, method, args, kwargs or {})

    def _read(self, model: str, ids, fields: list[str]) -> dict[int, dict]:
        ids = list(set(ids))
        return {r["id"]: r for r in self._call(model, "read", [ids], {"fields": fields})} if ids else {}

    def fetch_new(self, limit: int, exclude_ids: list[int], from_date: str) -> list[dict]:
        domain = [("move_type", "in", ["out_invoice", "out_refund"]), ("state", "=", "posted")]
        if from_date:
            domain.append(("invoice_date", ">=", from_date))
        if exclude_ids:
            domain.append(("id", "not in", exclude_ids))
        moves = self._call("account.move", "search_read", [domain],
                           {"fields": MOVE_FIELDS, "limit": limit, "order": "id asc"})
        return self._bundles(moves)

    def fetch_by_ids(self, ids: list[int]) -> list[dict]:
        return self._bundles(list(self._read("account.move", ids, MOVE_FIELDS).values()))

    def _bundles(self, moves: list[dict]) -> list[dict]:
        if not moves:
            return []
        m2o = lambda m, f: m[f][0] if m.get(f) else None  # noqa: E731
        partners = self._read("res.partner", {m2o(m, f) for m in moves for f in
                                              ("partner_id", "partner_shipping_id") if m2o(m, f)}, PARTNER_FIELDS)
        tags = self._read("res.partner.category", {t for p in partners.values() for t in p["category_id"]}, ["name"])
        currencies = self._read("res.currency", {m2o(m, "currency_id") for m in moves}, ["name", "decimal_places"])
        lines = self._read("account.move.line", [i for m in moves for i in m["invoice_line_ids"]], LINE_FIELDS)
        taxes = self._read("account.tax", {t for l in lines.values() for t in l["tax_ids"]},
                           ["name", "amount", "amount_type"])
        products = self._read("product.product", {m2o(l, "product_id") for l in lines.values() if l["product_id"]},
                              ["type"])

        out = []
        for m in moves:
            p = partners.get(m2o(m, "partner_id"), {})
            ship = partners.get(m2o(m, "partner_shipping_id"))
            cur = currencies[m2o(m, "currency_id")]
            out.append({
                "odoo_id": m["id"], "number": m["name"], "move_type": m["move_type"],
                "invoice_date": m["invoice_date"] or "", "invoice_date_due": m["invoice_date_due"] or None,
                "currency": cur["name"], "decimals": cur["decimal_places"],
                "amount_total": m["amount_total"], "ref": m["ref"] or None,
                "invoice_origin": m["invoice_origin"] or None,
                "reversed_entry": m["reversed_entry_id"][1].split(" ")[0] if m["reversed_entry_id"] else None,
                "partner": {
                    "name": p.get("name") or "", "vat": p.get("vat") or None,
                    "is_company": p.get("is_company", False), "phone": p.get("phone") or None,
                    "email": p.get("email") or None, "address": _address(p) if p else None,
                    "country_code": p.get("country_code") or None,
                    "company_registry": p.get("company_registry") or None,
                    "tags": [tags[t]["name"] for t in p.get("category_id", []) if t in tags],
                },
                "delivery_address": _address(ship) if ship and ship["id"] != p.get("id") else None,
                "lines": [
                    {"description": l["name"] or "", "quantity": l["quantity"], "price_unit": l["price_unit"],
                     "subtotal": l["price_subtotal"], "total": l["price_total"],
                     "product_type": products[l["product_id"][0]]["type"] if l["product_id"] else None,
                     "taxes": [taxes[t] for t in l["tax_ids"]]}
                    for i in m["invoice_line_ids"]
                    if (l := lines.get(i)) and l["display_type"] == "product"
                ],
            })
        return out

    def post_certification(self, odoo_id: int, body: str, qr_png_b64: str, filename: str) -> None:
        attachment_ids = []
        if qr_png_b64:
            attachment_ids.append(self._call("ir.attachment", "create", [{
                "name": filename, "type": "binary", "datas": qr_png_b64, "mimetype": "image/png",
                "res_model": "account.move", "res_id": odoo_id}]))
        self._call("account.move", "message_post", [[odoo_id]],
                   {"body": body, "message_type": "comment", "attachment_ids": attachment_ids})
