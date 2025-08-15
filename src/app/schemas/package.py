"""
Package Schemas
==============

Esquemas Pydantic para validación de datos de paquetes.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, validator
from decimal import Decimal
from enum import Enum

class PackageType(str, Enum):
    """Tipos de paquete disponibles"""
    NORMAL = "normal"
    EXTRA_DIMENSIONED = "extra_dimensioned"

class PackageStatus(str, Enum):
    """Estados de paquete disponibles"""
    ANNOUNCED = "announced"
    RECEIVED = "received"
    DELIVERED = "delivered"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

class PackageCreate(BaseModel):
    """Esquema para crear un nuevo paquete"""
    customer_id: int = Field(..., description="ID del cliente")
    description: str = Field(..., min_length=10, max_length=500, description="Descripción del paquete")
    package_type: PackageType = Field(default=PackageType.NORMAL, description="Tipo de paquete")
    weight_kg: Optional[float] = Field(None, ge=0, le=100, description="Peso en kilogramos")
    length_cm: Optional[float] = Field(None, ge=0, le=200, description="Largo en centímetros")
    width_cm: Optional[float] = Field(None, ge=0, le=200, description="Ancho en centímetros")
    height_cm: Optional[float] = Field(None, ge=0, le=200, description="Alto en centímetros")
    is_urgent: bool = Field(default=False, description="Paquete urgente")
    customer_notes: Optional[str] = Field(None, max_length=1000, description="Notas del cliente")

    @validator('description')
    def validate_description(cls, v):
        # Remove extra whitespace
        cleaned = ' '.join(v.split())
        if len(cleaned) < 10:
            raise ValueError('La descripción debe tener al menos 10 caracteres')
        return cleaned

    @validator('customer_notes')
    def validate_notes(cls, v):
        if v is not None:
            return ' '.join(v.split())
        return v

class PackageAnnounce(BaseModel):
    """Esquema para anunciar un paquete (incluye datos del cliente)"""
    # Customer information
    customer_phone: str = Field(..., description="Número de teléfono del cliente")
    customer_name: str = Field(..., min_length=2, max_length=100, description="Nombre completo del cliente")
    customer_email: Optional[str] = Field(None, description="Correo electrónico del cliente")
    customer_address: Optional[str] = Field(None, max_length=500, description="Dirección del cliente")
    customer_city: Optional[str] = Field(None, max_length=100, description="Ciudad del cliente")
    
    # Package information
    description: str = Field(..., min_length=10, max_length=500, description="Descripción del paquete")
    package_type: PackageType = Field(default=PackageType.NORMAL, description="Tipo de paquete")
    weight_kg: Optional[float] = Field(None, ge=0, le=100, description="Peso en kilogramos")
    length_cm: Optional[float] = Field(None, ge=0, le=200, description="Largo en centímetros")
    width_cm: Optional[float] = Field(None, ge=0, le=200, description="Ancho en centímetros")
    height_cm: Optional[float] = Field(None, ge=0, le=200, description="Alto en centímetros")
    is_urgent: bool = Field(default=False, description="Paquete urgente")
    customer_notes: Optional[str] = Field(None, max_length=1000, description="Notas del cliente")

    @validator('customer_phone')
    def validate_phone_number(cls, v):
        import re
        digits_only = re.sub(r'\D', '', v)
        
        if len(digits_only) == 10:
            if digits_only.startswith(('2', '3', '4', '5', '6', '7', '8')):
                return f"+57 {digits_only[:3]} {digits_only[3:6]} {digits_only[6:]}"
        elif len(digits_only) == 11:
            if digits_only.startswith('3'):
                return f"+57 {digits_only[1:4]} {digits_only[4:7]} {digits_only[7:]}"
        
        raise ValueError('Número de teléfono inválido. Use formato colombiano')

    @validator('customer_name')
    def validate_customer_name(cls, v):
        cleaned = ' '.join(v.split()).title()
        if len(cleaned) < 2:
            raise ValueError('El nombre debe tener al menos 2 caracteres')
        return cleaned

    @validator('description')
    def validate_description(cls, v):
        cleaned = ' '.join(v.split())
        if len(cleaned) < 10:
            raise ValueError('La descripción debe tener al menos 10 caracteres')
        return cleaned

class PackageUpdate(BaseModel):
    """Esquema para actualizar un paquete existente"""
    description: Optional[str] = Field(None, min_length=10, max_length=500)
    package_type: Optional[PackageType] = None
    weight_kg: Optional[float] = Field(None, ge=0, le=100)
    length_cm: Optional[float] = Field(None, ge=0, le=200)
    width_cm: Optional[float] = Field(None, ge=0, le=200)
    height_cm: Optional[float] = Field(None, ge=0, le=200)
    is_urgent: Optional[bool] = None
    customer_notes: Optional[str] = Field(None, max_length=1000)
    status: Optional[PackageStatus] = None

    @validator('description')
    def validate_description(cls, v):
        if v is not None:
            cleaned = ' '.join(v.split())
            if len(cleaned) < 10:
                raise ValueError('La descripción debe tener al menos 10 caracteres')
            return cleaned
        return v

class PackageReceive(BaseModel):
    """Esquema para recibir un paquete"""
    notes: Optional[str] = Field(None, max_length=1000, description="Notas de recepción")
    received_by: Optional[str] = Field(None, max_length=100, description="Recibido por")

class PackageResponse(BaseModel):
    """Esquema para respuesta de paquete"""
    id: int = Field(..., description="ID único del paquete")
    tracking_number: str = Field(..., description="Número de tracking")
    customer_id: int = Field(..., description="ID del cliente")
    description: str = Field(..., description="Descripción del paquete")
    package_type: PackageType = Field(..., description="Tipo de paquete")
    status: PackageStatus = Field(..., description="Estado del paquete")
    weight_kg: Optional[float] = Field(None, description="Peso en kilogramos")
    length_cm: Optional[float] = Field(None, description="Largo en centímetros")
    width_cm: Optional[float] = Field(None, description="Ancho en centímetros")
    height_cm: Optional[float] = Field(None, description="Alto en centímetros")
    is_urgent: bool = Field(..., description="Paquete urgente")
    customer_notes: Optional[str] = Field(None, description="Notas del cliente")
    base_cost: Decimal = Field(..., description="Costo base")
    storage_cost: Decimal = Field(..., description="Costo de bodegaje")
    total_cost: Decimal = Field(..., description="Costo total")
    announced_at: datetime = Field(..., description="Fecha de anuncio")
    received_at: Optional[datetime] = Field(None, description="Fecha de recepción")
    delivered_at: Optional[datetime] = Field(None, description="Fecha de entrega")
    expires_at: datetime = Field(..., description="Fecha de expiración")
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: datetime = Field(..., description="Fecha de última actualización")
    
    # Related data
    customer: Optional['CustomerResponse'] = Field(None, description="Información del cliente")
    files: List['FileUploadResponse'] = Field(default=[], description="Archivos adjuntos")
    notifications: List['NotificationResponse'] = Field(default=[], description="Notificaciones")
    deliveries: List['DeliveryResponse'] = Field(default=[], description="Entregas")

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: float(v)
        }

class PackageSearch(BaseModel):
    """Esquema para búsqueda de paquetes"""
    query: Optional[str] = Field(None, description="Término de búsqueda")
    tracking_number: Optional[str] = Field(None, description="Número de tracking específico")
    customer_phone: Optional[str] = Field(None, description="Teléfono del cliente")
    status: Optional[PackageStatus] = Field(None, description="Estado del paquete")
    package_type: Optional[PackageType] = Field(None, description="Tipo de paquete")
    is_urgent: Optional[bool] = Field(None, description="Paquete urgente")
    date_from: Optional[datetime] = Field(None, description="Fecha desde")
    date_to: Optional[datetime] = Field(None, description="Fecha hasta")
    page: int = Field(default=1, ge=1, description="Número de página")
    per_page: int = Field(default=20, ge=1, le=100, description="Elementos por página")

class PackageListResponse(BaseModel):
    """Esquema para lista de paquetes"""
    packages: List[PackageResponse] = Field(..., description="Lista de paquetes")
    total: int = Field(..., description="Total de paquetes")
    page: int = Field(..., description="Página actual")
    per_page: int = Field(..., description="Paquetes por página")
    total_pages: int = Field(..., description="Total de páginas")

class PackageStats(BaseModel):
    """Esquema para estadísticas de paquetes"""
    total_packages: int = Field(..., description="Total de paquetes")
    announced_count: int = Field(..., description="Paquetes anunciados")
    received_count: int = Field(..., description="Paquetes recibidos")
    delivered_count: int = Field(..., description="Paquetes entregados")
    expired_count: int = Field(..., description="Paquetes expirados")
    urgent_count: int = Field(..., description="Paquetes urgentes")
    packages_today: int = Field(..., description="Paquetes anunciados hoy")
    revenue_today: Decimal = Field(..., description="Ingresos de hoy")
    revenue_this_week: Decimal = Field(..., description="Ingresos de esta semana")
    revenue_this_month: Decimal = Field(..., description="Ingresos de este mes")
    average_delivery_time: Optional[float] = Field(None, description="Tiempo promedio de entrega (días)")
    packages_by_type: dict = Field(..., description="Paquetes por tipo")
    packages_by_status: dict = Field(..., description="Paquetes por estado")

    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }

class PackageTracking(BaseModel):
    """Esquema para seguimiento de paquete"""
    tracking_number: str = Field(..., description="Número de tracking")
    status: PackageStatus = Field(..., description="Estado actual")
    description: str = Field(..., description="Descripción del paquete")
    customer_name: str = Field(..., description="Nombre del cliente")
    customer_phone: str = Field(..., description="Teléfono del cliente")
    total_cost: Decimal = Field(..., description="Costo total")
    announced_at: datetime = Field(..., description="Fecha de anuncio")
    received_at: Optional[datetime] = Field(None, description="Fecha de recepción")
    delivered_at: Optional[datetime] = Field(None, description="Fecha de entrega")
    expires_at: datetime = Field(..., description="Fecha de expiración")
    timeline: List[dict] = Field(default=[], description="Historial de eventos")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: float(v)
        }

class PackageBulkAction(BaseModel):
    """Esquema para acciones masivas en paquetes"""
    package_ids: List[int] = Field(..., description="IDs de paquetes")
    action: str = Field(..., regex="^(receive|deliver|cancel|delete)$", description="Acción a realizar")
    notes: Optional[str] = Field(None, max_length=1000, description="Notas adicionales")

class PackageExport(BaseModel):
    """Esquema para exportación de paquetes"""
    format: str = Field(default="csv", regex="^(csv|excel|json)$", description="Formato de exportación")
    include_files: bool = Field(default=False, description="Incluir información de archivos")
    include_notifications: bool = Field(default=False, description="Incluir información de notificaciones")
    date_from: Optional[datetime] = Field(None, description="Fecha desde")
    date_to: Optional[datetime] = Field(None, description="Fecha hasta")
    status: Optional[PackageStatus] = Field(None, description="Filtrar por estado")
    package_type: Optional[PackageType] = Field(None, description="Filtrar por tipo")
