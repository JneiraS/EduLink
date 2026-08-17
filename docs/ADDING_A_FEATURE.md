# EduLink — Ajouter une fonctionnalité

Guide pratique pour implémenter **rapidement et correctement** une nouvelle
fonctionnalité dans EduLink, en respectant l'architecture hexagonale et les
conventions du projet. Prérequis : avoir lu [`docs/ARCHITECTURE.md`](ARCHITECTURE.md).

Règle d'or : **tests d'abord (TDD), dépendances vers l'intérieur, erreurs
métier dans le use case, câblage dans `create_app()`.**

---

## 1. Avant de coder : situer la fonctionnalité

Répondez à ces questions, elles déterminent les fichiers touchés :

| Question | Conséquence |
|---|---|
| Nouvelle donnée persistée ? (table, colonne) | → modèle ORM (`infrastructure/database/models.py`) + entité domaine + **migration Alembic** |
| Nouvelle règle métier ? (validation, droits, état) | → **use case** (`application/use_cases/`) qui lève `DomainError` |
| Nouvelle opération de lecture/écriture ? | → méthode sur le **port** (`domain/ports/repositories.py`) + implémentation dans l'adapter |
| Nouvelle page / formulaire ? | → **route** + **template** |
| Nouveau comportement temps réel ou push ? | → `RealtimeNotificationPort` (déjà implémenté par `SocketIONotificationService`) |
| Nouveau rôle / droit ? | → `UserRole` dans `domain/entities/user.py` + garde dans le use case |

Quelle que soit la réponse, la plupart des fonctionnalités traversent **toutes
les couches**. Le chemin complet est décrit ci-dessous.

---

## 2. Workflow TDD pas-à-pas

L'ordre minimise les allers-retours : on pose d'abord le contrat (tests +
ports), puis on l'implémente de l'intérieur (domaine) vers l'extérieur
(infrastructure, interfaces).

```bash
source .venv/bin/activate
```

### Étape 1 — Test de use case (rouge)

Dans `tests/application/test_<feature>_use_cases.py`, écrivez le test du
comportement métier (validation, autorisation, persistance) en utilisant les
adapters réels (cf. `tests/application/test_admin_use_cases.py`). Créez les
données via `tests/helpers.py` dans un `with app.app_context():`.

```python
def test_something_requires_admin(app):
    actor = create_user(app, role="PARENT")
    # ... comportement attendu ...
    with pytest.raises(AuthorizationError):
        get_use_cases().mon_use_case.execute(...)
```

Le test échoue tant que le use case n'existe pas. **C'est voulu.**

### Étape 2 — Entité domaine (si nouvelle donnée)

Créez `app/domain/entities/<entity>.py` : une **dataclass `slots=True`** avec
`id: int | None` (voir `app/domain/entities/user.py`). Aucun import framework.

### Étape 3 — Port

