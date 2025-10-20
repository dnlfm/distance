from math import radians, sin, cos, asin, sqrt
from typing import Optional, Dict, Any
import httpx


"""Distance utilities.

Provides a pure-Python Haversine implementation and an optional geodesic
backend powered by geopy (if installed). Additionally provides an OSRM-based
routing distance (uses either public router.project-osrm.org or a configured
OSRM service). Exported helpers:
- haversine_distance: always-available Haversine in kilometers
- geodesic_distance: optional geopy-based geodesic
- osrm_route_distance: async call to an OSRM service returning distance and duration
- fallback and helpers

- distance
"""

try:
    # Optional, used only if available
    from geopy.distance import geodesic as _geopy_geodesic  # type: ignore
    GEOPY_AVAILABLE = True
except Exception:
    _geopy_geodesic = None
    GEOPY_AVAILABLE = False


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute Haversine distance (in kilometers) between two WGS84 coordinates. - haversine

    All inputs are decimal degrees.
    """
    # convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    r = 6371.0  # Radius of earth in kilometers
    return c * r


def geodesic_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute geodesic distance (in kilometers) using geopy if available.

    Raises RuntimeError if geopy is not installed.
    - geodesic
    """
    if not GEOPY_AVAILABLE or _geopy_geodesic is None:
        raise RuntimeError("geopy is not available; install geopy to use geodesic distances")

    # geopy expects (lat, lon) pairs
    d = _geopy_geodesic((lat1, lon1), (lat2, lon2))
    # geopy returns distance object with kilometers attribute
    return float(d.kilometers)


async def osrm_route_distance(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
    client: httpx.AsyncClient,
    settings: Any,
) -> Dict[str, Optional[float]]:
    """Query OSRM route API to obtain routing distance and duration.

    Returns a dict with keys: distance_km (float), duration_seconds (float), method (str).
    If an error occurs an exception is raised so callers can fallback to haversine.

    Use settings.use_osrm_online to decide between public OSRM and configured OSRM service URL.
    """
    if settings.use_osrm_online:
        base_url = "https://router.project-osrm.org"
    else:
        base_url = settings.osrm_service_url.rstrip("/")

    profile = getattr(settings, "osrm_profile", "car")

    # OSRM expects lon,lat pairs
    coords = f"{lon1},{lat1};{lon2},{lat2}"
    url = f"{base_url}/route/v1/{profile}/{coords}?overview=false&alternatives=false&steps=false"

    headers = {"User-Agent": getattr(settings, "user_agent", "distance-finder/1.0")}

    try:
        resp = await client.get(url, headers=headers)
    except Exception as exc:
        raise RuntimeError(f"OSRM request failed: {exc}") from exc

    if resp.status_code != 200:
        raise RuntimeError(f"OSRM returned status {resp.status_code}")

    data = resp.json()
    if not data or data.get("code") != "Ok":
        # Some OSRM instances might return different keys; be defensive
        raise RuntimeError(f"OSRM response error: {data}")

    routes = data.get("routes")
    if not routes:
        raise RuntimeError("OSRM returned no routes")

    route = routes[0]
    distance_m = route.get("distance")
    duration_s = route.get("duration")

    distance_km = None
    if distance_m is not None:
        try:
            distance_km = float(distance_m) / 1000.0
        except Exception:
            distance_km = None

    duration_seconds = None
    if duration_s is not None:
        try:
            duration_seconds = float(duration_s)
        except Exception:
            duration_seconds = None

    return {"distance_km": distance_km, "duration_seconds": duration_seconds, "method": "osrm"}


async def distance_via_best_method(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
    client: Optional[httpx.AsyncClient],
    settings: Any,
) -> Dict[str, Optional[float]]:
    """Try OSRM first (if client provided), fallback to geodesic/geographic haversine.

    Returns dict with distance_km, duration_seconds, method.
    """
    # Try OSRM if we have an HTTP client and settings allow it
    if client is not None:
        try:
            result = await osrm_route_distance(lat1, lon1, lat2, lon2, client, settings)
            # If OSRM returned a valid distance, prefer it
            if result.get("distance_km") is not None:
                return result
        except Exception:
            # swallow and fallback
            pass

    # Try geodesic if available
    try:
        d_km = geodesic_distance(lat1, lon1, lat2, lon2)
        return {"distance_km": d_km, "duration_seconds": None, "method": "geodesic"}
    except Exception:
        # fallback to haversine
        d_km = haversine_distance(lat1, lon1, lat2, lon2)
        return {"distance_km": d_km, "duration_seconds": None, "method": "haversine"}
