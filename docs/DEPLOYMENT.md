# Deployment : Docker + CI/CD

EduLink est conteneurisé (Docker + Docker Compose) et livré sur un serveur de
production au moyen d'un pipeline GitHub Actions. Le serveur cible est un
**Raspberry Pi (ARM64)** — l'image est construite **sur le serveur**, en
architecture native.

## Workflow global

```
Vous (dev)                  GitHub                     Serveur (Raspberry Pi)
   │                          │                              │
   ├─ git push main ────────► │                              │
   │                          ├─ Actions: job "tests"       │
   │                          │   pytest + docker build ✓   │
   │                          ├─ Actions: job "deploy"      │
   │                          │   SSH (secrets SERVER_*)    │
   │                          ├────────────────────────────►│ cd /opt/edulink
   │                          │                             │ git reset --hard origin/main
   │                          │                             │ docker compose up -d --build
   │                          │                             │ (migrations Alembic auto au boot)
```

**Un changement de code accepté = un `git push` sur `main` = mise en ligne.**
Le déploiement ne se déclenche qu'après le job `tests` **vert**. Le bouton
« Run workflow » de l'onglet Actions permet un déploiement manuel de secours.

## Sécurité : deux paires de clés SSH

| Rôle | Clé privée (où) | Clé publique (où) |
|---|---|---|
| **CI → serveur** | secret GitHub `SERVER_SSH_KEY` | `~deploy/.ssh/authorized_keys` du serveur |
| **serveur → GitHub** (git pull du repo privé) | `/root/.ssh/id_deploy` (ou `~deploy`) | Deploy key du repo (lecture seule) |

`.env`, mots de passe, VAPID… **ne transitent jamais par GitHub** : ils vivent
uniquement dans `/opt/edulink/.env` sur le serveur, injectés par compose.
GitHub ne voit que la clé d'accès SSH.

## Préparation unique (une fois par serveur)

1. **Générer le profil Deploy (serveur → GitHub)**, sur le serveur :
   ```bash
   sudo bash scripts/server_setup.sh   # installe Docker, crée l'utilisateur deploy,
                                       # clone le repo, copie .env.production.example
   ```
   Si `id_deploy` n'existe pas, le générer d'abord sur le serveur :
   ```bash
   ssh-keygen -t ed25519 -f ~/.ssh/id_deploy -N ""
   ```
   Puis sur GitHub : **Settings → Deploy keys → Add deploy key**, coller
   `cat ~/.ssh/id_deploy.pub` (cocher « Allow write access » **désactivé**).

2. **Remplir le fichier d'environnement** :
   ```bash
   sudo nano /opt/edulink/.env
   ```
   Valeurs obligatoires : `POSTGRES_PASSWORD` (compose refuse de démarrer sans),
   `EDULINK_ADMIN_PASSWORD`. Recommandées : `SECRET_KEY`, `VAPID_PUBLIC_KEY`,
   `VAPID_PRIVATE_KEY` (`npx web-push generate-vapid-keys --json`, une fois).

3. **Générer le profil CI (CI → serveur)**, sur votre machine :
   ```bash
   ssh-keygen -t ed25519 -f ~/.ssh/edulink_ci -N ""    # clé privée       → secret
   ssh-copy-id -i ~/.ssh/edulink_ci.pub deploy@<ip-serveur>   # publique → serveur
   ```

4. **Ajouter les secrets du repo GitHub**
   (Settings → Secrets and variables → Actions → New repository secret) :
   | Secret | Valeur |
   |---|---|
   | `SERVER_HOST` | IP / DNS du Raspberry Pi |
   | `SERVER_USER` | `deploy` |
   | `SERVER_SSH_KEY` | contenu de `~/.ssh/edulink_ci` (clé privée) |
   | `SERVER_PORT` | ex. `22` (ou défaut SSH si différent) |

5. **Vérifier la branche** : le workflow ne doit laisser, par défaut, que le
   push sur `main`. Les merges passent par Pull Request (le job `tests`
   s'exécute dessus ; le `deploy`, jamais).

## Déploiement au quotidien

| Action | Commande |
|---|---|
| **Update de l'app après un push** | `git push` — GitHub Actions déploie automatiquement (build sur le Pi, migrations auto) |
| Déploiement manuel (secours) | `./scripts/deploy.sh` sur le serveur |
| Changement de config (.env) | éditer `/opt/edulink/.env` puis `docker compose up -d` |
| Logs de l'app | `docker compose logs -f web` |
| État de la pile | `docker compose ps` |
| Redémarrer après le boot du Pi | `docker compose up -d` (les volumes persistent) |
| Rollback | `git revert <sha>` + push **ou** sur le serveur `git reset --hard <sha> && docker compose up -d --build` |
| Test de la santé | `curl http://localhost:5050/health` → `{"status":"ok"}` |

### Détails à connaître

- **Base de données** : PostgreSQL 16 tourne dans le service `db` ; les données
  vivent dans le volume `pg_data`. `create_app()` exécute `alembic upgrade head`
  au démarrage du conteneur web, donc les migrations sont appliquées
  automatiquement à chaque déploiement. **Sauvegardez** `pg_data` :
  `docker compose exec db pg_dump -U edulink edulink > backup.sql`.
- **Volumes persistants** : `pg_data` (PostgreSQL), `edulink_instance`
  (`instance/` — contient le `secret_key` auto-généré si `SECRET_KEY` vide),
  `edulink_uploads` (`uploads/` — PDF des annonces).
- **HTTPS obligatoire en production** : `ProductionConfig` force
  `SESSION_COOKIE_SECURE=True` ; sans serveur TLS en façade (Caddy, Traefik,
  Nginx, ou le tunnel `scripts/start_tunnel.sh`), la connexion échouera.
- **SocketIO** : l'app tourne en `async_mode='threading'` ; gunicorn utilise un
  worker `gthread` unique (le limiter est en mémoire `memory://`, d'où
  l'unicité). Côté client, socket.io retombe automatiquement sur
  long-polling si le WebSocket n'est pas disponible.
- **Ollama** : un service externe (par ex. `http://192.168.1.28:11434`) ;
  l'app dégrade proprement (`ServiceUnavailableError`) s'il est injoignable.

## Côté CI (GitHub Actions)

`.github/workflows/ci.yml` :

- **`tests`** (sur chaque push/PR vers `main`) : `pytest` (SQLite mémoire),
  build de validation de l'image, `docker compose config`.
- **`deploy`** (push sur `main` uniquement) : SSH vers le serveur via
  `appleboy/ssh-action`, exécute `git reset --hard origin/main` +
  `docker compose up -d --build`, puis email le SHA déployé dans les logs.

Le développeur n'a **aucun geste** à faire entre le push et la mise en ligne.

## Ajouter un second serveur

Recommencer « Préparation unique » puis, pour basculer la cible, changer les
secrets `SERVER_*` (ou dupliquer un job `deploy` vers une autre paire de
secrets). Pour des environnements staging+prod distincts, voir le modèle des
environnements protégés de GitHub (deploy environments).