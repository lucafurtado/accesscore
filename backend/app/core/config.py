from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env.

    Values are resolved from process environment variables first, falling
    back to the .env file. Required fields have no default and must be
    supplied explicitly.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "AccessCore"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    database_url: str
    database_pool_size: int = 5
    database_max_overflow: int = 10

    redis_url: str

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    cors_origins: list[str] = ["http://localhost:3000"]
    bcrypt_rounds: int = 12


settings = Settings()
