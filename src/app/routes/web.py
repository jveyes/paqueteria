"""
Web Routes
=========

Rutas web para la interfaz de usuario con HTMX.
"""

from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Form, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.auth import get_current_active_user, get_current_user
from ..models.user import User
from ..services.package_service import PackageService
from ..services.customer_service import CustomerService
from ..services.notification_service import NotificationService
from ..schemas.package import PackageAnnounce, PackageReceive
from ..core.config import settings

router = APIRouter(tags=["Web Interface"])

# Configurar templates
templates = Jinja2Templates(directory="src/templates")

@router.get("/", response_class=HTMLResponse)
async def home_page(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Página principal
    
    Args:
        request: Request de FastAPI
        current_user: Usuario actual (opcional)
        db: Sesión de base de datos
        
    Returns:
        HTMLResponse: Página principal
    """
    # Obtener estadísticas básicas
    package_service = PackageService(db)
    stats = package_service.get_package_stats()
    
    return templates.TemplateResponse(
        "pages/home.html",
        {
            "request": request,
            "current_user": current_user,
            "stats": stats
        }
    )

@router.get("/announce", response_class=HTMLResponse)
async def announce_page(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Página para anunciar paquetes
    
    Args:
        request: Request de FastAPI
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        HTMLResponse: Página de anuncio
    """
    return templates.TemplateResponse(
        "pages/announce.html",
        {
            "request": request,
            "current_user": current_user
        }
    )

@router.post("/packages/announce", response_class=HTMLResponse)
async def announce_package_web(
    request: Request,
    customer_phone: str = Form(...),
    customer_name: str = Form(...),
    customer_email: Optional[str] = Form(None),
    customer_address: Optional[str] = Form(None),
    customer_city: Optional[str] = Form(None),
    description: str = Form(...),
    package_type: str = Form(...),
    weight_kg: Optional[float] = Form(None),
    length_cm: Optional[float] = Form(None),
    width_cm: Optional[float] = Form(None),
    height_cm: Optional[float] = Form(None),
    is_urgent: bool = Form(False),
    customer_notes: Optional[str] = Form(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Anunciar paquete desde la interfaz web
    
    Args:
        request: Request de FastAPI
        customer_phone: Teléfono del cliente
        customer_name: Nombre del cliente
        customer_email: Email del cliente
        customer_address: Dirección del cliente
        customer_city: Ciudad del cliente
        description: Descripción del paquete
        package_type: Tipo de paquete
        weight_kg: Peso en kg
        length_cm: Largo en cm
        width_cm: Ancho en cm
        height_cm: Alto en cm
        is_urgent: Si es urgente
        customer_notes: Notas adicionales
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        HTMLResponse: Resultado del anuncio
    """
    try:
        # Crear datos del paquete
        package_data = PackageAnnounce(
            customer_phone=customer_phone,
            customer_name=customer_name,
            customer_email=customer_email,
            customer_address=customer_address,
            customer_city=customer_city,
            description=description,
            package_type=package_type,
            weight_kg=weight_kg,
            length_cm=length_cm,
            width_cm=width_cm,
            height_cm=height_cm,
            is_urgent=is_urgent,
            customer_notes=customer_notes
        )
        
        # Anunciar paquete
        package_service = PackageService(db)
        package = package_service.announce_package(package_data)
        
        # Retornar respuesta de éxito
        return templates.TemplateResponse(
            "components/success_modal.html",
            {
                "request": request,
                "tracking_number": package.tracking_number,
                "customer_name": package.customer.full_name,
                "package_cost": package.formatted_cost
            }
        )
        
    except Exception as e:
        # Retornar error
        return templates.TemplateResponse(
            "components/error_message.html",
            {
                "request": request,
                "error_message": str(e)
            }
        )

@router.get("/receive", response_class=HTMLResponse)
async def receive_page(
    request: Request,
    page: int = Query(1, ge=1),
    search: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None),
    type_filter: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Página para recibir paquetes
    
    Args:
        request: Request de FastAPI
        page: Número de página
        search: Término de búsqueda
        status_filter: Filtro por estado
        type_filter: Filtro por tipo
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        HTMLResponse: Página de recepción
    """
    # Obtener estadísticas
    package_service = PackageService(db)
    stats = package_service.get_package_stats()
    
    # Obtener paquetes
    from ..schemas.package import PackageSearch
    search_params = PackageSearch(
        query=search,
        status=status_filter,
        package_type=type_filter,
        page=page,
        per_page=20
    )
    
    result = package_service.search_packages(search_params)
    
    return templates.TemplateResponse(
        "pages/receive.html",
        {
            "request": request,
            "current_user": current_user,
            "stats": stats,
            "packages": result["packages"],
            "total": result["total"],
            "page": result["page"],
            "total_pages": result["total_pages"],
            "search_query": search,
            "status_filter": status_filter,
            "type_filter": type_filter
        }
    )

@router.post("/packages/{tracking_number}/receive", response_class=HTMLResponse)
async def receive_package_web(
    request: Request,
    tracking_number: str,
    notes: Optional[str] = Form(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Recibir paquete desde la interfaz web
    
    Args:
        request: Request de FastAPI
        tracking_number: Número de tracking
        notes: Notas de recepción
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        HTMLResponse: Resultado de la recepción
    """
    try:
        package_service = PackageService(db)
        package = package_service.receive_package(tracking_number, notes)
        
        return templates.TemplateResponse(
            "components/success_message.html",
            {
                "request": request,
                "message": f"Paquete {tracking_number} recibido exitosamente",
                "package": package
            }
        )
        
    except Exception as e:
        return templates.TemplateResponse(
            "components/error_message.html",
            {
                "request": request,
                "error_message": str(e)
            }
        )

@router.get("/deliver", response_class=HTMLResponse)
async def deliver_page(
    request: Request,
    page: int = Query(1, ge=1),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Página para entregar paquetes
    
    Args:
        request: Request de FastAPI
        page: Número de página
        search: Término de búsqueda
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        HTMLResponse: Página de entrega
    """
    # Obtener paquetes recibidos
    package_service = PackageService(db)
    from ..schemas.package import PackageSearch
    
    search_params = PackageSearch(
        query=search,
        status="received",
        page=page,
        per_page=20
    )
    
    result = package_service.search_packages(search_params)
    
    return templates.TemplateResponse(
        "pages/deliver.html",
        {
            "request": request,
            "current_user": current_user,
            "packages": result["packages"],
            "total": result["total"],
            "page": result["page"],
            "total_pages": result["total_pages"],
            "search_query": search
        }
    )

@router.post("/packages/{tracking_number}/deliver", response_class=HTMLResponse)
async def deliver_package_web(
    request: Request,
    tracking_number: str,
    recipient_name: str = Form(...),
    payment_method: str = Form(...),
    amount_paid: float = Form(...),
    notes: Optional[str] = Form(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Entregar paquete desde la interfaz web
    
    Args:
        request: Request de FastAPI
        tracking_number: Número de tracking
        recipient_name: Nombre del destinatario
        payment_method: Método de pago
        amount_paid: Monto pagado
        notes: Notas de entrega
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        HTMLResponse: Resultado de la entrega
    """
    try:
        delivery_data = {
            "recipient_name": recipient_name,
            "payment_method": payment_method,
            "amount_paid": amount_paid,
            "notes": notes
        }
        
        package_service = PackageService(db)
        delivery = package_service.deliver_package(tracking_number, delivery_data)
        
        return templates.TemplateResponse(
            "components/success_message.html",
            {
                "request": request,
                "message": f"Paquete {tracking_number} entregado exitosamente",
                "delivery_number": delivery.delivery_number
            }
        )
        
    except Exception as e:
        return templates.TemplateResponse(
            "components/error_message.html",
            {
                "request": request,
                "error_message": str(e)
            }
        )

@router.get("/tracking/{tracking_number}", response_class=HTMLResponse)
async def track_package_web(
    request: Request,
    tracking_number: str,
    db: Session = Depends(get_db)
) -> Any:
    """
    Página de seguimiento de paquete (pública)
    
    Args:
        request: Request de FastAPI
        tracking_number: Número de tracking
        db: Sesión de base de datos
        
    Returns:
        HTMLResponse: Página de seguimiento
    """
    try:
        package_service = PackageService(db)
        tracking_info = package_service.get_package_tracking(tracking_number)
        
        if not tracking_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Paquete no encontrado"
            )
        
        return templates.TemplateResponse(
            "pages/tracking.html",
            {
                "request": request,
                "tracking_info": tracking_info
            }
        )
        
    except Exception as e:
        return templates.TemplateResponse(
            "pages/error.html",
            {
                "request": request,
                "error_message": str(e)
            }
        )

@router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Dashboard administrativo
    
    Args:
        request: Request de FastAPI
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        HTMLResponse: Dashboard administrativo
    """
    # Verificar permisos de administrador
    if not current_user.is_superuser and current_user.role not in ["admin", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado"
        )
    
    # Obtener estadísticas
    package_service = PackageService(db)
    customer_service = CustomerService(db)
    notification_service = NotificationService(db)
    
    package_stats = package_service.get_package_stats()
    customer_stats = customer_service.get_customer_stats()
    notification_stats = notification_service.get_notification_stats()
    
    return templates.TemplateResponse(
        "pages/admin/dashboard.html",
        {
            "request": request,
            "current_user": current_user,
            "package_stats": package_stats,
            "customer_stats": customer_stats,
            "notification_stats": notification_stats
        }
    )

@router.get("/admin/packages", response_class=HTMLResponse)
async def admin_packages(
    request: Request,
    page: int = Query(1, ge=1),
    search: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Gestión de paquetes (admin)
    
    Args:
        request: Request de FastAPI
        page: Número de página
        search: Término de búsqueda
        status_filter: Filtro por estado
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        HTMLResponse: Página de gestión de paquetes
    """
    if not current_user.is_superuser and current_user.role not in ["admin", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado"
        )
    
    package_service = PackageService(db)
    from ..schemas.package import PackageSearch
    
    search_params = PackageSearch(
        query=search,
        status=status_filter,
        page=page,
        per_page=50
    )
    
    result = package_service.search_packages(search_params)
    
    return templates.TemplateResponse(
        "pages/admin/packages.html",
        {
            "request": request,
            "current_user": current_user,
            "packages": result["packages"],
            "total": result["total"],
            "page": result["page"],
            "total_pages": result["total_pages"],
            "search_query": search,
            "status_filter": status_filter
        }
    )

@router.get("/admin/customers", response_class=HTMLResponse)
async def admin_customers(
    request: Request,
    page: int = Query(1, ge=1),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Gestión de clientes (admin)
    
    Args:
        request: Request de FastAPI
        page: Número de página
        search: Término de búsqueda
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        HTMLResponse: Página de gestión de clientes
    """
    if not current_user.is_superuser and current_user.role not in ["admin", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado"
        )
    
    customer_service = CustomerService(db)
    from ..schemas.customer import CustomerSearch
    
    search_params = CustomerSearch(
        query=search,
        page=page,
        per_page=50
    )
    
    result = customer_service.search_customers(search_params)
    
    return templates.TemplateResponse(
        "pages/admin/customers.html",
        {
            "request": request,
            "current_user": current_user,
            "customers": result["customers"],
            "total": result["total"],
            "page": result["page"],
            "total_pages": result["total_pages"],
            "search_query": search
        }
    )

@router.get("/admin/notifications", response_class=HTMLResponse)
async def admin_notifications(
    request: Request,
    page: int = Query(1, ge=1),
    notification_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Gestión de notificaciones (admin)
    
    Args:
        request: Request de FastAPI
        page: Número de página
        notification_type: Tipo de notificación
        status: Estado de la notificación
        current_user: Usuario actual
        db: Sesión de base de datos
        
    Returns:
        HTMLResponse: Página de gestión de notificaciones
    """
    if not current_user.is_superuser and current_user.role not in ["admin", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado"
        )
    
    notification_service = NotificationService(db)
    from ..schemas.notification import NotificationSearch
    
    search_params = NotificationSearch(
        notification_type=notification_type,
        status=status,
        page=page,
        per_page=50
    )
    
    result = notification_service.search_notifications(search_params)
    
    return templates.TemplateResponse(
        "pages/admin/notifications.html",
        {
            "request": request,
            "current_user": current_user,
            "notifications": result["notifications"],
            "total": result["total"],
            "page": result["page"],
            "total_pages": result["total_pages"],
            "notification_type": notification_type,
            "status": status
        }
    )

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request) -> Any:
    """
    Página de inicio de sesión
    
    Args:
        request: Request de FastAPI
        
    Returns:
        HTMLResponse: Página de login
    """
    return templates.TemplateResponse(
        "pages/login.html",
        {"request": request}
    )

@router.get("/profile", response_class=HTMLResponse)
async def profile_page(
    request: Request,
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Página de perfil de usuario
    
    Args:
        request: Request de FastAPI
        current_user: Usuario actual
        
    Returns:
        HTMLResponse: Página de perfil
    """
    return templates.TemplateResponse(
        "pages/profile.html",
        {
            "request": request,
            "current_user": current_user
        }
    )

@router.get("/help", response_class=HTMLResponse)
async def help_page(request: Request) -> Any:
    """
    Página de ayuda
    
    Args:
        request: Request de FastAPI
        
    Returns:
        HTMLResponse: Página de ayuda
    """
    return templates.TemplateResponse(
        "pages/help.html",
        {"request": request}
    )

@router.get("/contact", response_class=HTMLResponse)
async def contact_page(request: Request) -> Any:
    """
    Página de contacto
    
    Args:
        request: Request de FastAPI
        
    Returns:
        HTMLResponse: Página de contacto
    """
    return templates.TemplateResponse(
        "pages/contact.html",
        {"request": request}
    )
