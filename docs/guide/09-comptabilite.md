# Comptabilité : dépenses, sessions de caisse et résumés journaliers

Cette partie sert à suivre l'argent qui sort (les dépenses) et l'argent compté en caisse (les sessions de caisse). Elle garde aussi un résumé financier par jour. Elle est utilisée par le patron, le gérant, le gérant de boutique, le caissier et le comptable, chacun avec des droits différents. Le code se trouve dans `apps/accounting/`.

## Sommaire

- [Catégories de dépenses](#catégories-de-dépenses)
- [Liste des dépenses](#liste-des-dépenses)
- [Créer, consulter, modifier ou supprimer une dépense](#créer-consulter-modifier-ou-supprimer-une-dépense)
- [Liste des sessions de caisse](#liste-des-sessions-de-caisse)
- [Ouvrir une session de caisse](#ouvrir-une-session-de-caisse)
- [Consulter une session de caisse](#consulter-une-session-de-caisse)
- [Fermer une session et calculer la différence](#fermer-une-session-et-calculer-la-différence)
- [Résumés journaliers](#résumés-journaliers)
- [À retenir](#à-retenir)

## Catégories de dépenses

**Ce que voit l'utilisateur :** depuis la page des dépenses, le bouton des catégories ouvre une grille de cartes. Chaque carte affiche le nom, la description, le nombre de dépenses et leur total. Une catégorie inactive apparaît grisée. Un formulaire permet d'en créer une ou d'en modifier une.

**Ce qui se passe dans le code :**

1. L'adresse `accounting:expense_category_list` appelle `expense_category_list()` dans `apps/accounting/views.py`.
2. La vue lit le modèle `ExpenseCategory` (`apps/accounting/models.py`) : les catégories de l'entreprise de l'utilisateur et les catégories globales, c'est-à-dire sans entreprise.
3. Pour chaque catégorie, elle compte les dépenses et calcule leur total, puis affiche `apps/accounting/templates/accounting/expense_category_list.html`.
4. `accounting:expense_category_create` appelle `expense_category_create()`. Sur un envoi du formulaire (POST), la vue contrôle le nom, crée la catégorie, puis revient à la liste.
5. `accounting:expense_category_edit` appelle `expense_category_edit()`. La vue contrôle le nom, enregistre le nom, la description et l'état actif, puis revient à la liste.
6. Les deux formulaires utilisent `apps/accounting/templates/accounting/expense_category_form.html`.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Liste, `accounting:expense_category_list` | `apps/accounting/views.py` | `expense_category_list()` |
| Création, `accounting:expense_category_create` | `apps/accounting/views.py` | `expense_category_create()` |
| Modification, `accounting:expense_category_edit` | `apps/accounting/views.py` | `expense_category_edit()` |
| Modèle | `apps/accounting/models.py` | `ExpenseCategory` |
| Catégories par défaut | `apps/accounting/management/commands/seed_data.py` | `Command.handle()` |

**Règles à connaître :**

- La liste est ouverte à `admin`, `owner`, `manager` et `accountant`. La création et la modification sont réservées à `admin`, `owner` et `manager`. Les autres rôles sont renvoyés vers l'accueil (`home`) avec un message d'erreur.
- Le nom est obligatoire. Il doit être unique dans l'entreprise, sans tenir compte des majuscules.
- Il n'y a pas de route de suppression. Pour retirer une catégorie, on décoche « Catégorie active ». Elle disparaît alors des listes déroulantes des dépenses, mais reste dans la liste des catégories.
- En cas d'erreur à la modification, le formulaire réaffiche les valeurs enregistrées, pas celles qui viennent d'être saisies.
- La commande `seed_data` crée des catégories globales par défaut.

**Pour le tester :** connectez-vous avec le rôle `manager` et ouvrez `/accounting/expense-categories/`. Créez une catégorie, puis recréez-la avec le même nom : le second essai affiche « Une catégorie avec ce nom existe déjà. ».

## Liste des dépenses

**Ce que voit l'utilisateur :** la page affiche trois totaux (Aujourd'hui, Ce Mois, Total Général), des filtres et un tableau paginé. On peut filtrer par recherche, catégorie, mode de paiement et période. Les boutons PDF et Excel exportent la liste filtrée.

**Ce qui se passe dans le code :**

1. L'adresse `accounting:expense_list` appelle `expense_list()` dans `apps/accounting/views.py`.
2. La vue lit le modèle `Expense`, du plus récent au plus ancien, pour l'entreprise de l'utilisateur.
3. Elle applique les filtres de l'adresse : `category`, `payment`, `date` (`today`, `week`, `month`), `start` et `end` (dates au format AAAA-MM-JJ), et `search` (description, fournisseur, référence).
4. Elle appelle `export_list_response()` (`apps/core/exports.py`). Si `?export=pdf` ou `?export=xlsx` est présent, le fichier est renvoyé et la vue s'arrête là.
5. Sinon, elle pagine à 25 lignes, calcule les trois totaux et affiche `apps/accounting/templates/accounting/expense_list.html`.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Liste, `accounting:expense_list` | `apps/accounting/views.py` | `expense_list()` |
| Modèle | `apps/accounting/models.py` | `Expense` |
| Page | `apps/accounting/templates/accounting/expense_list.html` | |
| Export | `apps/core/exports.py` | `export_list_response()` |
| Lien du menu | `templates/base.html` | |

**Règles à connaître :**

- Rôles autorisés : `admin`, `owner`, `manager`, `boutique_manager` et `accountant`.
- Les trois totaux portent sur toutes les dépenses de l'entreprise. Ils ne changent pas avec les filtres.
- Les liens de pagination conservent la recherche, la catégorie, le paiement et `date`, mais pas `start` et `end`.
- `start` et `end` servent aux liens des tableaux de bord. Il n'y a pas de champ pour les saisir sur la page. Le filtre ne s'applique que si les deux sont présents. Une date mal écrite est ignorée.
- Le bouton des catégories et le bouton de modification s'affichent pour tous les rôles de la page. Un rôle non autorisé est renvoyé vers `home` en cliquant.
- Le fonctionnement de l'export est expliqué dans [le guide des rapports et exports](10-rapports-exports.md).

**Pour le tester :** avec le rôle `accountant`, ouvrez `/accounting/expenses/?date=month`. Seules les dépenses du mois apparaissent. Cliquez sur Excel : le fichier téléchargé contient les mêmes lignes.

## Créer, consulter, modifier ou supprimer une dépense

**Ce que voit l'utilisateur :** un formulaire demande la description, le montant, la date, la catégorie, le mode de paiement, le fournisseur, la référence, l'emplacement et des notes. Une case indique si la dépense est récurrente. La fiche de détail affiche ces informations, avec des boutons pour modifier ou supprimer.

**Ce qui se passe dans le code :**

1. `accounting:expense_create` appelle `expense_create()`. La vue prépare les catégories actives et les emplacements actifs, puis affiche `apps/accounting/templates/accounting/expense_form.html`.
2. Au POST, elle contrôle la description, le montant et la date. S'il y a une erreur, elle réaffiche le formulaire avec les messages.
3. Sinon, elle crée un `Expense` avec l'utilisateur connecté et son entreprise, puis revient à `accounting:expense_list`.
4. `accounting:expense_detail` appelle `expense_detail()` et affiche `apps/accounting/templates/accounting/expense_detail.html`.
5. `accounting:expense_edit` appelle `expense_edit()`. Les contrôles sont les mêmes. La vue met à jour la dépense, puis revient à `accounting:expense_detail`.
6. `accounting:expense_delete` appelle `expense_delete()`. Le formulaire de la fiche envoie un POST, après une confirmation dans le navigateur. La vue efface la dépense et revient à la liste.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Création, `accounting:expense_create` | `apps/accounting/views.py` | `expense_create()` |
| Détail, `accounting:expense_detail` | `apps/accounting/views.py` | `expense_detail()` |
| Modification, `accounting:expense_edit` | `apps/accounting/views.py` | `expense_edit()` |
| Suppression, `accounting:expense_delete` | `apps/accounting/views.py` | `expense_delete()` |
| Contrôle des rôles | `apps/accounting/views.py` | `role_required()` |
| Modèle | `apps/accounting/models.py` | `Expense` |
| Formulaire | `apps/accounting/templates/accounting/expense_form.html` | |

**Règles à connaître :**

- Créer et consulter : `admin`, `owner`, `manager`, `boutique_manager`, `accountant`.
- Modifier : `admin`, `owner`, `manager`, `accountant`.
- Supprimer : `admin`, `owner`, `manager`.
- La description et la date sont obligatoires. Le montant doit être strictement positif. Le reste du formulaire est facultatif.
- Les modes de paiement sont ceux de `Expense.PAYMENT_METHOD_CHOICES`, avec leurs libellés anglais : `Cash`, `Mobile Money`, `Card`, `Bank Transfer`.
- La case « Dépense récurrente » ne sert qu'à l'affichage et au filtre de l'API. Elle ajoute un badge dans la liste, mais aucune dépense n'est recréée automatiquement.
- Les boutons « Modifier » et « Supprimer » de la fiche s'affichent pour tous les rôles de la page. Un rôle non autorisé est renvoyé vers `home` en cliquant.
- La date n'est contrôlée que dans le navigateur (champ de type date). Une date mal formée envoyée au serveur provoque une erreur 500.
- La suppression est définitive : la ligne est effacée de la base, il n'y a pas de `is_active` sur `Expense`.
- Une visite simple (GET) de `accounting:expense_delete` ne supprime rien : elle renvoie vers la fiche.
- En cas d'erreur à la modification, le formulaire réaffiche les valeurs enregistrées, pas celles qui viennent d'être saisies.
- Une dépense n'a pas d'effet sur le stock, ni sur les sessions de caisse.

**Pour le tester :** avec le rôle `manager`, créez une dépense de 5000 à la date du jour. Elle apparaît dans la liste et le total « Aujourd'hui » augmente de 5000. Supprimez-la depuis sa fiche : elle disparaît.

## Liste des sessions de caisse

**Ce que voit l'utilisateur :** une session de caisse est la période entre l'ouverture et la fermeture d'une caisse par une personne. La page affiche le nombre de sessions ouvertes, l'écart total, un filtre par statut et un tableau. Chaque ligne donne le caissier, l'emplacement, les dates, les soldes et la différence.

**Ce qui se passe dans le code :**

1. L'adresse `accounting:cash_session_list` appelle `cash_session_list()` dans `apps/accounting/views.py`.
2. La vue lit le modèle `CashRegisterSession` (`apps/accounting/models.py`), du plus récent au plus ancien, pour l'entreprise de l'utilisateur.
3. Elle applique les filtres `status` et `user` de l'adresse. Si le rôle est `cashier`, elle garde seulement ses propres sessions.
4. Elle pagine à 25 lignes et calcule les deux chiffres du haut.
5. Elle affiche `apps/accounting/templates/accounting/cash_session_list.html`.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Liste, `accounting:cash_session_list` | `apps/accounting/views.py` | `cash_session_list()` |
| Modèle | `apps/accounting/models.py` | `CashRegisterSession` |
| Page | `apps/accounting/templates/accounting/cash_session_list.html` | |
| Lien du menu | `templates/base.html` | |
| Tableau de bord du caissier | `apps/core/dashboard_views.py` | `caisse_dashboard()` |
| Tableau de bord du comptable | `apps/core/dashboard_views.py` | `comptable_dashboard()` |

**Règles à connaître :**

- Rôles autorisés : `admin`, `owner`, `manager`, `boutique_manager`, `cashier` et `accountant`.
- La colonne « Solde Ferm. » affiche « - » quand le solde de fermeture vaut 0. La page de la session montre bien 0.
- L'écart total additionne la différence de toutes les sessions fermées visibles. Il ne change pas avec le filtre de statut.
- Le filtre `user` existe dans la vue, mais la page n'a pas de champ pour le choisir.
- `caisse_dashboard()` indique si la dernière session du caissier est ouverte. `comptable_dashboard()` liste les six dernières sessions fermées de l'entreprise.

**Pour le tester :** avec le rôle `cashier`, ouvrez `/accounting/cash-sessions/`. Seules vos sessions apparaissent. Choisissez le statut « Fermées » : les sessions ouvertes disparaissent du tableau.

## Ouvrir une session de caisse

**Ce que voit l'utilisateur :** un formulaire demande le solde d'ouverture, c'est-à-dire l'argent présent dans la caisse au départ. On peut aussi choisir un emplacement et ajouter des notes. Après validation, la page de la session s'affiche avec le message de confirmation.

**Ce qui se passe dans le code :**

1. L'adresse `accounting:cash_session_open` appelle `cash_session_open()` dans `apps/accounting/views.py`.
2. La vue cherche une session ouverte de cet utilisateur. Si elle en trouve une, elle affiche un avertissement et redirige vers `accounting:cash_session_detail`.
3. Sinon, elle affiche `apps/accounting/templates/accounting/cash_session_open.html` avec les emplacements actifs.
4. Au POST, elle contrôle le montant, puis crée un `CashRegisterSession` avec le statut par défaut `open` et l'heure actuelle.
5. Elle redirige vers `accounting:cash_session_detail`.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Ouverture, `accounting:cash_session_open` | `apps/accounting/views.py` | `cash_session_open()` |
| Modèle | `apps/accounting/models.py` | `CashRegisterSession` |
| Formulaire | `apps/accounting/templates/accounting/cash_session_open.html` | |

**Règles à connaître :**

- Rôles autorisés : `admin`, `owner`, `manager`, `boutique_manager` et `cashier`. Le rôle `accountant` voit les sessions mais ne peut pas en ouvrir.
- Un utilisateur a une seule session ouverte à la fois. Cette règle est vérifiée dans la vue.
- Le solde d'ouverture peut valoir 0, mais il ne peut pas être négatif. Un texte non numérique affiche « Montant invalide. ».
- L'emplacement est facultatif.
- Vendre ne demande pas de session ouverte. `Sale` n'a aucun lien avec `CashRegisterSession` et `apps/pos/` n'utilise pas ce modèle.

**Pour le tester :** avec le rôle `cashier` sans session ouverte, ouvrez `/accounting/cash-sessions/open/` et saisissez 10000. La page de la session s'ouvre. Retournez sur la même adresse : vous êtes renvoyé vers cette session avec « Vous avez déjà une session ouverte. ».

## Consulter une session de caisse

**Ce que voit l'utilisateur :** un bandeau indique si la session est en cours ou fermée. Trois cartes affichent le solde d'ouverture, le solde de fermeture et l'écart, marqué « Équilibré », « Excédent » ou « Déficit ». Le bas de page donne les informations de la session et les notes. Un bouton de fermeture apparaît si la session est ouverte.

**Ce qui se passe dans le code :**

1. L'adresse `accounting:cash_session_detail` appelle `cash_session_detail()` dans `apps/accounting/views.py`.
2. La vue charge le `CashRegisterSession` et vérifie qu'il appartient à l'entreprise de l'utilisateur.
3. Si le rôle est `cashier`, elle vérifie que la session est la sienne. Sinon, elle redirige vers la liste avec un message d'erreur.
4. Elle affiche `apps/accounting/templates/accounting/cash_session_detail.html`.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Détail, `accounting:cash_session_detail` | `apps/accounting/views.py` | `cash_session_detail()` |
| Page | `apps/accounting/templates/accounting/cash_session_detail.html` | |
| Lien depuis le comptable | `templates/dashboards/comptable.html` | |

**Règles à connaître :**

- Rôles autorisés : `admin`, `owner`, `manager`, `boutique_manager`, `cashier` et `accountant`.
- Le bouton de fermeture dépend seulement du statut de la session. Pour le rôle `accountant`, il mène à un refus et à un retour vers `home`.
- La ligne « Solde attendu » n'apparaît pas quand ce solde vaut 0.

**Pour le tester :** avec le rôle `accountant`, ouvrez une session fermée depuis la liste. Les trois cartes sont remplies et le bouton de fermeture n'apparaît pas.

## Fermer une session et calculer la différence

**Ce que voit l'utilisateur :** la page rappelle le solde d'ouverture et demande de compter l'argent de la caisse. L'utilisateur saisit le solde de fermeture et peut ajouter une note. Après validation, un message annonce une caisse équilibrée, un excédent (plus d'argent que prévu) ou un déficit (moins d'argent que prévu).

**Ce qui se passe dans le code :**

1. L'adresse `accounting:cash_session_close` appelle `cash_session_close()` dans `apps/accounting/views.py`.
2. La vue charge la session et vérifie l'entreprise. Si le rôle est `cashier`, elle vérifie aussi que la session est la sienne.
3. Si la session est déjà fermée, elle affiche un avertissement et redirige vers `accounting:cash_session_detail`.
4. Sur une simple visite, elle affiche `apps/accounting/templates/accounting/cash_session_close.html`.
5. Au POST, elle contrôle le solde de fermeture.
6. Elle calcule `expected_balance = opening_balance`, puis `difference = closing_balance - expected_balance`.
7. Elle enregistre le solde de fermeture, le solde attendu, la différence, `closed_at` et le statut `closed`. La note est ajoutée à la suite des notes existantes, précédée de `[Fermeture]`.
8. Elle choisit le message selon le signe de la différence, puis redirige vers `accounting:cash_session_detail`.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Fermeture et calcul, `accounting:cash_session_close` | `apps/accounting/views.py` | `cash_session_close()` |
| Modèle | `apps/accounting/models.py` | `CashRegisterSession` |
| Formulaire | `apps/accounting/templates/accounting/cash_session_close.html` | |
| Fermeture par l'API | `api/v1/views/accounting.py` | `CashRegisterSessionViewSet.close_session()` |

**Règles à connaître :**

- Rôles autorisés : `admin`, `owner`, `manager`, `boutique_manager` et `cashier`. Un caissier ne ferme que ses propres sessions.
- **Limite actuelle du calcul :** le solde attendu est égal au solde d'ouverture. Les ventes et les dépenses de la session ne sont pas comptées. Exemple : ouverture 10 000 FB, 5 000 FB de ventes en espèces, 15 000 FB comptés. La différence affichée est +5 000 FB (excédent), alors qu'il ne manque rien et que rien n'est en trop.
- Le solde de fermeture peut valoir 0, mais il ne peut pas être négatif.
- Le formulaire prévoit un aperçu « Écart prévu » pendant la saisie, mais il ne s'affiche pas. Le template écrit `opening_balance` avec une virgule décimale, à la française, dans son script (`1000,00`), ce qui bloque ce script. L'écart réel reste calculé par le serveur à la validation.
- Une session fermée ne peut pas être rouverte par une page web.
- L'API a son propre calcul. `CashRegisterSessionViewSet.close_session()` prend le solde attendu envoyé dans la requête. S'il est absent, il prend le solde de fermeture, et la différence vaut alors 0.

**Pour le tester :** avec le rôle `cashier`, ouvrez une session à 1000, puis fermez-la à 1500. La page affiche « Session fermée. Excédent de 500.00 FB. », un écart de +500 FB et un solde attendu de 1000 FB.

## Résumés journaliers

**Ce que voit l'utilisateur :** aucune page de l'application ne les affiche, et il n'existe aucune adresse `accounting:*` pour eux. Un résumé journalier est une ligne de totaux pour une date : ventes par mode de paiement, dépenses, coût des marchandises, bénéfices, nombre de ventes et de clients. On le crée avec une commande dans le terminal. On le lit dans l'administration Django ou par l'API.

```bash
python manage.py generate_daily_summary
python manage.py generate_daily_summary --date 2026-01-31
python manage.py generate_daily_summary --backfill 2026-01-01 2026-01-31
```

**Ce qui se passe dans le code :**

1. `Command.add_arguments()` déclare `--date` et `--backfill` dans `apps/accounting/management/commands/generate_daily_summary.py`.
2. `Command.handle()` choisit les jours : l'intervalle de `--backfill`, la date de `--date`, sinon la veille.
3. `Command.generate_summary_for_date()` lit les `Sale` au statut `completed` et les `SaleItem` (`apps/pos/models.py`), les `CreditPayment` (`apps/customers/models.py`) et les `Expense` du jour.
4. Elle calcule le bénéfice brut (`gross_profit`) : ventes moins coût des marchandises (prix d'achat multiplié par la quantité).
5. Elle calcule le bénéfice net (`net_profit`) : bénéfice brut moins dépenses.
6. Elle crée ou met à jour la ligne `DailySummary` de cette date, puis affiche les chiffres dans le terminal.
7. `DailySummaryAdmin` (`apps/accounting/admin.py`) affiche ces lignes dans `/admin/`. `DailySummaryViewSet` (`api/v1/views/accounting.py`) les sert sur `/api/v1/daily-summaries/`.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Commande `generate_daily_summary` | `apps/accounting/management/commands/generate_daily_summary.py` | `Command.handle()`, `Command.generate_summary_for_date()` |
| Modèle | `apps/accounting/models.py` | `DailySummary` |
| Administration | `apps/accounting/admin.py` | `DailySummaryAdmin` |
| API | `api/v1/views/accounting.py` | `DailySummaryViewSet`, `DailySummaryViewSet.daily_summary()` |
| Données de démonstration | `apps/core/management/commands/seed_full_data.py` | `Command.create_daily_summaries()` |

**Règles à connaître :**

- Le résumé n'est pas calculé automatiquement : aucune vue, aucun signal et aucune tâche planifiée du dépôt ne lance la commande.
- La commande additionne toutes les entreprises et tous les emplacements. La ligne créée n'a ni entreprise ni emplacement.
- Si plusieurs lignes existent déjà pour une date, la commande échoue avec `MultipleObjectsReturned`. Cela peut arriver avec `seed_full_data`, qui crée une ligne par boutique. Avec `--backfill`, l'erreur de ce jour est affichée et la boucle continue. Si une seule ligne existe, ses totaux sont remplacés.
- Dans l'administration, les résumés ne peuvent être ni ajoutés ni modifiés.
- `DailySummaryViewSet.daily_summary()` ne crée pas de résumé. Il renvoie une erreur 404 si la date n'a pas de ligne.
- Dans cette commande, le bénéfice net déduit le coût des marchandises. Le « Bénéfice Net » du [tableau de bord des rapports](10-rapports-exports.md) ne le déduit pas : les deux chiffres ne sont donc pas comparables.

**Pour le tester :** sur une base locale, lancez `python manage.py generate_daily_summary --date` suivi d'une date qui a des ventes et qui n'a pas encore de résumé. Le terminal affiche les totaux. Avec un compte qui a accès à l'administration Django, ouvrez ensuite `/admin/` : la ligne apparaît dans les résumés journaliers, sans possibilité de la modifier.

## À retenir

- Toutes les vues web de la comptabilité sont dans `apps/accounting/views.py`, et leurs rôles sont déclarés par `role_required()`.
- Une dépense supprimée est effacée définitivement. Une catégorie se désactive et ne se supprime pas.
- À la fermeture d'une session, la différence vaut solde de fermeture moins solde d'ouverture : les ventes ne sont pas prises en compte.
- Les sessions de caisse ne sont pas reliées aux ventes : on peut vendre sans session ouverte.
- Les résumés journaliers viennent de la commande `generate_daily_summary`. Aucune page web ne les affiche.
