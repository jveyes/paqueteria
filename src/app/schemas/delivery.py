"""
Delivery Schemas
===============

Esquemas Pydantic para validación de datos de entregas.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, validator
from decimal import Decimal
from enum import Enum

class DeliveryStatus(str, Enum):
    """Estados de entrega disponibles"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"

class PaymentMethod(str, Enum):
    """Métodos de pago disponibles"""
    CASH = "cash"
    CARD = "card"
    TRANSFER = "transfer"
    DIGITAL_WALLET = "digital_wallet"

class DeliveryCreate(BaseModel):
    """Esquema para crear una nueva entrega"""
    package_id: int = Field(..., description="ID del paquete")
    recipient_name: str = Field(..., min_length=2, max_length=100, description="Nombre del receptor")
    recipient_id: Optional[str] = Field(None, max_length=50, description="Documento del receptor")
    payment_method: PaymentMethod = Field(..., description="Método de pago")
    amount_paid: Decimal = Field(..., ge=0, description="Monto pagado")
    notes: Optional[str] = Field(None, max_length=1000, description="Notas de entrega")
    delivered_by: Optional[str] = Field(None, max_length=100, description="Entregado por")

    @validator('recipient_name')
    def validate_recipient_name(cls, v):
        cleaned = ' '.join(v.split()).title()
        if len(cleaned) < 2:
            raise ValueError('El nombre del receptor debe tener al menos 2 caracteres')
        return cleaned

    @validator('amount_paid')
    def validate_amount_paid(cls, v):
        if v <= 0:
            raise ValueError('El monto pagado debe ser mayor a 0')
        return v

class DeliveryUpdate(BaseModel):
    """Esquema para actualizar una entrega existente"""
    status: Optional[DeliveryStatus] = None
    recipient_name: Optional[str] = Field(None, min_length=2, max_length=100)
    recipient_id: Optional[str] = Field(None, max_length=50)
    payment_method: Optional[PaymentMethod] = None
    amount_paid: Optional[Decimal] = Field(None, ge=0)
    notes: Optional[str] = Field(None, max_length=1000)
    delivered_by: Optional[str] = Field(None, max_length=100)
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = Field(None, max_length=500)

    @validator('recipient_name')
    def validate_recipient_name(cls, v):
        if v is not None:
            cleaned = ' '.join(v.split()).title()
            if len(cleaned) < 2:
                raise ValueError('El nombre del receptor debe tener al menos 2 caracteres')
            return cleaned
        return v

    @validator('amount_paid')
    def validate_amount_paid(cls, v):
        if v is not None and v <= 0:
            raise ValueError('El monto pagado debe ser mayor a 0')
        return v

class DeliveryResponse(BaseModel):
    """Esquema para respuesta de entrega"""
    id: int = Field(..., description="ID único de la entrega")
    delivery_number: str = Field(..., description="Número de entrega")
    package_id: int = Field(..., description="ID del paquete")
    status: DeliveryStatus = Field(..., description="Estado de la entrega")
    recipient_name: str = Field(..., description="Nombre del receptor")
    recipient_id: Optional[str] = Field(None, description="Documento del receptor")
    payment_method: PaymentMethod = Field(..., description="Método de pago")
    amount_paid: Decimal = Field(..., description="Monto pagado")
    notes: Optional[str] = Field(None, description="Notas de entrega")
    delivered_by: Optional[str] = Field(None, description="Entregado por")
    started_at: Optional[datetime] = Field(None, description="Fecha de inicio")
    completed_at: Optional[datetime] = Field(None, description="Fecha de completado")
    cancelled_at: Optional[datetime] = Field(None, description="Fecha de cancelación")
    cancellation_reason: Optional[str] = Field(None, description="Razón de cancelación")
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: datetime = Field(..., description="Fecha de última actualización")
    
    # Related data
    package: Optional['PackageResponse'] = Field(None, description="Información del paquete")

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: float(v)
        }

class DeliveryStart(BaseModel):
    """Esquema para iniciar una entrega"""
    delivered_by: str = Field(..., min_length=2, max_length=100, description="Nombre de quien entrega")
    notes: Optional[str] = Field(None, max_length=1000, description="Notas adicionales")

class DeliveryComplete(BaseModel):
    """Esquema para completar una entrega"""
    recipient_name: str = Field(..., min_length=2, max_length=100, description="Nombre del receptor")
    recipient_id: Optional[str] = Field(None, max_length=50, description="Documento del receptor")
    payment_method: PaymentMethod = Field(..., description="Método de pago")
    amount_paid: Decimal = Field(..., ge=0, description="Monto pagado")
    notes: Optional[str] = Field(None, max_length=1000, description="Notas de entrega")

    @validator('recipient_name')
    def validate_recipient_name(cls, v):
        cleaned = ' '.join(v.split()).title()
        if len(cleaned) < 2:
            raise ValueError('El nombre del receptor debe tener al menos 2 caracteres')
        return cleaned

    @validator('amount_paid')
    def validate_amount_paid(cls, v):
        if v <= 0:
            raise ValueError('El monto pagado debe ser mayor a 0')
        return v

