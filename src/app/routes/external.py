"""
External API Routes
==================

Rutas para integración con APIs externas.
"""

from typing import Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.auth import get_current_active_user
from ..models.user import User
from ..services.external.liwa_sms import LIWASMSService, LIWASMSMessage, send_quick_sms
from ..services.external.aws_s3 import s3_service, upload_file_to_s3, download_file_from_s3, get_s3_presigned_url
from ..services.external.email_service import email_service, send_quick_email
from ..core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/external", tags=["External APIs"])

# =============================================================================
# SMS Routes
# =============================================================================

@router.post("/sms/send")
async def send_sms(
    phone_number: str = Form(...),
    message: str = Form(...),
    message_id: Optional[str] = Form(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Enviar SMS a través de LIWA
    
    Args:
        phone_number: Número de teléfono
        message: Mensaje a enviar
        message_id: ID opcional del mensaje
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        dict: Resultado del envío
    """
    try:
        async with LIWASMSService() as sms_service:
            sms_message = LIWASMSMessage(
                phone_number=phone_number,
                message=message,
                message_id=message_id
            )
            
            response = await sms_service.send_sms(sms_message)
            
            return {
                "success": response.success,
                "message_id": response.message_id,
                "external_id": response.external_id,
                "cost": response.cost,
                "remaining_balance": response.remaining_balance,
                "error_message": response.error_message
            }
    
    except Exception as e:
        logger.error(f"Error enviando SMS: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error enviando SMS: {str(e)}"
        )

@router.post("/sms/bulk")
async def send_bulk_sms(
    messages: List[dict],
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Enviar múltiples SMS
    
    Args:
        messages: Lista de mensajes
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        dict: Resultados del envío masivo
    """
    try:
        sms_messages = []
        for msg in messages:
            sms_message = LIWASMSMessage(
                phone_number=msg["phone_number"],
                message=msg["message"],
                message_id=msg.get("message_id")
            )
            sms_messages.append(sms_message)
        
        async with LIWASMSService() as sms_service:
            responses = await sms_service.send_bulk_sms(sms_messages)
            
            results = []
            for response in responses:
                results.append({
                    "success": response.success,
                    "message_id": response.message_id,
                    "external_id": response.external_id,
                    "error_message": response.error_message
                })
            
            return {
                "total_sent": len([r for r in results if r["success"]]),
                "total_failed": len([r for r in results if not r["success"]]),
                "results": results
            }
    
    except Exception as e:
        logger.error(f"Error enviando SMS masivo: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error enviando SMS masivo: {str(e)}"
        )

@router.get("/sms/balance")
async def get_sms_balance(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Obtener saldo de SMS
    
    Args:
        current_user: Usuario actual
        
    Returns:
        dict: Información del saldo
    """
    try:
        async with LIWASMSService() as sms_service:
            balance_info = await sms_service.check_balance()
            
            return balance_info
    
    except Exception as e:
        logger.error(f"Error obteniendo saldo SMS: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo saldo: {str(e)}"
        )

@router.get("/sms/status/{message_id}")
async def get_sms_status(
    message_id: str,
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Obtener estado de un SMS
    
    Args:
        message_id: ID del mensaje
        current_user: Usuario actual
        
    Returns:
        dict: Estado del mensaje
    """
    try:
        async with LIWASMSService() as sms_service:
            status_info = await sms_service.get_message_status(message_id)
            
            return status_info
    
    except Exception as e:
        logger.error(f"Error obteniendo estado SMS: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo estado: {str(e)}"
        )

# =============================================================================
# S3 Routes
# =============================================================================

@router.post("/s3/upload")
async def upload_file_s3(
    file: UploadFile = File(...),
    package_id: Optional[int] = Form(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Subir archivo a S3
    
    Args:
        file: Archivo a subir
        package_id: ID del paquete (opcional)
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        dict: Información del archivo subido
    """
    try:
        # Leer contenido del archivo
        content = await file.read()
        
        # Subir a S3
        file_info = await upload_file_to_s3(content, file.filename, package_id)
        
        return {
            "success": True,
            "file_key": file_info.key,
            "filename": file_info.filename,
            "size": file_info.size,
            "content_type": file_info.content_type,
            "url": file_info.url,
            "etag": file_info.etag
        }
    
    except Exception as e:
        logger.error(f"Error subiendo archivo a S3: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error subiendo archivo: {str(e)}"
        )

@router.get("/s3/download/{file_key:path}")
async def download_file_s3(
    file_key: str,
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Descargar archivo de S3
    
    Args:
        file_key: Clave del archivo en S3
        current_user: Usuario actual
        
    Returns:
        StreamingResponse: Archivo descargado
    """
    try:
        file_data = await download_file_from_s3(file_key)
        
        if not file_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Archivo no encontrado"
            )
        
        return StreamingResponse(
            iter([file_data["content"]]),
            media_type=file_data["content_type"],
            headers={
                "Content-Disposition": f"attachment; filename={file_data['filename']}"
            }
        )
    
    except Exception as e:
        logger.error(f"Error descargando archivo de S3: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error descargando archivo: {str(e)}"
        )

@router.get("/s3/presigned-url/{file_key:path}")
async def get_presigned_url(
    file_key: str,
    expires_in: int = 3600,
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Obtener URL firmada para descarga
    
    Args:
        file_key: Clave del archivo en S3
        expires_in: Tiempo de expiración en segundos
        current_user: Usuario actual
        
    Returns:
        dict: URL firmada
    """
    try:
        url = get_s3_presigned_url(file_key, expires_in)
        
        return {
            "success": True,
            "url": url,
            "expires_in": expires_in,
            "file_key": file_key
        }
    
    except Exception as e:
        logger.error(f"Error generando URL firmada: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generando URL: {str(e)}"
        )

@router.delete("/s3/delete/{file_key:path}")
async def delete_file_s3(
    file_key: str,
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Eliminar archivo de S3
    
    Args:
        file_key: Clave del archivo en S3
        current_user: Usuario actual
        
    Returns:
        dict: Resultado de la eliminación
    """
    try:
        success = await s3_service.delete_file(file_key)
        
        return {
            "success": success,
            "file_key": file_key
        }
    
    except Exception as e:
        logger.error(f"Error eliminando archivo de S3: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error eliminando archivo: {str(e)}"
        )

@router.get("/s3/list")
async def list_s3_files(
    prefix: Optional[str] = None,
    max_keys: int = 1000,
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Listar archivos en S3
    
    Args:
        prefix: Prefijo para filtrar
        max_keys: Número máximo de archivos
        current_user: Usuario actual
        
    Returns:
        dict: Lista de archivos
    """
    try:
        files = await s3_service.list_files(prefix, max_keys)
        
        file_list = []
        for file_info in files:
            file_list.append({
                "key": file_info.key,
                "filename": file_info.filename,
                "size": file_info.size,
                "content_type": file_info.content_type,
                "url": file_info.url,
                "last_modified": file_info.last_modified.isoformat()
            })
        
        return {
            "success": True,
            "files": file_list,
            "total_files": len(file_list)
        }
    
    except Exception as e:
        logger.error(f"Error listando archivos de S3: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listando archivos: {str(e)}"
        )

@router.get("/s3/stats")
async def get_s3_stats(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Obtener estadísticas de S3
    
    Args:
        current_user: Usuario actual
        
    Returns:
        dict: Estadísticas del bucket
    """
    try:
        stats = await s3_service.get_bucket_stats()
        
        return {
            "success": True,
            "stats": stats
        }
    
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas de S3: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo estadísticas: {str(e)}"
        )

# =============================================================================
# Email Routes
# =============================================================================

@router.post("/email/send")
async def send_email(
    to_email: str = Form(...),
    subject: str = Form(...),
    body: str = Form(...),
    to_name: Optional[str] = Form(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Enviar email
    
    Args:
        to_email: Email destinatario
        subject: Asunto del email
        body: Cuerpo del email
        to_name: Nombre del destinatario (opcional)
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        dict: Resultado del envío
    """
    try:
        response = await send_quick_email(to_email, subject, body, to_name)
        
        return {
            "success": response.success,
            "message_id": response.message_id,
            "error_message": response.error_message
        }
    
    except Exception as e:
        logger.error(f"Error enviando email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error enviando email: {str(e)}"
        )

@router.post("/email/bulk")
async def send_bulk_email(
    emails: List[dict],
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Enviar múltiples emails
    
    Args:
        emails: Lista de emails
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        dict: Resultados del envío masivo
    """
    try:
        from ..services.external.email_service import EmailMessage
        
        email_messages = []
        for email_data in emails:
            email_message = EmailMessage(
                to_email=email_data["to_email"],
                subject=email_data["subject"],
                body_text=email_data["body"],
                to_name=email_data.get("to_name")
            )
            email_messages.append(email_message)
        
        responses = await email_service.send_bulk_email(email_messages)
        
        results = []
        for response in responses:
            results.append({
                "success": response.success,
                "message_id": response.message_id,
                "error_message": response.error_message
            })
        
        return {
            "total_sent": len([r for r in results if r["success"]]),
            "total_failed": len([r for r in results if not r["success"]]),
            "results": results
        }
    
    except Exception as e:
        logger.error(f"Error enviando emails masivos: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error enviando emails masivos: {str(e)}"
        )

# =============================================================================
# Health Check Routes
# =============================================================================

@router.get("/health/sms")
async def sms_health_check(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Health check para SMS
    
    Args:
        current_user: Usuario actual
        
    Returns:
        dict: Estado del servicio SMS
    """
    try:
        async with LIWASMSService() as sms_service:
            balance_info = await sms_service.check_balance()
            
            return {
                "service": "sms",
                "status": "healthy" if balance_info.get("success") else "unhealthy",
                "balance": balance_info.get("balance", 0),
                "currency": balance_info.get("currency", "COP")
            }
    
    except Exception as e:
        logger.error(f"Error en health check SMS: {e}")
        return {
            "service": "sms",
            "status": "unhealthy",
            "error": str(e)
        }

@router.get("/health/s3")
async def s3_health_check(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Health check para S3
    
    Args:
        current_user: Usuario actual
        
    Returns:
        dict: Estado del servicio S3
    """
    try:
        stats = await s3_service.get_bucket_stats()
        
        return {
            "service": "s3",
            "status": "healthy" if "error" not in stats else "unhealthy",
            "bucket_name": stats.get("bucket_name"),
            "total_files": stats.get("total_files", 0),
            "total_size_mb": stats.get("total_size_mb", 0)
        }
    
    except Exception as e:
        logger.error(f"Error en health check S3: {e}")
        return {
            "service": "s3",
            "status": "unhealthy",
            "error": str(e)
        }

@router.get("/health/email")
async def email_health_check(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Health check para Email
    
    Args:
        current_user: Usuario actual
        
    Returns:
        dict: Estado del servicio Email
    """
    try:
        # Verificar configuración de email
        from ..core.config import settings
        
        config_ok = all([
            settings.SMTP_HOST,
            settings.SMTP_USERNAME,
            settings.SMTP_PASSWORD,
            settings.FROM_EMAIL
        ])
        
        return {
            "service": "email",
            "status": "healthy" if config_ok else "unhealthy",
            "smtp_host": settings.SMTP_HOST,
            "from_email": settings.FROM_EMAIL
        }
    
    except Exception as e:
        logger.error(f"Error en health check Email: {e}")
        return {
            "service": "email",
            "status": "unhealthy",
            "error": str(e)
        }

@router.get("/health/all")
async def all_external_services_health_check(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Health check para todos los servicios externos
    
    Args:
        current_user: Usuario actual
        
    Returns:
        dict: Estado de todos los servicios
    """
    sms_status = await sms_health_check(current_user)
    s3_status = await s3_health_check(current_user)
    email_status = await email_health_check(current_user)
    
    all_healthy = all([
        sms_status.get("status") == "healthy",
        s3_status.get("status") == "healthy",
        email_status.get("status") == "healthy"
    ])
    
    return {
        "overall_status": "healthy" if all_healthy else "degraded",
        "services": {
            "sms": sms_status,
            "s3": s3_status,
            "email": email_status
        }
    }
