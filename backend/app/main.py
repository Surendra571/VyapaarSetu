from contextlib import asynccontextmanager
from typing import AsyncGenerator
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.api.v1.router import api_v1_router
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown events."""
    print(f"Starting {settings.APP_NAME} backend in {settings.ENVIRONMENT} mode...")
    yield
    print(f"Stopping {settings.APP_NAME} backend...")


app = FastAPI(
    title=settings.APP_NAME,
    description="VyapaarSetu B2B FMCG Ordering Platform Backend API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configure Cross-Origin Resource Sharing (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"^https?:\/\/(localhost|127\.0\.0\.1|.*\.vercel\.app|.*\.onrender\.com)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(api_v1_router, prefix="/api/v1")

# Frontend static distribution path
FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

if FRONTEND_DIST.exists() and (FRONTEND_DIST / "index.html").exists():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    images_dir = FRONTEND_DIST / "images"
    if images_dir.exists():
        app.mount("/images", StaticFiles(directory=str(images_dir)), name="images")

    @app.get("/manifest.webmanifest", include_in_schema=False)
    async def get_manifest():
        return FileResponse(FRONTEND_DIST / "manifest.webmanifest")

    @app.get("/sw.js", include_in_schema=False)
    async def get_sw():
        return FileResponse(FRONTEND_DIST / "sw.js")


@app.get("/", tags=["Root"])
async def root(request: Request):
    """Root entry point: Serves the React SPA in browsers or returns JSON metadata for API clients."""
    accept = request.headers.get("accept", "")
    if "text/html" in accept and FRONTEND_DIST.exists() and (FRONTEND_DIST / "index.html").exists():
        return FileResponse(FRONTEND_DIST / "index.html")
    return {
        "app": settings.APP_NAME,
        "version": "0.1.0",
        "status": "operational",
        "docs": "/docs",
        "health_check": "/api/v1/health",
    }


if FRONTEND_DIST.exists() and (FRONTEND_DIST / "index.html").exists():
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa_screens(full_path: str, request: Request):
        if full_path.startswith("api/") or full_path in ("docs", "redoc", "openapi.json"):
            raise HTTPException(status_code=404, detail="Not Found")

        file_path = FRONTEND_DIST / full_path
        if file_path.is_file():
            return FileResponse(file_path)

        accept = request.headers.get("accept", "")
        if "text/html" in accept or "." not in full_path:
            return FileResponse(FRONTEND_DIST / "index.html")

        raise HTTPException(status_code=404, detail="File not found")
