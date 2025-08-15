"""
AWS S3 Service
=============

Servicio de integración con AWS S3 para almacenamiento de archivos.
"""

import asyncio
import aiofiles
import mimetypes
import hashlib
from typing import Optional, Dict, Any, List, BinaryIO
from datetime import datetime, timedelta
from pathlib import Path
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from pydantic import BaseModel, Field

from ...core.config import settings
from ...core.logging import get_logger

logger = get_logger(__name__)

class S3Config(BaseModel):
    """Configuración para AWS S3"""
    access_key_id: str = Field(..., description="AWS Access Key ID")
    secret_access_key: str = Field(..., description="AWS Secret Access Key")
    region: str = Field(..., description="AWS Region")
    bucket_name: str = Field(..., description="Nombre del bucket S3")
    endpoint_url: Optional[str] = Field(None, description="URL del endpoint S3")
    max_file_size: int = Field(10 * 1024 * 1024, description="Tamaño máximo de archivo (10MB)")
    allowed_extensions: List[str] = Field(
        default=[".jpg", ".jpeg", ".png", ".gif", ".pdf", ".doc", ".docx", ".txt"],
        description="Extensiones permitidas"
    )

class S3FileInfo(BaseModel):
    """Información de archivo en S3"""
    key: str = Field(..., description="Clave del archivo en S3")
    filename: str = Field(..., description="Nombre original del archivo")
    size: int = Field(..., description="Tamaño del archivo en bytes")
    content_type: str = Field(..., description="Tipo de contenido")
    etag: str = Field(..., description="ETag del archivo")
    last_modified: datetime = Field(..., description="Última modificación")
    url: Optional[str] = Field(None, description="URL pública del archivo")

