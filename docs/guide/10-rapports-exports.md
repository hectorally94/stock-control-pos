# Rapports et exports

Cette partie donne une vue chiffrée de l'activité et permet de sortir les données en fichiers Excel ou PDF. Le tableau de bord et les quatre rapports Excel servent au patron, au gérant et au comptable. L'export de liste réutilisable est disponible sur de nombreuses pages, pour les rôles qui ont accès à ces pages. Le code se trouve dans `apps/reports/` et `apps/core/exports.py`.

## Sommaire

- [Tableau de bord des rapports](#tableau-de-bord-des-rapports)
- [Panneau des rapports par emplacement](#panneau-des-rapports-par-emplacement)
- [Rapport Excel des ventes](#rapport-excel-des-ventes)
- [Rapport Excel d'inventaire](#rapport-excel-dinventaire)
- [Rapport Excel des dépenses](#rapport-excel-des-dépenses)
- [Rapport Excel des clients](#rapport-excel-des-clients)
- [Export de liste en PDF et Excel](#export-de-liste-en-pdf-et-excel)
- [Reçus de vente](#reçus-de-vente)
- [À retenir](#à-retenir)

## Tableau de bord des rapports

**Ce que voit l'utilisateur :** en haut, la période (du premier jour du mois à aujourd'hui) et quatre boutons qui téléchargent les rapports Excel (Ventes, Stock, Dépenses, Clients). Viennent ensuite quatre cartes : Ventes Aujourd'hui, Chiffre d'Affaires (Mois), Dépenses (Mois) et Bénéfice Net. Le panneau par emplacement et le suivi des crédits suivent. Plus bas se trouvent les graphiques, les produits les plus vendus, l'état du stock par emplacement et des raccourcis. La plupart des cartes et des graphiques sont cliquables et ouvrent la liste détaillée correspondante. La carte Bénéfice Net ne l'est pas. Dans l'état du stock, le nom d'un emplacement ouvre `locations:detail` et ses deux chiffres ouvrent `locations:stock`.

**Ce qui se passe dans le code :**

1. L'adresse `reports:dashboard` appelle `dashboard_view()` dans `apps/reports/views.py`.
2. La vue vérifie le rôle, puis prend l'entreprise de l'utilisateur.
3. Elle calcule les ventes du jour et du mois (`Sale` au statut `completed`), les dépenses du mois (`Expense`) et le bénéfice.
4. Elle calcule le suivi des crédits à partir de `CustomerCredit` et `CreditPayment` (`apps/customers/models.py`).
5. Elle prépare les données des graphiques : ventes sur 7 jours, ventes et dépenses sur 6 mois, top 5 des catégories, modes de paiement, top 10 des produits (`SaleItem`) et ventes par heure.
6. Elle calcule l'état du stock par emplacement à partir de `Location` et `LocationStock` (`apps/locations/models.py`).
7. Elle transforme les données des graphiques en JSON (un format texte lisible par JavaScript) et affiche `apps/reports/templates/reports/dashboard.html`.
8. Dans le template, Chart.js dessine les graphiques. Un clic ouvre `pos:sales_list` ou `accounting:expense_list` avec les filtres du point choisi.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Tableau de bord, `reports:dashboard` | `apps/reports/views.py` | `dashboard_view()` |
| Page et graphiques | `apps/reports/templates/reports/dashboard.html` | |
| Détail des ventes, `pos:sales_list` | `apps/pos/views_frontend.py` | `sales_list()` |
| Détail des dépenses, `accounting:expense_list` | `apps/accounting/views.py` | `expense_list()` |
| Détail des crédits, `customers:credit_list` | `apps/customers/views.py` | `credit_list()` |
| Lien du menu | `templates/base.html` | |

**Règles à connaître :**

- Rôles autorisés : `admin`, `owner`, `manager` et `accountant`. Les autres rôles sont renvoyés vers `home` avec un message d'erreur.
- **Bénéfice Net** vaut ici le chiffre d'affaires du mois moins les dépenses du mois. Le coût d'achat des produits n'est pas déduit.
- **Encaissé** vaut le chiffre d'affaires du mois, moins le crédit donné ce mois, plus les remboursements de ce mois.
- **Crédit en Cours** additionne le reste à payer des crédits aux statuts `pending` et `partial`, quelle que soit leur date.
- Le graphique sur 6 mois recule par pas de 30 jours. Selon le jour, un mois peut donc apparaître deux fois et un autre manquer. Les mois y sont écrits avec le format anglais (par exemple `Aug 2026`).
- Les dépenses du mois comptent aussi celles datées plus tard dans le mois ou dans le futur, car seule la date de début est filtrée.
- Le graphique par heure couvre de 6 h à 21 h 59. Une vente en dehors de ces heures n'y apparaît pas, mais elle reste dans les totaux.
- Pour un utilisateur sans entreprise, l'état du stock et la liste des emplacements restent vides.
- Les raccourcis du bas (`pos:cashier`, `stock:dashboard`, `transfers:create` et `/admin/`) s'affichent pour tous les rôles de la page. Chaque destination applique ses propres règles.
- `chart_data_api()` existe dans `apps/reports/views.py`, mais aucune route ne pointe vers elle. De même, aucun code n'utilise `apps/reports/cache_utils.py`.

**Pour le tester :** avec le rôle `manager`, ouvrez `/reports/`. Cliquez sur la carte Chiffre d'Affaires (Mois) : la liste des ventes du mois s'ouvre sur `/pos/sales/?date=month`. Avec le rôle `cashier`, `/reports/` renvoie vers l'accueil.

## Panneau des rapports par emplacement

**Ce que voit l'utilisateur :** sur le tableau de bord, le panneau « Rapports par Emplacement » contient une liste d'emplacements et des cartes d'actions. Par défaut, « Tous les emplacements » est sélectionné. Quand on choisit un emplacement, les liens des cartes visent cet emplacement, sans recharger la page.

| Carte | Action | Destination |
|---|---|---|
| Mouvements de Stock | Excel, PDF, Voir | `stock:movements` avec `?export=` et `?location=` |
| Ventes (du premier jour du mois à aujourd'hui) | Excel | `reports:export_sales` avec `?location=` |
| Ventes (du premier jour du mois à aujourd'hui) | Voir | `pos:sales_list` avec `?date=month` et `?location=` |
| Inventaire | Excel | `reports:export_inventory` avec `?location=` |

**Ce qui se passe dans le code :**

1. `dashboard_view()` prépare `report_locations` : les emplacements actifs de l'entreprise, triés par type et par nom.
2. `apps/reports/templates/reports/dashboard.html` crée une petite variable Alpine.js `loc` avec `x-data` et la relie à la liste avec `x-model`. Alpine.js est la bibliothèque des petites interactions de la page.
3. Les liens utilisent l'attribut `:href`. Ils ajoutent `location=` seulement si un emplacement est choisi.
4. Au clic, la vue de destination reçoit le paramètre : `movements_view()`, `sales_list()`, `export_sales_report()` ou `export_inventory_report()`.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Liste des emplacements | `apps/reports/views.py` | `dashboard_view()` |
| Panneau | `apps/reports/templates/reports/dashboard.html` | |
| Mouvements, `stock:movements` | `apps/stock/views_frontend.py` | `movements_view()` |
| Ventes, `pos:sales_list` | `apps/pos/views_frontend.py` | `sales_list()` |
| Excel des ventes, `reports:export_sales` | `apps/reports/views.py` | `export_sales_report()` |
| Excel de l'inventaire, `reports:export_inventory` | `apps/reports/views.py` | `export_inventory_report()` |

**Règles à connaître :**

- La carte « Mouvements de Stock » s'affiche pour `admin`, `owner` et `manager`, pas pour `accountant`.
- Les rapports des dépenses et des clients n'ont pas de version par emplacement.
- Les boutons Excel du haut de la page ignorent l'emplacement choisi dans le panneau.

**Pour le tester :** avec le rôle `manager`, choisissez une boutique, puis cliquez sur Excel dans la carte Inventaire. Le nom du fichier contient le code de la boutique et le fichier indique son nom en haut de la première feuille. Avec le rôle `accountant`, la carte des mouvements n'apparaît pas.

## Rapport Excel des ventes

**Ce que voit l'utilisateur :** un fichier `Rapport_Ventes_<début>_<fin>.xlsx` est téléchargé. Il contient trois feuilles.

| Feuille | Contenu |
|---|---|
| Résumé | Période, nombre de ventes, chiffre d'affaires, panier moyen, répartition par mode de paiement |
| Ventes Détaillées | Une ligne par vente : date, numéro, client, caissier, emplacement, montants, paiement, statut |
| Articles Vendus | Une ligne par article : produit, catégorie, quantité, prix de vente, prix d'achat, total, bénéfice |

**Ce qui se passe dans le code :**

1. L'adresse `reports:export_sales` appelle `export_sales_report()` dans `apps/reports/views.py`.
2. La vue vérifie le rôle, puis lit `start_date` et `end_date`. Sans ces deux dates, elle prend du premier jour du mois à aujourd'hui.
3. Elle prépare les filtres facultatifs : `customer_id`, `cashier_id`, `payment_method` et `location`.
4. Elle appelle `sales_report()` dans `apps/reports/utils/excel_generator.py`.
5. `sales_report()` lit les `Sale` au statut `completed` de l'entreprise et crée le classeur, c'est-à-dire le fichier Excel et ses feuilles, avec openpyxl.
6. `_report_header()`, `apply_header_style()`, `format_currency()` et `auto_adjust_column_width()` mettent en forme les feuilles.
7. La vue place le classeur dans la réponse, puis crée une ligne `ActionLog` (`apps/accounts/models.py`).

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Téléchargement, `reports:export_sales` | `apps/reports/views.py` | `export_sales_report()` |
| Création du classeur | `apps/reports/utils/excel_generator.py` | `sales_report()` |
| Bénéfice par article (propriété du modèle) | `apps/pos/models.py` | `SaleItem.profit` |

**Règles à connaître :**

- Rôles autorisés : `admin`, `owner`, `manager` et `accountant`. Les autres reçoivent une erreur 403 (accès refusé).
- Seules les ventes `completed` sont incluses. La colonne Statut affiche donc toujours la même valeur.
- Le bénéfice d'un article vaut (prix de vente - prix d'achat) x quantité.
- Les filtres client, caissier et mode de paiement n'existent que dans l'adresse. Aucun champ de la page ne les propose.
- Une date mal écrite dans l'adresse provoque une erreur 500. Si une seule des deux dates est donnée, le mois en cours est utilisé.

**Pour le tester :** avec le rôle `accountant`, ouvrez `/reports/` et cliquez sur le bouton Ventes. Dans le fichier, le nombre de ventes de « Résumé » est égal au nombre de lignes de « Ventes Détaillées ».

## Rapport Excel d'inventaire

**Ce que voit l'utilisateur :** un fichier `Rapport_Inventaire_<date>.xlsx` est téléchargé. Le code de l'emplacement est ajouté au nom si un emplacement est choisi. Le bouton du haut de la page s'appelle « Stock ». Le fichier contient trois feuilles.

| Feuille | Contenu |
|---|---|
| Stock par Produit | Une ligne par produit : quantité totale, seuil, statut, nombre d'emplacements, coût unitaire, valeur, et une ligne TOTAL |
| Détail par Emplacement | Une ligne par produit et par emplacement, avec la quantité et le statut |
| Produits Populaires | Produits actifs marqués populaires, avec prix de vente et stock actuel |

**Ce qui se passe dans le code :**

1. L'adresse `reports:export_inventory` appelle `export_inventory_report()` dans `apps/reports/views.py`.
2. La vue vérifie le rôle. Si `location` est présent, elle cherche l'emplacement dans l'entreprise de l'utilisateur.
3. Elle appelle `inventory_report()` dans `apps/reports/utils/excel_generator.py`.
4. `inventory_report()` lit `Stock` (`apps/stock/models.py`) et additionne les quantités par produit pour la première feuille.
5. Elle écrit le détail par emplacement, puis lit les `Product` populaires (`apps/products/models.py`).
6. La vue place le classeur dans la réponse et crée une ligne `ActionLog`.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Téléchargement, `reports:export_inventory` | `apps/reports/views.py` | `export_inventory_report()` |
| Création du classeur | `apps/reports/utils/excel_generator.py` | `inventory_report()` |
| Style de la ligne TOTAL | `apps/reports/utils/excel_generator.py` | `apply_total_row_style()` |
| Stock lu | `apps/stock/models.py` | `Stock` |

**Règles à connaître :**

- Rôles autorisés : `admin`, `owner`, `manager` et `accountant`. Les autres reçoivent une erreur 403.
- Le rapport n'a pas de période : il montre le stock au moment du téléchargement.
- Le statut vaut « Rupture » à 0 ou moins, « Stock faible » jusqu'au seuil du produit, sinon « En stock ».
- La valeur utilise le prix d'achat actuel du produit.
- Un produit sans ligne `Stock` n'apparaît pas dans les deux premières feuilles.
- Si `location` ne correspond à aucun emplacement de l'entreprise, le paramètre est ignoré et le rapport couvre tous les emplacements.

**Pour le tester :** avec le rôle `manager`, téléchargez le rapport sans emplacement. Un produit présent dans deux emplacements a une seule ligne dans la première feuille et deux lignes dans la deuxième.

## Rapport Excel des dépenses

**Ce que voit l'utilisateur :** un fichier `Rapport_Depenses_<début>_<fin>.xlsx` est téléchargé. Il contient deux feuilles.

| Feuille | Contenu |
|---|---|
| Dépenses par Catégorie | Pour chaque catégorie : montant, nombre, montant moyen, part du total, et une ligne TOTAL |
| Dépenses Détaillées | Une ligne par dépense : date, catégorie, description, montant, paiement, fournisseur, référence, emplacement, utilisateur |

**Ce qui se passe dans le code :**

1. L'adresse `reports:export_expenses` appelle `export_expense_report()` dans `apps/reports/views.py`.
2. La vue vérifie le rôle, puis lit `start_date` et `end_date`. Sans ces deux dates, elle prend le mois en cours.
3. Elle appelle `expense_report()` dans `apps/reports/utils/excel_generator.py`.
4. `expense_report()` lit `Expense` et `ExpenseCategory` (`apps/accounting/models.py`). Une catégorie sans dépense sur la période n'a pas de ligne.
5. La vue place le classeur dans la réponse et crée une ligne `ActionLog`.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Téléchargement, `reports:export_expenses` | `apps/reports/views.py` | `export_expense_report()` |
| Création du classeur | `apps/reports/utils/excel_generator.py` | `expense_report()` |
| Modèles lus | `apps/accounting/models.py` | `Expense`, `ExpenseCategory` |

**Règles à connaître :**

- Rôles autorisés : `admin`, `owner`, `manager` et `accountant`. Les autres reçoivent une erreur 403.
- La période porte sur la date de la dépense (`expense_date`), pas sur sa date de saisie.
- Les dépenses sans catégorie sont regroupées sous « Sans catégorie ».
- Une date mal écrite dans l'adresse provoque une erreur 500. Si une seule des deux dates est donnée, le mois en cours est utilisé.

**Pour le tester :** avec le rôle `accountant`, cliquez sur le bouton Dépenses de `/reports/`. Le TOTAL de la première feuille est égal à la carte « Dépenses (Mois) », si aucune dépense n'est datée après aujourd'hui.

## Rapport Excel des clients

**Ce que voit l'utilisateur :** un fichier `Rapport_Clients_<date>.xlsx` est téléchargé. Il contient deux feuilles.

| Feuille | Contenu |
|---|---|
| Top Clients | Les 100 meilleurs clients : rang, nom, téléphone, total des achats, nombre d'achats, panier moyen, solde de crédit, points de fidélité |
| Clients avec Crédit | Clients qui ont un solde : nom, téléphone, solde dû, limite de crédit, pourcentage utilisé |

**Ce qui se passe dans le code :**

1. L'adresse `reports:export_customers` appelle `export_customer_report()` dans `apps/reports/views.py`.
2. La vue vérifie le rôle, puis appelle `customer_report()` dans `apps/reports/utils/excel_generator.py`.
3. `customer_report()` lit les `Customer` actifs (`apps/customers/models.py`) et les trie par total d'achats.
4. Elle écrit ensuite les clients dont `current_balance` est supérieur à 0, du plus grand solde au plus petit.
5. La vue place le classeur dans la réponse et crée une ligne `ActionLog`.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Téléchargement, `reports:export_customers` | `apps/reports/views.py` | `export_customer_report()` |
| Création du classeur | `apps/reports/utils/excel_generator.py` | `customer_report()` |
| Modèle lu | `apps/customers/models.py` | `Customer` |

**Règles à connaître :**

- Rôles autorisés : `admin`, `owner`, `manager` et `accountant`. Les autres reçoivent une erreur 403.
- Le rapport n'a ni période ni filtre par emplacement.
- Les chiffres viennent des compteurs enregistrés sur `Customer`. Ils ne sont pas recalculés à partir des ventes.
- Si la limite de crédit vaut 0, le pourcentage utilisé affiche 0 %.

**Pour le tester :** avec le rôle `manager`, cliquez sur le bouton Clients de `/reports/`. Un client ayant un solde de crédit apparaît dans « Clients avec Crédit ». Le premier de « Top Clients » a le plus grand total d'achats.

## Export de liste en PDF et Excel

**Ce que voit l'utilisateur :** les pages de liste affichent deux boutons. **PDF** ouvre un document A4 paysage dans un nouvel onglet, pour le lire ou l'imprimer. **Excel** télécharge un fichier. Les deux reprennent les filtres actifs et toutes les pages de résultats, jusqu'à 5000 lignes. Le titre, la date de génération et le nombre de lignes sont indiqués en haut.

**Ce qui se passe dans le code :**

1. `templates/partials/export_buttons.html` charge les balises de `apps/core/templatetags/export_tags.py` et affiche les deux liens.
2. `export_url()` construit chaque lien à partir de l'adresse actuelle : elle garde les filtres, retire `page` et ajoute `export=pdf` ou `export=xlsx`.
3. Le clic rappelle la même vue, par exemple `expense_list()`. La vue applique ses contrôles et ses filtres habituels.
4. La vue appelle `export_list_response()` dans `apps/core/exports.py`, avant la pagination.
5. Si `export` ne vaut ni `xlsx` ni `pdf`, la fonction renvoie `None` et la vue continue normalement.
6. Sinon, elle garde 5000 lignes au maximum et prépare le sous-titre et le nom du fichier.
7. `_xlsx_response()` crée le fichier Excel avec openpyxl. `_pdf_response()` crée le PDF avec reportlab.
8. `_cell()` prépare les valeurs : `None` devient vide, les dates passent au format JJ/MM/AAAA, les nombres restent des nombres.
9. La vue renvoie directement le fichier, sans afficher le template.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Point d'entrée | `apps/core/exports.py` | `export_list_response()` |
| Fichier Excel | `apps/core/exports.py` | `_xlsx_response()` |
| Fichier PDF | `apps/core/exports.py` | `_pdf_response()`, `_trunc()` |
| Mise en forme des valeurs | `apps/core/exports.py` | `_cell()`, `fmt_qty()` |
| Balise de lien | `apps/core/templatetags/export_tags.py` | `export_url()` |
| Boutons | `templates/partials/export_buttons.html` | |

Les vues qui utilisent cet export aujourd'hui :

| Page | Fichier | Fonction ou classe |
|---|---|---|
| Dépenses, `accounting:expense_list` | `apps/accounting/views.py` | `expense_list()` |
| Clients, `customers:customer_list` | `apps/customers/views.py` | `customer_list()` |
| Crédits, `customers:credit_list` | `apps/customers/views.py` | `credit_list()` |
| Stock d'un emplacement, `locations:stock` | `apps/locations/views.py` | `location_stock()` |
| Historique des ventes, `pos:sales_list` | `apps/pos/views_frontend.py` | `sales_list()` |
| Produits, `products:product_list` | `apps/products/views.py` | `product_list()` |
| Produits en stock, `stock:in_stock` | `apps/stock/views_frontend.py` | `in_stock_view()` |
| Stock faible, `stock:low_stock` | `apps/stock/views_frontend.py` | `low_stock_view()`, `_stock_list_export()` |
| Ruptures, `stock:out_of_stock` | `apps/stock/views_frontend.py` | `out_of_stock_view()`, `_stock_list_export()` |
| Mouvements, `stock:movements` | `apps/stock/views_frontend.py` | `movements_view()` |
| Transferts, `transfers:list` | `apps/transfers/views.py` | `transfer_list()` |

**Règles à connaître :**

- L'export suit les droits de la page, car il passe par la même vue. Il n'a pas de contrôle de rôle propre.
- Les autres pages n'ont pas ces boutons, notamment les sessions de caisse, les catégories de dépenses et l'historique des paiements d'un client.
- La limite est `EXPORT_MAX_ROWS`, soit 5000 lignes. Au-delà, les lignes en trop sont retirées sans message d'avertissement. Le sous-titre indique le nombre de lignes exportées.
- Dans le PDF, le texte d'une cellule est coupé à 60 caractères. Le tableau ne passe pas à la ligne : une liste avec beaucoup de colonnes larges peut dépasser de la page.

**Pour le tester :** avec le rôle `manager`, ouvrez `/accounting/expenses/?date=month` et cliquez sur PDF. Le document s'ouvre dans un onglet et contient seulement les dépenses du mois. Si la liste a plusieurs pages, cliquez sur PDF depuis la page 2 : l'export contient quand même toutes les lignes.

### Ajouter un export à une nouvelle page

1. Dans la vue, appliquez d'abord les contrôles de rôle et tous les filtres.
2. Avant la pagination, appelez `export_list_response()` :

```python
from apps.core.exports import export_list_response

export = export_list_response(
    request,
    title="Liste des Dépenses",
    headers=["Date", "Description", "Montant"],
    rows=([e.expense_date, e.description, float(e.amount or 0)] for e in expenses),
    filename="depenses",
)
if export:
    return export
```

3. Chaque ligne de `rows` doit suivre l'ordre de `headers`. Utilisez `fmt_qty()` pour afficher une quantité sans zéros inutiles.
4. Dans le template, placez les boutons :

```django
{% include "partials/export_buttons.html" %}
```

5. Affichez ce template avec `render()` en lui passant `request`, car `export_url()` lit `request` dans le contexte.
6. Dans `title`, évitez les caractères `/ \ ? * : [ ]`. Le titre sert de nom de feuille Excel, et openpyxl refuse ces caractères. Seuls les 31 premiers caractères sont gardés pour ce nom.
7. Vérifiez la page avec un filtre actif, puis avec `?export=xlsx` et `?export=pdf`.

## Reçus de vente

Les reçus ne font pas partie de ces exports. Ils sont décrits dans le [guide de la caisse et des ventes](07-caisse-ventes.md).

## À retenir

- Le tableau de bord et les quatre rapports Excel sont réservés à `admin`, `owner`, `manager` et `accountant`.
- Les quatre rapports sont construits dans `apps/reports/utils/excel_generator.py`. Leurs vues, dans `apps/reports/views.py`, écrivent une ligne `ActionLog`.
- Le panneau par emplacement ne fait qu'ajouter `location=` aux liens existants.
- Le « Bénéfice Net » du tableau de bord ne déduit pas le coût d'achat des produits.
- Pour exporter une nouvelle liste : appelez `export_list_response()` avant la pagination et incluez `templates/partials/export_buttons.html`.
