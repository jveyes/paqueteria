"""
Routes package - Endpoints de la API
===================================

Rutas FastAPI para el sistema de paquetería.
"""

from .auth import router as auth_router
from .packages import router as packages_router
from .customers import router as customers_router
from .notifications import router as notifications_router
from .files import router as files_router
from .admin import router as admin_router
from .web import router as web_router

__all__ = [
    "auth_router",
    "packages_router", 
    "customers_router",
    "notifications_router",
    "files_router",
    "admin_router",
    "web_router"
]
