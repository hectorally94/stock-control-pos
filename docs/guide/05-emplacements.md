# Emplacements

Un emplacement est un lieu qui détient du stock : un dépôt ou une boutique. Cette partie permet de les créer, de définir leurs types et de consulter le stock de chaque lieu. Elle sert aux rôles de gestion et de stock, et au rôle `accountant` en consultation.

## Sommaire

- [Tableau de bord des emplacements](#tableau-de-bord-des-emplacements)
- [Créer et modifier un emplacement](#créer-et-modifier-un-emplacement)
- [Supprimer ou désactiver un emplacement](#supprimer-ou-désactiver-un-emplacement)
- [Détail d'un emplacement](#détail-dun-emplacement)
- [Stock d'un emplacement](#stock-dun-emplacement)
- [Types d'emplacement](#types-demplacement)
- [À retenir](#à-retenir)

## Tableau de bord des emplacements

**Ce que voit l'utilisateur :** une section Dépôts, une section Boutiques et un tableau « Vue d'ensemble du Stock ». Ce tableau donne, par emplacement, le nombre de produits, le stock faible et les ruptures. Chaque nombre est un lien vers le stock filtré, et un tiret remplace un compteur à 0. Les actions rapides mènent aux transferts, au stock global et à l'administration des emplacements.

**Ce qui se passe dans le code :**

1. `/locations/` est déclarée sous le nom `locations:dashboard` dans `apps/locations/urls.py` et appelle `dashboard()`.
2. La vue contrôle le rôle, puis charge les `Location` de l'entreprise, y compris les inactives.
3. Elle sépare les dépôts et les boutiques avec `location_type`.
4. Pour chaque emplacement, elle lit `LocationStock` et compte les lignes, le stock faible et les ruptures.
5. `apps/locations/templates/locations/dashboard.html` affiche les sections. `Location.type_display` donne le libellé du type.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| URL `locations:dashboard` | `apps/locations/urls.py` | `dashboard()` |
| Vue | `apps/locations/views.py` | `dashboard()` |
| Modèles | `apps/locations/models.py` | `Location`, `LocationStock` |
| Seuil d'alerte | `apps/locations/models.py` | `LocationStock.is_low_stock` |
| Template | `apps/locations/templates/locations/dashboard.html` | Aucune |
| Lien de menu | `templates/base.html` | Aucune |

**Règles à connaître :**

- Rôles autorisés : `admin`, `owner`, `manager`, `warehouse_manager`, `boutique_manager`, `stock_manager`, `accountant`. Les autres sont renvoyés vers `home`.
- L'entrée de menu « Emplacements » n'apparaît que pour `admin`, `owner`, `manager`, `warehouse_manager` et `boutique_manager`.
- Les boutons « Nouvel emplacement » et « Gérer les types » ne s'affichent que pour `admin`, `owner` et `manager`.
- Un compte sans entreprise ne voit aucun emplacement.
- « Produits » compte les lignes `LocationStock`, y compris celles à 0.
- Le stock faible compte les lignes positives qui ont atteint `LocationStock.min_stock_threshold`. Ce seuil vaut 0 par défaut et aucune page de l'application ne permet de le modifier. Il se règle dans l'administration Django, sous `/admin/locations/locationstock/`. L'API `location-stocks` renvoie une erreur serveur pour un compte rattaché à une entreprise. Sans ce réglage, le compteur reste à 0.
- Les actions rapides s'affichent pour tous les rôles de la page, mais chaque cible garde ses contrôles. `accountant` est renvoyé vers `home` par « Nouveau Transfert » et « Stock Global ». « Gérer » ouvre `/admin/locations/location/`, qui demande `is_staff`.

**Pour le tester :** en `manager`, ouvrez `/locations/`. Cliquez sur le nombre de la colonne Produits d'une ligne : `locations:stock` s'ouvre pour cet emplacement.

## Créer et modifier un emplacement

**Ce que voit l'utilisateur :** un formulaire avec le nom, le code, le type, l'adresse, le téléphone, l'e-mail, le responsable (un compte actif de l'entreprise) et deux cases : « Dépôt principal de l'entreprise » et « Actif ». Après la création, il revient au tableau de bord. Après une modification, il arrive sur le détail de l'emplacement.

**Ce qui se passe dans le code :**

1. `/locations/create/` mène à `location_create()`. `/locations/<pk>/edit/` mène à `location_edit()`.
2. `_active_types()` et `_managers_for()` remplissent les listes du formulaire.
3. En modification, `_location_data_from_instance()` préremplit le formulaire.
4. En POST, `_location_data_from_post()` nettoie les champs et `_validate_location()` les contrôle.
5. La vue copie `behaviour` du type choisi dans `location_type`, puis enregistre la `Location`.
6. `Location.save()` retire le statut de dépôt principal aux autres emplacements de l'entreprise si cette case est cochée.
7. `apps/locations/templates/locations/location_form.html` affiche le formulaire.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| URL `locations:create` | `apps/locations/urls.py` | `location_create()` |
| URL `locations:edit` | `apps/locations/urls.py` | `location_edit()` |
| Validation | `apps/locations/views.py` | `_validate_location()` |
| Modèle | `apps/locations/models.py` | `Location.save()` |
| Template | `apps/locations/templates/locations/location_form.html` | Aucune |

**Règles à connaître :**

- Rôles autorisés : `admin`, `owner`, `manager`. Les autres sont renvoyés vers `locations:dashboard`, et `cashier`, qui n'y a pas accès, continue vers `home`.
- Le nom, le code et le type sont obligatoires. Le code est unique dans l'entreprise.
- Le type doit être actif. Si le type actuel d'un emplacement a été désactivé, il faut en choisir un autre pour enregistrer.
- Une entreprise n'a qu'un seul dépôt principal à la fois.
- Si l'entreprise n'a aucun type actif, le formulaire propose d'en créer un.
- `LocationAdmin` (`apps/locations/admin.py`) n'a pas de champ de type. Un emplacement créé dans l'administration affiche le libellé de son comportement, et sa modification ici demande de lui choisir un type.

**Pour le tester :** en `manager`, créez un emplacement avec le type de votre choix. Il apparaît dans la section Dépôts ou Boutiques selon le comportement du type. Essayez ensuite le même code : le message « Un emplacement avec ce code existe déjà. » apparaît.

## Supprimer ou désactiver un emplacement

**Ce que voit l'utilisateur :** une zone de danger en bas du formulaire de modification, avec une demande de confirmation. Si la suppression est refusée, un message l'invite à décocher « Actif ».

**Ce qui se passe dans le code :**

1. Le bouton envoie un POST à `/locations/<pk>/delete/`, nommée `locations:delete`.
2. `location_delete()` renvoie vers `locations:detail` si la requête n'est pas un POST.
3. La vue cherche des lignes `LocationStock` et `Stock`, des mouvements et des transferts liés.
4. Si elle en trouve, elle affiche l'erreur et renvoie vers `locations:edit`.
5. Sinon, elle supprime l'emplacement et revient à `locations:dashboard`.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| URL `locations:delete` | `apps/locations/urls.py` | `location_delete()` |
| Vue | `apps/locations/views.py` | `location_delete()` |
| Modèles vérifiés | `apps/locations/models.py` | `LocationStock` |
| Modèles vérifiés | `apps/stock/models.py` | `Stock`, `StockMovement` |
| Modèle vérifié | `apps/transfers/models.py` | `Transfer` |
| Bouton | `apps/locations/templates/locations/location_form.html` | Aucune |

**Règles à connaître :**

- Rôles autorisés : `admin`, `owner`, `manager`.
- Une simple ligne de stock à 0 suffit à bloquer la suppression.
- Un emplacement inactif reste visible sur `locations:dashboard`, avec un badge « Inactif ».
- Il n'est plus proposé dans `stock:entry`, dans `transfers:create`, dans les filtres d'emplacement ni dans les formulaires de compte. Il disparaît aussi des cartes de `stock:dashboard`.
- Désactiver ne déplace pas le stock et ne crée aucun mouvement.

**Pour le tester :** en `manager`, essayez de supprimer un emplacement qui a du stock : un message refuse la suppression. Créez ensuite un emplacement neuf et supprimez-le : il disparaît.

## Détail d'un emplacement

**Ce que voit l'utilisateur :** des cartes (total, stock faible, rupture, statut), les coordonnées et la liste des produits de ce lieu avec une recherche instantanée. Chaque ligne propose « Entrée » et « Historique ». Des raccourcis « Envoyer » et « Recevoir » mènent aux transferts.

**Ce qui se passe dans le code :**

1. `/locations/<pk>/` est déclarée sous le nom `locations:detail` et appelle `location_detail()`.
2. La vue vérifie l'entreprise, puis la règle propre au caissier.
3. Elle lit les `LocationStock` de cet emplacement, triés par nom de produit.
4. Elle calcule les lignes en stock faible et le nombre de ruptures.
5. Elle lit `?next=` pour régler le bouton retour, à condition que l'adresse soit sur le même site. Sinon, le retour mène à `locations:dashboard`.
6. `apps/locations/templates/locations/detail.html` affiche la page. Alpine.js filtre les lignes sans recharger.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| URL `locations:detail` | `apps/locations/urls.py` | `location_detail()` |
| Vue | `apps/locations/views.py` | `location_detail()` |
| Modèle | `apps/locations/models.py` | `LocationStock` |
| Lien « Entrée » | `apps/stock/views_frontend.py` | `entry_view()` |
| Lien « Historique » | `apps/stock/views_frontend.py` | `movements_view()` |
| Template | `apps/locations/templates/locations/detail.html` | Aucune |

**Règles à connaître :**

- L'emplacement doit appartenir à l'entreprise de l'utilisateur. Un `cashier` ne peut consulter que son propre emplacement.
- « Entrée », « Historique », « Envoyer » et « Recevoir » ne s'affichent que pour `admin`, `owner`, `manager`, `warehouse_manager`, `boutique_manager` et `stock_manager`.
- Les deux boutons « Modifier » ne s'affichent que pour `admin`, `owner` et `manager`. Celui de l'en-tête ouvre `locations:edit`. Le raccourci du bas ouvre l'administration Django, qui demande `is_staff`.
- La liste ne contient que les produits ayant déjà une ligne `LocationStock` ici. Pour un autre produit, passez par `stock:entry`.
- « Recevoir » ouvre `transfers:list` filtrée avec `?destination=` sur cet emplacement. « Envoyer » ouvre `transfers:create` avec `?source=`.

**Pour le tester :** en `boutique_manager`, ouvrez la fiche d'un produit, puis cliquez sur un emplacement. Tapez un nom dans la recherche : le tableau se réduit. Le bouton retour ramène à la fiche produit.

## Stock d'un emplacement

**Ce que voit l'utilisateur :** l'inventaire complet du lieu, avec la quantité, le seuil et le statut : OK, Faible ou Rupture. Il peut filtrer par catégorie et par statut, exporter, préparer un transfert pour un produit, ou ouvrir un transfert vide avec le bouton « Envoyer Stock ».

**Ce qui se passe dans le code :**

1. `/locations/<pk>/stock/` est déclarée sous le nom `locations:stock` et appelle `location_stock()`.
2. La vue applique les mêmes contrôles d'accès que `location_detail()`.
3. Elle lit les `LocationStock` de l'emplacement, puis applique `?category=` et `?status=`.
4. `export_list_response()` renvoie le fichier si `?export=` est présent.
5. `apps/locations/templates/locations/stock.html` affiche le tableau. Le bouton de transfert ouvre `transfers:create` avec `?source=` et `?product=`.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| URL `locations:stock` | `apps/locations/urls.py` | `location_stock()` |
| Vue | `apps/locations/views.py` | `location_stock()` |
| Modèle | `apps/locations/models.py` | `LocationStock` |
| Export | `apps/core/exports.py` | `export_list_response()` |
| Template | `apps/locations/templates/locations/stock.html` | Aucune |

**Règles à connaître :**

- `?status=` accepte `low` (faible, sans les ruptures), `out` (rupture) et `alert` (les deux).
- Les quantités viennent de `LocationStock`, mises à jour par `StockMovement.save()`. Voir [le guide du stock](04-stock.md).
- Le filtre de catégorie ne propose que les catégories de l'entreprise, pas les catégories globales.
- Les cartes du bas de la page ne sont pas fiables. « Stock Faible » répète le nombre de lignes affichées et « En Rupture » affiche toujours 0. Fiez-vous aux compteurs de `locations:detail` et au tableau.

**Pour le tester :** en `warehouse_manager`, ouvrez `/locations/<pk>/stock/?status=out`. Seules les lignes à 0 ou moins restent. Le bouton PDF ouvre la même liste filtrée.

## Types d'emplacement

**Ce que voit l'utilisateur :** une liste de types propres à l'entreprise, comme « Pharmacie » ou « Entrepôt Froid », avec leur comportement, le nombre d'emplacements qui les utilisent et leur statut. Il peut créer, modifier et supprimer un type.

Le comportement décide du classement interne de l'emplacement : `warehouse` (dépôt) ou `boutique`.

**Ce qui se passe dans le code :**

1. `/locations/types/` mène à `type_list()`, qui compte les emplacements de chaque type dans `usage`.
2. `/locations/types/create/` mène à `type_create()`. `/locations/types/<pk>/edit/` mène à `type_edit()`.
3. Ces deux vues utilisent `_type_data_from_post()`, puis `_validate_type()`.
4. `type_edit()` enregistre le `LocationType`, puis recopie son comportement dans `location_type` de tous ses emplacements.
5. `/locations/types/<pk>/delete/` mène à `type_delete()`, qui supprime le type en POST s'il n'est pas utilisé.
6. `apps/locations/templates/locations/type_list.html` et `apps/locations/templates/locations/type_form.html` affichent les pages.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| URL `locations:type_list` | `apps/locations/urls.py` | `type_list()` |
| URL `locations:type_create` | `apps/locations/urls.py` | `type_create()` |
| URL `locations:type_edit` | `apps/locations/urls.py` | `type_edit()` |
| URL `locations:type_delete` | `apps/locations/urls.py` | `type_delete()` |
| Validation | `apps/locations/views.py` | `_validate_type()` |
| Modèle | `apps/locations/models.py` | `LocationType` |

**Règles à connaître :**

- Rôles autorisés : `admin`, `owner`, `manager`. Les autres sont renvoyés vers `locations:dashboard`.
- Le nom est obligatoire et unique dans l'entreprise. Le comportement doit être `warehouse` ou `boutique`.
- Changer le comportement d'un type déplace ses emplacements entre les sections Dépôts et Boutiques du tableau de bord.
- Un type utilisé ne peut pas être supprimé. On peut le désactiver : il disparaît alors de la liste du formulaire d'emplacement.

**Pour le tester :** en `manager`, créez le type « Pharmacie » avec le comportement Boutique, puis un emplacement de ce type. Il apparaît dans Boutiques, avec « Pharmacie » comme libellé. La suppression du type est ensuite refusée.

## À retenir

- Un emplacement a un type (`type_ref`) pour le libellé et un comportement (`location_type`) pour le classement.
- Le stock d'un lieu est dans `LocationStock`. Il doit changer uniquement par `StockMovement.save()`.
- Un emplacement avec du stock ou un historique ne se supprime pas : il se désactive.
- Le seuil de `LocationStock` est distinct du seuil du produit et vaut 0 par défaut. Les alertes des pages d'emplacement en dépendent.
- Un `cashier` n'accède qu'à son propre emplacement.
