"""
Customer Service
===============

Servicio para gestión de clientes con lógica de negocio.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc
import logging
import re

from ..models.customer import Customer
from ..models.package import Package
from ..models.notification import Notification
from ..schemas.customer import (
    CustomerCreate, CustomerUpdate, CustomerSearch, CustomerStats,
    CustomerVerification, CustomerExport
)
from ..core.config import settings

logger = logging.getLogger(__name__)

class CustomerService:
    """Servicio para gestión de clientes"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_customer(self, customer_data: CustomerCreate) -> Customer:
        """
        Crear un nuevo cliente
        
        Args:
            customer_data: Datos del cliente
            
        Returns:
            Customer: Cliente creado
        """
        try:
            # Verificar si ya existe un cliente con ese teléfono
            existing_customer = self.get_customer_by_phone(customer_data.phone_number)
            if existing_customer:
                raise ValueError(f"Ya existe un cliente con el teléfono {customer_data.phone_number}")
            
            # Crear cliente
            customer = Customer(
                phone_number=customer_data.phone_number,
                full_name=customer_data.full_name,
                email=customer_data.email,
                address=customer_data.address,
                city=customer_data.city,
                is_verified=customer_data.is_verified,
                verification_code=customer_data.verification_code
            )
            
            self.db.add(customer)
            self.db.commit()
            self.db.refresh(customer)
            
            logger.info(f"Cliente creado: {customer.full_name} ({customer.phone_number})")
            return customer
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creando cliente: {e}")
            raise
    
    def get_or_create_customer(self, phone_number: str, full_name: str, 
                              email: Optional[str] = None, address: Optional[str] = None,
                              city: Optional[str] = None) -> Customer:
        """
        Obtener cliente existente o crear uno nuevo
        
        Args:
            phone_number: Número de teléfono
            full_name: Nombre completo
            email: Correo electrónico (opcional)
            address: Dirección (opcional)
            city: Ciudad (opcional)
            
        Returns:
            Customer: Cliente existente o nuevo
        """
        # Buscar cliente existente
        customer = self.get_customer_by_phone(phone_number)
        
        if customer:
            # Actualizar información si es necesario
            updated = False
            if customer.full_name != full_name:
                customer.full_name = full_name
                updated = True
            
            if email and customer.email != email:
                customer.email = email
                updated = True
            
            if address and customer.address != address:
                customer.address = address
                updated = True
            
            if city and customer.city != city:
                customer.city = city
                updated = True
            
            if updated:
                customer.updated_at = datetime.utcnow()
                self.db.commit()
                self.db.refresh(customer)
                logger.info(f"Cliente actualizado: {customer.full_name}")
            
            return customer
        
        # Crear nuevo cliente
        customer_data = CustomerCreate(
            phone_number=phone_number,
            full_name=full_name,
            email=email,
            address=address,
            city=city
        )
        
        return self.create_customer(customer_data)
    
    def get_customer_by_id(self, customer_id: int) -> Optional[Customer]:
        """Obtener cliente por ID"""
        return self.db.query(Customer).filter(Customer.id == customer_id).first()
    
    def get_customer_by_phone(self, phone_number: str) -> Optional[Customer]:
        """Obtener cliente por número de teléfono"""
        return self.db.query(Customer).filter(Customer.phone_number == phone_number).first()
    
    def update_customer(self, customer_id: int, update_data: CustomerUpdate) -> Optional[Customer]:
        """Actualizar cliente"""
        customer = self.get_customer_by_id(customer_id)
        
        if not customer:
            return None
        
        # Verificar si el nuevo teléfono ya existe
        if update_data.phone_number and update_data.phone_number != customer.phone_number:
            existing = self.get_customer_by_phone(update_data.phone_number)
            if existing:
                raise ValueError(f"Ya existe un cliente con el teléfono {update_data.phone_number}")
        
        # Actualizar campos
        for field, value in update_data.dict(exclude_unset=True).items():
            setattr(customer, field, value)
        
        customer.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(customer)
        
        logger.info(f"Cliente actualizado: {customer.full_name}")
        return customer
    
    def verify_customer(self, verification_data: CustomerVerification) -> bool:
        """
        Verificar cliente con código
        
        Args:
            verification_data: Datos de verificación
            
        Returns:
            bool: True si la verificación es exitosa
        """
        customer = self.get_customer_by_phone(verification_data.phone_number)
        
        if not customer:
            raise ValueError("Cliente no encontrado")
        
        if customer.verify_code(verification_data.verification_code):
            customer.is_verified = True
            customer.updated_at = datetime.utcnow()
            self.db.commit()
            
            logger.info(f"Cliente verificado: {customer.full_name}")
            return True
        
        return False
    
    def generate_verification_code(self, phone_number: str) -> str:
        """
        Generar código de verificación para cliente
        
        Args:
            phone_number: Número de teléfono del cliente
            
        Returns:
            str: Código de verificación generado
        """
        customer = self.get_customer_by_phone(phone_number)
        
        if not customer:
            raise ValueError("Cliente no encontrado")
        
        # Generar código
        code = customer.generate_verification_code()
        customer.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(customer)
        
        logger.info(f"Código de verificación generado para: {customer.full_name}")
        return code
    
    def search_customers(self, search_params: CustomerSearch) -> Dict[str, Any]:
        """
        Buscar clientes con filtros
        
        Args:
            search_params: Parámetros de búsqueda
            
        Returns:
            Dict con clientes y metadatos de paginación
        """
        query = self.db.query(Customer)
        
        # Aplicar filtros
        if search_params.query:
            search_term = f"%{search_params.query}%"
            query = query.filter(
                or_(
                    Customer.full_name.ilike(search_term),
                    Customer.phone_number.ilike(search_term),
                    Customer.email.ilike(search_term),
                    Customer.address.ilike(search_term),
                    Customer.city.ilike(search_term)
                )
            )
        
        if search_params.phone_number:
            query = query.filter(Customer.phone_number == search_params.phone_number)
        
        if search_params.city:
            query = query.filter(Customer.city == search_params.city)
        
        if search_params.is_verified is not None:
            query = query.filter(Customer.is_verified == search_params.is_verified)
        
        if search_params.is_active is not None:
            query = query.filter(Customer.is_active == search_params.is_active)
        
        # Contar total
        total = query.count()
        
        # Aplicar paginación
        offset = (search_params.page - 1) * search_params.per_page
        customers = query.offset(offset).limit(search_params.per_page).all()
        
        # Calcular páginas
        total_pages = (total + search_params.per_page - 1) // search_params.per_page
        
        return {
            "customers": customers,
            "total": total,
            "page": search_params.page,
            "per_page": search_params.per_page,
            "total_pages": total_pages
        }
    
    def get_customer_stats(self) -> CustomerStats:
        """Obtener estadísticas de clientes"""
        today = datetime.utcnow().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        # Totales
        total_customers = self.db.query(Customer).count()
        active_customers = self.db.query(Customer).filter(Customer.is_active == True).count()
        verified_customers = self.db.query(Customer).filter(Customer.is_verified == True).count()
        
        # Nuevos clientes
        new_customers_today = self.db.query(Customer).filter(
            func.date(Customer.created_at) == today
        ).count()
        
        new_customers_this_week = self.db.query(Customer).filter(
            Customer.created_at >= week_ago
        ).count()
        
        new_customers_this_month = self.db.query(Customer).filter(
            Customer.created_at >= month_ago
        ).count()
        
        # Clientes por ciudad
        customers_by_city = {}
        city_stats = self.db.query(
            Customer.city,
            func.count(Customer.id).label('count')
        ).filter(
            Customer.city.isnot(None)
        ).group_by(Customer.city).all()
        
        for city, count in city_stats:
            customers_by_city[city] = count
        
        # Promedio de paquetes por cliente
        avg_packages = self.db.query(
            func.avg(func.count(Package.id))
        ).select_from(Customer).outerjoin(Package).group_by(Customer.id).scalar() or 0
        
        # Ingresos totales
        total_revenue = self.db.query(
            func.sum(Package.total_cost)
        ).join(Customer).filter(
            Package.status == 'delivered'
        ).scalar() or 0
        
        return CustomerStats(
            total_customers=total_customers,
            active_customers=active_customers,
            verified_customers=verified_customers,
            new_customers_today=new_customers_today,
            new_customers_this_week=new_customers_this_week,
            new_customers_this_month=new_customers_this_month,
            customers_by_city=customers_by_city,
            average_packages_per_customer=float(avg_packages),
            total_revenue=float(total_revenue)
        )
    
    def get_customer_packages(self, customer_id: int, limit: int = 10) -> List[Package]:
        """Obtener paquetes de un cliente"""
        return self.db.query(Package).filter(
            Package.customer_id == customer_id
        ).order_by(desc(Package.created_at)).limit(limit).all()
    
    def get_customer_notifications(self, customer_id: int, limit: int = 10) -> List[Notification]:
        """Obtener notificaciones de un cliente"""
        return self.db.query(Notification).filter(
            Notification.customer_id == customer_id
        ).order_by(desc(Notification.created_at)).limit(limit).all()
    
    def deactivate_customer(self, customer_id: int) -> bool:
        """Desactivar cliente"""
        customer = self.get_customer_by_id(customer_id)
        
        if not customer:
            return False
        
        customer.is_active = False
        customer.updated_at = datetime.utcnow()
        
        self.db.commit()
        
        logger.info(f"Cliente desactivado: {customer.full_name}")
        return True
    
    def activate_customer(self, customer_id: int) -> bool:
        """Activar cliente"""
        customer = self.get_customer_by_id(customer_id)
        
        if not customer:
            return False
        
        customer.is_active = True
        customer.updated_at = datetime.utcnow()
        
        self.db.commit()
        
        logger.info(f"Cliente activado: {customer.full_name}")
        return True
    
    def delete_customer(self, customer_id: int) -> bool:
        """Eliminar cliente (soft delete)"""
        customer = self.get_customer_by_id(customer_id)
        
        if not customer:
            return False
        
        # Verificar si tiene paquetes activos
        active_packages = self.db.query(Package).filter(
            and_(
                Package.customer_id == customer_id,
                Package.status.in_(['announced', 'received'])
            )
        ).count()
        
        if active_packages > 0:
            raise ValueError(f"No se puede eliminar el cliente. Tiene {active_packages} paquetes activos")
        
        customer.is_active = False
        customer.updated_at = datetime.utcnow()
        
        self.db.commit()
        
        logger.info(f"Cliente eliminado: {customer.full_name}")
        return True
    
    def export_customers(self, export_params: CustomerExport) -> Dict[str, Any]:
        """
        Exportar clientes
        
        Args:
            export_params: Parámetros de exportación
            
        Returns:
            Dict con datos exportados
        """
        query = self.db.query(Customer)
        
        # Aplicar filtros de fecha
        if export_params.date_from:
            query = query.filter(Customer.created_at >= export_params.date_from)
        
        if export_params.date_to:
            query = query.filter(Customer.created_at <= export_params.date_to)
        
        customers = query.all()
        
        # Preparar datos para exportación
        export_data = []
        for customer in customers:
            customer_data = {
                'id': customer.id,
                'phone_number': customer.phone_number,
                'full_name': customer.full_name,
                'email': customer.email,
                'address': customer.address,
                'city': customer.city,
                'is_verified': customer.is_verified,
                'is_active': customer.is_active,
                'created_at': customer.created_at.isoformat(),
                'updated_at': customer.updated_at.isoformat(),
                'last_activity': customer.last_activity.isoformat() if customer.last_activity else None
            }
            
            # Incluir información de paquetes si se solicita
            if export_params.include_packages:
                packages = self.get_customer_packages(customer.id, limit=100)
                customer_data['packages'] = [
                    {
                        'tracking_number': p.tracking_number,
                        'description': p.description,
                        'status': p.status.value,
                        'total_cost': float(p.total_cost),
                        'announced_at': p.announced_at.isoformat() if p.announced_at else None
                    }
                    for p in packages
                ]
            
            export_data.append(customer_data)
        
        return {
            'format': export_params.format,
            'total_customers': len(export_data),
            'data': export_data,
            'exported_at': datetime.utcnow().isoformat()
        }
    
    def update_customer_activity(self, customer_id: int) -> None:
        """Actualizar última actividad del cliente"""
        customer = self.get_customer_by_id(customer_id)
        
        if customer:
            customer.last_activity = datetime.utcnow()
            self.db.commit()
    
    def get_inactive_customers(self, days_inactive: int = 30) -> List[Customer]:
        """Obtener clientes inactivos"""
        inactive_date = datetime.utcnow() - timedelta(days=days_inactive)
        
        return self.db.query(Customer).filter(
            and_(
                Customer.is_active == True,
                or_(
                    Customer.last_activity.is_(None),
                    Customer.last_activity < inactive_date
                )
            )
        ).all()
    
    def get_top_customers(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Obtener clientes con más paquetes"""
        return self.db.query(
            Customer,
            func.count(Package.id).label('package_count'),
            func.sum(Package.total_cost).label('total_spent')
        ).outerjoin(Package).group_by(Customer.id).order_by(
            desc('package_count')
        ).limit(limit).all()
