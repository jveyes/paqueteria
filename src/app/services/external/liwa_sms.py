"""
LIWA SMS Service
===============

Servicio de integración con LIWA SMS para envío de mensajes en Colombia.
"""

import asyncio
import aiohttp
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field

from ...core.config import settings
from ...core.logging import get_logger

logger = get_logger(__name__)

class LIWASMSConfig(BaseModel):
    """Configuración para LIWA SMS"""
    api_key: str = Field(..., description="API Key de LIWA")
    api_url: str = Field(..., description="URL de la API de LIWA")
    sender_id: str = Field("PAQUETERIA", description="ID del remitente")
    country_code: str = Field("57", description="Código de país (Colombia)")
    max_retries: int = Field(3, description="Máximo número de reintentos")
    retry_delay: int = Field(5, description="Delay entre reintentos en segundos")

class LIWASMSMessage(BaseModel):
    """Mensaje SMS para LIWA"""
    phone_number: str = Field(..., description="Número de teléfono")
    message: str = Field(..., description="Contenido del mensaje")
    message_id: Optional[str] = Field(None, description="ID único del mensaje")
    scheduled_time: Optional[datetime] = Field(None, description="Tiempo programado")

class LIWASMSResponse(BaseModel):
    """Respuesta de LIWA SMS"""
    success: bool = Field(..., description="Si el envío fue exitoso")
    message_id: Optional[str] = Field(None, description="ID del mensaje en LIWA")
    external_id: Optional[str] = Field(None, description="ID externo del mensaje")
    error_code: Optional[str] = Field(None, description="Código de error")
    error_message: Optional[str] = Field(None, description="Mensaje de error")
    cost: Optional[float] = Field(None, description="Costo del mensaje")
    remaining_balance: Optional[float] = Field(None, description="Saldo restante")

