"""
Notification Service
==================

Servicio unificado de notificaciones que integra SMS, email y WhatsApp.
"""

import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
from pydantic import BaseModel, Field

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from .external.liwa_sms import LIWASMSService, LIWASMSMessage, send_quick_sms
from .external.email_service import EmailService, EmailMessage, send_quick_email
from ..models.notification import Notification, NotificationType, NotificationStatus
from ..models.package import Package
from ..models.customer import Customer
from ..core.logging import get_logger

logger = get_logger(__name__)

class NotificationPriority(Enum):
    """Prioridad de notificación"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

class NotificationTemplate(Enum):
    """Plantillas de notificación"""
    PACKAGE_ANNOUNCED = "package_announced"
    PACKAGE_RECEIVED = "package_received"
    PACKAGE_DELIVERED = "package_delivered"
    PACKAGE_EXPIRED = "package_expired"
    STORAGE_WARNING = "storage_warning"
    SYSTEM_ALERT = "system_alert"

class NotificationRequest(BaseModel):
    """Solicitud de notificación"""
    customer_id: int = Field(..., description="ID del cliente")
    package_id: Optional[int] = Field(None, description="ID del paquete")
    notification_type: NotificationType = Field(..., description="Tipo de notificación")
    template: NotificationTemplate = Field(..., description="Plantilla a usar")
    priority: NotificationPriority = Field(NotificationPriority.NORMAL, description="Prioridad")
    channels: List[str] = Field(default=["sms"], description="Canales de envío")
    custom_message: Optional[str] = Field(None, description="Mensaje personalizado")
    scheduled_time: Optional[datetime] = Field(None, description="Tiempo programado")
    template_data: Dict[str, Any] = Field(default_factory=dict, description="Datos para la plantilla")

class NotificationResult(BaseModel):
    """Resultado de notificación"""
    success: bool = Field(..., description="Si la notificación fue exitosa")
    notification_id: Optional[int] = Field(None, description="ID de la notificación")
    external_id: Optional[str] = Field(None, description="ID externo")
    error_message: Optional[str] = Field(None, description="Mensaje de error")
    channel: str = Field(..., description="Canal utilizado")

class NotificationService:
    """Servicio unificado de notificaciones"""
    
    def __init__(self, db: Session):
        self.db = db
        self.sms_service = LIWASMSService()
        self.email_service = EmailService()
    
    def _get_template_message(self, template: NotificationTemplate, template_data: Dict[str, Any]) -> str:
        """
        Obtener mensaje de la plantilla
        
        Args:
            template: Plantilla a usar
            template_data: Datos para la plantilla
            
        Returns:
            str: Mensaje formateado
        """
        if template == NotificationTemplate.PACKAGE_ANNOUNCED:
            tracking_number = template_data.get("tracking_number", "")
            package_cost = template_data.get("package_cost", "")
            return f"Su paquete ha sido anunciado. Tracking: {tracking_number}. Costo: {package_cost}. Recójalo en nuestras instalaciones."
        
        elif template == NotificationTemplate.PACKAGE_RECEIVED:
            tracking_number = template_data.get("tracking_number", "")
            return f"Su paquete ha sido recibido. Tracking: {tracking_number}. Está listo para entrega."
        
        elif template == NotificationTemplate.PACKAGE_DELIVERED:
            tracking_number = template_data.get("tracking_number", "")
            delivery_number = template_data.get("delivery_number", "")
            amount_paid = template_data.get("amount_paid", "")
            return f"Su paquete ha sido entregado. Tracking: {tracking_number}. Entrega: {delivery_number}. Pagado: {amount_paid}."
        
        elif template == NotificationTemplate.PACKAGE_EXPIRED:
            tracking_number = template_data.get("tracking_number", "")
            return f"Su paquete ha expirado. Tracking: {tracking_number}. Contacte nuestras oficinas."
        
        elif template == NotificationTemplate.STORAGE_WARNING:
            tracking_number = template_data.get("tracking_number", "")
            days_in_storage = template_data.get("days_in_storage", "")
            return f"Su paquete lleva {days_in_storage} días en bodega. Tracking: {tracking_number}. Recójalo pronto."
        
        elif template == NotificationTemplate.SYSTEM_ALERT:
            return template_data.get("message", "Alerta del sistema de paquetería.")
        
        else:
            return template_data.get("custom_message", "Notificación del sistema de paquetería.")
    
    def _get_email_template(self, template: NotificationTemplate, template_data: Dict[str, Any]) -> EmailMessage:
        """
        Obtener plantilla de email
        
        Args:
            template: Plantilla a usar
            template_data: Datos para la plantilla
            
        Returns:
            EmailMessage: Mensaje de email
        """
        customer_name = template_data.get("customer_name", "")
        customer_email = template_data.get("customer_email", "")
        tracking_number = template_data.get("tracking_number", "")
        
        if template == NotificationTemplate.PACKAGE_ANNOUNCED:
            package_cost = template_data.get("package_cost", "")
            return self.email_service.create_package_announcement_email(
                customer_name, customer_email, tracking_number, package_cost
            )
        
        elif template == NotificationTemplate.PACKAGE_RECEIVED:
            return self.email_service.create_package_received_email(
                customer_name, customer_email, tracking_number
            )
        
        elif template == NotificationTemplate.PACKAGE_DELIVERED:
            delivery_number = template_data.get("delivery_number", "")
            amount_paid = template_data.get("amount_paid", "")
            return self.email_service.create_package_delivered_email(
                customer_name, customer_email, tracking_number, delivery_number, amount_paid
            )
        
        else:
            # Email genérico
            subject = f"Notificación - {template.value.replace('_', ' ').title()}"
            body = self._get_template_message(template, template_data)
            return EmailMessage(
                to_email=customer_email,
                to_name=customer_name,
                subject=subject,
                body_text=body
            )
    
    async def send_notification(self, request: NotificationRequest) -> List[NotificationResult]:
        """
        Enviar notificación
        
        Args:
            request: Solicitud de notificación
            
        Returns:
            List[NotificationResult]: Resultados por canal
        """
        results = []
        
        # Obtener cliente y paquete
        customer = self.db.query(Customer).filter(Customer.id == request.customer_id).first()
        if not customer:
            logger.error(f"Cliente no encontrado: {request.customer_id}")
            return [NotificationResult(
                success=False,
                error_message="Cliente no encontrado",
                channel="unknown"
            )]
        
        package = None
        if request.package_id:
            package = self.db.query(Package).filter(Package.id == request.package_id).first()
        
        # Preparar datos de plantilla
        template_data = {
            "customer_name": customer.full_name,
            "customer_email": customer.email,
            "customer_phone": customer.phone_number,
            **request.template_data
        }
        
        if package:
            template_data.update({
                "tracking_number": package.tracking_number,
                "package_cost": package.formatted_cost,
                "package_description": package.description
            })
        
        # Enviar por cada canal solicitado
        for channel in request.channels:
            try:
                if channel == "sms":
                    result = await self._send_sms_notification(customer, request, template_data)
                elif channel == "email":
                    result = await self._send_email_notification(customer, request, template_data)
                elif channel == "whatsapp":
                    result = await self._send_whatsapp_notification(customer, request, template_data)
                else:
                    result = NotificationResult(
                        success=False,
                        error_message=f"Canal no soportado: {channel}",
                        channel=channel
                    )
                
                results.append(result)
                
            except Exception as e:
                logger.error(f"Error enviando notificación por {channel}: {e}")
                results.append(NotificationResult(
                    success=False,
                    error_message=str(e),
                    channel=channel
                ))
        
        return results
    
    async def _send_sms_notification(self, customer: Customer, request: NotificationRequest, template_data: Dict[str, Any]) -> NotificationResult:
        """
        Enviar notificación SMS
        
        Args:
            customer: Cliente
            request: Solicitud de notificación
            template_data: Datos de plantilla
            
        Returns:
            NotificationResult: Resultado del envío
        """
        try:
            # Crear mensaje SMS
            message = self._get_template_message(request.template, template_data)
            if request.custom_message:
                message = request.custom_message
            
            # Enviar SMS
            async with self.sms_service as sms:
                sms_message = LIWASMSMessage(
                    phone_number=customer.phone_number,
                    message=message,
                    message_id=f"sms_{request.template.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    scheduled_time=request.scheduled_time
                )
                
                response = await sms.send_sms(sms_message)
                
                # Crear registro en base de datos
                notification = Notification(
                    notification_type=request.notification_type,
                    status=NotificationStatus.SENT if response.success else NotificationStatus.FAILED,
                    customer_id=customer.id,
                    package_id=request.package_id,
                    recipient=customer.phone_number,
                    message=message,
                    external_id=response.message_id,
                    error_message=response.error_message if not response.success else None,
                    sent_at=datetime.now() if response.success else None
                )
                
                self.db.add(notification)
                self.db.commit()
                
                return NotificationResult(
                    success=response.success,
                    notification_id=notification.id,
                    external_id=response.message_id,
                    error_message=response.error_message,
                    channel="sms"
                )
                
        except Exception as e:
            logger.error(f"Error enviando SMS: {e}")
            return NotificationResult(
                success=False,
                error_message=str(e),
                channel="sms"
            )
    
    async def _send_email_notification(self, customer: Customer, request: NotificationRequest, template_data: Dict[str, Any]) -> NotificationResult:
        """
        Enviar notificación por email
        
        Args:
            customer: Cliente
            request: Solicitud de notificación
            template_data: Datos de plantilla
            
        Returns:
            NotificationResult: Resultado del envío
        """
        try:
            if not customer.email:
                return NotificationResult(
                    success=False,
                    error_message="Cliente no tiene email registrado",
                    channel="email"
                )
            
            # Crear mensaje de email
            email_message = self._get_email_template(request.template, template_data)
            if request.custom_message:
                email_message.body_text = request.custom_message
                email_message.body_html = f"<p>{request.custom_message}</p>"
            
            # Enviar email
            response = await self.email_service.send_email(email_message)
            
            # Crear registro en base de datos
            notification = Notification(
                notification_type=request.notification_type,
                status=NotificationStatus.SENT if response.success else NotificationStatus.FAILED,
                customer_id=customer.id,
                package_id=request.package_id,
                recipient=customer.email,
                message=email_message.body_text or email_message.body_html or "",
                external_id=response.message_id,
                error_message=response.error_message if not response.success else None,
                sent_at=datetime.now() if response.success else None
            )
            
            self.db.add(notification)
            self.db.commit()
            
            return NotificationResult(
                success=response.success,
                notification_id=notification.id,
                external_id=response.message_id,
                error_message=response.error_message,
                channel="email"
            )
            
        except Exception as e:
            logger.error(f"Error enviando email: {e}")
            return NotificationResult(
                success=False,
                error_message=str(e),
                channel="email"
            )
    
    async def _send_whatsapp_notification(self, customer: Customer, request: NotificationRequest, template_data: Dict[str, Any]) -> NotificationResult:
        """
        Enviar notificación por WhatsApp (placeholder)
        
        Args:
            customer: Cliente
            request: Solicitud de notificación
            template_data: Datos de plantilla
            
        Returns:
            NotificationResult: Resultado del envío
        """
        # TODO: Implementar integración con WhatsApp Business API
        logger.info(f"WhatsApp notificación para {customer.phone_number}: {self._get_template_message(request.template, template_data)}")
        
        return NotificationResult(
            success=True,
            error_message="WhatsApp no implementado aún",
            channel="whatsapp"
        )
    
    async def send_package_announcement(self, package: Package) -> List[NotificationResult]:
        """
        Enviar notificación de anuncio de paquete
        
        Args:
            package: Paquete anunciado
            
        Returns:
            List[NotificationResult]: Resultados de notificación
        """
        request = NotificationRequest(
            customer_id=package.customer_id,
            package_id=package.id,
            notification_type=NotificationType.SMS,
            template=NotificationTemplate.PACKAGE_ANNOUNCED,
            priority=NotificationPriority.HIGH if package.is_urgent else NotificationPriority.NORMAL,
            channels=["sms", "email"] if package.customer.email else ["sms"],
            template_data={
                "tracking_number": package.tracking_number,
                "package_cost": package.formatted_cost
            }
        )
        
        return await self.send_notification(request)
    
    async def send_package_received(self, package: Package) -> List[NotificationResult]:
        """
        Enviar notificación de paquete recibido
        
        Args:
            package: Paquete recibido
            
        Returns:
            List[NotificationResult]: Resultados de notificación
        """
        request = NotificationRequest(
            customer_id=package.customer_id,
            package_id=package.id,
            notification_type=NotificationType.SMS,
            template=NotificationTemplate.PACKAGE_RECEIVED,
            priority=NotificationPriority.NORMAL,
            channels=["sms", "email"] if package.customer.email else ["sms"],
            template_data={
                "tracking_number": package.tracking_number
            }
        )
        
        return await self.send_notification(request)
    
    async def send_package_delivered(self, package: Package, delivery_number: str, amount_paid: str) -> List[NotificationResult]:
        """
        Enviar notificación de paquete entregado
        
        Args:
            package: Paquete entregado
            delivery_number: Número de entrega
            amount_paid: Monto pagado
            
        Returns:
            List[NotificationResult]: Resultados de notificación
        """
        request = NotificationRequest(
            customer_id=package.customer_id,
            package_id=package.id,
            notification_type=NotificationType.SMS,
            template=NotificationTemplate.PACKAGE_DELIVERED,
            priority=NotificationPriority.NORMAL,
            channels=["sms", "email"] if package.customer.email else ["sms"],
            template_data={
                "tracking_number": package.tracking_number,
                "delivery_number": delivery_number,
                "amount_paid": amount_paid
            }
        )
        
        return await self.send_notification(request)
    
    async def send_storage_warning(self, package: Package, days_in_storage: int) -> List[NotificationResult]:
        """
        Enviar advertencia de bodegaje
        
        Args:
            package: Paquete en bodega
            days_in_storage: Días en bodega
            
        Returns:
            List[NotificationResult]: Resultados de notificación
        """
        request = NotificationRequest(
            customer_id=package.customer_id,
            package_id=package.id,
            notification_type=NotificationType.SMS,
            template=NotificationTemplate.STORAGE_WARNING,
            priority=NotificationPriority.HIGH,
            channels=["sms", "email"] if package.customer.email else ["sms"],
            template_data={
                "tracking_number": package.tracking_number,
                "days_in_storage": days_in_storage
            }
        )
        
        return await self.send_notification(request)
    
    def get_notification_stats(self) -> Dict[str, Any]:
        """
        Obtener estadísticas de notificaciones
        
        Returns:
            Dict[str, Any]: Estadísticas
        """
        total_notifications = self.db.query(Notification).count()
        sent_notifications = self.db.query(Notification).filter(
            Notification.status == NotificationStatus.SENT
        ).count()
        failed_notifications = self.db.query(Notification).filter(
            Notification.status == NotificationStatus.FAILED
        ).count()
        pending_notifications = self.db.query(Notification).filter(
            Notification.status == NotificationStatus.PENDING
        ).count()
        
        success_rate = (sent_notifications / total_notifications * 100) if total_notifications > 0 else 0
        
        return {
            "total_notifications": total_notifications,
            "sent_notifications": sent_notifications,
            "failed_notifications": failed_notifications,
            "pending_notifications": pending_notifications,
            "success_rate": round(success_rate, 2)
        }
    
    def cleanup_old_notifications(self, days: int = 90) -> int:
        """
        Limpiar notificaciones antiguas
        
        Args:
            days: Días a mantener
            
        Returns:
            int: Número de notificaciones eliminadas
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Eliminar notificaciones antiguas que no sean fallidas
        deleted_count = self.db.query(Notification).filter(
            and_(
                Notification.sent_at < cutoff_date,
                Notification.status != NotificationStatus.FAILED
            )
        ).delete()
        
        self.db.commit()
        
        logger.info(f"Eliminadas {deleted_count} notificaciones antiguas")
        return deleted_count
    
    async def process_scheduled_notifications(self) -> int:
        """
        Procesar notificaciones programadas
        
        Returns:
            int: Número de notificaciones procesadas
        """
        # Obtener notificaciones programadas pendientes
        pending_notifications = self.db.query(Notification).filter(
            and_(
                Notification.status == NotificationStatus.PENDING,
                Notification.scheduled_time <= datetime.now()
            )
        ).all()
        
        processed_count = 0
        
        for notification in pending_notifications:
            try:
                # Reintentar envío
                if notification.notification_type == NotificationType.SMS:
                    # Reintentar SMS
                    customer = self.db.query(Customer).filter(Customer.id == notification.customer_id).first()
                    if customer:
                        async with self.sms_service as sms:
                            sms_message = LIWASMSMessage(
                                phone_number=customer.phone_number,
                                message=notification.message
                            )
                            response = await sms.send_sms(sms_message)
                            
                            if response.success:
                                notification.status = NotificationStatus.SENT
                                notification.sent_at = datetime.now()
                                notification.external_id = response.message_id
                                processed_count += 1
                            else:
                                notification.status = NotificationStatus.FAILED
                                notification.error_message = response.error_message
                
                self.db.commit()
                
            except Exception as e:
                logger.error(f"Error procesando notificación programada {notification.id}: {e}")
                notification.status = NotificationStatus.FAILED
                notification.error_message = str(e)
                self.db.commit()
        
        return processed_count

# Funciones de conveniencia
async def send_package_notification(db: Session, package: Package, notification_type: str) -> List[NotificationResult]:
    """
    Función de conveniencia para enviar notificación de paquete
    
    Args:
        db: Sesión de base de datos
        package: Paquete
        notification_type: Tipo de notificación
        
    Returns:
        List[NotificationResult]: Resultados de notificación
    """
    service = NotificationService(db)
    
    if notification_type == "announced":
        return await service.send_package_announcement(package)
    elif notification_type == "received":
        return await service.send_package_received(package)
    else:
        logger.error(f"Tipo de notificación no válido: {notification_type}")
        return []
