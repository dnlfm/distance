FROM python:3.11-slim

# metadata
LABEL org.opencontainers.image.title="distance-finder"
LABEL org.opencontainers.image.description="FastAPI service to compute distances using Nominatim and Haversine formula"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system deps required for some Python packages (kept minimal)
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first to leverage Docker cache if they exist
COPY requirements.txt /app/

# Upgrade pip and install dependencies. If requirements.txt is absent, install minimal runtime deps.
RUN pip install --upgrade pip setuptools wheel \
    && if [ -f requirements.txt ]; then pip install -r requirements.txt; else pip install fastapi uvicorn[standard] httpx pydantic; fi

# Copy application code
COPY . /app

# Expose default HTTP port
EXPOSE 80

# Default command to run the FastAPI app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80", "--workers", "1"]
