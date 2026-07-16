from collections.abc import Generator
from os import environ

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from starlette.testclient import TestClient


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


@pytest.fixture
def api_client(db_session: Session) -> Generator[TestClient]:
    from app.core.config import Settings
    from app.db.seed import seed_session
    from app.db.session import get_db_session
    from app.main import create_app

    seed_session(db_session)
    settings = Settings(
        database_url=environ["DATABASE_URL"],
        app_env="test",
        demo_mode=True,
        cors_allowed_origins="http://localhost:5173",
        ttn_webhook_enabled=False,
        ttn_webhook_secret="integration-test-webhook-secret",
        webhook_body_limit_bytes=1_024,
    )
    application = create_app(settings)

    def override_session() -> Generator[Session]:
        yield db_session

    application.dependency_overrides[get_db_session] = override_session
    with TestClient(application, raise_server_exceptions=False) as client:
        yield client
