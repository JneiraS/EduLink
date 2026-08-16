# EduLink — Architecture & guide de compréhension

Ce document est le point d'entrée d'un nouveau développeur. Il décrit comment le
projet est structuré, pourquoi, et comment les pièces s'assemblent. Pour la
procédure détaillée d'ajout d'une fonctionnalité, voir
[`docs/ADDING_A_FEATURE.md`](ADDING_A_FEATURE.md).

---

## 1. Vue d'ensemble

EduLink est une plateforme **MVP de communication scolaire** : annonces,
messagerie par canaux (classes/groupes), notifications temps réel et push web
mobile. L'application est **mono-dépôt**, **mono-app Flask**, sans API REST
publique pour l'instant.

### Stack

- Python 3.12+, Flask (server + templates Jinja2)
- Flask-Login (sessions/auth), Flask-WTF (CSRF), Flask-Limiter (rate-limit)
- Flask-SQLAlchemy + SQLite, Alembic (migrations)
- Flask-SocketIO (`async_mode="threading"`) pour le temps réel
- Web Push (pywebpush + VAPID) pour la PWA
- Bootstrap 5 (CDN) + CSS custom dans `app/interfaces/web/static/`

### Fonctionnalités et mapping (route → use case → repository)

| Fonctionnalité | Blueprint (`interfaces/web/routes/`) | Use case (`application/use_cases/`) | Adapter principal (`infrastructure/`) |
|---|---|---|---|
| Login / logout / création de comptes | `auth_routes.py` | `LoginUser`, `RegisterUser` | `user_repository.py`, `auth/password_hasher.py` |
| Dashboard adapté au rôle | `dashboard_routes.py` | `GetDashboard` | `announcement_repository.py`, `notification_repository.py` |
| Annonces (liste, création, PDF) | `announcements_routes.py` | `CreateAnnouncement`, `ListAnnouncements` | `announcement_repository.py` |
| Canaux de messagerie (liste/création) | `messages_routes.py` | `CreateChannel`, `AddChannelMembers`, `ListUserChannels` | `channel_repository.py` |
| Messages en canal (chat + pagination) | `messages_routes.py` | `SendMessage`, `ListChannelMessages`, `ListChannelMembers` | `message_repository.py`, `channel_repository.py` |
| Notifications (liste / lecture) | `notifications_routes.py` | `ListNotifications`, `MarkNotificationRead` | `notification_repository.py` |
| Push web (abonnement PWA) | `push_routes.py` | `SubscribePushNotifications`, `UnsubscribePushNotifications` | `push_subscription_repository.py` |
| **Administration** (rôles, activ./désactiv., suppression) | `admin_routes.py` | `ListUsersForAdmin`, `UpdateUserRole`, `ToggleUserActive`, `ListAnnouncementsForAdmin`, `DeleteAnnouncement`, `ListChannelsForAdmin`, `DeleteChannel` | `user_repository.py`, `announcement_repository.py`, `channel_repository.py` |
| Requêtes utilitaires (lecture) | routes diverses | `ListAllUsers`, `FindUsersByIds` | `user_repository.py` |

Le temps réel n'apparaît pas dans un blueprint : `SocketIONotificationService`
(`infrastructure/notifications/socketio_service.py`) implémente
`RealtimeNotificationPort` et est appelé **par les use cases** (`SendMessage`,
`CreateAnnouncement`).

---

## 2. Architecture hexagonale (Ports & Adapters)

Le principe central : **les dépendances pointent vers l'intérieur**.

```txt
interfaces  →  application  →  domain
```

- **`domain`** (cœur) : ne connaît ni Flask, ni SQLAlchemy. Contient les règles
  métier pures.
- **`application`** : use cases purs (orchestration). Dépend uniquement du
  `domain` (ports abstraits).
- **`infrastructure`** : adaptateurs techniques (SQLAlchemy, SocketIO, Web Push,
  hash de mots de passe). Implémente les ports du `domain`.
- **`interfaces`** : adaptateurs d'entrée (routes web, templates). Appelle
  l'`application`, jamais l'infrastructure directement.

Règle pratique : si un module importe Flask/SQLAlchemy dans `app/domain`, c'est
une violation d'architecture.

### 2.1 `app/domain/` — le cœur métier

