# Clients et crédits

Cette partie gère les fiches clients et les dettes. Elle montre comment une vente à crédit devient une dette, comment on enregistre un remboursement et comment suivre ce qui reste dû. Elle sert aux rôles `cashier`, `boutique_manager`, `manager`, `admin` et `owner`. Le rôle `accountant` la consulte en lecture.

## Sommaire

- [La liste des clients](#la-liste-des-clients)
- [Créer un client](#créer-un-client)
- [La fiche client](#la-fiche-client)
- [Modifier un client](#modifier-un-client)
- [Activer ou désactiver un client](#activer-ou-désactiver-un-client)
- [Le crédit créé automatiquement](#le-crédit-créé-automatiquement)
- [La limite de crédit](#la-limite-de-crédit)
- [Enregistrer un remboursement](#enregistrer-un-remboursement)
- [La liste des crédits et ses exports](#la-liste-des-crédits-et-ses-exports)
- [L'historique des paiements](#lhistorique-des-paiements)
- [Le panneau de suivi des crédits](#le-panneau-de-suivi-des-crédits)
- [Les points de fidélité](#les-points-de-fidélité)
- [À retenir](#à-retenir)

## La liste des clients

**Ce que voit l'utilisateur :** quatre chiffres en haut (total des clients, clients actifs, clients avec crédit, crédit total), une recherche, un filtre de statut et un tableau. Chaque ligne donne le contact, les achats, le crédit, la limite et le statut. Les boutons mènent à la fiche, à la modification et, si le client a un solde, à l'historique de ses paiements. Des boutons PDF et Excel exportent la liste. En haut, « Crédits » ouvre la liste des crédits et « Nouveau Client » le formulaire de création.

**Ce qui se passe dans le code :**

1. L'adresse `/customers/` est déclarée dans `apps/customers/urls.py` sous le nom `customers:customer_list`.
2. `role_required()` vérifie le rôle, puis `customer_list()` (`apps/customers/views.py`) s'exécute.
3. La vue garde les clients de l'entreprise et les clients sans entreprise.
4. Elle applique `?status=` : `active`, `inactive` ou `credit` (solde supérieur à 0).
5. Elle applique `?search=` sur le nom, le téléphone et l'email.
6. Elle appelle `export_list_response()` (`apps/core/exports.py`). Si `?export=pdf` ou `?export=xlsx` est présent, le fichier est renvoyé et la vue s'arrête là.
7. Sinon, elle découpe la liste en pages de 25 clients et calcule les quatre chiffres du haut.
8. `apps/customers/templates/customers/customer_list.html` affiche la page.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Route `customers:customer_list` | `apps/customers/urls.py` | `customer_list()` |
| Vue | `apps/customers/views.py` | `customer_list()` |
| Contrôle du rôle | `apps/customers/views.py` | `role_required()` |
| Page | `apps/customers/templates/customers/customer_list.html` | Bloc `content` |
| Modèle | `apps/customers/models.py` | `Customer` |
| Export | `apps/core/exports.py` | `export_list_response()` |

**Règles à connaître :**

- Rôles acceptés : `admin`, `owner`, `manager`, `boutique_manager`, `cashier` et `accountant`.
- Sans filtre, la liste contient aussi les clients inactifs.
- Les quatre chiffres du haut ne changent pas avec les filtres.
- « Nouveau Client » et « Modifier » sont affichés à tous ces rôles, mais chaque page garde ses règles : `accountant` est renvoyé vers `home` pour les deux, `cashier` pour la modification.
- Un export contient 5000 lignes au maximum et respecte les filtres. Le PDF s'ouvre dans le navigateur. Le fichier Excel se télécharge.

**Pour le tester :** avec le rôle `cashier`, ouvrez `/customers/?status=credit`. Seuls les clients avec un solde s'affichent. Cliquez sur Excel : le fichier `clients_....xlsx` contient les mêmes clients.

## Créer un client

**Ce que voit l'utilisateur :** un formulaire avec le nom (obligatoire), le téléphone, l'email, l'adresse, la limite de crédit et des notes. Après l'enregistrement, on revient à la liste avec un message de succès. En cas d'erreur, le formulaire réapparaît avec les valeurs saisies et le message.

**Ce qui se passe dans le code :**

1. L'adresse `/customers/create/` est déclarée sous le nom `customers:customer_create`.
2. `customer_create()` (`apps/customers/views.py`) affiche `apps/customers/templates/customers/customer_form.html` en mode `create`.
3. À l'envoi, la vue contrôle le nom, l'unicité du téléphone et de l'email dans l'entreprise, et la limite de crédit.
4. Si tout est bon, `Customer.objects.create()` enregistre le client avec l'entreprise de l'utilisateur.
5. La vue redirige vers `customers:customer_list`.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Route `customers:customer_create` | `apps/customers/urls.py` | `customer_create()` |
| Vue et contrôles | `apps/customers/views.py` | `customer_create()` |
| Formulaire | `apps/customers/templates/customers/customer_form.html` | Mode `create` |
| Création depuis la caisse | `apps/pos/views_frontend.py` | `create_customer_view()` |

**Règles à connaître :**

- Rôles acceptés : `admin`, `owner`, `manager`, `boutique_manager` et `cashier`.
- La limite de crédit ne peut pas être négative. Elle vaut 0 si elle est laissée vide.
- Un téléphone ou un email déjà pris par un client de la même entreprise est refusé.
- La caisse a son propre chemin de création, sans ce contrôle d'unicité : voir [Créer un client à la caisse](07-caisse-ventes.md#créer-un-client-à-la-caisse).

**Pour le tester :** avec le rôle `cashier`, créez un client avec un téléphone, puis un second avec le même téléphone. Le second est refusé avec « Un client avec ce numéro de téléphone existe déjà. ».

## La fiche client

**Ce que voit l'utilisateur :** le contact, les statistiques (total des achats, limite, crédit utilisé, crédit disponible), le statut et les notes. Si des crédits sont ouverts, un bandeau indique leur nombre et le montant à recouvrer, avec un lien « Gérer les paiements ». Trois onglets suivent : Crédits, Ventes récentes et Paiements. Les boutons « Modifier » et « Désactiver » ou « Activer » sont en haut.

**Ce qui se passe dans le code :**

1. L'adresse `/customers/<pk>/` est déclarée sous le nom `customers:customer_detail`.
2. `customer_detail()` (`apps/customers/views.py`) lit le `Customer` et vérifie qu'il appartient à l'entreprise de l'utilisateur, ou à aucune.
3. La vue lit tous les `CustomerCredit` du client et isole ceux au statut `pending` ou `partial`.
4. Elle lit les 10 dernières `Sale` du client et ses 20 derniers `CreditPayment`.
5. `apps/customers/templates/customers/customer_detail.html` affiche la page. Les onglets sont gérés par Alpine.js, sans appel au serveur.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Route `customers:customer_detail` | `apps/customers/urls.py` | `customer_detail()` |
| Vue | `apps/customers/views.py` | `customer_detail()` |
| Page | `apps/customers/templates/customers/customer_detail.html` | Onglets `credits`, `sales`, `payments` |
| Modèles | `apps/customers/models.py` | `Customer`, `CustomerCredit`, `CreditPayment` |

**Règles à connaître :**

- Rôles acceptés : `admin`, `owner`, `manager`, `boutique_manager`, `cashier` et `accountant`.
- « Crédit disponible » n'apparaît que si la limite est supérieure à 0. Le template le calcule comme `credit_limit` **plus** `current_balance`. Le chiffre affiché est donc trop élevé quand le client a un solde.
- Dans l'onglet Crédits, la colonne « Montant » affiche seulement « FB », sans chiffre, et « Référence » affiche « - ». Le template lit `credit.amount` et `credit.reference`, qui n'existent pas sur `CustomerCredit`. Le montant de départ est dans `original_amount`.
- Dans l'onglet Ventes récentes, la colonne « Référence » affiche aussi « - », car `sale.reference` n'existe pas. Le numéro de vente est dans `sale_number`.
- Les boutons « Modifier » et « Désactiver » sont affichés à tous les rôles. Un rôle non autorisé est renvoyé vers `home` avec un message.

**Pour le tester :** avec le rôle `manager`, ouvrez la fiche d'un client qui a acheté. Le total des achats correspond à ses ventes et l'onglet « Ventes récentes » les liste.

## Modifier un client

**Ce que voit l'utilisateur :** le même formulaire que la création, déjà rempli, avec en plus une case « actif ». Si le client a un solde, un encadré le rappelle. Après l'enregistrement, on revient à sa fiche.

**Ce qui se passe dans le code :**

1. L'adresse `/customers/<pk>/edit/` est déclarée sous le nom `customers:customer_edit`.
2. `customer_edit()` (`apps/customers/views.py`) lit le client et vérifie l'entreprise.
3. À l'envoi, elle refait les contrôles de la création, en excluant le client lui-même de la recherche de doublons.
4. Elle met à jour les champs, puis appelle `customer.save()`.
5. Le signal `validate_customer_credit_limit()` (`apps/customers/signals.py`) contrôle la limite avant l'écriture.
6. La vue redirige vers `customers:customer_detail`.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Route `customers:customer_edit` | `apps/customers/urls.py` | `customer_edit()` |
| Vue | `apps/customers/views.py` | `customer_edit()` |
| Formulaire | `apps/customers/templates/customers/customer_form.html` | Mode `edit` |
| Contrôle de la limite | `apps/customers/signals.py` | `validate_customer_credit_limit()` |

**Règles à connaître :**

- Rôles acceptés : `admin`, `owner`, `manager` et `boutique_manager`. Le `cashier` crée des clients, mais ne les modifie pas.
- En cas d'erreur de validation, le formulaire réaffiche les valeurs enregistrées, pas celles saisies.
- Une limite inférieure au solde actuel n'est pas gérée par la vue : la `ValidationError` du signal provoque une page d'erreur 500. Le client n'est pas modifié.

**Pour le tester :** avec le rôle `manager`, changez la limite de crédit d'un client sans solde. La fiche s'ouvre avec la nouvelle limite.

## Activer ou désactiver un client

**Ce que voit l'utilisateur :** sur la fiche, le bouton « Désactiver » ou « Activer ». Après le clic, on revient à la liste avec un message. Le client reste dans la liste avec le statut inactif.

**Ce qui se passe dans le code :**

1. L'adresse `/customers/<pk>/toggle/` est déclarée sous le nom `customers:customer_toggle`.
2. Le formulaire de `apps/customers/templates/customers/customer_detail.html` envoie un POST à `customer_toggle()` (`apps/customers/views.py`).
3. La vue vérifie l'entreprise, inverse `is_active` et appelle `customer.save()`.
4. Elle redirige vers `customers:customer_list`.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Route `customers:customer_toggle` | `apps/customers/urls.py` | `customer_toggle()` |
| Vue | `apps/customers/views.py` | `customer_toggle()` |
| Bouton | `apps/customers/templates/customers/customer_detail.html` | Formulaire `customers:customer_toggle` |

**Règles à connaître :**

- Rôles acceptés : `admin`, `owner` et `manager`.
- C'est une *suppression logique* : la ligne reste en base, seul `is_active` change. L'application ne supprime pas de client.
- Seul un POST change le statut. Un GET redirige vers la liste sans rien modifier.
- Un client inactif n'apparaît plus dans la liste déroulante de la caisse (`cashier_view()`).
- La case « actif » de `customers:customer_edit` change le même champ.

**Pour le tester :** avec le rôle `manager`, désactivez un client. Il passe à « Inactif » sur `/customers/`. Avec le rôle `cashier`, il n'est plus proposé sur `/pos/`.

## Le crédit créé automatiquement

**Ce que voit l'utilisateur :** rien de spécial au moment de la vente. La ligne apparaît ensuite dans la liste des crédits et sur la fiche du client. Son montant dépend de la façon dont la vente a été créée.

**Ce qui se passe dans le code :**

1. Une `Sale` est créée avec `payment_method='credit'` et un client.
2. Le signal `update_customer_on_sale()` (`apps/customers/signals.py`) s'exécute. Un *signal* est une fonction que Django appelle automatiquement après l'enregistrement d'un modèle.
3. Il met à jour `total_purchases` et `purchase_count`, comme pour toute vente avec client.
4. Il calcule le montant du crédit : `total_amount - amount_paid`.
5. Il contrôle la limite : voir [La limite de crédit](#la-limite-de-crédit).
6. Il crée un `CustomerCredit` avec `original_amount` et `remaining_amount` égaux à ce montant, au statut `pending`.
7. Il ajoute le montant à `Customer.current_balance`, puis appelle `customer.save()`.

Le montant dépend du chemin suivi :

| Chemin | `amount_paid` envoyé | Crédit créé | Solde du client |
|---|---|---|---|
| Caisse web : `completeSale()` puis `pos:create_sale` | Égal au total | 0 FB, statut `pending` | Inchangé |
| API : `POST /api/v1/sales/` sans `amount_paid` | 0 (`SaleCreateSerializer.create()`) | Le total | Augmente du total |
| API : `POST /api/v1/sales/` avec un acompte | L'acompte | Le total moins l'acompte | Augmente de la différence |

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Création du crédit | `apps/customers/signals.py` | `update_customer_on_sale()` |
| Modèle du crédit | `apps/customers/models.py` | `CustomerCredit` |
| Vente depuis la caisse | `apps/pos/templates/pos/cashier.html` | `completeSale()` |
| Vente depuis l'API | `api/v1/serializers/pos.py` | `SaleCreateSerializer.create()` |
| Chargement du signal | `apps/customers/apps.py` | `CustomersConfig.ready()` |

**Règles à connaître :**

- Ne créez pas de `CustomerCredit` à la main pour une vente : le signal s'en charge, et `sale` est unique sur ce modèle.
- Le signal agit seulement à la création d'une vente `completed` qui a un client.
- Une vente à crédit faite à la caisse ne crée aucune dette réelle : le crédit vaut 0 FB et le solde ne bouge pas. Ce crédit reste au statut `pending` et ne peut pas être payé.
- Le signal ne renseigne pas `due_date`, et aucune page web ne permet de la saisir. Elle se règle dans l'administration Django ou par l'API. Sans échéance, un crédit n'est jamais en retard (`CustomerCredit.is_overdue`).
- Annuler ou rembourser une vente par l'API ne corrige ni le solde ni le crédit, car `update_customer_on_sale()` s'arrête dès que le statut n'est plus `completed`.

**Pour le tester :** avec le rôle `cashier`, vendez à crédit à un client sur `/pos/`, puis ouvrez `/customers/credits/` : le crédit affiche un reste de 0 FB. Pour voir une vraie dette, envoyez avec un jeton `cashier` `POST /api/v1/sales/` avec `customer`, `payment_method` à `credit` et `items`, en choisissant un client dont la limite couvre le total et un produit stocké dans un seul emplacement. Le reste affiché est alors égal au total.

## La limite de crédit

**Ce que voit l'utilisateur :** un champ « Limite de crédit (FB) » dans le formulaire du client, et la limite affichée sur sa fiche et dans la liste.

**Ce qui se passe dans le code :**

1. `customer_create()` et `customer_edit()` refusent une valeur négative ou invalide. Le champ `Customer.credit_limit` vaut 0 par défaut.
2. Lors d'une vente à crédit, `update_customer_on_sale()` calcule le nouveau solde : `current_balance` plus le montant du crédit.
3. Si ce solde dépasse `credit_limit`, le signal lève une `ValidationError` avec le texte « Limite de crédit dépassée ».
4. À chaque enregistrement d'un client existant, `validate_customer_credit_limit()` lève une `ValidationError` si `credit_limit` est inférieur à `current_balance`.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Champ | `apps/customers/models.py` | `Customer` |
| Saisie | `apps/customers/views.py` | `customer_create()`, `customer_edit()` |
| Contrôle à la vente | `apps/customers/signals.py` | `update_customer_on_sale()` |
| Contrôle à l'enregistrement du client | `apps/customers/signals.py` | `validate_customer_credit_limit()` |

**Règles à connaître :**

- Une limite de 0 refuse toute dette réelle. C'est la valeur d'un client créé à la caisse.
- À la caisse, le montant du crédit vaut 0. Le contrôle ne se déclenche donc pas, même pour un client dont la limite est de 0.
- Par l'API, le dépassement n'est pas transformé en réponse claire : la requête finit en erreur 500.
- Le refus arrive après l'écriture de la vente, sans transaction : la `Sale` reste en base sans ligne, et le stock ne bouge pas.

**Pour le tester :** avec le rôle `manager`, donnez à un client une limite de 1000 FB, puis envoyez par l'API une vente à crédit de 2000 FB pour ce client. Aucun `CustomerCredit` n'est créé et le solde du client reste inchangé.

## Enregistrer un remboursement

**Ce que voit l'utilisateur :** depuis la liste des crédits ou la fiche client, le bouton de paiement ouvre un formulaire : le client, le montant dû, les détails du crédit (avec un avertissement si l'échéance est dépassée), le montant à payer, déjà rempli avec le reste dû, des boutons rapides (« Tout payer », 10 000, 5 000 ou 1 000 FB selon le reste dû), le mode de paiement, une référence et des notes. Après l'enregistrement, la fiche client s'ouvre avec un message de succès.

**Ce qui se passe dans le code :**

1. L'adresse `/customers/credits/<credit_id>/pay/` est déclarée sous le nom `customers:record_payment`.
2. `record_payment()` (`apps/customers/views.py`) lit le crédit et vérifie l'entreprise du client.
3. Si le crédit est déjà `paid`, elle redirige vers la fiche avec un avertissement.
4. Sinon, elle affiche `apps/customers/templates/customers/record_payment.html`.
5. À l'envoi, elle vérifie que le montant est positif et ne dépasse pas `remaining_amount`.
6. Elle appelle `CreditPayment.objects.create()`, ce qui exécute `CreditPayment.save()` (`apps/customers/models.py`).
7. `CreditPayment.save()` retire le montant de `remaining_amount`. Le statut passe à `paid` si le reste atteint 0, sinon à `partial`.
8. La méthode retire aussi le montant de `Customer.current_balance`, sans descendre sous 0, puis appelle `customer.save()`.
9. La vue redirige vers `customers:customer_detail`.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Route `customers:record_payment` | `apps/customers/urls.py` | `record_payment()` |
| Vue et contrôles | `apps/customers/views.py` | `record_payment()` |
| Mise à jour du crédit et du solde | `apps/customers/models.py` | `CreditPayment.save()` |
| Formulaire | `apps/customers/templates/customers/record_payment.html` | Bloc `content` |

**Règles à connaître :**

- Rôles acceptés : `admin`, `owner`, `manager`, `boutique_manager` et `cashier`.
- Les modes proposés sont ceux de `CreditPayment.PAYMENT_METHOD_CHOICES`, avec leurs libellés anglais : `Cash`, `Mobile Money`, `Card`.
- La mise à jour se fait une seule fois, à la création du paiement. Modifier un paiement existant ne recalcule rien.
- Un crédit de 0 FB, comme ceux créés à la caisse, refuse tout paiement : le montant dépasse toujours le reste dû.
- « Crédit original » et « Déjà payé » affichent seulement « FB », sans chiffre, sur ce formulaire, car le template lit `credit.amount` et `credit.paid_amount`, qui n'existent pas sur le modèle.
- Un remboursement n'écrit rien dans `ActionLog` et n'est pas rattaché à une session de caisse.

**Pour le tester :** avec le rôle `cashier`, ouvrez le paiement d'un crédit de 2000 FB créé par l'API, et payez 500 FB. Le reste passe à 1500 FB, le statut à « Partiel », et le solde du client baisse de 500 FB. Payez ensuite 1500 FB : le statut passe à « Payé » et le bouton de paiement disparaît.

## La liste des crédits et ses exports

**Ce que voit l'utilisateur :** le total à recouvrer, le nombre de crédits en retard, une carte « Voir les retards » qui ouvre `?overdue=true`, une recherche par nom de client, un filtre de statut, une case « En retard seulement » et un tableau. Chaque ligne a un lien vers la fiche du client et, si le crédit n'est pas soldé, un lien vers le paiement. Des boutons PDF et Excel exportent la liste.

**Ce qui se passe dans le code :**

1. L'adresse `/customers/credits/` est déclarée sous le nom `customers:credit_list`.
2. `credit_list()` (`apps/customers/views.py`) lit les `CustomerCredit` des clients de l'entreprise.
3. Elle applique `?status=` : `pending`, `partial` ou `paid`.
4. Avec `?overdue=true`, elle garde les crédits dont l'échéance est passée et qui ne sont pas soldés.
5. Elle applique `?search=` sur le nom du client.
6. Elle appelle `export_list_response()`. Si `?export=` est présent, le fichier est renvoyé.
7. Sinon, elle découpe en pages de 25 crédits et calcule `total_pending` et `overdue_count`.
8. `apps/customers/templates/customers/credit_list.html` affiche la page.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Route `customers:credit_list` | `apps/customers/urls.py` | `credit_list()` |
| Vue | `apps/customers/views.py` | `credit_list()` |
| Page | `apps/customers/templates/customers/credit_list.html` | Bloc `content` |
| Retard | `apps/customers/models.py` | `CustomerCredit.is_overdue` |
| Export | `apps/core/exports.py` | `export_list_response()` |
| Menu | `templates/base.html` | Lien « Crédits » |

**Règles à connaître :**

- Rôles acceptés : `admin`, `owner`, `manager`, `boutique_manager`, `cashier` et `accountant`.
- Le lien de paiement est affiché à tous ces rôles. `accountant` est renvoyé vers `home` avec un message, car `record_payment()` ne l'accepte pas.
- Les chiffres du haut portent sur tous les crédits de l'entreprise et ne changent pas avec les filtres.
- Le filtre porte sur l'entreprise du client. Un client sans entreprise, comme ceux créés par l'API, figure sur `customers:customer_list`, mais ses crédits n'apparaissent ni ici ni dans le panneau de suivi pour un utilisateur rattaché à une entreprise.
- La colonne « Montant » de la page affiche seulement « FB », sans chiffre, car le template lit `credit.amount`. L'export, lui, donne le bon chiffre, car il lit `original_amount`.
- L'export a pour colonnes : client, téléphone, numéro de vente, montant initial, restant dû, statut, échéance et date de création. Il contient 5000 lignes au maximum et respecte les filtres.
- Le PDF s'ouvre dans le navigateur. Le fichier Excel se télécharge.

**Pour le tester :** avec le rôle `accountant`, ouvrez `/customers/credits/?status=pending`. Seuls les crédits en attente s'affichent. Cliquez sur Excel : le fichier `credits_clients_....xlsx` reprend les mêmes crédits.

## L'historique des paiements

**Ce que voit l'utilisateur :** pour un client, le total payé, le solde actuel, le nombre de paiements et un tableau : date, montant, méthode, référence, personne qui a reçu le paiement et notes. Si le client a un solde, un bouton « Voir crédits » ouvre la liste des crédits filtrée sur son nom.

**Ce qui se passe dans le code :**

1. L'adresse `/customers/<customer_id>/payments/` est déclarée sous le nom `customers:payment_history`.
2. `payment_history()` (`apps/customers/views.py`) lit le client et vérifie l'entreprise.
3. Elle lit tous les `CreditPayment` de ses crédits, du plus récent au plus ancien, en pages de 25.
4. Elle calcule `total_paid`, la somme de tous ses paiements.
5. `apps/customers/templates/customers/payment_history.html` affiche la page.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Route `customers:payment_history` | `apps/customers/urls.py` | `payment_history()` |
| Vue | `apps/customers/views.py` | `payment_history()` |
| Page | `apps/customers/templates/customers/payment_history.html` | Bloc `content` |
| Modèle | `apps/customers/models.py` | `CreditPayment` |

**Règles à connaître :**

- Rôles acceptés : `admin`, `owner`, `manager`, `boutique_manager`, `cashier` et `accountant`.
- La page sert à consulter. Le lien « Gérer les paiements » de la fiche client mène ici, mais le paiement se saisit sur `customers:record_payment`.
- Le lien de la liste des clients n'apparaît que si le solde est supérieur à 0, et celui de la fiche que si un crédit est ouvert. Une fois tout remboursé, l'historique reste disponible par son adresse, et l'onglet Paiements de la fiche montre les 20 derniers.
- Cette page n'a pas d'export.

**Pour le tester :** avec le rôle `manager`, ouvrez `/customers/<id>/payments/` pour un client qui a remboursé. Le total payé est égal à la somme des lignes.

## Le panneau de suivi des crédits

**Ce que voit l'utilisateur :** un panneau « Suivi des Crédits » avec quatre cartes cliquables et un bouton « Gérer les Crédits ». Il existe en deux versions : sur `pos:dashboard` pour la journée, et sur `reports:dashboard` pour le mois.

**Ce qui se passe dans le code :**

1. `sales_dashboard()` (`apps/pos/views_frontend.py`) et `dashboard_view()` (`apps/reports/views.py`) lisent `CustomerCredit` et `CreditPayment` des clients de l'entreprise.
2. Dans `sales_dashboard()`, pour `cashier` et `boutique_manager` qui ont un emplacement, le calcul se limite aux crédits dont la vente vient de cet emplacement.
3. Chaque vue calcule les chiffres du tableau ci-dessous.
4. `apps/pos/templates/pos/dashboard.html` et `apps/reports/templates/reports/dashboard.html` les affichent. Les cartes mènent à `pos:sales_list` ou `customers:credit_list`.

| Carte | Calcul | Période | Lien |
|---|---|---|---|
| Encaissé | Ventes `completed` − crédit donné + remboursements | Jour ou mois | `pos:sales_list` |
| Crédit Donné | Somme de `CustomerCredit.original_amount` | Jour ou mois | `pos:sales_list` avec `payment=credit` |
| Remboursements | Somme de `CreditPayment.amount` | Jour ou mois | `customers:credit_list` |
| Crédit en Cours | Somme de `remaining_amount` des crédits `pending` et `partial`, avec le nombre de clients | Toujours le total | `customers:credit_list` |

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Panneau du jour, route `pos:dashboard` | `apps/pos/views_frontend.py` | `sales_dashboard()` |
| Panneau du mois, route `reports:dashboard` | `apps/reports/views.py` | `dashboard_view()` |
| Crédits du rôle patron | `apps/core/dashboard_views.py` | `patron_dashboard()` |
| Crédits du rôle comptable | `apps/core/dashboard_views.py` | `comptable_dashboard()` |
| Crédits accordés du caissier | `apps/core/dashboard_views.py` | `caisse_dashboard()` |

**Règles à connaître :**

- `pos:dashboard` est ouvert à `admin`, `owner`, `manager`, `boutique_manager`, `cashier` et `accountant`. `reports:dashboard` est ouvert à `admin`, `owner`, `manager` et `accountant`.
- Le crédit en cours porte sur tout l'historique, pas seulement sur la période.
- Les ventes à crédit faites à la caisse créent un crédit de 0 FB. Elles comptent donc dans « Encaissé » et pas dans « Crédit Donné » ni dans le montant de « Crédit en Cours ». Leur client compte pourtant dans le nombre de clients concernés.
- Une vente créée par l'API n'a pas d'emplacement (`SaleViewSet.perform_create()`). Son crédit n'apparaît donc pas dans le panneau limité à un emplacement.
- `caisse_dashboard()` calcule autrement : sa carte « Crédits accordés » additionne `Sale.total_amount` des ventes à crédit du jour de l'utilisateur. Elle peut donc afficher un montant alors que le panneau affiche 0.

**Pour le tester :** avec le rôle `manager`, notez « Crédit en Cours » sur `/pos/dashboard/`. Enregistrez un remboursement de 500 FB sur un crédit ouvert : la carte baisse de 500 FB et « Remboursements Aujourd'hui » augmente de 500 FB.

## Les points de fidélité

**Ce que voit l'utilisateur :** aucune page web ne montre les points d'un client. Ils apparaissent dans la colonne « Points Fidélité » du rapport Excel des clients, dans le champ `loyalty_points` de l'API et dans l'administration Django, en lecture seule. Le programme est désactivé par défaut.

**Ce qui se passe dans le code :**

1. À la création d'une vente `completed` avec client, `update_customer_on_sale()` lit le réglage `loyalty_program_enabled` avec `StoreSetting.get_setting()`.
2. S'il vaut `true`, le signal lit `loyalty_points_rate`, 1000 par défaut.
3. Il ajoute à `Customer.loyalty_points` le total de la vente divisé par ce taux, arrondi à l'entier inférieur.
4. `customer.save()` enregistre les points avec les autres statistiques du client.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Calcul des points | `apps/customers/signals.py` | `update_customer_on_sale()` |
| Champ | `apps/customers/models.py` | `Customer` |
| Réglages par défaut | `apps/accounting/management/commands/seed_data.py` | `Command.handle()` |
| Colonne du rapport | `apps/reports/utils/excel_generator.py` | `customer_report()` |
| Modification des réglages | `api/v1/views/settings.py` | `StoreSettingViewSet.set_setting()` |

**Règles à connaître :**

- `seed_data` crée `loyalty_program_enabled` à `false` et `loyalty_points_rate` à `1000`.
- Aucune page de l'application ne permet d'utiliser ou de modifier ces points.
- Annuler ou rembourser une vente ne retire pas ses points, pour la même raison que les totaux du client.
- Un taux invalide ou égal à 0 est ignoré : la vente réussit, sans point.

**Pour le tester :** avec un compte `manager`, envoyez `POST /api/v1/settings/set_setting/` avec `{"key": "loyalty_program_enabled", "value": "true"}`. Avec le rôle `cashier`, vendez pour 5000 FB à un client sur `/pos/`. Avec le compte `manager`, téléchargez le rapport des clients sur `/reports/` : ce client a 5 points de plus si le taux est de 1000.

## À retenir

- Un crédit naît seul, dans `update_customer_on_sale()`. Son montant est `total_amount - amount_paid`.
- La caisse envoie un montant payé égal au total : ses ventes à crédit créent une dette de 0 FB. Seule l'API crée aujourd'hui une dette réelle à partir d'une vente.
- `CreditPayment.save()` met à jour le crédit et le solde du client. Passez toujours par ce modèle pour un remboursement.
- `Customer.credit_limit` vaut 0 par défaut et n'est contrôlée que sur le montant réel du crédit.
- Sur les pages web, plusieurs colonnes de montant n'affichent que « FB » : consultez `original_amount` et `remaining_amount`, ou l'export.
