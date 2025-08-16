#!/bin/bash

# =============================================================================
# SCRIPT DE CONFIGURACIÓN AWS LIGHTSAIL - Sistema de Paquetería v1.1
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
INSTANCE_NAME="paqueteria-server"
REGION="us-east-1"
BLUEPRINT_ID="ubuntu_22_04"
BUNDLE_ID="nano_2_0"  # 1GB RAM, 1 vCPU, 40GB SSD
DOMAIN_NAME="your-domain.com"

# Función para verificar AWS CLI
check_aws_cli() {
    log "Verificando AWS CLI..."
    
    if ! command -v aws &> /dev/null; then
        error "AWS CLI no está instalado. Instálelo primero: https://aws.amazon.com/cli/"
    fi
    
    # Verificar configuración de AWS
    if ! aws sts get-caller-identity &> /dev/null; then
        error "AWS CLI no está configurado. Ejecute 'aws configure' primero"
    fi
    
    log "AWS CLI verificado correctamente"
}

# Función para crear instancia
create_instance() {
    log "Creando instancia en AWS Lightsail..."
    
    # Crear instancia
    aws lightsail create-instances \
        --instance-names $INSTANCE_NAME \
        --availability-zone ${REGION}a \
        --blueprint-id $BLUEPRINT_ID \
        --bundle-id $BUNDLE_ID \
        --region $REGION
    
    if [ $? -eq 0 ]; then
        log "Instancia creada: $INSTANCE_NAME"
    else
        error "Error creando instancia"
    fi
    
    # Esperar a que la instancia esté lista
    log "Esperando a que la instancia esté lista..."
    aws lightsail wait instance-running \
        --instance-name $INSTANCE_NAME \
        --region $REGION
    
    log "Instancia lista"
}

# Función para configurar firewall
configure_firewall() {
    log "Configurando firewall..."
    
    # Abrir puerto SSH
    aws lightsail open-instance-public-ports \
        --instance-name $INSTANCE_NAME \
        --port-info fromPort=22,toPort=22,protocol=tcp \
        --region $REGION
    
    # Abrir puerto HTTP
    aws lightsail open-instance-public-ports \
        --instance-name $INSTANCE_NAME \
        --port-info fromPort=80,toPort=80,protocol=tcp \
        --region $REGION
    
    # Abrir puerto HTTPS
    aws lightsail open-instance-public-ports \
        --instance-name $INSTANCE_NAME \
        --port-info fromPort=443,toPort=443,protocol=tcp \
        --region $REGION
    
    log "Firewall configurado"
}

# Función para obtener IP pública
get_public_ip() {
    log "Obteniendo IP pública..."
    
    PUBLIC_IP=$(aws lightsail get-instance \
        --instance-name $INSTANCE_NAME \
        --region $REGION \
        --query 'instance.publicIpAddress' \
        --output text)
    
    echo "IP Pública: $PUBLIC_IP"
    echo "Guarde esta IP para configurar su dominio"
}

# Función para crear script de instalación
create_install_script() {
    log "Creando script de instalación..."
    
    cat > install-docker.sh << 'EOF'
#!/bin/bash

# Script de instalación de Docker en Ubuntu 22.04

set -e

echo "Actualizando sistema..."
sudo apt-get update
sudo apt-get upgrade -y

echo "Instalando dependencias..."
sudo apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

echo "Agregando repositorio de Docker..."
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

echo "Instalando Docker..."
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io

echo "Instalando Docker Compose..."
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

echo "Agregando usuario al grupo docker..."
sudo usermod -aG docker $USER

echo "Configurando Docker para iniciar automáticamente..."
sudo systemctl enable docker
sudo systemctl start docker

echo "Instalando herramientas adicionales..."
sudo apt-get install -y \
    htop \
    nginx \
    certbot \
    python3-certbot-nginx \
    fail2ban \
    ufw

echo "Configurando firewall..."
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw --force enable

echo "Configurando fail2ban..."
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

echo "Instalación completada!"
echo "Reinicie la sesión SSH para que los cambios de grupo surtan efecto"
EOF
    
    chmod +x install-docker.sh
    log "Script de instalación creado: install-docker.sh"
}

