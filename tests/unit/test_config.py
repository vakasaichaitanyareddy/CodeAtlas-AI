import pytest
from apps.api.app.config import Settings


def test_settings_defaults():
    settings = Settings()
    assert settings.ENVIRONMENT is not None
    assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 30
    assert settings.REFRESH_TOKEN_EXPIRE_DAYS == 7
    assert settings.JWT_ALGORITHM == "HS256"


def test_cors_origins_parsing():
    settings = Settings(ALLOWED_ORIGINS="http://localhost:3000, https://codeatlas.dev")
    assert "http://localhost:3000" in settings.ALLOWED_ORIGINS
    assert "https://codeatlas.dev" in settings.ALLOWED_ORIGINS


def test_production_security_enforcement():
    # Production with default secret must be rejected
    with pytest.raises(ValueError, match="SECRET_KEY"):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="codeatlas-insecure-secret-key-change-in-production-min-32-chars"
        ).validate_production_security()

    # Production with wildcard CORS must be rejected
    with pytest.raises(ValueError, match="ALLOWED_ORIGINS"):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="a" * 32,
            ALLOWED_ORIGINS="*",
        ).validate_production_security()

    # Valid production settings pass
    valid = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="super-secure-production-secret-key-atlas-32",
        ALLOWED_ORIGINS="https://app.codeatlas.dev",
    ).validate_production_security()
    assert valid.ENVIRONMENT == "production"
