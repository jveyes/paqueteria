"""
File Upload Schemas
==================

Esquemas Pydantic para validación de datos de archivos.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, validator
import re

class FileUploadResponse(BaseModel):
    """Esquema para respuesta de archivo subido"""
    id: int = Field(..., description="ID único del archivo")
    filename: str = Field(..., description="Nombre del archivo en el sistema")
    original_filename: str = Field(..., description="Nombre original del archivo")
    file_path: str = Field(..., description="Ruta del archivo")
    file_size: int = Field(..., description="Tamaño del archivo en bytes")
    mime_type: str = Field(..., description="Tipo MIME del archivo")
    package_id: int = Field(..., description="ID del paquete asociado")
    uploaded_at: datetime = Field(..., description="Fecha de subida")
    is_deleted: bool = Field(..., description="Archivo eliminado")
    deleted_at: Optional[datetime] = Field(None, description="Fecha de eliminación")
    
    # Computed fields
    file_size_mb: float = Field(..., description="Tamaño del archivo en MB")
    file_size_formatted: str = Field(..., description="Tamaño del archivo formateado")
    download_url: Optional[str] = Field(None, description="URL de descarga")
    preview_url: Optional[str] = Field(None, description="URL de vista previa")

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class FileUploadCreate(BaseModel):
    """Esquema para crear un nuevo archivo"""
    original_filename: str = Field(..., description="Nombre original del archivo")
    file_size: int = Field(..., ge=1, description="Tamaño del archivo en bytes")
    mime_type: str = Field(..., description="Tipo MIME del archivo")
    package_id: int = Field(..., description="ID del paquete asociado")

    @validator('original_filename')
    def validate_filename(cls, v):
        # Remove path traversal attempts
        if '..' in v or '/' in v or '\\' in v:
            raise ValueError('Nombre de archivo inválido')
        
        # Check for valid characters
        if not re.match(r'^[a-zA-Z0-9._-]+$', v):
            raise ValueError('Nombre de archivo contiene caracteres inválidos')
        
        return v

    @validator('file_size')
    def validate_file_size(cls, v):
        # Maximum file size: 10MB
        max_size = 10 * 1024 * 1024  # 10MB in bytes
        if v > max_size:
            raise ValueError('El archivo es demasiado grande. Máximo 10MB')
        return v

    @validator('mime_type')
    def validate_mime_type(cls, v):
        # Allowed MIME types
        allowed_types = [
            'image/jpeg', 'image/jpg', 'image/png', 'image/gif',
            'application/pdf', 'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'text/plain'
        ]
        
        if v not in allowed_types:
            raise ValueError('Tipo de archivo no permitido')
        return v

class FileUploadUpdate(BaseModel):
    """Esquema para actualizar un archivo"""
    original_filename: Optional[str] = Field(None, description="Nuevo nombre del archivo")
    is_deleted: Optional[bool] = Field(None, description="Marcar como eliminado")

    @validator('original_filename')
    def validate_filename(cls, v):
        if v is not None:
            if '..' in v or '/' in v or '\\' in v:
                raise ValueError('Nombre de archivo inválido')
            
            if not re.match(r'^[a-zA-Z0-9._-]+$', v):
                raise ValueError('Nombre de archivo contiene caracteres inválidos')
        return v

class FileUploadSearch(BaseModel):
    """Esquema para búsqueda de archivos"""
    package_id: Optional[int] = Field(None, description="ID del paquete")
    mime_type: Optional[str] = Field(None, description="Tipo MIME")
    filename: Optional[str] = Field(None, description="Nombre del archivo")
    date_from: Optional[datetime] = Field(None, description="Fecha desde")
    date_to: Optional[datetime] = Field(None, description="Fecha hasta")
    is_deleted: Optional[bool] = Field(None, description="Archivos eliminados")
    page: int = Field(default=1, ge=1, description="Número de página")
    per_page: int = Field(default=20, ge=1, le=100, description="Elementos por página")

class FileUploadListResponse(BaseModel):
    """Esquema para lista de archivos"""
    files: List[FileUploadResponse] = Field(..., description="Lista de archivos")
    total: int = Field(..., description="Total de archivos")
    page: int = Field(..., description="Página actual")
    per_page: int = Field(..., description="Archivos por página")
    total_pages: int = Field(..., description="Total de páginas")

class FileUploadStats(BaseModel):
    """Esquema para estadísticas de archivos"""
    total_files: int = Field(..., description="Total de archivos")
    total_size: int = Field(..., description="Tamaño total en bytes")
    total_size_mb: float = Field(..., description="Tamaño total en MB")
    files_today: int = Field(..., description="Archivos subidos hoy")
    files_this_week: int = Field(..., description="Archivos subidos esta semana")
    files_this_month: int = Field(..., description="Archivos subidos este mes")
    files_by_type: dict = Field(..., description="Archivos por tipo MIME")
    average_file_size: float = Field(..., description="Tamaño promedio de archivo")
    deleted_files: int = Field(..., description="Archivos eliminados")

class FileUploadBulkAction(BaseModel):
    """Esquema para acciones masivas en archivos"""
    file_ids: List[int] = Field(..., description="IDs de archivos")
    action: str = Field(..., pattern="^(delete|restore|download)$", description="Acción a realizar")

class FileUploadExport(BaseModel):
    """Esquema para exportación de archivos"""
    format: str = Field(default="csv", pattern="^(csv|excel|json)$", description="Formato de exportación")
    include_content: bool = Field(default=False, description="Incluir contenido de archivos")
    date_from: Optional[datetime] = Field(None, description="Fecha desde")
    date_to: Optional[datetime] = Field(None, description="Fecha hasta")
    mime_type: Optional[str] = Field(None, description="Filtrar por tipo MIME")
    package_id: Optional[int] = Field(None, description="Filtrar por paquete")

class FileUploadValidation(BaseModel):
    """Esquema para validación de archivos"""
    filename: str = Field(..., description="Nombre del archivo")
    file_size: int = Field(..., description="Tamaño del archivo")
    mime_type: str = Field(..., description="Tipo MIME")
    allowed_types: List[str] = Field(default=[
        'image/jpeg', 'image/jpg', 'image/png', 'image/gif',
        'application/pdf', 'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'text/plain'
    ], description="Tipos MIME permitidos")
    max_size_mb: int = Field(default=10, description="Tamaño máximo en MB")

    @validator('filename')
    def validate_filename(cls, v):
        if '..' in v or '/' in v or '\\' in v:
            raise ValueError('Nombre de archivo inválido')
        return v

    @validator('file_size')
    def validate_file_size(cls, v, values):
        max_size_mb = values.get('max_size_mb', 10)
        max_size_bytes = max_size_mb * 1024 * 1024
        
        if v > max_size_bytes:
            raise ValueError(f'El archivo es demasiado grande. Máximo {max_size_mb}MB')
        return v

    @validator('mime_type')
    def validate_mime_type(cls, v, values):
        allowed_types = values.get('allowed_types', [])
        
        if v not in allowed_types:
            raise ValueError('Tipo de archivo no permitido')
        return v
