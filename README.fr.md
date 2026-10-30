# Stock Control & POS

Application de gestion de stock et de point de vente (POS) pour boutiques, dépôts et pharmacies.

*English version: [README.md](README.md)*

## Fonctionnalités

- **Point de vente :** ventes, paiements (espèces, mobile, carte, crédit)
- **Stock :** entrées, sorties, mouvements, alertes de stock faible et de rupture
- **Multi-emplacements :** dépôt et boutiques, transferts de stock entre eux
- **Clients :** suivi des crédits et des remboursements
- **Comptabilité :** dépenses, sessions de caisse, résumés journaliers
- **Rapports :** tableaux de bord par rôle, exports PDF et Excel
- **API REST :** authentification JWT, documentation sur `/api/v1/docs/`

**Technologies :** Django 5.0, Django REST Framework, MySQL 8, TailwindCSS, AlpineJS.

## Installation sur Windows

### 1. Installer les outils

| Outil | Remarque |
|---|---|
| [Python 3.12 ou 3.13](https://www.python.org/downloads/windows/) | Cochez **« Add python.exe to PATH »** dans l'installateur. Évitez Python 3.14 pour l'instant. |
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) | Choisissez l'option WSL 2 et redémarrez si demandé. Si WSL manque : `wsl --install` dans PowerShell en administrateur. |
| [VS Code](https://code.visualstudio.com/) | Facultatif, utile comme éditeur. |

Lancez Docker Desktop et attendez qu'il soit prêt avant de continuer.

### 2. Télécharger le projet

Sur la page GitHub : **Code → Download ZIP**, puis décompressez le dossier.
Avec Git : `git clone https://github.com/hectorally94/stock-control-pos.git`

Ouvrez PowerShell dans le dossier du projet.

### 3. Créer l'environnement Python

```powershell
py -3.13 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Si vous avez installé Python 3.12, utilisez `py -3.12`.

### 4. Créer le fichier de configuration

```powershell
Copy-Item .env.example .env
notepad .env
```

Le Bloc-notes s'ouvre. Modifiez ces deux lignes pour qu'elles soient exactement comme ceci :

```
DB_PASSWORD=stockcontrol123
DB_HOST=127.0.0.1
```

Enregistrez avec `Ctrl+S`, puis fermez le Bloc-notes.

### 5. Démarrer la base de données

```powershell
docker compose up -d mysql
```

Attendez environ 1 minute que MySQL démarre, puis vérifiez :

```powershell
docker ps
```

La ligne `stock_control_mysql` doit afficher `(healthy)`. Si elle affiche `(health: starting)`, attendez encore et relancez la commande.

### 6. Remplir la base de données

Choisissez **une seule** des deux options.

#### Option A : importer la vraie base de données

Le fichier de la base de données n'est pas sur GitHub, car il contient des données réelles. Le responsable du projet vous l'envoie en privé. Il s'appelle `stock_control_20261030.sql`.

**Attention :** l'import remplace tout le contenu de votre base locale. Ce n'est pas un problème lors de la première installation.

**Étape 1 : vérifier que PowerShell est dans le bon dossier**

```powershell
dir manage.py
```

Le fichier `manage.py` doit s'afficher. Si vous voyez une erreur, ouvrez le bon dossier : dans l'Explorateur Windows, entrez dans le dossier du projet (celui qui contient `manage.py`), faites un clic droit dans une zone vide, puis choisissez **« Ouvrir dans le terminal »**. Après un téléchargement ZIP, ce dossier peut se trouver à l'intérieur d'un autre dossier du même nom.

Si PowerShell vient d'être rouvert, réactivez l'environnement Python :

```powershell
.venv\Scripts\Activate.ps1
```

**Étape 2 : créer le dossier `database`**

```powershell
mkdir database
```

**Étape 3 : placer le fichier dans ce dossier**

Dans l'Explorateur Windows, copiez le fichier `stock_control_20261030.sql` (souvent dans **Téléchargements**) et collez-le dans le dossier `database` du projet. Vérifiez ensuite :

```powershell
dir database
```

Vous devez voir `stock_control_20261030.sql`. Si le nom est différent (par exemple avec `(1)` à la fin), renommez le fichier.

**Étape 4 : copier le fichier dans le conteneur Docker**

```powershell
docker cp database\stock_control_20261030.sql stock_control_mysql:/tmp/backup.sql
```

**Étape 5 : importer le fichier dans MySQL**

Copiez cette commande en entier, sur une seule ligne :

```powershell
docker exec stock_control_mysql sh -c "mysql -uroot -pstockcontrol123 --default-character-set=utf8mb4 stock_control_pos < /tmp/backup.sql"
```

Cela prend quelques secondes. Le message `Using a password on the command line interface can be insecure` est normal : ce n'est pas une erreur.

**Étape 6 : vérifier l'import**

```powershell
docker exec stock_control_mysql mysql -uroot -pstockcontrol123 -e "SELECT COUNT(*) AS produits FROM stock_control_pos.products;"
```

Le résultat doit afficher **340**.

**Étape 7 : terminer la préparation**

```powershell
python manage.py migrate
```

Le message `No migrations to apply` est normal. N'exécutez ni `seed_data` ni `createsuperuser` : les données et les comptes viennent déjà du fichier importé. Demandez les identifiants au responsable du projet.

Passez ensuite à la section **« 7. Lancer l'application »** ci-dessous.

#### Option B : commencer avec une base vide

```powershell
python manage.py migrate
python manage.py seed_data
python manage.py createsuperuser
```

### 7. Lancer l'application

```powershell
python manage.py runserver
```

- Application : http://127.0.0.1:8000
- Documentation de l'API : http://127.0.0.1:8000/api/v1/docs/

Arrêtez le serveur avec `Ctrl+C`.

## Reprendre le travail plus tard

1. Lancez Docker Desktop.
2. Dans PowerShell, depuis le dossier du projet :

```powershell
docker compose up -d mysql
.venv\Scripts\Activate.ps1
python manage.py runserver
```

## Lancer les tests

Les tests utilisent SQLite en mémoire : Docker n'est pas nécessaire.

```powershell
pytest --ignore=tests/test_import_catalog.py
```

`tests/test_import_catalog.py` est exclu car il a besoin du fichier Excel du client, qui n'est pas sur GitHub.

## Problèmes fréquents

| Problème | Solution |
|---|---|
| « L'exécution de scripts est désactivée » à l'activation | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, puis réactivez |
| `py -3.13` introuvable | Fermez et rouvrez PowerShell, ou réinstallez Python avec l'option PATH cochée |
| `mysqlclient` ne s'installe pas | Vérifiez avec `python --version` que vous utilisez Python 3.12 ou 3.13 |
| `Can't connect to MySQL` (erreur 2003) | Docker n'est pas lancé ou MySQL démarre encore : `docker start stock_control_mysql`, attendez 30 secondes |
| `No such container: stock_control_mysql` | La base n'est pas démarrée : relancez `docker compose up -d mysql` |
| `The system cannot find the path specified` avec `docker cp` | Le fichier n'est pas dans `database` ou son nom est différent : vérifiez avec `dir database` |
| `Unknown database 'stock_control_pos'` | MySQL n'était pas encore prêt : attendez `(healthy)` dans `docker ps` et recommencez l'import |
| Port 3306 déjà utilisé | MySQL est déjà installé sur la machine : arrêtez son service, ou changez le port dans `docker-compose.yml` et `.env` |

## Sécurité

- Ne publiez jamais le fichier `.env` ni le fichier `.sql` de la base de données.
- Si vous recevez le fichier `.sql`, gardez-le privé : il contient des données réelles.
