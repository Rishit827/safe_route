from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    app_name: str = "SafeRoute API"
    environment: str = "development"
    database_url: str = "sqlite:///./saferoute.db"
    cors_origins: str = "http://localhost:3000,http://localhost:3001"
    admin_username: str = "admin"
    admin_password: str = "change-this-password"
    jwt_secret: str = "change-this-secret-before-deployment"
    jwt_expire_minutes: int = 720
    use_mock_data: bool = True
    collection_interval_minutes: int = 10
    region_bbox: str = "72.7,30.5,76.0,32.5"
    region_grid_size: int = 3
    sachet_feed_url: str = ""
    firms_map_key: str = ""
    ors_api_key: str = ""
    ors_base_url: str = "https://api.openrouteservice.org"
    openmeteo_rain_threshold_mm: float = 25.0
    hazard_group_distance_m: float = 1500.0
    route_penalty_weight: float = 0.35
    request_timeout_seconds: float = 12.0
    admin_password_hash: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        parts = [float(x.strip()) for x in self.region_bbox.split(",")]
        if len(parts) != 4:
            raise ValueError("REGION_BBOX must be min_lon,min_lat,max_lon,max_lat")
        return parts[0], parts[1], parts[2], parts[3]

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
