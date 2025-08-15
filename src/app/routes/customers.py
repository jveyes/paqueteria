"""
Customer Routes
==============

Rutas para gestión de clientes.
"""

from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.auth import get_current_active_user, require_permission
from ..models.user import User
from ..services.customer_service import CustomerService
from ..schemas.customer import (
    CustomerCreate, CustomerUpdate, CustomerResponse, CustomerSearch,
    CustomerStats, CustomerVerification, CustomerExport, CustomerListResponse
)

router = APIRouter(prefix="/api/customers", tags=["Customers"])

@router.post("/", response_model=CustomerResponse)
async def create_customer(
    customer_data: CustomerCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Crear un nuevo cliente
    
    Args:
        customer_data: Datos del cliente
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        CustomerResponse: Cliente creado
    """
    require_permission("customers:create")(current_user)
    
    customer_service = CustomerService(db)
    customer = customer_service.create_customer(customer_data)
    
    return CustomerResponse.from_orm(customer)

@router.get("/", response_model=CustomerListResponse)
async def list_customers(
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(20, ge=1, le=100, description="Elementos por página"),
    search: Optional[str] = Query(None, description="Término de búsqueda"),
    phone_number: Optional[str] = Query(None, description="Número de teléfono"),
    city: Optional[str] = Query(None, description="Ciudad"),
    is_verified: Optional[bool] = Query(None, description="Cliente verificado"),
    is_active: Optional[bool] = Query(None, description="Cliente activo"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Listar clientes con filtros
    
    Args:
        page: Número de página
        per_page: Elementos por página
        search: Término de búsqueda
        phone_number: Número de teléfono
        city: Ciudad
        is_verified: Cliente verificado
        is_active: Cliente activo
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        CustomerListResponse: Lista de clientes
    """
    require_permission("customers:read")(current_user)
    
    search_params = CustomerSearch(
        query=search,
        phone_number=phone_number,
        city=city,
        is_verified=is_verified,
        is_active=is_active,
        page=page,
        per_page=per_page
    )
    
    customer_service = CustomerService(db)
    result = customer_service.search_customers(search_params)
    
    return CustomerListResponse(
        customers=[CustomerResponse.from_orm(customer) for customer in result["customers"]],
        total=result["total"],
        page=result["page"],
        per_page=result["per_page"],
        total_pages=result["total_pages"]
    )

@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Obtener cliente por ID
    
    Args:
        customer_id: ID del cliente
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        CustomerResponse: Información del cliente
    """
    require_permission("customers:read")(current_user)
    
    customer_service = CustomerService(db)
    customer = customer_service.get_customer_by_id(customer_id)
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado"
        )
    
    return CustomerResponse.from_orm(customer)

@router.get("/phone/{phone_number}", response_model=CustomerResponse)
async def get_customer_by_phone(
    phone_number: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Obtener cliente por número de teléfono
    
    Args:
        phone_number: Número de teléfono
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        CustomerResponse: Información del cliente
    """
    require_permission("customers:read")(current_user)
    
    customer_service = CustomerService(db)
    customer = customer_service.get_customer_by_phone(phone_number)
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado"
        )
    
    return CustomerResponse.from_orm(customer)

@router.put("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: int,
    update_data: CustomerUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Actualizar cliente
    
    Args:
        customer_id: ID del cliente
        update_data: Datos de actualización
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        CustomerResponse: Cliente actualizado
    """
    require_permission("customers:update")(current_user)
    
    customer_service = CustomerService(db)
    customer = customer_service.update_customer(customer_id, update_data)
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado"
        )
    
    return CustomerResponse.from_orm(customer)

@router.post("/{customer_id}/verify")
async def verify_customer(
    customer_id: int,
    verification_data: CustomerVerification,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Verificar cliente con código
    
    Args:
        customer_id: ID del cliente
        verification_data: Datos de verificación
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        dict: Resultado de la verificación
    """
    require_permission("customers:verify")(current_user)
    
    customer_service = CustomerService(db)
    success = customer_service.verify_customer(verification_data)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código de verificación incorrecto"
        )
    
    return {"message": "Cliente verificado exitosamente"}

