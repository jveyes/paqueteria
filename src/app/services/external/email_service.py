"""
Email Service
============

Servicio de envío de emails usando SMTP.
"""

import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr

from ...core.config import settings
from ...core.logging import get_logger

logger = get_logger(__name__)

class EmailConfig(BaseModel):
    """Configuración para email"""
    smtp_host: str = Field(..., description="Servidor SMTP")
    smtp_port: int = Field(587, description="Puerto SMTP")
    smtp_username: str = Field(..., description="Usuario SMTP")
    smtp_password: str = Field(..., description="Contraseña SMTP")
    smtp_use_tls: bool = Field(True, description="Usar TLS")
    smtp_use_ssl: bool = Field(False, description="Usar SSL")
    from_email: str = Field(..., description="Email remitente")
    from_name: str = Field("Sistema de Paquetería", description="Nombre del remitente")
    max_retries: int = Field(3, description="Máximo número de reintentos")
    retry_delay: int = Field(5, description="Delay entre reintentos en segundos")

class EmailMessage(BaseModel):
    """Mensaje de email"""
    to_email: EmailStr = Field(..., description="Email destinatario")
    to_name: Optional[str] = Field(None, description="Nombre del destinatario")
    subject: str = Field(..., description="Asunto del email")
    body_text: Optional[str] = Field(None, description="Cuerpo del email en texto plano")
    body_html: Optional[str] = Field(None, description="Cuerpo del email en HTML")
    attachments: List[Dict[str, Any]] = Field(default_factory=list, description="Archivos adjuntos")
    message_id: Optional[str] = Field(None, description="ID único del mensaje")

class EmailResponse(BaseModel):
    """Respuesta del servicio de email"""
    success: bool = Field(..., description="Si el envío fue exitoso")
    message_id: Optional[str] = Field(None, description="ID del mensaje")
    error_code: Optional[str] = Field(None, description="Código de error")
    error_message: Optional[str] = Field(None, description="Mensaje de error")

