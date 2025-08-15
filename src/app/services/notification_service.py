"""
Notification Service
===================

Servicio para gestión de notificaciones con integración SMS.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc
import logging
import requests
import json

from ..models.notification import Notification, NotificationType, NotificationStatus
from ..models.customer import Customer
from ..models.package import Package
from ..schemas.notification import (
    NotificationCreate, NotificationUpdate, NotificationSearch,
    NotificationStats, NotificationBulkSend, NotificationRetry
)
from ..core.config import settings

logger = logging.getLogger(__name__)

class NotificationService:
    """Servicio para gestión de notificaciones"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_notification(self, notification_data: NotificationCreate) -> Notification:
        """
        Crear una nueva notificación
        
        Args:
            notification_data: Datos de la notificación
            
        Returns:
            Notification: Notificación creada
        """
        try:
            notification = Notification(
                notification_type=notification_data.notification_type,
                customer_id=notification_data.customer_id,
                package_id=notification_data.package_id,
                recipient=notification_data.recipient,
                message=notification_data.message,
                scheduled_at=notification_data.scheduled_at,
                priority=notification_data.priority,
                retry_count=notification_data.retry_count
            )
            
            self.db.add(notification)
            self.db.commit()
            self.db.refresh(notification)
            
            logger.info(f"Notificación creada: {notification.id} - {notification.notification_type.value}")
            return notification
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creando notificación: {e}")
            raise
    
    def send_sms(self, phone_number: str, message: str, 
                 package_id: Optional[int] = None, customer_id: Optional[int] = None) -> Notification:
        """
        Enviar SMS
        
        Args:
            phone_number: Número de teléfono
            message: Mensaje a enviar
            package_id: ID del paquete (opcional)
            customer_id: ID del cliente (opcional)
            
        Returns:
            Notification: Notificación creada
        """
        try:
            # Crear notificación
            notification_data = NotificationCreate(
                notification_type=NotificationType.SMS,
                customer_id=customer_id,
                package_id=package_id,
                recipient=phone_number,
                message=message,
                priority=1
            )
            
            notification = self.create_notification(notification_data)
            
            # Enviar SMS inmediatamente
            success = self._send_sms_via_api(phone_number, message, notification)
            
            if success:
                notification.mark_as_sent()
            else:
                notification.mark_as_failed("Error enviando SMS")
            
            self.db.commit()
            self.db.refresh(notification)
            
            return notification
            
        except Exception as e:
            logger.error(f"Error enviando SMS: {e}")
            raise
    
    def send_email(self, email: str, subject: str, message: str,
                   package_id: Optional[int] = None, customer_id: Optional[int] = None) -> Notification:
        """
        Enviar email
        
        Args:
            email: Dirección de email
            subject: Asunto del email
            message: Contenido del email
            package_id: ID del paquete (opcional)
            customer_id: ID del cliente (opcional)
            
        Returns:
            Notification: Notificación creada
        """
        try:
            # Crear notificación
            notification_data = NotificationCreate(
                notification_type=NotificationType.EMAIL,
                customer_id=customer_id,
                package_id=package_id,
                recipient=email,
                message=f"Subject: {subject}\n\n{message}",
                priority=2
            )
            
            notification = self.create_notification(notification_data)
            
            # Enviar email inmediatamente
            success = self._send_email_via_api(email, subject, message, notification)
            
            if success:
                notification.mark_as_sent()
            else:
                notification.mark_as_failed("Error enviando email")
            
            self.db.commit()
            self.db.refresh(notification)
            
            return notification
            
        except Exception as e:
            logger.error(f"Error enviando email: {e}")
            raise
    
    def send_whatsapp(self, phone_number: str, message: str,
                      package_id: Optional[int] = None, customer_id: Optional[int] = None) -> Notification:
        """
        Enviar WhatsApp
        
        Args:
            phone_number: Número de teléfono
            message: Mensaje a enviar
            package_id: ID del paquete (opcional)
            customer_id: ID del cliente (opcional)
            
        Returns:
            Notification: Notificación creada
        """
        try:
            # Crear notificación
            notification_data = NotificationCreate(
                notification_type=NotificationType.WHATSAPP,
                customer_id=customer_id,
                package_id=package_id,
                recipient=phone_number,
                message=message,
                priority=1
            )
            
            notification = self.create_notification(notification_data)
            
            # Enviar WhatsApp inmediatamente
            success = self._send_whatsapp_via_api(phone_number, message, notification)
            
            if success:
                notification.mark_as_sent()
            else:
                notification.mark_as_failed("Error enviando WhatsApp")
            
            self.db.commit()
            self.db.refresh(notification)
            
            return notification
            
        except Exception as e:
            logger.error(f"Error enviando WhatsApp: {e}")
            raise
    
    def get_notification_by_id(self, notification_id: int) -> Optional[Notification]:
        """Obtener notificación por ID"""
        return self.db.query(Notification).filter(Notification.id == notification_id).first()
    
    def search_notifications(self, search_params: NotificationSearch) -> Dict[str, Any]:
        """
        Buscar notificaciones con filtros
        
        Args:
            search_params: Parámetros de búsqueda
            
        Returns:
            Dict con notificaciones y metadatos de paginación
        """
        query = self.db.query(Notification)
        
        # Aplicar filtros
        if search_params.notification_type:
            query = query.filter(Notification.notification_type == search_params.notification_type)
        
        if search_params.status:
            query = query.filter(Notification.status == search_params.status)
        
        if search_params.customer_id:
            query = query.filter(Notification.customer_id == search_params.customer_id)
        
        if search_params.package_id:
            query = query.filter(Notification.package_id == search_params.package_id)
        
        if search_params.recipient:
            query = query.filter(Notification.recipient == search_params.recipient)
        
        if search_params.date_from:
            query = query.filter(Notification.created_at >= search_params.date_from)
        
        if search_params.date_to:
            query = query.filter(Notification.created_at <= search_params.date_to)
        
        # Contar total
        total = query.count()
        
        # Aplicar paginación
        offset = (search_params.page - 1) * search_params.per_page
        notifications = query.offset(offset).limit(search_params.per_page).all()
        
        # Calcular páginas
        total_pages = (total + search_params.per_page - 1) // search_params.per_page
        
        return {
            "notifications": notifications,
            "total": total,
            "page": search_params.page,
            "per_page": search_params.per_page,
            "total_pages": total_pages
        }
    
    def get_notification_stats(self) -> NotificationStats:
        """Obtener estadísticas de notificaciones"""
        today = datetime.utcnow().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        # Totales
        total_notifications = self.db.query(Notification).count()
        pending_count = self.db.query(Notification).filter(Notification.status == NotificationStatus.PENDING).count()
        sent_count = self.db.query(Notification).filter(Notification.status == NotificationStatus.SENT).count()
        delivered_count = self.db.query(Notification).filter(Notification.status == NotificationStatus.DELIVERED).count()
        failed_count = self.db.query(Notification).filter(Notification.status == NotificationStatus.FAILED).count()
        
        # Notificaciones de hoy
        notifications_today = self.db.query(Notification).filter(
            func.date(Notification.created_at) == today
        ).count()
        
        notifications_this_week = self.db.query(Notification).filter(
            Notification.created_at >= week_ago
        ).count()
        
        notifications_this_month = self.db.query(Notification).filter(
            Notification.created_at >= month_ago
        ).count()
        
        # Notificaciones por tipo
        notifications_by_type = {}
        for notification_type in NotificationType:
            count = self.db.query(Notification).filter(Notification.notification_type == notification_type).count()
            notifications_by_type[notification_type.value] = count
        
        # Notificaciones por estado
        notifications_by_status = {}
        for status in NotificationStatus:
            count = self.db.query(Notification).filter(Notification.status == status).count()
            notifications_by_status[status.value] = count
        
        # Tasa de éxito
        success_rate = 0
        if total_notifications > 0:
            success_count = sent_count + delivered_count
            success_rate = (success_count / total_notifications) * 100
        
        # Tiempo promedio de entrega
        avg_delivery_time = self.db.query(
            func.avg(func.extract('epoch', Notification.delivered_at - Notification.sent_at) / 60)
        ).filter(
            Notification.delivered_at.isnot(None)
        ).scalar()
        
        return NotificationStats(
            total_notifications=total_notifications,
            pending_count=pending_count,
            sent_count=sent_count,
            delivered_count=delivered_count,
            failed_count=failed_count,
            notifications_today=notifications_today,
            notifications_this_week=notifications_this_week,
            notifications_this_month=notifications_this_month,
            notifications_by_type=notifications_by_type,
            notifications_by_status=notifications_by_status,
            success_rate=success_rate,
            average_delivery_time=float(avg_delivery_time) if avg_delivery_time else None
        )
    
    def retry_failed_notification(self, notification_id: int, force: bool = False) -> bool:
        """
        Reintentar notificación fallida
        
        Args:
            notification_id: ID de la notificación
            force: Forzar reintento incluso si no cumple condiciones
            
        Returns:
            bool: True si el reintento fue exitoso
        """
        notification = self.get_notification_by_id(notification_id)
        
        if not notification:
            return False
        
        if notification.status != NotificationStatus.FAILED:
            raise ValueError("Solo se pueden reintentar notificaciones fallidas")
        
        if not force and not notification.can_retry():
            raise ValueError("La notificación no puede ser reintentada")
        
        # Reintentar según el tipo
        success = False
        
        if notification.notification_type == NotificationType.SMS:
            success = self._send_sms_via_api(notification.recipient, notification.message, notification)
        elif notification.notification_type == NotificationType.EMAIL:
            # Extraer subject y message del email
            lines = notification.message.split('\n', 1)
            subject = lines[0].replace('Subject: ', '')
            message = lines[1] if len(lines) > 1 else ''
            success = self._send_email_via_api(notification.recipient, subject, message, notification)
        elif notification.notification_type == NotificationType.WHATSAPP:
            success = self._send_whatsapp_via_api(notification.recipient, notification.message, notification)
        
        if success:
            notification.mark_as_sent()
        else:
            notification.mark_as_failed("Error en reintento")
        
        self.db.commit()
        
        return success
    
    def send_bulk_notifications(self, bulk_data: NotificationBulkSend) -> Dict[str, Any]:
        """
        Enviar notificaciones masivas
        
        Args:
            bulk_data: Datos para envío masivo
            
        Returns:
            Dict con resultados del envío masivo
        """
        results = {
            'total': len(bulk_data.customer_ids),
            'sent': 0,
            'failed': 0,
            'errors': []
        }
        
        for customer_id in bulk_data.customer_ids:
            try:
                customer = self.db.query(Customer).filter(Customer.id == customer_id).first()
                if not customer:
                    results['failed'] += 1
                    results['errors'].append(f"Cliente {customer_id} no encontrado")
                    continue
                
                # Personalizar mensaje
                message = bulk_data.message_template
                if bulk_data.variables:
                    for key, value in bulk_data.variables.items():
                        message = message.replace(f"{{{key}}}", str(value))
                
                # Enviar según tipo
                if bulk_data.notification_type == NotificationType.SMS:
                    self.send_sms(customer.phone_number, message, customer_id=customer_id)
                elif bulk_data.notification_type == NotificationType.EMAIL:
                    self.send_email(customer.email, "Notificación", message, customer_id=customer_id)
                elif bulk_data.notification_type == NotificationType.WHATSAPP:
                    self.send_whatsapp(customer.phone_number, message, customer_id=customer_id)
                
                results['sent'] += 1
                
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"Error enviando a cliente {customer_id}: {str(e)}")
        
        return results
    
    def _send_sms_via_api(self, phone_number: str, message: str, notification: Notification) -> bool:
        """
        Enviar SMS a través de LIWA API
        
        Args:
            phone_number: Número de teléfono
            message: Mensaje a enviar
            notification: Objeto de notificación
            
        Returns:
            bool: True si el envío fue exitoso
        """
        try:
            if not settings.LIWA_API_KEY or not settings.LIWA_API_URL:
                logger.warning("LIWA API no configurada")
                return False
            
            # Preparar datos para LIWA API
            payload = {
                'api_key': settings.LIWA_API_KEY,
                'to': phone_number,
                'message': message,
                'from': settings.LIWA_SENDER_ID or 'Paqueteria'
            }
            
            # Enviar request
            response = requests.post(
                settings.LIWA_API_URL,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Verificar respuesta de LIWA
                if data.get('success'):
                    notification.external_id = data.get('message_id')
                    notification.sent_at = datetime.utcnow()
                    logger.info(f"SMS enviado exitosamente: {phone_number}")
                    return True
                else:
                    error_msg = data.get('error', 'Error desconocido')
                    logger.error(f"Error en LIWA API: {error_msg}")
                    return False
            else:
                logger.error(f"Error HTTP en LIWA API: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error de conexión con LIWA API: {e}")
            return False
        except Exception as e:
            logger.error(f"Error inesperado enviando SMS: {e}")
            return False
    
    def _send_email_via_api(self, email: str, subject: str, message: str, notification: Notification) -> bool:
        """
        Enviar email a través de API externa
        
        Args:
            email: Dirección de email
            subject: Asunto del email
            message: Contenido del email
            notification: Objeto de notificación
            
        Returns:
            bool: True si el envío fue exitoso
        """
        try:
            # Por ahora, simular envío exitoso
            # En producción, integrar con servicio de email (SendGrid, Mailgun, etc.)
            logger.info(f"Email simulado enviado a: {email}")
            notification.sent_at = datetime.utcnow()
            return True
            
        except Exception as e:
            logger.error(f"Error enviando email: {e}")
            return False
    
    def _send_whatsapp_via_api(self, phone_number: str, message: str, notification: Notification) -> bool:
        """
        Enviar WhatsApp a través de API externa
        
        Args:
            phone_number: Número de teléfono
            message: Mensaje a enviar
            notification: Objeto de notificación
            
        Returns:
            bool: True si el envío fue exitoso
        """
        try:
            # Por ahora, simular envío exitoso
            # En producción, integrar con WhatsApp Business API
            logger.info(f"WhatsApp simulado enviado a: {phone_number}")
            notification.sent_at = datetime.utcnow()
            return True
            
        except Exception as e:
            logger.error(f"Error enviando WhatsApp: {e}")
            return False
    
    def process_scheduled_notifications(self) -> int:
        """
        Procesar notificaciones programadas
        
        Returns:
            int: Número de notificaciones procesadas
        """
        now = datetime.utcnow()
        
        # Obtener notificaciones programadas
        scheduled_notifications = self.db.query(Notification).filter(
            and_(
                Notification.status == NotificationStatus.PENDING,
                Notification.scheduled_at <= now
            )
        ).all()
        
        processed = 0
        for notification in scheduled_notifications:
            try:
                success = False
                
                if notification.notification_type == NotificationType.SMS:
                    success = self._send_sms_via_api(notification.recipient, notification.message, notification)
                elif notification.notification_type == NotificationType.EMAIL:
                    lines = notification.message.split('\n', 1)
                    subject = lines[0].replace('Subject: ', '')
                    message = lines[1] if len(lines) > 1 else ''
                    success = self._send_email_via_api(notification.recipient, subject, message, notification)
                elif notification.notification_type == NotificationType.WHATSAPP:
                    success = self._send_whatsapp_via_api(notification.recipient, notification.message, notification)
                
                if success:
                    notification.mark_as_sent()
                else:
                    notification.mark_as_failed("Error procesando notificación programada")
                
                processed += 1
                
            except Exception as e:
                logger.error(f"Error procesando notificación {notification.id}: {e}")
                notification.mark_as_failed(str(e))
        
        self.db.commit()
        
        if processed > 0:
            logger.info(f"Procesadas {processed} notificaciones programadas")
        
        return processed
    
    def cleanup_old_notifications(self, days: int = 90) -> int:
        """
        Limpiar notificaciones antiguas
        
        Args:
            days: Días a mantener
            
        Returns:
            int: Número de notificaciones eliminadas
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        deleted_count = self.db.query(Notification).filter(
            Notification.created_at < cutoff_date
        ).delete()
        
        self.db.commit()
        
        if deleted_count > 0:
            logger.info(f"Eliminadas {deleted_count} notificaciones antiguas")
        
        return deleted_count
