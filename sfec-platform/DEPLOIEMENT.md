# Mettre la plateforme en ligne

Deux options. **Render** est la plus simple (aucune administration de serveur) ; le **VPS** est moins cher et vous laisse le contrôle.

Dans les deux cas, la plateforme doit tourner avec **une seule instance** (la synchronisation automatique est dans le processus) et un **disque persistant** (la base SQLite garde la trace des factures déjà certifiées : la perdre provoquerait des renvois, refusés en `409` puis récupérés, mais à éviter).

## Variables à préparer

| Variable | Valeur |
| --- | --- |
| `ODOO_URL` / `ODOO_DB` / `ODOO_LOGIN` / `ODOO_API_KEY` | Accès API Odoo (plan Custom ; clé dans Préférences > Sécurité du compte) |
| `SFEC_MODE` | `sandbox` pour commencer, puis `production` |
| `SFEC_API_KEY` | Clé reçue après validation de la demande d'intégration API (ERP) sur e-Facture |
| `SYNC_FROM_DATE` | Date de bascule `AAAA-MM-JJ` (rien d'antérieur n'est envoyé) |
| `ADMIN_PASSWORD` | Mot de passe long du tableau de bord (utilisateur : `ADMIN_USER`, `admin` par défaut) |
| `SYNC_INTERVAL_MINUTES` | `5` (0 = synchronisation manuelle uniquement) |
| Facultatif | `SFEC_TRANSACTION_LOCATION`, `SFEC_TAXPAYER_NIU`, `PLATFORM_API_KEY` |

Ne mettez jamais ces valeurs dans le dépôt Git : uniquement dans l'interface de l'hébergeur ou dans le fichier `.env` du serveur.

## Option A — Render (≈ 7 $/mois + disque)

1. Créez un compte sur https://render.com et connectez votre compte GitHub.
2. **New > Web Service**, choisissez le dépôt, puis :
   - **Language / Runtime** : Docker
   - **Root Directory** : `sfec-platform`
   - **Instance type** : Starter (le plan gratuit s'endort et n'a pas de disque)
   - **Health Check Path** : `/health`
3. **Advanced > Add Disk** : Mount Path `/data`, taille 1 Go.
4. **Environment** : ajoutez les variables du tableau ci-dessus.
5. **Create Web Service**. Render construit l'image et fournit une adresse `https://sfec-platform-xxxx.onrender.com` (HTTPS inclus). Un domaine personnalisé peut être ajouté dans **Settings > Custom Domains**.
6. Ouvrez l'adresse, connectez-vous avec `admin` / `ADMIN_PASSWORD`.

Mise à jour : chaque `git push` sur la branche suivie redéploie automatiquement.

## Option B — VPS avec Docker (≈ 5 €/mois)

Serveur Ubuntu (OVH, Hetzner, DigitalOcean…) avec un nom de domaine, par exemple `sfec.votre-entreprise.com`, dont l'enregistrement DNS **A** pointe vers l'IP du serveur.

```bash
# Sur le serveur
curl -fsSL https://get.docker.com | sh
git clone https://github.com/<votre-compte>/<depot>.git && cd <depot>/sfec-platform
cp .env.example .env && nano .env      # renseigner les variables + DOMAIN=sfec.votre-entreprise.com
docker compose up -d --build
```

Caddy obtient et renouvelle automatiquement le certificat HTTPS. Ouvrez `https://sfec.votre-entreprise.com`.

- Mise à jour : `git pull && docker compose up -d --build`
- Journaux : `docker compose logs -f app`
- Sauvegarde quotidienne de la base (crontab -e) :
  ```
  0 2 * * * docker compose -f /chemin/sfec-platform/docker-compose.yml exec -T app sh -c 'cp /data/sfec.db /data/sfec-$(date +\%F).db'
  ```

## Vérifications après mise en ligne

1. `https://…/health` répond `{"ok": true, "sfec_mode": "sandbox"}`.
2. Le tableau de bord demande le mot de passe.
3. Validez une facture de test dans Odoo, cliquez **Synchroniser maintenant** : elle passe en « Certifiée » et le chatter Odoo reçoit la signature et le QR code.
4. Contrôlez les montants certifiés sur le portail e-Facture sandbox.
5. Passez `SFEC_MODE=production`, mettez `SYNC_FROM_DATE` à la date de bascule, redémarrez.
