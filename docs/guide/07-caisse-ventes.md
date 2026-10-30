# Caisse et ventes

Cette partie couvre la vente au comptoir : l'écran de caisse, le panier, le paiement, le reçu, le tableau de bord et l'historique. La caisse sert aux rôles `cashier` et `boutique_manager`. Le tableau de bord et l'historique servent aussi à `admin`, `owner`, `manager` et `accountant`.

## Sommaire

- [L'écran de caisse](#lécran-de-caisse)
- [Rechercher un produit](#rechercher-un-produit)
- [Le panier](#le-panier)
- [Les modes de paiement](#les-modes-de-paiement)
- [Créer un client à la caisse](#créer-un-client-à-la-caisse)
- [Le parcours complet d'une vente](#le-parcours-complet-dune-vente)
- [Le reçu](#le-reçu)
- [Le tableau de bord des ventes](#le-tableau-de-bord-des-ventes)
- [L'historique des ventes et ses exports](#lhistorique-des-ventes-et-ses-exports)
- [À retenir](#à-retenir)

## L'écran de caisse

**Ce que voit l'utilisateur :** une page en deux colonnes. À gauche : la recherche, les onglets (« Populaires », « Tous », puis une catégorie par onglet) et la grille des produits. À droite : le panier, le choix du client (« Client Anonyme » par défaut), le total, le mode de paiement et le bouton « Valider la Vente ». L'en-tête montre l'emplacement de l'utilisateur, l'heure et un lien vers le tableau de bord. La touche F2 place le curseur dans la recherche. La touche F12 valide la vente.

**Ce qui se passe dans le code :**

1. L'adresse `/pos/` est déclarée dans `apps/pos/urls.py` sous le nom `pos:cashier`.
2. `cashier_view()` (`apps/pos/views_frontend.py`) vérifie le rôle.
3. La vue lit les catégories actives qui ont au moins un produit actif.
4. Elle lit 16 produits populaires au maximum (`is_popular=True`). Pour chacun, elle calcule `current_stock`, `is_low_stock` et `is_out_of_stock` à partir de `Stock` (`product.stock_info`).
5. Le stock compté est celui de l'emplacement de l'utilisateur. S'il n'a pas d'emplacement, c'est le stock de son entreprise.
6. Elle lit 100 clients actifs au maximum pour la liste déroulante.
7. `apps/pos/templates/pos/cashier.html` affiche la page. L'attribut `x-data="posApp()"` active le composant `posApp()`. Alpine.js est la petite bibliothèque JavaScript qui relie ce composant au HTML.
8. `init()` met à jour l'heure chaque minute et installe les raccourcis F2 et F12.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Route `pos:cashier` | `apps/pos/urls.py` | `cashier_view()` |
| Vue de la page | `apps/pos/views_frontend.py` | `cashier_view()` |
| Page et composant | `apps/pos/templates/pos/cashier.html` | `posApp()`, `init()` |
| Stock affiché | `apps/stock/models.py` | `Stock` |

**Règles à connaître :**

- Seuls `cashier` et `boutique_manager` ouvrent la page. Les autres rôles sont renvoyés vers `home` avec un message. `admin` et `owner` suivent les ventes par le tableau de bord et les rapports.
- Le menu latéral (`templates/base.html`) montre cette page, sous le nom « Point de vente », à ces deux seuls rôles.
- Un client au-delà des 100 premiers n'apparaît pas dans la liste déroulante. Il n'y a pas de recherche de client à la caisse.
- La caisse ne vérifie pas qu'une session de caisse est ouverte, et `Sale` n'a aucun lien vers `CashRegisterSession`.

**Pour le tester :** avec le rôle `cashier`, ouvrez `/pos/`. Le nom de votre emplacement et les produits populaires s'affichent. Avec le rôle `manager`, la même adresse vous renvoie à l'accueil avec un message d'erreur.

## Rechercher un produit

**Ce que voit l'utilisateur :** la grille se met à jour pendant la saisie, sans recharger la page. On peut chercher par nom, code-barres, SKU, catégorie ou description. Chaque carte montre le prix et un badge de stock : vert, orange si le stock est faible, ou rouge « Épuisé ». Une carte épuisée ne peut pas être cliquée.

**Ce qui se passe dans le code :**

1. Le champ de recherche appelle `searchProducts()` 300 ms après la dernière touche. Les onglets appellent `filterByCategory()`.
2. `searchProducts()` construit les paramètres `q` et `category`, puis appelle `pos:search_products` avec `fetch()`. `fetch()` est la fonction du navigateur qui appelle le serveur sans recharger la page.
3. `search_products()` (`apps/pos/views_frontend.py`) découpe le texte en mots. Chaque mot doit se trouver dans le nom, le code-barres, le SKU, la catégorie ou la description.
4. La vue accepte aussi le texte entier trouvé tel quel dans le nom, le code-barres ou le SKU.
5. Elle applique `category` s'il est présent et garde 24 produits au maximum.
6. Avec `popular=1`, sans texte ni catégorie, elle renvoie 16 produits populaires au maximum. `refreshProducts()` utilise ce mode.
7. Elle calcule le stock de chaque produit comme `cashier_view()`.
8. Elle rend `apps/pos/templates/pos/partials/product_grid.html`. `searchProducts()` place ce HTML dans `#product-grid` et met à jour le compteur.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Route `pos:search_products` | `apps/pos/urls.py` | `search_products()` |
| Recherche côté serveur | `apps/pos/views_frontend.py` | `search_products()` |
| Appels côté navigateur | `apps/pos/templates/pos/cashier.html` | `searchProducts()`, `clearSearch()`, `filterByCategory()`, `refreshProducts()` |
| Carte produit | `apps/pos/templates/pos/partials/product_grid.html` | Boucle `{% for product in products %}` |

**Règles à connaître :**

- La réponse est du HTML, pas du JSON.
- Le badge orange apparaît quand le stock est inférieur ou égal à `min_stock_threshold`. Le rouge apparaît quand il est inférieur ou égal à 0.
- Le compteur de la grille ne compte que les cartes cliquables après un rechargement.
- Les onglets « Tous » et de catégorie montrent 24 produits au maximum, sans pagination. Pour atteindre les autres, il faut les chercher.
- Sur l'onglet « Populaires », une recherche porte sur tout le catalogue actif.
- Effacer la recherche sur cet onglet appelle `searchProducts()` sans paramètre. La grille montre alors 24 produits actifs, pas les populaires, alors que son titre reste « Produits Populaires ».

**Pour le tester :** avec le rôle `cashier`, ouvrez `/pos/` et tapez une partie d'un nom de produit. La grille se réduit. Tapez un texte qui n'existe pas : « Aucun produit trouvé » s'affiche.

## Le panier

**Ce que voit l'utilisateur :** un clic sur une carte ajoute le produit au panier. Chaque ligne montre le prix unitaire, la quantité, le total et le stock. Les boutons + et - et le champ quantité modifient la ligne. Le bouton « Vider » demande une confirmation. Le total se met à jour tout de suite.

**Ce qui se passe dans le code :**

1. Le clic appelle `addToCart()` avec l'identifiant, le nom, le prix et le stock du produit.
2. `addToCart()` ajoute une ligne à `cart`, ou augmente sa quantité si le produit y est déjà. Le serveur n'est pas appelé.
3. `incrementQuantity()`, `decrementQuantity()` et `updateQuantity()` modifient une ligne.
4. `removeFromCart()` retire une ligne. `decrementQuantity()` l'appelle quand la quantité vaut 1.
5. `clearCart()` vide le panier après confirmation.
6. Les propriétés calculées `subtotal`, `total` et `cartItemsCount` recalculent les montants à chaque changement.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Ajout d'un produit | `apps/pos/templates/pos/cashier.html` | `addToCart()` |
| Quantités | `apps/pos/templates/pos/cashier.html` | `incrementQuantity()`, `decrementQuantity()`, `updateQuantity()` |
| Retrait et vidage | `apps/pos/templates/pos/cashier.html` | `removeFromCart()`, `clearCart()` |

**Règles à connaître :**

- Le panier vit seulement dans la page. Il est perdu si on la recharge.
- La quantité ne peut pas dépasser le stock connu au moment de l'ajout de la ligne. Ce stock n'est pas actualisé tant que la ligne reste dans le panier.
- `updateQuantity()` convertit la saisie en nombre entier. On ne peut donc pas saisir une quantité décimale à la caisse.
- `total` est égal à `subtotal`. L'écran ne propose ni remise ni taxe.

**Pour le tester :** avec le rôle `cashier`, ajoutez un produit dont le stock est de 2, puis cliquez sur +. À 2, le bouton se bloque et « Quantité maximale atteinte » s'affiche. Rechargez la page : le panier est vide.

## Les modes de paiement

**Ce que voit l'utilisateur :** quatre boutons : Espèces, Mobile, Carte et Crédit. Espèces est choisi par défaut. Pour Crédit, un avertissement demande de choisir un client, et le bouton de validation reste grisé tant qu'aucun client n'est choisi.

**Ce qui se passe dans le code :**

1. Chaque bouton change la variable `payment_method` de `posApp()`.
2. Le bouton de validation est désactivé si le panier est vide, si une vente est en cours d'envoi, ou si le mode est `credit` sans client.
3. `completeSale()` refait le contrôle du client. Il protège aussi la validation par F12.
4. `completeSale()` envoie `payment_method`, et `create_sale_view()` l'enregistre dans `Sale.payment_method`.

| Bouton | Valeur enregistrée |
|---|---|
| Espèces | `cash` |
| Mobile | `mobile_money` |
| Carte | `card` |
| Crédit | `credit` |

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Boutons et avertissement | `apps/pos/templates/pos/cashier.html` | `posApp()` |
| Envoi du mode choisi | `apps/pos/templates/pos/cashier.html` | `completeSale()` |
| Valeurs possibles | `apps/pos/models.py` | `Sale.PAYMENT_METHOD_CHOICES` |

**Règles à connaître :**

- L'écran n'a pas de champ « montant reçu » ni de champ de référence de paiement. `completeSale()` envoie toujours `amount_paid` égal au total et `change_amount` à 0.
- Cette règle vaut aussi pour le mode `credit`. Une vente à crédit faite à la caisse crée donc un crédit de 0 FB : voir [le crédit automatique](08-clients-credits.md#le-crédit-créé-automatiquement).
- Après une vente, le client est remis à zéro, mais le mode de paiement reste celui de la vente précédente.

**Pour le tester :** avec le rôle `cashier`, ajoutez un produit et cliquez sur Crédit sans choisir de client. L'avertissement jaune s'affiche et « Valider la Vente » reste grisé. Choisissez un client : le bouton s'active.

## Créer un client à la caisse

**Ce que voit l'utilisateur :** le bouton à côté de la liste des clients ouvre une fenêtre « Nouveau Client » avec le nom (obligatoire), le téléphone, l'email et l'adresse. Après l'enregistrement, la fenêtre se ferme et le nouveau client est déjà sélectionné pour la vente.

**Ce qui se passe dans le code :**

1. Le formulaire appelle `createCustomer()`, qui envoie `newCustomer` en JSON à `pos:create_customer`. JSON est un format texte d'échange de données.
2. `create_customer_view()` (`apps/pos/views_frontend.py`) accepte seulement POST et vérifie le rôle.
3. La vue refuse une demande sans nom avec une erreur 400.
4. Elle crée le `Customer` avec l'entreprise de l'utilisateur et `is_active=True`.
5. Elle renvoie `customer_id` et `customer_name`.
6. `createCustomer()` ajoute le client à `newCustomers`, le sélectionne dans `customer_id` et vide le formulaire.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Route `pos:create_customer` | `apps/pos/urls.py` | `create_customer_view()` |
| Création côté serveur | `apps/pos/views_frontend.py` | `create_customer_view()` |
| Fenêtre et envoi | `apps/pos/templates/pos/cashier.html` | `createCustomer()` |
| Modèle | `apps/customers/models.py` | `Customer` |

**Règles à connaître :**

- Rôles acceptés par la vue : `admin`, `owner`, `manager`, `boutique_manager` et `cashier`.
- Le client créé ici a une limite de crédit de 0 FB (valeur par défaut). L'écran ne permet pas de la changer.
- Contrairement à `customer_create()`, cette vue ne cherche pas si le téléphone ou l'email existe déjà. Deux clients peuvent donc avoir le même téléphone.
- `validate_customer_credit_limit()` ne fait rien à la création : ce signal agit seulement sur un client qui existe déjà.

**Pour le tester :** avec le rôle `cashier`, ouvrez `/pos/`, cliquez sur le bouton « Nouveau client » et saisissez un nom. Le client est sélectionné dans la liste. Il apparaît ensuite sur `/customers/`.

## Le parcours complet d'une vente

**Ce que voit l'utilisateur :** le caissier remplit le panier, choisit éventuellement un client et un mode de paiement, puis clique sur « Valider la Vente » ou appuie sur F12. Le bouton affiche « Traitement... ». Un message vert annonce le numéro et le montant de la vente. Le panier se vide et les badges de stock se mettent à jour. Une question propose ensuite d'imprimer le reçu.

**Ce qui se passe dans le code :**

Dans cette section, un *signal* est une fonction que Django appelle automatiquement avant ou après l'enregistrement d'un modèle. Les signaux de la vente sont chargés au démarrage par `PosConfig.ready()` et `CustomersConfig.ready()`.

*Dans le navigateur*

1. `completeSale()` (`apps/pos/templates/pos/cashier.html`) s'arrête si le panier est vide, si un envoi est déjà en cours, ou si le mode `credit` n'a pas de client.
2. Elle passe `isProcessing` à vrai, ce qui bloque un second clic.
3. Elle prépare le JSON : `customer_id`, `subtotal`, `total_amount`, `amount_paid` (égal au total), `change_amount` (0), `payment_method` et `items`. Chaque élément de `items` contient `product_id`, `quantity`, `unit_price` et `total_price`. La remise et la taxe sont envoyées à 0.
4. Elle envoie le JSON en POST à `pos:create_sale` avec `fetch()`. L'en-tête `X-CSRFToken` porte le jeton que Django exige sur chaque POST.

*Sur le serveur : la vente*

5. `apps/pos/urls.py` dirige la demande vers `create_sale_view()` (`apps/pos/views_frontend.py`). Une autre méthode que POST reçoit une erreur 405.
6. La vue lit le JSON, puis l'entreprise et l'emplacement de l'utilisateur.
7. `Sale.generate_sale_number()` calcule le numéro `VNT-AAAAMMJJ-NNNN` à partir du dernier numéro du jour.
8. `Sale.objects.create()` lance l'enregistrement avec le statut `completed`.
9. Avant l'écriture, deux signaux `pre_save` s'exécutent : `store_original_sale_status_for_customer()` (`apps/customers/signals.py`) et `store_original_sale_status()` (`apps/pos/signals.py`). Pour une nouvelle vente, ils mettent `_original_status` à `None`.
10. La ligne est écrite dans la table `sales`.

*Sur le serveur : le client*

11. Le premier signal `post_save` est `update_customer_on_sale()` (`apps/customers/signals.py`). Sans client, il ne fait rien.
12. Avec un client, il ajoute le total à `total_purchases` et 1 à `purchase_count`.
13. Si le réglage `loyalty_program_enabled` vaut `true`, il ajoute des points de fidélité : 1 point par tranche de `loyalty_points_rate` FB.
14. Si le mode est `credit`, il calcule `total_amount - amount_paid`. Si le nouveau solde dépasse `credit_limit`, il lève une `ValidationError`.
15. Sinon, il crée un `CustomerCredit` au statut `pending` et ajoute le montant à `current_balance`.
16. `customer.save()` enregistre le client et déclenche `validate_customer_credit_limit()`.
17. Le deuxième signal, `handle_sale_status_changes()` (`apps/pos/signals.py`), ne fait rien à la création.
18. Le troisième signal, `log_sale_action()`, écrit « Vente créée » dans `ActionLog`, le journal d'audit.

*Sur le serveur : les lignes et le stock*

19. La vue parcourt `items`. Pour chaque élément, elle lit le `Product` et crée un `SaleItem`.
20. Le `SaleItem` garde une copie de `product_name`, `unit_price` et `purchase_price`. Une vente passée ne change donc pas si le produit change plus tard.
21. Chaque `SaleItem` déclenche `create_stock_movement_on_sale_item()` (`apps/pos/signals.py`).
22. Ce signal crée un `StockMovement` avec `movement_type='exit'`, `reason='sale'`, la quantité, l'emplacement de la vente et le numéro de vente en `reference`.
23. `StockMovement.save()` (`apps/stock/models.py`) retire la quantité de `Stock`.
24. Si le mouvement a un emplacement, la même méthode retire aussi la quantité de `LocationStock`. Tous les écrans de stock restent ainsi d'accord.
25. La vue répond en JSON avec `success`, `sale_id`, `sale_number` et `message`.

*De retour dans le navigateur*

26. `completeSale()` affiche le message vert pendant 4 secondes, vide `cart` et remet `customer_id` à zéro.
27. `refreshProducts()` recharge la grille avec le stock à jour.
28. Une question propose le reçu. Si l'utilisateur accepte, `pos:sale_receipt` s'ouvre dans un nouvel onglet.
29. En cas d'erreur, `completeSale()` affiche le message reçu dans une alerte. Le panier reste intact.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Envoi du panier | `apps/pos/templates/pos/cashier.html` | `completeSale()` |
| Route `pos:create_sale` | `apps/pos/urls.py` | `create_sale_view()` |
| Création de la vente et des lignes | `apps/pos/views_frontend.py` | `create_sale_view()` |
| Numéro de vente | `apps/pos/models.py` | `Sale.generate_sale_number()` |
| Modèles de vente | `apps/pos/models.py` | `Sale`, `SaleItem` |
| Statistiques client et crédit | `apps/customers/signals.py` | `update_customer_on_sale()` |
| Contrôle de la limite à l'enregistrement du client | `apps/customers/signals.py` | `validate_customer_credit_limit()` |
| Sortie de stock | `apps/pos/signals.py` | `create_stock_movement_on_sale_item()` |
| Journal d'audit | `apps/pos/signals.py` | `log_sale_action()` |
| Mise à jour du stock | `apps/stock/models.py` | `StockMovement.save()` |
| Stock par emplacement | `apps/locations/models.py` | `LocationStock` |

**Règles à connaître :**

- La page `pos:cashier`, d'où part cet appel, est réservée à `cashier` et `boutique_manager`.
- Toute vente créée ici a le statut `completed`.
- Les signaux gèrent le stock et le client. N'ajoutez pas de `StockMovement` ni de `CustomerCredit` à la main dans ce parcours : ils seraient comptés deux fois.
- Toute exception dans `create_sale_view()` donne une réponse JSON d'erreur 400.
- La vue n'utilise pas de `transaction.atomic()`. Une *transaction* annule tout en cas d'erreur. Sans elle, ce qui est déjà écrit reste en base. Par exemple, un `product_id` inconnu laisse une `Sale` sans cette ligne, et le serveur répond 400.
- Une vente sans emplacement ne vise pas de ligne de stock précise. Si le produit a plusieurs lignes `Stock` dans l'entreprise, `StockMovement.save()` échoue : la `Sale` et sa première ligne restent en base, sans sortie de stock. Donnez donc un emplacement à chaque caissier.
- La limite de quantité est appliquée dans le panier, pas par `create_sale_view()`. Si deux caisses vendent le même article en même temps, le stock peut devenir négatif.
- Aucune page web ne permet d'annuler ou de rembourser une vente. Cela passe par l'API, avec un compte `admin`, `owner` ou `manager` : `POST /api/v1/sales/<id>/cancel/` et `POST /api/v1/sales/<id>/refund/` (`SaleViewSet`, `api/v1/views/pos.py`).
- Lors d'une annulation ou d'un remboursement, `handle_sale_status_changes()` recrée le stock avec des mouvements d'entrée. Le client n'est pas corrigé : `update_customer_on_sale()` s'arrête dès que le statut n'est plus `completed`. Les totaux, le solde et le crédit restent donc inchangés.

**Pour le tester :** avec le rôle `cashier`, notez le stock d'un produit sur `/pos/`, puis vendez-en 2 à un client en espèces. Deux vérifications : le badge a baissé de 2 ; sur la fiche du client (`customers:customer_detail`), le total des achats a augmenté. Connectez-vous ensuite avec le rôle `manager`, car `stock:movements` n'est pas ouvert au `cashier` : la page montre une sortie dont la référence est le numéro de vente.

## Le reçu

**Ce que voit l'utilisateur :** un fichier PDF est téléchargé. Il contient le nom et les coordonnées du magasin, le numéro de vente, la date, le caissier, le client, les articles, le total, le montant payé, le mode de paiement, un message de fin et la date de génération du document. La remise, la TVA et la monnaie n'apparaissent que si elles sont supérieures à 0. Sans client, le reçu indique « Client anonyme ». On l'obtient juste après la vente, depuis l'historique ou depuis les tableaux de bord.

**Ce qui se passe dans le code :**

1. L'adresse `/pos/sales/<id>/receipt/` est déclarée sous le nom `pos:sale_receipt`.
2. `sale_receipt_pdf()` (`apps/pos/views_frontend.py`) vérifie le rôle et lit la `Sale`.
3. Elle lit le paramètre `format` (`A4` par défaut, ou `thermal`) et appelle `generate_receipt_pdf()` (`apps/pos/utils/receipt_generator.py`).
4. `generate_receipt_pdf()` lit `store_name`, `store_phone`, `store_address` et `receipt_footer` avec `StoreSetting.get_setting()`.
5. Elle construit le PDF avec ReportLab à partir de `sale.items`. `format_currency()` met en forme les montants.
6. La vue renvoie le PDF sous le nom `Recu_<numéro>.pdf` et ajoute une ligne `receipt` dans `ActionLog`.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Route `pos:sale_receipt` | `apps/pos/urls.py` | `sale_receipt_pdf()` |
| Vue | `apps/pos/views_frontend.py` | `sale_receipt_pdf()` |
| Construction du PDF | `apps/pos/utils/receipt_generator.py` | `generate_receipt_pdf()`, `format_currency()` |
| Réglages du magasin | `apps/settings/models.py` | `StoreSetting` |
| Liens vers le reçu | `apps/pos/templates/pos/sales_list.html`, `apps/pos/templates/pos/dashboard.html`, `templates/dashboards/caisse.html`, `templates/dashboards/gerant.html` | Lien `pos:sale_receipt` |

**Règles à connaître :**

- Rôles acceptés : `admin`, `owner`, `manager`, `boutique_manager` et `cashier`.
- `accountant` voit le lien dans l'historique et le tableau de bord, mais reçoit une erreur 403 s'il clique.
- Le PDF est envoyé en téléchargement (`attachment`), même si la caisse demande s'il faut « imprimer ». L'impression se fait ensuite depuis le fichier.
- Aucune page n'utilise `?format=thermal`. Ce format réduit la page à 8 cm, mais les tableaux gardent des largeurs fixes de 14 à 15 cm.
- Le mode de paiement est imprimé avec le libellé de `Sale.PAYMENT_METHOD_CHOICES`, en anglais (`Cash`, `Card`).
- Générer le même reçu plusieurs fois ajoute une ligne au journal à chaque fois.
- Le reçu d'une vente à crédit faite à la caisse indique un montant payé égal au total, car `completeSale()` envoie cette valeur.

**Pour le tester :** avec le rôle `cashier`, validez une vente et acceptez le reçu. Un fichier `Recu_VNT-...pdf` est téléchargé et ses lignes correspondent au panier.

## Le tableau de bord des ventes

**Ce que voit l'utilisateur :** les chiffres du jour, de la semaine et du mois, le panneau « Suivi des Crédits », des graphiques, les meilleurs produits du jour et les 20 dernières ventes. Presque tout est cliquable et ouvre l'historique déjà filtré. On appelle cela un *drill-down* : passer d'un chiffre au détail qui le compose.

**Ce qui se passe dans le code :**

1. L'adresse `/pos/dashboard/` est déclarée sous le nom `pos:dashboard`.
2. `sales_dashboard()` (`apps/pos/views_frontend.py`) vérifie le rôle.
3. La vue filtre `Sale` par entreprise. Pour `cashier` et `boutique_manager` qui ont un emplacement, elle filtre aussi par cet emplacement.
4. Elle additionne les ventes `completed` du jour, de la semaine (depuis lundi) et du mois.
5. Elle calcule les chiffres de crédit à partir de `CustomerCredit` et `CreditPayment` : voir [le panneau de suivi](08-clients-credits.md#le-panneau-de-suivi-des-crédits).
6. Elle prépare les données des graphiques : tendance sur 7 jours, modes de paiement du jour et ventes par heure de 6 h à 21 h.
7. Elle lit les 10 produits les plus vendus du jour (`SaleItem`) et les 20 dernières ventes, tous statuts confondus.
8. Pour `admin`, `owner` et `manager`, elle ajoute la performance des caissiers du jour.
9. `apps/pos/templates/pos/dashboard.html` affiche la page et dessine les graphiques avec Chart.js. Un clic sur un graphique ouvre `pos:sales_list` avec les bons paramètres.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Route `pos:dashboard` | `apps/pos/urls.py` | `sales_dashboard()` |
| Calculs | `apps/pos/views_frontend.py` | `sales_dashboard()` |
| Page et graphiques | `apps/pos/templates/pos/dashboard.html` | `new Chart` |
| Rôle → accueil | `apps/core/dashboard_views.py` | `dashboard_url_for()` |

**Règles à connaître :**

- Rôles acceptés : `admin`, `owner`, `manager`, `boutique_manager`, `cashier` et `accountant`. Les autres sont renvoyés vers `home`.
- Le menu latéral montre cette page, sous le nom « Mes ventes », à `cashier` et `boutique_manager` seulement. Les autres rôles autorisés y arrivent par un lien ou par son adresse.
- Le `cashier` arrive d'abord sur `dashboards:caisse`, qui propose un lien vers cette page.
- Les totaux ne comptent que les ventes `completed`.
- « Ouvrir la Caisse » et les « Actions Rapides » (Nouvelle Vente, Rapports, Stock, Accueil) sont affichés à tous, mais chaque page garde ses règles. `pos:cashier` renvoie vers l'accueil les rôles autres que `cashier` et `boutique_manager`. `reports:dashboard` et `stock:dashboard` y renvoient le `cashier`.

**Pour le tester :** avec le rôle `manager`, ouvrez `/pos/dashboard/`. La section « Performance des Caissiers » apparaît s'il y a des ventes aujourd'hui. Cliquez sur un point de la courbe des 7 jours : l'historique s'ouvre sur ce jour-là.

## L'historique des ventes et ses exports

**Ce que voit l'utilisateur :** un tableau des ventes avec le numéro, la date, le client, le caissier, le paiement, le statut, le total et un lien vers le reçu. Le nombre de ventes et leur total sont en haut. Des filtres et des boutons PDF et Excel sont disponibles. Un bandeau bleu rappelle les filtres venus d'un tableau de bord, avec un lien « Tout voir ».

**Ce qui se passe dans le code :**

1. L'adresse `/pos/sales/` est déclarée sous le nom `pos:sales_list`.
2. `sales_list()` (`apps/pos/views_frontend.py`) vérifie le rôle, puis filtre par entreprise.
3. Pour `cashier` et `boutique_manager` qui ont un emplacement, elle filtre aussi par cet emplacement.
4. Elle applique les paramètres de l'adresse (voir le tableau ci-dessous) et calcule le nombre et le total des ventes trouvées.
5. Elle appelle `export_list_response()` (`apps/core/exports.py`). Si `?export=pdf` ou `?export=xlsx` est présent, cette fonction renvoie le fichier et la vue s'arrête là.
6. Sinon, la vue découpe les résultats en pages de 50 ventes et rend `apps/pos/templates/pos/sales_list.html`.
7. `templates/partials/export_buttons.html` crée les boutons. Le tag `export_url()` (`apps/core/templatetags/export_tags.py`) garde les filtres actifs et retire le numéro de page.

| Paramètre | Valeurs | Dans le formulaire ? |
|---|---|---|
| `search` | Numéro de vente, nom du client ou référence de paiement | Oui |
| `payment` | `cash`, `mobile_money`, `card`, `credit` | Oui |
| `status` | `completed` (par défaut), `refunded`, `cancelled`, ou `all` pour tout | Oui |
| `date` | `today`, `week`, `month` | Oui |
| `date` | Un jour précis au format `AAAA-MM-JJ` | Non |
| `start` et `end` | Une période, les deux dates étant au format `AAAA-MM-JJ` | Non |
| `category` | Identifiant de catégorie, via les lignes de vente | Non |
| `cashier` | Identifiant de l'utilisateur | Non |
| `location` | Identifiant de l'emplacement de l'entreprise | Non |

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Route `pos:sales_list` | `apps/pos/urls.py` | `sales_list()` |
| Filtres et pagination | `apps/pos/views_frontend.py` | `sales_list()` |
| Page | `apps/pos/templates/pos/sales_list.html` | Bloc `content` |
| Génération des fichiers | `apps/core/exports.py` | `export_list_response()` |
| Boutons d'export | `templates/partials/export_buttons.html` | `export_url()` |

**Règles à connaître :**

- Rôles acceptés : `admin`, `owner`, `manager`, `boutique_manager`, `cashier` et `accountant`.
- Sans paramètre `status`, seules les ventes `completed` s'affichent.
- `location` est ignoré pour `cashier` et `boutique_manager` qui ont déjà un emplacement.
- Les filtres marqués « Non » arrivent par les liens des tableaux de bord. Le formulaire ne les conserve pas : cliquer sur « Filtrer » les efface.
- Un export contient 5000 lignes au maximum. Le PDF s'ouvre dans le navigateur, en A4 paysage. Le fichier Excel se télécharge.
- L'export a une colonne « Emplacement » que le tableau de la page n'a pas.
- `pos:sales_list` n'a pas d'entrée dans le menu latéral. On y arrive par les tableaux de bord, comme le lien « Voir tout l'historique » de `pos:dashboard`.
- Il n'existe pas de page de détail d'une vente. Pour voir ses articles, il faut ouvrir son reçu.

**Pour le tester :** avec le rôle `manager`, ouvrez `/pos/sales/?payment=cash&date=month`. Seules les ventes en espèces du mois s'affichent. Cliquez sur Excel : le fichier `ventes_....xlsx` contient les mêmes ventes.

## À retenir

- Une vente part de `completeSale()`, passe par `create_sale_view()`, puis les signaux mettent à jour le client et créent les mouvements de stock.
- Le stock ne baisse que par `StockMovement.save()`, qui met à jour `Stock` et `LocationStock`.
- La caisse enregistre toujours un montant payé égal au total, même pour une vente à crédit. La dette enregistrée est alors de 0 FB.
- La vue de vente n'utilise pas de transaction : une erreur en cours de route peut laisser une vente incomplète.
- L'annulation et le remboursement n'existent que dans l'API. Ils remettent le stock, mais ne corrigent ni le client ni son crédit.
