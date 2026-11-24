# Documentation de l'ETL des clients

## Objectif

Le pipeline transfère trois sources vers PostgreSQL, harmonise leurs champs puis charge une table unique : `lake.all_client`.

| Alias | Table brute | Origine |
|---|---|---|
| P | `brute.p_clients` | PostgreSQL, clients auto |
| M | `brute.m_client` | MySQL, clients vie |
| C | `brute.c_client` | CSV, autres clients |

La consolidation est une union de lignes (`UNION ALL` logique), pas une jointure entre les sources. La colonne `SOURCE` garde la provenance de chaque ligne.

## Fichiers utilisés et modifiés

- `config.py` : adresses des bases et chemin du CSV (paramétrables par variables d'environnement).
- `main.py` : extrait les trois systèmes sources vers les tables brutes du schéma `brute`. Le CSV est lu en entier avec le séparateur point-virgule.
- `centraliser_clients.py` : extrait les tables brutes, renomme/harmonise les colonnes, applique les transformations et recharge `lake.all_client`.
- `Script.sql` : crée la base et les schémas PostgreSQL.
- `requirements.txt` : dépendances Python nécessaires.
- `data/clients_autre_leger.csv` : fichier CSV source.

Aucun nouveau fichier Python n'a été nécessaire : le travail ETL est implémenté dans le fichier existant `centraliser_clients.py`. Le présent `doc.md` documente son fonctionnement.

## Schéma harmonisé

Les sources ont des noms de champs différents. `harmoniser_donnees` renomme les champs vers les colonnes communes suivantes :

`SOURCE`, `REFERENCE_SOURCE`, `NUMERO_CIN`, `NOM`, `PRENOMS`, `DATE_NAISSANCE`, `LIEU_NAISSANCE`, `ADRESSE`, `TELEPHONE`, `EMAIL`, `SEXE`, `PRODUIT`, `IMMATRICULATION`, `ANNEE_VEHICULE`, `PLATEFORME`, `CULTURE`, `SUPERFICIE_HA`, `GARANTIE_AGRICOLE`, `PORT_ATTACHE`, `GARANTIE_MARITIME`, `COTISATION_MENSUELLE_AR`, `DATE_ADHESION`.

Un champ absent dans une source devient NULL pour ses lignes. La concaténation conserve ainsi une structure commune sans perdre les colonnes propres à une source.

## Transformations

1. **Majuscules** : toutes les valeurs textuelles sont débarrassées des espaces en début/fin et mises en majuscules. Les dates et les valeurs numériques gardent leur type et leur valeur.
2. **CIN** : les caractères autres que les chiffres sont retirés (ce qui enlève notamment le préfixe `CIN` et les séparateurs). Une valeur vide/invalide devient NULL. Le résultat est converti en entier nullable Pandas `Int64`, puis stocké en PostgreSQL `BIGINT` (entier signé 64 bits). Exemple : `CIN- 800003046307` devient `800003046307`. Comme le CIN est stocké en nombre, d'éventuels zéros initiaux ne peuvent pas être conservés.
3. **Dates** : plusieurs formats usuels sont interprétés par `convertir_date`; les dates non reconnues deviennent NULL.
4. **Superficie** : la virgule décimale est remplacée par un point et la valeur convertie en numérique.

Les colonnes sont nommées en majuscules dans le DataFrame. PostgreSQL convertit automatiquement les identifiants non entourés de guillemets en minuscules : les noms SQL apparaissent donc en minuscules (par exemple `numero_cin`). Les valeurs textuelles, elles, sont conservées en majuscules.

## Chargement et exécution

1. Configurer les variables d'environnement des bases si les paramètres par défaut de `config.py` ne correspondent pas à l'installation.
2. Charger les sources brutes :

   ```bash
   venv/bin/python main.py
   ```

3. Consolider et transformer les lignes :

   ```bash
   venv/bin/python centraliser_clients.py
   ```

Le chargement vide `lake.all_client` puis insère l'ensemble des lignes (exécution rejouable, sans accumulation de doublons). La clé primaire `id_client` est générée par PostgreSQL. Il faut lancer l'extraction avant la centralisation, et configurer les accès aux bases sources et destination.

## Vérifications SQL

```sql
SELECT source, count(*)
FROM lake.all_client
GROUP BY source
ORDER BY source;

SELECT count(*) AS total FROM lake.all_client;

SELECT pg_typeof(numero_cin), numero_cin
FROM lake.all_client
WHERE numero_cin IS NOT NULL
LIMIT 10;
```

Les volumes varient selon les données présentes dans les sources. La dernière requête doit indiquer le type `bigint`.
