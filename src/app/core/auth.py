"""
Sistema de Autenticación JWT
===========================

Configuración y utilidades para autenticación JWT.
"""

from datetime import datetime, timedelta
from typing import Optional, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from ..models.user import User

# =============================================================================
# CONFIGURACIÓN DE SEGURIDAD
# =============================================================================

# Contexto para hashing de contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Esquema de seguridad para JWT
security = HTTPBearer()

# =============================================================================
# FUNCIONES DE UTILIDAD
# =============================================================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verificar contraseña
    
    Args:
        plain_password: Contraseña en texto plano
        hashed_password: Contraseña hasheada
        
    Returns:
        bool: True si la contraseña es correcta
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hashear contraseña
    
    Args:
        password: Contraseña en texto plano
        
    Returns:
        str: Contraseña hasheada
    """
    return pwd_context.hash(password)


def create_access_token(
    data: dict, 
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Crear token de acceso JWT
    
    Args:
        data: Datos a incluir en el token
        expires_delta: Tiempo de expiración
        
    Returns:
        str: Token JWT
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.SECRET_KEY.get_secret_value(), 
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Crear token de refresh JWT
    
    Args:
        data: Datos a incluir en el token
        expires_delta: Tiempo de expiración
        
    Returns:
        str: Token JWT de refresh
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.SECRET_KEY.get_secret_value(), 
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def verify_token(token: str) -> dict:
    """
    Verificar y decodificar token JWT
    
    Args:
        token: Token JWT
        
    Returns:
        dict: Datos del token
        
    Raises:
        HTTPException: Si el token es inválido
    """
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY.get_secret_value(), 
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )


# =============================================================================
# FUNCIONES DE AUTENTICACIÓN
# =============================================================================

def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """
    Autenticar usuario
    
    Args:
        db: Sesión de base de datos
        username: Nombre de usuario
        password: Contraseña
        
    Returns:
        User: Usuario autenticado o None
    """
    # Buscar por username o email
    user = db.query(User).filter(
        (User.username == username) | (User.email == username)
    ).first()
    
    if not user:
        return None
    
    if not verify_password(password, user.hashed_password):
        return None
    
    if not user.is_active:
        return None
    
    return user


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Obtener usuario actual desde token JWT
    
    Args:
        credentials: Credenciales HTTP
        db: Sesión de base de datos
        
    Returns:
        User: Usuario actual
        
    Raises:
        HTTPException: Si el token es inválido o el usuario no existe
    """
    token = credentials.credentials
    payload = verify_token(token)
    
    user_id: int = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario inactivo",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Obtener usuario activo actual
    
    Args:
        current_user: Usuario actual
        
    Returns:
        User: Usuario activo
        
    Raises:
        HTTPException: Si el usuario no está activo
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuario inactivo"
        )
    return current_user


def get_current_superuser(current_user: User = Depends(get_current_user)) -> User:
    """
    Obtener superusuario actual
    
    Args:
        current_user: Usuario actual
        
    Returns:
        User: Superusuario
        
    Raises:
        HTTPException: Si el usuario no es superusuario
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permisos insuficientes"
        )
    return current_user


# =============================================================================
# FUNCIONES DE PERMISOS
# =============================================================================

def require_permission(permission: str):
    """
    Decorador para requerir un permiso específico
    
    Args:
        permission: Permiso requerido
        
    Returns:
        function: Función decorada
    """
    def permission_checker(current_user: User = Depends(get_current_user)) -> User:
        if not current_user.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permiso requerido: {permission}"
            )
        return current_user
    
    return permission_checker


def require_role(role: str):
    """
    Decorador para requerir un rol específico
    
    Args:
        role: Rol requerido
        
    Returns:
        function: Función decorada
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role != role and not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Rol requerido: {role}"
            )
        return current_user
    
    return role_checker


# =============================================================================
# FUNCIONES DE TOKEN
# =============================================================================

def create_tokens_for_user(user: User) -> dict:
    """
    Crear tokens de acceso y refresh para un usuario
    
    Args:
        user: Usuario
        
    Returns:
        dict: Tokens creados
    """
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    access_token = create_access_token(
        data={"sub": str(user.id), "username": user.username, "role": user.role},
        expires_delta=access_token_expires
    )
    
    refresh_token = create_refresh_token(
        data={"sub": str(user.id)},
        expires_delta=refresh_token_expires
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }


def refresh_access_token(refresh_token: str) -> str:
    """
    Refrescar token de acceso usando refresh token
    
    Args:
        refresh_token: Token de refresh
        
    Returns:
        str: Nuevo token de acceso
        
    Raises:
        HTTPException: Si el refresh token es inválido
    """
    try:
        payload = jwt.decode(
            refresh_token,
            settings.SECRET_KEY.get_secret_value(),
            algorithms=[settings.ALGORITHM]
        )
        
        # Verificar que es un refresh token
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de refresh inválido"
            )
        
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de refresh inválido"
            )
        
        # Crear nuevo access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user_id},
            expires_delta=access_token_expires
        )
        
        return access_token
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de refresh inválido"
        )


# =============================================================================
# CONSTANTES DE PERMISOS
# =============================================================================

# Permisos del sistema
PERMISSIONS = {
    # Gestión de paquetes
    "package:create": "Crear paquetes",
    "package:read": "Leer paquetes",
    "package:update": "Actualizar paquetes",
    "package:delete": "Eliminar paquetes",
    "package:receive": "Recibir paquetes",
    "package:deliver": "Entregar paquetes",
    
    # Gestión de clientes
    "customer:create": "Crear clientes",
    "customer:read": "Leer clientes",
    "customer:update": "Actualizar clientes",
    "customer:delete": "Eliminar clientes",
    
    # Gestión de usuarios
    "user:create": "Crear usuarios",
    "user:read": "Leer usuarios",
    "user:update": "Actualizar usuarios",
    "user:delete": "Eliminar usuarios",
    
    # Gestión de notificaciones
    "notification:send": "Enviar notificaciones",
    "notification:read": "Leer notificaciones",
    
    # Reportes y estadísticas
    "report:view": "Ver reportes",
    "report:export": "Exportar reportes",
    
    # Configuración del sistema
    "system:configure": "Configurar sistema",
    "system:backup": "Realizar backups",
}


# Roles predefinidos
ROLES = {
    "admin": {
        "name": "Administrador",
        "description": "Acceso completo al sistema",
        "permissions": list(PERMISSIONS.keys())
    },
    "manager": {
        "name": "Gerente",
        "description": "Gestión de operaciones",
        "permissions": [
            "package:create", "package:read", "package:update", "package:receive", "package:deliver",
            "customer:create", "customer:read", "customer:update",
            "notification:send", "notification:read",
            "report:view", "report:export"
        ]
    },
    "operator": {
        "name": "Operador",
        "description": "Operaciones básicas",
        "permissions": [
            "package:read", "package:receive", "package:deliver",
            "customer:read",
            "notification:read"
        ]
    }
}
