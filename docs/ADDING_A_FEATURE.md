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
   nav-pill « Administration » dans `base.html` (visible si `ADMIN`) + styles
   `.admin-table`, `.status-badge`, `.avatar-sm` dans `app.css` + `data-confirm`
   pour les suppressions.
8. **Tests interface** — `tests/interfaces/test_admin_routes.py` : page
   protégée (302 anonyme), refus TEACHER (`b"Acces reserve a l"` — attention à
   l'apostrophe échappée `&#39;` !), listing, changement de rôle, toggle
   actif/inactif, suppression d'annonce avec purge du PDF.

**Leçon** : chaque brique est petite, pure et testée à son niveau ; le
câblage ne fait que de l'assemblage.

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