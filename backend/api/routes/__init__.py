# api/routes/__init__.py
from fastapi import APIRouter
from .auth import router as auth_router
from .documents import router as documents_router
from .analysis import router as analysis_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(documents_router, prefix="/api/v1/documents", tags=["documents"])
api_router.include_router(analysis_router, prefix="/api/v1", tags=["analysis"])