class EmailService:
    """Servicio para envío de emails"""
    
    def __init__(self):
        self.config = EmailConfig(
            smtp_host=settings.SMTP_HOST,
            smtp_port=settings.SMTP_PORT,
            smtp_username=settings.SMTP_USERNAME,
            smtp_password=settings.SMTP_PASSWORD,
            smtp_use_tls=settings.SMTP_USE_TLS,
            smtp_use_ssl=settings.SMTP_USE_SSL,
            from_email=settings.FROM_EMAIL,
            from_name=settings.FROM_NAME,
            max_retries=settings.EMAIL_MAX_RETRIES,
            retry_delay=settings.EMAIL_RETRY_DELAY
        )
    
    def _create_message(self, email_msg: EmailMessage) -> MIMEMultipart:
        """
        Crear mensaje MIME
        
        Args:
            email_msg: Mensaje de email
            
        Returns:
            MIMEMultipart: Mensaje MIME
        """
        # Crear mensaje
        msg = MIMEMultipart('alternative')
        msg['From'] = f"{self.config.from_name} <{self.config.from_email}>"
        msg['To'] = f"{email_msg.to_name} <{email_msg.to_email}>" if email_msg.to_name else email_msg.to_email
        msg['Subject'] = email_msg.subject
        
        # Agregar ID del mensaje
        if email_msg.message_id:
            msg['Message-ID'] = email_msg.message_id
        
        # Agregar cuerpo del mensaje
        if email_msg.body_text:
            text_part = MIMEText(email_msg.body_text, 'plain', 'utf-8')
            msg.attach(text_part)
        
        if email_msg.body_html:
            html_part = MIMEText(email_msg.body_html, 'html', 'utf-8')
            msg.attach(html_part)
        
        # Agregar archivos adjuntos
        for attachment in email_msg.attachments:
            try:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment['content'])
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f"attachment; filename= {attachment['filename']}"
                )
                msg.attach(part)
            except Exception as e:
                logger.error(f"Error agregando adjunto {attachment.get('filename', 'unknown')}: {e}")
        
        return msg
    
    async def send_email(self, email_msg: EmailMessage) -> EmailResponse:
        """
        Enviar email
        
        Args:
            email_msg: Mensaje de email
            
        Returns:
            EmailResponse: Respuesta del servicio
        """
        # Validar mensaje
        if not email_msg.body_text and not email_msg.body_html:
            return EmailResponse(
                success=False,
                error_code="INVALID_MESSAGE",
                error_message="El mensaje debe tener contenido de texto o HTML"
            )
        
        # Crear mensaje MIME
        msg = self._create_message(email_msg)
        
        # Intentar envío con reintentos
        for attempt in range(self.config.max_retries):
            try:
                logger.info(f"Enviando email a {email_msg.to_email} (intento {attempt + 1})")
                
                # Configurar conexión SMTP
                if self.config.smtp_use_ssl:
                    server = smtplib.SMTP_SSL(self.config.smtp_host, self.config.smtp_port)
                else:
                    server = smtplib.SMTP(self.config.smtp_host, self.config.smtp_port)
                
                # Configurar TLS si es necesario
                if self.config.smtp_use_tls and not self.config.smtp_use_ssl:
                    server.starttls()
                
                # Autenticación
                server.login(self.config.smtp_username, self.config.smtp_password)
                
                # Enviar email
                server.send_message(msg)
                server.quit()
                
                logger.info(f"Email enviado exitosamente a {email_msg.to_email}")
                return EmailResponse(
                    success=True,
                    message_id=email_msg.message_id
                )
                
            except smtplib.SMTPAuthenticationError as e:
                logger.error(f"Error de autenticación SMTP: {e}")
                return EmailResponse(
                    success=False,
                    error_code="AUTHENTICATION_ERROR",
                    error_message=f"Error de autenticación: {str(e)}"
                )
            
            except smtplib.SMTPRecipientsRefused as e:
                logger.error(f"Destinatario rechazado: {e}")
                return EmailResponse(
                    success=False,
                    error_code="RECIPIENT_REFUSED",
                    error_message=f"Destinatario rechazado: {str(e)}"
                )
            
            except smtplib.SMTPException as e:
                logger.error(f"Error SMTP: {e}")
                
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay)
                    continue
                
                return EmailResponse(
                    success=False,
                    error_code="SMTP_ERROR",
                    error_message=f"Error SMTP: {str(e)}"
                )
            
            except Exception as e:
                logger.error(f"Error inesperado enviando email: {e}")
                
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay)
                    continue
                
                return EmailResponse(
                    success=False,
                    error_code="UNKNOWN_ERROR",
                    error_message=f"Error inesperado: {str(e)}"
                )
        
        return EmailResponse(
            success=False,
            error_code="MAX_RETRIES_EXCEEDED",
            error_message="Se excedió el número máximo de reintentos"
        )
    
    async def send_bulk_email(self, email_messages: List[EmailMessage]) -> List[EmailResponse]:
        """
        Enviar múltiples emails
        
        Args:
            email_messages: Lista de mensajes de email
            
        Returns:
            List[EmailResponse]: Lista de respuestas
        """
        results = []
        
        for email_msg in email_messages:
            result = await self.send_email(email_msg)
            results.append(result)
            
            # Pequeña pausa entre envíos para evitar spam
            await asyncio.sleep(1)
        
        return results
    
    def create_package_announcement_email(self, customer_name: str, customer_email: str, tracking_number: str, package_cost: str) -> EmailMessage:
        """
        Crear email de anuncio de paquete
        
        Args:
            customer_name: Nombre del cliente
            customer_email: Email del cliente
            tracking_number: Número de tracking
            package_cost: Costo del paquete
            
        Returns:
            EmailMessage: Mensaje de email
        """
        subject = f"Paquete Anunciado - Tracking: {tracking_number}"
        
        body_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Paquete Anunciado</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center;">
                    <h1 style="color: #007bff; margin-bottom: 10px;">📦 Paquete Anunciado</h1>
                    <p style="font-size: 18px; margin-bottom: 20px;">Su paquete ha sido anunciado exitosamente</p>
                </div>
                
                <div style="background-color: white; padding: 20px; border-radius: 8px; margin-top: 20px; border: 1px solid #dee2e6;">
                    <h2 style="color: #28a745; margin-bottom: 15px;">Información del Paquete</h2>
                    
                    <div style="margin-bottom: 15px;">
                        <strong>Número de Tracking:</strong>
                        <span style="font-size: 18px; font-weight: bold; color: #007bff; margin-left: 10px;">{tracking_number}</span>
                    </div>
                    
                    <div style="margin-bottom: 15px;">
                        <strong>Costo del Paquete:</strong>
                        <span style="font-size: 16px; color: #28a745; margin-left: 10px;">{package_cost}</span>
                    </div>
                    
                    <div style="margin-bottom: 20px;">
                        <strong>Cliente:</strong>
                        <span style="margin-left: 10px;">{customer_name}</span>
                    </div>
                </div>
                
                <div style="background-color: #fff3cd; padding: 15px; border-radius: 8px; margin-top: 20px; border: 1px solid #ffeaa7;">
                    <h3 style="color: #856404; margin-bottom: 10px;">⚠️ Información Importante</h3>
                    <ul style="margin: 0; padding-left: 20px;">
                        <li>Su paquete debe ser recogido en nuestras instalaciones</li>
                        <li>Se aplicará costo de bodegaje después de 24 horas</li>
                        <li>El paquete expirará en 30 días si no es reclamado</li>
                        <li>Conserve este número de tracking para seguimiento</li>
                    </ul>
                </div>
                
                <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #dee2e6;">
                    <p style="color: #6c757d; font-size: 14px;">
                        Sistema de Paquetería v1.1<br>
                        Desarrollado por Jesús María Villalobos
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        body_text = f"""
        PAQUETE ANUNCIADO
        
        Su paquete ha sido anunciado exitosamente.
        
        INFORMACIÓN DEL PAQUETE:
        - Número de Tracking: {tracking_number}
        - Costo del Paquete: {package_cost}
        - Cliente: {customer_name}
        
        INFORMACIÓN IMPORTANTE:
        - Su paquete debe ser recogido en nuestras instalaciones
        - Se aplicará costo de bodegaje después de 24 horas
        - El paquete expirará en 30 días si no es reclamado
        - Conserve este número de tracking para seguimiento
        
        Sistema de Paquetería v1.1
        Desarrollado por Jesús María Villalobos
        """
        
        return EmailMessage(
            to_email=customer_email,
            to_name=customer_name,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            message_id=f"pkg_{tracking_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
    
    def create_package_received_email(self, customer_name: str, customer_email: str, tracking_number: str) -> EmailMessage:
        """
        Crear email de paquete recibido
        
        Args:
            customer_name: Nombre del cliente
            customer_email: Email del cliente
            tracking_number: Número de tracking
            
        Returns:
            EmailMessage: Mensaje de email
        """
        subject = f"Paquete Recibido - Tracking: {tracking_number}"
        
        body_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Paquete Recibido</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background-color: #d4edda; padding: 20px; border-radius: 8px; text-align: center;">
                    <h1 style="color: #155724; margin-bottom: 10px;">✅ Paquete Recibido</h1>
                    <p style="font-size: 18px; margin-bottom: 20px;">Su paquete ha sido recibido en nuestras instalaciones</p>
                </div>
                
                <div style="background-color: white; padding: 20px; border-radius: 8px; margin-top: 20px; border: 1px solid #dee2e6;">
                    <h2 style="color: #28a745; margin-bottom: 15px;">Información del Paquete</h2>
                    
                    <div style="margin-bottom: 15px;">
                        <strong>Número de Tracking:</strong>
                        <span style="font-size: 18px; font-weight: bold; color: #007bff; margin-left: 10px;">{tracking_number}</span>
                    </div>
                    
                    <div style="margin-bottom: 15px;">
                        <strong>Estado:</strong>
                        <span style="font-size: 16px; color: #28a745; margin-left: 10px;">RECIBIDO</span>
                    </div>
                    
                    <div style="margin-bottom: 20px;">
                        <strong>Cliente:</strong>
                        <span style="margin-left: 10px;">{customer_name}</span>
                    </div>
                </div>
                
                <div style="background-color: #d1ecf1; padding: 15px; border-radius: 8px; margin-top: 20px; border: 1px solid #bee5eb;">
                    <h3 style="color: #0c5460; margin-bottom: 10px;">📋 Próximos Pasos</h3>
                    <ul style="margin: 0; padding-left: 20px;">
                        <li>Su paquete está listo para ser entregado</li>
                        <li>Puede recogerlo en nuestras instalaciones</li>
                        <li>Recuerde traer identificación</li>
                        <li>El costo debe ser pagado al momento de la entrega</li>
                    </ul>
                </div>
                
                <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #dee2e6;">
                    <p style="color: #6c757d; font-size: 14px;">
                        Sistema de Paquetería v1.1<br>
                        Desarrollado por Jesús María Villalobos
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        body_text = f"""
        PAQUETE RECIBIDO
        
        Su paquete ha sido recibido en nuestras instalaciones.
        
        INFORMACIÓN DEL PAQUETE:
        - Número de Tracking: {tracking_number}
        - Estado: RECIBIDO
        - Cliente: {customer_name}
        
        PRÓXIMOS PASOS:
        - Su paquete está listo para ser entregado
        - Puede recogerlo en nuestras instalaciones
        - Recuerde traer identificación
        - El costo debe ser pagado al momento de la entrega
        
        Sistema de Paquetería v1.1
        Desarrollado por Jesús María Villalobos
        """
        
        return EmailMessage(
            to_email=customer_email,
            to_name=customer_name,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            message_id=f"rec_{tracking_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
    
    def create_package_delivered_email(self, customer_name: str, customer_email: str, tracking_number: str, delivery_number: str, amount_paid: str) -> EmailMessage:
        """
        Crear email de paquete entregado
        
        Args:
            customer_name: Nombre del cliente
            customer_email: Email del cliente
            tracking_number: Número de tracking
            delivery_number: Número de entrega
            amount_paid: Monto pagado
            
        Returns:
            EmailMessage: Mensaje de email
        """
        subject = f"Paquete Entregado - Tracking: {tracking_number}"
        
        body_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Paquete Entregado</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background-color: #d1ecf1; padding: 20px; border-radius: 8px; text-align: center;">
                    <h1 style="color: #0c5460; margin-bottom: 10px;">🚚 Paquete Entregado</h1>
                    <p style="font-size: 18px; margin-bottom: 20px;">Su paquete ha sido entregado exitosamente</p>
                </div>
                
                <div style="background-color: white; padding: 20px; border-radius: 8px; margin-top: 20px; border: 1px solid #dee2e6;">
                    <h2 style="color: #28a745; margin-bottom: 15px;">Información de la Entrega</h2>
                    
                    <div style="margin-bottom: 15px;">
                        <strong>Número de Tracking:</strong>
                        <span style="font-size: 18px; font-weight: bold; color: #007bff; margin-left: 10px;">{tracking_number}</span>
                    </div>
                    
                    <div style="margin-bottom: 15px;">
                        <strong>Número de Entrega:</strong>
                        <span style="font-size: 16px; color: #28a745; margin-left: 10px;">{delivery_number}</span>
                    </div>
                    
                    <div style="margin-bottom: 15px;">
                        <strong>Monto Pagado:</strong>
                        <span style="font-size: 16px; color: #28a745; margin-left: 10px;">{amount_paid}</span>
                    </div>
                    
                    <div style="margin-bottom: 20px;">
                        <strong>Cliente:</strong>
                        <span style="margin-left: 10px;">{customer_name}</span>
                    </div>
                </div>
                
                <div style="background-color: #d4edda; padding: 15px; border-radius: 8px; margin-top: 20px; border: 1px solid #c3e6cb;">
                    <h3 style="color: #155724; margin-bottom: 10px;">✅ Entrega Completada</h3>
                    <p style="margin: 0;">
                        Su paquete ha sido entregado exitosamente. Gracias por confiar en nuestro servicio.
                    </p>
                </div>
                
                <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #dee2e6;">
                    <p style="color: #6c757d; font-size: 14px;">
                        Sistema de Paquetería v1.1<br>
                        Desarrollado por Jesús María Villalobos
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        body_text = f"""
        PAQUETE ENTREGADO
        
        Su paquete ha sido entregado exitosamente.
        
        INFORMACIÓN DE LA ENTREGA:
        - Número de Tracking: {tracking_number}
        - Número de Entrega: {delivery_number}
        - Monto Pagado: {amount_paid}
        - Cliente: {customer_name}
        
        ENTREGA COMPLETADA:
        Su paquete ha sido entregado exitosamente. Gracias por confiar en nuestro servicio.
        
        Sistema de Paquetería v1.1
        Desarrollado por Jesús María Villalobos
        """
        
        return EmailMessage(
            to_email=customer_email,
            to_name=customer_name,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            message_id=f"del_{tracking_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )

# Instancia global del servicio
email_service = EmailService()

# Funciones de conveniencia
async def send_quick_email(to_email: str, subject: str, body: str, to_name: Optional[str] = None) -> EmailResponse:
    """
    Función de conveniencia para envío rápido de email
    
    Args:
        to_email: Email destinatario
        subject: Asunto del email
        body: Cuerpo del email
        to_name: Nombre del destinatario (opcional)
        
    Returns:
        EmailResponse: Respuesta del servicio
    """
    email_msg = EmailMessage(
        to_email=to_email,
        to_name=to_name,
        subject=subject,
        body_text=body
    )
    
    return await email_service.send_email(email_msg)