class DeliveryCancel(BaseModel):
    """Esquema para cancelar una entrega"""
    reason: str = Field(..., min_length=5, max_length=500, description="Razón de cancelación")
    notes: Optional[str] = Field(None, max_length=1000, description="Notas adicionales")

class DeliverySearch(BaseModel):
    """Esquema para búsqueda de entregas"""
    query: Optional[str] = Field(None, description="Término de búsqueda")
    delivery_number: Optional[str] = Field(None, description="Número de entrega específico")
    package_id: Optional[int] = Field(None, description="ID del paquete")
    status: Optional[DeliveryStatus] = Field(None, description="Estado de la entrega")
    payment_method: Optional[PaymentMethod] = Field(None, description="Método de pago")
    recipient_name: Optional[str] = Field(None, description="Nombre del receptor")
    delivered_by: Optional[str] = Field(None, description="Entregado por")
    date_from: Optional[datetime] = Field(None, description="Fecha desde")
    date_to: Optional[datetime] = Field(None, description="Fecha hasta")
    page: int = Field(default=1, ge=1, description="Número de página")
    per_page: int = Field(default=20, ge=1, le=100, description="Elementos por página")

class DeliveryListResponse(BaseModel):
    """Esquema para lista de entregas"""
    deliveries: List[DeliveryResponse] = Field(..., description="Lista de entregas")
    total: int = Field(..., description="Total de entregas")
    page: int = Field(..., description="Página actual")
    per_page: int = Field(..., description="Entregas por página")
    total_pages: int = Field(..., description="Total de páginas")

class DeliveryStats(BaseModel):
    """Esquema para estadísticas de entregas"""
    total_deliveries: int = Field(..., description="Total de entregas")
    pending_count: int = Field(..., description="Entregas pendientes")
    in_progress_count: int = Field(..., description="Entregas en progreso")
    completed_count: int = Field(..., description="Entregas completadas")
    cancelled_count: int = Field(..., description="Entregas canceladas")
    failed_count: int = Field(..., description="Entregas fallidas")
    deliveries_today: int = Field(..., description="Entregas de hoy")
    revenue_today: Decimal = Field(..., description="Ingresos de hoy")
    revenue_this_week: Decimal = Field(..., description="Ingresos de esta semana")
    revenue_this_month: Decimal = Field(..., description="Ingresos de este mes")
    average_delivery_time: Optional[float] = Field(None, description="Tiempo promedio de entrega (horas)")
    deliveries_by_status: dict = Field(..., description="Entregas por estado")
    deliveries_by_payment_method: dict = Field(..., description="Entregas por método de pago")
    success_rate: float = Field(..., description="Tasa de éxito (%)")

    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }

class DeliveryReceipt(BaseModel):
    """Esquema para recibo de entrega"""
    delivery_number: str = Field(..., description="Número de entrega")
    package_tracking: str = Field(..., description="Número de tracking del paquete")
    customer_name: str = Field(..., description="Nombre del cliente")
    customer_phone: str = Field(..., description="Teléfono del cliente")
    recipient_name: str = Field(..., description="Nombre del receptor")
    recipient_id: Optional[str] = Field(None, description="Documento del receptor")
    package_description: str = Field(..., description="Descripción del paquete")
    package_cost: Decimal = Field(..., description="Costo del paquete")
    payment_method: PaymentMethod = Field(..., description="Método de pago")
    amount_paid: Decimal = Field(..., description="Monto pagado")
    change: Decimal = Field(..., description="Cambio")
    delivered_by: str = Field(..., description="Entregado por")
    delivered_at: datetime = Field(..., description="Fecha y hora de entrega")
    notes: Optional[str] = Field(None, description="Notas adicionales")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: float(v)
        }

class DeliveryBulkAction(BaseModel):
    """Esquema para acciones masivas en entregas"""
    delivery_ids: List[int] = Field(..., description="IDs de entregas")
    action: str = Field(..., pattern="^(start|complete|cancel)$", description="Acción a realizar")
    notes: Optional[str] = Field(None, max_length=1000, description="Notas adicionales")

class DeliveryExport(BaseModel):
    """Esquema para exportación de entregas"""
    format: str = Field(default="csv", pattern="^(csv|excel|json|pdf)$", description="Formato de exportación")
    include_receipts: bool = Field(default=False, description="Incluir recibos")
    date_from: Optional[datetime] = Field(None, description="Fecha desde")
    date_to: Optional[datetime] = Field(None, description="Fecha hasta")
    status: Optional[DeliveryStatus] = Field(None, description="Filtrar por estado")
    payment_method: Optional[PaymentMethod] = Field(None, description="Filtrar por método de pago")
