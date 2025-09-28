# main.py
import os
import logging
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from config.settings import settings
from database.mongodb import connect_to_mongo, close_mongo_connection
from api.routes import api_router  # aggregated router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description="Enterprise-grade AI-powered financial document analysis system",
        version=settings.VERSION,
        openapi_url=f"{settings.API_V1_STR}/openapi.json" if settings.DEBUG else None,
        docs_url="/docs" if settings.DEBUG else "/docs",  # keep docs visible if you want
        redoc_url=None,
    )

    # Middleware
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*", "localhost", "127.0.0.1"])
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # Startup / Shutdown
    @app.on_event("startup")
    async def _startup():
        await connect_to_mongo()
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        logger.info("Startup complete")

    @app.on_event("shutdown")
    async def _shutdown():
        await close_mongo_connection()
        logger.info("Shutdown complete")

    # Health / root (keep trivial handlers here)
    @app.get("/")
    async def root():
        return {
            "message": f"{settings.PROJECT_NAME} API",
            "version": settings.VERSION,
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
        }

    # Mount all app routes
    app.include_router(api_router, prefix="")

    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app",
                host=os.getenv("HOST", "127.0.0.1"),
                port=int(os.getenv("PORT", 8000)),
                reload=settings.DEBUG)
