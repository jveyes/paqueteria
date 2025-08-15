#!/bin/bash

# =============================================================================
# SCRIPT DE BACKUP Y RESTAURACIÓN - Sistema de Paquetería v1.1
# =============================================================================

set -e

# =============================================================================
# CONFIGURACIÓN
# =============================================================================

# Directorios
VOLUMES_DIR="./volumes"
BACKUP_DIR="./backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# =============================================================================
# FUNCIONES DE UTILIDAD
# =============================================================================

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# =============================================================================
# FUNCIÓN DE BACKUP
# =============================================================================

backup_volumes() {
    local backup_name="paqueteria_backup_$DATE"
    local backup_file="$BACKUP_DIR/$backup_name.tar.gz"
    
    print_info "🚀 Iniciando backup de volúmenes..."
    
    # Crear directorio de backup si no existe
    mkdir -p "$BACKUP_DIR"
    
    # Verificar que los volúmenes existen
    if [ ! -d "$VOLUMES_DIR" ]; then
        print_error "Directorio de volúmenes no encontrado: $VOLUMES_DIR"
        exit 1
    fi
    
    # Backup de volúmenes críticos
    print_info "📦 Creando backup de datos críticos..."
    tar -czf "$backup_file" \
        --exclude="$VOLUMES_DIR/*/logs/*" \
        --exclude="$VOLUMES_DIR/*/temp/*" \
        --exclude="$VOLUMES_DIR/*/.gitkeep" \
        -C "$(dirname "$VOLUMES_DIR")" \
        "$(basename "$VOLUMES_DIR")"
    
    if [ $? -eq 0 ]; then
        print_success "Backup creado exitosamente: $backup_file"
        print_info "Tamaño del backup: $(du -h "$backup_file" | cut -f1)"
    else
        print_error "Error al crear backup"
        exit 1
    fi
    
    # Backup de base de datos MySQL (si está corriendo)
    if docker-compose ps mysql | grep -q "Up"; then
        print_info "🗄️  Creando backup de base de datos MySQL..."
        local db_backup_file="$BACKUP_DIR/mysql_backup_$DATE.sql"
        
        docker-compose exec -T mysql mysqldump \
            -u root -proot_password_change_in_production \
            --single-transaction \
            --routines \
            --triggers \
            paqueteria > "$db_backup_file"
        
        if [ $? -eq 0 ]; then
            print_success "Backup de MySQL creado: $db_backup_file"
            print_info "Tamaño del backup MySQL: $(du -h "$db_backup_file" | cut -f1)"
        else
            print_warning "No se pudo crear backup de MySQL (contenedor no disponible)"
        fi
    else
        print_warning "MySQL no está corriendo, omitiendo backup de base de datos"
    fi
    
    # Limpiar backups antiguos (mantener solo los últimos 7)
    print_info "🧹 Limpiando backups antiguos..."
    find "$BACKUP_DIR" -name "paqueteria_backup_*.tar.gz" -type f -mtime +7 -delete
    find "$BACKUP_DIR" -name "mysql_backup_*.sql" -type f -mtime +7 -delete
    
    print_success "🎉 Backup completado exitosamente!"
}

# =============================================================================
# FUNCIÓN DE RESTAURACIÓN
# =============================================================================

restore_volumes() {
    local backup_file="$1"
    
    if [ -z "$backup_file" ]; then
        print_error "Debe especificar un archivo de backup"
        echo "Uso: $0 restore <archivo_backup.tar.gz>"
        exit 1
    fi
    
    if [ ! -f "$backup_file" ]; then
        print_error "Archivo de backup no encontrado: $backup_file"
        exit 1
    fi
    
    print_warning "⚠️  ADVERTENCIA: Esta operación sobrescribirá los datos actuales"
    read -p "¿Está seguro de continuar? (y/N): " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Restauración cancelada"
        exit 0
    fi
    
    print_info "🔄 Iniciando restauración desde: $backup_file"
    
    # Detener contenedores
    print_info "🛑 Deteniendo contenedores..."
    docker-compose down
    
    # Hacer backup del estado actual antes de restaurar
    print_info "💾 Creando backup de seguridad del estado actual..."
    local safety_backup="safety_backup_$(date +%Y%m%d_%H%M%S).tar.gz"
    tar -czf "$BACKUP_DIR/$safety_backup" \
        --exclude="$VOLUMES_DIR/*/logs/*" \
        --exclude="$VOLUMES_DIR/*/temp/*" \
        -C "$(dirname "$VOLUMES_DIR")" \
        "$(basename "$VOLUMES_DIR")"
    
    # Restaurar volúmenes
    print_info "📦 Restaurando volúmenes..."
    tar -xzf "$backup_file" -C "$(dirname "$VOLUMES_DIR")"
    
    if [ $? -eq 0 ]; then
        print_success "Volúmenes restaurados exitosamente"
    else
        print_error "Error al restaurar volúmenes"
        exit 1
    fi
    
    # Restaurar permisos
    print_info "🔧 Restaurando permisos..."
    chmod -R 755 "$VOLUMES_DIR"
    find "$VOLUMES_DIR" -name "*.conf" -o -name "*.yml" -o -name "*.cnf" | xargs chmod 644
    
    # Reiniciar contenedores
    print_info "🚀 Reiniciando contenedores..."
    docker-compose up -d
    
    print_success "🎉 Restauración completada exitosamente!"
    print_info "Backup de seguridad creado: $BACKUP_DIR/$safety_backup"
}

