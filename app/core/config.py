from pydantic import BaseSettings


"""Configuration settings using pydantic BaseSettings. - config"""


class Settings(BaseSettings):
    """Application settings.

    - Reads configuration from environment variables and a local .env file
    - Fields: nominatim_url, user_agent, database_url, run_local, public_nominatim_url
    """
    # Primary Nominatim-compatible endpoint (can be a local nominatim container)
    nominatim_url: str = ""

    # HTTP User-Agent sent to Nominatim servers (required by their usage policy)
    user_agent: str = "distance-finder/1.0"

    # Database connection string used by the app (can be overridden via env)
    database_url: str = "postgresql://nominatim:nominatim@postgres:5432/nominatim"

    # When running locally via docker-compose this flag can be set to true
    # to prefer the local nominatim container if nominatim_url is not provided.
    run_local: bool = False

    # Public Nominatim endpoint used as a fallback when a private/primary endpoint fails
    public_nominatim_url: str = "https://nominatim.openstreetmap.org"

    class Config:
        """Pydantic config: load environment from a .env file by default. - config"""
        env_file = ".env"
        env_file_encoding = "utf-8"


def get_settings() -> Settings:
    """Return a Settings instance for dependency injection. - get_settings"""
    return Settings()
