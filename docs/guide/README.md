# Guide des fonctionnalités

Ce guide raconte ce que fait toute l'application et indique, pour chaque fonctionnalité, dans quel fichier et quelle fonction la trouver.

Chaque section suit le même plan :

- **Ce que voit l'utilisateur :** la fonctionnalité vue depuis l'écran.
- **Ce qui se passe dans le code :** les étapes dans l'ordre d'exécution.
- **Où le trouver :** les fichiers, fonctions et adresses.
- **Règles à connaître :** rôles, validations et effets automatiques.
- **Pour le tester :** une vérification à faire vous-même.

Avant de commencer, installez le projet avec [README.fr.md](../../README.fr.md) et parcourez [ARCHITECTURE.md](../../ARCHITECTURE.md).

## Les guides

| N° | Guide | Vous y trouverez |
|---|---|---|
| 01 | [Connexion, utilisateurs et rôles](01-connexion-utilisateurs-roles.md) | Connexion, comptes, rôles, journal d'actions, entreprise, paramètres, menu |
| 02 | [Tableaux de bord](02-tableaux-de-bord.md) | Page d'accueil selon le rôle, les quatre tableaux de bord |
| 03 | [Produits et catégories](03-produits-categories.md) | Catalogue, catégories, activation et désactivation |
| 04 | [Stock](04-stock.md) | Entrées, stock faible, ruptures, historique, `StockMovement` |
| 05 | [Emplacements](05-emplacements.md) | Dépôts, boutiques, types, stock par emplacement |
| 06 | [Transferts](06-transferts.md) | Création, envoi, réception et annulation d'un transfert |
| 07 | [Caisse et ventes](07-caisse-ventes.md) | Écran de caisse, parcours d'une vente, reçus, historique |
| 08 | [Clients et crédits](08-clients-credits.md) | Clients, ventes à crédit, remboursements |
| 09 | [Comptabilité](09-comptabilite.md) | Dépenses, sessions de caisse, résumés journaliers |
| 10 | [Rapports et exports](10-rapports-exports.md) | Rapports, exports Excel et PDF |
| 11 | [API REST](11-api-rest.md) | Connexion JWT et les 22 ressources de l'API |
| 12 | [Commandes, données et tests](12-commandes-donnees-tests.md) | Commandes `manage.py`, base de données, tests |

## Par où commencer

Lisez dans cet ordre, car chaque étape s'appuie sur la précédente :

1. [Connexion, utilisateurs et rôles](01-connexion-utilisateurs-roles.md) : qui peut faire quoi.
2. [Produits et catégories](03-produits-categories.md) : ce que l'on vend.
3. [Stock](04-stock.md) : **la partie la plus importante**, car tout passe par `StockMovement`.
4. [Emplacements](05-emplacements.md) puis [Transferts](06-transferts.md) : où se trouve le stock et comment il circule.
5. [Caisse et ventes](07-caisse-ventes.md) : **le parcours principal** de l'application.
6. [Clients et crédits](08-clients-credits.md), puis [Comptabilité](09-comptabilite.md).
7. [Tableaux de bord](02-tableaux-de-bord.md) et [Rapports et exports](10-rapports-exports.md) : ce que les responsables consultent.
8. [API REST](11-api-rest.md) et [Commandes, données et tests](12-commandes-donnees-tests.md) : pour aller plus loin.

## Je cherche...

| Je cherche... | Guide |
|---|---|
| Ce qui se passe quand un caissier vend un produit | [07](07-caisse-ventes.md) |
| Comment le stock est mis à jour | [04](04-stock.md) |
| Comment envoyer du stock du dépôt vers une boutique | [06](06-transferts.md) |
| Comment fonctionne une vente à crédit | [07](07-caisse-ventes.md) et [08](08-clients-credits.md) |
| Ce que chaque rôle a le droit de voir | [01](01-connexion-utilisateurs-roles.md) |
| D'où viennent les chiffres d'un tableau de bord | [02](02-tableaux-de-bord.md) |
| Comment ajouter un export PDF ou Excel à une page | [10](10-rapports-exports.md) |
| Comment appeler l'API | [11](11-api-rest.md) |
| Comment remplir la base de données | [12](12-commandes-donnees-tests.md) |
| Comment ajouter un test | [12](12-commandes-donnees-tests.md) |

## Comment lire le code avec ce guide

1. Ouvrez la section de la fonctionnalité dans le guide.
2. Ouvrez le fichier et la fonction indiqués dans **Où le trouver**.
3. Lisez les commentaires `Rôle` et `Liens` au-dessus de chaque fonction : ils indiquent ce qu'elle fait et avec quels fichiers elle est reliée.
4. Faites la vérification de **Pour le tester** dans l'application.

Si le guide et le code ne disent pas la même chose, c'est le code qui fait foi.
