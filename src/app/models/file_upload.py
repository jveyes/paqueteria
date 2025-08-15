"""
Modelo FileUpload - Archivos adjuntos
====================================

Modelo para gestionar archivos adjuntos a paquetes.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from ..core.database import Base


class FileUpload(Base):
    """
    Modelo para archivos adjuntos a paquetes
    """
    
    __tablename__ = "file_uploads"
    
    # =============================================================================
    # CAMPOS PRINCIPALES
    # =============================================================================
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)  # Tamaño en bytes
    mime_type = Column(String(100), nullable=False)
    
    # =============================================================================
    # RELACIONES
    # =============================================================================
    
    package_id = Column(Integer, ForeignKey("packages.id"), nullable=False)
    package = relationship("Package", back_populates="files")
    
    # =============================================================================
    # METADATA
    # =============================================================================
    
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    # =============================================================================
    # ÍNDICES
    # =============================================================================
    
    __table_args__ = (
        Index('idx_file_package', 'package_id'),
        Index('idx_file_uploaded_at', 'uploaded_at'),
        Index('idx_file_mime_type', 'mime_type'),
    )
    
    # =============================================================================
    # MÉTODOS
    # =============================================================================
    
    def get_file_size_mb(self) -> float:
        """
        Obtener tamaño del archivo en MB
        
        Returns:
            float: Tamaño en MB
        """
        return self.file_size / (1024 * 1024)
    
    def get_file_size_formatted(self) -> str:
        """
        Obtener tamaño del archivo formateado
        
        Returns:
            str: Tamaño formateado (ej: "1.5 MB")
        """
        size_mb = self.get_file_size_mb()
        if size_mb < 1:
            return f"{self.file_size / 1024:.1f} KB"
        else:
            return f"{size_mb:.1f} MB"
    
    def mark_as_deleted(self) -> None:
        """
        Marcar archivo como eliminado
        """
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
    
    def is_image(self) -> bool:
        """
        Verificar si es una imagen
        
        Returns:
            bool: True si es imagen
        """
        return self.mime_type.startswith('image/')
    
    def is_pdf(self) -> bool:
        """
        Verificar si es un PDF
        
        Returns:
            bool: True si es PDF
        """
        return self.mime_type == 'application/pdf'
    
    # =============================================================================
    # REPRESENTACIÓN
    # =============================================================================
    
    def __repr__(self) -> str:
        return f"<FileUpload(id={self.id}, filename='{self.filename}', size={self.file_size})>"
    
    def __str__(self) -> str:
        return f"{self.original_filename} ({self.get_file_size_formatted()})"
