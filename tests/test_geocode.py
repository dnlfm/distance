import pytest
import httpx

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app.services.geocode as geocode_module
from app.services.geocode import geocode_address, PUBLIC_NOMINATIM
from app.core.config import get_settings


"""Unit tests for the geocoding service (app.services.geocode).

These tests mock the internal _query_nominatim helper to avoid network I/O and
exercise success, not-found and error pathways.
"""


@pytest.fixture
def settings():
    """Return a Settings instance for tests. - settings"""
    return get_settings()


@pytest.mark.asyncio
async def test_geocode_success(monkeypatch, settings):
    """_geocode_address returns floats when the nominatim helper returns a valid item. - test_geocode_success"""

    async def fake_query(address: str, client: httpx.AsyncClient, url: str, user_agent: str):
        assert isinstance(address, str)
        # Should be called with either primary or public; accept both
        assert url.startswith("http")
        return [{"lat": "-23.55052", "lon": "-46.633308"}]

    monkeypatch.setattr(geocode_module, "_query_nominatim", fake_query)

    async with httpx.AsyncClient() as client:
        lat, lon = await geocode_address("Praça da Sé, São Paulo", client, settings)

    assert pytest.approx(lat, rel=1e-6) == -23.55052
    assert pytest.approx(lon, rel=1e-6) == -46.633308


@pytest.mark.asyncio
async def test_geocode_not_found_raises(monkeypatch, settings):
    """If nominatim returns an empty list for both primary and fallback, ValueError is raised. - test_geocode_not_found_raises"""

    async def fake_query_empty(address: str, client: httpx.AsyncClient, url: str, user_agent: str):
        return []

    monkeypatch.setattr(geocode_module, "_query_nominatim", fake_query_empty)

    async with httpx.AsyncClient() as client:
        with pytest.raises(ValueError):
            await geocode_address("An unknown place that does not exist", client, settings)


@pytest.mark.asyncio
async def test_geocode_invalid_format_raises(monkeypatch, settings):
    """If nominatim returns malformed items, ValueError is raised. - test_geocode_invalid_format_raises"""

    async def fake_query_bad_format(address: str, client: httpx.AsyncClient, url: str, user_agent: str):
        return [{"something": "else"}]

    monkeypatch.setattr(geocode_module, "_query_nominatim", fake_query_bad_format)

    async with httpx.AsyncClient() as client:
        with pytest.raises(ValueError):
            await geocode_address("Praça da Sé, São Paulo", client, settings)


@pytest.mark.asyncio
async def test_geocode_primary_failure_and_fallback(monkeypatch, settings):
    """Simulate primary failing with a RequestError and fallback returning a result. - test_geocode_primary_failure_and_fallback"""
    # Use a non-public primary URL so fallback will be attempted
    settings.nominatim_url = "https://example-nominatim.local"
    primary_url = settings.nominatim_url.rstrip("/")

    async def fake_query(address: str, client: httpx.AsyncClient, url: str, user_agent: str):
        if url.rstrip("/") == primary_url:
            raise httpx.RequestError("connect failure")
        # fallback
        return [{"lat": "-23.55052", "lon": "-46.633308"}]

    monkeypatch.setattr(geocode_module, "_query_nominatim", fake_query)

    async with httpx.AsyncClient() as client:
        lat, lon = await geocode_address("Praça da Sé, São Paulo", client, settings)

    assert pytest.approx(lat, rel=1e-6) == -23.55052
    assert pytest.approx(lon, rel=1e-6) == -46.633308


@pytest.mark.asyncio
async def test_geocode_both_endpoints_fail_raises(monkeypatch, settings):
    """If both primary and fallback raise network errors, ValueError should be raised. - test_geocode_both_endpoints_fail_raises"""

    async def always_fail(address: str, client: httpx.AsyncClient, url: str, user_agent: str):
        raise httpx.RequestError("network down")

    monkeypatch.setattr(geocode_module, "_query_nominatim", always_fail)

    async with httpx.AsyncClient() as client:
        with pytest.raises(ValueError):
            await geocode_address("Praça da Sé, São Paulo", client, settings)
