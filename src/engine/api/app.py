"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette.requests import Request
from uuid import UUID

from src.engine.api.auth import verify_api_key
from src.engine.db.session import admin_session
from src.engine.config import get_settings

from src.engine.api.routes import (
    actions,
    businesses,
    events,
    frontdesk,
    kill_switch,
    leads,
    reports,
    tracking,
)

settings = get_settings()

app = FastAPI(
    title="Autonomous Marketing Engine API",
    version="1.0.0",
    description="Multi-tenant, event-sourced, bandit-optimized autonomous marketing platform.",
)

# Enable CORS for Next.js dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


PUBLIC_PREFIXES = (
    "/health", "/docs", "/redoc", "/openapi.json",
    "/v1/webhooks/", "/t/",
)


@app.middleware("http")
async def authenticate_api_requests(request: Request, call_next):
    """Authenticate tenant API traffic and bind the API key to its tenant."""
    path = request.url.path
    if request.method == "OPTIONS" or any(path == p or path.startswith(p) for p in PUBLIC_PREFIXES):
        return await call_next(request)
    if not path.startswith("/v1/"):
        return await call_next(request)

    raw_key = request.headers.get("X-API-Key")
    requested_business = request.headers.get("X-Business-ID")
    if not raw_key or not requested_business:
        return JSONResponse(status_code=401, content={"detail": "X-API-Key and X-Business-ID headers are required."})
    try:
        requested_id = UUID(requested_business)
        with admin_session() as session:
            candidates = session.execute(
                text("SELECT business_id, key_hash FROM api_keys WHERE key_prefix = :prefix AND revoked_at IS NULL"),
                {"prefix": raw_key[:8]},
            ).fetchall()
            authenticated_id = next(
                (UUID(str(row[0])) for row in candidates if verify_api_key(raw_key, str(row[1]))),
                None,
            )
    except Exception:
        return JSONResponse(status_code=503, content={"detail": "Authentication service unavailable."})

    if authenticated_id is None:
        return JSONResponse(status_code=401, content={"detail": "Invalid or revoked API key."})
    if authenticated_id != requested_id:
        return JSONResponse(status_code=403, content={"detail": "API key does not belong to this business."})
    request.state.business_id = authenticated_id
    return await call_next(request)


# Mount routers
app.include_router(events.router)
app.include_router(leads.router)
app.include_router(tracking.router)
app.include_router(frontdesk.router)
app.include_router(actions.router)
app.include_router(kill_switch.router)
app.include_router(businesses.router)
app.include_router(reports.router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "healthy", "engine": "autonomous-marketing-engine"}
