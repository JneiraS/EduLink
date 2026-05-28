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
- Dashboard adapte au role.

## Lancement

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

Application disponible sur `http://localhost:5000`.

Compte admin seed au premier lancement:

- email: `admin@edulink.local`
- mot de passe: `Admin123!`

Variables optionnelles:

- `EDULINK_ADMIN_EMAIL`
- `EDULINK_ADMIN_PASSWORD`
- `DATABASE_URL`
- `SECRET_KEY`
- `UPLOAD_FOLDER`

## Tests

```bash
pytest
```

## Limites MVP

- Pas encore d'API REST publique
- Pas de multi-ecoles
- RBAC avance, audit logs et CI/CD non inclus
