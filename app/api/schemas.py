from typing import Optional, List
from pydantic import BaseModel


"""Pydantic schemas for request/response models. - schemas"""


class Location(BaseModel):
    """Represent an origin or destination location. - location"""
    lat: Optional[float] = None
    lon: Optional[float] = None
    address: Optional[str] = None


class Destination(BaseModel):
    """Destination data. - destination"""
    name: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    address: Optional[str] = None


class DistanceRequest(BaseModel):
    """Request body for distance computations. - distance_request"""
    origin: Location
    destinations: List[Destination]


class DistanceResult(BaseModel):
    """Single result item with computed distance. - distance_result"""
    name: Optional[str]
    lat: float
    lon: float
    distance_km: float


# --- New schemas for geocoding and address-only distance endpoint ---


class GeocodeRequest(BaseModel):
    """Request to geocode a single address. - geocode_request"""
    address: str


class GeocodeResult(BaseModel):
    """Response containing lat/lon for an address. - geocode_result"""
    lat: float
    lon: float


class AddressDestination(BaseModel):
    """Destination specified only by name and address (no lat/lon). - address_destination"""
    name: Optional[str] = None
    address: str


class AddressDistanceRequest(BaseModel):
    """Request that provides origin address and a list of destinations by address. - address_distance_request"""
    origin_address: str
    destinations: List[AddressDestination]