class LIWASMSService:
    """Servicio para integración con LIWA SMS"""
    
    def __init__(self):
        self.config = LIWASMSConfig(
            api_key=settings.LIWA_API_KEY,
            api_url=settings.LIWA_API_URL,
            sender_id=settings.LIWA_SENDER_ID,
            country_code=settings.LIWA_COUNTRY_CODE,
            max_retries=settings.LIWA_MAX_RETRIES,
            retry_delay=settings.LIWA_RETRY_DELAY
        )
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "Paqueteria-System/1.0"
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.session:
            await self.session.close()
    
    def _format_phone_number(self, phone_number: str) -> str:
        """
        Formatear número de teléfono para LIWA
        
        Args:
            phone_number: Número de teléfono
            
        Returns:
            str: Número formateado
        """
        # Remover espacios, guiones y paréntesis
        cleaned = ''.join(filter(str.isdigit, phone_number))
        
        # Si no tiene código de país, agregarlo
        if not cleaned.startswith(self.config.country_code):
            if cleaned.startswith('0'):
                cleaned = cleaned[1:]  # Remover 0 inicial
            cleaned = f"{self.config.country_code}{cleaned}"
        
        return cleaned
    
    def _validate_message(self, message: str) -> bool:
        """
        Validar mensaje SMS
        
        Args:
            message: Contenido del mensaje
            
        Returns:
            bool: Si el mensaje es válido
        """
        # LIWA SMS tiene límite de 160 caracteres por mensaje
        if len(message) > 160:
            logger.warning(f"Mensaje demasiado largo: {len(message)} caracteres")
            return False
        
        # Verificar caracteres válidos
        invalid_chars = ['\x00', '\x01', '\x02', '\x03', '\x04', '\x05', '\x06', '\x07']
        for char in invalid_chars:
            if char in message:
                logger.warning(f"Mensaje contiene caracteres inválidos")
                return False
        
        return True
    
    async def send_sms(self, message: LIWASMSMessage) -> LIWASMSResponse:
        """
        Enviar SMS a través de LIWA
        
        Args:
            message: Mensaje a enviar
            
        Returns:
            LIWASMSResponse: Respuesta del servicio
        """
        if not self.session:
            raise RuntimeError("Servicio no inicializado. Use async with.")
        
        # Validar mensaje
        if not self._validate_message(message.message):
            return LIWASMSResponse(
                success=False,
                error_code="INVALID_MESSAGE",
                error_message="Mensaje inválido o demasiado largo"
            )
        
        # Formatear número de teléfono
        formatted_phone = self._format_phone_number(message.phone_number)
        
        # Preparar payload
        payload = {
            "to": formatted_phone,
            "message": message.message,
            "from": self.config.sender_id,
            "message_id": message.message_id or f"msg_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "country_code": self.config.country_code
        }
        
        if message.scheduled_time:
            payload["scheduled_time"] = message.scheduled_time.isoformat()
        
        # Intentar envío con reintentos
        for attempt in range(self.config.max_retries):
            try:
                logger.info(f"Enviando SMS a {formatted_phone} (intento {attempt + 1})")
                
                async with self.session.post(
                    f"{self.config.api_url}/send",
                    json=payload
                ) as response:
                    response_data = await response.json()
                    
                    if response.status == 200:
                        # Éxito
                        logger.info(f"SMS enviado exitosamente: {response_data.get('message_id')}")
                        return LIWASMSResponse(
                            success=True,
                            message_id=response_data.get("message_id"),
                            external_id=response_data.get("external_id"),
                            cost=response_data.get("cost"),
                            remaining_balance=response_data.get("remaining_balance")
                        )
                    else:
                        # Error de API
                        error_msg = response_data.get("error", "Error desconocido")
                        logger.error(f"Error en API LIWA: {error_msg}")
                        
                        if attempt < self.config.max_retries - 1:
                            await asyncio.sleep(self.config.retry_delay)
                            continue
                        
                        return LIWASMSResponse(
                            success=False,
                            error_code=response_data.get("error_code", "API_ERROR"),
                            error_message=error_msg
                        )
            
            except aiohttp.ClientError as e:
                logger.error(f"Error de conexión con LIWA: {e}")
                
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay)
                    continue
                
                return LIWASMSResponse(
                    success=False,
                    error_code="CONNECTION_ERROR",
                    error_message=f"Error de conexión: {str(e)}"
                )
            
            except Exception as e:
                logger.error(f"Error inesperado enviando SMS: {e}")
                
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay)
                    continue
                
                return LIWASMSResponse(
                    success=False,
                    error_code="UNKNOWN_ERROR",
                    error_message=f"Error inesperado: {str(e)}"
                )
        
        return LIWASMSResponse(
            success=False,
            error_code="MAX_RETRIES_EXCEEDED",
            error_message="Se excedió el número máximo de reintentos"
        )
    
    async def send_bulk_sms(self, messages: List[LIWASMSMessage]) -> List[LIWASMSResponse]:
        """
        Enviar múltiples SMS
        
        Args:
            messages: Lista de mensajes a enviar
            
        Returns:
            List[LIWASMSResponse]: Lista de respuestas
        """
        if not self.session:
            raise RuntimeError("Servicio no inicializado. Use async with.")
        
        # Preparar payload para envío masivo
        bulk_payload = {
            "messages": [
                {
                    "to": self._format_phone_number(msg.phone_number),
                    "message": msg.message,
                    "from": self.config.sender_id,
                    "message_id": msg.message_id or f"bulk_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{i}",
                    "country_code": self.config.country_code
                }
                for i, msg in enumerate(messages)
            ]
        }
        
        try:
            logger.info(f"Enviando {len(messages)} SMS en lote")
            
            async with self.session.post(
                f"{self.config.api_url}/send-bulk",
                json=bulk_payload
            ) as response:
                response_data = await response.json()
                
                if response.status == 200:
                    # Procesar respuestas individuales
                    results = []
                    for i, msg_result in enumerate(response_data.get("results", [])):
                        if msg_result.get("success"):
                            results.append(LIWASMSResponse(
                                success=True,
                                message_id=msg_result.get("message_id"),
                                external_id=msg_result.get("external_id"),
                                cost=msg_result.get("cost")
                            ))
                        else:
                            results.append(LIWASMSResponse(
                                success=False,
                                error_code=msg_result.get("error_code"),
                                error_message=msg_result.get("error_message")
                            ))
                    
                    logger.info(f"Enviados {len([r for r in results if r.success])}/{len(messages)} SMS exitosamente")
                    return results
                else:
                    # Error en envío masivo
                    error_msg = response_data.get("error", "Error en envío masivo")
                    logger.error(f"Error en envío masivo LIWA: {error_msg}")
                    
                    return [
                        LIWASMSResponse(
                            success=False,
                            error_code="BULK_ERROR",
                            error_message=error_msg
                        )
                        for _ in messages
                    ]
        
        except Exception as e:
            logger.error(f"Error en envío masivo: {e}")
            return [
                LIWASMSResponse(
                    success=False,
                    error_code="BULK_ERROR",
                    error_message=f"Error en envío masivo: {str(e)}"
                )
                for _ in messages
            ]
    
    async def check_balance(self) -> Dict[str, Any]:
        """
        Verificar saldo de la cuenta
        
        Returns:
            Dict[str, Any]: Información del saldo
        """
        if not self.session:
            raise RuntimeError("Servicio no inicializado. Use async with.")
        
        try:
            async with self.session.get(f"{self.config.api_url}/balance") as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "success": True,
                        "balance": data.get("balance", 0),
                        "currency": data.get("currency", "COP"),
                        "last_updated": data.get("last_updated")
                    }
                else:
                    return {
                        "success": False,
                        "error": "No se pudo obtener el saldo"
                    }
        except Exception as e:
            logger.error(f"Error verificando saldo: {e}")
            return {
                "success": False,
                "error": f"Error verificando saldo: {str(e)}"
            }
    
    async def get_message_status(self, message_id: str) -> Dict[str, Any]:
        """
        Obtener estado de un mensaje
        
        Args:
            message_id: ID del mensaje
            
        Returns:
            Dict[str, Any]: Estado del mensaje
        """
        if not self.session:
            raise RuntimeError("Servicio no inicializado. Use async with.")
        
        try:
            async with self.session.get(
                f"{self.config.api_url}/status/{message_id}"
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "success": True,
                        "message_id": message_id,
                        "status": data.get("status"),
                        "delivered_at": data.get("delivered_at"),
                        "error_message": data.get("error_message")
                    }
                else:
                    return {
                        "success": False,
                        "error": "No se pudo obtener el estado del mensaje"
                    }
        except Exception as e:
            logger.error(f"Error obteniendo estado del mensaje: {e}")
            return {
                "success": False,
                "error": f"Error obteniendo estado: {str(e)}"
            }

# Función de conveniencia para envío rápido
async def send_quick_sms(phone_number: str, message: str, message_id: Optional[str] = None) -> LIWASMSResponse:
    """
    Función de conveniencia para envío rápido de SMS
    
    Args:
        phone_number: Número de teléfono
        message: Contenido del mensaje
        message_id: ID opcional del mensaje
        
    Returns:
        LIWASMSResponse: Respuesta del servicio
    """
    sms_message = LIWASMSMessage(
        phone_number=phone_number,
        message=message,
        message_id=message_id
    )
    
    async with LIWASMSService() as service:
        return await service.send_sms(sms_message)