# Función para mostrar instrucciones
show_instructions() {
    log "Instrucciones de configuración:"
    echo ""
    echo "1. Conectarse a la instancia:"
    echo "   ssh ubuntu@$PUBLIC_IP"
    echo ""
    echo "2. Subir el script de instalación:"
    echo "   scp install-docker.sh ubuntu@$PUBLIC_IP:~/"
    echo ""
    echo "3. Ejecutar el script de instalación:"
    echo "   ssh ubuntu@$PUBLIC_IP 'chmod +x install-docker.sh && ./install-docker.sh'"
    echo ""
    echo "4. Subir el código de la aplicación:"
    echo "   scp -r . ubuntu@$PUBLIC_IP:~/paqueteria"
    echo ""
    echo "5. Configurar variables de entorno:"
    echo "   ssh ubuntu@$PUBLIC_IP 'cd paqueteria && cp env.production.example .env.production'"
    echo ""
    echo "6. Editar variables de entorno:"
    echo "   ssh ubuntu@$PUBLIC_IP 'nano paqueteria/.env.production'"
    echo ""
    echo "7. Ejecutar despliegue:"
    echo "   ssh ubuntu@$PUBLIC_IP 'cd paqueteria && ./scripts/deploy.sh deploy'"
    echo ""
    echo "8. Configurar dominio:"
    echo "   Apunte su dominio $DOMAIN_NAME a la IP: $PUBLIC_IP"
    echo ""
    echo "9. Configurar SSL:"
    echo "   ssh ubuntu@$PUBLIC_IP 'cd paqueteria && ./scripts/deploy.sh ssl'"
    echo ""
}

# Función para crear snapshot
create_snapshot() {
    log "Creando snapshot de la instancia..."
    
    SNAPSHOT_NAME="${INSTANCE_NAME}-snapshot-$(date +%Y%m%d-%H%M%S)"
    
    aws lightsail create-instance-snapshot \
        --instance-snapshot-name $SNAPSHOT_NAME \
        --instance-name $INSTANCE_NAME \
        --region $REGION
    
    log "Snapshot creado: $SNAPSHOT_NAME"
}

# Función para mostrar costos
show_costs() {
    log "Información de costos:"
    echo ""
    echo "Plan Nano (1GB RAM, 1 vCPU, 40GB SSD):"
    echo "  - Costo mensual: ~$5-7 USD"
    echo "  - Transferencia: 1TB incluida"
    echo "  - Almacenamiento: 40GB SSD"
    echo ""
    echo "Costos adicionales:"
    echo "  - Dominio: ~$10-15 USD/año"
    echo "  - SSL: Gratuito (Let's Encrypt)"
    echo "  - Backup: Incluido en Lightsail"
    echo ""
}

# Función principal
main() {
    log "Iniciando configuración de AWS Lightsail..."
    
    # Verificar AWS CLI
    check_aws_cli
    
    # Crear instancia
    create_instance
    
    # Configurar firewall
    configure_firewall
    
    # Obtener IP pública
    get_public_ip
    
    # Crear script de instalación
    create_install_script
    
    # Mostrar instrucciones
    show_instructions
    
    # Mostrar costos
    show_costs
    
    log "Configuración de AWS Lightsail completada!"
}

# Función de ayuda
show_help() {
    echo "Uso: $0 [OPCIÓN]"
    echo ""
    echo "Opciones:"
    echo "  setup       Configurar instancia completa"
    echo "  create      Solo crear instancia"
    echo "  firewall    Solo configurar firewall"
    echo "  snapshot    Crear snapshot"
    echo "  costs       Mostrar información de costos"
    echo "  help        Mostrar esta ayuda"
    echo ""
}

# Procesar argumentos
case "${1:-setup}" in
    setup)
        main
        ;;
    create)
        check_aws_cli
        create_instance
        get_public_ip
        ;;
    firewall)
        configure_firewall
        ;;
    snapshot)
        create_snapshot
        ;;
    costs)
        show_costs
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        error "Opción desconocida: $1"
        show_help
        ;;
esac
