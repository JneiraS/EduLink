# EduLink MVP

Plateforme de communication scolaire avec architecture hexagonale (Ports & Adapters), construite avec Flask.

## Stack

- Python 3.12+
- Flask, Flask-Login, Flask-SocketIO, Flask-WTF
- SQLAlchemy (Flask-SQLAlchemy)
- SQLite
- Bootstrap 5

## Architecture

```txt
app/
  domain/
    entities/
    ports/
    errors.py
  application/
    use_cases/
    container.py
  infrastructure/
    database/
    repositories/
    auth/
    notifications/
  interfaces/
    web/
      routes/
      templates/
      static/
  config/
```

- `domain` contient les entites et ports, sans dependance Flask/SQLAlchemy.
- `application` contient les cas d'usage purs.
- `infrastructure` implemente les adapters techniques.
- `interfaces` expose les routes web et templates.

## Fonctionnalites MVP

- Authentification: connexion/deconnexion + creation des comptes par admin.
- Gestion des roles: `PARENT`, `TEACHER`, `ADMIN`.
- Annonces: creation et consultation + upload PDF.
- Messagerie: canaux (classe/groupe), messages en canal.
- Notifications: stockage en base + emission temps reel SocketIO.
- Notifications push mobile via PWA (Web Push) si cles VAPID configurees.
- Dashboard adapte au role.

## Lancement

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

Application disponible sur `http://127.0.0.1:5050`.

Compte admin seed au premier lancement:

- email: `admin@edulink.local`
- mot de passe: celui de `EDULINK_ADMIN_PASSWORD` (ou genere automatiquement en console)

Variables optionnelles:

- `EDULINK_ADMIN_EMAIL`
- `EDULINK_ADMIN_PASSWORD`
- `DATABASE_URL`
- `SECRET_KEY`
- `UPLOAD_FOLDER`
- `EDULINK_HOST`
- `EDULINK_PORT`
- `EDULINK_DEBUG`
- `VAPID_PUBLIC_KEY`
- `VAPID_PRIVATE_KEY`
- `VAPID_SUBJECT`

## Push Mobile (PWA)

1. Configurer les cles VAPID dans `.env`.
2. Lancer l'application et se connecter.
3. Cliquer sur `Activer push mobile` dans la barre du haut.
4. Accepter la permission navigateur.

Exemple de generation locale des cles (Python):

```bash
python - <<'PY'
from py_vapid import Vapid01, b64urlencode
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

v = Vapid01()
v.generate_keys()

public_key = b64urlencode(
  v.public_key.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
)
private_key = b64urlencode(
  v.private_key.private_numbers().private_value.to_bytes(32, "big")
)

print(f"VAPID_PUBLIC_KEY={public_key}")
print(f"VAPID_PRIVATE_KEY={private_key}")
PY
```

### Tunnel HTTPS (test mobile Android)

Le push web mobile exige HTTPS (une IP LAN en HTTP ne suffit pas).

1. Lancer l'application:

```bash
python run.py
```

2. Dans un autre terminal, lancer le tunnel:

```bash
bash scripts/start_tunnel.sh
```

3. Ouvrir sur le mobile l'URL `https://...` affichee dans le terminal du tunnel.

Le script utilise automatiquement, dans cet ordre:

- `cloudflared`
- `ngrok`
- `npx localtunnel`

## Tests

```bash
pytest
```

## Limites MVP

- Pas encore d'API REST publique
- Pas de multi-ecoles
- RBAC avance, audit logs et CI/CD non inclus
