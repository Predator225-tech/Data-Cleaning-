
import os
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent


def database_url(prefix, host, port, database, user, password, driver):
    return (
        f"{prefix}+{driver}://{user}:{password}"
        f"@{host}:{port}/{database}"
    )


# Les valeurs par defaut sont conservees pour le TP.
# Elles peuvent etre remplacees sans modifier ce fichier :
# export DB_PASSWORD=...
DB_POSTGRES_SOURCE = database_url(
    "postgresql",
    os.getenv("PG_SOURCE_HOST", "localhost"),
    os.getenv("PG_SOURCE_PORT", "5432"),
    os.getenv("PG_SOURCE_DB", "tp_assurance_auto"),
    os.getenv("PG_USER", "postgres"),
    os.getenv("PG_PASSWORD", "hatif"),
    "psycopg2",
)

DB_MYSQL_SOURCE = database_url(
    "mysql",
    os.getenv("MYSQL_SOURCE_HOST", "localhost"),
    os.getenv("MYSQL_SOURCE_PORT", "3306"),
    os.getenv("MYSQL_SOURCE_DB", "tp_assurance_life"),
    os.getenv("MYSQL_USER", "root"),
    os.getenv("MYSQL_PASSWORD", "hatif"),
    "pymysql",
)

DB_POSTGRES_DESTINATION = database_url(
    "postgresql",
    os.getenv("PG_DEST_HOST", "localhost"),
    os.getenv("PG_DEST_PORT", "5432"),
    os.getenv("PG_DEST_DB", "netoyage"),
    os.getenv("PG_USER", "postgres"),
    os.getenv("PG_PASSWORD", "hatif"),
    "psycopg2",
)

# Chemin stable quel que soit le dossier depuis lequel le script est lance.
CSV_PATH = str(PROJECT_DIR / "data" / "clients_autre_leger.csv")
