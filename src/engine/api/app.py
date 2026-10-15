"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

app = FastAPI(
    title="Autonomous Marketing Engine API",
    version="1.0.0",
    description="Multi-tenant, event-sourced, bandit-optimized autonomous marketing platform.",
)

# Enable CORS for Next.js dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
