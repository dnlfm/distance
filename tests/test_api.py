import pytest
from httpx import AsyncClient
import httpx
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import app
from app.core.config import get_settings
import app.services.geocode as geocode_module
from app.services.geocode import geocode_address


"""Tests for the distance API and geocoding service.

These tests include fixtures for settings and sample data. They mock the
internal nominatim query helper to avoid real network calls.
- geocode tests mock _query_nominatim
- distance endpoint test mocks geocode_address
"""


@pytest.fixture
def settings():
    """Return a Settings instance for tests. - settings"""
    return get_settings()


@pytest.fixture
def sample_destinations():
    """Sample destinations used across tests. - sample_destinations"""
    return [
        {"name": "Rio", "lat": -22.9068, "lon": -43.1729},
        {"name": "Campinas", "lat": -22.9099, "lon": -47.0626},
        {"name": "Santos", "lat": -23.9608, "lon": -46.3336},
    ]


@pytest.mark.asyncio
async def test_distance_sorting(sample_destinations):
    """Ensure /api/distance sorts results by increasing distance when lat/lon provided. - test_distance_sorting"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        payload = {
            "origin": {"lat": -23.55052, "lon": -46.633308},  # São Paulo
            "destinations": sample_destinations,
        }
        r = await ac.post("/api/distance", json=payload)
        assert r.status_code == 200
        data = r.json()
        distances = [item["distance_km"] for item in data]
        assert distances == sorted(distances)
        assert all("lat" in item and "lon" in item and "name" in item for item in data)


@pytest.mark.asyncio
async def test_geocode_success(monkeypatch, settings):
    """Mock the internal _query_nominatim to return a successful response. - test_geocode_success"""

    async def fake_query(address: str, client: httpx.AsyncClient, url: str, user_agent: str):
        return [{"lat": "-23.55052", "lon": "-46.633308"}]

    monkeypatch.setattr(geocode_module, "_query_nominatim", fake_query)

    async with httpx.AsyncClient() as client:
        lat, lon = await geocode_address("Praça da Sé, São Paulo", client, settings)
    assert pytest.approx(lat, rel=1e-6) == -23.55052
    assert pytest.approx(lon, rel=1e-6) == -46.633308


@pytest.mark.asyncio
async def test_geocode_fallback(monkeypatch, settings):
    """Simulate primary nominatim failing and public fallback succeeding. - test_geocode_fallback"""
    # Use a non-public primary URL so the code will attempt fallback
    settings.nominatim_url = "https://example-nominatim.local"
    primary_url = settings.nominatim_url.rstrip("/")

    async def fake_query(address: str, client: httpx.AsyncClient, url: str, user_agent: str):
        # If called with primary, simulate network error
        if url.rstrip("/") == primary_url:
            raise httpx.RequestError("connect failure")
        # Otherwise return a valid response
        return [{"lat": "-23.55052", "lon": "-46.633308"}]

    monkeypatch.setattr(geocode_module, "_query_nominatim", fake_query)

    async with httpx.AsyncClient() as client:
        lat, lon = await geocode_address("Praça da Sé, São Paulo", client, settings)
    assert pytest.approx(lat, rel=1e-6) == -23.55052
    assert pytest.approx(lon, rel=1e-6) == -46.633308


@pytest.mark.asyncio
async def test_distance_with_address_origin(monkeypatch, sample_destinations):
    """Test the /api/distance endpoint when origin is provided as an address string by mocking geocode_address. - test_distance_with_address_origin"""
    # Mock geocode_address to return São Paulo coordinates
    async def fake_geocode(address: str, client: httpx.AsyncClient, settings):
        return -23.55052, -46.633308

    monkeypatch.setattr(geocode_module, "geocode_address", fake_geocode)

    async with AsyncClient(app=app, base_url="http://test") as ac:
        payload = {
            "origin": {"address": "Praça da Sé, São Paulo"},
            "destinations": sample_destinations,
        }
        r = await ac.post("/api/distance", json=payload)
        assert r.status_code == 200
        data = r.json()
        distances = [item["distance_km"] for item in data]
        assert distances == sorted(distances)
        assert all("lat" in item and "lon" in item and "name" in item for item in data)


# Additional API edge-case tests
@pytest.mark.asyncio
async def test_missing_origin_fields_returns_422(sample_destinations):
    """Origin without lat/lon or address should return a 422. - test_missing_origin_fields_returns_422"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        payload = {"origin": {}, "destinations": sample_destinations}
        r = await ac.post("/api/distance", json=payload)
        assert r.status_code == 422


@pytest.mark.asyncio
async def test_missing_destination_fields_returns_422():
    """A destination without lat/lon or address should return a 422. - test_missing_destination_fields_returns_422"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        payload = {
            "origin": {"lat": -23.55052, "lon": -46.633308},
            "destinations": [{"name": "Nowhere"}],
        }
        r = await ac.post("/api/distance", json=payload)
        assert r.status_code == 422
