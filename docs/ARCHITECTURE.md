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

Versions critiques : Flask ≥ 3.1.3 et Werkzeug ≥ 3.1.5 (correctifs de
sécurité — ne pas revenir en arrière).

### Fonctionnalités et mapping (route → use case → repository)

| Fonctionnalité | Blueprint (`interfaces/web/routes/`) | Use case (`application/use_cases/`) | Adapter principal (`infrastructure/`) |
|---|---|---|---|
| Login / logout / création de comptes | `auth_routes.py` | `LoginUser`, `RegisterUser` | `user_repository.py`, `auth/password_hasher.py` |
| Dashboard adapté au rôle | `dashboard_routes.py` | `GetDashboard` | `announcement_repository.py`, `notification_repository.py`, `channel_repository.py`, `message_repository.py`, `children_repository.py`, `user_repository.py` |
| Annonces (liste, création ciblée, PDF) | `announcements_routes.py` | `CreateAnnouncement` (audience = « Tous » ou canaux de l'auteur), `ListAnnouncements` (visibilité scopée par appartenance), `GetAnnouncementPdf` | `announcement_repository.py` (`paginate`, `find_by_pdf_filename`), `channel_repository.py` |
| Accusé de réception des annonces (X/Y) | `announcements_routes.py` | `ConfirmAnnouncementRead`, `GetAnnouncementReadStatus` | `announcement_repository.py` |
| Canaux de messagerie (liste/création) | `messages_routes.py` | `CreateChannel`, `AddChannelMembers`, `ListUserChannels` | `channel_repository.py` |
| Conversations directes 1:1 | `messages_routes.py` (`/new-conversation`) | `OpenDirectConversation` | `channel_repository.py` |
| Messages en canal (chat + pagination + recherche + épinglés) | `messages_routes.py` | `SendMessage`, `ListChannelMessages`, `ListChannelMembers`, `SearchChannelMessages`, `PinMessage`, `ListPinnedMessages` | `message_repository.py` (`save`, `list_by_channel`, `search_by_channel`, `set_pinned`, `list_pinned`), `channel_repository.py` |
| Modèles de messages | `messages_routes.py` (`/templates`, `/templates/<id>/edit`) | `ListMessageTemplates`, `CreateMessageTemplate`, `UpdateMessageTemplate`, `DeleteMessageTemplate` | `message_template_repository.py` |
| Notifications (liste / lecture / lu à l'ouverture du canal) | `notifications_routes.py`, `messages_routes.py` (`/channels/<id>`) | `ListNotifications`, `MarkNotificationRead`, `MarkChannelNotificationsRead` | `notification_repository.py` |
| Préférences de notification (toggle global + par canal) | `messages_routes.py` (`/channels`, `/channels/<id>`) | `GetNotificationSettings`, `SetGlobalNotifications`, `ToggleChannelNotifications` | `notification_preferences_repository.py` (`get_global_enabled`, `is_channel_enabled`, `set_*`, `is_enabled`), `channel_repository.py` |
| Push web (abonnement PWA) | `push_routes.py` | `SubscribePushNotifications`, `UnsubscribePushNotifications` | `push_subscription_repository.py` |
| **Administration** (création de comptes, rôles, activ./désactiv., suppression) | `admin_routes.py` + lien vers `auth_routes.py` (`/auth/users/new`) | `ListUsersForAdmin`, `UpdateUserRole`, `ToggleUserActive`, `ListAnnouncementsForAdmin`, `DeleteAnnouncement`, `ListChannelsForAdmin`, `DeleteChannel` + `RegisterUser` | `user_repository.py`, `announcement_repository.py`, `channel_repository.py` |
| **Enfants** (rattachement à un parent, lien aux canaux de classe) | `admin_routes.py` (`/admin/children...`) + `parent_routes.py` (`/parent/children...`) | `CreateChild`, `ListChildren`, `ListClassNames`, `DeleteChild`, `LinkChildToClassChannels` | `children_repository.py`, `channel_repository.py` |
| **Statistiques admin** (graphiques Chart.js) | `admin_routes.py` (`/admin/stats`) | `GetAdminStats` (agrégations ; read-rates d'annonces calculés dans le use case) | `user_repository.py`, `message_repository.py`, `announcement_repository.py`, `channel_repository.py`, `push_subscription_repository.py` |
| Requêtes utilitaires (lecture) | routes diverses | `ListAllUsers`, `FindUsersByIds` (renvoient des `UserSummary` : `id`/`full_name`/`role` — **jamais** `email`/`password_hash`), `ListChannelMembers` (idem) | `user_repository.py` |

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
  `User`, `Channel` (avec `kind` : `"group"` ou `"direct"`), `Message`
  (avec `is_pinned`), `Announcement` (avec `target_channel_ids` pour le
  ciblage), `Notification`, `PushSubscription`, `MessageTemplate`, `Child`
  (enfant rattaché à un parent,
  avec `parent_id` et `class_name`), et `UserSummary` (DTO de lecture :
  `id`/`full_name`/`role` uniquement). Exemple :
  `app/domain/entities/user.py`.
  - `UserRole` (enum) : `PARENT` / `TEACHER` / `ADMIN`.
  - « Peut gérer les membres d'un canal » = `ADMIN` ou `TEACHER`.
- **`ports/`** — contrats **abstraits** (ABC) :
  - `repositories.py` : `UserRepositoryPort`, `AnnouncementRepositoryPort` (dont `mark_read` / `is_read` / `count_read` pour les accusés de réception,
    `count_unread_for_user` pour le compteur « annonces non lues » du dashboard,
    `paginate(page, per_page, channel_ids=None)` pour la liste scopée par
    appartenance, `find_by_pdf_filename` pour servir le PDF, et `list_recent(limit)`
    — les N dernières annonces, pour les read-rates des stats admin),
    `MessageRepositoryPort` (dont `search_by_channel`, `set_pinned` et
    `list_pinned` pour la recherche et les épinglés, `find_by_id` pour la garde
    d'appartenance de `PinMessage`, et `list_latest_by_channels`
    — dernier message par canal, une requête groupée, pour l'aperçu du dashboard,
    plus `count_grouped_by_date(since)` et `count_top_channels(limit)` pour les
    statistiques admin),
    `NotificationRepositoryPort` (dont `count_unread` pour la stat « non lus » et
    `mark_channel_read` — marque lues les notifications d'un canal quand on
    l'ouvre),
    `NotificationPreferencesPort` (`get_global_enabled`, `set_global_enabled`,
    `is_channel_enabled`, `set_channel_enabled`, `list_channel_states`,
    `is_enabled` — le toggle par conversation et le commutateur global),
    `ChannelRepositoryPort` (dont `find_direct_between` pour les 1:1 et
    `find_by_name(name, kind)` pour résoudre un canal par nom, optionnellement
    filtré par type — utilisé par le lien enfant → canaux de classe),
    `PushSubscriptionRepositoryPort` (dont `count_distinct_users` pour
    l'adoption push), `MessageTemplateRepositoryPort`
    (dont `update` pour modifier un modèle existant), `ChildrenRepositoryPort`
    (`save`, `list_by_parent`, `find_by_class`, `find_by_id`, `delete`,
    `list_class_names` pour les classes distinctes du formulaire). Les compteurs
    d'agrégation des stats admin (`UserRepositoryPort.count_total / count_active /
    count_by_role / count_grouped_by_date`) font des `GROUP BY date(created_at)`
    bruts — le padding des jours/semaines vides est fait dans `GetAdminStats`.
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
  `AnnouncementModel`, `AnnouncementReadModel`, `ChannelModel` (avec `kind`),
  `MessageModel`, `NotificationModel`, `PushSubscriptionModel`,
  `MessageTemplateModel`, `ChildModel` (table `children`), tables
  d'association `channel_members` et `announcement_channels`).
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
  `announcements_bp`, `messages_bp`, `notifications_bp`, `push_bp`,
  `parent_bp`).
- **`routes/utils.py`** : les **seuls** accès autorisés aux dépendances :
  - `get_use_cases()` → `app.extensions["use_cases"]`
  - `get_services()` → `app.extensions["services"]` (uniquement pour la
    passation Flask-Login `get_auth_model(id)`)
  - `current_actor()` → `User` domaine via `users.find_by_id(...)`
- **`routes/presentation.py`** : helpers de mise en forme (résolution des noms
  d'expéditeurs, construction de la vue des messages, parse des membres,
  `group_users_by_role` pour le sélecteur de membres).
- **`socket_events.py`** : enregistre les handlers SocketIO (rejoindre les
  rooms `user_<id>` et `channel_<id>`).
- **`templates/`** : Jinja2. **`static/`** : CSS/JS custom, manifest PWA.
  La navigation principale vit dans `base.html` : une navbar Bootstrap
  responsive (`navbar-expand-lg`) avec bouton hamburger sur écran < 992px.
  Les liens principaux (Annonces, Messagerie) sont des nav-pills ; pour
  `ADMIN`, les sections Membres, Enfants, Annonces et Canaux sont regroupées
  dans un menu déroulant « Administration » ; pour `PARENT`, le lien
  « Mes enfants » — il n'y a plus de sous-navigation `admin/_nav.html`.
  En mobile, le menu replié s'affiche en colonne et les libellés restent
  visibles (les styles icon-only d'avant ont été retirés).

Le **sélecteur de membres** (création de canal, « ajouter des membres ») est
un composant réutilisable : recherche temps réel, regroupement par rôle
(`group_users_by_role` dans `presentation.py`), sélection globale par groupe,
compteur de sélection et chips supprimables. Le comportement vit dans
`static/js/app.js` (`initMemberPicker`) via des `data-*` hooks — aucune fonction
JS inline. Sans JS, la liste complète des cases à cocher reste fonctionnelle.
Le même regroupement par rôle sert de **liste de contacts** pour les
conversations 1:1 (`messages/new_conversation.html`, radios de sélection
unique). Le compositeur de message embarque un sélecteur de **modèles**
(`initTemplateInsert` : boutons `data-template-content` qui insèrent le texte
dans le textarea, affiché dès qu'il existe au moins un modèle) et la page
annonce un sélecteur d'**audience** (`initAudiencePicker` : radios qui
affichent/masquent la liste des canaux ciblés). Le point d'entrée
« Gerer mes modeles » est lui **toujours visible** (page canal + page
Messagerie), pour éviter le cul-de-sac où l'on ne peut pas créer un premier
modèle sans en posséder déjà un. Sur la page Messagerie, le CTA
« Nouvelle conversation » est porté par l'**en-tête de page** (bouton primaire
à droite), donc visible en haut même sans canal existant.

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
   `ProductionConfig` si `APP_ENV=production`, sinon `DevelopmentConfig`
   (depuis `app/config/settings.py`). `ProductionConfig` force
   `SESSION_COOKIE_SECURE`, `HTTPONLY`, `SameSite=Lax` et une
   `PERMANENT_SESSION_LIFETIME` (défaut 12 h).
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
  message ≤5000, label de modèle de message ≤80, contenu de modèle ≤5000.

### Annonces ciblées & accusés de réception

- `CreateAnnouncement` notifie **tous** les utilisateurs sauf si
  `target_channel_ids` est renseigné : l'audience est alors l'**union des
  membres des canaux ciblés** (chaque canal doit exister → `NotFoundError`).
  Un `TEACHER` ne peut cibler que des canaux **dont il est membre**
  (`AuthorizationError` sinon) ; l'`ADMIN` peut tout cibler. Le sélecteur de la
  page ne propose que **les canaux de l'auteur** (`list_user_channels`) ;
  « Tous » reste disponible.
- **Visibilité en lecture** : `ListAnnouncements` ne renvoie que les annonces
  globales **ou** ciblées vers un canal dont l'acteur est membre
  (`paginate(..., channel_ids)` filtre via `announcement_channels`). Le
  téléchargement du PDF (`GetAnnouncementPdf` + route `/files/<filename>`)
  applique la même garde : un non-membre reçoit un 404. `ConfirmAnnouncementRead`
  refuse aussi les annonces hors périmètre (404).
- Les accusés de réception sont idempotents (`mark_read`). `GetAnnouncementReadStatus`
  calcule le dénominateur « X/Y » : union des membres des canaux ciblés pour une
  annonce ciblée, sinon le nombre total d'utilisateurs. Le compteur « Vu par
  X/Y » s'affiche pour admin/teacher ; le bouton « Confirmer la lecture » (ou
  l'état « Confirme ») pour tous.

### Conversations 1:1

- `Channel.kind` vaut `"group"` (défaut) ou `"direct"`. Les conversations
  directes sont **réservées à deux membres** : `AddChannelMembers` refuse
  d'ajouter qui que ce soit sur un canal `direct`, et l'UI masque le panneau
  « Ajouter des membres » **et la carte « Membres »** (redondante en 1:1 : le
  header affiche déjà le nom de l'autre personne, le compteur et les avatars).
  Le chat passe alors en pleine largeur (`col-lg-12`). `OpenDirectConversation`
  réutilise la conversation existante entre deux utilisateurs
  (`find_direct_between`) et nomme le canal **du nom de l'autre personne**.
  Tout utilisateur authentifié peut ouvrir une conversation directe (annuaire
  minimal).

### Enfants & canaux de classe

- Les enfants sont créés par un `ADMIN` (`CreateChild`) et rattachés à un
  compte `PARENT` (validation du rôle dans le use case). `CreateChild` relie
  **automatiquement** le parent au canal de classe (même logique que
  `LinkChildToClassChannels`, factorisée dans `_link_child_to_class_channels`) :
  plus besoin de cliquer sur « Lier aux canaux de classe » après la création.
  `ListChildren` ne renvoie que les enfants du parent appelant (route
  `parent_routes.py`), ce qui empêche un parent de voir les enfants d'un autre.
- `LinkChildToClassChannels` (réservé admin) relie le parent à un canal de
  classe : il cherche un canal **`kind="group"`** par `class_name`
  (`find_by_name(name, kind="group")`) et le crée s'il n'existe pas. Le filtre
  par `kind` évite de relier le parent à un canal `direct` qui porterait le
  même nom. Il reste disponible pour rattacher manuellement un enfant existant
  (ex. changement de classe).
- La page parent `/parent/children/<id>/channels` liste les canaux du parent
  dont le nom correspond à la classe de l'enfant (`list_user_channels` filtré
  par `class_name`). Un enfant d'un autre parent est introuvable → redirect.

### Sécurité

- CSRF activé en dev, désactivé en test (`TestingConfig.WTF_CSRF_ENABLED =
  False`).
- Login POST rate-limité (5/15 min/IP) via Flask-Limiter en dev
  (`RATE_LIMIT_ENABLED`) ; `/auth/invite/<token>` POST est limité à
  10/heure/IP. Tous les échecs de login lèvent le **même** message
  « Invalid credentials » (pas d'énumération de comptes), et la session est
  `session.clear()` + `session.permanent = True` avant `login_user()`.
- CSP `script-src 'self'` + CDNs (pas de `'unsafe-inline'` pour scripts) → tout
  JS custom doit vivre dans `static/js/app.js`.
- Uploads : dossier `UPLOAD_FOLDER` (défaut `uploads/`, gitignoré), **uniquement PDF**
  (`ALLOWED_EXTENSIONS = {"pdf"}`), **max 5 MB** (`MAX_CONTENT_LENGTH`), plus
  vérification des octets magiques `%PDF` avant sauvegarde.
- Push : `endpoint` dans une allowlist (HTTPS + hôtes FCM/Mozilla/Apple, port 443
  uniquement) et clés `p256dh` **exactement 65 octets** (clé publique ECDH P-256
  décompressée — pywebpush rejette toute autre taille) / `auth` en base64url
  valide (garde SSRF + validation stricte dans `push_routes.py`). Ne
  pas élargir l'allowlist sans revue sécurité. L'envoi push part d'un
  `ThreadPoolExecutor` borné (`_WEB_PUSH_WORKERS = 4`).
- Secrets : `.env` gitignoré ; ne jamais commiter ni logger les clés VAPID ni le
  mot de passe admin. L'admin seed n'est imprimé en console **que** si
  `EDULINK_DEBUG=1`.
- Sessions : `SESSION_COOKIE_HTTPONLY`, `SameSite=Lax` ; `Secure` + HSTS en
  production. `session.permanent` étend le cookie à `PERMANENT_SESSION_LIFETIME`.
- Canaux : `CreateChannel` vérifie que chaque membre existe (pas de membres
  fantômes) ; `CreateAnnouncement` impose qu'un `TEACHER` ne cible que des
  canaux dont il est membre (l'`ADMIN` peut tout cibler). `PinMessage` vérifie
  que le message appartient bien au canal (anti-BOLA inter-canaux).
- Recherche : les wildcards SQL `%`/`_` dans la requête de recherche de messages
  sont échappés (`escape="\\"`) pour rester littéraux.

### Données & migrations

- Le schéma est géré par **Alembic** (`migrations/`). En dev, `create_app()`
  lance `alembic upgrade head` au boot ; `scripts/migrate.sh` est le fallback
  explicite. En test, c'est `db.create_all()` sur la base `:memory:` (Alembic
  ne peut pas partager une connexion `:memory:`). **Tout changement de schéma
  passe par une nouvelle migration Alembic**, pas par `create_all`.
- Notifications : la colonne `content` est un **`Text`** (les titres d'annonce
  vont jusqu'à 255 caractères, « Nouvelle annonce: … » pourrait déborder un
  `String(255)`). La colonne `channel_id` (nullable) relie les notifications de
  message à un canal ; les notifications d'annonce la laissent `NULL`. L'UI
  navigue via `n.channel_id` — ne **pas** parser la chaîne `content`.
- **Préférences de notification** : deux tables — `user_notification_settings`
  (`user_id` PK, `global_enabled` booléen, commutateur « recevoir toutes les
  notifications ») et `channel_notification_settings` (`user_id` +
  `channel_id` PK, `enabled`). L'absence de ligne = activé (défaut). Le
  filtrage s'applique **dans `SendMessage`** avant de créer une notification ou
  d'émettre un push (`preferences.is_enabled(member_id, channel_id)` = global
  ET canal). Le toggle de canal est accessible à tous les membres ; la garde
  d'appartenance vit dans `ToggleChannelNotifications`.

### Pagination

- Annonces : pagination par page (`paginate(page, per_page, channel_ids)`,
  défaut 10, `?page=`) — la liste est scopée par appartenance.
- Messages de canal : pattern chat — `limit` (défaut 50) des derniers messages
  + lien « charger plus anciens » via `?before=<message_id>`
  (`list_by_channel(...)` retourne `(messages, has_more)`). Les **messages
  épinglés** (`is_pinned`, `set_pinned` / `list_pinned`) s'affichent dans une
  section « Épinglés » en tête du canal (hors conversations directes) ; le
  toggle épingler/désépingler est réservé à `ADMIN`/`TEACHER` (garde dans
  `PinMessage`).

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
| `APP_ENV=production` | Bascule sur `ProductionConfig` (cookie Secure, HSTS, expiration de session) |
| `SESSION_LIFETIME_SECONDS` | Durée de session en production (défaut 43200 = 12 h) |

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
  logout. De plus, pytest-flask pousse un `test_request_context` autouse qui
  **caches `current_user` pour toute la durée du test** : un second `login()`
  en cours de test ne rebranche pas réellement `current_user` (la session
  change, pas l'utilisateur courant). Pour « agir en tant qu'un autre
  utilisateur », créer les données directement en base (modèles SQLAlchemy)
  puis faire **un seul** `login()` — ne pas enchaîner deux logins.
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