# API REST

L'API REST donne accès aux mêmes données que les pages web, mais en JSON. Elle sert à un développeur ou à une application externe, par exemple une application mobile. Elle utilise Django REST Framework (DRF), une bibliothèque qui transforme les modèles Django en adresses web. Toutes ses adresses commencent par `/api/v1/`.

## Sommaire

- [Organisation de l'API](#organisation-de-lapi)
- [Permissions et rôles](#permissions-et-rôles)
- [Connexion JWT](#connexion-jwt)
- [Documentation Swagger](#documentation-swagger)
- [Les 22 ressources](#les-22-ressources)
- [Exemple complet : créer une vente](#exemple-complet--créer-une-vente)
- [Annuler ou rembourser une vente](#annuler-ou-rembourser-une-vente)
- [Paramètres des actions personnalisées](#paramètres-des-actions-personnalisées)
- [À retenir](#à-retenir)

## Organisation de l'API

**Ce que voit l'utilisateur :** le développeur envoie une requête HTTP à une adresse, par exemple `GET /api/v1/products/`. Il reçoit du JSON. Une liste est découpée en pages de 20 éléments, avec les clés `count`, `next`, `previous` et `results`. Avec un jeton, `GET /api/v1/` liste les préfixes de toutes les ressources.

Trois mots reviennent partout :

- Une **ressource** est un type de données accessible par l'API, comme `sales`.
- Un **ViewSet** est une classe qui regroupe les opérations d'une ressource : lister, lire, créer, modifier, supprimer.
- Un **serializer** convertit un objet Python en JSON, et valide le JSON reçu.

**Ce qui se passe dans le code :**

1. `stock_control/urls.py` envoie tout ce qui commence par `/api/v1/` vers `api/v1/urls.py`.
2. `api/v1/urls.py` crée un `DefaultRouter`. Chaque appel à `router.register` relie un préfixe d'adresse à un ViewSet.
3. Le routeur crée les routes standard : `GET` et `POST` sur `/api/v1/sales/`, puis `GET`, `PUT`, `PATCH` et `DELETE` sur `/api/v1/sales/<id>/`.
4. `JWTAuthentication`, déclarée dans `REST_FRAMEWORK` de `stock_control/settings.py`, identifie l'utilisateur grâce à son jeton.
5. DRF appelle `has_permission()` sur chaque classe de permission du ViewSet.
6. Le ViewSet choisit son serializer, souvent avec `get_serializer_class()`, par exemple `SaleViewSet.get_serializer_class()`.
7. Le serializer valide les données, puis le ViewSet enregistre ou lit le modèle.
8. Le ViewSet renvoie la réponse en JSON.

Une méthode décorée avec `@action` ajoute une route : c'est une **action personnalisée**. Son nom devient la fin de l'adresse, avec ses tirets bas. Exemple : `ProductViewSet.low_stock()` répond à `/api/v1/products/low_stock/`.

Les paramètres d'adresse suivants fonctionnent sur les listes, selon les champs que déclare chaque ViewSet :

| Paramètre | Rôle | Exemple |
|---|---|---|
| `?search=` | Recherche texte, via `search_fields` | `/api/v1/products/?search=6000` |
| `?ordering=` | Tri, via `ordering_fields` | `/api/v1/expenses/?ordering=-amount` |
| Nom de champ | Filtre exact, via `filterset_fields` | `/api/v1/sales/?status=completed` |
| `?page=` | Numéro de page | `/api/v1/sales/?page=2` |

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Inclusion de l'API | `stock_control/urls.py` | `urlpatterns` |
| Routeur | `api/v1/urls.py` | `router` |
| Réexport des ViewSets | `api/v1/views/__init__.py` | `__all__` |
| ViewSets, un fichier par domaine | `api/v1/views/` | `SaleViewSet`, `ProductViewSet`... |
| Serializers, un fichier par domaine | `api/v1/serializers/` | `SaleSerializer`, `ProductSerializer`... |
| Permissions | `api/v1/permissions.py`, `apps/core/permissions.py` | `IsCashier`, `IsManager`... |
| Connexion | `api/v1/auth/views.py`, `api/v1/auth/urls.py` | `CustomTokenObtainPairView` |
| Réglages DRF et JWT | `stock_control/settings.py` | `REST_FRAMEWORK`, `SIMPLE_JWT` |

**Règles à connaître :**

- Les dates sortent au format `JJ/MM/AAAA` (`DATE_FORMAT` et `DATETIME_FORMAT`). En entrée, envoyez-les au format `AAAA-MM-JJ`.
- Les actions personnalisées ne paginent pas leur réponse, sauf `StockMovementViewSet.movement_history()`. Elles renvoient une liste JSON simple ou un seul objet, sans les clés `count` et `results`.
- `DELETE` efface vraiment la ligne, y compris pour `products` et `customers` : l'API n'utilise pas `is_active` pour supprimer. Si une clé étrangère `RESTRICT` protège la ligne, comme pour un produit qui a des mouvements, la réponse est une erreur 500.
- Corriger une règle dans une vue web ne la corrige pas dans l'API : les deux portes d'entrée ont leur propre code.

**Pour le tester :** connectez-vous avec un rôle `manager` (voir [Connexion JWT](#connexion-jwt)), puis appelez `GET /api/v1/categories/`. La réponse contient `count` et `results`.

## Permissions et rôles

**Ce que voit l'utilisateur :** sans jeton, l'API répond 401. Avec un jeton dont le rôle n'est pas autorisé, elle répond 403. Font exception `/api/v1/auth/login/`, `/api/v1/auth/refresh/`, `/api/v1/auth/test/` et les trois adresses de documentation, ouvertes sans jeton.

**Ce qui se passe dans le code :**

1. DRF lit `permission_classes` sur le ViewSet, ou sur l'action si `@action` en déclare.
2. Si le ViewSet définit `get_permissions()`, cette méthode décide selon l'action : c'est le cas de `UserViewSet.get_permissions()` et de `CustomerViewSet.get_permissions()`.
3. DRF appelle `has_permission()` de chaque classe, qui compare `request.user.role` à sa liste de rôles.

Le projet a deux fichiers de permissions. `apps/core/permissions.py` contient aussi une classe `IsCashier`, distincte de celle de `api/v1/permissions.py` et qu'aucune vue n'utilise. Les classes utilisées par les ressources sont les suivantes :

| Classe | Fichier | Rôles acceptés |
|---|---|---|
| `IsAdminOnly` | `api/v1/permissions.py` | `admin`, `owner` |
| `IsAdminOrManager` | `api/v1/permissions.py` | `admin`, `owner`, `manager` |
| `IsAccountant` | `api/v1/permissions.py` | `admin`, `owner`, `manager` ; `accountant` en lecture seule |
| `IsStockManager` | `api/v1/permissions.py` | `admin`, `owner`, `manager`, `warehouse_manager`, `boutique_manager`, `stock_manager` |
| `IsCashier` | `api/v1/permissions.py` | `admin`, `owner`, `manager`, `boutique_manager`, `cashier` |
| `IsStaffOrOwner` | `apps/core/permissions.py` | Compte `is_staff`, ou rôle `owner` |
| `IsManager` | `apps/core/permissions.py` | `owner`, `manager`, `warehouse_manager`, `boutique_manager` |
| `CanManageStock` | `apps/core/permissions.py` | `owner`, `manager`, `warehouse_manager`, `stock_manager` |
| `CanManageTransfers` | `apps/core/permissions.py` | `owner`, `manager`, `warehouse_manager`, `boutique_manager` |
| `CanReceiveTransfers` | `apps/core/permissions.py` | `owner`, `manager`, `warehouse_manager`, `boutique_manager` |

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Permissions par rôle | `api/v1/permissions.py` | `IsAdminOrManager`, `IsCashier`... |
| Permissions par métier | `apps/core/permissions.py` | `IsManager`, `CanManageTransfers`... |
| Permissions selon l'action | `api/v1/views/accounts.py` | `UserViewSet.get_permissions()` |
| Permissions selon l'action | `api/v1/views/customers.py` | `CustomerViewSet.get_permissions()` |
| Filtrage par entreprise | `apps/core/mixins.py` | `EnterpriseViewSetMixin` |

**Règles à connaître :**

- Le rôle `admin` ne figure pas dans `IsManager`, `CanManageStock`, `CanManageTransfers` ni `CanReceiveTransfers`. Il reçoit donc 403 sur `locations`, `location-stocks`, `transfers` et `transfer-items`.
- `IsAccountant` ne laisse passer ni `cashier`, ni les rôles de stock. Un `cashier` reçoit donc 403 sur `/api/v1/products/`. Il doit connaître l'identifiant du produit pour créer une vente.
- `UserViewSet.roles()` n'est pas dans la liste de `UserViewSet.get_permissions()` : `/api/v1/users/roles/` répond 403 à un `manager`.

**Pour le tester :** connectez-vous en `cashier`, puis appelez `GET /api/v1/products/` : la réponse est 403. Avec un jeton `manager`, la même adresse répond 200.

## Connexion JWT

**Ce que voit l'utilisateur :** le développeur envoie son identifiant et son mot de passe. Il reçoit deux jetons, puis ajoute le jeton d'accès à chaque requête. Un JWT (JSON Web Token) est un texte signé par le serveur, qui prouve l'identité de son porteur sans session.

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "VOTRE_UTILISATEUR", "password": "VOTRE_MOT_DE_PASSE"}'
```

Réponse :

```json
{
  "refresh": "eyJhbGciOi...",
  "access": "eyJhbGciOi...",
  "user": {
    "id": 18,
    "username": "VOTRE_UTILISATEUR",
    "email": "...",
    "full_name": "...",
    "role": "cashier",
    "role_display": "Cashier (Caissier)"
  }
}
```

Utilisez ensuite le jeton `access` :

```bash
curl http://127.0.0.1:8000/api/v1/auth/me/ \
  -H "Authorization: Bearer VOTRE_JETON_ACCESS"
```

**Ce qui se passe dans le code :**

1. `api/v1/auth/urls.py` relie `/api/v1/auth/login/` à `CustomTokenObtainPairView`.
2. `CustomTokenObtainPairView.post()` laisse SimpleJWT vérifier les identifiants.
3. `CustomTokenObtainPairSerializer.validate()` ajoute le bloc `user` à la réponse.
4. `CustomTokenObtainPairSerializer.get_token()` ajoute `role`, `username` et `email` dans le contenu du jeton.
5. Si la réponse est 200, `CustomTokenObtainPairView.post()` crée un `ActionLog` de type `login` et met à jour `last_login`.
6. Aux requêtes suivantes, `JWTAuthentication` lit l'en-tête `Authorization: Bearer ...` et retrouve l'utilisateur.

Les autres adresses de connexion :

| Adresse | Méthode | Rôle |
|---|---|---|
| `/api/v1/auth/refresh/` | `POST` | Reçoit `{"refresh": "..."}`, renvoie un nouveau jeton `access` |
| `/api/v1/auth/logout/` | `POST` | Reçoit `{"refresh_token": "..."}` avec le jeton `access` en en-tête, et invalide le jeton `refresh`. Sans en-tête, la réponse est une redirection vers la page de connexion |
| `/api/v1/auth/me/` | `GET` | Renvoie le profil de l'utilisateur connecté |
| `/api/v1/auth/test/` | `POST` | Indique le nom reconnu par le jeton, ou `Anonymous` |

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Routes de connexion | `api/v1/auth/urls.py` | `urlpatterns` |
| Connexion | `api/v1/auth/views.py` | `CustomTokenObtainPairView.post()` |
| Contenu du jeton | `api/v1/auth/views.py` | `CustomTokenObtainPairSerializer.get_token()` |
| Déconnexion | `api/v1/auth/views.py` | `logout_view()` |
| Profil | `api/v1/auth/views.py` | `current_user_view()` |
| Test du jeton | `api/v1/auth/views.py` | `test_token_view()` |
| Durée des jetons | `stock_control/settings.py` | `SIMPLE_JWT` |

**Règles à connaître :**

- Le jeton `access` dure 1 heure, le jeton `refresh` dure 7 jours.
- `/api/v1/auth/refresh/` renvoie seulement `access` : le jeton `refresh` ne change pas (`ROTATE_REFRESH_TOKENS` vaut `False`).
- Sans `refresh_token`, `logout_view()` répond 400. Après une déconnexion réussie, ce jeton `refresh` est refusé avec une réponse 401.
- Le jeton `access` n'est pas invalidé par la déconnexion : il reste valable jusqu'à son expiration.
- Un mauvais mot de passe donne 401, et aucun `ActionLog` n'est créé.

**Pour le tester :** lancez le `curl` de connexion avec un compte de rôle `cashier`, puis appelez `/api/v1/auth/me/`. Le champ `role` doit valoir `cashier`.

## Documentation Swagger

**Ce que voit l'utilisateur :** une page web liste toutes les routes de l'API, leurs champs et leurs réponses. On peut y essayer une requête directement. Swagger est un outil qui affiche cette documentation à partir d'un fichier de description appelé schéma OpenAPI.

Adresses en local :

| Adresse | Nom de route | Contenu |
|---|---|---|
| `http://127.0.0.1:8000/api/v1/docs/` | `swagger-ui` | Page Swagger, pour lire et essayer |
| `http://127.0.0.1:8000/api/v1/redoc/` | `redoc` | Page ReDoc, pour lire |
| `http://127.0.0.1:8000/api/v1/schema/` | `schema` | Schéma OpenAPI brut |

**Ce qui se passe dans le code :**

1. `api/v1/urls.py` déclare les trois routes avec `SpectacularAPIView`, `SpectacularSwaggerView` et `SpectacularRedocView`, de la bibliothèque drf-spectacular.
2. `DEFAULT_SCHEMA_CLASS` de `stock_control/settings.py` désigne `AutoSchema`, qui lit les ViewSets et les serializers.
3. `SPECTACULAR_SETTINGS` donne le titre, la version et les préfixes du schéma.
4. Swagger charge le schéma depuis la route `schema`, puis affiche la page.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Routes de documentation | `api/v1/urls.py` | `SpectacularAPIView`, `SpectacularSwaggerView`, `SpectacularRedocView` |
| Réglages | `stock_control/settings.py` | `SPECTACULAR_SETTINGS` |

**Règles à connaître :**

- Pour essayer une route protégée, cliquez sur « Authorize » et collez le jeton `access`, sans le mot `Bearer`.
- Swagger charge ses fichiers depuis un CDN (un serveur public de fichiers) : sans Internet, la page ne s'affiche pas correctement.
- Le schéma est généré automatiquement. `logout_view()`, `current_user_view()` et `test_token_view()` n'ayant pas de serializer, leurs routes y figurent sans description de leur corps. Lisez le tableau de [Connexion JWT](#connexion-jwt) pour ces routes.

**Pour le tester :** lancez `python manage.py runserver` et ouvrez `/api/v1/docs/`. Déroulez `sales`, puis vérifiez la présence de `today_summary`.

## Les 22 ressources

**Ce que voit l'utilisateur :** chaque ligne du tableau est un préfixe d'adresse. Sauf mention contraire, il offre `GET`, `POST`, `PUT`, `PATCH` et `DELETE`. La colonne « Actions » indique les routes en plus. Une action marquée `<id>/` s'applique à un objet précis, par exemple `/api/v1/sales/<id>/cancel/`.

Tous les fichiers de vues sont dans `api/v1/views/`, tous les serializers dans `api/v1/serializers/`.

| Ressource | URL | Vue | Serializers | Permission | Actions | À quoi elle sert |
|---|---|---|---|---|---|---|
| `enterprises` | `/api/v1/enterprises/` | `EnterpriseViewSet` | `api/v1/serializers/core.py` | `IsStaffOrOwner` | `<id>/activate` (POST), `<id>/deactivate` (POST) | Gérer les entreprises. Montre l'entreprise de l'utilisateur. |
| `users` | `/api/v1/users/` | `UserViewSet` | `api/v1/serializers/accounts.py` | `IsAdminOrManager` pour lire et modifier ; `IsAdminOnly` pour créer, supprimer et `roles` | `roles` (GET) | Gérer les comptes et leurs rôles. |
| `action-logs` | `/api/v1/action-logs/` | `ActionLogViewSet` (lecture seule) | `api/v1/serializers/accounts.py` | `IsAdminOrManager` | `recent` (GET) | Lire le journal d'actions. `recent` donne les 50 dernières entrées. |
| `locations` | `/api/v1/locations/` | `LocationViewSet` | `api/v1/serializers/locations.py` | `IsManager` | `warehouses`, `boutiques`, `<id>/stock`, `<id>/low_stock` (GET) | Gérer les dépôts et les boutiques, et lire leur stock. |
| `location-stocks` | `/api/v1/location-stocks/` | `LocationStockViewSet` | `api/v1/serializers/locations.py` | `CanManageStock` | `low_stock_alerts`, `out_of_stock` (GET) | Lire le stock par emplacement. Voir les règles. |
| `transfers` | `/api/v1/transfers/` | `TransferViewSet` | `api/v1/serializers/transfers.py` | `CanManageTransfers` ; `CanReceiveTransfers` pour `receive` | `pending`, `in_transit`, `incoming`, `outgoing` (GET) ; `<id>/send`, `<id>/receive`, `<id>/cancel` (POST) | Créer un transfert entre emplacements et suivre son cycle. |
| `transfer-items` | `/api/v1/transfer-items/` | `TransferItemViewSet` | `api/v1/serializers/transfers.py` | `CanManageTransfers` | Aucune | Gérer les lignes d'un transfert. |
| `categories` | `/api/v1/categories/` | `CategoryViewSet` | `api/v1/serializers/products.py` | `IsAccountant` | Aucune | Gérer les catégories de produits. |
| `products` | `/api/v1/products/` | `ProductViewSet` | `api/v1/serializers/products.py` | `IsAccountant` | `low_stock`, `popular`, `<id>/stock_history` (GET) | Gérer le catalogue. `popular` liste les produits actifs marqués `is_popular`. |
| `product-packagings` | `/api/v1/product-packagings/` | `ProductPackagingViewSet` | `api/v1/serializers/products.py` | `IsAdminOrManager` | Aucune | Gérer les conditionnements d'un produit, comme un carton. |
| `stock` | `/api/v1/stock/` | `StockViewSet` | `api/v1/serializers/stock.py` | `IsStockManager` | `low_stock_alerts` (GET) | Lire les lignes de `Stock` et le stock faible. |
| `stock-movements` | `/api/v1/stock-movements/` | `StockMovementViewSet` | `api/v1/serializers/stock.py` | `IsStockManager` | `movement_history` (GET) | Créer et lire les entrées et sorties. C'est la bonne façon de changer une quantité. |
| `customers` | `/api/v1/customers/` | `CustomerViewSet` | `api/v1/serializers/customers.py` | `IsCashier` pour lire et créer ; `IsAdminOrManager` pour modifier et supprimer | `top_customers`, `with_credits` (GET) | Gérer les clients. `top_customers` donne les 10 plus gros acheteurs actifs. |
| `customer-credits` | `/api/v1/customer-credits/` | `CustomerCreditViewSet` | `api/v1/serializers/customers.py` | `IsAdminOrManager` | `overdue` (GET) | Lire et gérer les dettes des clients. |
| `credit-payments` | `/api/v1/credit-payments/` | `CreditPaymentViewSet` | `api/v1/serializers/customers.py` | `IsAdminOrManager` | Aucune | Enregistrer un remboursement de dette. |
| `sales` | `/api/v1/sales/` | `SaleViewSet` | `api/v1/serializers/pos.py` | `IsCashier` ; `IsAdminOrManager` pour `cancel` et `refund` | `today_summary`, `<id>/receipt` (GET) ; `<id>/cancel`, `<id>/refund` (POST) | Créer et lire les ventes. |
| `sale-items` | `/api/v1/sale-items/` | `SaleItemViewSet` (lecture seule) | `api/v1/serializers/pos.py` | `IsCashier` | Aucune | Lire les lignes de vente, filtrées par `sale` ou `product`. |
| `expense-categories` | `/api/v1/expense-categories/` | `ExpenseCategoryViewSet` | `api/v1/serializers/accounting.py` | `IsAccountant` | Aucune | Gérer les catégories de dépenses. |
| `expenses` | `/api/v1/expenses/` | `ExpenseViewSet` | `api/v1/serializers/accounting.py` | `IsAccountant` | `summary` (GET) | Gérer les dépenses. `summary` donne le total et le nombre. |
| `cash-register-sessions` | `/api/v1/cash-register-sessions/` | `CashRegisterSessionViewSet` | `api/v1/serializers/accounting.py` | `IsAdminOrManager` | `current_session` (GET) ; `<id>/close_session` (POST) | Ouvrir, lire et fermer une session de caisse. |
| `daily-summaries` | `/api/v1/daily-summaries/` | `DailySummaryViewSet` | `api/v1/serializers/accounting.py` | `IsAccountant` | `daily_summary` (GET) | Lire les résumés journaliers créés par `generate_daily_summary`. |
| `settings` | `/api/v1/settings/` | `StoreSettingViewSet` | `api/v1/serializers/settings.py` | `IsAdminOrManager` | `get_setting`, `all_settings` (GET) ; `set_setting` (POST) | Lire et modifier les paramètres du magasin. |

**Ce qui se passe dans le code :**

1. `api/v1/urls.py` importe chaque ViewSet depuis `api/v1/views/__init__.py`.
2. `router.register` associe le préfixe au ViewSet et lui donne un `basename`, utilisé par les noms de routes comme `sale-list` ou `sale-detail`.
3. La requête atteint le ViewSet, qui applique ses permissions, ses filtres, puis son serializer.
4. Trois ViewSets héritent de `EnterpriseViewSetMixin` : `LocationViewSet`, `LocationStockViewSet` et `TransferViewSet`. `EnterpriseQuerySetMixin.get_enterprise_queryset()` limite alors leurs résultats à l'entreprise de l'utilisateur.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Liste des ressources | `api/v1/urls.py` | `router` |
| Entreprises | `api/v1/views/core.py` | `EnterpriseViewSet` |
| Utilisateurs et journal | `api/v1/views/accounts.py` | `UserViewSet`, `ActionLogViewSet` |
| Emplacements | `api/v1/views/locations.py` | `LocationViewSet`, `LocationStockViewSet` |
| Transferts | `api/v1/views/transfers.py` | `TransferViewSet`, `TransferItemViewSet` |
| Produits | `api/v1/views/products.py` | `CategoryViewSet`, `ProductViewSet`, `ProductPackagingViewSet` |
| Stock | `api/v1/views/stock.py` | `StockViewSet`, `StockMovementViewSet` |
| Clients | `api/v1/views/customers.py` | `CustomerViewSet`, `CustomerCreditViewSet`, `CreditPaymentViewSet` |
| Ventes | `api/v1/views/pos.py` | `SaleViewSet`, `SaleItemViewSet` |
| Comptabilité | `api/v1/views/accounting.py` | `ExpenseCategoryViewSet`, `ExpenseViewSet`, `CashRegisterSessionViewSet`, `DailySummaryViewSet` |
| Paramètres | `api/v1/views/settings.py` | `StoreSettingViewSet` |

**Règles à connaître :**

*Produits et stock*

- `products` : `ProductListSerializer.get_stock_quantity()` et `ProductSerializer.get_stock_quantity()` renvoient toujours 0, et `ProductSerializer.get_is_low_stock()` renvoie toujours `False`. `Product.stock_info` est en effet une relation vers plusieurs lignes, pas un objet unique. Lisez les quantités sur `stock`.
- `products` : `ProductViewSet.low_stock()` renvoie toujours une liste vide, pour la même raison. Utilisez `/api/v1/stock/low_stock_alerts/`.
- `location-stocks` : pour un utilisateur rattaché à une entreprise, sauf superuser, toutes les routes répondent 500. `EnterpriseQuerySetMixin.get_enterprise_queryset()` filtre sur `enterprise`, un champ que `LocationStock` n'a pas. Pour lire le stock d'un emplacement, utilisez `/api/v1/locations/<id>/stock/`.
- `stock` : écrire directement sur cette ressource change `Stock`, sans mouvement ni mise à jour de `LocationStock`. Pour changer une quantité, créez un `stock-movements`.
- `stock-movements` : envoyez `location` si le produit a plusieurs lignes `Stock`. Sinon, `StockMovement.save()` échoue avec `MultipleObjectsReturned` et la réponse est 500.

*Champs obligatoires ou absents*

- `credit-payments` : `user` est obligatoire dans le JSON, puis `CreditPaymentViewSet.perform_create()` le remplace par l'utilisateur connecté.
- `credit-payments` : le montant n'est pas comparé au reste dû, contrairement à `record_payment()`. Un montant trop élevé solde le crédit et retire tout ce montant du solde du client, sans descendre sous 0.
- `locations` : `enterprise` est obligatoire dans le JSON, puis `LocationViewSet.perform_create()` le remplace par l'entreprise de l'utilisateur.
- `cash-register-sessions` : `user` et `opened_at` sont obligatoires pour créer une session.
- `users` : `UserSerializer` n'expose ni `enterprise` ni `location`. Un compte créé par l'API n'a donc ni entreprise ni emplacement.
- `products`, `categories`, `customers`, `sales`, `stock-movements`, `expense-categories`, `expenses` et `cash-register-sessions` ne renseignent pas `enterprise` à la création : le champ reste vide. `expenses` et `cash-register-sessions` n'exposent pas non plus `location`.
- Conséquence : pour un utilisateur rattaché à une entreprise, ces ventes, mouvements, dépenses et sessions n'apparaissent pas sur les pages web, qui filtrent par entreprise.

*Autres comportements*

- `transfers` : la réponse à `POST` contient seulement `source_location`, `destination_location` et `notes`, sans identifiant. Retrouvez le transfert avec `GET /api/v1/transfers/pending/`.
- `transfers` : `TransferViewSet.send()` et `TransferViewSet.receive()` passent par `Transfer.send()` et `Transfer.receive()`, qui créent les mouvements. Un stock insuffisant à l'envoi donne une réponse 400.
- `transfers` : le corps de `receive` est facultatif : `{"items": [{"id": 1, "received_quantity": "2"}]}`. Un `id` inconnu est ignoré.
- `transfers` : `cancel` exige `{"reason": "..."}`.
- `cash-register-sessions` : `CashRegisterSessionViewSet.close_session()` exige `closing_balance`. Sans `expected_balance`, ce solde prend la valeur de `closing_balance`, et `difference` vaut 0.
- `cash-register-sessions` : `current_session` répond 404 si l'utilisateur n'a pas de session ouverte.
- `daily-summaries` : `DailySummaryViewSet.daily_summary()` ne crée rien. Elle répond 404 si aucun résumé n'existe pour la date, et 400 si la date est mal écrite. S'il y en a plusieurs, elle renvoie seulement le premier.
- `settings` : `StoreSettingViewSet.set_setting()` crée la clé si elle n'existe pas, sinon remplace sa valeur.

**Pour le tester :** avec un jeton `stock_manager`, appelez `GET /api/v1/stock/low_stock_alerts/`, puis `GET /api/v1/customers/`. La première adresse répond 200, la seconde 403, car `IsCashier` n'accepte pas ce rôle.

## Exemple complet : créer une vente

**Ce que voit l'utilisateur :** le développeur envoie les produits et le mode de paiement. L'API calcule les montants, attribue un numéro de vente et retire la quantité du stock.

Étape 1, obtenez un jeton avec un compte `cashier` (voir [Connexion JWT](#connexion-jwt)).

Étape 2, envoyez la vente. Ici, le produit 12 coûte 1 000 FB :

```bash
curl -X POST http://127.0.0.1:8000/api/v1/sales/ \
  -H "Authorization: Bearer VOTRE_JETON_ACCESS" \
  -H "Content-Type: application/json" \
  -d '{
    "payment_method": "cash",
    "amount_paid": "5000",
    "items": [
      {"product": 12, "quantity": "3"}
    ]
  }'
```

Réponse 201 :

```json
{
  "sale_number": "VNT-20261030-0001",
  "customer": null,
  "subtotal": "3000.00",
  "discount_amount": "0.00",
  "discount_percent": "0.00",
  "tax_amount": "0.00",
  "total_amount": "3000.00",
  "amount_paid": "5000.00",
  "change_amount": "2000.00",
  "payment_method": "cash",
  "payment_reference": null,
  "status": "completed",
  "notes": null,
  "items": [
    {
      "product": 12,
      "quantity": "3.000",
      "unit_price": "1000.00",
      "discount_amount": "0.00",
      "tax_rate": "0.00",
      "tax_amount": "0.00",
      "total_price": "3000.00"
    }
  ]
}
```

Cette réponse ne contient pas `id`. Pour lire la vente ensuite, cherchez-la par son numéro : `GET /api/v1/sales/?search=VNT-20261030-0001`.

**Ce qui se passe dans le code :**

1. `IsCashier.has_permission()` vérifie le rôle.
2. `SaleViewSet.get_serializer_class()` choisit `SaleCreateSerializer`, car l'action est `create`.
3. `SaleItemCreateSerializer.validate_quantity()` refuse une quantité nulle ou négative, avec une réponse 400.
4. `SaleViewSet.perform_create()` appelle `serializer.save()` en ajoutant l'utilisateur connecté comme caissier.
5. `SaleCreateSerializer.create()` calcule chaque ligne : le prix vient de `product.sale_price` s'il n'est pas envoyé, et le total de ligne vaut quantité × prix − remise.
6. `SaleCreateSerializer.create()` calcule ensuite le sous-total, la remise, le total et la monnaie, puis appelle `Sale.generate_sale_number()`.
7. `Sale.objects.create()` enregistre la vente. Les signaux se déclenchent :
   - `store_original_sale_status_for_customer()` et `store_original_sale_status()` retiennent le statut avant enregistrement.
   - `update_customer_on_sale()` met à jour le client, s'il y en a un, et crée le `CustomerCredit` pour une vente à crédit.
   - `handle_sale_status_changes()` ne fait rien à la création.
   - `log_sale_action()` écrit un `ActionLog`.
8. `SaleItem.objects.create()` enregistre chaque ligne. `create_stock_movement_on_sale_item()` crée alors un `StockMovement` de type `exit` et de raison `sale`.
9. `StockMovement.save()` retire la quantité de `Stock`.
10. DRF renvoie la réponse 201.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Route et caissier | `api/v1/views/pos.py` | `SaleViewSet.perform_create()` |
| Calcul des montants | `api/v1/serializers/pos.py` | `SaleCreateSerializer.create()` |
| Validation des lignes | `api/v1/serializers/pos.py` | `SaleItemCreateSerializer` |
| Numéro de vente | `apps/pos/models.py` | `Sale.generate_sale_number()` |
| Mouvement de stock | `apps/pos/signals.py` | `create_stock_movement_on_sale_item()` |
| Journal | `apps/pos/signals.py` | `log_sale_action()` |
| Client et crédit | `apps/customers/signals.py` | `update_customer_on_sale()` |
| Mise à jour du stock | `apps/stock/models.py` | `StockMovement.save()` |

**Règles à connaître :**

- **Une vente API n'a pas d'emplacement.** `SaleViewSet.perform_create()` n'ajoute que le caissier : `enterprise` et `location` restent vides sur la vente et sur son mouvement. Pour un utilisateur rattaché à une entreprise, elle n'apparaît donc ni dans `pos:sales_list`, ni dans les tableaux de bord, ni dans `stock:movements`.
- **Produit présent dans plusieurs lignes `Stock` : erreur 500.** Sans emplacement, `StockMovement.save()` cherche une seule ligne avec le produit, et lève `MultipleObjectsReturned` s'il en trouve plusieurs. La vente et sa ligne restent pourtant enregistrées, car la requête n'est pas dans une transaction. Avec les données de `seed_full_data`, chaque produit a 4 lignes : les ventes API de ces produits échouent toutes ainsi.
- **Produit présent dans une seule ligne `Stock` :** cette ligne diminue, mais `LocationStock` ne change pas.
- **Produit sans ligne `Stock` :** une nouvelle ligne est créée, sans emplacement, avec une quantité négative.
- **Stock disponible :** il n'est pas contrôlé, et la quantité peut devenir négative.
- **Vente à crédit au-delà de la limite :** `update_customer_on_sale()` lève une `ValidationError` de Django, que DRF ne convertit pas : la réponse est 500. La vente reste enregistrée, sans ligne.
- **Vente à crédit sans `customer` :** elle est acceptée, mais aucun `CustomerCredit` n'est créé.
- **Montant payé :** sans `amount_paid`, il vaut le total, ou 0 pour une vente à crédit.
- **Taxes :** le total calculé n'ajoute pas `tax_amount`.
- **Reçu :** `SaleViewSet.receipt()` renvoie la vente en JSON. La branche PDF, qui attend `?format=pdf` ou `?format=thermal`, n'est pas accessible : DRF lit ce paramètre `format` avant la vue et répond 404. Le reçu PDF de la caisse web passe par `pos:sale_receipt`.

**Pour le tester :** avec un compte `manager`, appelez `/api/v1/stock/?product=<id>`. Choisissez un produit pour lequel `count` vaut 1, et notez sa quantité. Avec un compte `cashier`, créez la vente. Avec le compte `manager`, rappelez la même adresse : la quantité a diminué. Dans `/api/v1/stock-movements/?product=<id>`, une ligne `exit` porte le numéro de vente dans `reference`.

## Annuler ou rembourser une vente

**Ce que voit l'utilisateur :** un `admin`, un `owner` ou un `manager` envoie `POST /api/v1/sales/<id>/cancel/` ou `POST /api/v1/sales/<id>/refund/`. Il reçoit un message de confirmation, et la marchandise revient en stock. Le client et son crédit ne changent pas.

**Ce qui se passe dans le code :**

1. `SaleViewSet.cancel()` ou `SaleViewSet.refund()` refuse avec 400 si la vente a déjà ce statut.
2. La méthode change `status`, puis appelle `save()`.
3. `store_original_sale_status()` a retenu l'ancien statut.
4. `update_customer_on_sale()` s'arrête tout de suite, car le statut n'est plus `completed`.
5. `handle_sale_status_changes()` crée une entrée de stock par ligne : raison `correction` et référence `CANCEL-<numéro>` pour une annulation, raison `customer_return` et référence `REFUND-<numéro>` pour un remboursement.
6. `log_sale_action()` journalise le changement de statut.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Annulation | `api/v1/views/pos.py` | `SaleViewSet.cancel()` |
| Remboursement | `api/v1/views/pos.py` | `SaleViewSet.refund()` |
| Retour en stock | `apps/pos/signals.py` | `handle_sale_status_changes()` |
| Arrêt avant le client | `apps/customers/signals.py` | `update_customer_on_sale()` |

**Règles à connaître :**

- `total_purchases`, `purchase_count`, `loyalty_points`, `current_balance` et le `CustomerCredit` ne sont pas corrigés. Le bloc d'inversion de `update_customer_on_sale()` n'est jamais atteint.
- Le stock revient seulement si l'ancien statut est `completed`. Rembourser une vente déjà annulée répond 200, sans nouveau mouvement.
- Une vente faite à la caisse web a un emplacement : le stock revient dans `Stock` et `LocationStock` de cet emplacement.
- Le retour en stock utilise aussi `StockMovement.save()` : l'erreur `MultipleObjectsReturned` décrite plus haut s'applique à une vente sans emplacement. La réponse est alors 500, mais le nouveau statut reste enregistré, sans retour en stock. Un second envoi répond 400.

**Pour le tester :** reprenez la vente de l'exemple. Avec un compte `manager`, envoyez `cancel` : la quantité de `/api/v1/stock/` remonte. Renvoyez `cancel` : la réponse est 400.

## Paramètres des actions personnalisées

**Ce que voit l'utilisateur :** certaines actions acceptent des paramètres d'adresse qui leur sont propres. Ils ne passent pas par `filterset_fields`.

| Adresse | Paramètres | Réponse |
|---|---|---|
| `/api/v1/stock-movements/movement_history/` | `product_id`, `start_date`, `end_date`, `movement_type` | Liste paginée |
| `/api/v1/expenses/summary/` | `start_date`, `end_date`, `category_id` | `total` et `count`. `total` vaut `null` sans dépense |
| `/api/v1/daily-summaries/daily_summary/` | `date`, aujourd'hui par défaut | Le résumé de ce jour |
| `/api/v1/settings/get_setting/` | `key`, obligatoire | `key` et `value`. 400 sans `key`, 404 si la clé n'existe pas |
| `/api/v1/settings/set_setting/` (`POST`) | Corps JSON avec `key`, obligatoire, et `value` | Le paramètre enregistré |
| `/api/v1/sales/today_summary/` | Aucun | `count`, `total`, `total_sales`, `cash`, `mobile_money`, `card`, `credit` |

**Ce qui se passe dans le code :**

1. La méthode décorée avec `@action` lit `request.query_params`, ou `request.data` pour `POST`.
2. Elle filtre `get_queryset()`, ou agrège les lignes avec `aggregate`.
3. Elle renvoie la réponse. Seule `StockMovementViewSet.movement_history()` passe par la pagination.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Historique des mouvements | `api/v1/views/stock.py` | `StockMovementViewSet.movement_history()` |
| Total des dépenses | `api/v1/views/accounting.py` | `ExpenseViewSet.summary()` |
| Résumé d'un jour | `api/v1/views/accounting.py` | `DailySummaryViewSet.daily_summary()` |
| Lecture et écriture d'un paramètre | `api/v1/views/settings.py` | `StoreSettingViewSet.get_setting()`, `StoreSettingViewSet.set_setting()` |
| Ventes du jour | `api/v1/views/pos.py` | `SaleViewSet.today_summary()` |

**Règles à connaître :**

- Écrivez les dates de `start_date`, `end_date` et `date` au format `AAAA-MM-JJ`.
- `today_summary` ne compte que les ventes `completed` du jour.
- `all_settings` renvoie un seul objet : chaque clé y est associée à sa valeur.

**Pour le tester :** avec un jeton `manager`, appelez `GET /api/v1/expenses/summary/?start_date=2026-01-01&end_date=2026-01-31`. La réponse contient `total` et `count`. Appelez ensuite `GET /api/v1/settings/get_setting/` sans paramètre : la réponse est 400.

## À retenir

- Toute l'API part de `api/v1/urls.py`. Chaque ressource y relie un préfixe à un ViewSet de `api/v1/views/`.
- Connectez-vous par `POST /api/v1/auth/login/`, puis envoyez `Authorization: Bearer VOTRE_JETON_ACCESS`.
- Pour changer une quantité, créez un `stock-movements`, et ne modifiez pas `stock` directement.
- Les ventes API n'ont ni entreprise ni emplacement, et échouent si le produit a plusieurs lignes `Stock`.
- Annuler ou rembourser une vente remet le stock, mais ne corrige ni le client ni son crédit.
- La documentation interactive est sur `/api/v1/docs/`, mais le code reste la référence.