@router.post("/{customer_id}/generate-code")
async def generate_verification_code(
    customer_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Generar código de verificación para cliente
    
    Args:
        customer_id: ID del cliente
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        dict: Código generado
    """
    require_permission("customers:verify")(current_user)
    
    customer_service = CustomerService(db)
    customer = customer_service.get_customer_by_id(customer_id)
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado"
        )
    
    code = customer_service.generate_verification_code(customer.phone_number)
    
    return {
        "message": "Código de verificación generado",
        "code": code,
        "phone_number": customer.phone_number
    }

@router.post("/{customer_id}/activate")
async def activate_customer(
    customer_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Activar cliente
    
    Args:
        customer_id: ID del cliente
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        dict: Mensaje de confirmación
    """
    require_permission("customers:update")(current_user)
    
    customer_service = CustomerService(db)
    success = customer_service.activate_customer(customer_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado"
        )
    
    return {"message": "Cliente activado exitosamente"}

@router.post("/{customer_id}/deactivate")
async def deactivate_customer(
    customer_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Desactivar cliente
    
    Args:
        customer_id: ID del cliente
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        dict: Mensaje de confirmación
    """
    require_permission("customers:update")(current_user)
    
    customer_service = CustomerService(db)
    success = customer_service.deactivate_customer(customer_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado"
        )
    
    return {"message": "Cliente desactivado exitosamente"}

@router.delete("/{customer_id}")
async def delete_customer(
    customer_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Eliminar cliente (soft delete)
    
    Args:
        customer_id: ID del cliente
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        dict: Mensaje de confirmación
    """
    require_permission("customers:delete")(current_user)
    
    customer_service = CustomerService(db)
    success = customer_service.delete_customer(customer_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado"
        )
    
    return {"message": "Cliente eliminado exitosamente"}

@router.get("/{customer_id}/packages")
async def get_customer_packages(
    customer_id: int,
    limit: int = Query(10, ge=1, le=100, description="Límite de paquetes"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Obtener paquetes de un cliente
    
    Args:
        customer_id: ID del cliente
        limit: Límite de paquetes
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        List: Lista de paquetes del cliente
    """
    require_permission("customers:read")(current_user)
    
    customer_service = CustomerService(db)
    packages = customer_service.get_customer_packages(customer_id, limit)
    
    return [{"id": p.id, "tracking_number": p.tracking_number, "status": p.status.value} for p in packages]

@router.get("/{customer_id}/notifications")
async def get_customer_notifications(
    customer_id: int,
    limit: int = Query(10, ge=1, le=100, description="Límite de notificaciones"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Obtener notificaciones de un cliente
    
    Args:
        customer_id: ID del cliente
        limit: Límite de notificaciones
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        List: Lista de notificaciones del cliente
    """
    require_permission("customers:read")(current_user)
    
    customer_service = CustomerService(db)
    notifications = customer_service.get_customer_notifications(customer_id, limit)
    
    return [{"id": n.id, "type": n.notification_type.value, "status": n.status.value} for n in notifications]

@router.get("/stats/overview", response_model=CustomerStats)
async def get_customer_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Obtener estadísticas de clientes
    
    Args:
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        CustomerStats: Estadísticas de clientes
    """
    require_permission("customers:read")(current_user)
    
    customer_service = CustomerService(db)
    return customer_service.get_customer_stats()

@router.post("/export")
async def export_customers(
    export_params: CustomerExport,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Exportar clientes
    
    Args:
        export_params: Parámetros de exportación
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        dict: Datos exportados
    """
    require_permission("customers:export")(current_user)
    
    customer_service = CustomerService(db)
    return customer_service.export_customers(export_params)

@router.get("/top/list")
async def get_top_customers(
    limit: int = Query(10, ge=1, le=50, description="Límite de clientes"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Obtener clientes con más paquetes
    
    Args:
        limit: Límite de clientes
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        List: Lista de clientes top
    """
    require_permission("customers:read")(current_user)
    
    customer_service = CustomerService(db)
    top_customers = customer_service.get_top_customers(limit)
    
    return [
        {
            "customer": CustomerResponse.from_orm(customer),
            "package_count": package_count,
            "total_spent": float(total_spent) if total_spent else 0
        }
        for customer, package_count, total_spent in top_customers
    ]

@router.get("/inactive/list")
async def get_inactive_customers(
    days_inactive: int = Query(30, ge=1, description="Días de inactividad"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Obtener clientes inactivos
    
    Args:
        days_inactive: Días de inactividad
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        List: Lista de clientes inactivos
    """
    require_permission("customers:read")(current_user)
    
    customer_service = CustomerService(db)
    inactive_customers = customer_service.get_inactive_customers(days_inactive)
    
    return [CustomerResponse.from_orm(customer) for customer in inactive_customers]

@router.post("/{customer_id}/update-activity")
async def update_customer_activity(
    customer_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Actualizar actividad del cliente
    
    Args:
        customer_id: ID del cliente
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        dict: Mensaje de confirmación
    """
    require_permission("customers:update")(current_user)
    
    customer_service = CustomerService(db)
    customer_service.update_customer_activity(customer_id)
    
    return {"message": "Actividad del cliente actualizada"}

@router.get("/search/quick")
async def quick_search_customers(
    query: str = Query(..., min_length=2, description="Término de búsqueda"),
    limit: int = Query(10, ge=1, le=50, description="Límite de resultados"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Búsqueda rápida de clientes
    
    Args:
        query: Término de búsqueda
        limit: Límite de resultados
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        List: Lista de clientes encontrados
    """
    require_permission("customers:read")(current_user)
    
    customer_service = CustomerService(db)
    search_params = CustomerSearch(query=query, per_page=limit)
    result = customer_service.search_customers(search_params)
    
    return [
        {
            "id": customer.id,
            "full_name": customer.full_name,
            "phone_number": customer.phone_number,
            "email": customer.email,
            "is_verified": customer.is_verified,
            "is_active": customer.is_active
        }
        for customer in result["customers"]
    ]

@router.get("/health")
async def customers_health_check() -> Any:
    """
    Health check para el módulo de clientes
    
    Returns:
        dict: Estado del módulo
    """
    return {
        "status": "healthy",
        "module": "customers",
        "endpoints": [
            "create", "list", "get", "update", "verify", "activate",
            "deactivate", "delete", "packages", "notifications", "stats",
            "export", "top", "inactive", "search"
        ]
    }
