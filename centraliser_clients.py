
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime

from config import (
    DB_POSTGRES_DESTINATION
)

# ==========================================
# 1. CONNEXION A POSTGRESQL
# ==========================================


engine = create_engine(DB_POSTGRES_DESTINATION)


# ==========================================
# 2. CONVERSION DES DATES
# ==========================================

def convertir_date(valeur):

    if pd.isna(valeur):
        return None

    valeur = str(valeur).strip()

    formats = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y%m%d",
        "%d%m%Y"
    ]

    for format_date in formats:
        try:
            return datetime.strptime(
                valeur, format_date
            ).date()
        except ValueError:
            pass

    return None


# ==========================================
# 3. EXTRACTION DES DONNEES
# ==========================================

def extraire_donnees(conn):

    print("Extraction des donnees...")

    P = pd.read_sql_query(
        text("SELECT * FROM brute.p_clients"),
        conn
    )

    C = pd.read_sql_query(
        text("SELECT * FROM brute.c_client"),
        conn
    )

    M = pd.read_sql_query(
        text("SELECT * FROM brute.m_client"),
        conn
    )

    print("P :", len(P), "clients")
    print("C :", len(C), "clients")
    print("M :", len(M), "clients")

    return P, C, M


# ==========================================
# 4. HARMONISATION DES DONNEES
# ==========================================

def harmoniser_donnees(P, C, M):

    print("Harmonisation des donnees...")

    # --------------------------------------
    # SOURCE P
    # --------------------------------------

    P = P.rename(columns={
        "id_client_auto": "REFERENCE_SOURCE",
        "numero_cin": "NUMERO_CIN",
        "nom_assure": "NOM",
        "prenoms_assure": "PRENOMS",
        "ne_le": "DATE_NAISSANCE",
        "ne_a": "LIEU_NAISSANCE",
        "ville_residence": "ADRESSE",
        "mobile": "TELEPHONE",
        "courriel": "EMAIL",
        "sexe": "SEXE",
        "formule_auto": "PRODUIT",
        "immatriculation": "IMMATRICULATION",
        "annee_vehicule": "ANNEE_VEHICULE"
    })

    P["SOURCE"] = "P"

    P["REFERENCE_SOURCE"] = P["REFERENCE_SOURCE"].astype(str)

    # --------------------------------------
    # SOURCE C
    # --------------------------------------

    C = C.rename(columns={
        "ref_fiche": "REFERENCE_SOURCE",
        "piece_identite": "NUMERO_CIN",
        "patronyme": "NOM",
        "autres_noms": "PRENOMS",
        "date_naissance": "DATE_NAISSANCE",
        "commune_origine": "LIEU_NAISSANCE",
        "localite": "ADRESSE",
        "contact_tel": "TELEPHONE",
        "contact_mail": "EMAIL",
        "code_sexe": "SEXE",
        "type_navire": "PRODUIT",
        "plateforme": "PLATEFORME",
        "culture": "CULTURE",
        "superficie_ha": "SUPERFICIE_HA",
        "garantie_agricole": "GARANTIE_AGRICOLE",
        "port_attache": "PORT_ATTACHE",
        "garantie_maritime": "GARANTIE_MARITIME"
    })

    C["SOURCE"] = "C"

    C["REFERENCE_SOURCE"] = C["REFERENCE_SOURCE"].astype(str)

    # --------------------------------------
    # SOURCE M
    # --------------------------------------

    M = M.rename(columns={
        "ref_adherent": "REFERENCE_SOURCE",
        "cin_numerique": "NUMERO_CIN",
        "nom_adherent": "NOM",
        "prenoms_adherent": "PRENOMS",
        "date_naiss": "DATE_NAISSANCE",
        "lieu_naiss": "LIEU_NAISSANCE",
        "commune_domicile": "ADRESSE",
        "tel_contact": "TELEPHONE",
        "email_contact": "EMAIL",
        "genre": "SEXE",
        "produit": "PRODUIT",
        "cotisation_mensuelle_ar": "COTISATION_MENSUELLE_AR",
        "date_adhesion": "DATE_ADHESION"
    })

    M["SOURCE"] = "M"

    M["REFERENCE_SOURCE"] = M["REFERENCE_SOURCE"].astype(str)

    # --------------------------------------
    # CONVERSION DES TYPES
    # --------------------------------------

    for df in [P, C, M]:

        df["NUMERO_CIN"] = df["NUMERO_CIN"].astype("string")

        df["DATE_NAISSANCE"] = df["DATE_NAISSANCE"].apply(
            convertir_date
        )

    M["DATE_ADHESION"] = M["DATE_ADHESION"].apply(
        convertir_date
    )

    # Conversion de la superficie agricole
    if "SUPERFICIE_HA" in C.columns:

        C["SUPERFICIE_HA"] = pd.to_numeric(
            C["SUPERFICIE_HA"]
            .astype("string")
            .str.replace(",", ".", regex=False),
            errors="coerce"
        )

    # --------------------------------------
    # COLONNES COMMUNES
    # --------------------------------------

    colonnes = [
        "SOURCE",
        "REFERENCE_SOURCE",
        "NUMERO_CIN",
        "NOM",
        "PRENOMS",
        "DATE_NAISSANCE",
        "LIEU_NAISSANCE",
        "ADRESSE",
        "TELEPHONE",
        "EMAIL",
        "SEXE",
        "PRODUIT",
        "IMMATRICULATION",
        "ANNEE_VEHICULE",
        "PLATEFORME",
        "CULTURE",
        "SUPERFICIE_HA",
        "GARANTIE_AGRICOLE",
        "PORT_ATTACHE",
        "GARANTIE_MARITIME",
        "COTISATION_MENSUELLE_AR",
        "DATE_ADHESION"
    ]

    P = P.reindex(columns=colonnes)
    C = C.reindex(columns=colonnes)
    M = M.reindex(columns=colonnes)

    # Fusion des trois sources
    clients = pd.concat(
        [P, C, M],
        ignore_index=True
    )

    print("Total des clients :", len(clients))

    # Mettre toutes les valeurs textuelles en majuscules sans convertir
    # les objets date en texte.
    for colonne in clients.select_dtypes(
        include=["object", "string"]
    ).columns:
        clients[colonne] = clients[colonne].map(
            lambda valeur: valeur.strip().upper()
            if isinstance(valeur, str) else valeur
        )

    # Retirer le préfixe CIN et les séparateurs; ne conserver que les chiffres.
    # Le type nullable Int64 correspond au BIGINT PostgreSQL et garde les NULL.
    clients["NUMERO_CIN"] = (
        clients["NUMERO_CIN"]
        .astype("string")
        .str.replace(r"\D", "", regex=True)
        .replace("", pd.NA)
    )
    clients["NUMERO_CIN"] = pd.to_numeric(
        clients["NUMERO_CIN"],
        errors="coerce"
    ).astype("Int64")

    return clients


# ==========================================
# 5. CREATION DU SCHEMA ET DE LA TABLE
# ==========================================

def creer_table(conn):

    print("Creation du schema et de la table...")

    conn.execute(text("""
        CREATE SCHEMA IF NOT EXISTS lake;
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS lake.all_client (

            ID_CLIENT BIGSERIAL PRIMARY KEY,

            SOURCE VARCHAR(20) NOT NULL,
            REFERENCE_SOURCE TEXT,

            NUMERO_CIN BIGINT,
            NOM TEXT,
            PRENOMS TEXT,

            DATE_NAISSANCE DATE,
            LIEU_NAISSANCE TEXT,
            ADRESSE TEXT,

            TELEPHONE TEXT,
            EMAIL TEXT,
            SEXE TEXT,

            PRODUIT TEXT,

            IMMATRICULATION TEXT,
            ANNEE_VEHICULE SMALLINT,

            PLATEFORME TEXT,
            CULTURE TEXT,
            SUPERFICIE_HA NUMERIC(12,2),
            GARANTIE_AGRICOLE TEXT,

            PORT_ATTACHE TEXT,
            GARANTIE_MARITIME TEXT,

            COTISATION_MENSUELLE_AR INTEGER,
            DATE_ADHESION DATE
        );
    """))


# ==========================================
# 6. CHARGEMENT DANS LA TABLE CENTRALE
# ==========================================


def charger_donnees(conn, clients):

    print("Chargement des donnees...")

    # Vérifier les colonnes avant insertion
    print("\nNombre de colonnes :", len(clients.columns))
    print("Noms des colonnes :")
    print(clients.columns.tolist())

    # Vérifier les éventuelles colonnes dupliquées
    if clients.columns.duplicated().any():
        raise ValueError("Des colonnes sont dupliquees !")

    # Vérifier que les colonnes correspondent à la table
    colonnes_attendues = [
        "SOURCE",
        "REFERENCE_SOURCE",
        "NUMERO_CIN",
        "NOM",
        "PRENOMS",
        "DATE_NAISSANCE",
        "LIEU_NAISSANCE",
        "ADRESSE",
        "TELEPHONE",
        "EMAIL",
        "SEXE",
        "PRODUIT",
        "IMMATRICULATION",
        "ANNEE_VEHICULE",
        "PLATEFORME",
        "CULTURE",
        "SUPERFICIE_HA",
        "GARANTIE_AGRICOLE",
        "PORT_ATTACHE",
        "GARANTIE_MARITIME",
        "COTISATION_MENSUELLE_AR",
        "DATE_ADHESION"
    ]

    if list(clients.columns) != colonnes_attendues:
        raise ValueError(
            "Les colonnes du DataFrame ne correspondent pas "
            "aux colonnes attendues."
        )

    # Vider la table
    conn.execute(text("""
        TRUNCATE TABLE lake.all_client
        RESTART IDENTITY;
    """))

    # Les colonnes PostgreSQL creees ci-dessus sont en minuscules.
    # pandas doit donc utiliser les memes noms sans guillemets.
    clients_a_inserer = clients.rename(
        columns=lambda nom: nom.lower()
    )

    # Insertion
    clients_a_inserer.to_sql(
        name="all_client",
        schema="lake",
        con=conn,
        if_exists="append",
        index=False,
        chunksize=500,
        method=None
    )

    print("Chargement termine !")

# ==========================================
# 7. EXECUTION DE L'ETL
# ==========================================

def lancer_etl():

    try:

        with engine.begin() as conn:

            P, C, M = extraire_donnees(conn)

            clients = harmoniser_donnees(P, C, M)

            creer_table(conn)

            charger_donnees(conn, clients)

        print("\nETL TERMINE AVEC SUCCES !")

    except Exception as e:
        print("\nERREUR :", e)
        raise


if __name__ == "__main__":
    lancer_etl()
