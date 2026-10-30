# Produits et catégories

Cette partie gère le catalogue : les catégories, les produits et leurs conditionnements. Elle sert surtout au `admin`, au `owner` et au `manager`, qui créent et modifient le catalogue. Les rôles de stock consultent les produits pour faire leurs entrées et leurs transferts.

## Sommaire

- [Liste des catégories](#liste-des-catégories)
- [Créer et modifier une catégorie](#créer-et-modifier-une-catégorie)
- [Activer, désactiver ou supprimer une catégorie](#activer-désactiver-ou-supprimer-une-catégorie)
- [Liste des produits](#liste-des-produits)
- [Créer et modifier un produit](#créer-et-modifier-un-produit)
- [Fiche produit et stock par emplacement](#fiche-produit-et-stock-par-emplacement)
- [Activer, désactiver ou supprimer un produit](#activer-désactiver-ou-supprimer-un-produit)
- [Conditionnements](#conditionnements)
- [À retenir](#à-retenir)

## Liste des catégories

**Ce que voit l'utilisateur :** une grille de cartes. Chaque carte montre le nom, la description, le statut et le nombre de produits actifs. Un champ de recherche et un filtre de statut sont en haut. Un compteur indique le nombre de catégories actives sur le total.

**Ce qui se passe dans le code :**

1. L'adresse `/products/categories/` est déclarée dans `apps/products/urls.py` sous le nom `products:category_list`.
2. `role_required()` vérifie le rôle, puis `category_list()` s'exécute (`apps/products/views.py`).
3. La vue lit `Category` et ajoute `product_count`, le nombre de produits actifs de chaque catégorie.
4. Elle garde les catégories de l'entreprise et les catégories sans entreprise, dites globales.
5. Elle applique `?status=` (`active` ou `inactive`) et `?search=` (nom ou description).
6. `apps/products/templates/products/category_list.html` affiche les cartes.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| URL `products:category_list` | `apps/products/urls.py` | `category_list()` |
| Vue | `apps/products/views.py` | `category_list()` |
| Contrôle du rôle | `apps/products/views.py` | `role_required()` |
| Modèle | `apps/products/models.py` | `Category` |
| Template | `apps/products/templates/products/category_list.html` | Aucune |

**Règles à connaître :**

- Rôles autorisés : `admin`, `owner`, `manager`, `warehouse_manager`, `boutique_manager`.
- Les autres rôles sont renvoyés vers `home` avec un message. Un visiteur non connecté va vers la page de connexion.
- Les boutons Modifier, Activer et Supprimer ne s'affichent que pour `admin`, `owner` et `manager`.
- Le lien vers cette page se trouve sur la liste des produits et n'y apparaît que pour ces trois rôles.

**Pour le tester :** connectez-vous en `manager`, ouvrez `/products/categories/`, puis cherchez un nom. Seules les catégories correspondantes restent affichées.

## Créer et modifier une catégorie

**Ce que voit l'utilisateur :** un formulaire avec le nom, la description et une case « Categorie active ». Après l'enregistrement, il revient à la liste avec un message de succès.

**Ce qui se passe dans le code :**

1. `/products/categories/create/` mène à `category_create()`. `/products/categories/<pk>/edit/` mène à `category_edit()`.
2. En modification, la vue vérifie que la catégorie est accessible à l'entreprise de l'utilisateur.
3. Sur POST, la vue lit les champs et contrôle le nom.
4. Si tout est correct, elle crée ou enregistre la `Category`, puis redirige vers `products:category_list`.
5. Si une erreur existe, elle affiche le message et rend de nouveau `apps/products/templates/products/category_form.html`.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| URL `products:category_create` | `apps/products/urls.py` | `category_create()` |
| URL `products:category_edit` | `apps/products/urls.py` | `category_edit()` |
| Modèle | `apps/products/models.py` | `Category` |
| Template | `apps/products/templates/products/category_form.html` | Aucune |

**Règles à connaître :**

- Rôles autorisés : `admin`, `owner`, `manager`.
- Le nom est obligatoire. Il doit être unique dans l'entreprise, sans tenir compte des majuscules.
- Le formulaire produit a un lien « + Ajouter une categorie » vers `products:category_create`. Il quitte le formulaire produit : après la création, on revient à la liste des catégories.

**Pour le tester :** en `manager`, ouvrez `/products/categories/create/` et créez une catégorie. Recréez-la avec le même nom en minuscules : le message « Une catégorie avec ce nom existe déjà. » apparaît.

## Activer, désactiver ou supprimer une catégorie

**Ce que voit l'utilisateur :** sur chaque carte, un bouton bascule active ou désactive la catégorie. Une corbeille apparaît quand la carte compte 0 produit actif.

**Ce qui se passe dans le code :**

1. Le formulaire de la carte envoie un POST à `products:category_toggle` ou à `products:category_delete`.
2. `category_toggle()` inverse `is_active`, enregistre, puis revient à la liste.
3. `category_delete()` compte tous les produits de la catégorie, actifs ou non.
4. S'il y en a, la vue affiche une erreur. Sinon, sur POST, elle supprime la ligne.
5. Les deux vues redirigent vers `products:category_list`.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| URL `products:category_toggle` | `apps/products/urls.py` | `category_toggle()` |
| URL `products:category_delete` | `apps/products/urls.py` | `category_delete()` |
| Relation produit-catégorie | `apps/products/models.py` | `Product` |
| Boutons | `apps/products/templates/products/category_list.html` | Aucune |

**Règles à connaître :**

- Rôles autorisés : `admin`, `owner`, `manager`.
- Désactiver est une suppression logique : on garde la ligne et on met `is_active` à faux.
- Supprimer efface vraiment la catégorie de la base.
- La corbeille dépend des produits actifs, mais le serveur compte aussi les inactifs. Une catégorie qui n'a que des produits inactifs montre donc la corbeille, puis la suppression est refusée.
- Une catégorie désactivée disparaît des listes du formulaire produit et des filtres, y compris à la caisse. Ses produits restent actifs : la recherche de la caisse les propose encore.
- Pour enregistrer un produit dont la catégorie est inactive, il faut lui choisir une catégorie active.

**Pour le tester :** en `manager`, désactivez une catégorie, puis ouvrez `/products/create/`. Elle n'apparaît plus dans la liste. Réactivez-la ensuite.

## Liste des produits

**Ce que voit l'utilisateur :** un compteur de produits actifs, puis un tableau de produits avec prix, marge, unité, emplacements et statut. La colonne Emplacements affiche chaque lieu où le produit a du stock, avec sa quantité. Les filtres se relancent seuls pendant la saisie. Des boutons PDF et Excel exportent la liste filtrée.

**Ce qui se passe dans le code :**

1. `/products/` est déclarée sous le nom `products:product_list` et appelle `product_list()`.
2. La vue charge les `Product` de l'entreprise et les produits globaux.
3. Elle précharge les `LocationStock` dont la quantité est positive et les place dans `active_location_stocks`.
4. Elle applique les filtres : `?category=`, `?status=`, `?location=`, `?stock=` et `?search=`.
5. Si `?export=pdf` ou `?export=xlsx` est présent, `export_list_response()` (`apps/core/exports.py`) renvoie le fichier.
6. Sinon, `Paginator` découpe la liste en pages de 25 produits.
7. `apps/products/templates/products/product_list.html` affiche le tableau. `templates/partials/export_buttons.html` ajoute les boutons d'export.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| URL `products:product_list` | `apps/products/urls.py` | `product_list()` |
| Vue | `apps/products/views.py` | `product_list()` |
| Stock affiché | `apps/locations/models.py` | `LocationStock` |
| Marge affichée | `apps/products/models.py` | `Product.profit_margin` |
| Export | `apps/core/exports.py` | `export_list_response()` |
| Template | `apps/products/templates/products/product_list.html` | Aucune |

**Règles à connaître :**

- Rôles autorisés : `admin`, `owner`, `manager`, `warehouse_manager`, `boutique_manager`, `stock_manager`.
- L'entrée de menu « Produits » de `templates/base.html` n'apparaît que pour `admin`, `owner` et `manager`.
- Le compteur ne suit pas les filtres. La marge n'apparaît que si elle est positive.
- `?status=` accepte `active`, `inactive` et `popular`. La recherche porte sur le nom, le code-barres, le SKU (référence interne) et la description.
- Un export contient au plus 5000 lignes. Le PDF s'ouvre dans le navigateur et le fichier Excel se télécharge.
- `?stock=low` et `?stock=out` existent dans la vue, mais aucun champ du formulaire ni lien ne les propose.
- Ces deux filtres lisent des lignes `Stock` une par une. La ligne à 0 créée avec un nouveau produit y est donc comptée, même si ce produit a du stock ailleurs.

**Pour le tester :** en `manager`, ouvrez `/products/`, choisissez un emplacement dans le filtre. Seuls les produits ayant une quantité positive à cet endroit restent. Cliquez ensuite sur Excel : le fichier reprend la même liste.

## Créer et modifier un produit

**Ce que voit l'utilisateur :** un formulaire en blocs : informations de base avec l'unité de mesure, identification, prix avec le taux de taxe, seuil de stock et options. La marge se recalcule dès que l'on change un prix. Après l'enregistrement, il revient à la liste des produits. En cas d'erreur, la création réaffiche les valeurs saisies, et la modification réaffiche les valeurs enregistrées.

**Ce qui se passe dans le code :**

1. `/products/create/` mène à `product_create()`. `/products/<pk>/edit/` mène à `product_edit()`.
2. La vue prépare les catégories actives de l'entreprise et les catégories globales.
3. Sur POST, elle lit les champs, convertit les nombres et collecte les erreurs.
4. `product_create()` crée le `Product` et une ligne `Stock` à quantité 0, sans emplacement ni entreprise.
5. `product_edit()` enregistre le `Product` et ne touche pas au stock.
6. Les deux vues redirigent vers `products:product_list` en cas de succès.
7. Dans `apps/products/templates/products/product_form.html`, `updateMargin()` affiche la marge dans le navigateur.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| URL `products:product_create` | `apps/products/urls.py` | `product_create()` |
| URL `products:product_edit` | `apps/products/urls.py` | `product_edit()` |
| Modèle produit | `apps/products/models.py` | `Product` |
| Ligne de stock initiale | `apps/stock/models.py` | `Stock` |
| Calcul de marge à l'écran | `apps/products/templates/products/product_form.html` | `updateMargin()` |

**Règles à connaître :**

- Rôles autorisés : `admin`, `owner`, `manager`.
- Le nom et la catégorie sont obligatoires. Les prix ne peuvent pas être négatifs.
- Le seuil minimum (`min_stock_threshold`) doit être un nombre entier.
- Le code-barres, s'il est saisi, doit être unique dans toute la table `products`. Le SKU n'a pas ce contrôle : deux produits peuvent avoir le même.
- L'unité se choisit parmi `piece`, `sachet`, `carton`, `kg` et `liter`.
- Le taux de taxe se règle de 0 à 100 % et s'affiche sur la fiche s'il est supérieur à 0. La caisse (`apps/pos/templates/pos/cashier.html`) ne l'applique pas : elle envoie une taxe à 0.
- Le stock ne se saisit pas ici : il passe par `stock:entry`.
- Le modèle a un champ `image`, mais le formulaire web ne permet pas d'envoyer une image.
- La case « Produit populaire » remplit `is_popular`, qui affiche le produit en raccourci à la caisse.

**Pour le tester :** en `manager`, créez un produit avec un prix d'achat de 1000 et un prix de vente de 1500. Le formulaire affiche une marge de 50.0% et 500 FB de profit. Le produit apparaît ensuite dans `/products/` avec « Aucun emplacement ».

## Fiche produit et stock par emplacement

**Ce que voit l'utilisateur :** l'identification du produit, ses prix, sa marge, sa taxe éventuelle et le bloc « Stock par emplacement ». Ce bloc donne le total et une ligne par emplacement. Si le total vaut 0, il affiche « Aucun stock dans les emplacements. » avec un lien vers `stock:entry`. Une alerte rouge apparaît si le total atteint le seuil minimum. Des actions rapides permettent de faire une entrée de stock, de modifier ou de désactiver le produit.

**Ce qui se passe dans le code :**

1. `/products/<pk>/` est déclarée sous le nom `products:product_detail` et appelle `product_detail()`.
2. La vue charge le `Product` et vérifie qu'il est accessible à l'entreprise de l'utilisateur.
3. Elle lit toutes les lignes `Stock` du produit, triées par emplacement.
4. Elle additionne leurs quantités dans `total_stock`.
5. `apps/products/templates/products/product_detail.html` affiche les lignes dont la quantité n'est pas nulle.
6. Chaque emplacement renvoie vers `locations:detail`, avec `?next=` pour revenir à la fiche.
7. Le bouton d'entrée ouvre `stock:entry` avec `?product=` déjà rempli.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| URL `products:product_detail` | `apps/products/urls.py` | `product_detail()` |
| Lignes de stock | `apps/stock/models.py` | `Stock` |
| Pourcentage de marge | `apps/products/models.py` | `Product.profit_margin` |
| Page liée | `apps/locations/views.py` | `location_detail()` |
| Template | `apps/products/templates/products/product_detail.html` | Aucune |

**Règles à connaître :**

- Rôles autorisés : `admin`, `owner`, `manager`, `warehouse_manager`, `boutique_manager`, `stock_manager`.
- Les boutons Modifier et Activer ou Désactiver ne s'affichent que pour `admin`, `owner` et `manager`.
- La fiche lit `Stock`. La colonne Emplacements de `products:product_list` lit `LocationStock`.
- Une ligne de stock sans emplacement s'affiche sous le libellé « Sans emplacement », si sa quantité n'est pas nulle.
- L'alerte s'affiche seulement si le seuil est supérieur à 0 et si le total est inférieur ou égal au seuil.
- Le montant entre parenthèses à côté de la marge additionne le prix de vente et le prix d'achat. Ce n'est pas le profit. Seul le pourcentage représente la marge.

**Pour le tester :** en `manager`, faites une entrée de 10 unités dans un emplacement avec `stock:entry`, puis ouvrez la fiche du produit. Le total augmente de 10 et l'emplacement est listé. Un clic sur l'emplacement ouvre sa page, et le bouton retour ramène à la fiche.

## Activer, désactiver ou supprimer un produit

**Ce que voit l'utilisateur :** un bouton bascule sur la liste et sur la fiche produit. Le produit désactivé reste dans la liste, en plus clair, avec le statut « Inactif ». Il n'y a pas de bouton Supprimer à l'écran.

**Ce qui se passe dans le code :**

1. Le bouton envoie un POST à `products:product_toggle`.
2. `product_toggle()` inverse `is_active`, enregistre, puis revient à `products:product_list`.
3. `products:product_delete` n'a aucun bouton dans les templates. La route répond seulement à un POST envoyé directement.
4. `product_delete()` cherche des `SaleItem` et des `StockMovement` liés au produit.
5. Si elle en trouve, elle met `is_active` à faux et affiche « historique conservé ».
6. Sinon, elle supprime réellement le produit. Elle redirige ensuite vers `products:product_list`.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| URL `products:product_toggle` | `apps/products/urls.py` | `product_toggle()` |
| URL `products:product_delete` | `apps/products/urls.py` | `product_delete()` |
| Lignes de vente vérifiées | `apps/pos/models.py` | `SaleItem` |
| Mouvements vérifiés | `apps/stock/models.py` | `StockMovement` |
| Boutons | `apps/products/templates/products/product_list.html` | Aucune |

**Règles à connaître :**

- Rôles autorisés : `admin`, `owner`, `manager`.
- Un produit inactif n'est plus proposé à la caisse (`apps/pos/views_frontend.py`), ni dans `stock:entry`, ni dans `transfers:create`.
- Le stock et l'historique du produit sont conservés. Désactiver ne crée aucun mouvement.
- Le formulaire de modification a aussi une case « Produit actif », qui change le même champ.

**Pour le tester :** en `manager`, désactivez un produit depuis `/products/`, puis ouvrez `/stock/entry/` : il n'est plus dans la recherche. Réactivez-le pour le voir revenir.

## Conditionnements

**Ce que voit l'utilisateur :** rien dans les pages web de l'application. Un conditionnement se gère dans l'administration Django ou par l'API. Exemple : un carton de 12 pièces, avec son propre code-barres et un prix facultatif.

**Ce qui se passe dans le code :**

1. `ProductPackaging` (`apps/products/models.py`) relie un nom et `quantity_per_unit` à un `Product`.
2. Dans l'administration, `ProductPackagingInline` affiche les conditionnements sur la page du produit. `ProductPackagingAdmin` les liste séparément.
3. Dans l'API, `ProductPackagingViewSet` expose la ressource `product-packagings`.
4. `ProductSerializer` renvoie aussi les conditionnements dans le champ `packagings` de chaque produit.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Modèle | `apps/products/models.py` | `ProductPackaging` |
| Administration | `apps/products/admin.py` | `ProductPackagingInline`, `ProductPackagingAdmin` |
| API, vue | `api/v1/views/products.py` | `ProductPackagingViewSet` |
| API, serializer | `api/v1/serializers/products.py` | `ProductPackagingSerializer` |
| API, route | `api/v1/urls.py` | `ProductPackagingViewSet` |

**Règles à connaître :**

- Il n'existe aucune route `products:*` ni aucun template pour les conditionnements.
- Le code de la caisse et celui du stock ne l'utilisent pas. Une vente ou un mouvement ne convertit donc pas un carton en unités.
- Le code-barres d'un conditionnement est unique s'il est renseigné. Le prix de vente est facultatif.
- Dans l'API, cette ressource utilise la permission `IsAdminOrManager`.

**Pour le tester :** avec un compte `admin` ayant accès à `/admin/`, ouvrez un produit et ajoutez un conditionnement « Carton » de 12. Il apparaît ensuite dans la réponse de `GET /api/v1/product-packagings/`.

## À retenir

- Le catalogue se gère dans `apps/products/views.py`. Seuls `admin`, `owner` et `manager` peuvent le modifier.
- Un produit se désactive avec `is_active`. Son stock et son historique restent en place.
- Créer un produit ne donne pas de stock : il faut ensuite passer par `stock:entry` ou par un transfert.
- La fiche produit lit `Stock`, tandis que la liste lit `LocationStock` pour la colonne Emplacements.
- `ProductPackaging` existe dans le modèle, l'administration et l'API, mais pas dans les pages web ni à la caisse.
