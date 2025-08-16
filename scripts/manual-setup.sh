#!/bin/bash

# =============================================================================
# SCRIPT DE AYUDA PARA CONFIGURACIÓN MANUAL - Sistema de Paquetería v1.1
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

# Función para mostrar menú
show_menu() {
    echo ""
    echo "🚀 CONFIGURACIÓN MANUAL - Sistema de Paquetería v1.1"
    echo "=================================================="
    echo ""
    echo "1.  Verificar sistema"
    echo "2.  Instalar Docker"
    echo "3.  Instalar Docker Compose"
    echo "4.  Instalar herramientas adicionales"
    echo "5.  Configurar firewall"
    echo "6.  Generar SECRET_KEY"
    echo "7.  Verificar configuración"
    echo "8.  Mostrar comandos útiles"
    echo "9.  Mostrar guía completa"
    echo "0.  Salir"
    echo ""
    read -p "Selecciona una opción: " choice
}

# Función para verificar sistema
check_system() {
    log "Verificando sistema..."
    
    echo "📋 Información del sistema:"
    echo "OS: $(lsb_release -d | cut -f2)"
    echo "Kernel: $(uname -r)"
    echo "Arquitectura: $(uname -m)"
    echo "Memoria: $(free -h | awk 'NR==2{print $2}')"
    echo "Disco: $(df -h / | awk 'NR==2{print $2}')"
    echo ""
    
    echo "🔧 Herramientas disponibles:"
    echo "curl: $(command -v curl >/dev/null && echo "✅" || echo "❌")"
    echo "wget: $(command -v wget >/dev/null && echo "✅" || echo "❌")"
    echo "git: $(command -v git >/dev/null && echo "✅" || echo "❌")"
    echo "docker: $(command -v docker >/dev/null && echo "✅" || echo "❌")"
    echo "docker-compose: $(command -v docker-compose >/dev/null && echo "✅" || echo "❌")"
    echo "nginx: $(command -v nginx >/dev/null && echo "✅" || echo "❌")"
    echo ""
}

# Función para instalar Docker
install_docker() {
    log "Instalando Docker..."
    
    # Verificar si ya está instalado
    if command -v docker &> /dev/null; then
        warn "Docker ya está instalado"
        docker --version
        return
    fi
    
    echo "📦 Instalando dependencias..."
    sudo apt update
    sudo apt install -y \
        apt-transport-https \
        ca-certificates \
        curl \
        gnupg \
        lsb-release
    
    echo "🔑 Agregando clave GPG de Docker..."
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    
    echo "📝 Agregando repositorio de Docker..."
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    echo "📦 Instalando Docker..."
    sudo apt update
    sudo apt install -y docker-ce docker-ce-cli containerd.io
    
    echo "👤 Agregando usuario al grupo docker..."
    sudo usermod -aG docker $USER
    
    echo "🚀 Habilitando Docker al inicio..."
    sudo systemctl enable docker
    sudo systemctl start docker
    
    log "Docker instalado correctamente!"
    echo "⚠️  IMPORTANTE: Reinicia la sesión SSH para que los cambios de grupo surtan efecto"
}

# Función para instalar Docker Compose
install_docker_compose() {
    log "Instalando Docker Compose..."
    
    # Verificar si ya está instalado
    if command -v docker-compose &> /dev/null; then
        warn "Docker Compose ya está instalado"
        docker-compose --version
        return
    fi
    
    echo "📥 Descargando Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    
    echo "🔧 Haciendo ejecutable..."
    sudo chmod +x /usr/local/bin/docker-compose
    
    echo "✅ Verificando instalación..."
    docker-compose --version
    
    log "Docker Compose instalado correctamente!"
}

# Función para instalar herramientas adicionales
install_tools() {
    log "Instalando herramientas adicionales..."
    
    echo "📦 Instalando herramientas..."
    sudo apt update
    sudo apt install -y \
        nginx \
        certbot \
        python3-certbot-nginx \
        fail2ban \
        ufw \
        bc \
        htop \
        nano \
        git
    
    echo "🔧 Configurando fail2ban..."
    sudo systemctl enable fail2ban
    sudo systemctl start fail2ban
    
    log "Herramientas instaladas correctamente!"
}

# Función para configurar firewall
setup_firewall() {
    log "Configurando firewall..."
    
    echo "🔥 Configurando UFW..."
    sudo ufw allow ssh
    sudo ufw allow 80
    sudo ufw allow 443
    sudo ufw --force enable
    
    echo "📊 Estado del firewall:"
    sudo ufw status
    
    log "Firewall configurado correctamente!"
}

# Función para generar SECRET_KEY
generate_secret_key() {
    log "Generando SECRET_KEY..."
    
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    
    echo "🔑 SECRET_KEY generada:"
    echo "$SECRET_KEY"
    echo ""
    echo "📝 Copia esta clave y agrégala a tu archivo .env.production"
    echo "SECRET_KEY=$SECRET_KEY"
}

