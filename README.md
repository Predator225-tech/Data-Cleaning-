# ETL de centralisation des clients

Ce projet extrait trois sources (PostgreSQL, MySQL et CSV), les harmonise et charge leurs lignes dans la table PostgreSQL `lake.all_client`.

## Prérequis

- Python 3.10 ou plus récent
- PostgreSQL avec les sources auto disponibles dans `tp_assurance.clients_auto`
- MySQL avec la source vie disponible dans `tp_assurance_life.clients_life`
- Le fichier CSV `data/clients_autre_leger.csv`

Les tables source doivent exister avant le lancement. Les scripts de préparation du jeu de données sont dans `TP-DLA/` (voir leurs en-têtes pour les versions de serveur requises).

## Installation

Depuis le dossier du projet :

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
```

Sous Windows PowerShell, activez l'environnement avec `venv\Scripts\Activate.ps1`.

## Configuration des bases

Les paramètres par défaut sont définis dans `config.py`. Pour les modifier sans toucher au code, définissez les variables d'environnement avant de lancer les scripts :

| Variable | Valeur par défaut |
|---|---|
| `PG_SOURCE_HOST` | `localhost` |
| `PG_SOURCE_PORT` | `5432` |
| `PG_SOURCE_DB` | `tp_assurance_auto` |
| `PG_DEST_HOST` | `localhost` |
| `PG_DEST_PORT` | `5432` |
| `PG_DEST_DB` | `netoyage` |
| `PG_USER` | `postgres` |
| `PG_PASSWORD` | valeur par défaut définie dans `config.py` |
| `MYSQL_SOURCE_HOST` | `localhost` |
| `MYSQL_SOURCE_PORT` | `3306` |
| `MYSQL_SOURCE_DB` | `tp_assurance_life` |
| `MYSQL_USER` | `root` |
| `MYSQL_PASSWORD` | valeur par défaut définie dans `config.py` |

Exemple bash (remplacez les identifiants par ceux de votre environnement) :

```bash
export PG_PASSWORD='votre_mot_de_passe_postgres'
export MYSQL_PASSWORD='votre_mot_de_passe_mysql'
```

La destination PostgreSQL doit exister. Pour la créer et initialiser les schémas, le fichier `Script.sql` peut être exécuté avec un compte autorisé à créer une base :

```bash
psql -U postgres -d postgres -f Script.sql
```

Ce script crée la base `netoyage`, puis les schémas `brute` et `lake`. Si la base ou ces schémas existent déjà, adaptez le script ou utilisez une destination vide.

## Lancement

Exécutez les deux étapes dans cet ordre :

```bash
python main.py
python centraliser_clients.py
```

- `main.py` copie les sources PostgreSQL, MySQL et CSV dans le schéma `brute` de la base destination.
- `centraliser_clients.py` harmonise les colonnes, met les valeurs textuelles en majuscules, nettoie le CIN et charge les lignes dans `lake.all_client`.

La table centrale est vidée et rechargée à chaque exécution de la deuxième étape. Les valeurs de CIN sont stockées en entier PostgreSQL `BIGINT`; les valeurs absentes ou invalides deviennent `NULL`.

## Vérification

Dans PostgreSQL, connecté à la base destination :

```sql
SELECT source, count(*)
FROM lake.all_client
GROUP BY source
ORDER BY source;

SELECT count(*) AS total
FROM lake.all_client;

SELECT pg_typeof(numero_cin), numero_cin
FROM lake.all_client
WHERE numero_cin IS NOT NULL
LIMIT 10;
```

La dernière requête doit afficher le type `bigint`.

Pour le détail des correspondances de colonnes et des transformations, consultez [documentation/doc.md](documentation/doc.md).



800003046307# Data-Cleaning-
