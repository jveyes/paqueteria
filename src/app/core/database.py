"""
Configuración de base de datos
=============================

Configura SQLAlchemy 2.0 con async support, sesiones,
y utilidades para manejo de transacciones.
"""

from typing import AsyncGenerator, Generator
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from .config import settings

# =============================================================================
# CONFIGURACIÓN DE BASE DE DATOS
# =============================================================================

# Crear base para modelos
Base = declarative_base()

# Metadata para migraciones
metadata = MetaData()

# =============================================================================
# ENGINE Y SESSION SYNC (para migraciones y operaciones síncronas)
# =============================================================================

# Engine síncrono para migraciones
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=10,
    max_overflow=20,
    # Configuración específica para MySQL
    connect_args={
        "charset": "utf8mb4",
        "autocommit": False,
    } if "mysql" in settings.DATABASE_URL else {}
)

# Session factory síncrona
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# =============================================================================
# ENGINE Y SESSION ASYNC (para operaciones asíncronas)
# =============================================================================

# Convertir URL a async si es necesario
async_database_url = settings.DATABASE_URL
if async_database_url.startswith("mysql+pymysql"):
    async_database_url = async_database_url.replace("mysql+pymysql", "mysql+aiomysql")

# Engine asíncrono
async_engine = create_async_engine(
    async_database_url,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=10,
    max_overflow=20,
    # Configuración específica para MySQL
    connect_args={
        "charset": "utf8mb4",
        "autocommit": False,
    } if "mysql" in async_database_url else {}
)

# Session factory asíncrona
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# =============================================================================
# FUNCIONES DE UTILIDAD
# =============================================================================

def get_db() -> Generator[Session, None, None]:
    """
    Dependency para obtener sesión de base de datos síncrona
    
    Yields:
        Session: Sesión de SQLAlchemy
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency para obtener sesión de base de datos asíncrona
    
    Yields:
        AsyncSession: Sesión asíncrona de SQLAlchemy
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def create_tables() -> None:
    """
    Crear todas las tablas en la base de datos
    """
    Base.metadata.create_all(bind=engine)


async def create_tables_async() -> None:
    """
    Crear todas las tablas en la base de datos (async)
    """
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def drop_tables() -> None:
    """
    Eliminar todas las tablas de la base de datos
    """
    Base.metadata.drop_all(bind=engine)


async def drop_tables_async() -> None:
    """
    Eliminar todas las tablas de la base de datos (async)
    """
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# =============================================================================
# UTILIDADES DE TRANSACCIÓN
# =============================================================================

class DatabaseTransaction:
    """
    Context manager para manejar transacciones de base de datos
    """
    
    def __init__(self, session: Session):
        self.session = session
        self._transaction = None
    
    def __enter__(self):
        self._transaction = self.session.begin()
        return self.session
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # Rollback en caso de excepción
            self.session.rollback()
        else:
            # Commit si todo está bien
            self.session.commit()
        self.session.close()


class AsyncDatabaseTransaction:
    """
    Context manager para manejar transacciones asíncronas de base de datos
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self._transaction = None
    
    async def __aenter__(self):
        self._transaction = await self.session.begin()
        return self.session
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # Rollback en caso de excepción
            await self.session.rollback()
        else:
            # Commit si todo está bien
            await self.session.commit()
        await self.session.close()


# =============================================================================
# FUNCIONES DE CONEXIÓN
# =============================================================================

def check_database_connection() -> bool:
    """
    Verificar conexión a la base de datos
    
    Returns:
        bool: True si la conexión es exitosa
    """
    try:
        with engine.connect() as connection:
            connection.execute("SELECT 1")
        return True
    except Exception as e:
        print(f"Error de conexión a la base de datos: {e}")
        return False


async def check_async_database_connection() -> bool:
    """
    Verificar conexión asíncrona a la base de datos
    
    Returns:
        bool: True si la conexión es exitosa
    """
    try:
        async with async_engine.connect() as connection:
            await connection.execute("SELECT 1")
        return True
    except Exception as e:
        print(f"Error de conexión asíncrona a la base de datos: {e}")
        return False


# =============================================================================
# CONFIGURACIÓN DE MIGRACIONES
# =============================================================================

def get_alembic_config() -> dict:
    """
    Obtener configuración para Alembic
    
    Returns:
        dict: Configuración de Alembic
    """
    return {
        "script_location": "alembic",
        "sqlalchemy.url": settings.DATABASE_URL,
        "file_template": "%(year)d%(month).2d%(day).2d_%(hour).2d%(minute).2d_%(rev)s_%(slug)s",
        "version_path": "alembic/versions",
        "version_table": "alembic_version",
        "version_table_schema": None,
        "compare_type": True,
        "compare_server_default": True,
        "render_as_batch": True,
        "include_schemas": False,
        "include_name": None,
        "include_object": None,
        "include_symbol": None,
        "prepend_sys_path": ".",
        "version_num_template": "%04d",
        "version_name_template": "%(rev)s_%(slug)s",
        "version_locations": None,
        "file_template": "%(year)d%(month).2d%(day).2d_%(hour).2d%(minute).2d_%(rev)s_%(slug)s",
    }
