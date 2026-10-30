# Plateforme de connexion Odoo Online ⇄ SFEC

Middleware qui récupère les factures clients validées d'Odoo Online (API externe),
les envoie au SFEC pour certification, puis écrit l'UID / QR de certification dans le chatter de la facture.

```
Odoo Online --XML-RPC--> [ Plateforme : SQLite + FastAPI ] --HTTPS--> SFEC
                                   ^ tableau de bord web (/)
```

## Démarrage
```bash
python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
cp .env.example .env      # renseigner ODOO_* (clé API : Préférences > Sécurité du compte)
uvicorn app.main:app --reload
```
Tableau de bord : http://localhost:8000 · Tests : `pytest`

## Statut du connecteur SFEC
`SFEC_MODE=mock` (défaut) utilise un simulateur. Pour la production, adapter **uniquement**
`app/sfec/http.py` (endpoint, authentification, format du corps, champs de réponse) et
`build_payload` dans `app/service.py` avec la documentation officielle, puis `SFEC_MODE=http`.

## Notes
- Odoo Online : l'accès API externe exige un plan Custom ; aucun module personnalisé n'est nécessaire.
- Synchronisation idempotente (clé `odoo_id`) ; erreurs transitoires réessayées (`MAX_ATTEMPTS`), rejets visibles dans le tableau de bord.
- Automatisation : appeler `POST /api/sync` périodiquement (cron). Définir `PLATFORM_API_KEY` avant toute exposition publique et utiliser HTTPS.
