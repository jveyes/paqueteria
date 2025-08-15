"""
Customer Schemas
===============

Esquemas Pydantic para validación de datos de clientes.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, validator, EmailStr
import re

class CustomerCreate(BaseModel):
    """Esquema para crear un nuevo cliente"""
    phone_number: str = Field(..., description="Número de teléfono del cliente")
    full_name: str = Field(..., min_length=2, max_length=100, description="Nombre completo")
    email: Optional[EmailStr] = Field(None, description="Correo electrónico (opcional)")
    address: Optional[str] = Field(None, max_length=500, description="Dirección del cliente")
    city: Optional[str] = Field(None, max_length=100, description="Ciudad")
    is_verified: bool = Field(default=False, description="Estado de verificación")
    verification_code: Optional[str] = Field(None, max_length=6, description="Código de verificación")

    @validator('phone_number')
    def validate_phone_number(cls, v):
        # Remove all non-digit characters
        digits_only = re.sub(r'\D', '', v)
        
        # Colombian phone number validation
        if len(digits_only) == 10:
            # Fixed line: 2XX XXX XXXX
            if digits_only.startswith(('2', '3', '4', '5', '6', '7', '8')):
                return f"+57 {digits_only[:3]} {digits_only[3:6]} {digits_only[6:]}"
        elif len(digits_only) == 11:
            # Mobile: 3XX XXX XXXX
            if digits_only.startswith('3'):
                return f"+57 {digits_only[1:4]} {digits_only[4:7]} {digits_only[7:]}"
        
        raise ValueError('Número de teléfono inválido. Use formato colombiano (ej: 3001234567)')

    @validator('full_name')
    def validate_full_name(cls, v):
        # Remove extra spaces and capitalize
        cleaned = ' '.join(v.split()).title()
        if len(cleaned) < 2:
            raise ValueError('El nombre debe tener al menos 2 caracteres')
        return cleaned

    @validator('city')
    def validate_city(cls, v):
        if v is not None:
            return v.title()
        return v

class CustomerUpdate(BaseModel):
    """Esquema para actualizar un cliente existente"""
    phone_number: Optional[str] = Field(None, description="Número de teléfono")
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None
    address: Optional[str] = Field(None, max_length=500)
    city: Optional[str] = Field(None, max_length=100)
    is_verified: Optional[bool] = None
    is_active: Optional[bool] = None

    @validator('phone_number')
    def validate_phone_number(cls, v):
        if v is not None:
            digits_only = re.sub(r'\D', '', v)
            
            if len(digits_only) == 10:
                if digits_only.startswith(('2', '3', '4', '5', '6', '7', '8')):
                    return f"+57 {digits_only[:3]} {digits_only[3:6]} {digits_only[6:]}"
            elif len(digits_only) == 11:
                if digits_only.startswith('3'):
                    return f"+57 {digits_only[1:4]} {digits_only[4:7]} {digits_only[7:]}"
            
            raise ValueError('Número de teléfono inválido. Use formato colombiano')
        return v

    @validator('full_name')
    def validate_full_name(cls, v):
        if v is not None:
            cleaned = ' '.join(v.split()).title()
            if len(cleaned) < 2:
                raise ValueError('El nombre debe tener al menos 2 caracteres')
            return cleaned
        return v

    @validator('city')
    def validate_city(cls, v):
        if v is not None:
            return v.title()
        return v

class CustomerResponse(BaseModel):
    """Esquema para respuesta de cliente"""
    id: int = Field(..., description="ID único del cliente")
    phone_number: str = Field(..., description="Número de teléfono")
    full_name: str = Field(..., description="Nombre completo")
    email: Optional[str] = Field(None, description="Correo electrónico")
    address: Optional[str] = Field(None, description="Dirección")
    city: Optional[str] = Field(None, description="Ciudad")
    is_verified: bool = Field(..., description="Estado de verificación")
    is_active: bool = Field(..., description="Estado activo")
    verification_code: Optional[str] = Field(None, description="Código de verificación")
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: datetime = Field(..., description="Fecha de última actualización")
    last_activity: Optional[datetime] = Field(None, description="Última actividad")
    packages_count: int = Field(default=0, description="Número de paquetes")
    total_spent: float = Field(default=0.0, description="Total gastado")

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class CustomerVerification(BaseModel):
    """Esquema para verificación de cliente"""
    phone_number: str = Field(..., description="Número de teléfono")
    verification_code: str = Field(..., min_length=6, max_length=6, description="Código de verificación")

    @validator('verification_code')
    def validate_code(cls, v):
        if not v.isdigit():
            raise ValueError('El código debe contener solo números')
        return v

class CustomerSearch(BaseModel):
    """Esquema para búsqueda de clientes"""
    query: Optional[str] = Field(None, description="Término de búsqueda")
    phone_number: Optional[str] = Field(None, description="Número de teléfono específico")
    city: Optional[str] = Field(None, description="Ciudad")
    is_verified: Optional[bool] = Field(None, description="Estado de verificación")
    is_active: Optional[bool] = Field(None, description="Estado activo")
    page: int = Field(default=1, ge=1, description="Número de página")
    per_page: int = Field(default=20, ge=1, le=100, description="Elementos por página")

class CustomerListResponse(BaseModel):
    """Esquema para lista de clientes"""
    customers: List[CustomerResponse] = Field(..., description="Lista de clientes")
    total: int = Field(..., description="Total de clientes")
    page: int = Field(..., description="Página actual")
    per_page: int = Field(..., description="Clientes por página")
    total_pages: int = Field(..., description="Total de páginas")

class CustomerStats(BaseModel):
    """Esquema para estadísticas de clientes"""
    total_customers: int = Field(..., description="Total de clientes")
    active_customers: int = Field(..., description="Clientes activos")
    verified_customers: int = Field(..., description="Clientes verificados")
    new_customers_today: int = Field(..., description="Nuevos clientes hoy")
    new_customers_this_week: int = Field(..., description="Nuevos clientes esta semana")
    new_customers_this_month: int = Field(..., description="Nuevos clientes este mes")
    customers_by_city: dict = Field(..., description="Clientes por ciudad")
    average_packages_per_customer: float = Field(..., description="Promedio de paquetes por cliente")
    total_revenue: float = Field(..., description="Ingresos totales")

class CustomerExport(BaseModel):
    """Esquema para exportación de clientes"""
    format: str = Field(default="csv", regex="^(csv|excel|json)$", description="Formato de exportación")
    include_packages: bool = Field(default=False, description="Incluir información de paquetes")
    date_from: Optional[datetime] = Field(None, description="Fecha desde")
    date_to: Optional[datetime] = Field(None, description="Fecha hasta")
    filters: Optional[dict] = Field(None, description="Filtros adicionales")