# Función para verificar configuración
check_configuration() {
    log "Verificando configuración..."
    
    echo "🐳 Verificando Docker..."
    if command -v docker &> /dev/null; then
        echo "✅ Docker: $(docker --version)"
    else
        echo "❌ Docker: No instalado"
    fi
    
    echo "🐳 Verificando Docker Compose..."
    if command -v docker-compose &> /dev/null; then
        echo "✅ Docker Compose: $(docker-compose --version)"
    else
        echo "❌ Docker Compose: No instalado"
    fi
    
    echo "🌐 Verificando Nginx..."
    if command -v nginx &> /dev/null; then
        echo "✅ Nginx: $(nginx -v 2>&1)"
    else
        echo "❌ Nginx: No instalado"
    fi
    
    echo "🔒 Verificando firewall..."
    if sudo ufw status | grep -q "Status: active"; then
        echo "✅ Firewall: Activo"
    else
        echo "❌ Firewall: Inactivo"
    fi
    
    echo "📁 Verificando directorio del proyecto..."
    if [ -d "~/paqueteria" ]; then
        echo "✅ Proyecto: Encontrado en ~/paqueteria"
    else
        echo "❌ Proyecto: No encontrado"
    fi
    
    echo "📄 Verificando archivo de variables..."
    if [ -f ".env.production" ]; then
        echo "✅ Variables: Archivo .env.production encontrado"
    else
        echo "❌ Variables: Archivo .env.production no encontrado"
    fi
}

# Función para mostrar comandos útiles
show_useful_commands() {
    echo ""
    echo "🔧 COMANDOS ÚTILES"
    echo "=================="
    echo ""
    echo "🐳 Docker:"
    echo "  docker ps                    # Ver contenedores ejecutándose"
    echo "  docker-compose ps            # Ver estado de servicios"
    echo "  docker-compose logs -f       # Ver logs en tiempo real"
    echo "  docker-compose restart       # Reiniciar servicios"
    echo "  docker system prune -f       # Limpiar recursos no utilizados"
    echo ""
    echo "🌐 Nginx:"
    echo "  sudo nginx -t                # Verificar configuración"
    echo "  sudo systemctl restart nginx # Reiniciar Nginx"
    echo "  sudo tail -f /var/log/nginx/error.log  # Ver logs de error"
    echo ""
    echo "💾 Sistema:"
    echo "  df -h                        # Ver espacio en disco"
    echo "  free -h                      # Ver memoria"
    echo "  htop                         # Monitor de procesos"
    echo "  sudo ufw status              # Estado del firewall"
    echo ""
    echo "📊 Monitoreo:"
    echo "  docker stats                 # Estadísticas de contenedores"
    echo "  netstat -tlnp | grep 8000    # Verificar puerto 8000"
    echo "  curl http://localhost:8000/health  # Health check"
    echo ""
}

# Función para mostrar guía completa
show_complete_guide() {
    echo ""
    echo "📖 GUÍA COMPLETA DE CONFIGURACIÓN"
    echo "================================="
    echo ""
    echo "📋 Pasos completos:"
    echo "1. Crear instancia en AWS Lightsail"
    echo "2. Conectarse via SSH"
    echo "3. Actualizar sistema: sudo apt update && sudo apt upgrade -y"
    echo "4. Instalar Docker y Docker Compose"
    echo "5. Subir código: scp -r . ubuntu@[IP]:~/paqueteria"
    echo "6. Configurar variables: cp env.production.example .env.production"
    echo "7. Editar variables: nano .env.production"
    echo "8. Ejecutar despliegue: ./scripts/deploy.sh deploy"
    echo "9. Configurar Nginx"
    echo "10. Configurar SSL (opcional)"
    echo ""
    echo "📄 Ver archivo GUIA_CONFIGURACION_MANUAL.md para detalles completos"
    echo ""
}

# Función principal
main() {
    while true; do
        show_menu
        
        case $choice in
            1)
                check_system
                ;;
            2)
                install_docker
                ;;
            3)
                install_docker_compose
                ;;
            4)
                install_tools
                ;;
            5)
                setup_firewall
                ;;
            6)
                generate_secret_key
                ;;
            7)
                check_configuration
                ;;
            8)
                show_useful_commands
                ;;
            9)
                show_complete_guide
                ;;
            0)
                log "¡Hasta luego!"
                exit 0
                ;;
            *)
                error "Opción inválida"
                ;;
        esac
        
        echo ""
        read -p "Presiona Enter para continuar..."
    done
}

# Verificar si se ejecuta como root
if [ "$EUID" -eq 0 ]; then
    error "No ejecutes este script como root"
fi

# Ejecutar función principal
main
