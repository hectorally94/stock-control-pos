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

Dans le fichier, mettez `DB_PASSWORD=stockcontrol123`, puis enregistrez.

### 5. Démarrer la base de données

```powershell
docker compose up -d mysql
```

Attendez environ 30 secondes que MySQL démarre.

### 6. Remplir la base de données

Choisissez **une seule** des deux options.

#### Option A : importer la vraie base de données

Le fichier `.sql` n'est pas sur GitHub, car il contient des données réelles. Demandez-le au responsable du projet, puis placez-le dans un dossier `database\` à la racine du projet.

**Attention :** l'import remplace le contenu de votre base locale.

```powershell
docker cp database\stock_control_20261030.sql stock_control_mysql:/tmp/backup.sql
docker exec stock_control_mysql sh -c "mysql -uroot -pstockcontrol123 --default-character-set=utf8mb4 stock_control_pos < /tmp/backup.sql"
python manage.py migrate
```

Les comptes utilisateurs viennent de la base importée : demandez les identifiants au responsable du projet.

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
| Port 3306 déjà utilisé | MySQL est déjà installé sur la machine : arrêtez son service, ou changez le port dans `docker-compose.yml` et `.env` |

## Sécurité

- Ne publiez jamais le fichier `.env` ni le fichier `.sql` de la base de données.
- Si vous recevez le fichier `.sql`, gardez-le privé : il contient des données réelles.
