"""
Modelo Package - Paquetes del sistema
====================================

Modelo para gestionar los paquetes en el sistema de paquetería.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Numeric, ForeignKey, Index, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from ..core.database import Base


class PackageType(enum.Enum):
    """Tipos de paquete"""
    NORMAL = "normal"
    EXTRA_DIMENSIONED = "extra_dimensioned"


class PackageStatus(enum.Enum):
    """Estados de paquete"""
    ANNOUNCED = "announced"      # Anunciado por cliente
    RECEIVED = "received"        # Recibido en instalaciones
    DELIVERED = "delivered"      # Entregado al cliente
    CANCELLED = "cancelled"      # Cancelado
    EXPIRED = "expired"          # Expirado (no reclamado)


class Package(Base):
    """
    Modelo para paquetes del sistema de paquetería
    """
    
    __tablename__ = "packages"
    
    # =============================================================================
    # CAMPOS PRINCIPALES
    # =============================================================================
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tracking_number = Column(String(20), unique=True, index=True, nullable=False)
    
    # =============================================================================
    # RELACIONES
    # =============================================================================
    
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    customer = relationship("Customer", back_populates="packages")
    
    # =============================================================================
    # INFORMACIÓN DEL PAQUETE
    # =============================================================================
    
    description = Column(Text, nullable=False)
    package_type = Column(Enum(PackageType), default=PackageType.NORMAL, nullable=False)
    status = Column(Enum(PackageStatus), default=PackageStatus.ANNOUNCED, nullable=False)
    
    # =============================================================================
    # DIMENSIONES Y PESO
    # =============================================================================
    
    weight_kg = Column(Numeric(5, 2), nullable=True)  # Peso en kilogramos
    length_cm = Column(Numeric(5, 2), nullable=True)  # Largo en centímetros
    width_cm = Column(Numeric(5, 2), nullable=True)   # Ancho en centímetros
    height_cm = Column(Numeric(5, 2), nullable=True)  # Alto en centímetros
    
    # =============================================================================
    # COSTOS
    # =============================================================================
    
    base_cost = Column(Numeric(10, 2), nullable=False)  # Costo base del paquete
    storage_cost = Column(Numeric(10, 2), default=0, nullable=False)  # Costo de bodegaje
    total_cost = Column(Numeric(10, 2), nullable=False)  # Costo total
    
    # =============================================================================
    # FECHAS IMPORTANTES
    # =============================================================================
    
    announced_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    received_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # =============================================================================
    # INFORMACIÓN ADICIONAL
    # =============================================================================
    
    notes = Column(Text, nullable=True)  # Notas del administrador
    customer_notes = Column(Text, nullable=True)  # Notas del cliente
    is_urgent = Column(Boolean, default=False, nullable=False)
    
    # =============================================================================
    # METADATA
    # =============================================================================
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # =============================================================================
    # RELACIONES
    # =============================================================================
    
    # Relación con archivos
    files = relationship("FileUpload", back_populates="package", cascade="all, delete-orphan")
    
    # Relación con notificaciones
    notifications = relationship("Notification", back_populates="package", cascade="all, delete-orphan")
    
    # Relación con entregas
    deliveries = relationship("Delivery", back_populates="package", cascade="all, delete-orphan")
    
    # =============================================================================
    # ÍNDICES
    # =============================================================================
    
    __table_args__ = (
        Index('idx_package_tracking', 'tracking_number'),
        Index('idx_package_customer_status', 'customer_id', 'status'),
        Index('idx_package_status_created', 'status', 'created_at'),
        Index('idx_package_expires_at', 'expires_at'),
        Index('idx_package_type_status', 'package_type', 'status'),
    )
    
    # =============================================================================
    # MÉTODOS
    # =============================================================================
    
    def generate_tracking_number(self) -> str:
        """
        Generar número de tracking único
        
        Returns:
            str: Número de tracking generado
        """
        import random
        import string
        
        # Formato: PAQ-YYYYMMDD-XXXXX
        from datetime import datetime
        date_part = datetime.now().strftime("%Y%m%d")
        random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        
        return f"PAQ-{date_part}-{random_part}"
    
    def calculate_base_cost(self) -> Decimal:
        """
        Calcular costo base del paquete
        
        Returns:
            Decimal: Costo base calculado
        """
        from ..core.config import settings
        
        if self.package_type == PackageType.NORMAL:
            return Decimal(str(settings.PACKAGE_NORMAL_COST))
        else:
            return Decimal(str(settings.PACKAGE_EXTRA_COST))
    
    def calculate_storage_cost(self) -> Decimal:
        """
        Calcular costo de bodegaje
        
        Returns:
            Decimal: Costo de bodegaje calculado
        """
        from ..core.config import settings
        
        if not self.received_at:
            return Decimal('0')
        
        # Calcular días desde la recepción
        now = datetime.utcnow()
        days_in_storage = (now - self.received_at).days
        
        # Aplicar período de gracia
        grace_hours = settings.STORAGE_GRACE_HOURS
        grace_days = grace_hours / 24
        
        if days_in_storage <= grace_days:
            return Decimal('0')
        
        # Calcular días cobrables
        chargeable_days = days_in_storage - grace_days
        daily_cost = Decimal(str(settings.STORAGE_COST_PER_DAY))
        
        return daily_cost * chargeable_days
    
    def calculate_total_cost(self) -> Decimal:
        """
        Calcular costo total del paquete
        
        Returns:
            Decimal: Costo total calculado
        """
        self.base_cost = self.calculate_base_cost()
        self.storage_cost = self.calculate_storage_cost()
        self.total_cost = self.base_cost + self.storage_cost
        return self.total_cost
    
    def mark_as_received(self) -> None:
        """
        Marcar paquete como recibido
        """
        self.status = PackageStatus.RECEIVED
        self.received_at = datetime.utcnow()
        self.calculate_total_cost()
    
    def mark_as_delivered(self) -> None:
        """
        Marcar paquete como entregado
        """
        self.status = PackageStatus.DELIVERED
        self.delivered_at = datetime.utcnow()
        self.calculate_total_cost()
    
    def cancel(self) -> None:
        """
        Cancelar paquete
        """
        self.status = PackageStatus.CANCELLED
    
    def check_expiration(self) -> bool:
        """
        Verificar si el paquete ha expirado
        
        Returns:
            bool: True si ha expirado
        """
        if not self.expires_at:
            return False
        
        if datetime.utcnow() > self.expires_at:
            self.status = PackageStatus.EXPIRED
            return True
        
        return False
    
    def set_expiration_date(self, days: int = 30) -> None:
        """
        Establecer fecha de expiración
        
        Args:
            days: Días hasta la expiración
        """
        self.expires_at = datetime.utcnow() + timedelta(days=days)
    
    def get_dimensions_text(self) -> str:
        """
        Obtener texto de dimensiones
        
        Returns:
            str: Texto formateado de dimensiones
        """
        if not any([self.length_cm, self.width_cm, self.height_cm]):
            return "No especificadas"
        
        dimensions = []
        if self.length_cm:
            dimensions.append(f"L: {self.length_cm}cm")
        if self.width_cm:
            dimensions.append(f"A: {self.width_cm}cm")
        if self.height_cm:
            dimensions.append(f"H: {self.height_cm}cm")
        
        return " x ".join(dimensions)
    
    def get_files_count(self) -> int:
        """
        Obtener número de archivos adjuntos
        
        Returns:
            int: Número de archivos
        """
        return len(self.files) if self.files else 0
    
    # =============================================================================
    # REPRESENTACIÓN
    # =============================================================================
    
    def __repr__(self) -> str:
        return f"<Package(id={self.id}, tracking='{self.tracking_number}', status='{self.status.value}')>"
    
    def __str__(self) -> str:
        return f"Paquete {self.tracking_number} - {self.status.value}"
    
    # =============================================================================
    # PROPIEDADES
    # =============================================================================
    
    @property
    def is_active(self) -> bool:
        """Verificar si el paquete está activo"""
        return self.status in [PackageStatus.ANNOUNCED, PackageStatus.RECEIVED]
    
    @property
    def is_delivered(self) -> bool:
        """Verificar si el paquete fue entregado"""
        return self.status == PackageStatus.DELIVERED
    
    @property
    def is_cancelled(self) -> bool:
        """Verificar si el paquete fue cancelado"""
        return self.status == PackageStatus.CANCELLED
    
    @property
    def is_expired(self) -> bool:
        """Verificar si el paquete expiró"""
        return self.status == PackageStatus.EXPIRED
    
    @property
    def days_in_storage(self) -> int:
        """Días en bodegaje"""
        if not self.received_at:
            return 0
        
        return (datetime.utcnow() - self.received_at).days
    
    @property
    def formatted_cost(self) -> str:
        """Costo formateado en pesos colombianos"""
        return f"${self.total_cost:,.0f} COP"
    
    @property
    def short_description(self) -> str:
        """Descripción corta"""
        if len(self.description) <= 50:
            return self.description
        return self.description[:47] + "..."
