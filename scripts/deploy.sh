#!/bin/bash

# =============================================================================
# SCRIPT DE DESPLIEGUE - Sistema de Paquetería v1.1
# =============================================================================

set -e  # Salir en caso de error

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para logging
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

# Variables de configuración
PROJECT_NAME="paqueteria"
DOCKER_COMPOSE_FILE="docker-compose.yml"
ENV_FILE=".env.production"
BACKUP_DIR="/backups"
LOG_DIR="/logs"

# Función para verificar dependencias
check_dependencies() {
    log "Verificando dependencias..."
    
    # Verificar Docker
    if ! command -v docker &> /dev/null; then
        error "Docker no está instalado"
    fi
    
    # Verificar Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose no está instalado"
    fi
    
    # Verificar archivo de variables de entorno
    if [ ! -f "$ENV_FILE" ]; then
        error "Archivo $ENV_FILE no encontrado"
    fi
    
    log "Dependencias verificadas correctamente"
}

# Función para crear backup
create_backup() {
    log "Creando backup de la base de datos..."
    
    BACKUP_FILE="$BACKUP_DIR/backup_$(date +%Y%m%d_%H%M%S).sql"
    
    # Crear directorio de backup si no existe
    mkdir -p "$BACKUP_DIR"
    
    # Crear backup de MySQL
    docker-compose exec -T mysql mysqldump -u root -p"$MYSQL_ROOT_PASSWORD" \
        --single-transaction --routines --triggers paqueteria > "$BACKUP_FILE"
    
    if [ $? -eq 0 ]; then
        log "Backup creado: $BACKUP_FILE"
    else
        warn "No se pudo crear el backup"
    fi
}

# Función para detener servicios
stop_services() {
    log "Deteniendo servicios..."
    docker-compose down
    log "Servicios detenidos"
}

# Función para limpiar recursos no utilizados
cleanup() {
    log "Limpiando recursos no utilizados..."
    
    # Eliminar contenedores huérfanos
    docker container prune -f
    
    # Eliminar imágenes no utilizadas
    docker image prune -f
    
    # Eliminar volúmenes no utilizados
    docker volume prune -f
    
    # Eliminar redes no utilizadas
    docker network prune -f
    
    log "Limpieza completada"
}

# Función para construir imágenes
build_images() {
    log "Construyendo imágenes Docker..."
    docker-compose build --no-cache
    log "Imágenes construidas correctamente"
}

# Función para iniciar servicios
start_services() {
    log "Iniciando servicios..."
    docker-compose up -d
    
    # Esperar a que los servicios estén listos
    log "Esperando a que los servicios estén listos..."
    sleep 30
    
    # Verificar health checks
    check_health
}

# Función para verificar health checks
check_health() {
    log "Verificando health checks..."
    
    # Verificar FastAPI
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        log "FastAPI: OK"
    else
        error "FastAPI health check falló"
    fi
    
    # Verificar MySQL
    if docker-compose exec mysql mysqladmin ping -h localhost -u root -p"$MYSQL_ROOT_PASSWORD" > /dev/null 2>&1; then
        log "MySQL: OK"
    else
        error "MySQL health check falló"
    fi
    
    # Verificar Nginx
    if curl -f http://localhost:80 > /dev/null 2>&1; then
        log "Nginx: OK"
    else
        error "Nginx health check falló"
    fi
    
    log "Todos los health checks pasaron"
}

# Función para ejecutar migraciones
run_migrations() {
    log "Ejecutando migraciones de base de datos..."
    
    # Ejecutar migraciones con Alembic
    docker-compose exec fastapi alembic upgrade head
    
    if [ $? -eq 0 ]; then
        log "Migraciones ejecutadas correctamente"
    else
        error "Error ejecutando migraciones"
    fi
}

# Función para verificar logs
check_logs() {
    log "Verificando logs de servicios..."
    
    # Mostrar logs de los últimos 10 minutos
    docker-compose logs --since=10m
}

# Función para mostrar estado de servicios
show_status() {
    log "Estado de servicios:"
    docker-compose ps
    
    log "Uso de recursos:"
    docker stats --no-stream
}