Ajoutez la méthode abstraite au bon port dans `app/domain/ports/repositories.py`
(ou `services.py` si c'est un service). C'est le **contrat** que les use cases
vont appeler.

### Étape 4 — Adapter + modèle ORM + migration (si besoin)

- Ajoutez la méthode dans l'adapter SQLAlchemy correspondant
  (`app/infrastructure/repositories/*.py`), avec le mapping **`_to_entity`**
  (l'ORM ne doit jamais sortir de l'infrastructure).
- Si nouvelle table/colonne : modifiez `app/infrastructure/database/models.py`
  puis générez une migration :
  ```bash
  alembic revision --autogenerate -m "describe change"
  alembic upgrade head
  ```
- Ajoutez un test adapter dans `tests/infrastructure/` (ex.
  `tests/infrastructure/test_admin_repositories.py`).

### Étape 5 — Use case

Créez `app/application/use_cases/<feature>_use_cases.py` :

```python
@dataclass(slots=True)
class MonUseCase:
    users: UserRepositoryPort

    def execute(self, actor: User, ...):
        if actor.role != UserRole.ADMIN:
            raise AuthorizationError("...")
        ...
```

- **Validation et droits dans le use case**, jamais dans la route.
- Levez `AuthorizationError` / `NotFoundError` / `ValidationError` /
  `AuthenticationError` de `app/domain/errors.py`.
- Retournez des **entités domaine**.

Faites passer le test de l'étape 1 (vert).

### Étape 6 — Câblage (composition root)

- Ajoutez le champ au dataclass `UseCaseContainer`
  (`app/application/container.py`).
- Instanciez le use case dans `create_app()` (`app/__init__.py`) et enregistrez-le
  sur `app.extensions["use_cases"]`.

### Étape 7 — Route

- Créez/extendez un blueprint dans `app/interfaces/web/routes/` (voir
  `admin_routes.py` comme référence complète : `Blueprint("admin", __name__,
  url_prefix="/admin")`, `@login_required`, garde de rôle, `try/except
  DomainError` → `flash(str(exc), "danger")`).
- Accédez aux dépendances **uniquement** via `get_use_cases()` /
  `current_actor()` (`app/interfaces/web/routes/utils.py`).
- **Interdits** dans une route : importer `app.infrastructure`, importer
  `app.extensions.db`, lever `flask.abort`.
- Enregistrez le blueprint dans `create_app()` (`app.register_blueprint(...)`).

### Étape 8 — Template + CSS/JS

- Créez le template dans `app/interfaces/web/templates/<feature>/`.
- Extendez `base.html` ; la navigation suit le motif des nav-pills existantes.
  Pour ajouter une page, soit un lien `nav-pill` direct dans `base.html`, soit
  une entrée du menu déroulant « Administration » (réservé `ADMIN`). La navbar
  est `navbar-expand-lg` avec hamburger : les libellés restent visibles en
  mobile.
- **CSP sans `'unsafe-inline'` pour les scripts** : tout JS custom va dans
  `static/js/app.js`, tout CSS dans `static/css/app.css`. Pas de script inline
  dans un template.
- Boutons de suppression/confirmation : utilisez `data-confirm` (géré par
  `initConfirmDialogs` dans `app.js`).
- Sélection multiple de personnes : réutilisez le **sélecteur de membres**
  (`group_users_by_role` dans `presentation.py` + `initMemberPicker` dans
  `app.js`), qui fournit recherche, regroupement par rôle et compteur. Pour une
  sélection **unique** (ex. l'interlocuteur d'une conversation 1:1), le même
  `group_users_by_role` alimente une liste de radios (`messages/new_conversation.html`).
- Bascule d'options de formulaire (afficher/masquer un bloc) : `data-audience-toggle`
  + `data-audience-target` (gérés par `initAudiencePicker`) — voir le sélecteur
  d'audience des annonces.
- Insertion d'un contenu réutilisable dans un textarea (modèles de messages) :
  boutons `data-template-content` gérés par `initTemplateInsert`.

### Étape 9 — Tests d'interface

Ajoutez `tests/interfaces/test_<feature>_routes.py` : accès (anonyme → 302,
rôle insuffisant → message flash), comportement nominal, cas d'erreur. Utilisez
`login(client, user_id)` de `tests/helpers.py`.

### Étape 10 — Vérification finale

```bash
pytest            # toute la suite
```

Puis un boot rapide en dev pour valider le rendu et la CSP
(`EDULINK_DEBUG=1 python run.py`).

---

## 3. Exemple fil rouge : le panneau d'administration

Fonctionnalité « gestion des membres, annonces et canaux » (admin). C'est
l'implémentation de référence : suivez ses fichiers dans l'ordre.

1. **Tests use cases** — `tests/application/test_admin_use_cases.py` :
   garde ADMIN (`_require_admin`), protection du compte propre (on ne peut pas
   changer son propre rôle / se désactiver), protection du **dernier admin
   actif** (on ne peut ni le rétrograder ni le désactiver), rôle invalide →
   `ValidationError`.
2. **Ports** — ajout de méthodes : `AnnouncementRepositoryPort.find_by_id /
   delete / list_all`, `ChannelRepositoryPort.find_by_id / list_all / delete /
   list_member_ids`, `UserRepositoryPort.list_users` (déjà présente).
3. **Adapters** — `app/infrastructure/repositories/*.py` : implémentations avec
   `_to_entity` ; `DeleteChannel` purge la table `channel_members` via la
   relation ORM avant suppression. **Aucune migration** : aucune colonne
   ajoutée.
4. **Use cases** — `app/application/use_cases/admin_use_cases.py` :
   `ListUsersForAdmin`, `UpdateUserRole`, `ToggleUserActive`,
   `ListAnnouncementsForAdmin`, `DeleteAnnouncement`, `ListChannelsForAdmin`
   (retourne des `dict` avec `member_count`), `DeleteChannel`. Tous commencent
   par `_require_admin(actor)`.
5. **Câblage** — champs ajoutés dans `container.py`, instances dans
   `create_app()` (`app/__init__.py`).
6. **Routes** — `app/interfaces/web/routes/admin_routes.py` :
   `_guard_admin()` → `current_actor()`, contrôle du rôle, flash si refus ;
   routes GET pour lister + POST pour les actions ; `_remove_pdf()` purge le
   fichier PDF lors de la suppression d'annonce (via `_uploads_dir` importé de
   `announcements_routes.py`).
