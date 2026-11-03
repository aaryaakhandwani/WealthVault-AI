from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.v1.endpoints.health import router as health_router
from src.api.v1.router import api_router
from src.core.config import get_settings


def create_app() -> FastAPI:
    """Application factory for WealthVault-AI FastAPI backend."""
    settings = get_settings()

    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        debug=settings.DEBUG,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Set up CORS middleware if origins are configured
    if settings.ALLOWED_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.ALLOWED_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Top-level direct health check: GET /health
    app.include_router(health_router)

    # Versioned API routes: e.g. GET /api/v1/health
    app.include_router(api_router, prefix=settings.API_V1_STR)

    return app


app = create_app()