# Función para configurar SSL
setup_ssl() {
    log "Configurando SSL con Let's Encrypt..."
    
    # Verificar si certbot está disponible
    if ! command -v certbot &> /dev/null; then
        warn "Certbot no está instalado. Instalando..."
        apt-get update && apt-get install -y certbot python3-certbot-nginx
    fi
    
    # Obtener certificado SSL
    certbot --nginx -d your-domain.com -d www.your-domain.com --non-interactive --agree-tos --email your-email@example.com
    
    # Configurar renovación automática
    (crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet") | crontab -
    
    log "SSL configurado correctamente"
}

# Función para configurar firewall
setup_firewall() {
    log "Configurando firewall..."
    
    # Permitir SSH
    ufw allow ssh
    
    # Permitir HTTP
    ufw allow 80
    
    # Permitir HTTPS
    ufw allow 443
    
    # Habilitar firewall
    ufw --force enable
    
    log "Firewall configurado correctamente"
}

# Función para configurar monitoreo
setup_monitoring() {
    log "Configurando monitoreo básico..."
    
    # Crear script de monitoreo
    cat > /usr/local/bin/monitor.sh << 'EOF'
#!/bin/bash
# Script de monitoreo básico

# Verificar servicios
if ! docker-compose ps | grep -q "Up"; then
    echo "ERROR: Servicios no están ejecutándose"
    exit 1
fi

# Verificar espacio en disco
DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 80 ]; then
    echo "WARNING: Uso de disco alto: ${DISK_USAGE}%"
fi

# Verificar memoria
MEMORY_USAGE=$(free | awk 'NR==2{printf "%.2f", $3*100/$2}')
if (( $(echo "$MEMORY_USAGE > 80" | bc -l) )); then
    echo "WARNING: Uso de memoria alto: ${MEMORY_USAGE}%"
fi

echo "OK: Sistema funcionando correctamente"
EOF
    
    chmod +x /usr/local/bin/monitor.sh
    
    # Agregar al crontab
    (crontab -l 2>/dev/null; echo "*/5 * * * * /usr/local/bin/monitor.sh") | crontab -
    
    log "Monitoreo configurado correctamente"
}

# Función principal de despliegue
main() {
    log "Iniciando despliegue de $PROJECT_NAME..."
    
    # Cargar variables de entorno
    source "$ENV_FILE"
    
    # Verificar dependencias
    check_dependencies
    
    # Crear backup
    create_backup
    
    # Detener servicios
    stop_services
    
    # Limpiar recursos
    cleanup
    
    # Construir imágenes
    build_images
    
    # Iniciar servicios
    start_services
    
    # Ejecutar migraciones
    run_migrations
    
    # Verificar logs
    check_logs
    
    # Mostrar estado
    show_status
    
    log "Despliegue completado exitosamente!"
}

# Función de ayuda
show_help() {
    echo "Uso: $0 [OPCIÓN]"
    echo ""
    echo "Opciones:"
    echo "  deploy      Realizar despliegue completo"
    echo "  backup      Crear backup de la base de datos"
    echo "  stop        Detener servicios"
    echo "  start       Iniciar servicios"
    echo "  restart     Reiniciar servicios"
    echo "  logs        Mostrar logs"
    echo "  status      Mostrar estado de servicios"
    echo "  ssl         Configurar SSL"
    echo "  firewall    Configurar firewall"
    echo "  monitor     Configurar monitoreo"
    echo "  help        Mostrar esta ayuda"
    echo ""
}

# Procesar argumentos
case "${1:-deploy}" in
    deploy)
        main
        ;;
    backup)
        source "$ENV_FILE"
        create_backup
        ;;
    stop)
        stop_services
        ;;
    start)
        source "$ENV_FILE"
        start_services
        ;;
    restart)
        source "$ENV_FILE"
        stop_services
        start_services
        ;;
    logs)
        check_logs
        ;;
    status)
        show_status
        ;;
    ssl)
        setup_ssl
        ;;
    firewall)
        setup_firewall
        ;;
    monitor)
        setup_monitoring
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        error "Opción desconocida: $1"
        show_help
        ;;
esac
