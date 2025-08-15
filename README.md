# 🚀 Sistema de Gestión de Paquetería v1.1

## 📋 Información del Proyecto

| Campo | Valor |
|-------|-------|
| **Autor** | Jesús María Villalobos |
| **Email** | jveyes@gmail.com |
| **Repositorio** | [https://github.com/jveyes/paqueteria.git](https://github.com/jveyes/paqueteria.git) |
| **Versión** | 1.0.0 |
| **Estado** | En Desarrollo |
| **Licencia** | MIT |

## 🎯 Descripción

El **Sistema de Gestión de Paquetería v1.1** es una plataforma digital moderna que simplifica y automatiza todo el proceso de gestión de paquetes para edificios, conjuntos residenciales y empresas. Es como tener un "conserje digital" que maneja todos tus paquetes de forma inteligente y eficiente.

**Sitio Web:** [paquetes.papyrus.com.co](https://paquetes.papyrus.com.co)

## 🏗️ Stack Tecnológico

### Backend
- **Framework:** FastAPI (Python 3.11+)
- **Servidor:** Uvicorn ASGI
- **ORM:** SQLAlchemy 2.0.23
- **Base de Datos:** MySQL 8.0
- **Autenticación:** JWT con python-jose
- **Validación:** Pydantic models

### Frontend
- **CSS Framework:** Tailwind CSS 3.x
- **Interactividad:** HTMX 1.x
- **JavaScript:** Alpine.js 3.x
- **Templates:** Jinja2

### Infraestructura
- **Contenedores:** Docker + Docker Compose
- **Proxy:** Nginx
- **Nube:** AWS Lightsail
- **Almacenamiento:** AWS S3
- **SMS:** LIWA API (Colombia)

## 📁 Estructura del Proyecto

```
paqueteria/
├── docker-compose.yml          # Configuración de contenedores
├── Dockerfile                  # Imagen de FastAPI
├── requirements.txt            # Dependencias Python
├── .env.example               # Variables de entorno
├── src/                       # Código fuente
│   ├── main.py               # Aplicación principal FastAPI
│   ├── app/                  # Módulos de la aplicación
│   │   ├── models/          # Modelos SQLAlchemy
│   │   ├── schemas/         # Esquemas Pydantic
│   │   ├── routes/          # Rutas de la API
│   │   ├── services/        # Servicios externos
│   │   └── utils/           # Utilidades
│   ├── static/              # Archivos estáticos
│   └── templates/           # Templates HTML
├── scripts/                  # Scripts de inicialización
├── nginx/                    # Configuración Nginx
└── volumes/                  # Volúmenes persistentes
```

## 🚀 Instalación y Configuración

### Prerrequisitos

- Python 3.11+
- Docker y Docker Compose
- MySQL 8.0 (o usar Docker)
- Git

### Configuración Local

1. **Clonar el repositorio:**
```bash
git clone https://github.com/jveyes/paqueteria.git
cd paqueteria
```

2. **Configurar variables de entorno:**
```bash
cp .env.example .env
# Editar .env con tus credenciales
```

3. **Instalar dependencias:**
```bash
pip install -r requirements.txt
```

4. **Configurar base de datos:**
```bash
# Crear base de datos MySQL
mysql -u root -p
CREATE DATABASE paqueteria CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

5. **Ejecutar migraciones:**
```bash
alembic upgrade head
```

6. **Iniciar la aplicación:**
```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### Configuración con Docker

1. **Construir y ejecutar contenedores:**
```bash
docker-compose up -d --build
```

2. **Verificar estado:**
```bash
docker-compose ps
docker-compose logs -f
```

## 🔧 Variables de Entorno

Crear un archivo `.env` con las siguientes variables:

```bash
# Database
DATABASE_URL=mysql+pymysql://user:pass@localhost:3306/paqueteria

# LIWA SMS
LIWA_API_KEY=your_liwa_api_key
LIWA_API_URL=https://api.liwa.co/sms

# AWS S3
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
AWS_REGION=us-east-1
S3_BUCKET_NAME=paqueteria-files

# Application
SECRET_KEY=your_secret_key
DEBUG=False
HOST=0.0.0.0
PORT=8000

# File Upload
MAX_FILE_SIZE=10485760
ALLOWED_EXTENSIONS=jpg,jpeg,png,pdf
```

## 📊 Modelo de Negocio

### Estructura de Costos
- **Paquete Normal:** $1,500 COP
- **Paquete Extra dimensionado:** $2,000 COP
- **Bodegaje:** $1,000 COP/día (con 24h de gracia)

### Estados de Paquete
- `announced` - Anunciado por cliente
- `received` - Recibido en instalaciones
- `delivered` - Entregado al cliente

### Tipos de Paquete
- `normal` - Paquete estándar
- `extra_dimensioned` - Paquete extra dimensionado

## 🎯 Funcionalidades Principales

### 1. Anuncio de Paquetes (Cliente)
- Formulario público para anunciar llegada de paquetes
- Generación automática de códigos únicos
- Envío de SMS de confirmación

### 2. Recepción de Paquetes (Administrativo)
- Verificación de paquetes anunciados
- Registro de recepción con fotos
- Notificación automática al cliente

### 3. Actualización de Datos (Cliente)
- Autenticación con código único
- Actualización de información de entrega
- Bloqueo post-entrega

### 4. Entrega y Cobro (Administrativo)
- Cálculo automático de costos
- Registro de entrega
- Cierre de transacciones

## 🧪 Testing

### Ejecutar pruebas unitarias:
```bash
pytest tests/ -v
```

### Ejecutar pruebas de integración:
```bash
pytest tests/integration/ -v
```

### Cobertura de código:
```bash
pytest --cov=src tests/
```

## 🚀 Despliegue

### Despliegue en AWS Lightsail

1. **Configurar instancia:**
```bash
# Conectar a la instancia
ssh ubuntu@tu-instancia-ip

# Clonar repositorio
git clone https://github.com/jveyes/paqueteria.git
cd paqueteria
```

2. **Configurar variables de producción:**
```bash
cp .env.example .env
# Editar con credenciales de producción
```

3. **Desplegar con Docker:**
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### URLs de Acceso
- **Aplicación:** https://tu-dominio.com
- **API Documentation:** https://tu-dominio.com/docs
- **Health Check:** https://tu-dominio.com/health

## 📝 API Documentation

La documentación automática de la API está disponible en:
- **Swagger UI:** `/docs`
- **ReDoc:** `/redoc`

### Endpoints Principales

#### Paquetes
- `POST /api/v1/packages/announce` - Anunciar paquete
- `GET /api/v1/packages/{tracking_number}` - Obtener paquete
- `PUT /api/v1/packages/{tracking_number}/receive` - Registrar recepción
- `PUT /api/v1/packages/{tracking_number}/deliver` - Registrar entrega

#### Notificaciones
- `POST /api/v1/notifications/sms` - Enviar SMS
- `GET /api/v1/notifications/history` - Historial de notificaciones

#### Archivos
- `POST /api/v1/files/upload` - Subir archivo
- `GET /api/v1/files/{file_id}` - Obtener archivo

## 🔒 Seguridad

- **Autenticación:** JWT tokens
- **Validación:** Pydantic models
- **Rate Limiting:** Implementado con Nginx
- **HTTPS:** SSL/TLS en producción
- **Sanitización:** Validación de archivos y inputs

## 📊 Monitoreo

### Logs
- **Aplicación:** `/var/log/paqueteria/app.log`
- **Nginx:** `/var/log/nginx/`
- **Docker:** `docker-compose logs -f`

### Métricas
- **Health Check:** `/health`
- **Prometheus:** `/metrics` (futuro)

## 🤝 Contribución

1. Fork el proyecto
2. Crear una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abrir un Pull Request

### Estándares de Código
- Seguir PEP 8 para Python
- Usar type hints
- Documentar funciones con docstrings
- Escribir pruebas para nuevas funcionalidades

## 📄 Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para detalles.

## 📞 Contacto

- **Autor:** Jesús María Villalobos
- **Email:** jveyes@gmail.com
- **Repositorio:** [https://github.com/jveyes/paqueteria.git](https://github.com/jveyes/paqueteria.git)
- **Sitio Web:** [paquetes.papyrus.com.co](https://paquetes.papyrus.com.co)

## 🙏 Agradecimientos

- FastAPI por el excelente framework
- Tailwind CSS por el sistema de diseño
- HTMX por la interactividad sin JavaScript complejo
- LIWA por el servicio SMS en Colombia
- AWS por la infraestructura en la nube

---

**Desarrollado con ❤️ por Jesús María Villalobos**