- **`entities/`** — entités **dataclass** (`slots=True`), `id: int | None` :
  `User`, `Channel`, `Message`, `Announcement`, `Notification`,
  `PushSubscription`. Exemple : `app/domain/entities/user.py`.
  - `UserRole` (enum) : `PARENT` / `TEACHER` / `ADMIN`.
  - « Peut gérer les membres d'un canal » = `ADMIN` ou `TEACHER`.
- **`ports/`** — contrats **abstraits** (ABC) :
  - `repositories.py` : `UserRepositoryPort`, `AnnouncementRepositoryPort`,
    `MessageRepositoryPort`, `NotificationRepositoryPort`,
    `ChannelRepositoryPort`, `PushSubscriptionRepositoryPort`.
  - `services.py` : `PasswordHasherPort`, `RealtimeNotificationPort`.
- **`errors.py`** — hiérarchie d'erreurs métier :
  `DomainError` → `AuthenticationError`, `AuthorizationError`, `NotFoundError`,
  `ValidationError`. **Le business logic lève ces erreurs**, jamais
  `flask.abort`.

### 2.2 `app/application/` — les use cases

- Chaque use case est un **dataclass** (`slots=True`) dont les dépendances sont
  les **ports** (injection de dépendance) et expose `execute(...)`.
  Exemple de référence : `app/application/use_cases/message_use_cases.py`
  (`SendMessage` injecte `MessageRepositoryPort`, `ChannelRepositoryPort`,
  `NotificationRepositoryPort`, `RealtimeNotificationPort`).
- Un use case fait : **validation métier** (limites de longueur, droits, état)
  → lève `DomainError` → appelle les ports → **retourne une entité domaine**.
- `container.py` : `UseCaseContainer` (dataclass) déclare tous les use cases
  disponibles — c'est le **contrat** exposé aux routes.
- Aucune importation d'infrastructure ni de Flask ici (sauf `container.py` qui
  importe les classes de use cases, pas les adapters).

### 2.3 `app/infrastructure/` — les adaptateurs

