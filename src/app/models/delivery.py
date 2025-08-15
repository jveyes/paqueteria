"""
Modelo Delivery - Entregas de paquetes
====================================

Modelo para gestionar las entregas de paquetes.
"""

from datetime import datetime
from decimal import Decimal
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Numeric, ForeignKey, Index, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from ..core.database import Base


class DeliveryStatus(enum.Enum):
    """Estados de entrega"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class PaymentMethod(enum.Enum):
    """Métodos de pago"""
    CASH = "cash"
    CARD = "card"
    TRANSFER = "transfer"
    DIGITAL_WALLET = "digital_wallet"


class Delivery(Base):
    """
    Modelo para entregas de paquetes
    """
    
    __tablename__ = "deliveries"
    
    # =============================================================================
    # CAMPOS PRINCIPALES
    # =============================================================================
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    delivery_number = Column(String(20), unique=True, index=True, nullable=False)
    
    # =============================================================================
    # RELACIONES
    # =============================================================================
    
    package_id = Column(Integer, ForeignKey("packages.id"), nullable=False)
    package = relationship("Package", back_populates="deliveries")
    
    # =============================================================================
    # ESTADO Y TIPO
    # =============================================================================
    
    status = Column(Enum(DeliveryStatus), default=DeliveryStatus.PENDING, nullable=False)
    payment_method = Column(Enum(PaymentMethod), nullable=True)
    
    # =============================================================================
    # COSTOS
    # =============================================================================
    
    amount_paid = Column(Numeric(10, 2), nullable=False)
    change_given = Column(Numeric(10, 2), default=0, nullable=False)
    
    # =============================================================================
    # INFORMACIÓN DE ENTREGA
    # =============================================================================
    
    delivered_by = Column(String(100), nullable=True)  # Nombre del empleado
    recipient_name = Column(String(100), nullable=True)  # Nombre del receptor
    recipient_id = Column(String(20), nullable=True)  # Documento del receptor
    
    # =============================================================================
    # FECHAS
    # =============================================================================
    
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # =============================================================================
    # NOTAS Y COMENTARIOS
    # =============================================================================
    
    notes = Column(Text, nullable=True)  # Notas del empleado
    customer_feedback = Column(Text, nullable=True)  # Feedback del cliente
    
    # =============================================================================
    # METADATA
    # =============================================================================
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # =============================================================================
    # ÍNDICES
    # =============================================================================
    
    __table_args__ = (
        Index('idx_delivery_number', 'delivery_number'),
        Index('idx_delivery_package', 'package_id'),
        Index('idx_delivery_status', 'status'),
        Index('idx_delivery_scheduled_at', 'scheduled_at'),
        Index('idx_delivery_completed_at', 'completed_at'),
    )
    
    # =============================================================================
    # MÉTODOS
    # =============================================================================
    
    def generate_delivery_number(self) -> str:
        """
        Generar número de entrega único
        
        Returns:
            str: Número de entrega generado
        """
        import random
        import string
        
        # Formato: ENT-YYYYMMDD-XXXXX
        from datetime import datetime
        date_part = datetime.now().strftime("%Y%m%d")
        random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        
        return f"ENT-{date_part}-{random_part}"
    
    def start_delivery(self, delivered_by: str) -> None:
        """
        Iniciar entrega
        
        Args:
            delivered_by: Nombre del empleado
        """
        self.status = DeliveryStatus.IN_PROGRESS
        self.started_at = datetime.utcnow()
        self.delivered_by = delivered_by
    
    def complete_delivery(
        self, 
        recipient_name: str = None,
        recipient_id: str = None,
        payment_method: PaymentMethod = None,
        amount_paid: Decimal = None,
        notes: str = None
    ) -> None:
        """
        Completar entrega
        
        Args:
            recipient_name: Nombre del receptor
            recipient_id: Documento del receptor
            payment_method: Método de pago
            amount_paid: Monto pagado
            notes: Notas adicionales
        """
        self.status = DeliveryStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        
        if recipient_name:
            self.recipient_name = recipient_name
        if recipient_id:
            self.recipient_id = recipient_id
        if payment_method:
            self.payment_method = payment_method
        if amount_paid:
            self.amount_paid = amount_paid
            # Calcular cambio
            if amount_paid > self.package.total_cost:
                self.change_given = amount_paid - self.package.total_cost
        if notes:
            self.notes = notes
        
        # Marcar paquete como entregado
        self.package.mark_as_delivered()
    
    def cancel_delivery(self, reason: str = None) -> None:
        """
        Cancelar entrega
        
        Args:
            reason: Razón de la cancelación
        """
        self.status = DeliveryStatus.CANCELLED
        if reason:
            self.notes = f"Cancelado: {reason}"
    
    def fail_delivery(self, reason: str = None) -> None:
        """
        Marcar entrega como fallida
        
        Args:
            reason: Razón del fallo
        """
        self.status = DeliveryStatus.FAILED
        if reason:
            self.notes = f"Falló: {reason}"
    
    def get_duration_minutes(self) -> int:
        """
        Obtener duración de la entrega en minutos
        
        Returns:
            int: Duración en minutos
        """
        if not self.started_at or not self.completed_at:
            return 0
        
        duration = self.completed_at - self.started_at
        return int(duration.total_seconds() / 60)
    
    # =============================================================================
    # REPRESENTACIÓN
    # =============================================================================
    
    def __repr__(self) -> str:
        return f"<Delivery(id={self.id}, number='{self.delivery_number}', status='{self.status.value}')>"
    
    def __str__(self) -> str:
        return f"Entrega {self.delivery_number} - {self.status.value}"
    
    # =============================================================================
    # PROPIEDADES
    # =============================================================================
    
    @property
    def is_pending(self) -> bool:
        """Verificar si está pendiente"""
        return self.status == DeliveryStatus.PENDING
    
    @property
    def is_in_progress(self) -> bool:
        """Verificar si está en progreso"""
        return self.status == DeliveryStatus.IN_PROGRESS
    
    @property
    def is_completed(self) -> bool:
        """Verificar si está completada"""
        return self.status == DeliveryStatus.COMPLETED
    
    @property
    def is_cancelled(self) -> bool:
        """Verificar si está cancelada"""
        return self.status == DeliveryStatus.CANCELLED
    
    @property
    def is_failed(self) -> bool:
        """Verificar si falló"""
        return self.status == DeliveryStatus.FAILED
    
    @property
    def formatted_amount_paid(self) -> str:
        """Monto pagado formateado"""
        return f"${self.amount_paid:,.0f} COP"
    
    @property
    def formatted_change(self) -> str:
        """Cambio formateado"""
        return f"${self.change_given:,.0f} COP"
    
    @property
    def duration_formatted(self) -> str:
        """Duración formateada"""
        minutes = self.get_duration_minutes()
        if minutes < 60:
            return f"{minutes} min"
        else:
            hours = minutes // 60
            remaining_minutes = minutes % 60
            return f"{hours}h {remaining_minutes}min"
