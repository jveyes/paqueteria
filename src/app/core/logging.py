"""
Configuración de logging estructurado
====================================

Configura el sistema de logging con formato estructurado,
rotación de archivos y diferentes niveles según el entorno.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional

from .config import settings


def setup_logging(
    log_level: Optional[str] = None,
    log_file: Optional[str] = None,
    log_format: Optional[str] = None
) -> None:
    """
    Configura el sistema de logging
    
    Args:
        log_level: Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Ruta del archivo de log
        log_format: Formato del log
    """
    
    # Usar configuración por defecto si no se especifica
    log_level = log_level or settings.LOG_LEVEL
    log_file = log_file or settings.LOG_FILE
    log_format = log_format or settings.LOG_FORMAT
    
    # Crear directorio de logs si no existe
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Configurar formato
    formatter = logging.Formatter(log_format)
    
    # Configurar handler para consola
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
    
    # Configurar handler para archivo
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(getattr(logging, log_level.upper()))
    
    # Configurar logger raíz
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Configurar loggers específicos
    loggers = [
        "uvicorn",
        "uvicorn.error",
        "uvicorn.access",
        "fastapi",
        "sqlalchemy",
        "celery",
        "redis",
        "requests",
        "boto3",
        "botocore"
    ]
    
    for logger_name in loggers:
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.propagate = True
    
    # Log de inicio
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configurado - Nivel: {log_level}, Archivo: {log_file}")


def get_logger(name: str) -> logging.Logger:
    """
    Obtiene un logger configurado
    
    Args:
        name: Nombre del logger
        
    Returns:
        Logger configurado
    """
    return logging.getLogger(name)


class StructuredFormatter(logging.Formatter):
    """
    Formateador estructurado para logs JSON
    """
    
    def format(self, record):
        # Agregar campos adicionales al record
        record.app_name = settings.APP_NAME
        record.app_version = settings.APP_VERSION
        record.environment = "development" if settings.DEBUG else "production"
        
        # Formato estructurado
        log_entry = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "app_name": record.app_name,
            "app_version": record.app_version,
            "environment": record.environment
        }
        
        # Agregar información adicional si está disponible
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
        if hasattr(record, 'package_id'):
            log_entry['package_id'] = record.package_id
        
        # Agregar excepción si existe
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return str(log_entry)


def setup_structured_logging() -> None:
    """
    Configura logging estructurado con formato JSON
    """
    import json
    
    class JSONFormatter(logging.Formatter):
        def format(self, record):
            log_entry = {
                "timestamp": self.formatTime(record),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "app_name": settings.APP_NAME,
                "app_version": settings.APP_VERSION,
                "environment": "development" if settings.DEBUG else "production"
            }
            
            # Agregar campos adicionales
            if hasattr(record, 'user_id'):
                log_entry['user_id'] = record.user_id
            if hasattr(record, 'request_id'):
                log_entry['request_id'] = record.request_id
            if hasattr(record, 'package_id'):
                log_entry['package_id'] = record.package_id
            
            # Agregar excepción si existe
            if record.exc_info:
                log_entry['exception'] = self.formatException(record.exc_info)
            
            return json.dumps(log_entry, ensure_ascii=False)
    
    # Configurar formateador JSON
    json_formatter = JSONFormatter()
    
    # Configurar handlers
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(json_formatter)
    
    file_handler = logging.handlers.RotatingFileHandler(
        settings.LOG_FILE,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(json_formatter)
    
    # Configurar logger raíz
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))


# Configurar logging al importar el módulo
if not logging.getLogger().handlers:
    setup_logging()
