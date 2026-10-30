# Tableaux de bord

Un tableau de bord résume l'activité sur une seule page. Chaque rôle arrive sur le sien après la connexion : direction, gérants, caissiers et comptables ont quatre pages distinctes. Les rôles limités au stock utilisent le tableau de bord du stock.

## Sommaire

- [Accueil et redirection selon le rôle](#accueil-et-redirection-selon-le-rôle)
- [Garde de rôle](#garde-de-rôle)
- [Tableau de bord Patron](#tableau-de-bord-patron)
- [Tableau de bord Gérant](#tableau-de-bord-gérant)
- [Tableau de bord Caisse](#tableau-de-bord-caisse)
- [Tableau de bord Comptabilité](#tableau-de-bord-comptabilité)
- [Liens de détail](#liens-de-détail)
- [Ce que voient les rôles limités au stock](#ce-que-voient-les-rôles-limités-au-stock)
- [À retenir](#à-retenir)

## Accueil et redirection selon le rôle

**Ce que voit l'utilisateur :** après la connexion, ou en cliquant sur le logo, il arrive directement sur la page de son rôle. Il ne voit pas de page d'accueil commune.

| Rôle | Destination | Adresse |
|---|---|---|
| `admin`, `owner` | `dashboards:patron` | `/dashboard/patron/` |
| `manager`, `boutique_manager` | `dashboards:gerant` | `/dashboard/gerant/` |
| `cashier` | `dashboards:caisse` | `/dashboard/caisse/` |
| `accountant` | `dashboards:comptable` | `/dashboard/comptable/` |
| `warehouse_manager`, `stock_manager` | `stock:dashboard` | `/stock/` |

**Ce qui se passe dans le code :**

1. `stock_control/urls.py` associe `/` à `home_dashboard()`, sous le nom `home`.
2. `home_dashboard()` (`apps/core/dashboard_views.py`) exige une connexion avec `@login_required`.
3. Si le compte n'a pas d'entreprise, elle rend `templates/home.html`, avec des compteurs à zéro.
4. Sinon, `dashboard_url_for()` cherche le rôle dans `DASHBOARD_ROLES`, le dictionnaire qui associe chaque tableau de bord à ses rôles.
5. Si le rôle n'y figure pas, la fonction renvoie `stock:dashboard` pour les rôles de stock et `pos:dashboard` pour les autres.
6. `home_dashboard()` redirige vers cette adresse.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| URL `home` | `stock_control/urls.py` | `home_dashboard()` |
| Routage | `apps/core/dashboard_views.py` | `home_dashboard()`, `dashboard_url_for()`, `DASHBOARD_ROLES` |
| Page sans entreprise | `templates/home.html` | Template |
| Tests | `tests/test_role_dashboards.py` | `TestHomeDispatch` |

**Règles à connaître :**

- `templates/home.html` affiche des cartes selon le rôle. Ses compteurs restent à zéro et ne sont pas cliquables, car la vue ne transmet aucun lien.
- Un compte qui a une entreprise mais un rôle vide part vers `pos:dashboard`. `sales_dashboard()` le renvoie vers `home`, ce qui crée une boucle de redirections. Attribuez toujours un rôle à ces comptes.

**Pour le tester :** connectez-vous avec un rôle `accountant`, puis ouvrez `/`. L'adresse devient `/dashboard/comptable/`.

## Garde de rôle

**Ce que voit l'utilisateur :** s'il saisit l'adresse d'un autre tableau de bord, il arrive sur le sien. Aucun message d'erreur ne s'affiche.

**Ce qui se passe dans le code :**

1. Les URL `dashboards:patron`, `dashboards:gerant`, `dashboards:caisse` et `dashboards:comptable` sont dans `apps/core/urls.py`, sous `/dashboard/`.
2. Chaque vue appelle d'abord `_guard()` (`apps/core/dashboard_views.py`) avec le nom de sa route.
3. `_guard()` lit les rôles permis dans `DASHBOARD_ROLES`. Si le rôle n'y est pas, elle renvoie une redirection vers `dashboard_url_for()`.
4. La vue retourne cette redirection s'il y en a une. Sinon, elle poursuit son calcul.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Garde | `apps/core/dashboard_views.py` | `_guard()` |
| Rôles permis | `apps/core/dashboard_views.py` | `DASHBOARD_ROLES` |
| Routes | `apps/core/urls.py` | `urlpatterns` |
| Tests | `tests/test_role_dashboards.py` | `test_owner_cannot_open_caisse()`, `test_cashier_cannot_open_patron()`, `test_accountant_cannot_open_gerant()` |

**Règles à connaître :**

- Un rôle n'ouvre qu'un seul de ces tableaux de bord. Par exemple, `owner` n'ouvre pas `dashboards:caisse`.
- `_guard()` s'applique seulement à ces quatre pages. `stock:dashboard`, `pos:dashboard` et `reports:dashboard` ont leurs propres contrôles.

**Pour le tester :** avec un rôle `cashier`, ouvrez `/dashboard/patron/`. Vous arrivez sur `/dashboard/caisse/`, sans message.

## Tableau de bord Patron

**Ce que voit l'utilisateur :** la vue de toute l'entreprise pour le mois en cours. Elle montre quatre indicateurs clés, ou KPI (chiffres résumés), puis des graphiques et des classements.

| KPI ou bloc | Calcul |
|---|---|
| CA du mois | Somme de `total_amount` des ventes `completed` depuis le 1er du mois |
| Bénéfice (marge) | CA du mois moins le coût d'achat des articles vendus |
| Valeur du stock | Somme de quantité × `purchase_price` du produit, sur les lignes `Stock` |
| Crédits en cours | Somme de `remaining_amount` des crédits `pending` ou `partial`, et nombre de clients |
| Graphique Chiffre d'affaires | Barres du CA des 6 derniers mois |
| Ventes par emplacement | 6 premiers emplacements du mois, avec une barre proportionnelle |
| Top produits | 5 premiers produits du mois par chiffre d'affaires |
| État du stock | Nombre de lignes en stock faible et en rupture |

**Ce qui se passe dans le code :**

1. `dashboards:patron` appelle `patron_dashboard()` (`apps/core/dashboard_views.py`), après `@login_required` et `_guard()`.
2. La vue filtre `Sale` sur l'entreprise et le statut `completed`.
3. `_cogs()` additionne `purchase_price` × `quantity` des `SaleItem` du mois. `SaleItem` conserve le prix d'achat au moment de la vente.
4. La vue parcourt `Stock` pour la valeur du stock et les alertes, avec `Stock.is_low_stock` (`apps/stock/models.py`).
5. `_sales_month_series()` calcule les barres du graphique. `_month_periods()` calcule les dates utilisées au clic.
6. `templates/dashboards/patron.html` affiche les cartes avec `templates/dashboards/_kpi.html`.
7. Le filtre `json_script` place les données du graphique dans la page. Chart.js, chargé depuis un CDN, dessine ensuite les barres.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| `dashboards:patron` | `apps/core/urls.py`, `apps/core/dashboard_views.py` | `patron_dashboard()` |
| Coût des ventes | `apps/core/dashboard_views.py` | `_cogs()` |
| Séries mensuelles | `apps/core/dashboard_views.py` | `_sales_month_series()`, `_month_periods()`, `_last_months()` |
| Page | `templates/dashboards/patron.html` | Template |
| Seuil de stock faible | `apps/stock/models.py` | `Stock.is_low_stock` |

**Règles à connaître :**

- Rôles autorisés : `admin` et `owner`.
- Le CA inclut tous les modes de paiement, dont le crédit, même si la carte indique « Chiffre d'affaires encaissé ».
- Le bénéfice ne déduit pas les dépenses.
- Les « références en stock » et les alertes comptent des lignes `Stock`. Un produit présent dans trois emplacements compte donc pour trois.

**Pour le tester :** avec un rôle `owner`, ouvrez `/dashboard/patron/`. Le nom de l'entreprise apparaît sous le titre. Cliquez sur une barre du graphique : la liste des ventes de ce mois s'ouvre.

## Tableau de bord Gérant

**Ce que voit l'utilisateur :** l'activité courante. `manager` voit toutes les boutiques. `boutique_manager` voit le nom de son emplacement sous le titre, et les chiffres de celui-ci.

| KPI ou bloc | Calcul |
|---|---|
| Ventes du jour | Somme et nombre des ventes `completed` du jour |
| Transferts en attente | Transferts `pending` ou `in_transit` |
| Stock faible | Lignes `Stock` faibles, avec le nombre de ruptures en dessous |
| Dépenses du mois | Somme et nombre des `Expense` depuis le 1er du mois |
| Graphique Ventes | Courbe du total quotidien sur 14 jours |
| À réapprovisionner | 6 premières lignes en stock faible |
| Activité récente | 8 dernières ventes |

**Ce qui se passe dans le code :**

1. `dashboards:gerant` appelle `gerant_dashboard()` (`apps/core/dashboard_views.py`), après `@login_required` et `_guard()`.
2. La variable `scoped` vaut `user.location` pour `boutique_manager`, et `None` pour `manager`.
3. Si `scoped` a une valeur, la vue filtre `Sale`, `Transfer` (source ou destination), `Stock` et `Expense` sur cet emplacement.
4. Elle parcourt `Stock`, et sépare les ruptures des stocks faibles.
5. Elle calcule le total de chaque jour sur 14 jours, avec les dates au format ISO (`AAAA-MM-JJ`) pour les clics.
6. `templates/dashboards/gerant.html` affiche le résultat, et Chart.js dessine la courbe.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| `dashboards:gerant` | `apps/core/urls.py`, `apps/core/dashboard_views.py` | `gerant_dashboard()` |
| Page | `templates/dashboards/gerant.html` | Template |
| Cartes KPI | `templates/dashboards/_kpi.html`, `templates/dashboards/_kpi_body.html` | Templates inclus |
| Modèle des transferts | `apps/transfers/models.py` | `Transfer` |
| Modèle des dépenses | `apps/accounting/models.py` | `Expense` |

**Règles à connaître :**

- Rôles autorisés : `manager` et `boutique_manager`.
- La liste « À réapprovisionner » n'affiche pas les ruptures : elles sont seulement comptées sur la carte.
- « Transferts en attente » ne compte pas les brouillons. Un transfert créé par le web y entre donc seulement après son envoi, quand il passe à `in_transit`.
- Un `boutique_manager` sans emplacement voit le texte « Toutes les boutiques » et les chiffres de toute l'entreprise.

**Pour le tester :** avec un rôle `boutique_manager` rattaché à une boutique, ouvrez `/dashboard/gerant/`. Le nom de la boutique s'affiche sous le titre. Avec un rôle `manager`, le texte indique « Toutes les boutiques ».

## Tableau de bord Caisse

**Ce que voit l'utilisateur :** la page « Ma journée », avec un gros bouton « Nouvelle vente ». Tous les chiffres concernent les ventes du jour du caissier connecté.

| KPI ou bloc | Calcul |
|---|---|
| Mes ventes du jour | Somme de `total_amount` de ses ventes `completed` du jour |
| Transactions | Nombre de ventes, et panier moyen (total ÷ nombre) |
| Session caisse | « Ouverte » ou « Fermée », selon sa dernière `CashRegisterSession` |
| Crédits accordés | Somme et nombre de ses ventes du jour payées à crédit |
| Mes ventes par heure | Barres du montant vendu chaque heure, de 7 h à 20 h |
| Mes dernières ventes | 8 dernières ventes du jour |

**Ce qui se passe dans le code :**

1. `dashboards:caisse` appelle `caisse_dashboard()` (`apps/core/dashboard_views.py`), après `@login_required` et `_guard()`.
2. La vue filtre `Sale` sur l'entreprise, le statut `completed`, l'utilisateur et la date du jour.
3. Elle prend la dernière `CashRegisterSession` du compte, triée sur `opened_at`. La session est ouverte si son statut vaut `open`.
4. Elle répartit les ventes par heure en Python, avec la fonction `timezone.localtime` de Django, pour rester compatible avec MySQL et SQLite.
5. `templates/dashboards/caisse.html` affiche le résultat, et Chart.js dessine les barres.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| `dashboards:caisse` | `apps/core/urls.py`, `apps/core/dashboard_views.py` | `caisse_dashboard()` |
| Page | `templates/dashboards/caisse.html` | Template |
| Session de caisse | `apps/accounting/models.py` | `CashRegisterSession` |
| Vente | `apps/pos/models.py` | `Sale` |

**Règles à connaître :**

- Rôle autorisé : `cashier`.
- Une vente réalisée avant 7 h ou après 20 h 59 compte dans les KPI, mais n'apparaît pas sur le graphique.
- La carte « Session caisse » affiche « Ouvrez une session pour vendre », mais `cashier_view()` et `create_sale_view()` (`apps/pos/views_frontend.py`) ne vérifient pas la session.
- `pos:dashboard`, atteint par « Tout voir », filtre par emplacement et non par caissier. Il peut donc inclure les ventes de collègues du même emplacement.

**Pour le tester :** avec un rôle `cashier`, enregistrez une vente avec `pos:cashier`, puis ouvrez `/dashboard/caisse/`. Le total, le nombre de transactions et la liste augmentent.

## Tableau de bord Comptabilité

**Ce que voit l'utilisateur :** les finances de toute l'entreprise, sans bouton de saisie sur cette page.

| KPI ou bloc | Calcul |
|---|---|
| Revenus (mois) | Somme de `total_amount` des ventes `completed` du mois |
| Dépenses (mois) | Somme de `amount` des `Expense` du mois |
| Bénéfice (marge) | Revenus moins coût d'achat, et marge en pourcentage des revenus |
| Crédits clients | Somme de `remaining_amount` des crédits `pending` ou `partial`, et nombre de clients |
| Revenus vs Dépenses | Barres groupées sur 6 mois |
| Dépenses par catégorie | Anneau et liste des 6 premières catégories du mois |
| Sessions de caisse à rapprocher | 6 dernières sessions fermées, avec montant attendu et écart |

**Ce qui se passe dans le code :**

1. `dashboards:comptable` appelle `comptable_dashboard()` (`apps/core/dashboard_views.py`), après `@login_required` et `_guard()`.
2. La vue filtre `Sale` et `Expense` sur l'entreprise, puis calcule les totaux du mois.
3. `_cogs()` donne le coût d'achat. La marge vaut bénéfice ÷ revenus × 100.
4. `_last_months()` et `_month_periods()` préparent les 6 mois du graphique et leurs dates.
5. La vue charge les `CashRegisterSession` au statut `closed`, triées sur `closed_at`.
6. `templates/dashboards/comptable.html` affiche le résultat, et Chart.js dessine les deux graphiques.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| `dashboards:comptable` | `apps/core/urls.py`, `apps/core/dashboard_views.py` | `comptable_dashboard()` |
| Page | `templates/dashboards/comptable.html` | Template |
| Dépenses | `apps/accounting/models.py` | `Expense` |
| Crédits | `apps/customers/models.py` | `CustomerCredit` |
| Calcul de l'écart | `apps/accounting/views.py` | `cash_session_close()` |

**Règles à connaître :**

- Rôle autorisé : `accountant`.
- Le bénéfice ne déduit pas les dépenses, comme sur le tableau de bord Patron.
- La liste des sessions contient les 6 dernières fermées, y compris celles dont l'écart est nul.
- `cash_session_close()` prend le solde d'ouverture comme montant attendu, sans ajouter les ventes. L'écart affiché vaut donc le solde de fermeture moins le solde d'ouverture.

**Pour le tester :** avec un rôle `accountant`, ouvrez `/dashboard/comptable/`. Cliquez sur une barre rouge : la liste des dépenses de ce mois s'ouvre. Cliquez sur une barre verte : la liste des ventes de ce mois s'ouvre.

## Liens de détail

**Ce que voit l'utilisateur :** la plupart des cartes, lignes et graphiques sont cliquables. Un clic ouvre la liste qui explique le chiffre : c'est le « drill-down », ou lien de détail.

| Tableau de bord | Élément cliqué | Cible |
|---|---|---|
| Patron | CA du mois | `pos:sales_list` avec `?date=month` |
| Patron | Bénéfice, Rapports détaillés | `reports:dashboard` |
| Patron | Valeur du stock, Stock faible | `stock:low_stock` |
| Patron | Rupture de stock | `stock:out_of_stock` |
| Patron | Crédits en cours | `customers:credit_list` |
| Patron | Barre du graphique | `pos:sales_list` avec `?start=` et `?end=` |
| Patron | Ligne d'emplacement | `pos:sales_list` avec `?location=` et `?date=month` |
| Patron | Ligne de produit | `products:product_detail` |
| Gérant | Ventes du jour, Historique des ventes | `pos:sales_list` avec `?date=today` |
| Gérant | Point de la courbe | `pos:sales_list` avec `?date=AAAA-MM-JJ` |
| Gérant | Transferts en attente | `transfers:list` |
| Gérant | Stock faible, Tout voir | `stock:low_stock` |
| Gérant | Dépenses du mois | `accounting:expense_list` |
| Gérant | Ligne à réapprovisionner | `stock:movements` avec `?product=` et `?location=` |
| Gérant | Ligne de vente récente | `pos:sale_receipt` |
| Caisse | Nouvelle vente | `pos:cashier` |
| Caisse | Mes ventes du jour, Tout voir, graphique | `pos:dashboard` |
| Caisse | Session caisse | `accounting:cash_session_list` |
| Caisse | Ligne de vente | `pos:sale_receipt` |
| Comptabilité | Revenus, Rapports et exports | `reports:dashboard` |
| Comptabilité | Dépenses (mois) | `accounting:expense_list` |
| Comptabilité | Crédits clients | `customers:credit_list` |
| Comptabilité | Barre verte du graphique | `pos:sales_list` avec `?start=` et `?end=` |
| Comptabilité | Barre rouge du graphique | `accounting:expense_list` avec `?start=` et `?end=` |
| Comptabilité | Ligne de catégorie | `accounting:expense_list` avec `?category=` et `?date=month` |
| Comptabilité | Toutes les sessions | `accounting:cash_session_list` |
| Comptabilité | Ligne de session | `accounting:cash_session_detail` |

**Ce qui se passe dans le code :**

1. Chaque vue construit ses liens et les place dans le contexte du template, comme `link_sales` ou `sales_base`.
2. `templates/dashboards/_kpi.html` reçoit le lien dans `href`, puis `templates/dashboards/_kpi_body.html` affiche la carte. Avec `href`, la carte est un lien. Sans `href`, c'est un simple bloc.
3. Pour les graphiques, le template lit les dates dans des données `json_script`, et l'option `onClick` de Chart.js change l'adresse de la page.
4. La vue cible lit les paramètres. Par exemple, `sales_list()` (`apps/pos/views_frontend.py`) lit `date`, `start`, `end` et `location`, et `expense_list()` (`apps/accounting/views.py`) lit `category`, `date`, `start` et `end`.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Construction des liens | `apps/core/dashboard_views.py` | `patron_dashboard()`, `gerant_dashboard()`, `caisse_dashboard()`, `comptable_dashboard()` |
| Carte KPI | `templates/dashboards/_kpi.html`, `templates/dashboards/_kpi_body.html` | Templates inclus |
| `pos:sales_list` | `apps/pos/views_frontend.py` | `sales_list()` |
| `pos:dashboard` | `apps/pos/views_frontend.py` | `sales_dashboard()` |
| `pos:cashier` | `apps/pos/views_frontend.py` | `cashier_view()` |
| `pos:sale_receipt` | `apps/pos/views_frontend.py` | `sale_receipt_pdf()` |
| `stock:low_stock` | `apps/stock/views_frontend.py` | `low_stock_view()` |
| `stock:out_of_stock` | `apps/stock/views_frontend.py` | `out_of_stock_view()` |
| `stock:movements` | `apps/stock/views_frontend.py` | `movements_view()` |
| `customers:credit_list` | `apps/customers/views.py` | `credit_list()` |
| `accounting:expense_list` | `apps/accounting/views.py` | `expense_list()` |
| `accounting:cash_session_list` | `apps/accounting/views.py` | `cash_session_list()` |
| `accounting:cash_session_detail` | `apps/accounting/views.py` | `cash_session_detail()` |
| `transfers:list` | `apps/transfers/views.py` | `transfer_list()` |
| `products:product_detail` | `apps/products/views.py` | `product_detail()` |
| `reports:dashboard` | `apps/reports/views.py` | `dashboard_view()` |
| Tests | `tests/test_role_dashboards.py` | `test_patron_chart_and_links()`, `test_comptable_chart_bases()`, `test_caisse_chart_base()`, `test_kpi_cards_are_links()` |

**Règles à connaître :**

- La cible garde ses propres contrôles de rôle : un lien ne donne aucun droit.
- Les cartes « Transactions » et « Crédits accordés » de Caisse, le « Bénéfice » de Comptabilité et l'anneau des catégories ne sont pas cliquables.
- `pos:sale_receipt` télécharge un PDF et écrit une entrée dans `ActionLog` à chaque ouverture.
- `sales_list()` affiche par défaut les ventes `completed`, comme les chiffres des tableaux de bord.
- La carte « Valeur du stock » du Patron mène à la liste du stock faible, pas à une page de valorisation.
- Une ligne sans emplacement (Patron) ou sans catégorie (Comptabilité) n'a pas de filtre propre : elle ouvre la liste générale de la cible.

**Pour le tester :** avec un rôle `owner`, cliquez sur une ligne de « Ventes par emplacement ». L'adresse contient `?location=` et `&date=month`, et la liste montre les ventes de cet emplacement.

## Ce que voient les rôles limités au stock

**Ce que voit l'utilisateur :** `warehouse_manager` et `stock_manager` n'ont pas de groupe « Tableau de bord » dans le menu. Ils arrivent sur la page « Gestion de Stock », avec un bouton « Nouvelle Entrée » en haut. Elle montre :

- les cartes Produits en Stock, Stock Faible, Rupture de Stock, Mouvements Aujourd'hui, Entrées ce Mois et Sorties ce Mois ;
- les graphiques Mouvements de Stock (14 jours), Stock par Catégorie, Types de Mouvements (ce mois) et Top 10 Produits en Stock ;
- les blocs Stock par Emplacement, Rupture de Stock, Alertes Stock Faible et Mouvements Récents ;
- les raccourcis Entrée Stock, Transfert, Emplacements et Rapports.

Leur menu contient « Stock » et « Configuration ». `warehouse_manager` a aussi « Emplacements » et « Transferts ».

**Ce qui se passe dans le code :**

1. `home_dashboard()` appelle `dashboard_url_for()`, qui renvoie `stock:dashboard` pour ces deux rôles.
2. `stock:dashboard` (`apps/stock/urls.py`) appelle `dashboard_view()` (`apps/stock/views_frontend.py`).
3. La vue contrôle le rôle, puis filtre `Stock` et `StockMovement` sur l'entreprise.
4. Elle calcule les compteurs, les séries de 14 jours, le stock par catégorie, les raisons de mouvement et le stock par emplacement.
5. Elle convertit les données en JSON pour Chart.js, et rend `apps/stock/templates/stock/dashboard.html`.
6. Au clic, les cartes et les graphiques ouvrent `stock:movements`, `stock:in_stock`, `stock:low_stock`, `stock:out_of_stock` ou `products:product_detail`. Les blocs d'emplacement ouvrent `locations:detail` ou `locations:stock`.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| `stock:dashboard` | `apps/stock/urls.py`, `apps/stock/views_frontend.py` | `dashboard_view()` |
| Page | `apps/stock/templates/stock/dashboard.html` | Template |
| Choix de la destination | `apps/core/dashboard_views.py` | `dashboard_url_for()` |
| `stock:entry` | `apps/stock/views_frontend.py` | `entry_view()` |
| `stock:in_stock` | `apps/stock/views_frontend.py` | `in_stock_view()` |
| Menu de ces rôles | `templates/base.html` | Conditions `{% if user.role in ... %}` |
| Tests | `tests/test_role_dashboards.py` | `test_stock_roles_land_on_stock_dashboard()` |

**Règles à connaître :**

- Rôles autorisés sur `stock:dashboard` : `admin`, `owner`, `manager`, `warehouse_manager`, `boutique_manager` et `stock_manager`.
- Ces rôles n'ouvrent aucun des quatre tableaux `dashboards:*` : `_guard()` les ramène sur `/stock/`.
- La page affiche les données de toute l'entreprise, même si le compte a un emplacement.
- Le raccourci « Rapports » s'affiche pour tous, mais `reports:dashboard` refuse ces deux rôles : ils reviennent à leur accueil avec un message d'erreur.
- `stock_manager` peut ouvrir `transfers:create` et `locations:dashboard` depuis les raccourcis « Transfert » et « Emplacements », même si son menu n'a pas ces entrées.

**Pour le tester :** connectez-vous avec un rôle `stock_manager`. Vous arrivez sur `/stock/`, et le menu ne propose que « Stock » et « Configuration ». Cliquez sur le raccourci « Rapports » : un message d'erreur s'affiche et vous revenez sur `/stock/`.

## À retenir

- `/` ne montre pas de page : `home_dashboard()` et `dashboard_url_for()` redirigent chaque rôle vers sa page.
- `DASHBOARD_ROLES` et `_guard()` décident qui ouvre quel tableau de bord.
- Tous les calculs sont dans `apps/core/dashboard_views.py`, et les pages dans `templates/dashboards/`.
- Le chiffre d'affaires compte les ventes `completed`, crédit inclus, et le bénéfice ne déduit pas les dépenses.
- Les rôles `warehouse_manager` et `stock_manager` utilisent `stock:dashboard`, et non un tableau `dashboards:*`.
