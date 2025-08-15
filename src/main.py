# =============================================================================
# MAIN.PY - Sistema de Paquetería v1.1
# =============================================================================

"""
Aplicación principal FastAPI para el Sistema de Gestión de Paquetería v1.1

Este módulo configura y ejecuta la aplicación FastAPI con todas las rutas,
middleware y configuraciones necesarias.
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.database import engine, Base
from app.core.logging import setup_logging
from app.routes import packages, notifications, files, admin, auth
from app.utils.health_check import health_check_router

# =============================================================================
# Configuración de logging
# =============================================================================
logger = logging.getLogger(__name__)
setup_logging()

# =============================================================================
# Rate Limiter
# =============================================================================
limiter = Limiter(key_func=get_remote_address)

# =============================================================================
# Eventos de ciclo de vida de la aplicación
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Eventos de ciclo de vida de la aplicación
    """
    # Startup
    logger.info("🚀 Iniciando Sistema de Paquetería v1.1")
    
    # Crear tablas de base de datos
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Base de datos inicializada correctamente")
    except Exception as e:
        logger.error(f"❌ Error inicializando base de datos: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("🛑 Cerrando Sistema de Paquetería v1.1")

# =============================================================================
# Configuración de la aplicación FastAPI
# =============================================================================

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Sistema de Gestión de Paquetería v1.1 - Plataforma digital moderna para gestión de paquetes",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan
)

# =============================================================================
# Middleware
# =============================================================================

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate Limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# =============================================================================
# Configuración de archivos estáticos y templates
# =============================================================================

# Archivos estáticos
app.mount("/static", StaticFiles(directory="src/static"), name="static")

# Templates
templates = Jinja2Templates(directory="src/templates")

# =============================================================================
# Rutas principales
# =============================================================================

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """
    Página principal de la aplicación
    """
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "app_name": settings.APP_NAME,
            "app_version": settings.APP_VERSION
        }
    )

@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint
    """
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "database": "connected"
    }

# =============================================================================
# Incluir routers
# =============================================================================

# Health check router
app.include_router(health_check_router, prefix="/health", tags=["health"])

# API routers
app.include_router(
    packages.router,
    prefix="/api/v1/packages",
    tags=["packages"]
)

app.include_router(
    notifications.router,
    prefix="/api/v1/notifications",
    tags=["notifications"]
)

app.include_router(
    files.router,
    prefix="/api/v1/files",
    tags=["files"]
)

app.include_router(
    auth.router,
    prefix="/api/v1/auth",
    tags=["authentication"]
)

app.include_router(
    admin.router,
    prefix="/api/v1/admin",
    tags=["admin"]
)

# =============================================================================
# Manejo de errores
# =============================================================================

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """
    Manejo de errores 404
    """
    return templates.TemplateResponse(
        "404.html",
        {
            "request": request,
            "app_name": settings.APP_NAME
        },
        status_code=404
    )

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: HTTPException):
    """
    Manejo de errores 500
    """
    logger.error(f"Error interno del servidor: {exc}")
    return templates.TemplateResponse(
        "500.html",
        {
            "request": request,
            "app_name": settings.APP_NAME
        },
        status_code=500
    )

# =============================================================================
# Middleware de logging
# =============================================================================

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Middleware para logging de requests
    """
    logger.info(f"Request: {request.method} {request.url}")
    response = await call_next(request)
    logger.info(f"Response: {response.status_code}")
    return response

# =============================================================================
# Punto de entrada principal
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )
