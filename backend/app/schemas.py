from datetime import datetime
from typing import Literal, Any
from pydantic import BaseModel, Field, ConfigDict

HazardType = Literal["flood", "fire", "blockage", "other"]

class Coordinates(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)

class RouteRequest(BaseModel):
    start: Coordinates
    end: Coordinates

class HazardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    type: str
    title: str
    description: str
    lat: float
    lng: float
    radius_m: float
    source: str
    severity: int
    confidence: float
    admin_rating: int | None
    verified: bool
    admin_status: str
    created_at: datetime
    updated_at: datetime
    expires_at: datetime | None
    final_score: float = 0
    treatment: str = "flagged"

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class RateRequest(BaseModel):
    rating: int = Field(ge=1, le=5)

class ConfirmRequest(BaseModel):
    status: Literal["confirmed", "dismissed"]

class VerifyRequest(Coordinates):
    type: HazardType
    title: str = Field(min_length=2, max_length=240)
    description: str = ""
    radius_m: float = Field(default=200, gt=0, le=10000)
    notes: str = ""
    who_was_called: str = ""
    rating: int = Field(ge=1, le=5)

class SettingsUpdate(BaseModel):
    values: dict[str, Any]

class RefreshResponse(BaseModel):
    message: str
    imported: int
    errors: list[str] = []
