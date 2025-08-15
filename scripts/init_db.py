#!/usr/bin/env python3
"""
Script de inicialización de base de datos
=========================================

Crea las tablas y datos iniciales para el sistema de paquetería.
"""

import sys
import os
from pathlib import Path

# Agregar el directorio src al path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy.orm import Session
from app.core.database import engine, SessionLocal, create_tables
from app.core.auth import get_password_hash, ROLES
from app.models import User, Customer, Package, PackageType, PackageStatus
from app.core.logging import get_logger

logger = get_logger(__name__)


def create_superuser(db: Session) -> User:
    """
    Crear superusuario inicial
    
    Args:
        db: Sesión de base de datos
        
    Returns:
        User: Usuario creado
    """
    # Verificar si ya existe un superusuario
    existing_superuser = db.query(User).filter(User.is_superuser == True).first()
    if existing_superuser:
        logger.info(f"Superusuario ya existe: {existing_superuser.username}")
        return existing_superuser
    
    # Crear superusuario
    superuser = User(
        username="admin",
        email="admin@paqueteria.com",
        full_name="Administrador del Sistema",
        hashed_password=get_password_hash("admin123"),
        is_active=True,
        is_superuser=True,
        role="admin"
    )
    
    # Agregar todos los permisos
    import json
    superuser.permissions = json.dumps(list(ROLES["admin"]["permissions"]))
    
    db.add(superuser)
    db.commit()
    db.refresh(superuser)
    
    logger.info(f"Superusuario creado: {superuser.username}")
    return superuser


def create_sample_users(db: Session) -> list[User]:
    """
    Crear usuarios de ejemplo
    
    Args:
        db: Sesión de base de datos
        
    Returns:
        list[User]: Lista de usuarios creados
    """
    users_data = [
        {
            "username": "gerente",
            "email": "gerente@paqueteria.com",
            "full_name": "Gerente de Operaciones",
            "password": "gerente123",
            "role": "manager"
        },
        {
            "username": "operador",
            "email": "operador@paqueteria.com",
            "full_name": "Operador del Sistema",
            "password": "operador123",
            "role": "operator"
        }
    ]
    
    created_users = []
    
    for user_data in users_data:
        # Verificar si el usuario ya existe
        existing_user = db.query(User).filter(User.username == user_data["username"]).first()
        if existing_user:
            logger.info(f"Usuario ya existe: {existing_user.username}")
            created_users.append(existing_user)
            continue
        
        # Crear usuario
        user = User(
            username=user_data["username"],
            email=user_data["email"],
            full_name=user_data["full_name"],
            hashed_password=get_password_hash(user_data["password"]),
            is_active=True,
            is_superuser=False,
            role=user_data["role"]
        )
        
        # Agregar permisos según el rol
        import json
        if user_data["role"] in ROLES:
            user.permissions = json.dumps(ROLES[user_data["role"]]["permissions"])
        
        db.add(user)
        created_users.append(user)
        
        logger.info(f"Usuario creado: {user.username}")
    
    db.commit()
    return created_users


def create_sample_customers(db: Session) -> list[Customer]:
    """
    Crear clientes de ejemplo
    
    Args:
        db: Sesión de base de datos
        
    Returns:
        list[Customer]: Lista de clientes creados
    """
    customers_data = [
        {
            "phone_number": "3001234567",
            "full_name": "Juan Pérez",
            "email": "juan.perez@email.com",
            "address": "Calle 123 #45-67",
            "city": "Bogotá",
            "department": "Cundinamarca",
            "is_verified": True
        },
        {
            "phone_number": "3109876543",
            "full_name": "María García",
            "email": "maria.garcia@email.com",
            "address": "Carrera 78 #90-12",
            "city": "Medellín",
            "department": "Antioquia",
            "is_verified": True
        },
        {
            "phone_number": "3155551234",
            "full_name": "Carlos López",
            "email": "carlos.lopez@email.com",
            "address": "Avenida 5 #23-45",
            "city": "Cali",
            "department": "Valle del Cauca",
            "is_verified": False
        }
    ]
    
    created_customers = []
    
    for customer_data in customers_data:
        # Verificar si el cliente ya existe
        existing_customer = db.query(Customer).filter(
            Customer.phone_number == customer_data["phone_number"]
        ).first()
        
        if existing_customer:
            logger.info(f"Cliente ya existe: {existing_customer.full_name}")
            created_customers.append(existing_customer)
            continue
        
        # Crear cliente
        customer = Customer(**customer_data)
        db.add(customer)
        created_customers.append(customer)
        
        logger.info(f"Cliente creado: {customer.full_name}")
    
    db.commit()
    return created_customers


