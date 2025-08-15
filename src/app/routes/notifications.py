"""
Notification Routes
==================

Rutas para gestión de notificaciones.
"""

from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.auth import get_current_active_user, require_permission
from ..models.user import User
from ..services.notification_service import NotificationService
from ..schemas.notification import (
    NotificationCreate, NotificationResponse, NotificationSearch,
    NotificationStats, NotificationBulkSend, NotificationRetry,
    NotificationListResponse
)

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])

@router.post("/send-sms")
async def send_sms(
    phone_number: str,
    message: str,
    package_id: Optional[int] = None,
    customer_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Enviar SMS
    
    Args:
        phone_number: Número de teléfono
        message: Mensaje a enviar
        package_id: ID del paquete (opcional)
        customer_id: ID del cliente (opcional)
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        NotificationResponse: Notificación creada
    """
    require_permission("notifications:send")(current_user)
    
    notification_service = NotificationService(db)
    notification = notification_service.send_sms(phone_number, message, package_id, customer_id)
    
    return NotificationResponse.from_orm(notification)

@router.post("/send-email")
async def send_email(
    email: str,
    subject: str,
    message: str,
    package_id: Optional[int] = None,
    customer_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Enviar email
    
    Args:
        email: Dirección de email
        subject: Asunto del email
        message: Contenido del email
        package_id: ID del paquete (opcional)
        customer_id: ID del cliente (opcional)
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        NotificationResponse: Notificación creada
    """
    require_permission("notifications:send")(current_user)
    
    notification_service = NotificationService(db)
    notification = notification_service.send_email(email, subject, message, package_id, customer_id)
    
    return NotificationResponse.from_orm(notification)

@router.post("/send-whatsapp")
async def send_whatsapp(
    phone_number: str,
    message: str,
    package_id: Optional[int] = None,
    customer_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Enviar WhatsApp
    
    Args:
        phone_number: Número de teléfono
        message: Mensaje a enviar
        package_id: ID del paquete (opcional)
        customer_id: ID del cliente (opcional)
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        NotificationResponse: Notificación creada
    """
    require_permission("notifications:send")(current_user)
    
    notification_service = NotificationService(db)
    notification = notification_service.send_whatsapp(phone_number, message, package_id, customer_id)
    
    return NotificationResponse.from_orm(notification)

@router.get("/", response_model=NotificationListResponse)
async def list_notifications(
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(20, ge=1, le=100, description="Elementos por página"),
    notification_type: Optional[str] = Query(None, description="Tipo de notificación"),
    status: Optional[str] = Query(None, description="Estado de la notificación"),
    customer_id: Optional[int] = Query(None, description="ID del cliente"),
    package_id: Optional[int] = Query(None, description="ID del paquete"),
    recipient: Optional[str] = Query(None, description="Destinatario"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Listar notificaciones con filtros
    
    Args:
        page: Número de página
        per_page: Elementos por página
        notification_type: Tipo de notificación
        status: Estado de la notificación
        customer_id: ID del cliente
        package_id: ID del paquete
        recipient: Destinatario
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        NotificationListResponse: Lista de notificaciones
    """
    require_permission("notifications:read")(current_user)
    
    search_params = NotificationSearch(
        notification_type=notification_type,
        status=status,
        customer_id=customer_id,
        package_id=package_id,
        recipient=recipient,
        page=page,
        per_page=per_page
    )
    
    notification_service = NotificationService(db)
    result = notification_service.search_notifications(search_params)
    
    return NotificationListResponse(
        notifications=[NotificationResponse.from_orm(notif) for notif in result["notifications"]],
        total=result["total"],
        page=result["page"],
        per_page=result["per_page"],
        total_pages=result["total_pages"]
    )

@router.get("/{notification_id}", response_model=NotificationResponse)
async def get_notification(
    notification_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Obtener notificación por ID
    
    Args:
        notification_id: ID de la notificación
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        NotificationResponse: Información de la notificación
    """
    require_permission("notifications:read")(current_user)
    
    notification_service = NotificationService(db)
    notification = notification_service.get_notification_by_id(notification_id)
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notificación no encontrada"
        )
    
    return NotificationResponse.from_orm(notification)

@router.post("/{notification_id}/retry")
async def retry_notification(
    notification_id: int,
    force: bool = Query(False, description="Forzar reintento"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Reintentar notificación fallida
    
    Args:
        notification_id: ID de la notificación
        force: Forzar reintento
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        dict: Resultado del reintento
    """
    require_permission("notifications:retry")(current_user)
    
    notification_service = NotificationService(db)
    success = notification_service.retry_failed_notification(notification_id, force)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error reintentando notificación"
        )
    
    return {"message": "Notificación reintentada exitosamente"}

@router.post("/bulk-send")
async def send_bulk_notifications(
    bulk_data: NotificationBulkSend,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Enviar notificaciones masivas
    
    Args:
        bulk_data: Datos para envío masivo
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        dict: Resultado del envío masivo
    """
    require_permission("notifications:bulk_send")(current_user)
    
    notification_service = NotificationService(db)
    return notification_service.send_bulk_notifications(bulk_data)

@router.get("/stats/overview", response_model=NotificationStats)
async def get_notification_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Obtener estadísticas de notificaciones
    
    Args:
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        NotificationStats: Estadísticas de notificaciones
    """
    require_permission("notifications:read")(current_user)
    
    notification_service = NotificationService(db)
    return notification_service.get_notification_stats()

@router.post("/process-scheduled")
async def process_scheduled_notifications(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Procesar notificaciones programadas
    
    Args:
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        dict: Resultado del procesamiento
    """
    require_permission("notifications:process")(current_user)
    
    notification_service = NotificationService(db)
    processed_count = notification_service.process_scheduled_notifications()
    
    return {
        "message": f"Procesadas {processed_count} notificaciones programadas",
        "processed_count": processed_count
    }

@router.post("/cleanup")
async def cleanup_old_notifications(
    days: int = Query(90, ge=1, description="Días a mantener"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Limpiar notificaciones antiguas
    
    Args:
        days: Días a mantener
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        dict: Resultado de la limpieza
    """
    require_permission("notifications:cleanup")(current_user)
    
    notification_service = NotificationService(db)
    deleted_count = notification_service.cleanup_old_notifications(days)
    
    return {
        "message": f"Eliminadas {deleted_count} notificaciones antiguas",
        "deleted_count": deleted_count
    }

@router.get("/failed/list")
async def list_failed_notifications(
    limit: int = Query(50, ge=1, le=200, description="Límite de notificaciones"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Listar notificaciones fallidas
    
    Args:
        limit: Límite de notificaciones
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        List: Lista de notificaciones fallidas
    """
    require_permission("notifications:read")(current_user)
    
    notification_service = NotificationService(db)
    search_params = NotificationSearch(status="failed", per_page=limit)
    result = notification_service.search_notifications(search_params)
    
    return [NotificationResponse.from_orm(notif) for notif in result["notifications"]]

@router.get("/pending/list")
async def list_pending_notifications(
    limit: int = Query(50, ge=1, le=200, description="Límite de notificaciones"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Listar notificaciones pendientes
    
    Args:
        limit: Límite de notificaciones
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        List: Lista de notificaciones pendientes
    """
    require_permission("notifications:read")(current_user)
    
    notification_service = NotificationService(db)
    search_params = NotificationSearch(status="pending", per_page=limit)
    result = notification_service.search_notifications(search_params)
    
    return [NotificationResponse.from_orm(notif) for notif in result["notifications"]]

@router.get("/count/unread")
async def get_unread_notifications_count(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Obtener conteo de notificaciones no leídas
    
    Args:
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        dict: Conteo de notificaciones
    """
    require_permission("notifications:read")(current_user)
    
    notification_service = NotificationService(db)
    search_params = NotificationSearch(status="pending", per_page=1000)
    result = notification_service.search_notifications(search_params)
    
    return {
        "count": result["total"],
        "notifications": [
            {
                "id": notif.id,
                "type": notif.notification_type.value,
                "recipient": notif.recipient,
                "created_at": notif.created_at.isoformat()
            }
            for notif in result["notifications"]
        ]
    }

@router.get("/types/sms/stats")
async def get_sms_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Obtener estadísticas de SMS
    
    Args:
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        dict: Estadísticas de SMS
    """
    require_permission("notifications:read")(current_user)
    
    notification_service = NotificationService(db)
    search_params = NotificationSearch(notification_type="sms", per_page=1000)
    result = notification_service.search_notifications(search_params)
    
    total_sms = result["total"]
    sent_sms = len([n for n in result["notifications"] if n.status.value == "sent"])
    failed_sms = len([n for n in result["notifications"] if n.status.value == "failed"])
    
    success_rate = (sent_sms / total_sms * 100) if total_sms > 0 else 0
    
    return {
        "total_sms": total_sms,
        "sent_sms": sent_sms,
        "failed_sms": failed_sms,
        "success_rate": round(success_rate, 2)
    }

@router.get("/health")
async def notifications_health_check() -> Any:
    """
    Health check para el módulo de notificaciones
    
    Returns:
        dict: Estado del módulo
    """
    return {
        "status": "healthy",
        "module": "notifications",
        "endpoints": [
            "send-sms", "send-email", "send-whatsapp", "list", "get",
            "retry", "bulk-send", "stats", "process-scheduled", "cleanup",
            "failed", "pending", "count", "sms-stats"
        ]
    }
