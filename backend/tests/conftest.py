from collections.abc import Generator
from os import environ

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session


@pytest.fixture
def db_session() -> Generator[Session]:
    database_url = environ.get("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL is not configured for PostgreSQL integration tests")

    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        connection = engine.connect()
    except OperationalError:
        pytest.skip("PostgreSQL integration database is not reachable")

    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
        engine.dispose()
