
import pandas as pd

from sqlalchemy import (
    create_engine,
    MetaData,
    Table,
    Column,
    Text,
    SmallInteger,
    BigInteger,
    Integer,
    Date,
    String,
    PrimaryKeyConstraint,
    select,
    delete,
    text
)

from sqlalchemy.dialects import mysql

from config import (
    DB_POSTGRES_SOURCE,
    DB_MYSQL_SOURCE,
    DB_POSTGRES_DESTINATION,
    CSV_PATH
)


# =====================================================
# 1. CREATION DES CONNEXIONS
# =====================================================

engine_pg_source = create_engine(DB_POSTGRES_SOURCE)

engine_mysql_source = create_engine(DB_MYSQL_SOURCE)

engine_destination = create_engine(DB_POSTGRES_DESTINATION)


# =====================================================
# 2. PREPARATION DE LA BASE DESTINATION
# =====================================================

with engine_destination.begin() as conn:
    conn.execute(text("CREATE SCHEMA IF NOT EXISTS brute"))

metadata_destination = MetaData()


# =====================================================
# 3. FONCTION POUR INSERER LES DONNEES
# =====================================================

def inserer_donnees(table_destination, donnees):

    with engine_destination.begin() as conn:

        # Vider la table pour éviter les doublons
        # lors d'une nouvelle exécution.
        conn.execute(delete(table_destination))

        if donnees:
            conn.execute(
                table_destination.insert(),
                donnees
            )

    print(
        f"{table_destination.name} : "
        f"{len(donnees)} lignes insérées."
    )


# =====================================================
# 4. EXTRACTION POSTGRESQL
# =====================================================

def extraire_postgresql():

    print("\n===== EXTRACTION POSTGRESQL =====")

    metadata_source = MetaData()

    # Récupérer automatiquement la structure
    # de la table source.
    table_source = Table(
        "clients_auto",
        metadata_source,
        schema="tp_assurance",
        autoload_with=engine_pg_source
    )

    # Reproduire la structure dans le schéma brute
    # avec le nouveau nom p_clients.
    table_destination = table_source.to_metadata(
        metadata_destination,
        name="p_clients",
        schema="brute"
    )

    metadata_destination.create_all(engine_destination)

    # Extraire toutes les données
    with engine_pg_source.connect() as conn:

        resultat = conn.execute(
            select(table_source)
        )

        donnees = [
            dict(ligne)
            for ligne in resultat.mappings()
        ]

    print("Nombre de lignes extraites :", len(donnees))

    # Insérer dans PostgreSQL destination
    inserer_donnees(
        table_destination,
        donnees
    )


# =====================================================
# 5. EXTRACTION MYSQL
# =====================================================

def convertir_type_mysql(type_source):

    # BIGINT
    if isinstance(type_source, mysql.BIGINT):
        return BigInteger()

    # TINYINT : MySQL n'a pas de type TINYINT
    # natif dans PostgreSQL.
    elif isinstance(type_source, mysql.TINYINT):
        return SmallInteger()

    # INTEGER
    elif isinstance(type_source, mysql.INTEGER):
        return Integer()

    # DATE
    elif isinstance(type_source, mysql.DATE):
        return Date()

    # VARCHAR
    elif isinstance(type_source, mysql.VARCHAR):
        return String(type_source.length)

    # TEXT
    elif isinstance(type_source, mysql.TEXT):
        return Text()

    # Autres types non prévus
    else:
        return Text()


def extraire_mysql():

    print("\n===== EXTRACTION MYSQL =====")

    metadata_source = MetaData()

    # Lire automatiquement la structure MySQL
    table_source = Table(
        "clients_life",
        metadata_source,
        schema="tp_assurance_life",
        autoload_with=engine_mysql_source
    )

    # Construire la table destination
    # en conservant les noms des colonnes.
    colonnes = []

    for colonne in table_source.columns:

        nouveau_type = convertir_type_mysql(
            colonne.type
        )

        nouvelle_colonne = Column(
            colonne.name,
            nouveau_type,
            nullable=colonne.nullable,
            primary_key=colonne.primary_key
        )

        colonnes.append(nouvelle_colonne)

    table_destination = Table(
        "m_client",
        metadata_destination,
        *colonnes,
        schema="brute"
    )

    # Reproduire la clé primaire
    cles_primaires = [
        colonne.name
        for colonne in table_source.primary_key.columns
    ]

    if cles_primaires:
        table_destination.append_constraint(
            PrimaryKeyConstraint(*cles_primaires)
        )

    metadata_destination.create_all(engine_destination)

    # Extraire toutes les données MySQL
    with engine_mysql_source.connect() as conn:

        resultat = conn.execute(
            select(table_source)
        )

        donnees = [
            dict(ligne)
            for ligne in resultat.mappings()
        ]

    print("Nombre de lignes extraites :", len(donnees))

    # Insérer dans PostgreSQL
    inserer_donnees(
        table_destination,
        donnees
    )


# =====================================================
# 6. EXTRACTION CSV
# =====================================================

def extraire_csv():

    print("\n===== EXTRACTION CSV =====")

    # Lire toutes les lignes du CSV, séparées par des points-virgules.
    # dtype=str conserve les valeurs sous forme de texte.
    df = pd.read_csv(
        CSV_PATH,
        sep=";",
        encoding="utf-8-sig",
        dtype=str,
        keep_default_na=False
        )

    print("Nombre de lignes extraites :", len(df))

    # Créer automatiquement les colonnes PostgreSQL.
    # TEXT permet de préserver les formats originaux :
    # dates, numéros avec zéros, nombres avec virgules, etc.
    colonnes = [
        Column(nom, Text(), nullable=True)
        for nom in df.columns
    ]

    table_destination = Table(
        "c_client",
        metadata_destination,
        *colonnes,
        schema="brute"
    )

    metadata_destination.create_all(engine_destination)

    # Convertir le DataFrame en liste de dictionnaires.
    donnees = df.to_dict(orient="records")

    # Insérer les données
    inserer_donnees(
        table_destination,
        donnees
    )


# =====================================================
# 7. VERIFICATION DES TRANSFERTS
# =====================================================

def verifier_transferts():

    print("\n===== VERIFICATION DES TRANSFERTS =====")

    tables = [
        "p_clients",
        "m_client",
        "c_client"
    ]

    with engine_destination.connect() as conn:

        for nom in tables:

            resultat = conn.execute(
                text(
                    f'SELECT COUNT(*) FROM brute."{nom}"'
                )
            )

            nombre = resultat.scalar()

            print(
                f"brute.{nom} : {nombre} lignes"
            )


# =====================================================
# 8. EXECUTION GENERALE
# =====================================================

def lancer_transfert():

    try:

        extraire_postgresql()

        extraire_mysql()

        extraire_csv()

        verifier_transferts()

        print("\n================================")
        print("TRANSFERT TERMINE AVEC SUCCES")
        print("================================")

    except Exception as erreur:

        print("\nERREUR DURANT LE TRANSFERT :")
        print(erreur)

        raise

    finally:

        engine_pg_source.dispose()
        engine_mysql_source.dispose()
        engine_destination.dispose()


if __name__ == "__main__":

    lancer_transfert()
