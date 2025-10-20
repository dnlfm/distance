from math import radians, sin, cos, asin, sqrt
from typing import Optional


"""Distance utilities.

Provides a pure-Python Haversine implementation and an optional geodesic
backend powered by geopy (if installed). Exported helpers are:
- haversine_distance: always-available Haversine in kilometers
- distance_between: convenience wrapper that can use 'haversine' or 'geodesic'

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


def distance_between(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
    method: Optional[str] = "haversine",
) -> float:
    """Compute distance between two points in kilometers using chosen method.

    method: 'haversine' (default) or 'geodesic'. If 'geodesic' is requested but
    geopy is not installed, a RuntimeError is raised.
    - distance_between
    """
    method = (method or "haversine").lower()
    if method == "haversine":
        return haversine_distance(lat1, lon1, lat2, lon2)
    if method == "geodesic":
        return geodesic_distance(lat1, lon1, lat2, lon2)
    raise ValueError(f"Unknown distance method: {method}")