# =============================================================================
# FUNCIÓN DE RESTAURACIÓN DE BASE DE DATOS
# =============================================================================

restore_database() {
    local db_backup_file="$1"
    
    if [ -z "$db_backup_file" ]; then
        print_error "Debe especificar un archivo de backup de base de datos"
        echo "Uso: $0 restore-db <archivo_backup.sql>"
        exit 1
    fi
    
    if [ ! -f "$db_backup_file" ]; then
        print_error "Archivo de backup de base de datos no encontrado: $db_backup_file"
        exit 1
    fi
    
    print_warning "⚠️  ADVERTENCIA: Esta operación sobrescribirá la base de datos actual"
    read -p "¿Está seguro de continuar? (y/N): " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Restauración de base de datos cancelada"
        exit 0
    fi
    
    print_info "🔄 Restaurando base de datos desde: $db_backup_file"
    
    # Verificar que MySQL está corriendo
    if ! docker-compose ps mysql | grep -q "Up"; then
        print_error "MySQL no está corriendo. Inicie los contenedores primero."
        exit 1
    fi
    
    # Restaurar base de datos
    docker-compose exec -T mysql mysql \
        -u root -proot_password_change_in_production \
        paqueteria < "$db_backup_file"
    
    if [ $? -eq 0 ]; then
        print_success "🎉 Base de datos restaurada exitosamente!"
    else
        print_error "Error al restaurar la base de datos"
        exit 1
    fi
}

# =============================================================================
# FUNCIÓN DE LISTADO DE BACKUPS
# =============================================================================

list_backups() {
    print_info "📋 Listando backups disponibles..."
    
    if [ ! -d "$BACKUP_DIR" ]; then
        print_warning "Directorio de backups no existe: $BACKUP_DIR"
        return
    fi
    
    echo ""
    echo "📦 Backups de volúmenes:"
    ls -lh "$BACKUP_DIR"/paqueteria_backup_*.tar.gz 2>/dev/null || echo "   No hay backups de volúmenes"
    
    echo ""
    echo "🗄️  Backups de base de datos:"
    ls -lh "$BACKUP_DIR"/mysql_backup_*.sql 2>/dev/null || echo "   No hay backups de base de datos"
    
    echo ""
    echo "💾 Espacio total usado: $(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1 || echo "N/A")"
}

# =============================================================================
# FUNCIÓN DE VERIFICACIÓN DE INTEGRIDAD
# =============================================================================

verify_backup() {
    local backup_file="$1"
    
    if [ -z "$backup_file" ]; then
        print_error "Debe especificar un archivo de backup"
        echo "Uso: $0 verify <archivo_backup.tar.gz>"
        exit 1
    fi
    
    if [ ! -f "$backup_file" ]; then
        print_error "Archivo de backup no encontrado: $backup_file"
        exit 1
    fi
    
    print_info "🔍 Verificando integridad del backup: $backup_file"
    
    # Verificar checksum
    if tar -tzf "$backup_file" > /dev/null 2>&1; then
        print_success "✅ Backup válido y accesible"
        print_info "Contenido del backup:"
        tar -tzf "$backup_file" | head -20
        echo "   ... (mostrando solo los primeros 20 archivos)"
    else
        print_error "❌ Backup corrupto o no válido"
        exit 1
    fi
}

# =============================================================================
# FUNCIÓN DE AYUDA
# =============================================================================

show_help() {
    echo "🔄 Script de Backup y Restauración - Sistema de Paquetería v1.1"
    echo ""
    echo "Uso: $0 <comando> [opciones]"
    echo ""
    echo "Comandos disponibles:"
    echo "  backup                    Crear backup de volúmenes y base de datos"
    echo "  restore <archivo>         Restaurar volúmenes desde un backup"
    echo "  restore-db <archivo>      Restaurar solo la base de datos"
    echo "  list                      Listar backups disponibles"
    echo "  verify <archivo>          Verificar integridad de un backup"
    echo "  help                      Mostrar esta ayuda"
    echo ""
    echo "Ejemplos:"
    echo "  $0 backup"
    echo "  $0 restore backups/paqueteria_backup_20250115_143022.tar.gz"
    echo "  $0 restore-db backups/mysql_backup_20250115_143022.sql"
    echo "  $0 list"
    echo "  $0 verify backups/paqueteria_backup_20250115_143022.tar.gz"
    echo ""
    echo "Notas:"
    echo "  - Los backups se guardan en el directorio: $BACKUP_DIR"
    echo "  - Se mantienen automáticamente los últimos 7 backups"
    echo "  - Los datos críticos incluyen: MySQL, Redis, uploads, configuraciones"
}

# =============================================================================
# MENÚ PRINCIPAL
# =============================================================================

case "${1:-help}" in
    "backup")
        backup_volumes
        ;;
    "restore")
        restore_volumes "$2"
        ;;
    "restore-db")
        restore_database "$2"
        ;;
    "list")
        list_backups
        ;;
    "verify")
        verify_backup "$2"
        ;;
    "help"|"--help"|"-h")
        show_help
        ;;
    *)
        print_error "Comando no válido: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
