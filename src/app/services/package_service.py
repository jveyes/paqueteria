"""
Package Service
==============

Servicio para gestión de paquetes con lógica de negocio.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc
import logging

from ..models.package import Package, PackageType, PackageStatus
from ..models.customer import Customer
from ..models.file_upload import FileUpload
from ..models.notification import Notification
from ..models.delivery import Delivery
from ..schemas.package import (
    PackageCreate, PackageUpdate, PackageAnnounce, PackageReceive,
    PackageSearch, PackageStats, PackageTracking
)
from ..core.config import settings
from .customer_service import CustomerService
from .notification_service import NotificationService
from .file_service import FileService

logger = logging.getLogger(__name__)

class PackageService:
    """Servicio para gestión de paquetes"""
    
    def __init__(self, db: Session):
        self.db = db
        self.customer_service = CustomerService(db)
        self.notification_service = NotificationService(db)
        self.file_service = FileService(db)
    
    def announce_package(self, package_data: PackageAnnounce) -> Package:
        """
        Anunciar un nuevo paquete
        
        Args:
            package_data: Datos del paquete y cliente
            
        Returns:
            Package: Paquete creado
        """
        try:
            # Buscar o crear cliente
            customer = self.customer_service.get_or_create_customer(
                phone_number=package_data.customer_phone,
                full_name=package_data.customer_name,
                email=package_data.customer_email,
                address=package_data.customer_address,
                city=package_data.customer_city
            )
            
            # Crear paquete
            package = Package(
                customer_id=customer.id,
                description=package_data.description,
                package_type=package_data.package_type,
                weight_kg=package_data.weight_kg,
                length_cm=package_data.length_cm,
                width_cm=package_data.width_cm,
                height_cm=package_data.height_cm,
                is_urgent=package_data.is_urgent,
                customer_notes=package_data.customer_notes,
                status=PackageStatus.ANNOUNCED,
                announced_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(days=30)
            )
            
            # Generar número de tracking
            package.generate_tracking_number()
            
            # Calcular costos
            package.calculate_costs()
            
            self.db.add(package)
            self.db.commit()
            self.db.refresh(package)
            
            # Enviar notificación SMS al cliente
            self._send_announcement_notification(package)
            
            logger.info(f"Paquete anunciado: {package.tracking_number}")
            return package
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error anunciando paquete: {e}")
            raise
    
    def receive_package(self, tracking_number: str, notes: Optional[str] = None) -> Package:
        """
        Recibir un paquete anunciado
        
        Args:
            tracking_number: Número de tracking del paquete
            notes: Notas de recepción
            
        Returns:
            Package: Paquete actualizado
        """
        try:
            package = self.get_package_by_tracking(tracking_number)
            
            if not package:
                raise ValueError(f"Paquete no encontrado: {tracking_number}")
            
            if package.status != PackageStatus.ANNOUNCED:
                raise ValueError(f"Paquete no puede ser recibido. Estado actual: {package.status}")
            
            # Actualizar estado
            package.status = PackageStatus.RECEIVED
            package.received_at = datetime.utcnow()
            
            # Actualizar costos de bodegaje
            package.calculate_costs()
            
            self.db.commit()
            self.db.refresh(package)
            
            # Enviar notificación de recepción
            self._send_reception_notification(package)
            
            logger.info(f"Paquete recibido: {tracking_number}")
            return package
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error recibiendo paquete {tracking_number}: {e}")
            raise
    
    def deliver_package(self, tracking_number: str, delivery_data: dict) -> Delivery:
        """
        Entregar un paquete recibido
        
        Args:
            tracking_number: Número de tracking del paquete
            delivery_data: Datos de la entrega
            
        Returns:
            Delivery: Entrega creada
        """
        try:
            package = self.get_package_by_tracking(tracking_number)
            
            if not package:
                raise ValueError(f"Paquete no encontrado: {tracking_number}")
            
            if package.status != PackageStatus.RECEIVED:
                raise ValueError(f"Paquete no puede ser entregado. Estado actual: {package.status}")
            
            # Crear entrega
            from ..models.delivery import Delivery, DeliveryStatus, PaymentMethod
            
            delivery = Delivery(
                package_id=package.id,
                recipient_name=delivery_data['recipient_name'],
                recipient_id=delivery_data.get('recipient_id'),
                payment_method=PaymentMethod(delivery_data['payment_method']),
                amount_paid=Decimal(str(delivery_data['amount_paid'])),
                notes=delivery_data.get('notes'),
                status=DeliveryStatus.COMPLETED,
                completed_at=datetime.utcnow()
            )
            
            delivery.generate_delivery_number()
            
            self.db.add(delivery)
            
            # Actualizar estado del paquete
            package.status = PackageStatus.DELIVERED
            package.delivered_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(delivery)
            self.db.refresh(package)
            
            # Enviar notificación de entrega
            self._send_delivery_notification(package, delivery)
            
            logger.info(f"Paquete entregado: {tracking_number}")
            return delivery
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error entregando paquete {tracking_number}: {e}")
            raise
    
    def get_package_by_tracking(self, tracking_number: str) -> Optional[Package]:
        """Obtener paquete por número de tracking"""
        return self.db.query(Package).filter(Package.tracking_number == tracking_number).first()
    
    def get_package_by_id(self, package_id: int) -> Optional[Package]:
        """Obtener paquete por ID"""
        return self.db.query(Package).filter(Package.id == package_id).first()
    
    def search_packages(self, search_params: PackageSearch) -> Dict[str, Any]:
        """
        Buscar paquetes con filtros
        
        Args:
            search_params: Parámetros de búsqueda
            
        Returns:
            Dict con paquetes y metadatos de paginación
        """
        query = self.db.query(Package)
        
        # Aplicar filtros
        if search_params.query:
            search_term = f"%{search_params.query}%"
            query = query.filter(
                or_(
                    Package.tracking_number.ilike(search_term),
                    Package.description.ilike(search_term),
                    Package.customer.has(Customer.full_name.ilike(search_term)),
                    Package.customer.has(Customer.phone_number.ilike(search_term))
                )
            )
        
        if search_params.tracking_number:
            query = query.filter(Package.tracking_number == search_params.tracking_number)
        
        if search_params.customer_phone:
            query = query.filter(Package.customer.has(Customer.phone_number == search_params.customer_phone))
        
        if search_params.status:
            query = query.filter(Package.status == search_params.status)
        
        if search_params.package_type:
            query = query.filter(Package.package_type == search_params.package_type)
        
        if search_params.is_urgent is not None:
            query = query.filter(Package.is_urgent == search_params.is_urgent)
        
        if search_params.date_from:
            query = query.filter(Package.announced_at >= search_params.date_from)
        
        if search_params.date_to:
            query = query.filter(Package.announced_at <= search_params.date_to)
        
        # Contar total
        total = query.count()
        
        # Aplicar paginación
        offset = (search_params.page - 1) * search_params.per_page
        packages = query.offset(offset).limit(search_params.per_page).all()
        
        # Calcular páginas
        total_pages = (total + search_params.per_page - 1) // search_params.per_page
        
        return {
            "packages": packages,
            "total": total,
            "page": search_params.page,
            "per_page": search_params.per_page,
            "total_pages": total_pages
        }
    
    def get_package_stats(self) -> PackageStats:
        """Obtener estadísticas de paquetes"""
        today = datetime.utcnow().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        # Totales
        total_packages = self.db.query(Package).count()
        announced_count = self.db.query(Package).filter(Package.status == PackageStatus.ANNOUNCED).count()
        received_count = self.db.query(Package).filter(Package.status == PackageStatus.RECEIVED).count()
        delivered_count = self.db.query(Package).filter(Package.status == PackageStatus.DELIVERED).count()
        expired_count = self.db.query(Package).filter(Package.status == PackageStatus.EXPIRED).count()
        urgent_count = self.db.query(Package).filter(Package.is_urgent == True).count()
        
        # Paquetes de hoy
        packages_today = self.db.query(Package).filter(
            func.date(Package.announced_at) == today
        ).count()
        
        # Ingresos
        revenue_today = self.db.query(func.sum(Package.total_cost)).filter(
            func.date(Package.delivered_at) == today
        ).scalar() or Decimal('0')
        
        revenue_this_week = self.db.query(func.sum(Package.total_cost)).filter(
            Package.delivered_at >= week_ago
        ).scalar() or Decimal('0')
        
        revenue_this_month = self.db.query(func.sum(Package.total_cost)).filter(
            Package.delivered_at >= month_ago
        ).scalar() or Decimal('0')
        
        # Tiempo promedio de entrega
        avg_delivery_time = self.db.query(
            func.avg(func.extract('epoch', Package.delivered_at - Package.received_at) / 86400)
        ).filter(
            Package.delivered_at.isnot(None)
        ).scalar()
        
        # Paquetes por tipo
        packages_by_type = {}
        for package_type in PackageType:
            count = self.db.query(Package).filter(Package.package_type == package_type).count()
            packages_by_type[package_type.value] = count
        
        # Paquetes por estado
        packages_by_status = {}
        for status in PackageStatus:
            count = self.db.query(Package).filter(Package.status == status).count()
            packages_by_status[status.value] = count
        
        return PackageStats(
            total_packages=total_packages,
            announced_count=announced_count,
            received_count=received_count,
            delivered_count=delivered_count,
            expired_count=expired_count,
            urgent_count=urgent_count,
            packages_today=packages_today,
            revenue_today=revenue_today,
            revenue_this_week=revenue_this_week,
            revenue_this_month=revenue_this_month,
            average_delivery_time=float(avg_delivery_time) if avg_delivery_time else None,
            packages_by_type=packages_by_type,
            packages_by_status=packages_by_status
        )
    
    def get_package_tracking(self, tracking_number: str) -> Optional[PackageTracking]:
        """Obtener información de seguimiento de paquete"""
        package = self.get_package_by_tracking(tracking_number)
        
        if not package:
            return None
        
        # Construir timeline
        timeline = []
        
        # Anuncio
        timeline.append({
            "event": "announced",
            "date": package.announced_at,
            "description": "Paquete anunciado",
            "icon": "box"
        })
        
        # Recepción
        if package.received_at:
            timeline.append({
                "event": "received",
                "date": package.received_at,
                "description": "Paquete recibido en nuestras instalaciones",
                "icon": "download"
            })
        
        # Entrega
        if package.delivered_at:
            timeline.append({
                "event": "delivered",
                "date": package.delivered_at,
                "description": "Paquete entregado al cliente",
                "icon": "truck"
            })
        
        # Ordenar por fecha
        timeline.sort(key=lambda x: x["date"])
        
        return PackageTracking(
            tracking_number=package.tracking_number,
            status=package.status,
            description=package.description,
            customer_name=package.customer.full_name,
            customer_phone=package.customer.phone_number,
            total_cost=package.total_cost,
            announced_at=package.announced_at,
            received_at=package.received_at,
            delivered_at=package.delivered_at,
            expires_at=package.expires_at,
            timeline=timeline
        )
    
    def update_package(self, package_id: int, update_data: PackageUpdate) -> Optional[Package]:
        """Actualizar paquete"""
        package = self.get_package_by_id(package_id)
        
        if not package:
            return None
        
        # Actualizar campos
        for field, value in update_data.dict(exclude_unset=True).items():
            setattr(package, field, value)
        
        # Recalcular costos si es necesario
        if any(field in update_data.dict(exclude_unset=True) for field in ['weight_kg', 'length_cm', 'width_cm', 'height_cm']):
            package.calculate_costs()
        
        package.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(package)
        
        return package
    
    def delete_package(self, package_id: int) -> bool:
        """Eliminar paquete (soft delete)"""
        package = self.get_package_by_id(package_id)
        
        if not package:
            return False
        
        # Solo permitir eliminar paquetes anunciados
        if package.status != PackageStatus.ANNOUNCED:
            raise ValueError("Solo se pueden eliminar paquetes anunciados")
        
        self.db.delete(package)
        self.db.commit()
        
        return True
    
    def expire_packages(self) -> int:
        """Expirar paquetes que han superado el límite de tiempo"""
        expired_date = datetime.utcnow() - timedelta(days=30)
        
        expired_packages = self.db.query(Package).filter(
            and_(
                Package.status == PackageStatus.ANNOUNCED,
                Package.announced_at < expired_date
            )
        ).all()
        
        count = 0
        for package in expired_packages:
            package.status = PackageStatus.EXPIRED
            package.updated_at = datetime.utcnow()
            count += 1
        
        self.db.commit()
        
        if count > 0:
            logger.info(f"Expiraron {count} paquetes")
        
        return count
    
    def _send_announcement_notification(self, package: Package):
        """Enviar notificación de anuncio"""
        try:
            message = f"Su paquete ha sido anunciado. Número de tracking: {package.tracking_number}. Costo: ${package.total_cost:,.0f} COP"
            
            self.notification_service.send_sms(
                phone_number=package.customer.phone_number,
                message=message,
                package_id=package.id,
                customer_id=package.customer.id
            )
        except Exception as e:
            logger.error(f"Error enviando notificación de anuncio: {e}")
    
    def _send_reception_notification(self, package: Package):
        """Enviar notificación de recepción"""
        try:
            message = f"Su paquete {package.tracking_number} ha sido recibido. Está listo para recoger."
            
            self.notification_service.send_sms(
                phone_number=package.customer.phone_number,
                message=message,
                package_id=package.id,
                customer_id=package.customer.id
            )
        except Exception as e:
            logger.error(f"Error enviando notificación de recepción: {e}")
    
    def _send_delivery_notification(self, package: Package, delivery):
        """Enviar notificación de entrega"""
        try:
            message = f"Su paquete {package.tracking_number} ha sido entregado exitosamente. Gracias por usar nuestros servicios."
            
            self.notification_service.send_sms(
                phone_number=package.customer.phone_number,
                message=message,
                package_id=package.id,
                customer_id=package.customer.id
            )
        except Exception as e:
            logger.error(f"Error enviando notificación de entrega: {e}")
