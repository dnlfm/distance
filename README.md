# Distance Finder

Quick Start
-----------

1) Prepare local nominatim data folder (optional, only required if you plan to run a local Nominatim service):

   The repository includes a Makefile target that creates a folder for Nominatim data and will also copy .env.example to .env if present. Run:

   ```sh
   make setup
   ```

   Ensure the downloaded file is present in `./nominatim_data` before proceeding to step 2 below.

2) Run the full stack (app + local Nominatim + OSRM):

   ```sh
   docker-compose up --build
   ```

   It may take a while, about 45+ minutes to process OSRM routes before it becomes available.

About
-----------

Small FastAPI service to geocode an origin address (using a Nominatim-compatible service) and compute distances (Haversine) to a list of destinations, returning the destinations sorted by ascending distance.

This repo provides:
- FastAPI app (app/) with a /api/distance endpoint
- Geocoding service that queries a configured Nominatim endpoint and falls back to the public nominatim.openstreetmap.org
- Haversine distance implementation (and optional geopy geodesic if installed)
- Dockerfile and docker-compose.yml with an optional local Nominatim service
- Tests using pytest + pytest-asyncio and httpx

Prerequisites
- Docker & docker-compose
- Git
- (Optional, for local development) Python 3.11 and pip

Quick overview
1. If you want to use the public Nominatim service (no local Nominatim): just run the API and point NOMINATIM_URL to the public service (default).
2. If you want a local Nominatim instance with OSM data for Southeast Brazil (sudeste), download the sudeste OSM extract and follow Nominatim import instructions (outlined below).

Downloading OSM data for Sudeste (Southeast Brazil)
1. Create a folder to hold the downloaded file:

   mkdir -p ./nominatim_data

2. Download the Sudeste extract (Geofabrik) — file name may change, but the latest snapshot is available at the Geofabrik sudeste page:

   wget -P ./nominatim_data https://download.geofabrik.de/south-america/brazil/sudeste-latest.osm.pbf

3. You now have a file like ./nominatim_data/sudeste-latest.osm.pbf to import into a Nominatim instance.

Running a local Nominatim service
- Nominatim installation and import are documented at: https://nominatim.org/release-docs/latest/admin/Installation/
- The included docker-compose.yml contains an optional nominatim service using the mediagis/nominatim image. Importing OSM data into Nominatim is an intensive, multi-step process (requires PostgreSQL/postgis, sufficient RAM, and possibly manual import commands).

