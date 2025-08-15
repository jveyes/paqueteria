"""
Modelo Customer - Clientes del sistema
=====================================

Modelo para gestionar clientes que anuncian paquetes.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from ..core.database import Base


class Customer(Base):
    """
    Modelo para clientes del sistema de paquetería
    """
    
    __tablename__ = "customers"
    
    # =============================================================================
    # CAMPOS PRINCIPALES
    # =============================================================================
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    phone_number = Column(String(20), unique=True, index=True, nullable=False)
    full_name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=True)
    
    # =============================================================================
    # INFORMACIÓN DE CONTACTO
    # =============================================================================
    
    address = Column(Text, nullable=True)
    city = Column(String(50), nullable=True)
    department = Column(String(50), nullable=True)
    country = Column(String(50), default="Colombia", nullable=False)
    
    # =============================================================================
    # PREFERENCIAS
    # =============================================================================
    
    preferred_notification_method = Column(String(20), default="sms", nullable=False)  # sms, whatsapp, email
    language = Column(String(10), default="es", nullable=False)  # es, en
    
    # =============================================================================
    # ESTADO
    # =============================================================================
    
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    verification_code = Column(String(10), nullable=True)
    verification_expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # =============================================================================
    # METADATA
    # =============================================================================
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_activity = Column(DateTime(timezone=True), nullable=True)
    
    # =============================================================================
    # RELACIONES
    # =============================================================================
    
    # Relación con paquetes (un cliente puede tener muchos paquetes)
    packages = relationship("Package", back_populates="customer", cascade="all, delete-orphan")
    
    # Relación con notificaciones
    notifications = relationship("Notification", back_populates="customer", cascade="all, delete-orphan")
    
    # =============================================================================
    # ÍNDICES
    # =============================================================================
    
    __table_args__ = (
        Index('idx_customer_phone_active', 'phone_number', 'is_active'),
        Index('idx_customer_email_active', 'email', 'is_active'),
        Index('idx_customer_created_at', 'created_at'),
    )
    
    # =============================================================================
    # MÉTODOS
    # =============================================================================
    
    def generate_verification_code(self) -> str:
        """
        Generar código de verificación
        
        Returns:
            str: Código de verificación de 6 dígitos
        """
        import random
        import string
        
        # Generar código de 6 dígitos
        code = ''.join(random.choices(string.digits, k=6))
        self.verification_code = code
        
        # Establecer expiración (15 minutos)
        from datetime import timedelta
        self.verification_expires_at = datetime.utcnow() + timedelta(minutes=15)
        
        return code
    
    def verify_code(self, code: str) -> bool:
        """
        Verificar código de verificación
        
        Args:
            code: Código a verificar
            
        Returns:
            bool: True si el código es válido
        """
        if not self.verification_code or not self.verification_expires_at:
            return False
        
        if datetime.utcnow() > self.verification_expires_at:
            return False
        
        if self.verification_code == code:
            self.is_verified = True
            self.verification_code = None
            self.verification_expires_at = None
            return True
        
        return False
    
    def update_last_activity(self) -> None:
        """
        Actualizar timestamp de última actividad
        """
        self.last_activity = datetime.utcnow()
    
    def get_packages_count(self) -> int:
        """
        Obtener número total de paquetes del cliente
        
        Returns:
            int: Número de paquetes
        """
        return len(self.packages) if self.packages else 0
    
    def get_active_packages_count(self) -> int:
        """
        Obtener número de paquetes activos del cliente
        
        Returns:
            int: Número de paquetes activos
        """
        if not self.packages:
            return 0
        
        return len([p for p in self.packages if p.status in ['announced', 'received']])
    
    # =============================================================================
    # REPRESENTACIÓN
    # =============================================================================
    
    def __repr__(self) -> str:
        return f"<Customer(id={self.id}, phone='{self.phone_number}', name='{self.full_name}')>"
    
    def __str__(self) -> str:
        return f"{self.full_name} ({self.phone_number})"
    
    # =============================================================================
    # PROPIEDADES
    # =============================================================================
    
    @property
    def display_name(self) -> str:
        """Nombre para mostrar"""
        return self.full_name
    
    @property
    def formatted_phone(self) -> str:
        """Número de teléfono formateado"""
        if not self.phone_number:
            return ""
        
        # Formato colombiano: +57 300 123 4567
        phone = self.phone_number.replace(" ", "").replace("-", "").replace("+", "")
        
        if phone.startswith("57"):
            phone = phone[2:]
        
        if len(phone) == 10:
            return f"+57 {phone[:3]} {phone[3:6]} {phone[6:]}"
        
        return self.phone_number
    
    @property
    def is_verification_expired(self) -> bool:
        """Verificar si el código de verificación ha expirado"""
        if not self.verification_expires_at:
            return True
        return datetime.utcnow() > self.verification_expires_at
    
    @property
    def can_receive_notifications(self) -> bool:
        """Verificar si puede recibir notificaciones"""
        return self.is_active and self.is_verified
