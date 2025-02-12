from sqlalchemy import inspect
from sqlalchemy_utils import database_exists, create_database
from database import DATABASE_URL, engine
from routers import (
    models
)


def check_tables():
    """
    Check if required tables exist in the database.

    :return: None
    """
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    required_tables = {"trips", "trip_days", "activities"}
    missing_tables = required_tables - set(tables)

    if missing_tables:
        print(f"Missing tables: {missing_tables}")
    else:
        print("All required tables exist.")


def setup_database():
    """
    Set up the database by creating it if it does not exist and creating tables if they do not exist.

    :return: None
    """
    # Check if the database exists, create it if not
    if not database_exists(DATABASE_URL):
        print("Database does not exist. Creating database...")
        create_database(DATABASE_URL)
        print("Database created successfully!")
    else:
        print("Database already exists.")

    # Create tables if they do not exist
    print("Checking and creating tables...")
    models.Base.metadata.create_all(bind=engine)
    check_tables()


if __name__ == "__main__":
    setup_database()
