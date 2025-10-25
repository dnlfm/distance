# Distance Finder

A FastAPI service that geocodes an origin and computes distances to multiple destinations, returning results sorted by ascending distance. It uses a Nominatim-compatible service for geocoding and OSRM for routing (with geodesic/haversine fallbacks).

Requirements
- Docker and docker-compose
- Optional for local dev: Python 3.11+, pip

Quick links
- [Quick Start](#quick-start)
- [API](#api)
  - [/api/distance](#1-post-apidistance)
  - [/api/geocode](#2-post-apigeocode)
  - [/api/distance/addresses](#3-post-apidistanceaddresses)
  - [/api/distance/parts](#4-post-apidistanceparts)
  - [/api/distance/structured](#5-post-apidistancestructured)
  - [/api/geocode/parts](#6-post-apigeocodeparts)
  - [/api/geocode/structured](#7-post-apigeocodestructured)
- [Environment variables](#environment-variables-env-recommended)
- [Run with docker-compose](#run-with-docker-compose)
- [Local Nominatim notes (optional)](#local-nominatim-notes-optional)
- [Running tests](#running-tests)
- [Troubleshooting](#troubleshooting)
- [License](#license)


Quick Start
-----------

1) Prepare local Nominatim data folder (optional, only if you plan to run a local Nominatim service):

   The repository includes a Makefile target that creates a folder for Nominatim data and will also copy .env.example to .env if present. Run:

   ```sh
   make setup
   ```

   If you plan to import your own OSM extract, place the .osm.pbf file under ./nominatim_data.

2) Run the full stack (app + local Nominatim + OSRM):

   ```sh
   docker-compose up --build
   ```

   Notes:
   - When using a local OSRM dataset, the preprocessing step can take some time before routing becomes available, 45+ minutes for southeast part of Brazil.
   - You can also run just the app and use public Nominatim/OSRM — see [Environment variables](#environment-variables-env-recommended).


API
---

All endpoints return destinations sorted by ascending distance.

#### 1) POST /api/distance

**About**: Returns the distance between one origin and multiple destinations. You may provide lat/lon or address for both origin and destinations.

Example (address origin, destinations by lat/lon):

```bash
curl -s -X POST "http://localhost:80/api/distance" -H "Content-Type: application/json" -d '
{
  "origin": {"address": "Praça da Sé, São Paulo"},
  "destinations": [
    {"name": "Rio", "lat": -22.9068, "lon": -43.1729},
    {"name": "Campinas", "lat": -22.9099, "lon": -47.0626}
  ]
}' | jq
```

**Response**:

```json
[
  {
    "name": "Campinas",
    "lat": -22.9099,
    "lon": -47.0626,
    "distance_km": 93.5963,
    "duration_seconds": 4576.7,
    "distance_method": "osrm"
  },
  {
    "name": "Rio",
    "lat": -22.9068,
    "lon": -43.1729,
    "distance_km": 433.6192,
    "duration_seconds": 20070.9,
    "distance_method": "osrm"
  }
]
```

#### 2) POST /api/geocode

**About**: Geocode a single address and return lat/lon. Useful to persist geocoding in your own DB.

```bash
curl -s -X POST "http://localhost:80/api/geocode" \
  -H "Content-Type: application/json" \
  -d '{"address":"Praça da Sé, São Paulo"}' | jq
```

**Response**:

```json
{
  "lat": -23.5503898,
  "lon": -46.633081
}
```

#### 3) POST /api/distance/addresses

**About**: Convenience endpoint that accepts only addresses. The service geocodes origin and destinations, then computes distances.

```bash
curl -s -X POST "http://localhost:80/api/distance/addresses" \
  -H "Content-Type: application/json" \
  -d '{
    "origin_address": "Praça da Sé, São Paulo",
    "destinations": [
      {"name": "Rio", "address": "Praça Mauá, Rio de Janeiro"},
      {"name": "Campinas", "address": "Praça Rui Barbosa, Campinas"}
    ]
  }' | jq
```

**Response**:

```json
[
  {
    "name": "Campinas",
    "lat": -22.9099,
    "lon": -47.0626,
    "distance_km": 93.5963,
    "duration_seconds": 4576.7,
    "distance_method": "osrm"
  },
  {
    "name": "Rio",
    "lat": -22.9068,
    "lon": -43.1729,
    "distance_km": 433.6192,
    "duration_seconds": 20070.9,
    "distance_method": "osrm"
  }
]
```

#### 4) POST /api/distance/parts

**About**: Best-effort geocoding from an ordered list of strings, from most specific to most generic. If geocoding fails with all parts, the service progressively drops the earliest parts until a match is found.

- Request schema:
  - origin_parts: [string, ...]
  - destinations: [{ name?, parts: [string, ...] }, ...]

Example:

```bash
curl -s -X POST "http://localhost:80/api/distance/parts" \
  -H "Content-Type: application/json" \
  -d '{
    "origin_parts": [
      "Rua da Bahia 1000",
      "Funcionários",
      "Belo Horizonte",
      "MG"
    ],
    "destinations": [
      {
        "name": "Praça Sete",
        "parts": ["Praça Sete de Setembro", "Centro", "Belo Horizonte", "MG"]
      },
      {
        "name": "Pampulha",
        "parts": ["Av. Otacílio Negrão de Lima", "Pampulha", "Belo Horizonte", "MG"]
      }
    ]
  }' | jq
```

**Response**:

```json
[
  {
    "name": "Praça Sete",
    "lat": -19.9191023,
    "lon": -43.9385851,
    "distance_km": 2.9329,
    "duration_seconds": 283.7,
    "distance_method": "osrm"
  },
  {
    "name": "Pampulha",
    "lat": -19.8589878,
    "lon": -43.9818625,
    "distance_km": 12.4155,
    "duration_seconds": 1032.9,
    "distance_method": "osrm"
  }
]
```

Notes:
- Provide parts in decreasing specificity order. The service falls back by trimming from the front: [street, neighborhood, city, state] → [neighborhood, city, state] → [city, state] → [state].

#### 5) POST /api/distance/structured

**About**: Structured convenience endpoint. Provide street, neighborhood, city, and state. Internally it converts to ordered parts and applies the same best-effort geocoding as /distance/parts.

- Request schema:
  - origin: { street?, neighborhood?, city?, state? }
  - destinations: [{ name?, street?, neighborhood?, city?, state? }, ...]

Example:

```bash
curl -s -X POST "http://localhost:80/api/distance/structured" \
  -H "Content-Type: application/json" \
  -d '{
    "origin": {
      "street": "Rua da Bahia 1000",
      "neighborhood": "Funcionários",
      "city": "Belo Horizonte",
      "state": "MG"
    },
    "destinations": [
      {
        "name": "Praça Sete",
        "street": "Praça Sete de Setembro",
        "neighborhood": "Centro",
        "city": "Belo Horizonte",
        "state": "MG"
      },
      {
        "name": "Pampulha",
        "street": "Av. Otacílio Negrão de Lima",
        "neighborhood": "Pampulha",
        "city": "Belo Horizonte",
        "state": "MG"
      }
    ]
  }' | jq
```

Example response:

```json
[
  {
    "name": "Praça Sete",
    "lat": -19.9191023,
    "lon": -43.9385851,
    "distance_km": 2.9329,
    "duration_seconds": 283.7,
    "distance_method": "osrm"
  },
  {
    "name": "Pampulha",
    "lat": -19.8589878,
    "lon": -43.9818625,
    "distance_km": 12.4155,
    "duration_seconds": 1032.9,
    "distance_method": "osrm"
  }
]
```



#### 6) POST /api/geocode/parts

**About**: Best-effort geocoding from an ordered list of strings, from most specific to most generic. Returns a single lat/lon pair.

```bash
curl -s -X POST "http://localhost:80/api/geocode/parts" \
  -H "Content-Type: application/json" \
  -d '{
    "parts": [
      "Rua da Bahia 1000",
      "Funcionários",
      "Belo Horizonte",
      "MG"
    ]
  }' | jq
```

**Response**:

```json
{
  "lat": -19.9325162,
  "lon": -43.9273183
}
```

#### 7) POST /api/geocode/structured

**About**: Structured convenience endpoint. Provide street, neighborhood, city, and state. Internally it converts to ordered parts and applies the same best-effort geocoding as /geocode/parts.

```bash
curl -s -X POST "http://localhost:80/api/geocode/structured" \
  -H "Content-Type: application/json" \
  -d '{
    "street": "Rua da Bahia 1000",
    "neighborhood": "Funcionários",
    "city": "Belo Horizonte",
    "state": "MG"
  }' | jq
```

**Response**:

```json
{
  "lat": -19.9325162,
  "lon": -43.9273183
}
```
Environment variables (.env recommended)
----------------------------------------

The app reads configuration from environment variables (and .env). Key variables:
- NOMINATIM_URL: Primary Nominatim-compatible endpoint. Default: https://nominatim.openstreetmap.org
- PUBLIC_NOMINATIM_URL: Fallback public endpoint used when primary fails
- USER_AGENT: HTTP User-Agent header for Nominatim requests
- RUN_LOCAL: When true, prefer local Nominatim configured in docker-compose
- DATABASE_URL: Connection string used by services that require a DB
- USE_OSRM_ONLINE: If true, use public OSRM (router.project-osrm.org)
- OSRM_SERVICE_URL: URL for a local OSRM service when not using the public one
- OSRM_PROFILE: OSRM profile (car | foot | bike). Default: car
- LOG_LEVEL: Logging level for the app
- DOCKER_PLATFORM: Build target platform hint
- NOMINATIM_DB_*: Optional DB parameters for a Nominatim container

Run with docker-compose
-----------------------

- Full stack (app + optional local services):

  ```sh
  docker-compose up --build
  ```

- App only (using public Nominatim/OSRM depending on your .env):

  ```sh
  docker-compose up --build app
  ```

- Rebuild only the app image and run:

  ```sh
  docker-compose build app
  docker-compose up app
  ```

Local Nominatim notes (optional)
--------------------------------

- Nominatim installation/import: https://nominatim.org/release-docs/latest/admin/Installation/
- The mediagis/nominatim image can import from a local .osm.pbf (PBF_PATH) or a remote URL (PBF_URL).
- Importing OSM data is resource-intensive and may take hours. Ensure adequate CPU/RAM/disk.


Running tests
-------------

Locally (Python env):

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
```

Using Docker (inside the app image):

```sh
docker-compose build app
docker-compose run --rm app pytest -q
```


Troubleshooting
---------------

- Public Nominatim services enforce rate limits and require a meaningful User-Agent. Cache results when possible.
- OSRM preprocessing or map data availability can delay routing readiness on first run.
- If using a local Nominatim, make sure the app container can resolve its hostname (docker network or host mapping).


License
-------

This project relies on OpenStreetMap data (ODbL) and Nominatim. Ensure compliance with OSM licensing and Nominatim usage policies.