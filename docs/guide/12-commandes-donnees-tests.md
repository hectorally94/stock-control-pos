# Commandes, données et tests

Cette partie explique comment remplir une base, la faire évoluer et vérifier le code. Elle s'adresse au développeur, qui travaille dans un terminal. Une commande de gestion est un script du projet, lancé avec `python manage.py <nom>`. Ces commandes sont rangées dans les dossiers `management/commands/` des applications.

## Sommaire

- [`generate_daily_summary`](#generate_daily_summary)
- [`seed_data`](#seed_data)
- [`seed_full_data`](#seed_full_data)
- [`setup_enterprise`](#setup_enterprise)
- [`import_catalog`](#import_catalog)
- [`seed_catalog`](#seed_catalog)
- [`seed_scenario`](#seed_scenario)
- [Le fichier de base de données](#le-fichier-de-base-de-données)
- [Les migrations](#les-migrations)
- [Organisation des tests](#organisation-des-tests)
- [Ajouter un test](#ajouter-un-test)
- [À retenir](#à-retenir)

## `generate_daily_summary`

**Ce que voit l'utilisateur :** le développeur lance la commande. Le terminal affiche, pour chaque jour traité, les ventes, les dépenses, les bénéfices et la répartition des paiements. Le résultat est enregistré dans `DailySummary`, que l'API sert sur `daily-summaries`.

```bash
python manage.py generate_daily_summary
python manage.py generate_daily_summary --date 2026-10-20
python manage.py generate_daily_summary --backfill 2026-10-01 2026-10-20
```

| Option | Effet |
|---|---|
| Aucune | Traite la veille |
| `--date AAAA-MM-JJ` | Traite ce jour |
| `--backfill DEBUT FIN` | Traite tous les jours de la période, bornes comprises. Cette option passe avant `--date` |

**Quand l'utiliser :** pour calculer le résumé d'un jour terminé, ou pour rattraper une période passée. Le code du projet ne la planifie pas : lancez-la vous-même, ou confiez-la à un planificateur.

**Ce qui se passe dans le code :**

1. `Command.add_arguments()` déclare les options.
2. `Command.handle()` choisit les jours et refuse une date mal formée ou une période inversée, avec une `CommandError`.
3. Pour chaque jour, `Command.generate_summary_for_date()` lit les `Sale` au statut `completed`, et additionne `total_amount` au total et par mode de paiement.
4. La méthode calcule le coût des marchandises à partir de `SaleItem`, soit `purchase_price` × `quantity`.
5. Elle additionne `CreditPayment` (crédit encaissé) et `Expense` (dépenses).
6. Elle calcule le bénéfice brut (ventes moins coût) et le bénéfice net (brut moins dépenses).
7. Elle crée ou met à jour la ligne `DailySummary` de cette date.
8. `Command._format_currency()` met en forme les montants affichés.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Commande | `apps/accounting/management/commands/generate_daily_summary.py` | `Command.handle()` |
| Calcul d'un jour | `apps/accounting/management/commands/generate_daily_summary.py` | `Command.generate_summary_for_date()` |
| Résultat | `apps/accounting/models.py` | `DailySummary` |

**Règles à connaître :**

- Le calcul regroupe toutes les entreprises et tous les emplacements. `enterprise` et `location` restent vides sur la ligne créée.
- La commande cherche la ligne par date seule. Si plusieurs lignes existent pour ce jour, elle échoue avec `MultipleObjectsReturned`. C'est le cas pour les jours générés par `seed_full_data`, qui crée une ligne par boutique.
- Avec `--backfill`, une erreur est affichée et comptée, puis la boucle continue. Sans `--backfill`, la commande s'arrête.
- Relancer un jour écrase ses chiffres, avec le contenu actuel de la base. Si les ventes ont été effacées, le résumé repasse à 0 pour les ventes.

**Pour le tester :** après `migrate`, lancez la commande sur une base vide. Elle affiche `créé` et des montants à 0. Relancez-la : elle affiche `mis à jour`.

## `seed_data`

**Ce que voit l'utilisateur :** le terminal liste les catégories de dépenses et les paramètres, créés ou déjà présents.

```bash
python manage.py seed_data
```

Cette commande n'a pas d'option.

**Quand l'utiliser :** une fois, juste après `migrate`, sur une base vide. Elle est inutile si vous importez le fichier de base de données.

**Ce qui se passe dans le code :**

1. `Command.handle()` parcourt 9 catégories de dépenses, nommées en anglais (`Rent`, `Utilities`...).
2. Elle appelle `ExpenseCategory.objects.get_or_create()` pour chacune, en cherchant par nom.
3. Elle parcourt 21 paramètres (`store_name`, `currency_code`, `loyalty_points_rate`...).
4. Elle appelle `StoreSetting.objects.get_or_create()` pour chacun, en cherchant par clé.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Commande | `apps/accounting/management/commands/seed_data.py` | `Command.handle()` |
| Catégories | `apps/accounting/models.py` | `ExpenseCategory` |
| Paramètres | `apps/settings/models.py` | `StoreSetting` |
| Lecture de `loyalty_program_enabled` | `apps/customers/signals.py` | `update_customer_on_sale()` |

**Règles à connaître :**

- La commande est relançable sans doublon. Elle ne modifie pas une valeur existante.
- Les catégories créées n'ont pas d'entreprise.

**Pour le tester :** lancez-la deux fois. La seconde fois, chaque ligne indique que l'élément existe déjà.

## `seed_full_data`

**Ce que voit l'utilisateur :** le terminal affiche dix étapes, de `[1/10]` à `[10/10]`, puis le tableau des comptes de test créés. Sur une base SQLite, l'exécution a pris environ une minute.

```bash
python manage.py seed_full_data
python manage.py seed_full_data --clear
```

| Option | Effet |
|---|---|
| Aucune | Crée les données de démonstration |
| `--clear` | Vide d'abord les ventes, crédits, transferts, stocks, dépenses, résumés, clients, produits et catégories de produits |

**Quand l'utiliser :** sur une base de développement vide, pour tester les tableaux de bord avec beaucoup de données. C'est l'option B de `README.fr.md`. Ne l'utilisez jamais sur une base réelle.

**Ce qui se passe dans le code :**

1. `Command.handle()` appelle `Command.clear_data()` si `--clear` est présent.
2. Dans une transaction, `Command.create_enterprise()` crée l'entreprise de code `CGM-001`.
3. `Command.create_locations()` crée un dépôt et trois boutiques. `Command.create_users()` crée les comptes de démonstration.
4. `Command.create_categories()` et `Command.create_products()` créent 10 catégories et 80 produits.
5. `Command.create_initial_stock()` crée le stock du dépôt, avec une quantité aléatoire entre 50 et 500.
6. `Command.create_transfers()` crée 30 transferts sur 30 jours. `Command.create_customers()` crée 120 clients.
7. `Command.create_sales()` crée les ventes des 60 derniers jours, environ 1 350 selon le hasard.
8. `Command.create_expenses()` crée les dépenses. `Command.create_daily_summaries()` crée une ligne par boutique et par jour sur 30 jours, soit 90 résumés lors de l'essai.
9. Après la transaction, `Command.print_login_credentials()` affiche les comptes.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Commande | `apps/core/management/commands/seed_full_data.py` | `Command.handle()` |
| Effacement | `apps/core/management/commands/seed_full_data.py` | `Command.clear_data()` |
| Ventes | `apps/core/management/commands/seed_full_data.py` | `Command.create_sales()` |
| Comptes affichés | `apps/core/management/commands/seed_full_data.py` | `Command.print_login_credentials()` |

**Règles à connaître :**

- La commande n'est pas relançable sans effet : sans `--clear`, une seconde exécution a doublé les ventes, les transferts, les dépenses et les clients.
- `--clear` efface les données de toutes les entreprises, pas seulement `CGM-001`. Il garde les entreprises, les emplacements, les utilisateurs, les catégories de dépenses et les sessions de caisse. `LocationStock` n'est pas vidé directement, mais ses lignes disparaissent avec les produits.
- `--clear` s'arrête avec `RestrictedError` si un `CustomerCredit` existe, car il supprime les ventes avant les crédits. Comme cet effacement est hors transaction, les `SaleItem` sont déjà supprimés à ce moment-là.
- Les données créées ne contiennent aucune vente à crédit : les modes de paiement sont `cash`, `mobile_money` et `card`.
- `Stock` et `LocationStock` ne concordent pas après cette commande. `Command.create_initial_stock()` et `Command.create_transfers()` écrivent la quantité dans `Stock`, puis `StockMovement.save()` l'ajoute encore. Lors d'un essai, `Stock` totalisait 49 108 unités et `LocationStock` 19 895.
- Chaque produit a 4 lignes `Stock`. Une vente créée par l'API échoue donc sur ces données (voir [API REST](11-api-rest.md)).
- `generate_daily_summary` échoue sur les jours déjà résumés par cette commande.

**Pour le tester :** sur une base vide, lancez la commande, puis connectez-vous avec le compte `owner` affiché dans le terminal. Le tableau de bord du patron montre des ventes.

## `setup_enterprise`

**Ce que voit l'utilisateur :** le terminal indique ce qui a été créé ou mis à jour, puis résume l'entreprise et ses emplacements.

```bash
python manage.py setup_enterprise
```

Cette commande n'a pas d'option.

**Quand l'utiliser :** pour préparer l'entreprise `DEMO-ENT`, par exemple avant `import_catalog`, ou pour rattacher à une entreprise d'anciennes données qui n'en ont pas.

**Ce qui se passe dans le code :**

1. `Command.handle()` s'exécute dans une transaction.
2. Elle crée ou retrouve l'entreprise `DEMO-ENT`.
3. Elle crée ou retrouve le dépôt `DEPOT-MAIN` et les boutiques `BTQ-CENTRE` et `BTQ-NORD`.
4. Elle cherche les comptes nommés `admin`, `manager`, `stock_manager`, `cashier` et `accountant`, puis les rattache à l'entreprise s'ils existent.
5. Elle rattache à `DEMO-ENT` toutes les lignes sans entreprise : catégories, produits, clients, stocks, mouvements, ventes, catégories de dépenses, dépenses, sessions de caisse et résumés.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Commande | `apps/core/management/commands/setup_enterprise.py` | `Command.handle()` |
| Entreprise | `apps/core/models.py` | `Enterprise` |
| Emplacements | `apps/locations/models.py` | `Location` |

**Règles à connaître :**

- La commande ne crée aucun utilisateur. Elle modifie seulement les comptes existants qui portent ces noms.
- Elle change des rôles : `admin` devient `owner`, `manager` devient `boutique_manager`, `stock_manager` devient `warehouse_manager`.
- Les stocks et mouvements sans entreprise passent au dépôt. Les ventes, dépenses, sessions et résumés sans entreprise passent à `BTQ-CENTRE`.

**Pour le tester :** sur une base vide, lancez-la deux fois. La seconde fois, le terminal indique que l'entreprise et les emplacements existent déjà.

## `import_catalog`

**Ce que voit l'utilisateur :** le terminal affiche l'entreprise, l'emplacement choisi et le nombre de produits par catégorie. Il termine par le nombre de produits créés et la valeur totale du stock.

```bash
python manage.py import_catalog --enterprise DEMO-ENT --file CHEMIN/VERS/FICHIER.xlsx --dry-run
python manage.py import_catalog --enterprise DEMO-ENT --file CHEMIN/VERS/FICHIER.xlsx
python manage.py import_catalog --enterprise DEMO-ENT --file CHEMIN/VERS/FICHIER.xlsx --no-wipe
```

| Option | Valeur par défaut | Effet |
|---|---|---|
| `--file` | `stockcontrollist.xlsx` dans `apps/products/data/` | Chemin du classeur Excel |
| `--enterprise` | `DEMO-ENT` | Code de l'entreprise |
| `--location` | Dépôt principal, sinon un dépôt, sinon un emplacement actif | Identifiant ou nom de l'emplacement qui reçoit le stock |
| `--no-wipe` | Désactivée | Importe sans rien effacer |
| `--dry-run` | Désactivée | Lit le fichier et affiche un résumé, sans rien écrire |

**Quand l'utiliser :** pour remplacer tout le catalogue d'une entreprise à partir de la liste Excel du client. Lancez toujours `--dry-run` d'abord.

**Ce qui se passe dans le code :**

1. `Command.handle()` vérifie le fichier, l'entreprise et l'emplacement. Elle choisit aussi l'utilisateur auquel attribuer les mouvements : un `admin` ou `owner` de l'entreprise, sinon un autre de ses comptes, sinon un superuser.
2. `Command._parse_sheet()` lit chaque feuille. Elle repère la ligne d'en-tête contenant `QTE`, puis les colonnes de code (`CODE` ou `PIECE`), de quantité (`MAG` ou `QTE`) et de prix (`P.U` ou `PU`).
3. `_clean_id()`, `_is_number()` et `_to_decimal()` nettoient les cellules.
4. Les trois premières feuilles deviennent `Roulements`, `Paliers & Roulements montés` et `Pièces & Accessoires`. Une feuille suivante garde son propre nom.
5. Avec `--dry-run`, la commande affiche quelques exemples et s'arrête.
6. Sinon, dans une transaction, `Command._wipe()` efface les données de l'entreprise, sauf avec `--no-wipe`.
7. La commande crée les catégories et les produits, en cherchant chaque produit par nom.
8. Pour chaque quantité positive, elle crée un `StockMovement` d'entrée, de raison `initial_stock`. `StockMovement.save()` met à jour `Stock` et `LocationStock`.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Commande | `apps/products/management/commands/import_catalog.py` | `Command.handle()` |
| Lecture d'une feuille | `apps/products/management/commands/import_catalog.py` | `Command._parse_sheet()` |
| Effacement | `apps/products/management/commands/import_catalog.py` | `Command._wipe()` |
| Tests | `tests/test_import_catalog.py` | `TestImportCatalog` |

**Règles à connaître :**

- **Sans `--no-wipe`, l'effacement est total pour l'entreprise :** produits, catégories, ventes, crédits, paiements de crédit, mouvements, transferts et stocks. Les compteurs des clients repassent à zéro. Les clients, les emplacements, les utilisateurs et les dépenses restent.
- Le fichier Excel n'est pas dans le dépôt, car `.gitignore` l'exclut. Sans `--file`, la commande s'arrête donc avec `File not found`.
- Le produit reçoit le même prix d'achat et de vente, un seuil de stock à 0 et l'unité `piece`. Son `sku` reprend les 50 premiers caractères du nom.
- Avec `--no-wipe`, un produit existant n'est pas modifié, mais une nouvelle entrée de stock est créée. Relancer l'import ajoute donc les quantités une seconde fois.
- `--dry-run` a besoin lui aussi d'une entreprise, d'un emplacement et d'un utilisateur valides.

**Pour le tester :** lancez `setup_enterprise`, créez un superuser ou un compte rattaché à `DEMO-ENT`, puis lancez `--dry-run` sur votre fichier Excel. Le terminal affiche `Dry run` et le nombre de produits. Aucune donnée ne change.

## `seed_catalog`

**Ce que voit l'utilisateur :** pour chaque entreprise, le terminal indique le nombre de catégories et de produits assurés, et combien sont nouveaux.

```bash
python manage.py seed_catalog
python manage.py seed_catalog --enterprise DEMO-ENT
python manage.py seed_catalog --enterprise DEMO-ENT --with-stock
```

| Option | Effet |
|---|---|
| Aucune | Remplit toutes les entreprises existantes |
| `--enterprise CODE` | Remplit seulement cette entreprise |
| `--with-stock` | Crée aussi une ligne `Stock` à quantité 0 par produit |

**Quand l'utiliser :** pour obtenir un petit catalogue d'exemple dans une entreprise qui existe déjà, sans créer d'utilisateurs ni de ventes.

**Ce qui se passe dans le code :**

1. `Command.handle()` sélectionne les entreprises. S'il n'y en a aucune, elle affiche un message et s'arrête.
2. `Command._seed_enterprise()` crée 7 catégories, en cherchant par nom dans l'entreprise.
3. Elle crée les 26 produits de la liste `CATALOG`, en cherchant par `sku` dans l'entreprise.
4. Avec `--with-stock`, `Command._ensure_stock()` crée les lignes `Stock` au dépôt principal, sinon au premier emplacement actif.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Commande | `apps/products/management/commands/seed_catalog.py` | `Command.handle()` |
| Création du catalogue | `apps/products/management/commands/seed_catalog.py` | `Command._seed_enterprise()` |
| Lignes de stock | `apps/products/management/commands/seed_catalog.py` | `Command._ensure_stock()` |
| Tests | `tests/test_stock_entry_dropdown.py` | `TestSeedCatalogCommand` |

**Règles à connaître :**

- La commande est relançable sans doublon.
- Elle ne met aucune marchandise en stock. `--with-stock` écrit des lignes à 0 dans `Stock`, sans mouvement ni `LocationStock`.

**Pour le tester :** lancez `setup_enterprise`, puis deux fois `seed_catalog`. La seconde fois, le terminal indique `0 new`.

## `seed_scenario`

**Ce que voit l'utilisateur :** le terminal indique le dépôt, les boutiques, les transferts réalisés et le stock final de chaque emplacement.

```bash
python manage.py seed_scenario --enterprise DEMO-ENT
python manage.py seed_scenario --enterprise DEMO-ENT --units 500 --per-boutique 50 --boutiques 3 --demo-cases
python manage.py seed_scenario --enterprise DEMO-ENT --reset
```

| Option | Défaut | Effet |
|---|---|---|
| `--enterprise CODE` | Entreprise du dépôt principal, sinon la première | Entreprise visée |
| `--units` | 500 | Stock initial du dépôt, par produit |
| `--per-boutique` | 50 | Quantité envoyée à chaque boutique, par produit |
| `--boutiques` | 3 | Nombre de boutiques à servir |
| `--reset` | Désactivée | Efface d'abord transferts, mouvements et stocks de l'entreprise |
| `--demo-cases` | Désactivée | Crée un exemple de stock faible et un exemple de rupture |

**Quand l'utiliser :** pour tester le parcours complet du stock, avec de vrais transferts, après avoir créé un catalogue avec `seed_catalog` ou `import_catalog`.

**Ce qui se passe dans le code :**

1. `Command.handle()` choisit l'entreprise, puis appelle `Command._run()`, qui s'exécute dans une transaction.
2. `Command._run()` cherche un utilisateur de l'entreprise. Avec `--reset`, elle appelle `Command._reset_inventory()`.
3. Elle crée si besoin les types d'emplacement, le dépôt et les boutiques manquantes.
4. Pour chaque produit actif, elle crée un `StockMovement` d'entrée au dépôt, avec la note `SCENARIO_INIT`, s'il n'existe pas déjà.
5. Pour chaque boutique sans transfert portant la note `SCENARIO:<code>`, elle crée un `Transfer` et ses `TransferItem`.
6. Elle appelle `Transfer.send()`, puis `Transfer.receive()`. Ces méthodes créent les mouvements de sortie et d'entrée.
7. Avec `--demo-cases`, `Command._make_demo_cases()` utilise `current_qty()` et `drive_to()` pour descendre deux produits de la première boutique.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Commande | `apps/products/management/commands/seed_scenario.py` | `Command.handle()` |
| Scénario | `apps/products/management/commands/seed_scenario.py` | `Command._run()` |
| Remise à zéro | `apps/products/management/commands/seed_scenario.py` | `Command._reset_inventory()` |
| Transferts | `apps/transfers/models.py` | `Transfer.send()`, `Transfer.receive()` |
| Tests | `tests/test_multilocation_inventory.py` | `TestSeedScenarioCommand` |

**Règles à connaître :**

- L'entreprise doit déjà avoir un utilisateur et des produits. Sinon, la commande affiche `No user found` ou `No products` et s'arrête.
- Elle est relançable sans doublon grâce aux notes `SCENARIO_INIT` et `SCENARIO:<code>`. Changer `--units` lors d'une relance ne change donc rien pour les produits déjà traités, sauf avec `--reset`.
- Si le dépôt n'a pas assez de stock pour un transfert, `Transfer.send()` lève une `ValidationError`. La commande s'arrête avec une trace d'erreur et la transaction annule tout, y compris `--reset`.
- Le dépôt utilisé est le premier dépôt actif, même s'il n'est pas marqué `is_main_warehouse`.
- La commande connaît 5 noms de boutiques par défaut. Elle ne peut donc pas en créer plus de 5.
- `--reset` ne supprime ni les ventes, ni les produits, ni les emplacements, ni les utilisateurs.

**Pour le tester :** lancez `setup_enterprise`, `seed_catalog`, puis `seed_scenario` en `--enterprise DEMO-ENT`, avec au moins un compte rattaché à cette entreprise. Connecté en `owner`, ouvrez `locations:dashboard` : le dépôt et les boutiques ont du stock.

## Le fichier de base de données

**Ce que voit l'utilisateur :** le développeur importe `database/stock_control_20261030.sql` dans MySQL et obtient une base déjà remplie, sans lancer de commande de remplissage. C'est l'option A de `README.fr.md`.

```powershell
docker cp database\stock_control_20261030.sql stock_control_mysql:/tmp/backup.sql
docker exec stock_control_mysql sh -c "mysql -uroot -pVOTRE_MOT_DE_PASSE --default-character-set=utf8mb4 stock_control_pos < /tmp/backup.sql"
python manage.py migrate
```

Le mot de passe local se trouve dans `docker-compose.yml`.

**Ce qui se passe dans le code :**

1. Le fichier est une copie SQL de 35 tables. Pour chaque table, il contient `DROP TABLE IF EXISTS`, `CREATE TABLE`, puis les données.
2. L'import remplace donc les tables existantes de votre base locale.
3. La table `django_migrations` du fichier enregistre les 20 migrations du projet. `migrate` n'a donc rien à appliquer pour ces applications.
4. Au démarrage, `stock_control/settings.py` lit les identifiants de connexion dans `.env`, puis Django utilise ces tables.

Contenu du fichier :

| Données | Nombre |
|---|---|
| Entreprises (`DEMO-ENT`) | 1 |
| Emplacements | 4 |
| Comptes utilisateurs | 9 |
| Catégories de produits | 3 |
| Produits | 340 |
| Lignes `Stock` | 343 |
| Lignes `LocationStock` | 343 |
| Mouvements de stock | 353 |
| Transferts | 6 |
| Clients | 15 |
| Dépenses | 78 |
| Sessions de caisse | 24 |
| Résumés journaliers | 37 |
| Paramètres du magasin | 21 |
| Ventes et crédits | 0 |

Voici le lien entre ce fichier et chaque commande :

| Commande | Lien avec le fichier | Faut-il la lancer après l'import ? |
|---|---|---|
| `seed_data` | Le fichier contient déjà 9 catégories de dépenses et 21 paramètres | Non |
| `seed_full_data` | Le fichier ne vient pas de cette commande : elle crée une autre entreprise, `CGM-001` | Non. `--clear` effacerait aussi les données du fichier |
| `setup_enterprise` | L'entreprise `DEMO-ENT` et le code `DEPOT-MAIN` sont déjà présents, mais pas `BTQ-CENTRE` | Non. Elle créerait une boutique et y rattacherait des comptes |
| `import_catalog` | Le catalogue en porte la trace : ses 3 catégories, ses 340 produits et la référence `Import stock 31/12/2024` sur les mouvements | Non, sauf pour remplacer le catalogue. Il faut alors le fichier Excel |
| `seed_catalog` | Ses produits d'exemple ne font pas partie du catalogue | Non. Elle ajouterait 26 produits |
| `seed_scenario` | Le fichier ne contient aucune note `SCENARIO_INIT` | Non. Elle ajouterait du stock et des transferts pour tous les produits |
| `generate_daily_summary` | Les 37 résumés n'ont ni entreprise ni emplacement : la commande peut les mettre à jour | Oui pour les nouveaux jours. Sur les anciens jours, les ventes repasseraient à 0, car le fichier n'en contient plus |

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Copie de la base | `database/stock_control_20261030.sql` | Aucune |
| Procédure d'import | `README.fr.md` | Section 6, option A |
| Base MySQL locale | `docker-compose.yml` | Service `mysql` |
| Schéma détaillé | `docs/database_schema.md` | Aucune |

**Règles à connaître :**

- L'import efface le contenu actuel des tables. Ne le faites que sur une base de développement.
- Ne lancez pas `seed_data` ni `createsuperuser` après l'import : `README.fr.md` l'indique, les données et les comptes viennent du fichier.
- N'ajoutez jamais de données confidentielles dans le dossier `database/`, car il est public.
- La table `cache_table` existe déjà dans le fichier. Avec l'option B, il faut la créer par `python manage.py createcachetable`, car `CACHES` de `stock_control/settings.py` utilise `DatabaseCache`.

**Pour le tester :** après l'import, comptez les produits dans la table `products` de MySQL. Le résultat doit être 340.

## Les migrations

**Ce que voit l'utilisateur :** après une modification de modèle, le développeur crée puis applique une migration. Une migration est un fichier Python qui décrit un changement de la structure de la base.

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py showmigrations
python manage.py makemigrations --check --dry-run
```

La dernière commande vérifie, sans rien écrire, que les modèles et les migrations concordent. Elle affiche aujourd'hui `No changes detected`.

**Ce qui se passe dans le code :**

1. Vous modifiez un modèle, par exemple dans `apps/products/models.py`.
2. `makemigrations` compare les modèles aux migrations et écrit un nouveau fichier dans `apps/<nom>/migrations/`.
3. `migrate` applique les fichiers manquants, puis les note dans la table `django_migrations`.
4. Certaines migrations écrivent aussi des données. `seed_types()` crée ainsi les types Dépôt et Boutique pour chaque entreprise existante, et relie les emplacements à ces types. `unseed_types()` fait le chemin inverse.

| Application | Nombre de migrations |
|---|---|
| `accounting`, `customers`, `locations` | 3 chacune |
| `accounts`, `pos`, `products`, `stock` | 2 chacune |
| `core`, `settings`, `transfers` | 1 chacune |
| `reports` | Aucune, car l'application n'a pas de modèle |

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Migrations de chaque application | `apps/<nom>/migrations/` | `Migration` |
| Migration de données | `apps/locations/migrations/0003_seed_location_types.py` | `seed_types()` |
| Schéma détaillé | `docs/database_schema.md` | Aucune |

**Règles à connaître :**

- Validez le fichier de migration avec le changement de modèle : les autres développeurs et les tests en ont besoin.
- Les tests construisent leur base avec ces migrations. Une migration oubliée peut donc faire échouer les tests.
- Après l'import du fichier SQL, lancez quand même `migrate` : il applique les migrations plus récentes que le fichier.

**Pour le tester :** ajoutez un champ à un modèle, lancez `makemigrations --check --dry-run` : la commande signale le changement. Retirez ensuite le champ.

## Organisation des tests

**Ce que voit l'utilisateur :** le développeur lance `pytest`, et chaque test s'affiche avec son résultat. Les tests n'ont besoin ni de Docker ni de MySQL. À la date de ce guide, 302 tests passent sans le fichier Excel.

```bash
pytest --ignore=tests/test_import_catalog.py
pytest tests/test_api.py -v
pytest tests/test_api.py::TestSaleAPI::test_create_sale -v
```

**Ce qui se passe dans le code :**

1. `pytest.ini` désigne `stock_control.settings_test` comme réglages, et limite la recherche des tests au dossier `tests/`.
2. `stock_control/settings_test.py` importe `stock_control/settings.py`, puis remplace quelques réglages : SQLite en mémoire pour la base, un cache en mémoire, des sessions en base et un hachage de mot de passe rapide.
3. pytest-django crée la base de test en appliquant les migrations.
4. `tests/conftest.py` déclare les fixtures. Une fixture est un élément préparé automatiquement pour un test, qui le demande en paramètre.
5. `tests/factories.py` déclare les factories. Une factory crée un objet valide, en remplissant les champs que vous ne précisez pas.
6. Chaque test marqué `@pytest.mark.django_db` a accès à la base. pytest-django annule ses écritures à la fin du test.

| Fichier | Ce qu'il couvre |
|---|---|
| `tests/test_api.py` | API REST |
| `tests/test_models.py` | Modèles |
| `tests/test_views.py` | Vues web |
| `tests/test_forms_e2e.py` | Formulaires |
| `tests/test_ui_navigation.py` | Navigation |
| `tests/test_role_dashboards.py` | Tableaux de bord par rôle |
| `tests/test_multilocation_inventory.py` | Stock multi-emplacements, et `seed_scenario` |
| `tests/test_locations_crud.py` | Gestion des emplacements |
| `tests/test_product_list_locations.py` | Listes de produits par emplacement |
| `tests/test_stock_entry_dropdown.py` | Formulaire d'entrée de stock, et `seed_catalog` |
| `tests/test_import_catalog.py` | `import_catalog`, avec le fichier Excel du client |

Les fixtures de `tests/conftest.py` :

| Fixtures | Contenu |
|---|---|
| `api_client` | Client API sans authentification |
| `admin_client`, `manager_client`, `cashier_client`, `stock_manager_client` | Client API déjà authentifié avec ce rôle |
| `authenticated_client` | Client API authentifié en `admin` |
| `admin_user`, `manager_user`, `cashier_user`, `stock_manager_user`, `accountant_user` | Utilisateur de ce rôle |
| `user_factory`, `category_factory`, `product_factory`, `stock_factory`, `customer_factory`, `sale_factory`, `expense_factory` | Accès à la factory |

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Configuration de pytest | `pytest.ini` | Section `pytest` |
| Réglages de test | `stock_control/settings_test.py` | `DATABASES`, `CACHES`, `PASSWORD_HASHERS` |
| Fixtures | `tests/conftest.py` | `api_client`, `cashier_client`... |
| Factories | `tests/factories.py` | `UserFactory`, `ProductFactory`, `SaleFactory`... |
| Vente complète | `tests/factories.py` | `create_complete_sale()` |
| Stock avec historique | `tests/factories.py` | `create_stock_with_movements()` |

**Règles à connaître :**

- `pytest.ini` contient `-x`, qui arrête tout au premier échec. Sans le fichier Excel, un simple `pytest` s'arrête donc sur `tests/test_import_catalog.py`. Utilisez `--ignore=tests/test_import_catalog.py`.
- `pytest.ini` active aussi la mesure de couverture, qui génère le dossier `htmlcov/`.
- Les clients authentifiés de `tests/conftest.py` partagent la même fixture `api_client`. Dans un test, en demander deux revient à garder le dernier rôle authentifié.
- Il n'existe pas de fixture de client pour `accountant`, `warehouse_manager` ni `boutique_manager`. Il n'existe pas non plus de factory pour `Enterprise`, `Location` ni `Transfer` : les tests les créent directement.
- Par défaut, les factories ne remplissent ni `enterprise` ni `location`. Pour une vue filtrée par entreprise, passez-les en paramètres.
- Évitez le SQL propre à MySQL dans le code : il ne fonctionne pas avec SQLite pendant les tests.
- `test_batch4.py`, à la racine du projet, n'est pas dans `tests/` : un simple `pytest` ne le lance pas.

**Pour le tester :** lancez `pytest tests/test_api.py -v`, sans démarrer Docker. Tous les tests de ce fichier passent.

## Ajouter un test

**Ce que voit l'utilisateur :** le développeur écrit une fonction `test_...`, la lance, et voit `passed`. Si le code change plus tard et casse ce comportement, le test échoue.

Exemple : vérifier qu'une vente créée par l'API retire la quantité du stock. Ajoutez ce test dans `tests/test_api.py`, ou dans un nouveau fichier du dossier `tests/` dont le nom commence par `test_`.

```python
import pytest
from decimal import Decimal
from django.urls import reverse
from rest_framework import status

from apps.stock.models import Stock
from tests.factories import StockFactory


@pytest.mark.django_db
class TestSaleUpdatesStock:

    # Vérifie qu'une vente créée par l'API retire la quantité du stock.
    # Liens : SaleViewSet (api/v1/views/pos.py), apps/pos/signals.py, apps/stock/models.py
    def test_sale_reduces_stock(self, cashier_client, product_factory):
        product = product_factory(sale_price=Decimal('1000.00'))
        StockFactory(product=product, quantity=Decimal('10.000'))

        response = cashier_client.post(
            reverse('sale-list'),
            {'payment_method': 'cash', 'items': [{'product': product.id, 'quantity': '3'}]},
            format='json',
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert Stock.objects.get(product=product).quantity == Decimal('7.000')
```

**Ce qui se passe dans le code :**

1. pytest trouve la classe `Test...` et la méthode `test_...`, selon les règles de `pytest.ini`.
2. Il prépare `cashier_client`, qui crée `cashier_user` et authentifie `api_client`.
3. `product_factory` et `StockFactory` créent le produit et sa ligne de stock.
4. `reverse` transforme le nom de route `sale-list` en adresse.
5. Le client envoie la requête à `SaleViewSet`, sans passer par un vrai serveur.
6. Les `assert` vérifient la réponse et la base.

**Où le trouver :**

| Élément | Fichier | Fonction ou classe |
|---|---|---|
| Tests de l'API existants | `tests/test_api.py` | `TestSaleAPI` |
| Client de caissier | `tests/conftest.py` | `cashier_client` |
| Factories | `tests/factories.py` | `ProductFactory`, `StockFactory` |

**Règles à connaître :**

- Le nom du fichier doit correspondre à `test_*.py`, `*_tests.py` ou `tests.py`, celui de la classe à `Test*`, et celui de la fonction à `test_*`. Le projet utilise `test_*.py`.
- Sans `@pytest.mark.django_db`, le test ne peut pas accéder à la base.
- Pour une page web, utilisez la fixture `client` de pytest-django et `client.force_login(user)`, comme dans `tests/test_views.py`.
- Pour une commande, utilisez `call_command`, comme dans `tests/test_multilocation_inventory.py`.
- Les fichiers du projet commentent chaque test avec deux lignes en français : ce qu'il vérifie, puis ses liens.

**Pour le tester :** lancez `pytest tests/test_api.py::TestSaleUpdatesStock -v`, en remplaçant le nom du fichier si vous avez créé le vôtre. Le test passe. Remplacez ensuite `7.000` par `8.000` : il échoue, ce qui prouve qu'il vérifie vraiment le stock.

## À retenir

- Base vide, deux chemins à ne pas combiner : soit l'import de `database/stock_control_20261030.sql` puis `migrate`, soit `migrate`, `createcachetable`, `seed_data` et `seed_full_data`.
- `import_catalog` efface par défaut toutes les données liées au catalogue de l'entreprise. Lancez d'abord `--dry-run`.
- `seed_data`, `setup_enterprise`, `seed_catalog`, `seed_scenario` et `generate_daily_summary` sont relançables sans doublon. `seed_full_data` et `import_catalog --no-wipe` ne le sont pas.
- Après une modification de modèle : `makemigrations`, puis `migrate`, et validez le fichier de migration.
- Lancez les tests avec `pytest --ignore=tests/test_import_catalog.py` tant que vous n'avez pas le fichier Excel du client.
