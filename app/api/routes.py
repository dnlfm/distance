from typing import List, Tuple, Any
from fastapi import APIRouter, HTTPException, Depends
import httpx

from app.api import schemas
from app.core.config import Settings, get_settings
from app.services.geocode import geocode_address, geocode_best_effort
from app.services.distance import haversine_distance, distance_via_best_method


"""API routes for distance computations. - api, routes"""

router = APIRouter()


async def _resolve_latlon(item: Any, client: httpx.AsyncClient, settings: Settings) -> Tuple[float, float]:
    """Resolve a lat/lon pair from either an object with lat/lon/address or a plain address string. - helper

    Accepts:
    - a string (treated as an address)
    - a pydantic model/object with attributes 'lat', 'lon', and/or 'address'

    Returns (lat, lon) or raises HTTPException for validation/geocoding errors.
    """
    # If a plain string is provided, treat it as an address
    if isinstance(item, str):
        address = item.strip()
        if not address:
            raise HTTPException(status_code=422, detail="Address must be provided")
        try:
            return await geocode_address(address, client, settings)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Otherwise, duck-type the object for lat/lon/address attributes
    lat = getattr(item, "lat", None)
    lon = getattr(item, "lon", None)
    address = getattr(item, "address", None)

    if lat is not None and lon is not None:
        return lat, lon

    if address:
        try:
            return await geocode_address(address, client, settings)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    raise HTTPException(status_code=422, detail="Location must have lat/lon or address")


@router.post("/distance", response_model=List[schemas.DistanceResult])
async def compute_distances(
    req: schemas.DistanceRequest,
    settings: Settings = Depends(get_settings),
):
    """Compute distances from origin to provided destinations and return them ordered by distance. - compute, distances"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Resolve origin
        origin_lat, origin_lon = await _resolve_latlon(req.origin, client, settings)

        results: List[schemas.DistanceResult] = []

        for dest in req.destinations:
            lat, lon = await _resolve_latlon(dest, client, settings)

            # Try routing-based distance first (OSRM -> geodesic -> haversine)
            dist_info = await distance_via_best_method(origin_lat, origin_lon, lat, lon, client, settings)

            dist_km = dist_info.get("distance_km") or 0.0
            duration = dist_info.get("duration_seconds")
            method = dist_info.get("method")

            results.append(
                schemas.DistanceResult(
                    name=dest.name or dest.address or "",
                    lat=lat,
                    lon=lon,
                    distance_km=dist_km,
                    duration_seconds=duration,
                    distance_method=method,
                )
            )

        # sort by distance asc
        results.sort(key=lambda r: r.distance_km)
        return results


@router.post("/geocode", response_model=schemas.GeocodeResult)
async def geocode_single(
    req: schemas.GeocodeRequest,
    settings: Settings = Depends(get_settings),
):
    """Geocode a single address and return its latitude and longitude. - geocode_single"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            lat, lon = await geocode_address(req.address, client, settings)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return schemas.GeocodeResult(lat=lat, lon=lon)


@router.post("/geocode/parts", response_model=schemas.GeocodeResult)
async def geocode_parts(
    req: schemas.PartsGeocodeRequest,
    settings: Settings = Depends(get_settings),
):
    """Geocode using best-effort ordered parts, most specific to most generic. - geocode_parts"""
    parts = _clean_parts(req.parts)
    if not parts:
        raise HTTPException(status_code=422, detail="parts must contain non-empty strings")

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            lat, lon = await geocode_best_effort(parts, client, settings)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return schemas.GeocodeResult(lat=lat, lon=lon)


@router.post("/geocode/structured", response_model=schemas.GeocodeResult)
async def geocode_structured(
    req: schemas.StructuredLocation,
    settings: Settings = Depends(get_settings),
):
    """Geocode from structured fields (street/neighborhood/city/state) using best-effort. - geocode_structured"""
    parts = _loc_to_parts(req)
    if not parts:
        raise HTTPException(status_code=422, detail="At least one non-empty field must be provided")

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            lat, lon = await geocode_best_effort(parts, client, settings)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return schemas.GeocodeResult(lat=lat, lon=lon)


