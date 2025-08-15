"""
Package Routes
=============

Rutas para gestión de paquetes.
"""

from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.auth import get_current_active_user, require_permission
from ..models.user import User
from ..services.package_service import PackageService
from ..schemas.package import (
    PackageCreate, PackageUpdate, PackageAnnounce, PackageReceive,
    PackageResponse, PackageSearch, PackageStats, PackageTracking,
    PackageListResponse, PackageBulkAction
)

router = APIRouter(prefix="/api/packages", tags=["Packages"])

@router.post("/announce", response_model=PackageResponse)
async def announce_package(
    package_data: PackageAnnounce,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Anunciar un nuevo paquete
    
    Args:
        package_data: Datos del paquete y cliente
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        PackageResponse: Paquete creado
    """
    require_permission("packages:create")(current_user)
    
    package_service = PackageService(db)
    package = package_service.announce_package(package_data)
    
    return PackageResponse.from_orm(package)

@router.post("/{tracking_number}/receive", response_model=PackageResponse)
async def receive_package(
    tracking_number: str,
    receive_data: PackageReceive,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Recibir un paquete anunciado
    
    Args:
        tracking_number: Número de tracking del paquete
        receive_data: Datos de recepción
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        PackageResponse: Paquete actualizado
    """
    require_permission("packages:receive")(current_user)
    
    package_service = PackageService(db)
    package = package_service.receive_package(tracking_number, receive_data.notes)
    
    return PackageResponse.from_orm(package)

@router.post("/{tracking_number}/deliver")
async def deliver_package(
    tracking_number: str,
    delivery_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Entregar un paquete recibido
    
    Args:
        tracking_number: Número de tracking del paquete
        delivery_data: Datos de la entrega
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        dict: Información de la entrega
    """
    require_permission("packages:deliver")(current_user)
    
    package_service = PackageService(db)
    delivery = package_service.deliver_package(tracking_number, delivery_data)
    
    return {
        "message": "Paquete entregado exitosamente",
        "delivery_number": delivery.delivery_number,
        "tracking_number": tracking_number
    }

@router.get("/", response_model=PackageListResponse)
async def list_packages(
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(20, ge=1, le=100, description="Elementos por página"),
    search: Optional[str] = Query(None, description="Término de búsqueda"),
    status: Optional[str] = Query(None, description="Estado del paquete"),
    package_type: Optional[str] = Query(None, description="Tipo de paquete"),
    is_urgent: Optional[bool] = Query(None, description="Paquete urgente"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Listar paquetes con filtros
    
    Args:
        page: Número de página
        per_page: Elementos por página
        search: Término de búsqueda
        status: Estado del paquete
        package_type: Tipo de paquete
        is_urgent: Paquete urgente
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        PackageListResponse: Lista de paquetes
    """
    require_permission("packages:read")(current_user)
    
    search_params = PackageSearch(
        query=search,
        status=status,
        package_type=package_type,
        is_urgent=is_urgent,
        page=page,
        per_page=per_page
    )
    
    package_service = PackageService(db)
    result = package_service.search_packages(search_params)
    
    return PackageListResponse(
        packages=[PackageResponse.from_orm(pkg) for pkg in result["packages"]],
        total=result["total"],
        page=result["page"],
        per_page=result["per_page"],
        total_pages=result["total_pages"]
    )

@router.get("/{tracking_number}", response_model=PackageResponse)
async def get_package(
    tracking_number: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Obtener paquete por número de tracking
    
    Args:
        tracking_number: Número de tracking
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        PackageResponse: Información del paquete
    """
    require_permission("packages:read")(current_user)
    
    package_service = PackageService(db)
    package = package_service.get_package_by_tracking(tracking_number)
    
    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paquete no encontrado"
        )
    
    return PackageResponse.from_orm(package)

@router.get("/{tracking_number}/tracking", response_model=PackageTracking)
async def track_package(
    tracking_number: str,
    db: Session = Depends(get_db)
) -> Any:
    """
    Seguimiento de paquete (público)
    
    Args:
        tracking_number: Número de tracking
        db: Sesión de base de datos
        
    Returns:
        PackageTracking: Información de seguimiento
    """
    package_service = PackageService(db)
    tracking_info = package_service.get_package_tracking(tracking_number)
    
    if not tracking_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paquete no encontrado"
        )
    
    return tracking_info

@router.put("/{tracking_number}", response_model=PackageResponse)
async def update_package(
    tracking_number: str,
    update_data: PackageUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Actualizar paquete
    
    Args:
        tracking_number: Número de tracking
        update_data: Datos de actualización
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        PackageResponse: Paquete actualizado
    """
    require_permission("packages:update")(current_user)
    
    package_service = PackageService(db)
    package = package_service.get_package_by_tracking(tracking_number)
    
    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paquete no encontrado"
        )
    
    updated_package = package_service.update_package(package.id, update_data)
    
    if not updated_package:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error actualizando paquete"
        )
    
    return PackageResponse.from_orm(updated_package)

@router.delete("/{tracking_number}")
async def delete_package(
    tracking_number: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Eliminar paquete
    
    Args:
        tracking_number: Número de tracking
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        dict: Mensaje de confirmación
    """
    require_permission("packages:delete")(current_user)
    
    package_service = PackageService(db)
    package = package_service.get_package_by_tracking(tracking_number)
    
    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paquete no encontrado"
        )
    
    success = package_service.delete_package(package.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error eliminando paquete"
        )
    
    return {"message": "Paquete eliminado exitosamente"}

@router.get("/stats/overview", response_model=PackageStats)
async def get_package_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Obtener estadísticas de paquetes
    
    Args:
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        PackageStats: Estadísticas de paquetes
    """
    require_permission("packages:read")(current_user)
    
    package_service = PackageService(db)
    return package_service.get_package_stats()

@router.post("/bulk-action")
async def bulk_action_packages(
    bulk_data: PackageBulkAction,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Acción masiva en paquetes
    
    Args:
        bulk_data: Datos de la acción masiva
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        dict: Resultado de la acción masiva
    """
    require_permission("packages:bulk_action")(current_user)
    
    package_service = PackageService(db)
    
    results = {
        "action": bulk_data.action,
        "total": len(bulk_data.package_ids),
        "success": 0,
        "failed": 0,
        "errors": []
    }
    
    for package_id in bulk_data.package_ids:
        try:
            package = package_service.get_package_by_id(package_id)
            
            if not package:
                results["failed"] += 1
                results["errors"].append(f"Paquete {package_id} no encontrado")
                continue
            
            if bulk_data.action == "receive":
                if package.status.value == "announced":
                    package_service.receive_package(package.tracking_number, bulk_data.notes)
                    results["success"] += 1
                else:
                    results["failed"] += 1
                    results["errors"].append(f"Paquete {package.tracking_number} no puede ser recibido")
            
            elif bulk_data.action == "deliver":
                if package.status.value == "received":
                    # Para entrega masiva, usar datos por defecto
                    delivery_data = {
                        "recipient_name": "Cliente",
                        "payment_method": "cash",
                        "amount_paid": float(package.total_cost)
                    }
                    package_service.deliver_package(package.tracking_number, delivery_data)
                    results["success"] += 1
                else:
                    results["failed"] += 1
                    results["errors"].append(f"Paquete {package.tracking_number} no puede ser entregado")
            
            elif bulk_data.action == "cancel":
                if package.status.value in ["announced", "received"]:
                    package_service.update_package(package.id, PackageUpdate(status="cancelled"))
                    results["success"] += 1
                else:
                    results["failed"] += 1
                    results["errors"].append(f"Paquete {package.tracking_number} no puede ser cancelado")
            
            elif bulk_data.action == "delete":
                if package.status.value == "announced":
                    package_service.delete_package(package.id)
                    results["success"] += 1
                else:
                    results["failed"] += 1
                    results["errors"].append(f"Paquete {package.tracking_number} no puede ser eliminado")
                    
        except Exception as e:
            results["failed"] += 1
            results["errors"].append(f"Error procesando paquete {package_id}: {str(e)}")
    
    return results

@router.post("/expire")
async def expire_packages(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Expirar paquetes automáticamente
    
    Args:
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        dict: Resultado de la expiración
    """
    require_permission("packages:expire")(current_user)
    
    package_service = PackageService(db)
    expired_count = package_service.expire_packages()
    
    return {
        "message": f"Expiraron {expired_count} paquetes",
        "expired_count": expired_count
    }

@router.get("/urgent/list")
async def list_urgent_packages(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Listar paquetes urgentes
    
    Args:
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        List[PackageResponse]: Lista de paquetes urgentes
    """
    require_permission("packages:read")(current_user)
    
    package_service = PackageService(db)
    search_params = PackageSearch(is_urgent=True, per_page=100)
    result = package_service.search_packages(search_params)
    
    return [PackageResponse.from_orm(pkg) for pkg in result["packages"]]

@router.get("/pending/list")
async def list_pending_packages(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Listar paquetes pendientes de recepción
    
    Args:
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        List[PackageResponse]: Lista de paquetes pendientes
    """
    require_permission("packages:read")(current_user)
    
    package_service = PackageService(db)
    search_params = PackageSearch(status="announced", per_page=100)
    result = package_service.search_packages(search_params)
    
    return [PackageResponse.from_orm(pkg) for pkg in result["packages"]]

@router.get("/health")
async def packages_health_check() -> Any:
    """
    Health check para el módulo de paquetes
    
    Returns:
        dict: Estado del módulo
    """
    return {
        "status": "healthy",
        "module": "packages",
        "endpoints": [
            "announce", "receive", "deliver", "list", "tracking",
            "update", "delete", "stats", "bulk_action"
        ]
    }
