from typing import Tuple, List
import httpx

from app.core.config import Settings


"""Simple geocoding service that queries a Nominatim-compatible endpoint.

This module will try the configured Nominatim URL and fall back to the public
nominatim.openstreetmap.org service if the primary endpoint fails or returns
no results.
- geocode
"""

# Module-level public fallback constant (tests import this)
PUBLIC_NOMINATIM = "https://nominatim.openstreetmap.org"


async def _query_nominatim(address: str, client: httpx.AsyncClient, url: str, user_agent: str):
    """Internal helper to query a Nominatim /search endpoint. - helper"""
    params = {"q": address, "format": "json", "limit": 1}
    headers = {"User-Agent": user_agent}
    resp = await client.get(url.rstrip("/") + "/search", params=params, headers=headers)
    resp.raise_for_status()
    # httpx.Response.json() is synchronous but safe to call here
    return resp.json()


async def geocode_address(address: str, client: httpx.AsyncClient, settings: Settings) -> Tuple[float, float]:
    """Geocode an address string using the configured Nominatim endpoint.

    Tries settings.nominatim_url first (if set). If settings.nominatim_url is
    empty and settings.run_local is True, the local container URL
    (http://nominatim:8080) will be used as the primary endpoint. On
    network/error or empty result, will attempt the public
    settings.public_nominatim_url (or the module-level PUBLIC_NOMINATIM) as a fallback.

    Returns (lat, lon) as floats. Raises ValueError if not found or both
    endpoints fail.
    - geocode_address
    """
    public_url = settings.public_nominatim_url or PUBLIC_NOMINATIM

    # Determine primary url: prefer explicitly configured settings.nominatim_url,
    # otherwise if run_local is True use the typical nominatim container URL,
    # otherwise fall back to the public service.
    if settings.nominatim_url:
        primary_url = settings.nominatim_url.rstrip("/")
    elif settings.run_local:
        primary_url = "http://nominatim:8080"
    else:
        primary_url = public_url.rstrip("/")

    tried_public = primary_url.rstrip("/") == public_url.rstrip("/")

    # Try primary endpoint
    try:
        data = await _query_nominatim(address, client, primary_url, settings.user_agent)
    except httpx.RequestError as exc:
        # network-level error, try public fallback if available
        if tried_public:
            raise ValueError(f"Geocoding request failed for address '{address}': {exc}") from exc
        try:
            data = await _query_nominatim(address, client, public_url, settings.user_agent)
        except Exception as exc2:
            raise ValueError(f"Geocoding failed for address '{address}': primary error {exc}; fallback error {exc2}") from exc2
    except httpx.HTTPStatusError as exc:
        # server returned non-2xx, try fallback if not already public
        if tried_public:
            raise ValueError(f"Geocoding HTTP error for address '{address}': {exc}") from exc
        try:
            data = await _query_nominatim(address, client, public_url, settings.user_agent)
        except Exception as exc2:
            raise ValueError(f"Geocoding failed for address '{address}': primary HTTP error {exc}; fallback error {exc2}") from exc2

    # If primary returned but no results, attempt fallback (if applicable)
    if not data:
        if tried_public:
            raise ValueError(f"Address not found: {address}")
        try:
            data = await _query_nominatim(address, client, public_url, settings.user_agent)
        except Exception as exc:
            raise ValueError(f"Address not found and fallback failed for: {address}. Error: {exc}") from exc
        if not data:
            raise ValueError(f"Address not found: {address}")

    item = data[0]
    try:
        lat = float(item["lat"])
        lon = float(item["lon"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"Unexpected geocoding response format for address '{address}': {item}") from exc

    return lat, lon

async def geocode_best_effort(parts: List[str], client: httpx.AsyncClient, settings: Settings) -> Tuple[float, float]:
    """Best-effort geocoding by progressively dropping most specific parts. - geocode_best_effort

    Accepts parts ordered from most specific to most generic. Tries the full
    joined address first, then iteratively removes the first element until a
    result is found or none remain.
    """
    if not parts:
        raise ValueError("No address parts provided")

    cleaned = [p.strip() for p in parts if isinstance(p, str) and p.strip()]
    if not cleaned:
        raise ValueError("No valid address parts provided")

    for i in range(0, len(cleaned)):
        candidate = ", ".join(cleaned[i:])
        try:
            return await geocode_address(candidate, client, settings)
        except ValueError:
            continue

    raise ValueError(f"Address not found from provided parts: {cleaned}")
