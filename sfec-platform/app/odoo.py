"""Client de l'API externe d'Odoo (XML-RPC), compatible Odoo Online.

Odoo Online n'accepte pas de module personnalisé : on lit les factures clients
validées et on écrit le résultat de la certification dans le chatter de la facture
(aucun champ personnalisé requis).
"""
import xmlrpc.client
from typing import Protocol

from .config import settings


class OdooGateway(Protocol):
    def fetch_posted_invoices(self, limit: int, exclude_ids: list[int]) -> list[dict]: ...
    def post_certification(self, odoo_id: int, body: str) -> None: ...


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

    def fetch_posted_invoices(self, limit: int, exclude_ids: list[int]) -> list[dict]:
        domain = [("move_type", "=", "out_invoice"), ("state", "=", "posted")]
        if exclude_ids:
            domain.append(("id", "not in", exclude_ids))
        moves = self._call("account.move", "search_read", [domain], {
            "fields": ["name", "partner_id", "invoice_date", "currency_id", "amount_untaxed",
                       "amount_tax", "amount_total", "invoice_line_ids"],
            "limit": limit, "order": "id asc",
        })
        partner_ids = {m["partner_id"][0] for m in moves if m["partner_id"]}
        partners = {}
        if partner_ids:
            for p in self._call("res.partner", "read", [list(partner_ids)], {"fields": ["vat", "name"]}):
                partners[p["id"]] = p
        line_ids = [i for m in moves for i in m["invoice_line_ids"]]
        lines_by_id = {}
        if line_ids:
            for ln in self._call("account.move.line", "read", [line_ids], {
                "fields": ["name", "quantity", "price_unit", "discount", "price_subtotal",
                           "price_total", "display_type"]}):
                lines_by_id[ln["id"]] = ln
        out = []
        for m in moves:
            p = partners.get(m["partner_id"][0], {}) if m["partner_id"] else {}
            out.append({
                "odoo_id": m["id"], "number": m["name"],
                "partner_name": m["partner_id"][1] if m["partner_id"] else "",
                "partner_tax_id": p.get("vat") or "",
                "invoice_date": m["invoice_date"] or "",
                "currency": m["currency_id"][1] if m["currency_id"] else "",
                "amount_untaxed": m["amount_untaxed"], "amount_tax": m["amount_tax"],
                "amount_total": m["amount_total"],
                "lines": [
                    {"description": l["name"], "quantity": l["quantity"], "unit_price": l["price_unit"],
                     "discount": l["discount"], "subtotal": l["price_subtotal"], "total": l["price_total"]}
                    for i in m["invoice_line_ids"]
                    if (l := lines_by_id.get(i)) and l["display_type"] == "product"
                ],
            })
        return out

    def post_certification(self, odoo_id: int, body: str) -> None:
        self._call("account.move", "message_post", [[odoo_id]], {"body": body, "message_type": "comment"})
