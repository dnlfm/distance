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
    # Optional estimated travel duration in seconds (when routing/OSRM is used)
    duration_seconds: Optional[float] = None
    # Method used to compute distance: 'osrm', 'geodesic', 'haversine', etc.
    distance_method: Optional[str] = None


# --- New schemas for geocoding and address-only distance endpoint ---


class GeocodeRequest(BaseModel):
    """Request to geocode a single address. - geocode_request"""
    address: str


class GeocodeResult(BaseModel):
    """Response containing lat/lon for an address. - geocode_result"""
    lat: float
    lon: float



class PartsGeocodeRequest(BaseModel):
    """Request to geocode using ordered parts. - parts_geocode_request"""
    parts: List[str]

class AddressDestination(BaseModel):
    """Destination specified only by name and address (no lat/lon). - address_destination"""
    name: Optional[str] = None
    address: str


class AddressDistanceRequest(BaseModel):
    """Request that provides origin address and a list of destinations by address. - address_distance_request"""
    origin_address: str
    destinations: List[AddressDestination]

# --- Best-effort parts-based schemas ---


class PartsDestination(BaseModel):
    """Destination using ordered address parts. - parts_destination"""
    name: Optional[str] = None
    parts: List[str]


class PartsDistanceRequest(BaseModel):
    """Distance request using origin parts and destination parts. - parts_distance_request"""
    origin_parts: List[str]
    destinations: List[PartsDestination]


# --- Structured address schemas (street/neighborhood/city/state) ---


class StructuredLocation(BaseModel):
    """Structured address fields for flexible geocoding. - structured_location"""
    street: Optional[str] = None
    neighborhood: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None


class StructuredDestination(BaseModel):
    """Structured destination with optional name. - structured_destination"""
    name: Optional[str] = None
    street: Optional[str] = None
    neighborhood: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None


class StructuredDistanceRequest(BaseModel):
    """Request using structured origin and destinations. - structured_distance_request"""
    origin: StructuredLocation
    destinations: List[StructuredDestination]
