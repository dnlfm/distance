from fastapi import FastAPI
from app.api.routes import router


"""FastAPI application entrypoint.
Provides the ASGI app instance and includes API routes.
"""

app = FastAPI(title="Distance Finder")
app.include_router(router, prefix="/api")


# Simple root
@app.get("/", tags=["root"])  
async def root():
    """Root health endpoint. - health"""
    return {"status": "ok", "service": "distance-finder"}
