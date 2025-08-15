"""
Configuración centralizada de la aplicación
==========================================

Maneja todas las variables de entorno y configuraciones
usando Pydantic Settings para validación automática.
"""

import os
from typing import Optional, List
from pydantic import BaseSettings, validator, Field
from pydantic.types import SecretStr


class Settings(BaseSettings):
    """
    Configuración principal de la aplicación
    """
    
    # =============================================================================
    # CONFIGURACIÓN DE LA APLICACIÓN
    # =============================================================================
    APP_NAME: str = "Sistema de Paquetería v1.1"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False, env="DEBUG")
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")
    
    # =============================================================================
    # BASE DE DATOS
    # =============================================================================
    DATABASE_URL: str = Field(
        default="mysql+pymysql://paqueteria_user:paqueteria_pass@localhost:3306/paqueteria",
        env="DATABASE_URL"
    )
    
    @validator("DATABASE_URL")
    def validate_database_url(cls, v):
        if not v:
            raise ValueError("DATABASE_URL no puede estar vacío")
        return v
    
    # =============================================================================
    # SEGURIDAD
    # =============================================================================
    SECRET_KEY: SecretStr = Field(
        default="your-secret-key-change-in-production",
        env="SECRET_KEY"
    )
    ALGORITHM: str = Field(default="HS256", env="ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, env="REFRESH_TOKEN_EXPIRE_DAYS")
    
    # =============================================================================
    # CORS
    # =============================================================================
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        env="CORS_ORIGINS"
    )
    
    @validator("CORS_ORIGINS", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    # =============================================================================
    # RATE LIMITING
    # =============================================================================
    RATE_LIMIT_PER_MINUTE: int = Field(default=60, env="RATE_LIMIT_PER_MINUTE")
    RATE_LIMIT_PER_HOUR: int = Field(default=1000, env="RATE_LIMIT_PER_HOUR")
    
    # =============================================================================
    # LIWA SMS API
    # =============================================================================
    LIWA_API_KEY: Optional[SecretStr] = Field(default=None, env="LIWA_API_KEY")
    LIWA_API_URL: str = Field(
        default="https://api.liwa.co/sms",
        env="LIWA_API_URL"
    )
    LIWA_ENABLED: bool = Field(default=True, env="LIWA_ENABLED")
    
    # =============================================================================
    # AWS S3
    # =============================================================================
    AWS_ACCESS_KEY_ID: Optional[str] = Field(default=None, env="AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: Optional[SecretStr] = Field(default=None, env="AWS_SECRET_ACCESS_KEY")
    AWS_REGION: str = Field(default="us-east-1", env="AWS_REGION")
    S3_BUCKET_NAME: str = Field(default="paqueteria-files", env="S3_BUCKET_NAME")
    S3_ENABLED: bool = Field(default=True, env="S3_ENABLED")
    
    # =============================================================================
    # WHATSAPP API (OPCIONAL)
    # =============================================================================
    WHATSAPP_API_KEY: Optional[SecretStr] = Field(default=None, env="WHATSAPP_API_KEY")
    WHATSAPP_API_URL: Optional[str] = Field(default=None, env="WHATSAPP_API_URL")
    WHATSAPP_ENABLED: bool = Field(default=False, env="WHATSAPP_ENABLED")
    
    # =============================================================================
    # REDIS
    # =============================================================================
    REDIS_URL: str = Field(
        default="redis://localhost:6379",
        env="REDIS_URL"
    )
    REDIS_DB: int = Field(default=0, env="REDIS_DB")
    
    # =============================================================================
    # CELERY
    # =============================================================================
    CELERY_BROKER_URL: str = Field(
        default="redis://localhost:6379/1",
        env="CELERY_BROKER_URL"
    )
    CELERY_RESULT_BACKEND: str = Field(
        default="redis://localhost:6379/2",
        env="CELERY_RESULT_BACKEND"
    )
    
    # =============================================================================
    # LOGGING
    # =============================================================================
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        env="LOG_FORMAT"
    )
    LOG_FILE: str = Field(default="/app/logs/app.log", env="LOG_FILE")
    
    # =============================================================================
    # ARCHIVOS
    # =============================================================================
    MAX_FILE_SIZE: int = Field(default=10 * 1024 * 1024, env="MAX_FILE_SIZE")  # 10MB
    ALLOWED_FILE_TYPES: List[str] = Field(
        default=["image/jpeg", "image/png", "image/gif", "application/pdf"],
        env="ALLOWED_FILE_TYPES"
    )
    UPLOAD_DIR: str = Field(default="/app/uploads", env="UPLOAD_DIR")
    
    @validator("ALLOWED_FILE_TYPES", pre=True)
    def parse_allowed_file_types(cls, v):
        if isinstance(v, str):
            return [file_type.strip() for file_type in v.split(",")]
        return v
    
    # =============================================================================
    # NEGOCIO
    # =============================================================================
    PACKAGE_NORMAL_COST: int = Field(default=1500, env="PACKAGE_NORMAL_COST")  # COP
    PACKAGE_EXTRA_COST: int = Field(default=2000, env="PACKAGE_EXTRA_COST")    # COP
    STORAGE_COST_PER_DAY: int = Field(default=1000, env="STORAGE_COST_PER_DAY")  # COP
    STORAGE_GRACE_HOURS: int = Field(default=24, env="STORAGE_GRACE_HOURS")   # horas
    
    # =============================================================================
    # MONITORING
    # =============================================================================
    PROMETHEUS_ENABLED: bool = Field(default=True, env="PROMETHEUS_ENABLED")
    METRICS_PORT: int = Field(default=9090, env="METRICS_PORT")
    
    # =============================================================================
    # BACKUP
    # =============================================================================
    BACKUP_ENABLED: bool = Field(default=True, env="BACKUP_ENABLED")
    BACKUP_RETENTION_DAYS: int = Field(default=7, env="BACKUP_RETENTION_DAYS")
    BACKUP_SCHEDULE: str = Field(default="0 2 * * *", env="BACKUP_SCHEDULE")  # 2 AM daily
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Instancia global de configuración
settings = Settings()


def get_settings() -> Settings:
    """
    Obtiene la instancia de configuración
    """
    return settings


# Configuraciones específicas por entorno
class DevelopmentSettings(Settings):
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"


class ProductionSettings(Settings):
    DEBUG: bool = False
    LOG_LEVEL: str = "WARNING"


class TestingSettings(Settings):
    DEBUG: bool = True
    DATABASE_URL: str = "sqlite:///./test.db"
    TESTING: bool = True


def get_settings_by_env(env: str = "development") -> Settings:
    """
    Obtiene configuración según el entorno
    """
    env = env.lower()
    if env == "production":
        return ProductionSettings()
    elif env == "testing":
        return TestingSettings()
    else:
        return DevelopmentSettings()
