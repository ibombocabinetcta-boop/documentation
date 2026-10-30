# Plateforme de connexion Odoo Online ⇄ SFEC

Middleware qui certifie automatiquement les factures et avoirs clients d'**Odoo Online** auprès du
**SFEC** (Système de Facturation Électronique Certifié, République du Congo) via l'intégration
officielle « API · ERP en ligne » ([documentation](https://docs.sfec.gouv.cg/api)).

```
Odoo Online --XML-RPC--> [ Plateforme : FastAPI + SQLite ] --POST /api/v1/invoices--> SFEC
     ^                              | tableau de bord web (/)
     +---- chatter : signature + QR code (pièce jointe) ----+
```

## Démarrage
```bash
python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements-dev.txt
cp .env.example .env      # renseigner ODOO_*, SFEC_*, SYNC_FROM_DATE
uvicorn app.main:app --reload
```
Tableau de bord : http://localhost:8000 · Tests : `pytest`

## Mise en service
1. **Clé SFEC** : sur le portail e-Facture, créer une demande d'intégration **API (ERP)** ; après validation par la DGID, renseigner `SFEC_API_KEY`.
2. **Sandbox d'abord** : `SFEC_MODE=sandbox`, puis `production` une fois les factures de test validées. Ne jamais mélanger les environnements.
3. **`SYNC_FROM_DATE`** : date de bascule ; les factures antérieures ne sont jamais envoyées.
4. **Odoo** :
   - Comptabilité > Configuration > Paramètres : arrondi des taxes **par ligne** (sinon les totaux peuvent différer d'1 F et la facture est bloquée avant envoi).
   - NIU des clients dans le champ **N° TVA / NIF** du contact (16 ou 17 caractères pour une société ou une administration).
   - Taux de TVA reconnus : 18 % (normal), 5 % (réduit), 0 % (exonéré). Les centimes additionnels doivent être une taxe dont le nom contient « centime ».
   - Clients publics : étiquette de contact `Administration`. Clients hors Congo : pays renseigné.
5. **Mise en ligne** : voir [DEPLOIEMENT.md](DEPLOIEMENT.md) (Render ou VPS). Synchronisation automatique via `SYNC_INTERVAL_MINUTES`, tableau de bord protégé par `ADMIN_PASSWORD`.

## Correspondance Odoo → SFEC
| Odoo | SFEC |
| --- | --- |
| Facture client (`out_invoice`) | `salesInvoice` |
| Avoir lié à une facture (`reversed_entry_id`) | `creditNote` + `reference_invoice_id` = n° de la facture d'origine |
| Avoir sans facture d'origine | `creditNoteOnAccount` + référence de l'avoir |
| Société / particulier / pays ≠ CG / étiquette Administration | `business` / `individual` / `foreign` / `government` |
| Remise % de ligne | `discount_amount` de l'article, cumul dans `total_line_discount_amount` |
| Produit de type service / autre | `type` = `service` / `product` |

`electronic_stamp_duty` est toujours `0` (décret). Les débours, l'escompte global et les taxes
additionnelles (TAR, etc.) ne sont pas encore gérés : une facture qui en contient est bloquée avec un message explicite.

## Fiabilité
- Import idempotent (clé `odoo_id`) ; avoirs envoyés après leur facture d'origine.
- `409` (numéro déjà certifié, ex. réponse perdue) : la certification existante est relue via `GET /api/v1/invoices/{n°}`.
- `400`/`404`/`409` : facture **rejetée**, message du SFEC affiché ; corriger dans Odoo puis « réessayer » (la facture est relue dans Odoo).
- `429`/`5xx`/réseau : renvoi automatique (jusqu'à `MAX_ATTEMPTS`). `401` : le lot est interrompu, rien n'est marqué en échec.
- Si l'écriture dans Odoo échoue, la certification est conservée et l'écriture est retentée sans recertifier.
