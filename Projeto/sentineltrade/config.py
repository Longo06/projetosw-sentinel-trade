import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

# Valores de exemplo/padrão que nunca podem ser usados fora do ambiente de desenvolvimento.
_INSECURE_SECRETS = {"", "dev-only-change-this-secret", "change-this-to-a-long-random-secret"}


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./sentineltrade.db")
    secret_key: str = os.getenv("SECRET_KEY", "dev-only-change-this-secret")
    app_env: str = os.getenv("APP_ENV", "development")
    mfa_ttl_seconds: int = 300
    session_ttl_seconds: int = 8 * 60 * 60
    quote_max_age_seconds: int = 10
    quote_timeout_seconds: int = 3
    broker_timeout_seconds: int = 5
    max_retries: int = 3
    trading_timezone: str = "America/Sao_Paulo"


def validate_settings(current: Settings) -> None:
    """Impede subir a aplicação fora de desenvolvimento com chave de assinatura fraca."""
    if current.app_env != "development":
        if current.secret_key in _INSECURE_SECRETS or len(current.secret_key) < 32:
            raise RuntimeError(
                "SECRET_KEY insegura. Defina uma chave aleatória com pelo menos 32 caracteres "
                "(ex.: python -c \"import secrets; print(secrets.token_urlsafe(48))\") "
                "quando APP_ENV != development."
            )


settings = Settings()
validate_settings(settings)
