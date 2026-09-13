import os

from sqlalchemy import create_engine, URL


DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "geoasset"
DB_USER = "postgres"


def get_engine():
    """
    Create a SQLAlchemy connection to PostgreSQL/PostGIS.

    The database password is read from the
    GEOASSET_DB_PASSWORD environment variable
    instead of being stored in source code.
    """

    password = os.getenv("GEOASSET_DB_PASSWORD")

    if not password:
        raise RuntimeError(
            "GEOASSET_DB_PASSWORD environment variable is not set."
        )

    database_url = URL.create(
        "postgresql+psycopg",
        username=DB_USER,
        password=password,
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME
    )

    return create_engine(
        database_url,
        pool_pre_ping=True
    )