Important note about importing data with the mediagis/nominatim image
- The mediagis/nominatim container typically expects either PBF_URL (a remote URL to download the .osm.pbf) or PBF_PATH (a path inside the container to a local .osm.pbf file) to be provided so it can import data when the container is first started.
- In this repo we've added optional support to provide PBF_PATH via docker-compose (defaults to /var/lib/nominatim/sudeste-latest.osm.pbf). If you mount your ./nominatim_data into the container (see docker-compose.override.yml) and name the file sudeste-latest.osm.pbf it will be picked up automatically by default.
- If you prefer to instruct the image to download the PBF remotely, set PBF_URL instead (e.g. PBF_URL=https://download.geofabrik.de/.../sudeste-latest.osm.pbf).
- If you already have a pre-imported nominatim dataset inside the volume (i.e. database files already present), you do not need PBF_URL/PBF_PATH — the container can be started against the existing DB files.

Minimal notes for using the included nominatim container (high-level):
- By default docker-compose.yml defines a named volume for nominatim data. For importing a local .osm.pbf file, a bind mount is often easier — create docker-compose.override.yml to mount ./nominatim_data into the container path expected by the image (example below).
- Follow the mediagis/nominatim image docs or official Nominatim docs for the exact import commands (they may change between image versions).

Downloading notes and import
- The import step is resource-heavy and can take many hours depending on hardware. Always consult the Nominatim docs for import flags and required memory/disk.

Example docker-compose.override.yml (optional — mount local data for import):

version: "3.8"
services:
  nominatim:
    volumes:
      - ./nominatim_data:/var/lib/nominatim:rw

Save the file as docker-compose.override.yml next to docker-compose.yml. With the bind mount in place you can use the container's import utilities to point to /var/lib/nominatim/sudeste-latest.osm.pbf.

If you do not want the container to attempt an automatic import, either provide a pre-imported volume (database files already in place) or ensure PBF_URL/PBF_PATH are not set.

Running the app and full stack with docker-compose
1. Build and start all services (app, postgres, nominatim):

   docker-compose up --build

Note: If you don't want to run a local Nominatim, you can still run the app only. The app by default will use the public nominatim.openstreetmap.org endpoint (as configured in app/core/config.py). To run only the app and rely on the public Nominatim:

   docker-compose up --build app

Or rebuild only the app image and run it:

   docker-compose build app
   docker-compose up app

Environment variables (.env recommended)
You can override settings via environment variables. The app reads:
- NOMINATIM_URL: URL of your Nominatim-compatible service. Default: https://nominatim.openstreetmap.org
- USER_AGENT: HTTP User-Agent header used when calling Nominatim. Default: distance-finder/1.0
- DATABASE_URL: used by the nominatim service in docker-compose to connect to postgres (when running nominatim locally)
- PBF_PATH: (optional) path inside the nominatim container to a local .osm.pbf file (e.g. /var/lib/nominatim/sudeste-latest.osm.pbf). If provided, the mediagis/nominatim image will use this path to locate a PBF to import. Alternatively provide PBF_URL to download the PBF remotely.

Example .env (create a file named .env in repo root or export variables in your shell):

NOMINATIM_URL=https://nominatim.openstreetmap.org
USER_AGENT=distance-finder/1.0
DATABASE_URL=postgresql://nominatim:nominatim@postgres:5432/nominatim
# Optional: tell the nominatim container where the PBF is inside the container volume
# PBF_PATH=/var/lib/nominatim/sudeste-latest.osm.pbf

If you run a local nominatim service that is reachable at http://nominatim:8080 (as in docker-compose.yml), set NOMINATIM_URL=http://nominatim:8080

API usage
1. Endpoint: POST /api/distance
2. Request JSON (origin can be lat/lon or address; destinations are list of destinations with lat/lon or address):

Example using an address origin (existing endpoint):

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

Response: JSON array of objects with fields: name, lat, lon, distance_km (sorted ascending by distance)

New endpoints added

To make the service easier to integrate with other systems, two additional endpoints are provided:

- POST /api/geocode — geocode a single address and return lat/lon. Use this to persist geocoded results in your own DB and avoid repeated calls to Nominatim.
- POST /api/distance/addresses — a shortcut endpoint that accepts an origin_address string and a list of destinations defined only by name and address (no lat/lon required). The service will geocode all addresses and compute distances, returning the same DistanceResult items (name, lat, lon, distance_km) sorted by ascending distance.

Examples

Geocode a single address (useful to store lat/lon in another service):

```bash
curl -s -X POST "http://localhost:80/api/geocode" \
  -H "Content-Type: application/json" \
  -d '{"address":"Praça da Sé, São Paulo"}' | jq
```

Example response:

```json
{
  "lat": -23.55052,
  "lon": -46.633309
}
```

Use the geocode endpoint to cache results in your DB. The app also exposes the same geocoding functionality internally when you provide an address instead of lat/lon to the /api/distance endpoint.

Compute distances providing only addresses (shortcut endpoint):

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

Example response (array sorted by distance_km):

```json
[
  {"name":"Campinas","lat":-22.9099,"lon":-47.0626,"distance_km":...},
  {"name":"Rio","lat":-22.9068,"lon":-43.1729,"distance_km":...}
]
```

Notes and best practices

- Rate limits and caching: Public Nominatim servers impose rate limits and require a meaningful User-Agent header. For production workloads or larger volumes of requests, host your own Nominatim instance or cache geocoding results in your own DB. The /api/geocode endpoint is provided to help storing lat/lon for addresses you care about.
- Error handling: Geocoding failures return HTTP 400 with an error message. Validation errors return HTTP 422.
- Sorting: Distance responses are sorted by ascending distance (closest first).
- Reuse: Internally the routes reuse the same geocoding helper so behavior is consistent between /api/geocode, /api/distance when addresses are provided, and /api/distance/addresses.

Running tests
Locally (if you have Python & dependencies installed):

1. Create a virtual environment and install requirements:

   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt

2. Run pytest:

   pytest -q

Using Docker (run tests inside the app image/container):

   # Build the image (if not already built)
   docker-compose build app

   # Run tests in the app image (temporary container)
   docker-compose run --rm app pytest -q

Notes and troubleshooting
- Using the public nominatim: Public Nominatim servers impose usage limits and require a meaningful User-Agent. For heavy use or private datasets, host your own Nominatim.
- Local Nominatim import requires significant disk and memory and can be time consuming. Read the official docs carefully and consider preparing a machine with adequate resources.
- If you change NOMINATIM_URL to a local address, make sure the app container can resolve the hostname (docker-compose networking or use an IP / host mapping).

Next steps / optional improvements
- Add docker-compose.override.yml and .env.example to simplify local customization
- Provide automated Nominatim import scripts and tuned docker-compose profiles for import vs runtime
- Add more tests covering edge cases and geocoding fallback behaviors

License & acknowledgements
- This project relies on OpenStreetMap data (ODbL) and Nominatim. If you use OSM data locally, ensure you comply with OSM licensing and Nominatim usage policies.