- **`database/models.py`** : modèles SQLAlchemy (`UserModel`,
  `AnnouncementModel`, `ChannelModel`, `MessageModel`, `NotificationModel`,
  `PushSubscriptionModel`, table d'association `channel_members`).
- **`repositories/`** : implémentations SQLAlchemy des ports. Chaque repo a une
  méthode privée **`_to_entity(model) -> Entity`** : c'est le **seul endroit**
  où se fait le mapping ORM → domaine. Un repo expose parfois une méthode
  concrète hors port (ex. `UserRepository.get_auth_model(id)` pour la
  passation Flask-Login — délibérément absent des ports).
- **`auth/password_hasher.py`** : `WerkzeugPasswordHasher` (port
  `PasswordHasherPort`).
- **`notifications/socketio_service.py`** : `SocketIONotificationService`
  (port `RealtimeNotificationPort`). Émet via SocketIO + déclenche le web push
  dans un `ThreadPoolExecutor` (en arrière-plan).

### 2.4 `app/interfaces/web/` — l'entrée HTTP

- **`routes/`** : blueprints Flask (`auth_bp`, `dashboard_bp`, `admin_bp`,
  `announcements_bp`, `messages_bp`, `notifications_bp`, `push_bp`).
- **`routes/utils.py`** : les **seuls** accès autorisés aux dépendances :
  - `get_use_cases()` → `app.extensions["use_cases"]`
  - `get_services()` → `app.extensions["services"]` (uniquement pour la
    passation Flask-Login `get_auth_model(id)`)
  - `current_actor()` → `User` domaine via `users.find_by_id(...)`
- **`routes/presentation.py`** : helpers de mise en forme (résolution des noms
  d'expéditeurs, construction de la vue des messages, parse des membres).
- **`socket_events.py`** : enregistre les handlers SocketIO (rejoindre les
  rooms `user_<id>` et `channel_<id>`).
- **`templates/`** : Jinja2. **`static/`** : CSS/JS custom, manifest PWA.

---

## 3. Cycle de vie d'une requête

```txt
Requête HTTP
   │
   ▼
Blueprint + @login_required            (routes/*.py)
   │
   ├── current_actor()                  → users_repo.find_by_id()  → User (domaine)
   └── get_use_cases().<uc>.execute(actor, ...)
            │
            ▼
   Use case (application)               → valide, lève DomainError
            │  appelle des ports (abstraits, domaine)
            ▼
   Adapter repo (infrastructure)        → db.session → modèle ORM
            │  _to_entity()
            ▼
   Entité domaine retournée vers la route
            │
            ▼
   render_template(...)                 → template + statiques (CSS/JS)
```

Cas particulier : un use case qui écrit (`SendMessage`, `CreateAnnouncement`)
appelle aussi `RealtimeNotificationPort` (socket + push), sans que la route n'en
ait connaissance.

---

## 4. Le câblage (composition root)

Tout est assemblé dans **`app/__init__.py` → `create_app()`** :

1. Configuration : `TestingConfig` si `testing=True`, sinon
   `DevelopmentConfig` (depuis `app/config/settings.py`).
2. `_resolve_secret_key(app)` : `SECRET_KEY` = env var, sinon clé aléatoire
   persistée dans `instance/secret_key` (0600, gitignoré). Le défaut public
   `dev-secret-change-me` n'est **jamais** utilisé.
3. Initialisation des extensions : `db`, `csrf`, `login_manager`, `socketio`,
   `limiter` (`app/extensions.py`).
4. Enregistrement des blueprints.
5. Schéma : `db.create_all()` si test, sinon `alembic upgrade head`
   automatiquement au boot. Puis `_seed_initial_admin()`.
6. Instanciation des **adapters** (repos + hasher + `SocketIONotificationService`),
   stockés sur `app.extensions["services"]`.
7. Instanciation du `UseCaseContainer` avec chaque use case branché sur ses
   adapters, stocké sur `app.extensions["use_cases"]`.
8. `register_socket_handlers(socketio)`.
9. En-têtes de sécurité (`after_request`) : CSP, `X-Frame-Options`,
   `nosniff`, `Referrer-Policy`, HSTS si HTTPS. **Aucun script inline** : le
   script de thème vit dans `static/js/app.js`.
10. Errorhandler global `DomainError` : flash + redirect dashboard (filet de
    sécurité).

Point d'entrée : `run.py` → `create_app()` + `socketio.run(...)` (host/port via
`EDULINK_HOST`/`EDULINK_PORT`, défaut `0.0.0.0:5050`).

---

## 5. Conventions clés (à respecter)

### Erreurs métier

- Lève des `DomainError` (`AuthorizationError`, `NotFoundError`,
  `ValidationError`, `AuthenticationError`) **dans le use case**.
- Les routes attrapent ces exceptions et font `flash(str(exc), "danger")`.
- Ne pas lever `flask.abort` pour de la logique métier.
- Limites de longueur → `ValidationError` **dans le use case**, jamais dans la
  route. Limites actuelles : `full_name` ≤120, email ≤254, password 8–128,
  titre d'annonce ≤255, contenu d'annonce ≤5000, nom de canal ≤120, contenu de
  message ≤5000.

### Sécurité

- CSRF activé en dev, désactivé en test (`TestingConfig.WTF_CSRF_ENABLED =
  False`).
- Login POST rate-limité (5/15 min/IP) via Flask-Limiter en dev
  (`RATE_LIMIT_ENABLED`).
- CSP `script-src 'self'` + CDNs (pas de `'unsafe-inline'` pour scripts) → tout
  JS custom doit vivre dans `static/js/app.js`.
- Uploads : dossier `UPLOAD_FOLDER` (défaut `uploads/`), **uniquement PDF**
  (`ALLOWED_EXTENSIONS = {"pdf"}`), **max 5 MB** (`MAX_CONTENT_LENGTH`), plus
  vérification des octets magiques `%PDF` avant sauvegarde.
- Push : `endpoint` dans une allowlist (HTTPS + hôtes FCM/Mozilla/Apple) et clés
  `p256dh`/`auth` en base64url valide (garde SSRF dans `push_routes.py`). Ne
  pas élargir l'allowlist sans revue sécurité.
- Secrets : `.env` gitignoré ; ne jamais commiter ni logger les clés VAPID ni le
  mot de passe admin. L'admin seed n'est imprimé en console **que** si
  `EDULINK_DEBUG=1`.

### Données & migrations

- Le schéma est géré par **Alembic** (`migrations/`). En dev, `create_app()`
  lance `alembic upgrade head` au boot ; `scripts/migrate.sh` est le fallback
  explicite. En test, c'est `db.create_all()` sur la base `:memory:` (Alembic
  ne peut pas partager une connexion `:memory:`). **Tout changement de schéma
  passe par une nouvelle migration Alembic**, pas par `create_all`.