class S3Service:
    """Servicio para integración con AWS S3"""
    
    def __init__(self):
        self.config = S3Config(
            access_key_id=settings.AWS_ACCESS_KEY_ID,
            secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region=settings.AWS_REGION,
            bucket_name=settings.S3_BUCKET_NAME,
            endpoint_url=settings.S3_ENDPOINT_URL,
            max_file_size=settings.MAX_FILE_SIZE,
            allowed_extensions=settings.ALLOWED_FILE_EXTENSIONS
        )
        
        # Configurar cliente S3
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=self.config.access_key_id,
            aws_secret_access_key=self.config.secret_access_key,
            region_name=self.config.region,
            endpoint_url=self.config.endpoint_url
        )
        
        self.s3_resource = boto3.resource(
            's3',
            aws_access_key_id=self.config.access_key_id,
            aws_secret_access_key=self.config.secret_access_key,
            region_name=self.config.region,
            endpoint_url=self.config.endpoint_url
        )
    
    def _generate_file_key(self, filename: str, package_id: Optional[int] = None) -> str:
        """
        Generar clave única para el archivo en S3
        
        Args:
            filename: Nombre del archivo
            package_id: ID del paquete (opcional)
            
        Returns:
            str: Clave única del archivo
        """
        timestamp = datetime.now().strftime("%Y/%m/%d")
        file_hash = hashlib.md5(f"{filename}_{datetime.now().isoformat()}".encode()).hexdigest()[:8]
        extension = Path(filename).suffix.lower()
        
        if package_id:
            return f"packages/{package_id}/{timestamp}/{file_hash}{extension}"
        else:
            return f"uploads/{timestamp}/{file_hash}{extension}"
    
    def _validate_file(self, filename: str, file_size: int) -> bool:
        """
        Validar archivo antes de subir
        
        Args:
            filename: Nombre del archivo
            file_size: Tamaño del archivo
            
        Returns:
            bool: Si el archivo es válido
        """
        # Verificar tamaño
        if file_size > self.config.max_file_size:
            logger.warning(f"Archivo demasiado grande: {file_size} bytes")
            return False
        
        # Verificar extensión
        extension = Path(filename).suffix.lower()
        if extension not in self.config.allowed_extensions:
            logger.warning(f"Extensión no permitida: {extension}")
            return False
        
        return True
    
    def _get_content_type(self, filename: str) -> str:
        """
        Obtener tipo de contenido del archivo
        
        Args:
            filename: Nombre del archivo
            
        Returns:
            str: Tipo de contenido MIME
        """
        content_type, _ = mimetypes.guess_type(filename)
        return content_type or 'application/octet-stream'
    
    async def upload_file(self, file_data: BinaryIO, filename: str, package_id: Optional[int] = None) -> S3FileInfo:
        """
        Subir archivo a S3
        
        Args:
            file_data: Datos del archivo
            filename: Nombre del archivo
            package_id: ID del paquete (opcional)
            
        Returns:
            S3FileInfo: Información del archivo subido
        """
        # Validar archivo
        file_size = len(file_data.read())
        file_data.seek(0)  # Resetear posición
        
        if not self._validate_file(filename, file_size):
            raise ValueError(f"Archivo inválido: {filename}")
        
        # Generar clave única
        file_key = self._generate_file_key(filename, package_id)
        content_type = self._get_content_type(filename)
        
        try:
            logger.info(f"Subiendo archivo {filename} a S3: {file_key}")
            
            # Subir archivo
            response = self.s3_client.upload_fileobj(
                file_data,
                self.config.bucket_name,
                file_key,
                ExtraArgs={
                    'ContentType': content_type,
                    'Metadata': {
                        'original-filename': filename,
                        'package-id': str(package_id) if package_id else '',
                        'uploaded-at': datetime.now().isoformat()
                    }
                }
            )
            
            # Obtener información del archivo
            head_response = self.s3_client.head_object(
                Bucket=self.config.bucket_name,
                Key=file_key
            )
            
            file_info = S3FileInfo(
                key=file_key,
                filename=filename,
                size=file_size,
                content_type=content_type,
                etag=head_response['ETag'].strip('"'),
                last_modified=head_response['LastModified'],
                url=self._get_public_url(file_key)
            )
            
            logger.info(f"Archivo subido exitosamente: {file_key}")
            return file_info
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"Error subiendo archivo a S3: {error_code} - {error_message}")
            raise RuntimeError(f"Error subiendo archivo: {error_message}")
        
        except Exception as e:
            logger.error(f"Error inesperado subiendo archivo: {e}")
            raise RuntimeError(f"Error inesperado: {str(e)}")
    
    async def download_file(self, file_key: str) -> Optional[Dict[str, Any]]:
        """
        Descargar archivo de S3
        
        Args:
            file_key: Clave del archivo en S3
            
        Returns:
            Optional[Dict[str, Any]]: Datos del archivo
        """
        try:
            logger.info(f"Descargando archivo de S3: {file_key}")
            
            # Obtener objeto
            response = self.s3_client.get_object(
                Bucket=self.config.bucket_name,
                Key=file_key
            )
            
            # Leer contenido
            content = response['Body'].read()
            
            # Obtener metadatos
            metadata = response.get('Metadata', {})
            original_filename = metadata.get('original-filename', file_key.split('/')[-1])
            
            return {
                'content': content,
                'filename': original_filename,
                'content_type': response['ContentType'],
                'size': response['ContentLength'],
                'etag': response['ETag'].strip('"'),
                'last_modified': response['LastModified']
            }
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.warning(f"Archivo no encontrado en S3: {file_key}")
                return None
            else:
                logger.error(f"Error descargando archivo de S3: {e}")
                raise RuntimeError(f"Error descargando archivo: {e}")
        
        except Exception as e:
            logger.error(f"Error inesperado descargando archivo: {e}")
            raise RuntimeError(f"Error inesperado: {str(e)}")
    
    def generate_presigned_url(self, file_key: str, expires_in: int = 3600) -> str:
        """
        Generar URL firmada para descarga
        
        Args:
            file_key: Clave del archivo en S3
            expires_in: Tiempo de expiración en segundos
            
        Returns:
            str: URL firmada
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.config.bucket_name,
                    'Key': file_key
                },
                ExpiresIn=expires_in
            )
            
            logger.info(f"URL firmada generada para {file_key}, expira en {expires_in} segundos")
            return url
            
        except Exception as e:
            logger.error(f"Error generando URL firmada: {e}")
            raise RuntimeError(f"Error generando URL: {str(e)}")
    
    def generate_upload_url(self, file_key: str, content_type: str, expires_in: int = 3600) -> str:
        """
        Generar URL firmada para subida
        
        Args:
            file_key: Clave del archivo en S3
            content_type: Tipo de contenido
            expires_in: Tiempo de expiración en segundos
            
        Returns:
            str: URL firmada para subida
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': self.config.bucket_name,
                    'Key': file_key,
                    'ContentType': content_type
                },
                ExpiresIn=expires_in
            )
            
            logger.info(f"URL de subida generada para {file_key}")
            return url
            
        except Exception as e:
            logger.error(f"Error generando URL de subida: {e}")
            raise RuntimeError(f"Error generando URL de subida: {str(e)}")
    
    async def delete_file(self, file_key: str) -> bool:
        """
        Eliminar archivo de S3
        
        Args:
            file_key: Clave del archivo en S3
            
        Returns:
            bool: Si la eliminación fue exitosa
        """
        try:
            logger.info(f"Eliminando archivo de S3: {file_key}")
            
            self.s3_client.delete_object(
                Bucket=self.config.bucket_name,
                Key=file_key
            )
            
            logger.info(f"Archivo eliminado exitosamente: {file_key}")
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.warning(f"Archivo no encontrado para eliminar: {file_key}")
                return True  # Considerar como éxito si no existe
            else:
                logger.error(f"Error eliminando archivo de S3: {e}")
                return False
        
        except Exception as e:
            logger.error(f"Error inesperado eliminando archivo: {e}")
            return False
    
    async def list_files(self, prefix: str = "", max_keys: int = 1000) -> List[S3FileInfo]:
        """
        Listar archivos en S3
        
        Args:
            prefix: Prefijo para filtrar archivos
            max_keys: Número máximo de archivos a listar
            
        Returns:
            List[S3FileInfo]: Lista de archivos
        """
        try:
            logger.info(f"Listando archivos en S3 con prefijo: {prefix}")
            
            response = self.s3_client.list_objects_v2(
                Bucket=self.config.bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys
            )
            
            files = []
            for obj in response.get('Contents', []):
                # Obtener metadatos
                head_response = self.s3_client.head_object(
                    Bucket=self.config.bucket_name,
                    Key=obj['Key']
                )
                
                metadata = head_response.get('Metadata', {})
                original_filename = metadata.get('original-filename', obj['Key'].split('/')[-1])
                
                file_info = S3FileInfo(
                    key=obj['Key'],
                    filename=original_filename,
                    size=obj['Size'],
                    content_type=head_response['ContentType'],
                    etag=head_response['ETag'].strip('"'),
                    last_modified=head_response['LastModified'],
                    url=self._get_public_url(obj['Key'])
                )
                files.append(file_info)
            
            logger.info(f"Listados {len(files)} archivos")
            return files
            
        except Exception as e:
            logger.error(f"Error listando archivos: {e}")
            return []
    
    async def get_bucket_stats(self) -> Dict[str, Any]:
        """
        Obtener estadísticas del bucket
        
        Returns:
            Dict[str, Any]: Estadísticas del bucket
        """
        try:
            # Contar objetos
            response = self.s3_client.list_objects_v2(
                Bucket=self.config.bucket_name
            )
            
            total_files = len(response.get('Contents', []))
            total_size = sum(obj['Size'] for obj in response.get('Contents', []))
            
            # Obtener información del bucket
            bucket_info = self.s3_client.head_bucket(
                Bucket=self.config.bucket_name
            )
            
            return {
                'bucket_name': self.config.bucket_name,
                'total_files': total_files,
                'total_size_bytes': total_size,
                'total_size_mb': total_size / (1024 * 1024),
                'region': self.config.region,
                'creation_date': bucket_info.get('ResponseMetadata', {}).get('HTTPHeaders', {}).get('date')
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas del bucket: {e}")
            return {
                'bucket_name': self.config.bucket_name,
                'error': str(e)
            }
    
    def _get_public_url(self, file_key: str) -> Optional[str]:
        """
        Obtener URL pública del archivo (si está configurado)
        
        Args:
            file_key: Clave del archivo en S3
            
        Returns:
            Optional[str]: URL pública
        """
        if hasattr(settings, 'S3_PUBLIC_URL') and settings.S3_PUBLIC_URL:
            return f"{settings.S3_PUBLIC_URL}/{file_key}"
        return None
    
    async def copy_file(self, source_key: str, destination_key: str) -> bool:
        """
        Copiar archivo dentro de S3
        
        Args:
            source_key: Clave del archivo origen
            destination_key: Clave del archivo destino
            
        Returns:
            bool: Si la copia fue exitosa
        """
        try:
            logger.info(f"Copiando archivo de {source_key} a {destination_key}")
            
            copy_source = {
                'Bucket': self.config.bucket_name,
                'Key': source_key
            }
            
            self.s3_client.copy_object(
                CopySource=copy_source,
                Bucket=self.config.bucket_name,
                Key=destination_key
            )
            
            logger.info(f"Archivo copiado exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"Error copiando archivo: {e}")
            return False
    
    async def move_file(self, source_key: str, destination_key: str) -> bool:
        """
        Mover archivo dentro de S3
        
        Args:
            source_key: Clave del archivo origen
            destination_key: Clave del archivo destino
            
        Returns:
            bool: Si el movimiento fue exitoso
        """
        # Copiar archivo
        if await self.copy_file(source_key, destination_key):
            # Eliminar archivo original
            return await self.delete_file(source_key)
        return False

# Instancia global del servicio
s3_service = S3Service()

# Funciones de conveniencia
async def upload_file_to_s3(file_data: BinaryIO, filename: str, package_id: Optional[int] = None) -> S3FileInfo:
    """
    Función de conveniencia para subir archivo a S3
    
    Args:
        file_data: Datos del archivo
        filename: Nombre del archivo
        package_id: ID del paquete (opcional)
        
    Returns:
        S3FileInfo: Información del archivo subido
    """
    return await s3_service.upload_file(file_data, filename, package_id)

async def download_file_from_s3(file_key: str) -> Optional[Dict[str, Any]]:
    """
    Función de conveniencia para descargar archivo de S3
    
    Args:
        file_key: Clave del archivo en S3
        
    Returns:
        Optional[Dict[str, Any]]: Datos del archivo
    """
    return await s3_service.download_file(file_key)

def get_s3_presigned_url(file_key: str, expires_in: int = 3600) -> str:
    """
    Función de conveniencia para obtener URL firmada
    
    Args:
        file_key: Clave del archivo en S3
        expires_in: Tiempo de expiración en segundos
        
    Returns:
        str: URL firmada
    """
    return s3_service.generate_presigned_url(file_key, expires_in)
