"""
Admin Routes
===========

Rutas administrativas para gestión del sistema.
"""

from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.auth import get_current_superuser, require_permission
from ..models.user import User
from ..services.package_service import PackageService
from ..services.customer_service import CustomerService
from ..services.notification_service import NotificationService
from ..services.file_service import FileService

router = APIRouter(prefix="/api/admin", tags=["Administration"])

@router.get("/dashboard")
async def admin_dashboard(
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
) -> Any:
    """
    Dashboard administrativo con estadísticas completas
    
    Args:
        current_user: Usuario actual (debe ser superusuario)
        db: Sesión de base de datos
        
    Returns:
        dict: Estadísticas completas del sistema
    """
    package_service = PackageService(db)
    customer_service = CustomerService(db)
    notification_service = NotificationService(db)
    file_service = FileService(db)
    
    # Obtener todas las estadísticas
    package_stats = package_service.get_package_stats()
    customer_stats = customer_service.get_customer_stats()
    notification_stats = notification_service.get_notification_stats()
    file_stats = file_service.get_file_stats()
    
    return {
        "system_info": {
            "app_name": "Sistema de Paquetería v1.1",
            "version": "1.0.0",
            "admin_user": current_user.username
        },
        "package_stats": package_stats,
        "customer_stats": customer_stats,
        "notification_stats": notification_stats,
        "file_stats": file_stats
    }

@router.post("/maintenance/cleanup")
async def system_cleanup(
    cleanup_type: str = Query(..., description="Tipo de limpieza"),
    days: int = Query(90, ge=1, description="Días a mantener"),
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
) -> Any:
    """
    Limpieza del sistema
    
    Args:
        cleanup_type: Tipo de limpieza (notifications, files, packages)
        days: Días a mantener
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        dict: Resultado de la limpieza
    """
    results = {}
    
    if cleanup_type == "notifications":
        notification_service = NotificationService(db)
        deleted_count = notification_service.cleanup_old_notifications(days)
        results["notifications_deleted"] = deleted_count
    
    elif cleanup_type == "files":
        file_service = FileService(db)
        deleted_count = file_service.cleanup_orphaned_files()
        results["files_deleted"] = deleted_count
    
    elif cleanup_type == "packages":
        package_service = PackageService(db)
        expired_count = package_service.expire_packages()
        results["packages_expired"] = expired_count
    
    elif cleanup_type == "all":
        # Limpieza completa
        notification_service = NotificationService(db)
        file_service = FileService(db)
        package_service = PackageService(db)
        
        notifications_deleted = notification_service.cleanup_old_notifications(days)
        files_deleted = file_service.cleanup_orphaned_files()
        packages_expired = package_service.expire_packages()
        
        results = {
            "notifications_deleted": notifications_deleted,
            "files_deleted": files_deleted,
            "packages_expired": packages_expired
        }
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipo de limpieza no válido"
        )
    
    return {
        "message": "Limpieza completada exitosamente",
        "results": results
    }

@router.post("/maintenance/process-scheduled")
async def process_scheduled_tasks(
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
) -> Any:
    """
    Procesar tareas programadas
    
    Args:
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        dict: Resultado del procesamiento
    """
    results = {}
    
    # Procesar notificaciones programadas
    notification_service = NotificationService(db)
    notifications_processed = notification_service.process_scheduled_notifications()
    results["notifications_processed"] = notifications_processed
    
    # Expirar paquetes
    package_service = PackageService(db)
    packages_expired = package_service.expire_packages()
    results["packages_expired"] = packages_expired
    
    return {
        "message": "Tareas programadas procesadas exitosamente",
        "results": results
    }

