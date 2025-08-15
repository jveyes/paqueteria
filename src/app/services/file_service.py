"""
File Service
===========

Servicio para gestión de archivos con integración AWS S3.
"""

import os
import uuid
import mimetypes
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, BinaryIO
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc
import logging
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import hashlib

from ..models.file_upload import FileUpload
from ..models.package import Package
from ..schemas.file_upload import (
    FileUploadCreate, FileUploadUpdate, FileUploadSearch,
    FileUploadStats, FileUploadValidation
)
from ..core.config import settings

logger = logging.getLogger(__name__)

class FileService:
    """Servicio para gestión de archivos"""
    
    def __init__(self, db: Session):
        self.db = db
        self.s3_client = None
        self._init_s3_client()
    
    def _init_s3_client(self):
        """Inicializar cliente S3"""
        try:
            if (settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY and 
                settings.AWS_REGION and settings.S3_BUCKET_NAME):
                
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                    region_name=settings.AWS_REGION
                )
                logger.info("Cliente S3 inicializado correctamente")
            else:
                logger.warning("Configuración S3 incompleta, usando almacenamiento local")
                
        except Exception as e:
            logger.error(f"Error inicializando cliente S3: {e}")
    
    def upload_file(self, file_content: BinaryIO, original_filename: str, 
                   package_id: int, file_size: int) -> FileUpload:
        """
        Subir archivo
        
        Args:
            file_content: Contenido del archivo
            original_filename: Nombre original del archivo
            package_id: ID del paquete asociado
            file_size: Tamaño del archivo en bytes
            
        Returns:
            FileUpload: Archivo subido
        """
        try:
            # Validar archivo
            validation = FileUploadValidation(
                filename=original_filename,
                file_size=file_size,
                mime_type=mimetypes.guess_type(original_filename)[0] or 'application/octet-stream'
            )
            
            # Generar nombre único
            file_extension = os.path.splitext(original_filename)[1]
            unique_filename = f"{uuid.uuid4().hex}{file_extension}"
            
            # Determinar ruta de almacenamiento
            if self.s3_client:
                file_path = f"packages/{package_id}/{unique_filename}"
                success = self._upload_to_s3(file_content, file_path, file_size)
            else:
                file_path = self._upload_to_local(file_content, unique_filename, package_id)
                success = True
            
            if not success:
                raise ValueError("Error subiendo archivo")
            
            # Crear registro en base de datos
            file_upload = FileUpload(
                filename=unique_filename,
                original_filename=original_filename,
                file_path=file_path,
                file_size=file_size,
                mime_type=validation.mime_type,
                package_id=package_id
            )
            
            self.db.add(file_upload)
            self.db.commit()
            self.db.refresh(file_upload)
            
            logger.info(f"Archivo subido: {original_filename} -> {file_path}")
            return file_upload
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error subiendo archivo: {e}")
            raise
    
    def get_file_by_id(self, file_id: int) -> Optional[FileUpload]:
        """Obtener archivo por ID"""
        return self.db.query(FileUpload).filter(FileUpload.id == file_id).first()
    
    def get_files_by_package(self, package_id: int) -> List[FileUpload]:
        """Obtener archivos de un paquete"""
        return self.db.query(FileUpload).filter(
            and_(
                FileUpload.package_id == package_id,
                FileUpload.is_deleted == False
            )
        ).all()
    
    def download_file(self, file_id: int) -> Optional[Dict[str, Any]]:
        """
        Descargar archivo
        
        Args:
            file_id: ID del archivo
            
        Returns:
            Dict con contenido y metadatos del archivo
        """
        file_upload = self.get_file_by_id(file_id)
        
        if not file_upload or file_upload.is_deleted:
            return None
        
        try:
            if self.s3_client:
                # Descargar desde S3
                response = self.s3_client.get_object(
                    Bucket=settings.S3_BUCKET_NAME,
                    Key=file_upload.file_path
                )
                file_content = response['Body'].read()
            else:
                # Leer desde almacenamiento local
                local_path = os.path.join(settings.UPLOAD_DIR, file_upload.file_path)
                with open(local_path, 'rb') as f:
                    file_content = f.read()
            
            return {
                'content': file_content,
                'filename': file_upload.original_filename,
                'mime_type': file_upload.mime_type,
                'size': file_upload.file_size
            }
            
        except Exception as e:
            logger.error(f"Error descargando archivo {file_id}: {e}")
            return None
    
    def delete_file(self, file_id: int) -> bool:
        """
        Eliminar archivo (soft delete)
        
        Args:
            file_id: ID del archivo
            
        Returns:
            bool: True si se eliminó correctamente
        """
        file_upload = self.get_file_by_id(file_id)
        
        if not file_upload:
            return False
        
        try:
            # Marcar como eliminado
            file_upload.mark_as_deleted()
            self.db.commit()
            
            logger.info(f"Archivo marcado como eliminado: {file_upload.original_filename}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error eliminando archivo: {e}")
            return False
    
    def permanently_delete_file(self, file_id: int) -> bool:
        """
        Eliminar archivo permanentemente
        
        Args:
            file_id: ID del archivo
            
        Returns:
            bool: True si se eliminó correctamente
        """
        file_upload = self.get_file_by_id(file_id)
        
        if not file_upload:
            return False
        
        try:
            # Eliminar archivo físico
            if self.s3_client:
                self.s3_client.delete_object(
                    Bucket=settings.S3_BUCKET_NAME,
                    Key=file_upload.file_path
                )
            else:
                local_path = os.path.join(settings.UPLOAD_DIR, file_upload.file_path)
                if os.path.exists(local_path):
                    os.remove(local_path)
            
            # Eliminar registro de base de datos
            self.db.delete(file_upload)
            self.db.commit()
            
            logger.info(f"Archivo eliminado permanentemente: {file_upload.original_filename}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error eliminando archivo permanentemente: {e}")
            return False
    
    def search_files(self, search_params: FileUploadSearch) -> Dict[str, Any]:
        """
        Buscar archivos con filtros
        
        Args:
            search_params: Parámetros de búsqueda
            
        Returns:
            Dict con archivos y metadatos de paginación
        """
        query = self.db.query(FileUpload)
        
        # Aplicar filtros
        if search_params.package_id:
            query = query.filter(FileUpload.package_id == search_params.package_id)
        
        if search_params.mime_type:
            query = query.filter(FileUpload.mime_type == search_params.mime_type)
        
        if search_params.filename:
            query = query.filter(FileUpload.original_filename.ilike(f"%{search_params.filename}%"))
        
        if search_params.date_from:
            query = query.filter(FileUpload.uploaded_at >= search_params.date_from)
        
        if search_params.date_to:
            query = query.filter(FileUpload.uploaded_at <= search_params.date_to)
        
        if search_params.is_deleted is not None:
            query = query.filter(FileUpload.is_deleted == search_params.is_deleted)
        
        # Contar total
        total = query.count()
        
        # Aplicar paginación
        offset = (search_params.page - 1) * search_params.per_page
        files = query.offset(offset).limit(search_params.per_page).all()
        
        # Calcular páginas
        total_pages = (total + search_params.per_page - 1) // search_params.per_page
        
        return {
            "files": files,
            "total": total,
            "page": search_params.page,
            "per_page": search_params.per_page,
            "total_pages": total_pages
        }
    
    def get_file_stats(self) -> FileUploadStats:
        """Obtener estadísticas de archivos"""
        today = datetime.utcnow().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        # Totales
        total_files = self.db.query(FileUpload).count()
        total_size = self.db.query(func.sum(FileUpload.file_size)).scalar() or 0
        total_size_mb = total_size / (1024 * 1024)
        
        # Archivos de hoy
        files_today = self.db.query(FileUpload).filter(
            func.date(FileUpload.uploaded_at) == today
        ).count()
        
        files_this_week = self.db.query(FileUpload).filter(
            FileUpload.uploaded_at >= week_ago
        ).count()
        
        files_this_month = self.db.query(FileUpload).filter(
            FileUpload.uploaded_at >= month_ago
        ).count()
        
        # Archivos por tipo
        files_by_type = {}
        type_stats = self.db.query(
            FileUpload.mime_type,
            func.count(FileUpload.id).label('count')
        ).group_by(FileUpload.mime_type).all()
        
        for mime_type, count in type_stats:
            files_by_type[mime_type] = count
        
        # Tamaño promedio
        avg_size = self.db.query(func.avg(FileUpload.file_size)).scalar() or 0
        average_file_size = avg_size / (1024 * 1024)  # Convertir a MB
        
        # Archivos eliminados
        deleted_files = self.db.query(FileUpload).filter(FileUpload.is_deleted == True).count()
        
        return FileUploadStats(
            total_files=total_files,
            total_size=total_size,
            total_size_mb=total_size_mb,
            files_today=files_today,
            files_this_week=files_this_week,
            files_this_month=files_this_month,
            files_by_type=files_by_type,
            average_file_size=average_file_size,
            deleted_files=deleted_files
        )
    
    def validate_file(self, file_content: BinaryIO, original_filename: str, 
                     file_size: int) -> FileUploadValidation:
        """
        Validar archivo antes de subir
        
        Args:
            file_content: Contenido del archivo
            original_filename: Nombre original del archivo
            file_size: Tamaño del archivo en bytes
            
        Returns:
            FileUploadValidation: Resultado de la validación
        """
        # Verificar tamaño
        if file_size > settings.MAX_FILE_SIZE:
            raise ValueError(f"Archivo demasiado grande. Máximo {settings.MAX_FILE_SIZE / (1024*1024)}MB")
        
        # Verificar tipo MIME
        mime_type = mimetypes.guess_type(original_filename)[0] or 'application/octet-stream'
        if mime_type not in settings.ALLOWED_MIME_TYPES:
            raise ValueError(f"Tipo de archivo no permitido: {mime_type}")
        
        # Verificar nombre de archivo
        if '..' in original_filename or '/' in original_filename or '\\' in original_filename:
            raise ValueError("Nombre de archivo inválido")
        
        # Calcular hash para verificar integridad
        file_content.seek(0)
        file_hash = hashlib.md5(file_content.read()).hexdigest()
        
        return FileUploadValidation(
            filename=original_filename,
            file_size=file_size,
            mime_type=mime_type,
            file_hash=file_hash
        )
    
    def _upload_to_s3(self, file_content: BinaryIO, file_path: str, file_size: int) -> bool:
        """
        Subir archivo a S3
        
        Args:
            file_content: Contenido del archivo
            file_path: Ruta en S3
            file_size: Tamaño del archivo
            
        Returns:
            bool: True si se subió correctamente
        """
        try:
            file_content.seek(0)
            
            self.s3_client.upload_fileobj(
                file_content,
                settings.S3_BUCKET_NAME,
                file_path,
                ExtraArgs={
                    'ContentType': mimetypes.guess_type(file_path)[0] or 'application/octet-stream',
                    'Metadata': {
                        'original-size': str(file_size),
                        'uploaded-at': datetime.utcnow().isoformat()
                    }
                }
            )
            
            return True
            
        except (ClientError, NoCredentialsError) as e:
            logger.error(f"Error subiendo a S3: {e}")
            return False
    
    def _upload_to_local(self, file_content: BinaryIO, filename: str, package_id: int) -> str:
        """
        Subir archivo a almacenamiento local
        
        Args:
            file_content: Contenido del archivo
            filename: Nombre del archivo
            package_id: ID del paquete
            
        Returns:
            str: Ruta relativa del archivo
        """
        # Crear directorio si no existe
        package_dir = os.path.join(settings.UPLOAD_DIR, 'packages', str(package_id))
        os.makedirs(package_dir, exist_ok=True)
        
        # Ruta completa del archivo
        file_path = os.path.join(package_dir, filename)
        
        # Guardar archivo
        file_content.seek(0)
        with open(file_path, 'wb') as f:
            f.write(file_content.read())
        
        # Retornar ruta relativa
        return f"packages/{package_id}/{filename}"
    
    def get_file_url(self, file_id: int, expires_in: int = 3600) -> Optional[str]:
        """
        Obtener URL de descarga del archivo
        
        Args:
            file_id: ID del archivo
            expires_in: Tiempo de expiración en segundos
            
        Returns:
            str: URL de descarga o None si no se puede generar
        """
        file_upload = self.get_file_by_id(file_id)
        
        if not file_upload or file_upload.is_deleted:
            return None
        
        try:
            if self.s3_client:
                # Generar URL firmada de S3
                url = self.s3_client.generate_presigned_url(
                    'get_object',
                    Params={
                        'Bucket': settings.S3_BUCKET_NAME,
                        'Key': file_upload.file_path
                    },
                    ExpiresIn=expires_in
                )
                return url
            else:
                # URL local
                return f"/api/files/{file_id}/download"
                
        except Exception as e:
            logger.error(f"Error generando URL para archivo {file_id}: {e}")
            return None
    
    def cleanup_orphaned_files(self) -> int:
        """
        Limpiar archivos huérfanos (sin paquete asociado)
        
        Returns:
            int: Número de archivos eliminados
        """
        try:
            # Buscar archivos huérfanos
            orphaned_files = self.db.query(FileUpload).filter(
                and_(
                    FileUpload.is_deleted == False,
                    ~FileUpload.package_id.in_(
                        self.db.query(Package.id)
                    )
                )
            ).all()
            
            deleted_count = 0
            for file_upload in orphaned_files:
                if self.permanently_delete_file(file_upload.id):
                    deleted_count += 1
            
            if deleted_count > 0:
                logger.info(f"Eliminados {deleted_count} archivos huérfanos")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error limpiando archivos huérfanos: {e}")
            return 0
    
    def get_storage_usage(self) -> Dict[str, Any]:
        """
        Obtener información de uso de almacenamiento
        
        Returns:
            Dict con información de uso
        """
        try:
            # Estadísticas por paquete
            package_stats = self.db.query(
                FileUpload.package_id,
                func.count(FileUpload.id).label('file_count'),
                func.sum(FileUpload.file_size).label('total_size')
            ).filter(
                FileUpload.is_deleted == False
            ).group_by(FileUpload.package_id).all()
            
            # Estadísticas por tipo
            type_stats = self.db.query(
                FileUpload.mime_type,
                func.count(FileUpload.id).label('file_count'),
                func.sum(FileUpload.file_size).label('total_size')
            ).filter(
                FileUpload.is_deleted == False
            ).group_by(FileUpload.mime_type).all()
            
            return {
                'package_stats': [
                    {
                        'package_id': package_id,
                        'file_count': file_count,
                        'total_size_mb': (total_size or 0) / (1024 * 1024)
                    }
                    for package_id, file_count, total_size in package_stats
                ],
                'type_stats': [
                    {
                        'mime_type': mime_type,
                        'file_count': file_count,
                        'total_size_mb': (total_size or 0) / (1024 * 1024)
                    }
                    for mime_type, file_count, total_size in type_stats
                ]
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas de almacenamiento: {e}")
            return {'package_stats': [], 'type_stats': []}