7. **Templates** — `templates/admin/{members,announcements,channels}.html` +
   menu déroulant « Administration » dans `base.html` (visible si `ADMIN`) +
   styles `.admin-table`, `.status-badge`, `.avatar-sm` dans `app.css` +
   `data-confirm` pour les suppressions.
8. **Tests interface** — `tests/interfaces/test_admin_routes.py` : page
   protégée (302 anonyme), refus TEACHER (`b"Acces reserve a l"` — attention à
   l'apostrophe échappée `&#39;` !), listing, changement de rôle, toggle
   actif/inactif, suppression d'annonce avec purge du PDF.

**Leçon** : chaque brique est petite, pure et testée à son niveau ; le
câblage ne fait que de l'assemblage.

### Exemple fil rouge n°2 : les enfants (feature « Enfants »)

Feature « enfants » (rattachement d'un enfant à un parent, lien aux canaux de
classe) — second exemple complet, avec nouvelle table. Suivez ses fichiers :

1. **Tests use cases** — `tests/application/test_children_use_cases.py` (avec
   repos in-memory) : garde ADMIN sur `CreateChild`/`DeleteChild`/
   `LinkChildToClassChannels`, validation des noms (≤120), `parent_id` requis
   et doit être un `PARENT`, `DeleteChild` lève `NotFoundError` si absent,
   `LinkChildToClassChannels` ne **réutilise pas un canal `direct`** du même nom
   (filtre `kind="group"`), et **`CreateChild` relie automatiquement** le parent
   au canal de classe (créé s'il manque, réutilisé s'il existe).
2. **Ports** — `ChildrenRepositoryPort` (`save`, `list_by_parent`,
    `find_by_class`, `find_by_id`, `delete`, `list_class_names` pour les
    classes distinctes du formulaire) ; `ChannelRepositoryPort.find_by_name`
    gagne un paramètre `kind: str | None = None` (filtre optionnel).
3. **Adapters + migration** — `SQLAlchemyChildrenRepository` (mapping
   `_to_entity`) ; table `children` via migration Alembic
   (`migrations/versions/317b92dacc5c_add_children_table.py`).
4. **Use cases** — `app/application/use_cases/children_use_cases.py`
    (`CreateChild`, `ListChildren`, `ListClassNames`, `DeleteChild`,
    `LinkChildToClassChannels`).
5. **Câblage** — champs dans `container.py` + instances dans `create_app()`
    (`app/__init__.py`, dont l'enregistrement du blueprint `parent_bp`).
6. **Routes** — `admin_routes.py` (`/admin/children`, `/children/create`,
    `/children/<id>/delete`, `/children/<id>/link-channels`) + `parent_routes.py`
    (`/parent/children`, `/parent/children/<id>/channels` avec garde `PARENT` et
    résolution de l'enfant **via `ListChildren` du parent** — un enfant d'un
    autre parent est introuvable). La route `/admin/children` passe
    `class_names` (via `ListClassNames`) pour le `datalist` du formulaire.
7. **Templates** — `admin/children.html` (le champ « Classe » est un input
    libre relié à un `<datalist id="class-list">` listant les classes
    existantes : on peut choisir ou saisir une nouvelle classe),
    `parent/children.html`, `parent/child_channels.html` + entrée « Enfants »
    du menu déroulant « Administration » dans `base.html` (pour `ADMIN`) et
    lien « Mes enfants » pour `PARENT`.
8. **Tests interface** — `tests/interfaces/test_children_routes.py` : accès
   refusé aux rôles non habilités, listing, création (qui **relie aussi** le
   parent au canal de classe — vérifie les membres du canal via `row.user_id`),
   suppression, lien manuel aux canaux de classe, redirection pour un enfant
   d'un autre parent.

**Leçon** : le filtre par `kind` sur `find_by_name` montre comment un port peut
gagner un paramètre optionnel pour durcir une règle métier sans changer son
contrat pour les autres appelants.

---

### Exemple fil rouge n°3 : la recherche de messages dans un canal

Fonctionnalité « recherche ILIKE par canal, avec garde d'appartenance ».

1. **Tests use cases** — `tests/application/test_message_use_cases.py` (avec
   `InMemoryMessages` + `InMemoryChannels(members=...)`) :
   `SearchChannelMessages` relève `NotFoundError` si le canal n'existe pas,
   `AuthorizationError` si l'acteur n'en est pas membre, `ValidationError` pour
   une requête vide/trop longue, et renvoie les messages dont le contenu
   contient le mot-clé (ILIKE).
2. **Ports** — `MessageRepositoryPort.search_by_channel(channel_id, query, limit)`
   ajouté.
3. **Adapters** — `SQLAlchemyMessageRepository.search_by_channel` utilise
   `MessageModel.content.ilike(f"%{query}%")`, trié par `id desc` puis inversé
   pour l'ordre croissant d'affichage.
4. **Use cases** — `app/application/use_cases/message_use_cases.py`
   (`SearchChannelMessages`).
5. **Câblage** — champ `search_channel_messages` dans `container.py` + instance
   dans `create_app()` (`app/__init__.py`).
6. **Routes** — `messages_routes.py` (`/channels/<id>` GET avec `?q=` pour la
   recherche, `?before=` pour la pagination) : un `q` présent déclenche
   `SearchChannelMessages` et rend les résultats dans le même template
   `channel_detail.html`, avec variable `search_mode` (sinon listing paginé
   normal).
7. **Templates + CSS** — `messages/channel_detail.html` : un
   `<form method="get">` de recherche dans le bloc du compositeur, et un état
   vide « Aucun message ne contient … » quand `search_mode`. Styles
   `.search-form` dans `app.css`.
8. **Tests interface** — `tests/interfaces/test_messages_routes.py` :
   résultats de recherche visibles pour un membre, refus (`AuthorizationError`)
   pour un non-membre, état vide quand aucune correspondance.

**Leçon** : la garde d'appartenance et le `NotFoundError` sont partagés entre
`ListChannelMessages` et `SearchChannelMessages` — factorisez-les dans le use
case (ou un helper) plutôt que de dupliquer la logique dans la route.

---

### Exemple fil rouge n°4 : messages épinglés / importants

Fonctionnalité « colonne `is_pinned` + section Épinglés en tête + toggle
enseignant/admin ».

1. **Tests use cases** — `tests/application/test_message_use_cases.py` :
   `PinMessage` relève `AuthorizationError` pour un `PARENT` (seuls
   `ADMIN`/`TEACHER` épingle), `NotFoundError` si le message n'existe pas, et
   bascule `is_pinned` via `set_pinned` ; `ListPinnedMessages` impose la
   **même garde d'appartenance** que le listing et ne renvoie que les épinglés.
2. **Ports** — `MessageRepositoryPort.set_pinned(message_id, pinned)` et
   `list_pinned(channel_id)` ajoutés.
3. **Entité + migration** — champ `is_pinned: bool = False` sur `Message` ;
   colonne `is_pinned` (Boolean, `server_default=false()`) sur `messages`
   (migration `a1f42c8d9e77_add_messages_is_pinned`).
4. **Adapters** — `SQLAlchemyMessageRepository.set_pinned` / `list_pinned`
   (filtre `channel_id` + `is_pinned=True`, tri `created_at desc` puis
   inversion), `is_pinned` ajouté à `_to_entity`.
5. **Use cases** — `app/application/use_cases/message_use_cases.py`
   (`PinMessage`, `ListPinnedMessages`). **Refactor** : la garde
   canal/membre est extraite dans `_assert_channel_access` et partagée par
   `ListChannelMessages`, `SearchChannelMessages`, `PinMessage` et
   `ListPinnedMessages`.
6. **Câblage** — champs `pin_message` et `list_pinned_messages` dans
   `container.py` + instances dans `create_app()`.
7. **Routes** — `messages_routes.py` : branche POST `action == "toggle_pin"`
   sur `/channels/<id>` (message_id + `pinned` cible), et GET qui charge
   `list_pinned_messages` (hors conversations directes) pour la section.
8. **Templates + CSS** — `messages/channel_detail.html` : section « Épinglés »
   en tête du `.chat-messages` (visible uniquement si des épinglés existent,
   hors direct), bouton pin (toggle) sur chaque bulle réservé à
   `can_manage_members` ; `build_messages_view` gagne `id`/`is_pinned`. Styles
   `.pinned-section` / `.pin-form` dans `app.css`.
9. **Tests interface** — `tests/interfaces/test_messages_routes.py` : un
   enseignant épingle et la section s'affiche (persistance DB), un `PARENT`
   reçoit `AuthorizationError` (état inchangé), et le bouton pin est absent
   pour un parent.

**Leçon** : une capacité d'écriture réservée à certains rôles (épingler)
se contrôle **dans le use case**, pas seulement dans le template — le template
cache le bouton, le use case reste la garde de vérité.

---

### Exemple fil rouge n°5 : préférences de notification par conversation

Fonctionnalité « toggle global (recevoir toutes les notifications) + toggle
par conversation (canal ou 1:1) », visible par **tous** les membres.

1. **Tests use cases** — `tests/application/test_notification_preferences_use_cases.py`
   (fakes `InMemoryPrefs` + `InMemoryChannelsForPrefs`) :
   `GetNotificationSettings` renvoie `global_enabled` + `channel_states`
   (défaut tout activé), `ToggleChannelNotifications` inverse l'état et impose
   l'appartenance (`NotFoundError`/`AuthorizationError`), `SetGlobalNotifications`
   persiste. Côté `SendMessage` (`tests/application/test_message_notifications_use_case.py`) :
   un membre « muet » (canal désactivé) **ne reçoit ni notification ni push**.
2. **Ports** — `NotificationPreferencesPort` ajouté (`get_global_enabled`,
   `set_global_enabled`, `is_channel_enabled`, `set_channel_enabled`,
   `list_channel_states`, `is_enabled`).
3. **Migration** — `c3d9b4e5f6a7_add_notification_preferences` : tables
   `user_notification_settings` et `channel_notification_settings` (absence de
   ligne = activé).
4. **Adapters** — `notification_preferences_repository.py`
   (`SQLAlchemyNotificationPreferencesRepository`) : `db.session.get` sur la
   clé composite `(user_id, channel_id)`, défaut `True`, upsert simple.
5. **Use cases** — `notification_use_cases.py` (`GetNotificationSettings`,
   `SetGlobalNotifications`, `ToggleChannelNotifications`). Ce dernier réutilise
   `_assert_channel_access` de `message_use_cases.py`.
6. **Filtrage** — `SendMessage` reçoit `preferences: NotificationPreferencesPort`
   en dépendance et saute `notifications.save` + `realtime.notify_user` quand
   `is_enabled(member_id, channel_id)` est faux (global OU canal désactivé).
7. **Câblage** — champs `get_notification_settings`, `set_global_notifications`,
   `toggle_channel_notifications` dans `container.py` + instances dans
   `create_app()` ; service `notification_preferences`.
8. **Routes** — `messages_routes.py` : `POST /channels/<id>/notifications`
   (toggle canal, redirect liste), `POST /notifications/global` (toggle global),
   branche `action == "toggle_notifications"` sur `/channels/<id>` (toggle depuis
   le canal) ; le GET des listes et du canal passe `notif_*` / `notifications_enabled`.
9. **Templates + CSS + JS** — `channels.html` : commutateur global (form-switch,
   soumission **via `data-global-notif-form` dans `app.js`** — pas de script
   inline, CSP) + bouton cloche par conversation ; `channel_detail.html` :
   bouton cloche dans le header. Styles `.notif-global-toggle` /
   `.notif-channel-toggle` dans `app.css`.
10. **Tests interface** — `tests/interfaces/test_messages_routes.py` : la liste
    rend les toggles, le toggle global et le toggle canal persistent en DB, un
    non-membre est refusé (`AuthorizationError`, aucun enregistrement), et le
    toggle depuis `channel_detail` fonctionne.

**Leçon** : un toggle d'abonnement n'est pas un privilège de rôle — il est
ouvert à **tout membre** et la garde n'est que l'appartenance au canal. Le
filtrage réel (ne pas créer la notification) vit dans le **use case d'écriture**
(`SendMessage`), pas dans le template.

---

### Exemple fil rouge n°6 : enrichissement du tableau de bord (rôle)

Le dashboard était « vide » (hero + actions rapides + timeline). Il a été
enrichi pour les 3 rôles : **stat cards**, **mes conversations** (avec aperçu du
dernier message), panneau **« Mes enfants »** (parent), vue d'ensemble plateforme
+ **inscriptions récentes** (admin), onboarding par rôle.

1. **Tests use cases** — `tests/application/test_dashboard_use_case.py`
   (fakes `InMemoryAnnouncements/Notifications/Channels/Messages/Children/Users`) :
   `role_message` par rôle, `stats` (non lus, nb conversations, annonces non
   lues), `conversations` avec `last_message`, `latest_announcements` avec
   `is_read`, `children` pour le parent, `user_counts`/`channel_count`/
   `announcement_count`/`recent_users` pour l'admin, et **absence** de clés
   rôle-spécifiques pour les autres rôles.
2. **Ports** — trois nouvelles méthodes :
   `MessageRepositoryPort.list_latest_by_channels(channel_ids)` (dernier message
   par canal, **une requête groupée** via `MAX(id)`, pas de N+1),
   `NotificationRepositoryPort.count_unread(user_id)`,
   `AnnouncementRepositoryPort.count_unread_for_user(user_id)`.
3. **Adapters** — `message_repository.py`, `notification_repository.py`,
   `announcement_repository.py` implémentent les méthodes (tests dans
   `tests/infrastructure/test_dashboard_repositories.py`).
4. **Use case** — `GetDashboard` reçoit 6 repos et renvoie un dict complet ;
   les clés rôle-spécifiques (`children`, `user_counts`…) ne sont ajoutées que
   pour le rôle concerné.
5. **Câblage** — `GetDashboard` instancié dans `create_app()` avec tous les
   repos ; la route passe le nouveau contexte au template.
6. **Template + CSS** — `home.html` : `.stat-grid` / `.stat-card--brand|warn|ok`
   (icônes teintées via `color-mix`), `.conversation-item` (aperçu ellipsis +
   hover `--list-hover-bg`), `.child-card`, `.recent-user-item`. Les empty-states
   guident l'action (parent sans enfant, admin → créer des comptes).
7. **Tests interface** — `tests/interfaces/test_dashboard_routes.py` : stat
   cards visibles pour tous les rôles, panel enfants + onboarding parent,
   conversation avec dernier message (enseignant), stats + inscriptions récentes
   (admin).

**Leçons** : (1) un dashboard n'est pas « un template avec des chiffres » — les
compteurs vivent dans le **use case**, pas dans la route ni le template ; (2) les
**clés rôle-spécifiques conditionnelles** (`if actor.role == ...`) évitent de
fuir des données d'un rôle vers un autre ; (3) pour un aperçu « dernier message »
sur N canaux, une méthode de port groupée (`MAX(id)` + fetch) évite le N+1.
(4) un compteur « non lus » sans mécanisme de passage en lu reste bloqué à une
valeur — la lecture effective se fait à l'ouverture du canal :
`MarkChannelNotificationsRead` (use case) → `mark_channel_read` (port/repo,
`UPDATE ... WHERE channel_id AND user_id AND is_read=False`), appelé dans le GET
de `channel_detail`, avec la même garde `_assert_channel_access`.

---

## 4. Checklist finale avant de considérer une fonctionnalité terminée

- [ ] Use case testé en premier (TDD) ; validation/droits dans le use case,
      `DomainError` levées.
- [ ] Port mis à jour si nouvelle opération ; adapter conforme, mapping via
      `_to_entity`.
- [ ] Migration Alembic créée **si et seulement si** le schéma change.
- [ ] Use case déclaré dans `container.py` **et** instancié dans `create_app()`.
- [ ] Route : `@login_required`, accès via `get_use_cases()`/`current_actor()`,
      pas d'import infrastructure, `flash(str(exc), "danger")` sur `DomainError`.
- [ ] Template sans script inline (CSP) ; JS/CSS dans `static/`.
- [ ] Tests d'interface couvrant accès + comportement nominal + erreur.
- [ ] `pytest` tout vert.
- [ ] **Documentation mise à jour** : `docs/ARCHITECTURE.md` (mapping
      fonctionnalité → use case, nouvelles conventions) et/ou
      `docs/ADDING_A_FEATURE.md` (nouveaux pièges / patterns).

---

## 5. Pièges courants (rappel)

- **Fonctionnalités JS / UX** : il n'y a pas de framework de test JS dans le
  projet. Les composants `app.js` (ex. `initMemberPicker`) sont testés via le
  **contrat DOM rendu** : les tests de route assertent la présence des
  `data-*` hooks et de la structure que le JS attend. Tout nouveau composant JS
  doit exposer ces hooks (`data-*`) et rester fonctionnel **sans JS**
  (amélioration progressive), le JS allant uniquement dans `static/js/app.js`
  (CSP).
- **Apostrophes dans les assertions** : les templates échappent HTML, une
  apostrophe devient `&#39;`. Asserter sur des sous-chaînes sans apostrophe.
- **Attributs multi-lignes** : un `<input>` rendu sur plusieurs lignes (retours
  à la ligne dans le template) produit des espaces/retours dans le HTML. Pour
  asserter sur un attribut exact (ex. `value="3" id="member_3" checked`),
  écrire l'input sur une seule ligne dans le template.
- **Point d'entrée toujours exposé** : une liste vide ne doit pas masquer
  l'accès à la fonctionnalité (cul-de-sac de découvrabilité). Ex. les modèles
  de messages : le lien « Gerer mes modeles » est affiché en permanence sur la
  page canal et sur la page Messagerie, le picker de sélection seul est
  conditionnel à l'existence de modèles.
- **Plusieurs logins sur le même `app.test_client()`** : la session est
  partagée entre clients d'un même app. Un seul login par client, ou logout
  explicite entre deux. Attention : pytest-flask pousse un
  `test_request_context` autouse qui **caches `current_user`** pour toute la
  durée du test — enchaîner `login(A)` puis `login(B)` ne rebranche pas
  réellement l'utilisateur courant. Pour « agir en tant qu'un autre », créer
  les données directement en base puis faire **un seul** `login()`.
- **Colonne `NOT NULL` sur une table existante** : `alembic revision
  --autogenerate` ne détecte pas le besoin d'un `server_default`. Pour que
  SQLite remplisse les lignes existantes, ajoutez `server_default="..."` à la
  colonne dans la migration (ex. `channels.kind` → `server_default='group'`).
- **Clé primaire composite** : `db.session.get(Model, (pk1, pk2))` (ex.
  `AnnouncementReadModel`).
- **`Model.query.get(id)` est déprécié** : utiliser `db.session.get(Model, id)`.
- **Changement de schéma** : passer par une migration Alembic, jamais par
  `create_all` (les tests re-créent le schéma eux-mêmes via `create_all` sur
  `:memory:`, mais le dev/prod suit les migrations).
- **Nouvelle limite de longueur** : la lever en `ValidationError` dans le use
  case, pas dans la route.
- **Web push / SocketIO** : ne pas bloquer la requête HTTP sur le push ; les
  écritures DB et les émissions socket restent dans la requête, le push part en
  arrière-plan (`ThreadPoolExecutor`).
- **Allowlist push** (`endpoint` HTTPS + hôtes FCM/Mozilla/Apple) : ne pas
  l'élargir sans revue sécurité.