@router.get("/system/health")
async def system_health_check(
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
) -> Any:
    """
    Health check completo del sistema
    
    Args:
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        dict: Estado de salud del sistema
    """
    health_status = {
        "status": "healthy",
        "timestamp": "2025-01-15T14:30:00Z",
        "modules": {}
    }
    
    try:
        # Verificar base de datos
        db.execute("SELECT 1")
        health_status["modules"]["database"] = "healthy"
    except Exception as e:
        health_status["modules"]["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "unhealthy"
    
    try:
        # Verificar servicios
        package_service = PackageService(db)
        customer_service = CustomerService(db)
        notification_service = NotificationService(db)
        file_service = FileService(db)
        
        # Pruebas básicas de servicios
        package_service.get_package_stats()
        customer_service.get_customer_stats()
        notification_service.get_notification_stats()
        file_service.get_file_stats()
        
        health_status["modules"]["services"] = "healthy"
    except Exception as e:
        health_status["modules"]["services"] = f"unhealthy: {str(e)}"
        health_status["status"] = "unhealthy"
    
    return health_status

@router.get("/system/storage")
async def system_storage_info(
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
) -> Any:
    """
    Información de almacenamiento del sistema
    
    Args:
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        dict: Información de almacenamiento
    """
    file_service = FileService(db)
    storage_usage = file_service.get_storage_usage()
    file_stats = file_service.get_file_stats()
    
    return {
        "file_stats": file_stats,
        "storage_usage": storage_usage,
        "storage_info": {
            "total_files": file_stats.total_files,
            "total_size_mb": file_stats.total_size_mb,
            "average_file_size": file_stats.average_file_size
        }
    }

@router.get("/system/notifications/status")
async def notification_system_status(
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
) -> Any:
    """
    Estado del sistema de notificaciones
    
    Args:
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        dict: Estado del sistema de notificaciones
    """
    notification_service = NotificationService(db)
    stats = notification_service.get_notification_stats()
    
    # Verificar configuración de APIs externas
    from ..core.config import settings
    
    api_status = {
        "liwa_sms": {
            "configured": bool(settings.LIWA_API_KEY and settings.LIWA_API_URL),
            "api_key": "configured" if settings.LIWA_API_KEY else "missing",
            "api_url": settings.LIWA_API_URL or "not configured"
        },
        "aws_s3": {
            "configured": bool(settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY),
            "bucket": settings.S3_BUCKET_NAME or "not configured",
            "region": settings.AWS_REGION or "not configured"
        }
    }
    
    return {
        "notification_stats": stats,
        "api_status": api_status,
        "system_status": "operational" if stats.success_rate > 90 else "degraded"
    }

@router.post("/system/backup")
async def create_system_backup(
    backup_type: str = Query("full", description="Tipo de backup"),
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
) -> Any:
    """
    Crear backup del sistema
    
    Args:
        backup_type: Tipo de backup (full, database, files)
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        dict: Información del backup
    """
    # En una implementación real, aquí se ejecutaría el script de backup
    import subprocess
    import datetime
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    try:
        if backup_type == "full":
            # Backup completo usando el script
            result = subprocess.run(
                ["./scripts/backup-restore.sh", "backup"],
                capture_output=True,
                text=True,
                cwd="."
            )
            
            if result.returncode == 0:
                return {
                    "message": "Backup completo creado exitosamente",
                    "timestamp": timestamp,
                    "type": "full"
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error creando backup: {result.stderr}"
                )
        
        elif backup_type == "database":
            # Solo backup de base de datos
            result = subprocess.run(
                ["docker-compose", "exec", "-T", "mysql", "mysqldump", "-u", "paqueteria_user", "-ppaqueteria_pass", "paqueteria"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                return {
                    "message": "Backup de base de datos creado exitosamente",
                    "timestamp": timestamp,
                    "type": "database"
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error creando backup de base de datos: {result.stderr}"
                )
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tipo de backup no válido"
            )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error en backup: {str(e)}"
        )

@router.get("/system/logs")
async def get_system_logs(
    log_type: str = Query("app", description="Tipo de log"),
    lines: int = Query(100, ge=1, le=1000, description="Número de líneas"),
    current_user: User = Depends(get_current_superuser)
) -> Any:
    """
    Obtener logs del sistema
    
    Args:
        log_type: Tipo de log (app, nginx, mysql, redis)
        lines: Número de líneas a obtener
        current_user: Usuario actual
        
    Returns:
        dict: Logs del sistema
    """
    import subprocess
    
    log_files = {
        "app": "./volumes/logs/app.log",
        "nginx": "./volumes/nginx/logs/access.log",
        "mysql": "./volumes/mysql/logs/mysql.log",
        "redis": "./volumes/redis/logs/redis.log"
    }
    
    if log_type not in log_files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipo de log no válido"
        )
    
    try:
        result = subprocess.run(
            ["tail", "-n", str(lines), log_files[log_type]],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            return {
                "log_type": log_type,
                "lines": lines,
                "content": result.stdout.split('\n')
            }
        else:
            return {
                "log_type": log_type,
                "lines": lines,
                "content": [f"Error leyendo log: {result.stderr}"]
            }
    
    except Exception as e:
        return {
            "log_type": log_type,
            "lines": lines,
            "content": [f"Error: {str(e)}"]
        }

@router.get("/system/performance")
async def system_performance_metrics(
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
) -> Any:
    """
    Métricas de rendimiento del sistema
    
    Args:
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        dict: Métricas de rendimiento
    """
    import psutil
    import datetime
    
    # Métricas del sistema
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # Métricas de la aplicación
    package_service = PackageService(db)
    customer_service = CustomerService(db)
    notification_service = NotificationService(db)
    
    package_stats = package_service.get_package_stats()
    customer_stats = customer_service.get_customer_stats()
    notification_stats = notification_service.get_notification_stats()
    
    return {
        "timestamp": datetime.datetime.now().isoformat(),
        "system_metrics": {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_available_gb": memory.available / (1024**3),
            "disk_percent": disk.percent,
            "disk_free_gb": disk.free / (1024**3)
        },
        "application_metrics": {
            "total_packages": package_stats.total_packages,
            "total_customers": customer_stats.total_customers,
            "total_notifications": notification_stats.total_notifications,
            "notification_success_rate": notification_stats.success_rate
        }
    }

@router.get("/health")
async def admin_health_check() -> Any:
    """
    Health check para el módulo administrativo
    
    Returns:
        dict: Estado del módulo
    """
    return {
        "status": "healthy",
        "module": "administration",
        "endpoints": [
            "dashboard", "maintenance", "system", "backup", "logs", "performance"
        ]
    }
