#!/bin/bash

# =============================================================================
# SCRIPT DE CONFIGURACIÓN CON GIT - Sistema de Paquetería v1.1
# =============================================================================

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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
REPO_URL="https://github.com/jveyes/paqueteria.git"
PROJECT_DIR="paqueteria"

# Función para actualizar sistema
update_system() {
    log "Actualizando sistema..."
    sudo apt update && sudo apt upgrade -y
    log "Sistema actualizado"
}

# Función para instalar Git
install_git() {
    log "Instalando Git..."
    
    if command -v git &> /dev/null; then
        warn "Git ya está instalado"
        git --version
        return
    fi
    
    sudo apt install -y git curl wget htop nano
    log "Git instalado correctamente"
}

# Función para clonar repositorio
clone_repository() {
    log "Clonando repositorio..."
    
    if [ -d "$PROJECT_DIR" ]; then
        warn "El directorio $PROJECT_DIR ya existe"
        read -p "¿Quieres eliminar el directorio existente y clonar de nuevo? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$PROJECT_DIR"
        else
            log "Usando directorio existente"
            return
        fi
    fi
    
    git clone "$REPO_URL"
    
    if [ $? -eq 0 ]; then
        log "Repositorio clonado correctamente"
    else
        error "Error clonando repositorio"
    fi
}

# Función para configurar Git
setup_git() {
    log "Configurando Git..."
    
    # Configurar usuario Git (opcional)
    read -p "¿Quieres configurar Git con tu información? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "Nombre de usuario Git: " git_name
        read -p "Email Git: " git_email
        
        git config --global user.name "$git_name"
        git config --global user.email "$git_email"
        
        log "Git configurado con: $git_name <$git_email>"
    fi
}

# Función para navegar al proyecto
navigate_to_project() {
    log "Navegando al proyecto..."
    cd "$PROJECT_DIR"
    
    # Verificar que estamos en el directorio correcto
    if [ -f "docker-compose.yml" ] && [ -f "requirements.txt" ]; then
        log "Directorio del proyecto encontrado"
        pwd
        ls -la
    else
        error "No se encontró el proyecto en el directorio actual"
    fi
}

# Función para hacer scripts ejecutables
make_scripts_executable() {
    log "Haciendo scripts ejecutables..."
    chmod +x scripts/*.sh
    log "Scripts hechos ejecutables"
}

# Función para configurar variables de entorno
setup_environment() {
    log "Configurando variables de entorno..."
    
    if [ -f ".env.production" ]; then
        warn "Archivo .env.production ya existe"
        read -p "¿Quieres sobrescribirlo? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            return
        fi
    fi
    
    cp env.production.example .env.production
    
    # Generar SECRET_KEY
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    
    # Reemplazar SECRET_KEY en el archivo
    sed -i "s/your-super-secret-production-key-change-this-immediately/$SECRET_KEY/" .env.production
    
    log "Variables de entorno configuradas"
    echo "🔑 SECRET_KEY generada automáticamente"
    echo "📝 Edita .env.production para configurar otras variables"
}

# Función para mostrar instrucciones
show_instructions() {
    log "Configuración con Git completada!"
    echo ""
    echo "📋 Próximos pasos:"
    echo "1. Editar variables de entorno:"
    echo "   nano .env.production"
    echo ""
    echo "2. Ejecutar script de configuración:"
    echo "   ./scripts/manual-setup.sh"
    echo ""
    echo "3. O ejecutar despliegue directo:"
    echo "   ./scripts/deploy.sh deploy"
    echo ""
    echo "🔧 Variables importantes a configurar:"
    echo "   - ALLOWED_HOSTS=tu-dominio.com"
    echo "   - LIWA_API_KEY=tu_clave_api_liwa"
    echo "   - AWS_ACCESS_KEY_ID=tu_aws_access_key"
    echo "   - AWS_SECRET_ACCESS_KEY=tu_aws_secret_key"
    echo "   - SMTP_USER=tu_email@gmail.com"
    echo "   - SMTP_PASSWORD=tu_password_email"
    echo ""
}

# Función para mostrar comandos útiles
show_useful_commands() {
    echo ""
    echo "🔧 COMANDOS ÚTILES PARA GIT:"
    echo "============================"
    echo ""
    echo "📥 Actualizar código:"
    echo "   git pull origin main"
    echo ""
    echo "📊 Ver estado:"
    echo "   git status"
    echo "   git log --oneline -10"
    echo ""
    echo "🔄 Actualizar aplicación:"
    echo "   git pull origin main"
    echo "   docker-compose build --no-cache"
    echo "   docker-compose up -d"
    echo ""
    echo "📝 Ver cambios:"
    echo "   git diff"
    echo "   git show"
    echo ""
}

# Función principal
main() {
    log "Iniciando configuración con Git..."
    
    # Verificar si se ejecuta como root
    if [ "$EUID" -eq 0 ]; then
        error "No ejecutes este script como root"
    fi
    
    # Actualizar sistema
    update_system
    
    # Instalar Git
    install_git
    
    # Configurar Git
    setup_git
    
    # Clonar repositorio
    clone_repository
    
    # Navegar al proyecto
    navigate_to_project
    
    # Hacer scripts ejecutables
    make_scripts_executable
    
    # Configurar variables de entorno
    setup_environment
    
    # Mostrar instrucciones
    show_instructions
    
    # Mostrar comandos útiles
    show_useful_commands
    
    log "¡Configuración con Git completada exitosamente!"
}

# Ejecutar función principal
main
