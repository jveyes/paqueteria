"""
Authentication Routes
====================

Rutas para autenticación y autorización.
"""

from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.auth import (
    authenticate_user, create_access_token, create_refresh_token,
    get_current_user, get_current_active_user, get_current_superuser,
    verify_token, refresh_access_token, get_password_hash
)
from ..models.user import User
from ..schemas.user import UserLogin, UserToken, UserResponse, PasswordChange
from ..core.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])

security = HTTPBearer()

@router.post("/login", response_model=UserToken)
async def login(
    user_credentials: UserLogin,
    db: Session = Depends(get_db)
) -> Any:
    """
    Iniciar sesión de usuario
    
    Args:
        user_credentials: Credenciales del usuario
        db: Sesión de base de datos
        
    Returns:
        UserToken: Token de acceso y información del usuario
    """
    # Autenticar usuario
    user = authenticate_user(db, user_credentials.username, user_credentials.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuario inactivo"
        )
    
    # Crear tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        data={"sub": user.username}, expires_delta=refresh_token_expires
    )
    
    # Actualizar último login
    user.last_login = timedelta.now()
    db.commit()
    
    return UserToken(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.from_orm(user)
    )

@router.post("/refresh", response_model=dict)
async def refresh_token(
    refresh_token: str,
    db: Session = Depends(get_db)
) -> Any:
    """
    Refrescar token de acceso
    
    Args:
        refresh_token: Token de refresco
        db: Sesión de base de datos
        
    Returns:
        dict: Nuevo token de acceso
    """
    try:
        # Verificar token de refresco
        payload = verify_token(refresh_token)
        username = payload.get("sub")
        
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de refresco inválido"
            )
        
        # Obtener usuario
        user = db.query(User).filter(User.username == username).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario no encontrado o inactivo"
            )
        
        # Crear nuevo token de acceso
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        new_access_token = create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )
        
        return {
            "access_token": new_access_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de refresco inválido"
        )

@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Cerrar sesión
    
    Args:
        current_user: Usuario actual
        
    Returns:
        dict: Mensaje de confirmación
    """
    # En una implementación más avanzada, aquí se invalidaría el token
    # Por ahora, solo retornamos un mensaje de éxito
    return {"message": "Sesión cerrada exitosamente"}

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Obtener información del usuario actual
    
    Args:
        current_user: Usuario actual
        
    Returns:
        UserResponse: Información del usuario
    """
    return UserResponse.from_orm(current_user)

@router.put("/me/password")
async def change_password(
    password_change: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Cambiar contraseña del usuario actual
    
    Args:
        password_change: Datos para cambio de contraseña
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        dict: Mensaje de confirmación
    """
    # Verificar contraseña actual
    if not current_user.verify_password(password_change.current_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contraseña actual incorrecta"
        )
    
    # Cambiar contraseña
    current_user.set_password(password_change.new_password)
    db.commit()
    
    return {"message": "Contraseña cambiada exitosamente"}

@router.post("/verify-token")
async def verify_access_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Any:
    """
    Verificar token de acceso
    
    Args:
        credentials: Credenciales de autorización
        
    Returns:
        dict: Información del token
    """
    try:
        payload = verify_token(credentials.credentials)
        return {
            "valid": True,
            "username": payload.get("sub"),
            "exp": payload.get("exp")
        }
    except Exception:
        return {"valid": False}

@router.get("/permissions")
async def get_user_permissions(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Obtener permisos del usuario actual
    
    Args:
        current_user: Usuario actual
        
    Returns:
        dict: Permisos del usuario
    """
    return {
        "user_id": current_user.id,
        "username": current_user.username,
        "role": current_user.role,
        "permissions": current_user.permissions_list,
        "is_superuser": current_user.is_superuser
    }

@router.post("/register", response_model=UserResponse)
async def register_user(
    user_data: dict,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
) -> Any:
    """
    Registrar nuevo usuario (solo superusuarios)
    
    Args:
        user_data: Datos del nuevo usuario
        current_user: Usuario actual (debe ser superusuario)
        db: Sesión de base de datos
        
    Returns:
        UserResponse: Usuario creado
    """
    # Verificar que el usuario actual sea superusuario
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los superusuarios pueden registrar nuevos usuarios"
        )
    
    # Verificar que el username no exista
    existing_user = db.query(User).filter(User.username == user_data["username"]).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El nombre de usuario ya existe"
        )
    
    # Verificar que el email no exista
    existing_email = db.query(User).filter(User.email == user_data["email"]).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya está registrado"
        )
    
    # Crear nuevo usuario
    hashed_password = get_password_hash(user_data["password"])
    new_user = User(
        username=user_data["username"],
        email=user_data["email"],
        full_name=user_data["full_name"],
        hashed_password=hashed_password,
        role=user_data.get("role", "operator"),
        is_active=user_data.get("is_active", True)
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return UserResponse.from_orm(new_user)

@router.get("/health")
async def auth_health_check() -> Any:
    """
    Health check para el módulo de autenticación
    
    Returns:
        dict: Estado del módulo
    """
    return {
        "status": "healthy",
        "module": "authentication",
        "jwt_enabled": bool(settings.SECRET_KEY),
        "access_token_expire_minutes": settings.ACCESS_TOKEN_EXPIRE_MINUTES
    }
