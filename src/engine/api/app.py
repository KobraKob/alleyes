"""FastAPI application entry point."""

from uuid import UUID

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from src.engine.api.auth import verify_api_key
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
from src.engine.config import get_settings
from src.engine.db.session import admin_session

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


PUBLIC_PATHS = {
    "/health",
    "/ready",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/v1/webhooks/whatsapp",
}
PUBLIC_PREFIXES = ("/t/",)


@app.middleware("http")
async def authenticate_api_requests(
    request: Request, call_next: RequestResponseEndpoint
) -> Response:
    """Authenticate tenant API traffic and bind the API key to its tenant."""
    path = request.url.path
    if (
        request.method == "OPTIONS"
        or path in PUBLIC_PATHS
        or any(path.startswith(p) for p in PUBLIC_PREFIXES)
    ):
        return await call_next(request)
    if not path.startswith("/v1/"):
        return await call_next(request)

    raw_key = request.headers.get("X-API-Key")
    requested_business = request.headers.get("X-Business-ID")
    if not raw_key or not requested_business:
        return JSONResponse(
            status_code=401,
            content={"detail": "X-API-Key and X-Business-ID headers are required."},
        )
    try:
        requested_id = UUID(requested_business)
    except ValueError:
        return JSONResponse(status_code=400, content={"detail": "X-Business-ID must be a UUID."})

    try:
        with admin_session() as session:
            candidates = session.execute(
                text(
                    "SELECT business_id, key_hash FROM api_keys "
                    "WHERE key_prefix = :prefix AND revoked_at IS NULL"
                ),
                {"prefix": raw_key[:8]},
            ).fetchall()
            authenticated_id = next(
                (UUID(str(row[0])) for row in candidates if verify_api_key(raw_key, str(row[1]))),
                None,
            )
    except Exception:
        return JSONResponse(
            status_code=503, content={"detail": "Authentication service unavailable."}
        )

    if authenticated_id is None:
        return JSONResponse(
            status_code=401, content={"detail": "Invalid or revoked API key."}
        )
    if authenticated_id != requested_id:
        return JSONResponse(
            status_code=403,
            content={"detail": "API key does not belong to this business."},
        )
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
    """Liveness probe. Does not require database availability."""
    return {"status": "healthy", "engine": "alleeyes"}


@app.get("/ready")
def readiness_check() -> dict[str, str]:
    """Readiness probe verifies database connectivity and schema access."""
    try:
        with admin_session() as session:
            session.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database unavailable.") from exc
    return {"status": "ready", "database": "reachable"}