def create_sample_packages(db: Session, customers: list[Customer]) -> list[Package]:
    """
    Crear paquetes de ejemplo
    
    Args:
        db: Sesión de base de datos
        customers: Lista de clientes
        
    Returns:
        list[Package]: Lista de paquetes creados
    """
    if not customers:
        logger.warning("No hay clientes para crear paquetes")
        return []
    
    packages_data = [
        {
            "description": "Paquete con ropa y zapatos",
            "package_type": PackageType.NORMAL,
            "status": PackageStatus.ANNOUNCED,
            "weight_kg": 2.5,
            "length_cm": 30,
            "width_cm": 20,
            "height_cm": 15,
            "is_urgent": False
        },
        {
            "description": "Electrónicos frágiles",
            "package_type": PackageType.EXTRA_DIMENSIONED,
            "status": PackageStatus.RECEIVED,
            "weight_kg": 5.0,
            "length_cm": 50,
            "width_cm": 40,
            "height_cm": 30,
            "is_urgent": True
        },
        {
            "description": "Documentos importantes",
            "package_type": PackageType.NORMAL,
            "status": PackageStatus.DELIVERED,
            "weight_kg": 0.5,
            "length_cm": 25,
            "width_cm": 15,
            "height_cm": 5,
            "is_urgent": True
        }
    ]
    
    created_packages = []
    
    for i, package_data in enumerate(packages_data):
        # Asignar cliente de forma rotativa
        customer = customers[i % len(customers)]
        
        # Crear paquete
        package = Package(
            customer_id=customer.id,
            tracking_number=f"PAQ-20250115-{chr(65+i)}0001",  # A0001, B0001, C0001
            **package_data
        )
        
        # Calcular costos
        package.calculate_total_cost()
        
        # Si está recibido, establecer fecha de recepción
        if package.status == PackageStatus.RECEIVED:
            from datetime import datetime, timedelta
            package.received_at = datetime.utcnow() - timedelta(days=2)
            package.calculate_total_cost()
        
        # Si está entregado, establecer fecha de entrega
        if package.status == PackageStatus.DELIVERED:
            from datetime import datetime, timedelta
            package.received_at = datetime.utcnow() - timedelta(days=5)
            package.delivered_at = datetime.utcnow() - timedelta(days=1)
            package.calculate_total_cost()
        
        db.add(package)
        created_packages.append(package)
        
        logger.info(f"Paquete creado: {package.tracking_number}")
    
    db.commit()
    return created_packages


def main():
    """
    Función principal
    """
    logger.info("Iniciando inicialización de base de datos...")
    
    try:
        # Crear tablas
        logger.info("Creando tablas...")
        create_tables()
        logger.info("Tablas creadas exitosamente")
        
        # Crear sesión de base de datos
        db = SessionLocal()
        
        try:
            # Crear superusuario
            logger.info("Creando superusuario...")
            superuser = create_superuser(db)
            
            # Crear usuarios de ejemplo
            logger.info("Creando usuarios de ejemplo...")
            users = create_sample_users(db)
            
            # Crear clientes de ejemplo
            logger.info("Creando clientes de ejemplo...")
            customers = create_sample_customers(db)
            
            # Crear paquetes de ejemplo
            logger.info("Creando paquetes de ejemplo...")
            packages = create_sample_packages(db, customers)
            
            logger.info("Inicialización completada exitosamente!")
            logger.info(f"Usuarios creados: {len(users)}")
            logger.info(f"Clientes creados: {len(customers)}")
            logger.info(f"Paquetes creados: {len(packages)}")
            
            # Mostrar credenciales
            print("\n" + "="*50)
            print("CREDENCIALES DE ACCESO")
            print("="*50)
            print(f"Superusuario: {superuser.username}")
            print(f"Contraseña: admin123")
            print(f"Email: {superuser.email}")
            print("\nUsuarios de ejemplo:")
            for user in users:
                print(f"- {user.username}: {user.username}123")
            print("="*50)
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error durante la inicialización: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
