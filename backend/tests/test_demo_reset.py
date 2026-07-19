import pytest
from app.core.config import Settings
from app.db.reset_demo import DemoResetRefused, validate_reset_environment


def settings(*, app_env: str = "development", demo_mode: bool = True) -> Settings:
    return Settings(
        database_url="postgresql+psycopg://example:example@db/example",
        app_env=app_env,
        demo_mode=demo_mode,
    )


def test_demo_reset_requires_explicit_confirmation() -> None:
    with pytest.raises(DemoResetRefused, match="--confirm-reset"):
        validate_reset_environment(settings(), confirmed=False)


@pytest.mark.parametrize(
    "configured",
    (settings(app_env="production"), settings(demo_mode=False)),
)
def test_demo_reset_refuses_non_demo_or_production(configured: Settings) -> None:
    with pytest.raises(DemoResetRefused, match="development or test demo mode"):
        validate_reset_environment(configured, confirmed=True)
