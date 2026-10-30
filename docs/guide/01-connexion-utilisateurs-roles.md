# Connexion, utilisateurs et rôles

Cette partie explique qui peut entrer dans l'application, ce que chaque compte a le droit de voir, et comment les comptes sont gérés. Elle concerne tous les utilisateurs. La gestion des comptes est réservée aux rôles `admin`, `owner` et `manager`.

## Sommaire

- [Connexion](#connexion)
- [Bouton Quitter](#bouton-quitter)
- [Rôles et contrôle d'accès](#rôles-et-contrôle-daccès)
- [Liste et fiche des utilisateurs](#liste-et-fiche-des-utilisateurs)
- [Création d'un utilisateur](#création-dun-utilisateur)
- [Modification d'un utilisateur](#modification-dun-utilisateur)
- [Activation et désactivation d'un compte](#activation-et-désactivation-dun-compte)
- [Journal d'actions](#journal-dactions)
- [Entreprise et cloisonnement des données](#entreprise-et-cloisonnement-des-données)
- [Paramètres du magasin](#paramètres-du-magasin)
- [Menu de navigation par rôle](#menu-de-navigation-par-rôle)
- [Visite guidée](#visite-guidée)
- [Guide public](#guide-public)
- [À retenir](#à-retenir)

## Connexion

**Ce que voit l'utilisateur :** une page avec un nom d'utilisateur, un mot de passe et un bouton « Se connecter ». Si les informations sont fausses, le message « Nom d'utilisateur ou mot de passe incorrect. » s'affiche. Si elles sont bonnes, l'utilisateur arrive sur son tableau de bord. Un bouton en haut à droite change le thème clair ou sombre de la page.

**Ce qui se passe dans le code :**

1. Un visiteur non connecté ouvre une page protégée. Le décorateur `@login_required` le renvoie vers `login`, avec `?next=` pour mémoriser la page demandée. Un décorateur est une fonction qui enveloppe une vue pour ajouter un contrôle avant son exécution.
2. `stock_control/urls.py` sert `/login/` avec `LoginView.as_view()`, la vue fournie par Django, et le template `templates/login.html`.
3. Django vérifie le mot de passe sur le modèle `User` (`apps/accounts/models.py`), le modèle indiqué par `AUTH_USER_MODEL`.
4. En cas de succès, Django ouvre une session : le navigateur reçoit un cookie qui l'identifie aux requêtes suivantes.
5. Django redirige vers `?next=` s'il existe, sinon vers `LOGIN_REDIRECT_URL`, qui vaut `home` (`stock_control/settings.py`).
6. `home_dashboard()` (`apps/core/dashboard_views.py`) choisit le tableau de bord du rôle. Voir [le chapitre suivant](02-tableaux-de-bord.md).

Pour les clients API, la connexion passe par `CustomTokenObtainPairView.post()` (`api/v1/auth/views.py`), sur `POST /api/v1/auth/login/`. Elle renvoie un jeton JWT : une chaîne signée que le client envoie à chaque requête à la place d'un cookie.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| URL `login` | `stock_control/urls.py` | `LoginView.as_view()` |
| Page de connexion | `templates/login.html` | Formulaire `POST` |
| Réglages de connexion | `stock_control/settings.py` | `LOGIN_URL`, `LOGIN_REDIRECT_URL` |
| Modèle du compte | `apps/accounts/models.py` | `User` |
| Connexion API | `api/v1/auth/views.py` | `CustomTokenObtainPairView.post()` |

**Règles à connaître :**

- Un compte avec `is_active=False` ne peut pas se connecter. Il reçoit le même message d'erreur qu'un mauvais mot de passe.
- Aucun rôle n'est vérifié à la connexion. Le rôle agit ensuite, dans chaque vue.

**Pour le tester :** ouvrez `/` sans être connecté. Vous arrivez sur `/login/?next=/`. Connectez-vous avec un compte de rôle `cashier` rattaché à une entreprise : vous arrivez sur `/dashboard/caisse/`.

## Bouton Quitter

**Ce que voit l'utilisateur :** un bouton rouge « Quitter » en haut à droite de chaque page connectée. Sur petit écran, seule son icône s'affiche. Il envoie l'utilisateur vers la page de connexion.

**Ce qui se passe dans le code :**

1. `templates/base.html` affiche un formulaire `POST` dont l'action est `{% url 'logout' %}`.
2. La réponse redirige le navigateur vers `login`.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Bouton « Quitter » | `templates/base.html` | Formulaire de l'en-tête |
| Page de destination | `stock_control/urls.py` | `LoginView.as_view()` |
| Déconnexion des clients API | `api/v1/auth/urls.py`, `api/v1/auth/views.py` | `logout_view()` |

**Règles à connaître :**

- Pour un client API qui envoie son jeton JWT, `logout_view()` attend un `refresh_token`, l'invalide et écrit une entrée `logout` dans `ActionLog`.

**Pour le tester :** connectez-vous avec n'importe quel rôle, puis cliquez sur « Quitter ». La page de connexion s'affiche.

## Rôles et contrôle d'accès

**Ce que voit l'utilisateur :** chaque compte a un rôle. Il décide du menu, du tableau de bord et des pages accessibles. Sur une page interdite, l'utilisateur revient à son accueil avec un message rouge, en général « Vous n'avez pas accès à cette page » ou « Vous n'avez pas les permissions nécessaires. ».

| Rôle | Libellé | Usage principal |
|---|---|---|
| `admin` | Administrator | Direction, gestion complète |
| `owner` | Owner (Propriétaire) | Direction, gestion complète |
| `manager` | Manager (Gérant) | Gestion courante de toute l'entreprise |
| `warehouse_manager` | Warehouse Manager (Gestionnaire Dépôt) | Stock, emplacements, transferts |
| `boutique_manager` | Boutique Manager (Gestionnaire Boutique) | Vente et gestion d'une boutique |
| `stock_manager` | Stock Manager (Gestionnaire de stock) | Opérations de stock |
| `cashier` | Cashier (Caissier) | Caisse et clients |
| `accountant` | Accountant (Comptable/Auditeur) | Finances et rapports |

Le libellé est le texte exact affiché dans les listes de rôles, les filtres et l'en-tête.

**Ce qui se passe dans le code :**

1. Le rôle est stocké dans `User.role`. La liste vient de `User.ROLE_CHOICES` (`apps/accounts/models.py`).
2. Dans les pages web, une vue contrôle le rôle de l'une de ces façons :
   - avec `role_required()`, défini séparément dans `apps/accounts/views.py`, `apps/customers/views.py`, `apps/accounting/views.py`, `apps/products/views.py` et `apps/locations/views.py` ;
   - avec un test direct sur `request.user.role`, par exemple dans `apps/stock/views_frontend.py`, `apps/pos/views_frontend.py` et `apps/reports/views.py` ;
   - avec les listes `TRANSFER_MANAGE_ROLES` et `TRANSFER_VIEW_ROLES` dans `apps/transfers/views.py` ;
   - avec `_guard()` pour les tableaux de bord (`apps/core/dashboard_views.py`).
3. En cas de refus, `role_required()` ajoute un message avec le système `messages` de Django et redirige vers `home`. La copie de `apps/locations/views.py` redirige vers `locations:dashboard`.
4. `templates/base.html` affiche ces messages en haut de la page.
5. Dans l'API, les ViewSets déclarent leurs classes de permission. Les principales sont dans `api/v1/permissions.py` : `IsAdminOrManager`, `IsStockManager`, `IsCashier`, `IsAccountant` et `IsAdminOnly`. Quelques classes sont dans `apps/core/permissions.py`, comme `IsManager` et `CanManageTransfers`.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Liste des rôles | `apps/accounts/models.py` | `User.ROLE_CHOICES` |
| Contrôle dans la gestion des comptes | `apps/accounts/views.py` | `role_required()` |
| Contrôle des transferts | `apps/transfers/views.py` | `TRANSFER_MANAGE_ROLES`, `TRANSFER_VIEW_ROLES` |
| Contrôle des tableaux de bord | `apps/core/dashboard_views.py` | `_guard()`, `DASHBOARD_ROLES` |
| Permissions de l'API | `api/v1/permissions.py` | `IsAdminOrManager`, `IsStockManager`, `IsCashier`, `IsAccountant`, `IsAdminOnly` |
| Permissions complémentaires de l'API | `apps/core/permissions.py` | `IsManager`, `IsStaffOrOwner`, `CanManageStock`, `CanManageTransfers` |

**Règles à connaître :**

- Le menu n'accorde aucun droit : c'est la vue qui décide. Masquer un lien ne suffit pas. Toute nouvelle vue doit contrôler le rôle elle-même.
- Une règle ajoutée à une vue web ne s'applique pas à l'API. Il faut la vérifier aux deux endroits.
- Le champ `is_staff` est distinct du rôle. Il ouvre l'accès à `/admin/`.

**Pour le tester :** connectez-vous avec un compte de rôle `cashier`, puis ouvrez `/accounts/users/`. Vous revenez sur `/dashboard/caisse/` avec le message « Vous n'avez pas les permissions nécessaires. ».

## Liste et fiche des utilisateurs

**Ce que voit l'utilisateur :** la page « Utilisateurs » liste les comptes de son entreprise, avec le rôle, l'emplacement et le statut. Il peut chercher par nom ou email, et filtrer par rôle, emplacement ou statut. Un compteur indique le nombre de comptes actifs sur le total affiché. L'icône de détail ouvre une fiche avec les coordonnées, les dates, l'état du compte, l'emplacement et l'entreprise. Une « Légende des Rôles » résume les rôles en bas de la liste.

**Ce qui se passe dans le code :**

1. `accounts:user_list` (`apps/accounts/urls.py`) appelle `user_list()` (`apps/accounts/views.py`).
2. `@login_required` et `role_required()` contrôlent l'accès.
3. La vue charge les `User` de `user.enterprise`, avec `select_related('location')` pour éviter une requête par ligne.
4. Elle applique les paramètres `role`, `location`, `status` et `search`.
5. Elle calcule `total_users` et `active_users`, puis rend `apps/accounts/templates/accounts/user_list.html`.
6. `accounts:user_detail` appelle `user_detail()`. La vue charge le compte, compare les entreprises, puis rend `apps/accounts/templates/accounts/user_detail.html`.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| `accounts:user_list` | `apps/accounts/urls.py`, `apps/accounts/views.py` | `user_list()` |
| `accounts:user_detail` | `apps/accounts/urls.py`, `apps/accounts/views.py` | `user_detail()` |
| Page de liste | `apps/accounts/templates/accounts/user_list.html` | Template |
| Fiche | `apps/accounts/templates/accounts/user_detail.html` | Template |

**Règles à connaître :**

- Rôles autorisés : `admin`, `owner` et `manager`.
- `user_list()` exige que le compte connecté ait une entreprise. Sinon, il revient à `home` avec un message.
- La fiche d'un compte d'une autre entreprise renvoie vers `accounts:user_list` avec un message.
- La liste n'a pas de pagination.
- Les boutons de modification et d'activation sont masqués sur sa propre ligne et sur sa propre fiche. Ils restent visibles sur un compte de rôle supérieur, et la vue refuse l'action au clic.
- Un compte sans emplacement affiche « Non assigné » dans la liste et « Accès à tous les emplacements » sur la fiche.

**Pour le tester :** avec un rôle `manager`, ouvrez `/accounts/users/`. Choisissez le filtre de rôle « Cashier (Caissier) », puis cliquez sur « Filtrer » : seuls les caissiers restent affichés, et le compteur change.

## Création d'un utilisateur

**Ce que voit l'utilisateur :** un formulaire « Nouvel Utilisateur » : identité, rôle, emplacement et mot de passe. Après l'enregistrement, il revient à la liste avec un message vert. En cas d'erreur, le formulaire réapparaît avec les messages et ses champs sont vides. Une icône en forme d'œil affiche ou masque chaque mot de passe.

**Ce qui se passe dans le code :**

1. `accounts:user_create` appelle `user_create()` (`apps/accounts/views.py`).
2. La vue charge les emplacements actifs de l'entreprise, et calcule `available_roles`, la liste des rôles que l'auteur peut attribuer.
3. Sur `POST`, elle valide le nom d'utilisateur, l'email, le mot de passe et le rôle.
4. Elle crée le compte avec `User.objects.create()`, dans l'entreprise de l'auteur. La fonction `make_password` de Django hache le mot de passe : la base stocke une empreinte, pas le texte.
5. Elle redirige vers `accounts:user_list`. Le formulaire vient de `apps/accounts/templates/accounts/user_create.html`.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| `accounts:user_create` | `apps/accounts/urls.py`, `apps/accounts/views.py` | `user_create()` |
| Formulaire | `apps/accounts/templates/accounts/user_create.html` | Template |
| Compte créé | `apps/accounts/models.py` | `User` |

**Règles à connaître :**

- Rôles autorisés : `admin`, `owner` et `manager`.
- `admin` et `owner` peuvent attribuer tous les rôles. `manager` ne peut pas attribuer `admin`, `owner` ni `manager`.
- Le nom d'utilisateur et l'email sont obligatoires et uniques dans toute la base.
- Le mot de passe compte au moins 6 caractères et doit être confirmé.
- L'emplacement est facultatif. Il doit appartenir à l'entreprise de l'auteur. Sinon, le compte est créé sans emplacement. La liste ne propose que les emplacements actifs, et son choix vide s'intitule « Aucun (tous les emplacements) ».
- Le compte créé a `is_active=True` et `is_staff=False`. Un compte `admin` ou `owner` créé ici voit le lien « Admin Django », mais `/admin/` lui présente l'écran de connexion de l'administration, tant que `is_staff` n'est pas activé.

**Pour le tester :** avec un rôle `manager`, ouvrez `/accounts/users/create/`. La liste des rôles ne propose ni `admin`, ni `owner`, ni `manager`. Créez un caissier : il apparaît dans la liste.

## Modification d'un utilisateur

**Ce que voit l'utilisateur :** un formulaire prérempli avec l'email, le prénom, le nom, le téléphone, le rôle et l'emplacement. Un champ facultatif, avec une icône en forme d'œil, permet de définir un nouveau mot de passe. En cas d'erreur, le formulaire réaffiche les valeurs enregistrées, pas celles saisies.

**Ce qui se passe dans le code :**

1. `accounts:user_edit` appelle `user_edit()` (`apps/accounts/views.py`).
2. La vue refuse un compte d'une autre entreprise, sa propre fiche et un compte de rôle supérieur.
3. Elle calcule `available_roles`, comme à la création.
4. Sur `POST`, elle valide les champs, met à jour le `User`, puis appelle `target_user.save()`.
5. Elle redirige vers `accounts:user_list`. Le formulaire vient de `apps/accounts/templates/accounts/user_edit.html`.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| `accounts:user_edit` | `apps/accounts/urls.py`, `apps/accounts/views.py` | `user_edit()` |
| Formulaire | `apps/accounts/templates/accounts/user_edit.html` | Template |

**Règles à connaître :**

- Rôles autorisés : `admin`, `owner` et `manager`.
- L'ordre des rôles est, du plus haut au plus bas : `admin`, `owner`, `manager`, `warehouse_manager`, `boutique_manager`, `stock_manager`, `cashier`, `accountant`. Un compte de rang supérieur à l'auteur ne peut pas être modifié. Par exemple, `owner` ne modifie pas `admin`.
- Le nom d'utilisateur n'est pas modifiable ici.
- Si le nouveau mot de passe est vide, l'ancien est conservé. S'il est renseigné, il compte au moins 6 caractères. Il n'y a pas de champ de confirmation.
- Vider le champ emplacement retire l'emplacement du compte.
- Le formulaire d'un `manager` ne propose pas le rôle `manager`. La fiche d'un autre `manager` se modifie donc avec un compte `admin` ou `owner`.
- Sur sa propre fiche, la vue renvoie vers la liste avec un message qui cite les « paramètres du profil ». Cette page n'existe pas : le projet n'a aucune route de profil.

**Pour le tester :** avec un rôle `admin`, modifiez le téléphone d'un caissier. Le message vert s'affiche et la fiche montre le nouveau numéro. Essayez ensuite d'ouvrir votre propre `/accounts/users/<id>/edit/` : vous revenez à la liste.

## Activation et désactivation d'un compte

**Ce que voit l'utilisateur :** un bouton sur chaque ligne de la liste et sur la fiche. Le navigateur demande une confirmation. Un compte désactivé apparaît atténué dans la liste et ne peut plus se connecter.

**Ce qui se passe dans le code :**

1. Le formulaire de `user_list.html` ou de `user_detail.html` envoie un `POST` vers `accounts:user_toggle_active`.
2. `user_toggle_active()` (`apps/accounts/views.py`) applique les contrôles d'entreprise et de hiérarchie.
3. Elle inverse `target_user.is_active`, enregistre et ajoute un message.
4. Elle redirige vers `accounts:user_list`.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| `accounts:user_toggle_active` | `apps/accounts/urls.py`, `apps/accounts/views.py` | `user_toggle_active()` |
| Boutons | `apps/accounts/templates/accounts/user_list.html`, `apps/accounts/templates/accounts/user_detail.html` | Formulaires `POST` |
| Champ modifié | `apps/accounts/models.py` | `User.is_active` |

**Règles à connaître :**

- Rôles autorisés : `admin`, `owner` et `manager`.
- On ne peut pas se désactiver soi-même, ni agir sur un rôle supérieur, selon l'ordre donné dans la section précédente.
- Seul `POST` change l'état. Un `GET` redirige vers la liste sans rien modifier.
- Ces pages ne suppriment jamais un compte : la désactivation est une suppression logique, c'est-à-dire que la ligne reste en base.

**Pour le tester :** avec un rôle `admin`, désactivez un compte de rôle `cashier`. Essayez de vous connecter avec ce compte : le message d'erreur de connexion s'affiche. Réactivez-le.

## Journal d'actions

**Ce que voit l'utilisateur :** aucune page web dédiée. Le journal se consulte dans l'administration Django, ou par l'API. Une entrée indique l'auteur, le type d'action, l'objet concerné, une description et la date.

**Ce qui se passe dans le code :** ces points du code créent une entrée `ActionLog` (`apps/accounts/models.py`) :

1. `log_sale_action()` (`apps/pos/signals.py`) : création d'une vente et changement de son statut. Un signal est une fonction que Django appelle automatiquement après un événement, ici l'enregistrement d'une `Sale`.
2. `sale_receipt_pdf()` (`apps/pos/views_frontend.py`) et `SaleViewSet.receipt()` (`api/v1/views/pos.py`) : génération d'un reçu PDF.
3. `export_sales_report()`, `export_inventory_report()`, `export_expense_report()` et `export_customer_report()` (`apps/reports/views.py`) : exports Excel des rapports.
4. `CustomTokenObtainPairView.post()` et `logout_view()` (`api/v1/auth/views.py`) : connexion et déconnexion par jeton JWT. La connexion par la page web n'écrit pas d'entrée.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Modèle | `apps/accounts/models.py` | `ActionLog` |
| Consultation dans l'administration | `apps/accounts/admin.py` | `ActionLogAdmin` |
| Consultation par l'API (`/api/v1/action-logs/`) | `api/v1/views/accounts.py` | `ActionLogViewSet` |
| Dernières entrées (`/api/v1/action-logs/recent/`) | `api/v1/views/accounts.py` | `ActionLogViewSet.recent()` |
| Écriture lors d'une vente | `apps/pos/signals.py` | `log_sale_action()` |

**Règles à connaître :**

- Le champ `action_type` accepte `login`, `logout`, `create`, `update` et `delete`. Aucun code actuel n'écrit de valeur `delete`.
- `ActionLogAdmin.has_add_permission()` et `ActionLogAdmin.has_change_permission()` interdisent l'ajout et la modification dans l'administration.
- `ActionLogViewSet` est en lecture seule et demande `IsAdminOrManager`.
- `ActionLog` n'a pas de champ `enterprise` : une entrée se rattache à une entreprise seulement par son auteur.

**Pour le tester :** avec un rôle `cashier`, enregistrez une vente. Avec un compte qui a `is_staff`, ouvrez `/admin/accounts/actionlog/` : une entrée `create` de type `sale` apparaît en tête.

## Entreprise et cloisonnement des données

**Ce que voit l'utilisateur :** il ne voit que les données de son entreprise, et le nom de celle-ci apparaît en pied de page. Certains rôles voient seulement leur emplacement. Il n'existe pas de page web pour gérer les entreprises.

« Multi-entreprise » (multi-tenant) signifie qu'une même installation sert plusieurs sociétés, dont les données restent séparées.

**Ce qui se passe dans le code :**

1. `Enterprise` (`apps/core/models.py`) décrit une société : nom, code unique, coordonnées, devise, logo.
2. `User.enterprise` et `User.location` (`apps/accounts/models.py`) rattachent le compte à une entreprise et à un emplacement. Ces deux champs peuvent être vides.
3. Une vue web lit l'entreprise du compte, puis filtre son queryset, c'est-à-dire sa requête vers la base. Exemple : `Sale.objects.filter(enterprise=enterprise)` dans `patron_dashboard()`.
4. Certaines vues filtrent aussi par `user.location` pour `cashier` et `boutique_manager`. Exemple : `sales_list()` (`apps/pos/views_frontend.py`).
5. Dans l'API, `EnterpriseViewSetMixin` (`apps/core/mixins.py`) applique ce filtre avec `EnterpriseViewSetMixin.get_queryset()`, et renseigne l'entreprise avec `EnterpriseViewSetMixin.perform_create()`. `TransferViewSet`, `LocationViewSet` et `LocationStockViewSet` l'héritent.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Modèle | `apps/core/models.py` | `Enterprise` |
| Administration | `apps/core/admin.py` | `EnterpriseAdmin` |
| API (`/api/v1/enterprises/`) | `api/v1/views/core.py` | `EnterpriseViewSet` |
| Filtre de l'API | `apps/core/mixins.py` | `EnterpriseViewSetMixin`, `EnterpriseQuerySetMixin` |
| Création de données de démonstration | `apps/core/management/commands/setup_enterprise.py`, `apps/core/management/commands/seed_full_data.py` | Commandes `setup_enterprise` et `seed_full_data` |

**Règles à connaître :**

- Le filtre n'est pas automatique dans les vues web : chaque vue doit l'écrire. Pensez-y pour toute nouvelle vue.
- `accounts:user_create` rattache le nouveau compte à l'entreprise de son auteur.
- `UserAdmin` (`apps/accounts/admin.py`) et `UserSerializer` (`api/v1/serializers/accounts.py`) n'exposent ni `enterprise` ni `location`. Pour rattacher un compte existant à une entreprise, il faut une commande ou le shell Django. L'emplacement d'un compte déjà rattaché se change avec `accounts:user_edit`.
- Les classes `EnterpriseAwareModel`, `TimeStampedModel` et `AuditableModel` existent dans `apps/core/models.py`, mais aucun modèle n'en hérite aujourd'hui. Les modèles déclarent leurs champs eux-mêmes.
- `LocationViewSetMixin` et `AuditMixin` (`apps/core/mixins.py`) ne sont utilisés par aucune vue.
- Un compte sans entreprise voit la page simple `templates/home.html` à l'accueil.

**Pour le tester :** avec deux entreprises en base, connectez-vous avec un rôle `admin` de la première. Ouvrez `/accounts/users/<id>/` avec l'identifiant d'un compte de la seconde. Vous revenez à la liste avec le message « Vous n'avez pas accès à cet utilisateur. ».

## Paramètres du magasin

**Ce que voit l'utilisateur :** aucune page web dédiée. Le nom du magasin, son téléphone, son adresse et le pied de page apparaissent sur les reçus PDF. Les réglages se modifient dans l'administration Django ou par l'API.

**Ce qui se passe dans le code :**

1. `StoreSetting` (`apps/settings/models.py`) stocke des paires clé et valeur, dans la table `store_settings`.
2. La commande `seed_data` (`apps/accounting/management/commands/seed_data.py`) crée les clés par défaut sans écraser les clés existantes.
3. `StoreSetting.get_setting()` lit une valeur et renvoie une valeur par défaut si la clé manque.
4. `generate_receipt_pdf()` (`apps/pos/utils/receipt_generator.py`) lit `store_name`, `store_phone`, `store_address` et `receipt_footer`.
5. Le signal de `apps/customers/signals.py` lit `loyalty_program_enabled` et `loyalty_points_rate` pour les points de fidélité.
6. `StoreSettingViewSet` (`api/v1/views/settings.py`) expose le CRUD, c'est-à-dire création, lecture, modification et suppression, ainsi que `StoreSettingViewSet.set_setting()`, qui appelle `StoreSetting.set_setting()`.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Modèle | `apps/settings/models.py` | `StoreSetting`, `StoreSetting.get_setting()`, `StoreSetting.set_setting()` |
| Administration | `apps/settings/admin.py` | `StoreSettingAdmin` |
| API (`/api/v1/settings/`) | `api/v1/views/settings.py` | `StoreSettingViewSet` |
| Valeurs par défaut | `apps/accounting/management/commands/seed_data.py` | Commande `seed_data` |
| Lecture pour les reçus | `apps/pos/utils/receipt_generator.py` | `generate_receipt_pdf()` |

**Règles à connaître :**

- `apps/settings/views.py` ne contient aucune vue et l'application n'a pas de fichier `urls.py` : il n'y a pas de route web.
- `StoreSetting` n'a pas de champ `enterprise` : une même clé vaut pour toutes les entreprises de l'installation.
- L'API demande `IsAdminOrManager`.
- Seules les six clés citées ci-dessus sont lues par le code métier. Les autres clés créées par `seed_data`, comme `language` ou `allow_negative_stock`, n'ont pas d'effet aujourd'hui.

**Pour le tester :** avec un compte qui a `is_staff`, modifiez `receipt_footer` dans `/admin/settings/storesetting/`. Téléchargez ensuite le reçu d'une vente : le nouveau texte apparaît en bas.

## Menu de navigation par rôle

**Ce que voit l'utilisateur :** un menu latéral groupé par thème, qui change selon le rôle. L'en-tête contient l'aide, le thème, le nom de l'utilisateur et « Quitter ». Sur grand écran, le menu peut être réduit. Sur mobile, il s'ouvre avec le bouton à trois barres.

| Groupe | Entrée | Cible | Rôles qui la voient |
|---|---|---|---|
| Tableau de bord | Patron | `dashboards:patron` | `admin`, `owner` |
| Tableau de bord | Gérant | `dashboards:gerant` | `manager`, `boutique_manager` |
| Tableau de bord | Caisse | `dashboards:caisse` | `cashier` |
| Tableau de bord | Comptabilité | `dashboards:comptable` | `accountant` |
| Stock | Stock | `stock:dashboard` | `admin`, `owner`, `manager`, `warehouse_manager`, `boutique_manager`, `stock_manager` |
| Stock | Produits | `products:product_list` | `admin`, `owner`, `manager` |
| Stock | Emplacements | `locations:dashboard` | `admin`, `owner`, `manager`, `warehouse_manager`, `boutique_manager` |
| Stock | Transferts | `transfers:list` | `admin`, `owner`, `manager`, `warehouse_manager`, `boutique_manager` |
| Caisse | Point de vente | `pos:cashier` | `boutique_manager`, `cashier`, `manager` |
| Caisse | Mes ventes | `pos:dashboard` | `boutique_manager`, `cashier`, `manager` |
| Caisse | Sessions Caisse | `accounting:cash_session_list` | `admin`, `owner`, `manager`, `boutique_manager`, `cashier`, `accountant` |
| Caisse | Clients | `customers:customer_list` | `admin`, `owner`, `manager`, `boutique_manager`, `cashier`, `accountant` |
| Caisse | Crédits | `customers:credit_list` | `admin`, `owner`, `manager`, `boutique_manager`, `cashier`, `accountant` |
| Rapports | Rapports | `reports:dashboard` | `admin`, `owner`, `manager`, `accountant` |
| Dépenses | Dépenses | `accounting:expense_list` | `admin`, `owner`, `manager`, `boutique_manager`, `accountant` |
| Utilisateurs | Utilisateurs | `accounts:user_list` | `admin`, `owner`, `manager` |
| Configuration | Admin Django | `/admin/` | `admin`, `owner` |
| Configuration | Thème clair ou sombre | Bouton sans page | Tous |

**Ce qui se passe dans le code :**

1. Chaque page connectée hérite de `templates/base.html`, qui dessine le menu si `user.is_authenticated` est vrai.
2. Chaque entrée est entourée d'une condition, comme `{% if user.role in 'admin,owner,manager' %}`.
3. La variable `vn` contient `request.resolver_match.view_name`, le nom de la route courante. Elle sert à surligner l'entrée active.
4. Le thème et l'état réduit du menu sont gardés dans `localStorage`, un petit stockage du navigateur. Alpine.js lit ces valeurs dans `x-data`.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Menu latéral et en-tête | `templates/base.html` | Conditions `{% if user.role in ... %}` |
| Tests du menu | `tests/test_role_dashboards.py` | `test_owner_sees_all_groups()`, `test_cashier_groups_are_limited()` |

**Règles à connaître :**

- `user.role in 'a,b,c'` teste une portion de texte, pas un élément de liste. Comme `manager` est contenu dans `boutique_manager`, la condition `'boutique_manager,cashier'` est vraie pour `manager`. C'est pourquoi `manager` voit « Point de vente » et « Mes ventes ».
- `cashier_view()` (`apps/pos/views_frontend.py`) n'accepte que `boutique_manager` et `cashier`. Un `manager` qui clique sur « Point de vente » revient à son accueil avec un message d'erreur.
- `stock_manager` et `accountant` peuvent ouvrir `transfers:list`, mais le menu ne leur propose pas cette entrée.
- `pos:sales_list` n'a pas d'entrée dans le menu. On l'atteint depuis les tableaux de bord.
- L'entrée « Admin Django » mène à une page qui demande aussi `is_staff`.

**Pour le tester :** connectez-vous successivement avec les rôles `cashier` et `owner`. Le `cashier` voit les groupes Tableau de bord, Caisse et Configuration. Le `owner` voit aussi Stock, Rapports, Dépenses et Utilisateurs.

## Visite guidée

**Ce que voit l'utilisateur :** à la première ouverture d'une page connectée, une visite pas à pas se lance après une seconde. Elle présente le menu, le thème et l'aide, puis les modules de son rôle. Le bouton « ? » de l'en-tête la relance.

| Étape | Rôles concernés |
|---|---|
| `welcome`, `navigation`, `theme`, `help`, `complete` | Tous |
| `pos-intro` | `cashier`, `boutique_manager`, `manager` |
| `stock-intro` | `admin`, `owner`, `manager`, `warehouse_manager`, `boutique_manager`, `stock_manager` |
| `transfers-intro` | `admin`, `owner`, `manager`, `warehouse_manager`, `boutique_manager` |
| `reports-intro` | `admin`, `owner`, `manager`, `accountant` |
| `customers-intro` | `admin`, `owner`, `manager`, `boutique_manager`, `cashier`, `accountant` |
| `admin-intro` | `admin`, `owner`, `manager` |

**Ce qui se passe dans le code :**

1. `templates/base.html` charge la bibliothèque Shepherd.js depuis un CDN, un serveur public de fichiers.
2. À la fin du chargement de la page, un minuteur d'une seconde lit la clé `tour_completed_<id>` dans `localStorage`.
3. Si la clé est absente, `startTour()` appelle `createTour()`, qui construit les étapes, puis démarre la visite.
4. Django choisit les étapes au moment du rendu, avec les mêmes conditions `{% if user.role in ... %}` que le menu.
5. La fin ou l'annulation de la visite écrit la clé dans `localStorage`.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Construction de la visite | `templates/base.html` | `createTour()` |
| Démarrage | `templates/base.html` | `startTour()` |
| Bouton « ? » | `templates/base.html` | Élément `tour-help-btn` |

**Règles à connaître :**

- Rien n'est stocké côté serveur. Un autre navigateur, ou un `localStorage` vidé, relance la visite.
- La visite n'existe que sur les pages qui héritent de `templates/base.html`, pour un compte connecté.
- L'étape `admin-intro` cite « Admin Django » aussi pour `manager`, alors que son menu n'a pas cette entrée.

**Pour le tester :** connectez-vous avec un rôle `stock_manager` dans une fenêtre de navigation privée. La visite démarre et contient l'étape « Gestion de Stock », mais pas « Transferts ».

## Guide public

**Ce que voit l'utilisateur :** une documentation fonctionnelle, ouverte dans un nouvel onglet depuis le lien « Comment fonctionne l'application ? — Guide » de la page de connexion. Elle décrit le concept, les rôles, les parcours et une démonstration guidée. Aucune connexion n'est nécessaire.

**Ce qui se passe dans le code :**

1. `stock_control/urls.py` associe `/guide/` à `functional_documentation()`, sous le nom `functional_documentation`.
2. `functional_documentation()` (`apps/core/views.py`) lit `docs/functional_documentation.html`.
3. Elle renvoie le fichier tel quel, sans passer par les templates Django, car il contient des accolades JavaScript que Django essaierait d'interpréter.
4. Si le fichier manque, elle renvoie une erreur 404.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| URL `functional_documentation` | `stock_control/urls.py` | `functional_documentation()` |
| Vue | `apps/core/views.py` | `functional_documentation()` |
| Contenu | `docs/functional_documentation.html` | Fichier HTML autonome |
| Lien d'accès | `templates/login.html` | Lien sous le formulaire |

**Règles à connaître :**

- Le fichier est écrit à la main. Il ne suit pas le code automatiquement : en cas de différence, le code fait foi.
- Le menu des pages connectées n'a pas de lien vers `/guide/`.

**Pour le tester :** sans être connecté, ouvrez `/guide/`. La page « Documentation Fonctionnelle » s'affiche sans redirection vers `/login/`.

## À retenir

- La connexion web utilise la session Django. L'API utilise des jetons JWT.
- Le rôle se contrôle dans chaque vue : le menu de `templates/base.html` ne protège rien.
- Les comptes se gèrent avec les cinq routes `accounts:*`, et se désactivent au lieu d'être supprimés.
- Le filtre par entreprise s'écrit dans chaque vue web. `Enterprise` et `StoreSetting` n'ont pas de page web.
- `ActionLog` enregistre les ventes, les reçus, les exports et les connexions JWT. Il se consulte dans l'administration ou par l'API.