@router.post("/distance/addresses", response_model=List[schemas.DistanceResult])
async def compute_distances_from_addresses(
    req: schemas.AddressDistanceRequest,
    settings: Settings = Depends(get_settings),
):
    """Shortcut endpoint: accept origin + destinations as addresses only, geocode them and compute distances. - address_shortcut"""
    if not req.origin_address or not req.destinations:
        raise HTTPException(status_code=422, detail="origin_address and destinations are required")

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            origin_lat, origin_lon = await _resolve_latlon(req.origin_address, client, settings)
        except HTTPException:
            raise

        results: List[schemas.DistanceResult] = []
        for dest in req.destinations:
            lat, lon = await _resolve_latlon(dest, client, settings)

            dist_info = await distance_via_best_method(origin_lat, origin_lon, lat, lon, client, settings)
            dist_km = dist_info.get("distance_km") or 0.0
            duration = dist_info.get("duration_seconds")
            method = dist_info.get("method")

            results.append(
                schemas.DistanceResult(
                    name=dest.name or dest.address or "",
                    lat=lat,
                    lon=lon,
                    distance_km=dist_km,
                    duration_seconds=duration,
                    distance_method=method,
                )
            )

        results.sort(key=lambda r: r.distance_km)
        return results


@router.post("/distance/parts", response_model=List[schemas.DistanceResult])
async def compute_distances_from_parts(
    req: schemas.PartsDistanceRequest,
    settings: Settings = Depends(get_settings),
):
    """Compute distances using best-effort geocoding from ordered parts. - distance_parts"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        origin_parts = _clean_parts(req.origin_parts)
        if not origin_parts:
            raise HTTPException(status_code=422, detail="origin_parts must contain non-empty strings")

        try:
            origin_lat, origin_lon = await geocode_best_effort(origin_parts, client, settings)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        results: List[schemas.DistanceResult] = []
        for dest in req.destinations:
            dest_parts = _clean_parts(dest.parts)
            if not dest_parts:
                raise HTTPException(status_code=422, detail="Each destination must include non-empty parts")

            try:
                lat, lon = await geocode_best_effort(dest_parts, client, settings)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

            dist_info = await distance_via_best_method(origin_lat, origin_lon, lat, lon, client, settings)
            dist_km = dist_info.get("distance_km") or 0.0
            duration = dist_info.get("duration_seconds")
            method = dist_info.get("method")

            results.append(
                schemas.DistanceResult(
                    name=dest.name or ", ".join(dest_parts),
                    lat=lat,
                    lon=lon,
                    distance_km=dist_km,
                    duration_seconds=duration,
                    distance_method=method,
                )
            )

        results.sort(key=lambda r: r.distance_km)
        return results


@router.post("/distance/structured", response_model=List[schemas.DistanceResult])
async def compute_distances_structured(
    req: schemas.StructuredDistanceRequest,
    settings: Settings = Depends(get_settings),
):
    """Compute distances from structured address fields using best-effort geocoding. - distance_structured"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        origin_parts = _loc_to_parts(req.origin)
        if not origin_parts:
            raise HTTPException(status_code=422, detail="Origin must include at least one non-empty field")

        try:
            origin_lat, origin_lon = await geocode_best_effort(origin_parts, client, settings)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        results: List[schemas.DistanceResult] = []
        for dest in req.destinations:
            dest_parts = _loc_to_parts(dest)
            if not dest_parts:
                raise HTTPException(status_code=422, detail="Each destination must include at least one non-empty field")

            try:
                lat, lon = await geocode_best_effort(dest_parts, client, settings)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

            dist_info = await distance_via_best_method(origin_lat, origin_lon, lat, lon, client, settings)
            dist_km = dist_info.get("distance_km") or 0.0
            duration = dist_info.get("duration_seconds")
            method = dist_info.get("method")

            results.append(
                schemas.DistanceResult(
                    name=getattr(dest, "name", None) or ", ".join(dest_parts),
                    lat=lat,
                    lon=lon,
                    distance_km=dist_km,
                    duration_seconds=duration,
                    distance_method=method,
                )
            )

        results.sort(key=lambda r: r.distance_km)
        return results

def _clean_parts(parts: List[str]) -> List[str]:
    """Normalize ordered parts by stripping and dropping empties. - clean_parts"""
    return [p.strip() for p in parts if isinstance(p, str) and p.strip()]


def _loc_to_parts(loc: Any) -> List[str]:
    """Extract ordered parts from a structured object. - loc_to_parts"""
    parts = [
        getattr(loc, "street", None),
        getattr(loc, "neighborhood", None),
        getattr(loc, "city", None),
        getattr(loc, "state", None),
    ]
    return [p.strip() for p in parts if isinstance(p, str) and p.strip()]
