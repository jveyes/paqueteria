"""
File Routes
==========

Rutas para gestión de archivos.
"""

from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import io

from ..core.database import get_db
from ..core.auth import get_current_active_user, require_permission
from ..models.user import User
from ..services.file_service import FileService
from ..schemas.file_upload import (
    FileUploadResponse, FileUploadSearch, FileUploadStats,
    FileUploadListResponse
)

router = APIRouter(prefix="/api/files", tags=["Files"])

@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    package_id: int = Query(..., description="ID del paquete"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Subir archivo
    
    Args:
        file: Archivo a subir
        package_id: ID del paquete asociado
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        FileUploadResponse: Archivo subido
    """
    require_permission("files:upload")(current_user)
    
    # Validar archivo
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nombre de archivo requerido"
        )
    
    # Leer contenido del archivo
    file_content = await file.read()
    file_size = len(file_content)
    
    # Crear objeto de archivo para el servicio
    file_obj = io.BytesIO(file_content)
    file_obj.name = file.filename
    
    file_service = FileService(db)
    
    try:
        # Validar archivo
        validation = file_service.validate_file(file_obj, file.filename, file_size)
        
        # Subir archivo
        file_upload = file_service.upload_file(file_obj, file.filename, package_id, file_size)
        
        return FileUploadResponse.from_orm(file_upload)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error subiendo archivo: {str(e)}"
        )

@router.get("/", response_model=FileUploadListResponse)
async def list_files(
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(20, ge=1, le=100, description="Elementos por página"),
    package_id: Optional[int] = Query(None, description="ID del paquete"),
    mime_type: Optional[str] = Query(None, description="Tipo MIME"),
    filename: Optional[str] = Query(None, description="Nombre del archivo"),
    is_deleted: Optional[bool] = Query(None, description="Archivo eliminado"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Listar archivos con filtros
    
    Args:
        page: Número de página
        per_page: Elementos por página
        package_id: ID del paquete
        mime_type: Tipo MIME
        filename: Nombre del archivo
        is_deleted: Archivo eliminado
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        FileUploadListResponse: Lista de archivos
    """
    require_permission("files:read")(current_user)
    
    search_params = FileUploadSearch(
        package_id=package_id,
        mime_type=mime_type,
        filename=filename,
        is_deleted=is_deleted,
        page=page,
        per_page=per_page
    )
    
    file_service = FileService(db)
    result = file_service.search_files(search_params)
    
    return FileUploadListResponse(
        files=[FileUploadResponse.from_orm(file_upload) for file_upload in result["files"]],
        total=result["total"],
        page=result["page"],
        per_page=result["per_page"],
        total_pages=result["total_pages"]
    )

@router.get("/{file_id}", response_model=FileUploadResponse)
async def get_file(
    file_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Obtener información de archivo por ID
    
    Args:
        file_id: ID del archivo
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        FileUploadResponse: Información del archivo
    """
    require_permission("files:read")(current_user)
    
    file_service = FileService(db)
    file_upload = file_service.get_file_by_id(file_id)
    
    if not file_upload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Archivo no encontrado"
        )
    
    return FileUploadResponse.from_orm(file_upload)

@router.get("/{file_id}/download")
async def download_file(
    file_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Descargar archivo
    
    Args:
        file_id: ID del archivo
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        StreamingResponse: Archivo para descarga
    """
    require_permission("files:download")(current_user)
    
    file_service = FileService(db)
    file_data = file_service.download_file(file_id)
    
    if not file_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Archivo no encontrado"
        )
    
    # Crear respuesta de streaming
    file_stream = io.BytesIO(file_data["content"])
    
    return StreamingResponse(
        file_stream,
        media_type=file_data["mime_type"],
        headers={
            "Content-Disposition": f"attachment; filename={file_data['filename']}",
            "Content-Length": str(file_data["size"])
        }
    )

@router.get("/{file_id}/url")
async def get_file_url(
    file_id: int,
    expires_in: int = Query(3600, ge=300, le=86400, description="Tiempo de expiración en segundos"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Obtener URL de descarga del archivo
    
    Args:
        file_id: ID del archivo
        expires_in: Tiempo de expiración en segundos
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        dict: URL de descarga
    """
    require_permission("files:read")(current_user)
    
    file_service = FileService(db)
    url = file_service.get_file_url(file_id, expires_in)
    
    if not url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Archivo no encontrado"
        )
    
    return {"download_url": url, "expires_in": expires_in}

@router.get("/package/{package_id}/list")
async def get_package_files(
    package_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Obtener archivos de un paquete
    
    Args:
        package_id: ID del paquete
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        List: Lista de archivos del paquete
    """
    require_permission("files:read")(current_user)
    
    file_service = FileService(db)
    files = file_service.get_files_by_package(package_id)
    
    return [FileUploadResponse.from_orm(file_upload) for file_upload in files]

@router.delete("/{file_id}")
async def delete_file(
    file_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Eliminar archivo (soft delete)
    
    Args:
        file_id: ID del archivo
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        dict: Mensaje de confirmación
    """
    require_permission("files:delete")(current_user)
    
    file_service = FileService(db)
    success = file_service.delete_file(file_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Archivo no encontrado"
        )
    
    return {"message": "Archivo eliminado exitosamente"}

@router.delete("/{file_id}/permanent")
async def permanently_delete_file(
    file_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Eliminar archivo permanentemente
    
    Args:
        file_id: ID del archivo
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        dict: Mensaje de confirmación
    """
    require_permission("files:delete")(current_user)
    
    file_service = FileService(db)
    success = file_service.permanently_delete_file(file_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Archivo no encontrado"
        )
    
    return {"message": "Archivo eliminado permanentemente"}

@router.get("/stats/overview", response_model=FileUploadStats)
async def get_file_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Obtener estadísticas de archivos
    
    Args:
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        FileUploadStats: Estadísticas de archivos
    """
    require_permission("files:read")(current_user)
    
    file_service = FileService(db)
    return file_service.get_file_stats()

@router.get("/storage/usage")
async def get_storage_usage(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Obtener información de uso de almacenamiento
    
    Args:
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        dict: Información de uso de almacenamiento
    """
    require_permission("files:read")(current_user)
    
    file_service = FileService(db)
    return file_service.get_storage_usage()

@router.post("/cleanup/orphaned")
async def cleanup_orphaned_files(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Limpiar archivos huérfanos
    
    Args:
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        dict: Resultado de la limpieza
    """
    require_permission("files:cleanup")(current_user)
    
    file_service = FileService(db)
    deleted_count = file_service.cleanup_orphaned_files()
    
    return {
        "message": f"Eliminados {deleted_count} archivos huérfanos",
        "deleted_count": deleted_count
    }

@router.post("/bulk-upload")
async def bulk_upload_files(
    files: List[UploadFile] = File(...),
    package_id: int = Query(..., description="ID del paquete"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Subir múltiples archivos
    
    Args:
        files: Lista de archivos a subir
        package_id: ID del paquete asociado
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        dict: Resultado de la subida masiva
    """
    require_permission("files:upload")(current_user)
    
    file_service = FileService(db)
    
    results = {
        "total": len(files),
        "uploaded": 0,
        "failed": 0,
        "errors": [],
        "files": []
    }
    
    for file in files:
        try:
            if not file.filename:
                results["failed"] += 1
                results["errors"].append(f"Archivo sin nombre")
                continue
            
            # Leer contenido del archivo
            file_content = await file.read()
            file_size = len(file_content)
            
            # Crear objeto de archivo para el servicio
            file_obj = io.BytesIO(file_content)
            file_obj.name = file.filename
            
            # Validar archivo
            validation = file_service.validate_file(file_obj, file.filename, file_size)
            
            # Subir archivo
            file_upload = file_service.upload_file(file_obj, file.filename, package_id, file_size)
            
            results["uploaded"] += 1
            results["files"].append(FileUploadResponse.from_orm(file_upload))
            
        except Exception as e:
            results["failed"] += 1
            results["errors"].append(f"Error subiendo {file.filename}: {str(e)}")
    
    return results

@router.get("/types/allowed")
async def get_allowed_file_types(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Obtener tipos de archivo permitidos
    
    Args:
        current_user: Usuario actual
        
    Returns:
        dict: Tipos de archivo permitidos
    """
    require_permission("files:read")(current_user)
    
    from ..core.config import settings
    
    return {
        "allowed_mime_types": settings.ALLOWED_MIME_TYPES,
        "max_file_size_mb": settings.MAX_FILE_SIZE / (1024 * 1024),
        "max_file_size_bytes": settings.MAX_FILE_SIZE
    }

@router.get("/health")
async def files_health_check() -> Any:
    """
    Health check para el módulo de archivos
    
    Returns:
        dict: Estado del módulo
    """
    return {
        "status": "healthy",
        "module": "files",
        "endpoints": [
            "upload", "list", "get", "download", "url", "package-files",
            "delete", "permanent-delete", "stats", "storage-usage",
            "cleanup", "bulk-upload", "allowed-types"
        ]
    }
