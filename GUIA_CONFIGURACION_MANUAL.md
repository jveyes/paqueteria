# 🛠️ Guía de Configuración Manual - Sistema de Paquetería v1.1

## 🎯 **Configuración Manual del Servidor**

### **PASO 1: Crear Instancia en AWS Lightsail**

#### **1.1 Acceder a AWS Lightsail**
1. Ve a [AWS Lightsail Console](https://lightsail.aws.amazon.com/)
2. Inicia sesión con tu cuenta de AWS
3. Selecciona la región: **US East (N. Virginia)**

#### **1.2 Crear Instancia**
1. Click en **"Create instance"**
2. **Choose a region and Availability Zone:**
   - Region: US East (N. Virginia)
   - Availability Zone: us-east-1a

3. **Choose your instance image:**
   - Platform: Linux/Unix
   - Operating system: Ubuntu
   - Version: Ubuntu 22.04 LTS

4. **Choose your instance plan:**
   - **Nano (1GB RAM, 1 vCPU, 40GB SSD)** - $5 USD/mes
   - Este plan es suficiente para empezar

5. **Identify your instance:**
   - Name: `paqueteria-server`
   - Tags: `paqueteria`, `production`

6. Click **"Create instance"**

#### **1.3 Configurar Firewall**
1. Ve a la pestaña **"Networking"**
2. Click en **"Add rule"**
3. Agregar reglas:
   - **HTTP (80)** - Allow
   - **HTTPS (443)** - Allow
   - **SSH (22)** - Allow (ya está por defecto)

### **PASO 2: Conectarse al Servidor**

#### **2.1 Obtener IP Pública**
1. En la consola de Lightsail, copia la **IP pública** de tu instancia
2. Ejemplo: `3.123.45.67`

#### **2.2 Conectarse via SSH**
```bash
# Conectarse al servidor
ssh ubuntu@[TU_IP_PUBLICA]

# Ejemplo:
ssh ubuntu@3.123.45.67
```

### **PASO 3: Configurar el Servidor**

#### **3.1 Actualizar Sistema**
```bash
# Actualizar paquetes
sudo apt update && sudo apt upgrade -y

# Instalar herramientas básicas
sudo apt install -y curl wget git htop nano
```

#### **3.2 Instalar Docker**
```bash
# Instalar dependencias
sudo apt install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Agregar clave GPG de Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Agregar repositorio de Docker
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Instalar Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io

# Agregar usuario al grupo docker
sudo usermod -aG docker $USER

# Habilitar Docker al inicio
sudo systemctl enable docker
sudo systemctl start docker
```

#### **3.3 Instalar Docker Compose**
```bash
# Descargar Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

# Hacer ejecutable
sudo chmod +x /usr/local/bin/docker-compose

# Verificar instalación
docker-compose --version
```

#### **3.4 Instalar Herramientas Adicionales**
```bash
# Instalar Nginx, Certbot, etc.
sudo apt install -y \
    nginx \
    certbot \
    python3-certbot-nginx \
    fail2ban \
    ufw \
    bc

# Configurar firewall
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw --force enable

# Configurar fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### **PASO 4: Subir el Código**

#### **4.1 Desde tu máquina local**
```bash
# Subir todo el proyecto
scp -r . ubuntu@[TU_IP_PUBLICA]:~/paqueteria

# Ejemplo:
scp -r . ubuntu@3.123.45.67:~/paqueteria
```

#### **4.2 Verificar en el servidor**
```bash
# Conectarse al servidor
ssh ubuntu@[TU_IP_PUBLICA]

# Verificar que se subió correctamente
ls -la ~/paqueteria
```

### **PASO 5: Configurar Variables de Entorno**

#### **5.1 Crear archivo de variables**
```bash
# En el servidor
cd ~/paqueteria
cp env.production.example .env.production
```

#### **5.2 Editar variables (IMPORTANTE)**
```bash
# Editar el archivo
nano .env.production
```

#### **5.3 Variables que DEBES cambiar:**
```bash
# Generar SECRET_KEY (ejecutar en servidor)
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Cambiar estas variables:
SECRET_KEY=tu_clave_secreta_generada
ALLOWED_HOSTS=tu-dominio.com,www.tu-dominio.com
LIWA_API_KEY=tu_clave_api_liwa
AWS_ACCESS_KEY_ID=tu_aws_access_key
AWS_SECRET_ACCESS_KEY=tu_aws_secret_key
SMTP_USER=tu_email@gmail.com
SMTP_PASSWORD=tu_password_email
```

### **PASO 6: Configurar Dominio (Opcional)**

#### **6.1 Si tienes dominio:**
1. Ve a tu proveedor de dominios
2. Configura un registro A:
   - Nombre: `@` o `www`
   - Valor: `[TU_IP_PUBLICA]`
   - TTL: 300 segundos

#### **6.2 Si NO tienes dominio:**
- Usaremos la IP directa
- SSL será más complicado pero posible

### **PASO 7: Ejecutar Despliegue**

#### **7.1 Hacer scripts ejecutables**
```bash
# En el servidor
cd ~/paqueteria
chmod +x scripts/deploy.sh
```

#### **7.2 Ejecutar despliegue**
```bash
# Despliegue completo
./scripts/deploy.sh deploy
```

#### **7.3 Verificar servicios**
```bash
# Ver estado de contenedores
docker-compose ps

# Ver logs
docker-compose logs

# Verificar health checks
curl http://localhost:8000/health
```

### **PASO 8: Configurar SSL (Si tienes dominio)**

#### **8.1 Con dominio configurado:**
```bash
# Configurar SSL automáticamente
./scripts/deploy.sh ssl
```

#### **8.2 Sin dominio (SSL manual):**
```bash
# Generar certificado autofirmado
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/private/nginx-selfsigned.key \
    -out /etc/ssl/certs/nginx-selfsigned.crt

# Configurar Nginx para usar certificado
sudo nano /etc/nginx/sites-available/paqueteria
```

### **PASO 9: Configurar Nginx**

#### **9.1 Copiar configuración**
```bash
# Copiar configuración de Nginx
sudo cp nginx/nginx.conf /etc/nginx/nginx.conf

# Verificar configuración
sudo nginx -t

# Reiniciar Nginx
sudo systemctl restart nginx
```

#### **9.2 Configurar proxy reverso**
```bash
# Crear configuración de sitio
sudo nano /etc/nginx/sites-available/paqueteria

# Contenido:
server {
    listen 80;
    server_name [TU_IP_PUBLICA] [TU_DOMINIO];
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Habilitar sitio
sudo ln -s /etc/nginx/sites-available/paqueteria /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### **PASO 10: Verificar Funcionamiento**

#### **10.1 Probar aplicación**
```bash
# Desde tu máquina local
curl http://[TU_IP_PUBLICA]

# O abrir en navegador:
# http://[TU_IP_PUBLICA]
```

#### **10.2 Verificar logs**
```bash
# En el servidor
docker-compose logs -f

# Logs de Nginx
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### **PASO 11: Configurar Monitoreo**

#### **11.1 Script de monitoreo básico**
```bash
# Crear script de monitoreo
sudo nano /usr/local/bin/monitor-paqueteria.sh

# Contenido:
#!/bin/bash
echo "=== Monitoreo Paquetería $(date) ==="

# Verificar servicios
if docker-compose ps | grep -q "Up"; then
    echo "✅ Servicios ejecutándose"
else
    echo "❌ Servicios caídos"
fi

# Verificar espacio en disco
DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
echo "💾 Uso de disco: ${DISK_USAGE}%"

# Verificar memoria
MEMORY_USAGE=$(free | awk 'NR==2{printf "%.1f", $3*100/$2}')
echo "🧠 Uso de memoria: ${MEMORY_USAGE}%"

# Hacer ejecutable
sudo chmod +x /usr/local/bin/monitor-paqueteria.sh

# Agregar al crontab
(crontab -l 2>/dev/null; echo "*/5 * * * * /usr/local/bin/monitor-paqueteria.sh") | crontab -
```

### **PASO 12: Configurar Backup**

#### **12.1 Script de backup automático**
```bash
# Crear script de backup
sudo nano /usr/local/bin/backup-paqueteria.sh

# Contenido:
#!/bin/bash
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/backup_$DATE.sql"

mkdir -p $BACKUP_DIR

# Backup de base de datos
docker-compose exec -T mysql mysqldump -u root -p"$MYSQL_ROOT_PASSWORD" \
    --single-transaction --routines --triggers paqueteria > $BACKUP_FILE

# Comprimir backup
gzip $BACKUP_FILE

# Eliminar backups antiguos (más de 30 días)
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete

echo "Backup creado: ${BACKUP_FILE}.gz"

# Hacer ejecutable
sudo chmod +x /usr/local/bin/backup-paqueteria.sh

# Agregar al crontab (backup diario a las 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * * /usr/local/bin/backup-paqueteria.sh") | crontab -
```

## 🎯 **Comandos de Mantenimiento**

### **Comandos útiles:**
```bash
# Ver estado de servicios
docker-compose ps

# Ver logs en tiempo real
docker-compose logs -f

# Reiniciar servicios
docker-compose restart

# Actualizar aplicación
git pull
docker-compose build --no-cache
docker-compose up -d

# Ver uso de recursos
docker stats

# Limpiar recursos no utilizados
docker system prune -f

# Verificar espacio en disco
df -h

# Verificar memoria
free -h

# Verificar procesos
htop
```

## 🚨 **Solución de Problemas**

### **Problemas comunes:**

#### **1. Puerto 8000 no accesible:**
```bash
# Verificar si el servicio está ejecutándose
docker-compose ps

# Ver logs del servicio
docker-compose logs fastapi

# Verificar puertos
netstat -tlnp | grep 8000
```

#### **2. Base de datos no conecta:**
```bash
# Verificar MySQL
docker-compose logs mysql

# Conectar a MySQL
docker-compose exec mysql mysql -u root -p

# Verificar variables de entorno
docker-compose exec fastapi env | grep DATABASE
```

#### **3. Nginx no funciona:**
```bash
# Verificar configuración
sudo nginx -t

# Ver logs
sudo tail -f /var/log/nginx/error.log

# Reiniciar Nginx
sudo systemctl restart nginx
```

## ✅ **Checklist Final**

- [ ] Instancia AWS Lightsail creada
- [ ] Conectado via SSH
- [ ] Docker instalado
- [ ] Docker Compose instalado
- [ ] Código subido al servidor
- [ ] Variables de entorno configuradas
- [ ] Dominio configurado (opcional)
- [ ] Despliegue ejecutado
- [ ] SSL configurado (opcional)
- [ ] Nginx configurado
- [ ] Monitoreo configurado
- [ ] Backup configurado
- [ ] Aplicación funcionando

---

**¡Tu servidor está listo para producción! 🚀**
