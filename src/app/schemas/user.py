"""
User Schemas
============

Esquemas Pydantic para validación de datos de usuarios.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, validator
from enum import Enum

class UserRole(str, Enum):
    """Roles de usuario disponibles"""
    ADMIN = "admin"
    MANAGER = "manager"
    OPERATOR = "operator"

class UserCreate(BaseModel):
    """Esquema para crear un nuevo usuario"""
    username: str = Field(..., min_length=3, max_length=50, description="Nombre de usuario único")
    email: EmailStr = Field(..., description="Correo electrónico válido")
    full_name: str = Field(..., min_length=2, max_length=100, description="Nombre completo")
    password: str = Field(..., min_length=8, description="Contraseña segura")
    role: UserRole = Field(default=UserRole.OPERATOR, description="Rol del usuario")
    permissions: Optional[List[str]] = Field(default=None, description="Permisos específicos")
    is_active: bool = Field(default=True, description="Estado activo del usuario")

    @validator('username')
    def username_alphanumeric(cls, v):
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('El nombre de usuario debe contener solo letras, números, guiones y guiones bajos')
        return v.lower()

    @validator('password')
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('La contraseña debe tener al menos 8 caracteres')
        if not any(c.isupper() for c in v):
            raise ValueError('La contraseña debe contener al menos una letra mayúscula')
        if not any(c.islower() for c in v):
            raise ValueError('La contraseña debe contener al menos una letra minúscula')
        if not any(c.isdigit() for c in v):
            raise ValueError('La contraseña debe contener al menos un número')
        return v

class UserUpdate(BaseModel):
    """Esquema para actualizar un usuario existente"""
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    role: Optional[UserRole] = None
    permissions: Optional[List[str]] = None
    is_active: Optional[bool] = None

    @validator('username')
    def username_alphanumeric(cls, v):
        if v is not None:
            if not v.replace('_', '').replace('-', '').isalnum():
                raise ValueError('El nombre de usuario debe contener solo letras, números, guiones y guiones bajos')
            return v.lower()
        return v

class UserLogin(BaseModel):
    """Esquema para autenticación de usuario"""
    username: str = Field(..., description="Nombre de usuario o email")
    password: str = Field(..., description="Contraseña")

class UserToken(BaseModel):
    """Esquema para respuesta de token de autenticación"""
    access_token: str = Field(..., description="Token de acceso JWT")
    refresh_token: str = Field(..., description="Token de refresco JWT")
    token_type: str = Field(default="bearer", description="Tipo de token")
    expires_in: int = Field(..., description="Tiempo de expiración en segundos")
    user: 'UserResponse' = Field(..., description="Información del usuario")

class UserResponse(BaseModel):
    """Esquema para respuesta de usuario"""
    id: int = Field(..., description="ID único del usuario")
    username: str = Field(..., description="Nombre de usuario")
    email: EmailStr = Field(..., description="Correo electrónico")
    full_name: str = Field(..., description="Nombre completo")
    role: UserRole = Field(..., description="Rol del usuario")
    permissions: Optional[List[str]] = Field(None, description="Permisos específicos")
    is_active: bool = Field(..., description="Estado activo")
    is_superuser: bool = Field(..., description="Es superusuario")
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: datetime = Field(..., description="Fecha de última actualización")
    last_login: Optional[datetime] = Field(None, description="Último inicio de sesión")

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class UserProfile(BaseModel):
    """Esquema para perfil de usuario"""
    id: int
    username: str
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class PasswordChange(BaseModel):
    """Esquema para cambio de contraseña"""
    current_password: str = Field(..., description="Contraseña actual")
    new_password: str = Field(..., min_length=8, description="Nueva contraseña")
    confirm_password: str = Field(..., description="Confirmación de nueva contraseña")

    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Las contraseñas no coinciden')
        return v

    @validator('new_password')
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('La contraseña debe tener al menos 8 caracteres')
        if not any(c.isupper() for c in v):
            raise ValueError('La contraseña debe contener al menos una letra mayúscula')
        if not any(c.islower() for c in v):
            raise ValueError('La contraseña debe contener al menos una letra minúscula')
        if not any(c.isdigit() for c in v):
            raise ValueError('La contraseña debe contener al menos un número')
        return v

class UserListResponse(BaseModel):
    """Esquema para lista de usuarios"""
    users: List[UserResponse] = Field(..., description="Lista de usuarios")
    total: int = Field(..., description="Total de usuarios")
    page: int = Field(..., description="Página actual")
    per_page: int = Field(..., description="Usuarios por página")
    total_pages: int = Field(..., description="Total de páginas")

class UserStats(BaseModel):
    """Esquema para estadísticas de usuarios"""
    total_users: int = Field(..., description="Total de usuarios")
    active_users: int = Field(..., description="Usuarios activos")
    inactive_users: int = Field(..., description="Usuarios inactivos")
    users_by_role: dict = Field(..., description="Usuarios por rol")
    new_users_today: int = Field(..., description="Nuevos usuarios hoy")
    new_users_this_week: int = Field(..., description="Nuevos usuarios esta semana")
    new_users_this_month: int = Field(..., description="Nuevos usuarios este mes")
