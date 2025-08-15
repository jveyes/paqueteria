"""
Notification Schemas
===================

Esquemas Pydantic para validación de datos de notificaciones.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, validator
from enum import Enum

class NotificationType(str, Enum):
    """Tipos de notificación disponibles"""
    SMS = "sms"
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    PUSH = "push"

class NotificationStatus(str, Enum):
    """Estados de notificación disponibles"""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    CANCELLED = "cancelled"

class NotificationCreate(BaseModel):
    """Esquema para crear una nueva notificación"""
    notification_type: NotificationType = Field(..., description="Tipo de notificación")
    customer_id: int = Field(..., description="ID del cliente")
    package_id: Optional[int] = Field(None, description="ID del paquete (opcional)")
    recipient: str = Field(..., description="Destinatario (teléfono, email, etc.)")
    message: str = Field(..., min_length=1, max_length=1000, description="Mensaje a enviar")
    scheduled_at: Optional[datetime] = Field(None, description="Fecha programada de envío")
    priority: int = Field(default=1, ge=1, le=5, description="Prioridad (1-5)")
    retry_count: int = Field(default=0, ge=0, le=3, description="Número de reintentos")

    @validator('message')
    def validate_message(cls, v):
        if not v.strip():
            raise ValueError('El mensaje no puede estar vacío')
        return v.strip()

    @validator('recipient')
    def validate_recipient(cls, v, values):
        notification_type = values.get('notification_type')
        
        if notification_type == NotificationType.SMS:
            # Validar formato de teléfono colombiano
            import re
            digits_only = re.sub(r'\D', '', v)
            if len(digits_only) not in [10, 11]:
                raise ValueError('Número de teléfono inválido para SMS')
        elif notification_type == NotificationType.EMAIL:
            # Validar formato de email
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, v):
                raise ValueError('Formato de email inválido')
        elif notification_type == NotificationType.WHATSAPP:
            # Validar formato de teléfono para WhatsApp
            import re
            digits_only = re.sub(r'\D', '', v)
            if len(digits_only) not in [10, 11]:
                raise ValueError('Número de teléfono inválido para WhatsApp')
        
        return v

class NotificationUpdate(BaseModel):
    """Esquema para actualizar una notificación existente"""
    status: Optional[NotificationStatus] = None
    external_id: Optional[str] = Field(None, description="ID externo del servicio")
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    error_message: Optional[str] = Field(None, max_length=500, description="Mensaje de error")
    retry_count: Optional[int] = Field(None, ge=0, le=3)

class NotificationResponse(BaseModel):
    """Esquema para respuesta de notificación"""
    id: int = Field(..., description="ID único de la notificación")
    notification_type: NotificationType = Field(..., description="Tipo de notificación")
    status: NotificationStatus = Field(..., description="Estado de la notificación")
    customer_id: int = Field(..., description="ID del cliente")
    package_id: Optional[int] = Field(None, description="ID del paquete")
    recipient: str = Field(..., description="Destinatario")
    message: str = Field(..., description="Mensaje enviado")
    external_id: Optional[str] = Field(None, description="ID externo del servicio")
    priority: int = Field(..., description="Prioridad")
    retry_count: int = Field(..., description="Número de reintentos")
    scheduled_at: Optional[datetime] = Field(None, description="Fecha programada")
    sent_at: Optional[datetime] = Field(None, description="Fecha de envío")
    delivered_at: Optional[datetime] = Field(None, description="Fecha de entrega")
    error_message: Optional[str] = Field(None, description="Mensaje de error")
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: datetime = Field(..., description="Fecha de última actualización")

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class NotificationSearch(BaseModel):
    """Esquema para búsqueda de notificaciones"""
    notification_type: Optional[NotificationType] = Field(None, description="Tipo de notificación")
    status: Optional[NotificationStatus] = Field(None, description="Estado de la notificación")
    customer_id: Optional[int] = Field(None, description="ID del cliente")
    package_id: Optional[int] = Field(None, description="ID del paquete")
    recipient: Optional[str] = Field(None, description="Destinatario")
    date_from: Optional[datetime] = Field(None, description="Fecha desde")
    date_to: Optional[datetime] = Field(None, description="Fecha hasta")
    page: int = Field(default=1, ge=1, description="Número de página")
    per_page: int = Field(default=20, ge=1, le=100, description="Elementos por página")

class NotificationListResponse(BaseModel):
    """Esquema para lista de notificaciones"""
    notifications: List[NotificationResponse] = Field(..., description="Lista de notificaciones")
    total: int = Field(..., description="Total de notificaciones")
    page: int = Field(..., description="Página actual")
    per_page: int = Field(..., description="Notificaciones por página")
    total_pages: int = Field(..., description="Total de páginas")

class NotificationStats(BaseModel):
    """Esquema para estadísticas de notificaciones"""
    total_notifications: int = Field(..., description="Total de notificaciones")
    pending_count: int = Field(..., description="Notificaciones pendientes")
    sent_count: int = Field(..., description="Notificaciones enviadas")
    delivered_count: int = Field(..., description="Notificaciones entregadas")
    failed_count: int = Field(..., description="Notificaciones fallidas")
    notifications_today: int = Field(..., description="Notificaciones de hoy")
    notifications_this_week: int = Field(..., description="Notificaciones de esta semana")
    notifications_this_month: int = Field(..., description="Notificaciones de este mes")
    notifications_by_type: dict = Field(..., description="Notificaciones por tipo")
    notifications_by_status: dict = Field(..., description="Notificaciones por estado")
    success_rate: float = Field(..., description="Tasa de éxito (%)")
    average_delivery_time: Optional[float] = Field(None, description="Tiempo promedio de entrega (minutos)")

class NotificationBulkSend(BaseModel):
    """Esquema para envío masivo de notificaciones"""
    notification_type: NotificationType = Field(..., description="Tipo de notificación")
    customer_ids: List[int] = Field(..., description="IDs de clientes")
    message_template: str = Field(..., description="Plantilla de mensaje")
    variables: Optional[dict] = Field(None, description="Variables para la plantilla")
    scheduled_at: Optional[datetime] = Field(None, description="Fecha programada")
    priority: int = Field(default=1, ge=1, le=5, description="Prioridad")

    @validator('message_template')
    def validate_template(cls, v):
        if not v.strip():
            raise ValueError('La plantilla de mensaje no puede estar vacía')
        return v.strip()

class NotificationRetry(BaseModel):
    """Esquema para reintentar notificación fallida"""
    notification_id: int = Field(..., description="ID de la notificación")
    force: bool = Field(default=False, description="Forzar reintento")

class NotificationTemplate(BaseModel):
    """Esquema para plantillas de notificación"""
    name: str = Field(..., min_length=1, max_length=100, description="Nombre de la plantilla")
    notification_type: NotificationType = Field(..., description="Tipo de notificación")
    subject: Optional[str] = Field(None, max_length=200, description="Asunto (para email)")
    message: str = Field(..., min_length=1, max_length=1000, description="Plantilla de mensaje")
    variables: List[str] = Field(default=[], description="Variables disponibles")
    is_active: bool = Field(default=True, description="Plantilla activa")
    description: Optional[str] = Field(None, max_length=500, description="Descripción")

    @validator('message')
    def validate_message(cls, v):
        if not v.strip():
            raise ValueError('La plantilla de mensaje no puede estar vacía')
        return v.strip()

class NotificationTemplateResponse(BaseModel):
    """Esquema para respuesta de plantilla de notificación"""
    id: int = Field(..., description="ID único de la plantilla")
    name: str = Field(..., description="Nombre de la plantilla")
    notification_type: NotificationType = Field(..., description="Tipo de notificación")
    subject: Optional[str] = Field(None, description="Asunto")
    message: str = Field(..., description="Plantilla de mensaje")
    variables: List[str] = Field(..., description="Variables disponibles")
    is_active: bool = Field(..., description="Plantilla activa")
    description: Optional[str] = Field(None, description="Descripción")
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: datetime = Field(..., description="Fecha de última actualización")

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
