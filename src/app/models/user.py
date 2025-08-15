"""
Modelo User - Administradores del sistema
========================================

Modelo para gestionar usuarios administradores del sistema de paquetería.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from passlib.hash import bcrypt

from ..core.database import Base


class User(Base):
    """
    Modelo para usuarios administradores del sistema
    """
    
    __tablename__ = "users"
    
    # =============================================================================
    # CAMPOS PRINCIPALES
    # =============================================================================
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    full_name = Column(String(100), nullable=False)
    
    # =============================================================================
    # SEGURIDAD
    # =============================================================================
    
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    
    # =============================================================================
    # ROLES Y PERMISOS
    # =============================================================================
    
    role = Column(String(20), default="admin", nullable=False)  # admin, manager, operator
    permissions = Column(Text, nullable=True)  # JSON string de permisos
    
    # =============================================================================
    # METADATA
    # =============================================================================
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # =============================================================================
    # MÉTODOS
    # =============================================================================
    
    def set_password(self, password: str) -> None:
        """
        Hashear y establecer contraseña
        
        Args:
            password: Contraseña en texto plano
        """
        self.hashed_password = bcrypt.hash(password)
    
    def verify_password(self, password: str) -> bool:
        """
        Verificar contraseña
        
        Args:
            password: Contraseña en texto plano
            
        Returns:
            bool: True si la contraseña es correcta
        """
        return bcrypt.verify(password, self.hashed_password)
    
    def has_permission(self, permission: str) -> bool:
        """
        Verificar si el usuario tiene un permiso específico
        
        Args:
            permission: Permiso a verificar
            
        Returns:
            bool: True si tiene el permiso
        """
        if self.is_superuser:
            return True
        
        if not self.permissions:
            return False
        
        import json
        try:
            user_permissions = json.loads(self.permissions)
            return permission in user_permissions
        except (json.JSONDecodeError, TypeError):
            return False
    
    def add_permission(self, permission: str) -> None:
        """
        Agregar un permiso al usuario
        
        Args:
            permission: Permiso a agregar
        """
        import json
        
        if not self.permissions:
            self.permissions = json.dumps([permission])
        else:
            try:
                user_permissions = json.loads(self.permissions)
                if permission not in user_permissions:
                    user_permissions.append(permission)
                    self.permissions = json.dumps(user_permissions)
            except (json.JSONDecodeError, TypeError):
                self.permissions = json.dumps([permission])
    
    def remove_permission(self, permission: str) -> None:
        """
        Remover un permiso del usuario
        
        Args:
            permission: Permiso a remover
        """
        import json
        
        if not self.permissions:
            return
        
        try:
            user_permissions = json.loads(self.permissions)
            if permission in user_permissions:
                user_permissions.remove(permission)
                self.permissions = json.dumps(user_permissions)
        except (json.JSONDecodeError, TypeError):
            pass
    
    def update_last_login(self) -> None:
        """
        Actualizar timestamp del último login
        """
        self.last_login = datetime.utcnow()
    
    # =============================================================================
    # REPRESENTACIÓN
    # =============================================================================
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"
    
    def __str__(self) -> str:
        return f"{self.full_name} ({self.username})"
    
    # =============================================================================
    # PROPIEDADES
    # =============================================================================
    
    @property
    def is_authenticated(self) -> bool:
        """Verificar si el usuario está autenticado"""
        return self.is_active
    
    @property
    def display_name(self) -> str:
        """Nombre para mostrar"""
        return self.full_name or self.username
