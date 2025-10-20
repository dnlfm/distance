from pydantic import BaseSettings


"""Configuration settings using pydantic BaseSettings. - config"""


class Settings(BaseSettings):
    """Application settings.

    - Reads configuration from environment variables and a local .env file
    - Fields: nominatim_url, user_agent, database_url, run_local, public_nominatim_url
      plus OSRM related configuration: use_osrm_online, osrm_service_url, osrm_profile
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

    # OSRM configuration
    # If true, use the public router.project-osrm.org service (no local container required)
    # Set the environment variable USE_OSRM_ONLINE to control this behaviour.
    use_osrm_online: bool = True

    # When use_osrm_online is false, the service will call this URL. Set via OSRM_SERVICE_URL.
    osrm_service_url: str = "http://osrm:5000"

    # OSRM profile to use: driving, walking, cycling
    osrm_profile: str = "car"

    class Config:
        """Pydantic config: load environment from a .env file by default. - config"""
        env_file = ".env"
        env_file_encoding = "utf-8"


def get_settings() -> Settings:
    """Return a Settings instance for dependency injection. - get_settings"""
    return Settings()
