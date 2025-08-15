"""
Schemas de validación Pydantic
==============================

Esquemas para validación de datos de entrada y salida de la API.
"""

from .user import UserCreate, UserUpdate, UserResponse, UserLogin, UserToken
from .customer import CustomerCreate, CustomerUpdate, CustomerResponse
from .package import PackageCreate, PackageUpdate, PackageResponse, PackageAnnounce
from .notification import NotificationCreate, NotificationResponse
from .delivery import DeliveryCreate, DeliveryUpdate, DeliveryResponse
from .file_upload import FileUploadResponse

__all__ = [
    # User schemas
    "UserCreate", "UserUpdate", "UserResponse", "UserLogin", "UserToken",
    
    # Customer schemas
    "CustomerCreate", "CustomerUpdate", "CustomerResponse",
    
    # Package schemas
    "PackageCreate", "PackageUpdate", "PackageResponse", "PackageAnnounce",
    
    # Notification schemas
    "NotificationCreate", "NotificationResponse",
    
    # Delivery schemas
    "DeliveryCreate", "DeliveryUpdate", "DeliveryResponse",
    
    # File upload schemas
    "FileUploadResponse"
]
