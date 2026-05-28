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
python -c "from py_vapid import Vapid01,b64urlencode; from cryptography.hazmat.primitives.serialization import Encoding,PublicFormat,PrivateFormat,NoEncryption; v=Vapid01(); v.generate_keys(); print('VAPID_PUBLIC_KEY='+b64urlencode(v.public_key.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint))); print(v.private_key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()).decode())"
```

## Tests

```bash
pytest
```

## Limites MVP

- Pas encore d'API REST publique
- Pas de multi-ecoles
- RBAC avance, audit logs et CI/CD non inclus