- Notifications : la colonne `channel_id` (nullable) relie les notifications de
  message à un canal ; les notifications d'annonce la laissent `NULL`. L'UI
  navigue via `n.channel_id` — ne **pas** parser la chaîne `content`.

### Pagination

- Annonces : pagination par page (`paginate(page, per_page)`, défaut 10,
  `?page=`).
- Messages de canal : pattern chat — `limit` (défaut 50) des derniers messages
  + lien « charger plus anciens » via `?before=<message_id>`
  (`list_by_channel(...)` retourne `(messages, has_more)`).

### Accès aux dépendances dans les routes

- Toujours via `get_use_cases()` / `current_actor()` (`routes/utils.py`).
- Ne jamais importer `app.infrastructure` ni `app.extensions.db` dans une route.
- Les lectures (liste des utilisateurs, résolution des noms) passent par les
  use cases de requête (`list_all_users`, `find_users_by_ids`).

---

## 6. Variables d'environnement & secrets

| Variable | Rôle |
|---|---|
| `EDULINK_ADMIN_EMAIL` / `EDULINK_ADMIN_PASSWORD` | Admin seed au premier boot (défaut `admin@edulink.local`) |
| `EDULINK_DEBUG=1` | Mode debug + impression du mot de passe admin généré |
| `EDULINK_HOST` / `EDULINK_PORT` | Bind du serveur (défaut `0.0.0.0:5050`) |
| `DATABASE_URL` | URI SQLite (défaut `sqlite:///edulink.db`) |
| `SECRET_KEY` | Si absent → clé générée persistée dans `instance/secret_key` |
| `UPLOAD_FOLDER` | Dossier des PDF (défaut `uploads/`) |
| `VAPID_PUBLIC_KEY` / `VAPID_PRIVATE_KEY` / `VAPID_SUBJECT` | Web push (tests : vides et hermétiques) |
| `SESSION_COOKIE_SECURE` | Cookie session en HTTPS |

---

## 7. Tests

### Structure

```txt
tests/
  domain/            → tests d'entités pures
  application/       → tests de use cases (avec repos SQLAlchemy réels)
  infrastructure/    → tests d'adapters (repos)
  interfaces/        → tests de routes via app.test_client()
  conftest.py        → fixtures app / client / factories
  helpers.py         → login, create_user, create_channel, add_message,
                       add_announcement, add_notification
```

### Fixtures (`tests/conftest.py`)

- `app` : `create_app(testing=True)` → SQLite `:memory:`, CSRF off, VAPID vide.
- `client` : `app.test_client()`.
- `user_factory` / `channel_factory` : raccourcis vers `tests/helpers.py`.

### Pièges connus (importants !)

- **Flash échappés** : les messages flash sont échappés HTML dans les templates
  — une apostrophe rend `&#39;`. Asserter sur des sous-chaînes **sans
  apostrophe** (ex. `b"Acces reserve a l"`).
- **Un login par client** : plusieurs `app.test_client()` du même app partagent
  l'état de session. Ne pas cumuler deux logins sur le même client sans
  logout.
- **`db.session.get(Model, id)`** plutôt que `Model.query.get(id)` (deprecated
  en SQLAlchemy 2.0).
- Les fonctions temps réel (SocketIO) et le web push ne sont testés
  qu'indirectement : les tests de use cases reposent sur un service realtime
  qui tolère l'absence de client connecté.

### Lancer

```bash
source .venv/bin/activate
pytest            # pyproject.toml configure pythonpath, pas besoin de -m pytest
```

---

## 8. Pour aller plus loin

- Procédure d'ajout d'une fonctionnalité : `docs/ADDING_A_FEATURE.md`.
- Conventions machine/agents et pièges historiques : `AGENTS.md`.
- Setup et tunnel HTTPS pour tester le push sur mobile : `README.md`.