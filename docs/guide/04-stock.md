# Stock

Cette partie suit les quantités : ce qui entre, ce qui sort et ce qu'il reste. Elle sert aux rôles `admin`, `owner`, `manager`, `warehouse_manager`, `boutique_manager` et `stock_manager`. Lisez d'abord la première section : toute la logique du stock repose sur elle.

## Sommaire

- [StockMovement.save, la source unique de vérité](#stockmovementsave-la-source-unique-de-vérité)
- [Tableau de bord du stock](#tableau-de-bord-du-stock)
- [Formulaire d'entrée de stock](#formulaire-dentrée-de-stock)
- [Produits en stock](#produits-en-stock)
- [Stock faible](#stock-faible)
- [Rupture de stock](#rupture-de-stock)
- [Historique des mouvements](#historique-des-mouvements)
- [Stock dans l'administration Django](#stock-dans-ladministration-django)
- [À retenir](#à-retenir)

## StockMovement.save, la source unique de vérité

**Ce que voit l'utilisateur :** il n'a pas d'écran dédié. Il enregistre une entrée, une vente ou un transfert, et les quantités changent partout en même temps : tableau de bord, emplacements et rapports. Chaque changement laisse une ligne dans l'historique.

Un mouvement (`StockMovement`) est une ligne qui dit : tel produit est entré ou sorti, en telle quantité, à tel endroit, pour telle raison. La source unique de vérité signifie ceci : on ne modifie pas une quantité à la main, on crée un mouvement.

**Ce qui se passe dans le code :**

1. Un appelant exécute `StockMovement.objects.create()` : `entry_view()`, `Transfer.send()`, `Transfer.receive()`, `Transfer.cancel()` ou un signal de `apps/pos/signals.py`.
2. `StockMovement.save()` (`apps/stock/models.py`) note si la ligne est nouvelle, puis enregistre le mouvement.
3. Si la ligne existait déjà, la méthode s'arrête là.
4. Elle calcule l'écart : `+quantité` pour `entry`, `-quantité` pour `exit`.
5. Elle cherche ou crée la ligne `Stock` avec le produit, plus l'emplacement et l'entreprise s'ils sont renseignés. Elle ajoute l'écart.
6. Pour une entrée, elle met à jour `last_restock_date`.
7. Si le mouvement a un emplacement, elle cherche ou crée la ligne `LocationStock` (emplacement et produit), et y ajoute le même écart.
8. Les vues et les templates lisent ensuite `Stock` ou `LocationStock`.

Voici quelle table alimente quel écran :

| Table | Écrans qui la lisent |
|---|---|
| `Stock` | `stock:dashboard` (compteurs et listes), `stock:in_stock`, `stock:low_stock`, `stock:out_of_stock`, `products:product_detail` |
| `LocationStock` | `stock:dashboard` (cartes par emplacement), `locations:dashboard`, `locations:detail`, `locations:stock`, `products:product_list`, `transfers:create` |

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Mise à jour du stock | `apps/stock/models.py` | `StockMovement.save()` |
| Stock par ligne | `apps/stock/models.py` | `Stock` |
| Stock par emplacement | `apps/locations/models.py` | `LocationStock` |
| Entrée manuelle | `apps/stock/views_frontend.py` | `entry_view()` |
| Transferts | `apps/transfers/models.py` | `Transfer.send()`, `Transfer.receive()`, `Transfer.cancel()` |
| Vente | `apps/pos/signals.py` | `create_stock_movement_on_sale_item()` |
| Annulation et remboursement | `apps/pos/signals.py` | `handle_sale_status_changes()` |
| API | `api/v1/views/stock.py` | `StockMovementViewSet.perform_create()` |

**Règles à connaître :**

- `save()` agit seulement à la création. Modifier ou supprimer un mouvement existant ne recalcule pas le stock.
- `quantity` reste positive. C'est `movement_type` qui donne le sens du mouvement.
- `save()` ne vérifie pas la quantité disponible : une sortie peut rendre le stock négatif. `Transfer.send()` fait ce contrôle avant de créer ses sorties.
- Le commentaire du modèle parle d'agrégat, mais `Stock` a en général une ligne par produit et par emplacement. Pour avoir le total d'un produit, il faut additionner ses lignes.
- Sans emplacement, `LocationStock` n'est pas mis à jour. Le mouvement s'ajoute alors à la ligne `Stock` trouvée ou créée pour ce produit et cette entreprise. La ligne trouvée peut appartenir à n'importe quel emplacement.
- Si plusieurs lignes correspondent à un mouvement sans emplacement, `get_or_create()` lève une erreur. Le mouvement est déjà enregistré à ce moment-là, mais le stock n'a pas changé.
- `StockMovement.save()` n'ouvre pas de transaction. Une erreur après le premier enregistrement laisse donc le mouvement en base.

**Pour le tester :** en `manager`, notez la quantité d'un produit dans `/locations/<pk>/stock/`. Ajoutez 5 unités à cet emplacement avec `stock:entry`. La quantité augmente de 5 dans `locations:stock` et dans `stock:in_stock`, et une ligne apparaît dans `stock:movements`.

## Tableau de bord du stock

**Ce que voit l'utilisateur :** des cartes cliquables (produits en stock, stock faible, rupture, mouvements du jour, entrées et sorties du mois), quatre graphiques, des cartes par emplacement, les listes d'alertes et les derniers mouvements. Un clic sur une colonne ou une part de graphique ouvre la liste correspondante.

**Ce qui se passe dans le code :**

1. `/stock/` est déclarée sous le nom `stock:dashboard` dans `apps/stock/urls.py` et appelle `dashboard_view()`.
2. La vue contrôle le rôle, puis filtre `Stock` et `StockMovement` par entreprise.
3. Elle calcule les compteurs. Une boucle Python classe chaque ligne `Stock` en rupture (quantité à 0 ou moins) ou en stock faible (`Stock.is_low_stock`).
4. Elle prépare en JSON les données de 14 jours de mouvements, du stock par catégorie, des raisons du mois et du top 10 des produits.
5. Pour chaque emplacement actif, elle calcule le total, le nombre de produits et les alertes à partir de `LocationStock`.
6. `apps/stock/templates/stock/dashboard.html` affiche le tout et dessine les graphiques avec Chart.js.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| URL `stock:dashboard` | `apps/stock/urls.py` | `dashboard_view()` |
| Vue | `apps/stock/views_frontend.py` | `dashboard_view()` |
| Modèles | `apps/stock/models.py` | `Stock`, `StockMovement` |
| Cartes par emplacement | `apps/locations/models.py` | `Location`, `LocationStock` |
| Template | `apps/stock/templates/stock/dashboard.html` | Aucune |
| Lien de menu | `templates/base.html` | Aucune |

**Règles à connaître :**

- Rôles autorisés : `admin`, `owner`, `manager`, `warehouse_manager`, `boutique_manager`, `stock_manager`. Les autres sont renvoyés vers `home`.
- « Produits en stock » compte les produits distincts ayant une quantité positive.
- Les alertes comptent des lignes `Stock`. Un même produit peut donc compter une fois par emplacement.
- Les cartes par emplacement utilisent le seuil de `LocationStock`, et non celui du produit. Leurs alertes incluent aussi les ruptures.
- Sur le graphique des 14 jours, un clic prend la première série affichée. Le lien porte donc `?type=entry`, même sur une barre rouge. Pour voir les sorties d'un jour, masquez « Entrées » en cliquant sur sa légende, puis cliquez sur la colonne.

**Pour le tester :** en `stock_manager`, ouvrez `/stock/`. Cliquez sur une colonne du graphique des 14 jours : `stock:movements` s'ouvre, filtré sur ce jour, et le bandeau rappelle la date.

## Formulaire d'entrée de stock

**Ce que voit l'utilisateur :** un formulaire avec une recherche de produit, la quantité, le coût unitaire, l'emplacement, la raison, la référence et les notes. Le bouton reste désactivé tant qu'aucun produit n'est choisi. Le coût se remplit seul quand on choisit un produit dont le prix de vente est positif. La touche Entrée choisit le premier produit de la liste. Si le catalogue est vide, la page invite à créer un produit, ou à contacter un responsable pour les rôles qui ne peuvent pas en créer.

**Ce qui se passe dans le code :**

1. `/stock/entry/` est déclarée sous le nom `stock:entry` et appelle `entry_view()`.
2. En GET, la vue charge les produits actifs de l'entreprise et les transforme en `products_json`.
3. Dans `apps/stock/templates/stock/entry.html`, `stockEntryForm()` crée la recherche avec Alpine.js. `filtered()` filtre la liste et `select()` retient le produit.
4. En POST, la vue valide le produit, la quantité, le coût et l'emplacement.
5. Si tout est correct, elle exécute `StockMovement.objects.create()` avec `movement_type='entry'`.
6. `StockMovement.save()` met à jour `Stock` et `LocationStock`.
7. La vue redirige vers `next` s'il est valide, sinon vers `stock:dashboard`.

Paramètres acceptés dans l'adresse :

| Paramètre | Effet | Si la valeur n'est pas retenue |
|---|---|---|
| `?product=<id>` | Présélectionne le produit et remplit le coût. | Produit inconnu ou inactif : rien n'est présélectionné. |
| `?location=<id>` | Fixe l'emplacement, affiché avec un cadenas, sans liste. | Emplacement inconnu ou inactif : la liste normale s'affiche. |
| `?next=<adresse>` | Indique la page de retour après l'enregistrement. | Adresse absente ou externe : retour vers `stock:dashboard`. |

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| URL `stock:entry` | `apps/stock/urls.py` | `entry_view()` |
| Vue | `apps/stock/views_frontend.py` | `entry_view()` |
| Modèle | `apps/stock/models.py` | `StockMovement` |
| Recherche de produit | `apps/stock/templates/stock/entry.html` | `stockEntryForm()` |

**Règles à connaître :**

- Rôles autorisés : `admin`, `owner`, `manager`, `warehouse_manager`, `boutique_manager`, `stock_manager`.
- Le produit doit être actif et appartenir à l'entreprise. La quantité doit être supérieure à 0. Le coût est facultatif et ne peut pas être négatif.
- Le coût est prérempli avec le prix de vente (`sale_price`), et non avec le prix d'achat. Il reste modifiable.
- Si aucun emplacement n'est choisi, la vue utilise celui de l'utilisateur. S'il n'en a pas, le mouvement est créé sans emplacement. Voir les effets dans la première section.
- `next` n'est accepté que s'il pointe vers le même site.
- La liste des raisons propose Achat (par défaut), Retour Client, Correction, Stock Initial, Transfert Entrant et Autre. Choisir « Transfert Entrant » ici n'a aucun lien avec un `Transfer`.
- La page ne fait que des entrées. Aucune page de l'application n'enregistre une sortie manuelle comme une perte ou une casse. Ces raisons existent dans le modèle, et l'API `stock-movements` permet de créer de tels mouvements, comme l'administration Django (voir la dernière section).

**Pour le tester :** en `manager`, ouvrez une page d'emplacement et cliquez sur « Entrée » pour un produit. Le produit est présélectionné et l'emplacement est verrouillé. Enregistrez 3 unités : vous revenez à la page d'emplacement, avec 3 unités de plus.

## Produits en stock

**Ce que voit l'utilisateur :** le nombre de produits et d'unités en stock, puis deux onglets. « Par produit » donne une ligne par produit, avec le nombre d'emplacements et le total. « Détail des unités » donne une ligne par produit et par emplacement. Il peut filtrer et exporter.

**Ce qui se passe dans le code :**

1. `/stock/in-stock/` est déclarée sous le nom `stock:in_stock` et appelle `in_stock_view()`.
2. La vue garde les lignes `Stock` de l'entreprise avec une quantité positive.
3. Elle applique `?search=` (nom, SKU, code-barres), `?location=` et `?category=`.
4. Elle prépare `stock_rows` pour le détail, et `by_product` pour le regroupement par produit.
5. Selon `?tab=units`, `export_list_response()` choisit le contenu à exporter lorsque `?export=` est présent.
6. `apps/stock/templates/stock/in_stock.html` affiche les onglets, que Alpine.js change sans recharger la page.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| URL `stock:in_stock` | `apps/stock/urls.py` | `in_stock_view()` |
| Vue | `apps/stock/views_frontend.py` | `in_stock_view()` |
| Modèle | `apps/stock/models.py` | `Stock` |
| Export | `apps/core/exports.py` | `export_list_response()` |
| Template | `apps/stock/templates/stock/in_stock.html` | Aucune |

**Règles à connaître :**

- Rôles autorisés : les mêmes que pour `stock:dashboard`.
- Le contenu de l'export dépend de `tab` dans l'adresse. Après un simple clic sur un onglet, l'adresse ne change pas : relancez le filtre pour exporter cet onglet.
- Le total reprend les lignes `Stock` filtrées. Une ligne sans emplacement s'affiche sous « Sans emplacement ».

**Pour le tester :** en `warehouse_manager`, ouvrez `/stock/in-stock/` et filtrez un emplacement. Les deux onglets se limitent à cet emplacement, et le total d'unités change.

## Stock faible

**Ce que voit l'utilisateur :** la liste des lignes qui ont encore du stock, mais qui ont atteint le seuil minimum du produit. Chaque ligne a un lien vers le produit et un lien de réapprovisionnement. Il peut exporter en PDF ou en Excel.

**Ce qui se passe dans le code :**

1. `/stock/low-stock/` est déclarée sous le nom `stock:low_stock` et appelle `low_stock_view()`.
2. La vue lit les lignes `Stock` de l'entreprise.
3. Une boucle Python garde celles où `Stock.is_low_stock` est vrai et où la quantité est positive.
4. `_stock_list_export()` renvoie le fichier si `?export=` est présent.
5. `apps/stock/templates/stock/stock_list.html` affiche la liste.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| URL `stock:low_stock` | `apps/stock/urls.py` | `low_stock_view()` |
| Règle de seuil | `apps/stock/models.py` | `Stock.is_low_stock` |
| Export | `apps/stock/views_frontend.py` | `_stock_list_export()` |
| Template partagé | `apps/stock/templates/stock/stock_list.html` | Aucune |
| Liens depuis les tableaux de bord | `apps/core/dashboard_views.py` | Aucune |

**Règles à connaître :**

- Rôles autorisés : les mêmes que pour `stock:dashboard`.
- Une ligne est faible si sa quantité est positive et inférieure ou égale à `Product.min_stock_threshold`. Ce seuil s'applique à chaque ligne d'emplacement, pas au total du produit.
- Avec un seuil à 0, un produit n'apparaît jamais ici.
- Quand la quantité est sous le seuil, la colonne « Manquant » affiche seulement un tiret, sans valeur calculée. Quand elle est égale au seuil, la colonne affiche 0.

**Pour le tester :** en `manager`, réglez le seuil d'un produit au-dessus de sa quantité dans un emplacement. Ouvrez `/stock/low-stock/` : la ligne apparaît avec cet emplacement.

## Rupture de stock

**Ce que voit l'utilisateur :** la même page que le stock faible, avec un titre rouge, pour les lignes dont la quantité est nulle ou négative.

**Ce qui se passe dans le code :**

1. `/stock/out-of-stock/` est déclarée sous le nom `stock:out_of_stock` et appelle `out_of_stock_view()`.
2. La vue filtre les lignes `Stock` de l'entreprise avec une quantité inférieure ou égale à 0.
3. `_stock_list_export()` renvoie le fichier si `?export=` est présent.
4. La vue transmet la liste sous le nom `low_stock_items`, pour réutiliser `apps/stock/templates/stock/stock_list.html`.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| URL `stock:out_of_stock` | `apps/stock/urls.py` | `out_of_stock_view()` |
| Modèle | `apps/stock/models.py` | `Stock` |
| Export | `apps/stock/views_frontend.py` | `_stock_list_export()` |
| Template partagé | `apps/stock/templates/stock/stock_list.html` | Aucune |

**Règles à connaître :**

- Rôles autorisés : les mêmes que pour `stock:dashboard`.
- La rupture se lit ligne par ligne. Un produit vide dans une boutique est listé, même s'il reste du stock dans un dépôt.
- Un produit qui n'a jamais eu de mouvement n'apparaît pas pour un utilisateur rattaché à une entreprise. En effet, sa ligne initiale créée par `product_create()` n'a pas d'entreprise.

**Pour le tester :** en `manager`, transférez toute la quantité d'un produit depuis un emplacement. Une fois le transfert envoyé, `/stock/out-of-stock/` affiche ce produit avec cet emplacement.

## Historique des mouvements

**Ce que voit l'utilisateur :** toutes les entrées et sorties, de la plus récente à la plus ancienne, avec le produit, la quantité, la raison, l'emplacement, l'auteur et la référence. Il peut filtrer, exporter, et voir l'historique d'un seul produit depuis une page d'emplacement. Le bandeau de filtre propose « Tout voir » et, si un emplacement est filtré, « Retour à l'emplacement ».

**Ce qui se passe dans le code :**

1. `/stock/movements/` est déclarée sous le nom `stock:movements` et appelle `movements_view()`.
2. La vue lit les `StockMovement` de l'entreprise, triés par date décroissante.
3. Elle applique `?type=`, `?reason=`, `?date=`, `?search=`, `?product=` et `?location=`.
4. `export_list_response()` renvoie le fichier si `?export=` est présent. Les raisons y sont traduites avec `REASON_LABELS`.
5. Sinon, `Paginator` découpe la liste en pages de 50 lignes.
6. `apps/stock/templates/stock/movements.html` affiche le tableau et, si besoin, un bandeau qui rappelle le produit, l'emplacement ou le jour filtré.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| URL `stock:movements` | `apps/stock/urls.py` | `movements_view()` |
| Vue | `apps/stock/views_frontend.py` | `movements_view()` |
| Modèle | `apps/stock/models.py` | `StockMovement` |
| Export | `apps/core/exports.py` | `export_list_response()` |
| Template | `apps/stock/templates/stock/movements.html` | Aucune |

**Règles à connaître :**

- Rôles autorisés : les mêmes que pour `stock:dashboard`.
- `?date=` accepte `today`, `week`, `month` ou un jour au format `AAAA-MM-JJ`. Une date invalide est ignorée.
- La recherche porte sur le nom du produit, la référence et les notes.
- La page affiche les codes de raison bruts, par exemple `transfer_in`, car le champ `reason` n'a pas de `choices`. Seul l'export les traduit.
- La colonne Type de la page affiche « Entry » ou « Exit ». L'export affiche « Entrée » ou « Sortie ».
- La page arrondit les quantités à l'entier. L'export garde les décimales.
- Le filtre de raison ne propose pas `other_entry` ni `other_exit`.
- Les liens de pagination ne conservent pas `?product=` ni `?location=`.

**Pour le tester :** en `manager`, ouvrez une page d'emplacement et cliquez sur « Historique » pour un produit. Le bandeau indique le produit et l'emplacement, et le tableau ne montre que leurs mouvements.

## Stock dans l'administration Django

**Ce que voit l'utilisateur :** un compte qui a `is_staff` trouve les lignes de stock sous `/admin/stock/stock/` et les mouvements sous `/admin/stock/stockmovement/`, avec recherche et filtres. Ces pages ne remplacent pas les écrans précédents.

**Ce qui se passe dans le code :**

1. `StockAdmin` (`apps/stock/admin.py`) affiche chaque ligne `Stock`. Le champ `quantity` y est modifiable.
2. Enregistrer une ligne `Stock` n'appelle pas `StockMovement.save()` : aucun mouvement n'est créé.
3. `StockMovementAdmin` propose le produit, le type, la raison, la quantité, le coût, la référence, les notes et l'utilisateur.
4. Ajouter un mouvement ici appelle `StockMovement.save()`, comme les autres appelants.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Lignes de stock | `apps/stock/admin.py` | `StockAdmin` |
| Mouvements | `apps/stock/admin.py` | `StockMovementAdmin` |

**Règles à connaître :**

- Corriger `quantity` dans `StockAdmin` ne change pas `LocationStock` et ne laisse aucune trace dans l'historique. Préférez un mouvement.
- Le formulaire de `StockMovementAdmin` n'a ni emplacement ni entreprise. Ce mouvement suit donc la règle des mouvements sans emplacement décrite dans la première section : `LocationStock` ne change pas, et une erreur survient si le produit a plusieurs lignes `Stock`.
- Sans entreprise, ce mouvement n'apparaît pas dans `stock:movements` pour un utilisateur rattaché à une entreprise.

**Pour le tester :** avec un compte qui a `is_staff`, ouvrez `/admin/stock/stockmovement/`. Filtrez par type : vous retrouvez les mouvements créés par les entrées et les transferts.

## À retenir

- Pour changer une quantité, créez un `StockMovement`. N'écrivez jamais directement dans `Stock` ni dans `LocationStock`.
- `StockMovement.save()` met à jour `Stock`, puis `LocationStock` si le mouvement a un emplacement.
- `save()` n'agit qu'à la création et ne bloque pas un stock négatif.
- Les pages de stock lisent surtout `Stock` et le seuil du produit. Les pages d'emplacement lisent `LocationStock` et leur propre seuil.
- La page `stock:entry` ne fait que des entrées. Les sorties viennent des ventes, des transferts, de l'API ou de l'administration Django.
