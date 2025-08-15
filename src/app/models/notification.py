"""
Modelo Notification - Notificaciones del sistema
==============================================

Modelo para gestionar notificaciones SMS, WhatsApp y email.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Index, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from ..core.database import Base


class NotificationType(enum.Enum):
    """Tipos de notificación"""
    SMS = "sms"
    WHATSAPP = "whatsapp"
    EMAIL = "email"


class NotificationStatus(enum.Enum):
    """Estados de notificación"""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    DELIVERED = "delivered"


class Notification(Base):
    """
    Modelo para notificaciones del sistema
    """
    
    __tablename__ = "notifications"
    
    # =============================================================================
    # CAMPOS PRINCIPALES
    # =============================================================================
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    notification_type = Column(Enum(NotificationType), nullable=False)
    status = Column(Enum(NotificationStatus), default=NotificationStatus.PENDING, nullable=False)
    
    # =============================================================================
    # RELACIONES
    # =============================================================================
    
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    customer = relationship("Customer", back_populates="notifications")
    
    package_id = Column(Integer, ForeignKey("packages.id"), nullable=True)
    package = relationship("Package", back_populates="notifications")
    
    # =============================================================================
    # CONTENIDO
    # =============================================================================
    
    recipient = Column(String(100), nullable=False)  # Teléfono, email, etc.
    subject = Column(String(200), nullable=True)  # Para emails
    message = Column(Text, nullable=False)
    template_name = Column(String(100), nullable=True)  # Nombre del template usado
    
    # =============================================================================
    # METADATA
    # =============================================================================
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    
    # =============================================================================
    # RESPUESTA DEL SERVICIO
    # =============================================================================
    
    external_id = Column(String(100), nullable=True)  # ID del servicio externo
    error_message = Column(Text, nullable=True)  # Mensaje de error si falló
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    
    # =============================================================================
    # ÍNDICES
    # =============================================================================
    
    __table_args__ = (
        Index('idx_notification_customer', 'customer_id'),
        Index('idx_notification_package', 'package_id'),
        Index('idx_notification_status', 'status'),
        Index('idx_notification_type', 'notification_type'),
        Index('idx_notification_created_at', 'created_at'),
        Index('idx_notification_external_id', 'external_id'),
    )
    
    # =============================================================================
    # MÉTODOS
    # =============================================================================
    
    def mark_as_sent(self, external_id: str = None) -> None:
        """
        Marcar notificación como enviada
        
        Args:
            external_id: ID del servicio externo
        """
        self.status = NotificationStatus.SENT
        self.sent_at = datetime.utcnow()
        if external_id:
            self.external_id = external_id
    
    def mark_as_delivered(self) -> None:
        """
        Marcar notificación como entregada
        """
        self.status = NotificationStatus.DELIVERED
        self.delivered_at = datetime.utcnow()
    
    def mark_as_failed(self, error_message: str) -> None:
        """
        Marcar notificación como fallida
        
        Args:
            error_message: Mensaje de error
        """
        self.status = NotificationStatus.FAILED
        self.error_message = error_message
        self.retry_count += 1
    
    def can_retry(self) -> bool:
        """
        Verificar si se puede reintentar
        
        Returns:
            bool: True si se puede reintentar
        """
        return self.retry_count < self.max_retries and self.status == NotificationStatus.FAILED
    
    def reset_for_retry(self) -> None:
        """
        Resetear para reintento
        """
        self.status = NotificationStatus.PENDING
        self.error_message = None
    
    # =============================================================================
    # REPRESENTACIÓN
    # =============================================================================
    
    def __repr__(self) -> str:
        return f"<Notification(id={self.id}, type='{self.notification_type.value}', status='{self.status.value}')>"
    
    def __str__(self) -> str:
        return f"Notificación {self.notification_type.value} - {self.status.value}"
    
    # =============================================================================
    # PROPIEDADES
    # =============================================================================
    
    @property
    def is_sent(self) -> bool:
        """Verificar si fue enviada"""
        return self.status in [NotificationStatus.SENT, NotificationStatus.DELIVERED]
    
    @property
    def is_delivered(self) -> bool:
        """Verificar si fue entregada"""
        return self.status == NotificationStatus.DELIVERED
    
    @property
    def is_failed(self) -> bool:
        """Verificar si falló"""
        return self.status == NotificationStatus.FAILED
    
    @property
    def is_pending(self) -> bool:
        """Verificar si está pendiente"""
        return self.status == NotificationStatus.PENDING
    
    @property
    def short_message(self) -> str:
        """Mensaje corto"""
        if len(self.message) <= 100:
            return self.message
        return self.message[:97] + "..."
