# 🛠️ Configuración Manual - Resumen Final

## 🎯 **Configuración Manual del Servidor - Sistema de Paquetería v1.1**

### ✅ **Archivos Preparados para Configuración Manual:**

#### **1. Guía Completa**
- **Archivo:** `GUIA_CONFIGURACION_MANUAL.md`
- **Contenido:** Guía paso a paso completa
- **Incluye:** 12 pasos detallados con comandos

#### **2. Script de Ayuda**
- **Archivo:** `scripts/manual-setup.sh`
- **Función:** Menú interactivo para configuración
- **Características:** Instalación automática de herramientas

#### **3. Variables de Entorno**
- **Archivo:** `env.production.example`
- **Función:** Template para configuración de producción
- **Incluye:** Todas las variables necesarias

#### **4. Scripts de Despliegue**
- **Archivo:** `scripts/deploy.sh`
- **Función:** Automatización del despliegue
- **Características:** Health checks, backup, monitoreo

## 🚀 **Pasos Rápidos para Configuración Manual:**

### **PASO 1: Crear Instancia AWS Lightsail**
1. Ve a [AWS Lightsail Console](https://lightsail.aws.amazon.com/)
2. Crea instancia Ubuntu 22.04 LTS
3. Plan: Nano (1GB RAM, 1 vCPU, 40GB SSD) - $5/mes
4. Configura firewall: puertos 22, 80, 443

### **PASO 2: Conectarse al Servidor**
```bash
ssh ubuntu@[TU_IP_PUBLICA]
```

### **PASO 3: Usar Script de Ayuda**
```bash
# Subir código al servidor
scp -r . ubuntu@[TU_IP_PUBLICA]:~/paqueteria

# Conectarse al servidor
ssh ubuntu@[TU_IP_PUBLICA]

# Navegar al proyecto
cd ~/paqueteria

# Ejecutar script de ayuda
./scripts/manual-setup.sh
```

### **PASO 4: Seguir el Menú Interactivo**
1. **Opción 1:** Verificar sistema
2. **Opción 2:** Instalar Docker
3. **Opción 3:** Instalar Docker Compose
4. **Opción 4:** Instalar herramientas adicionales
5. **Opción 5:** Configurar firewall
6. **Opción 6:** Generar SECRET_KEY
7. **Opción 7:** Verificar configuración

### **PASO 5: Configurar Variables**
```bash
# Copiar template
cp env.production.example .env.production

# Editar variables
nano .env.production
```

### **PASO 6: Ejecutar Despliegue**
```bash
# Hacer scripts ejecutables
chmod +x scripts/deploy.sh

# Ejecutar despliegue
./scripts/deploy.sh deploy
```

## 📋 **Variables Importantes a Configurar:**

### **Obligatorias:**
```bash
SECRET_KEY=tu_clave_secreta_generada
ALLOWED_HOSTS=tu-dominio.com,www.tu-dominio.com
LIWA_API_KEY=tu_clave_api_liwa
AWS_ACCESS_KEY_ID=tu_aws_access_key
AWS_SECRET_ACCESS_KEY=tu_aws_secret_key
SMTP_USER=tu_email@gmail.com
SMTP_PASSWORD=tu_password_email
```

### **Opcionales (para funcionalidades avanzadas):**
```bash
SENTRY_DSN=tu_sentry_dsn
BACKUP_S3_BUCKET=tu_bucket_backup
```

## 🔧 **Comandos de Mantenimiento:**

### **Verificar Estado:**
```bash
# Estado de servicios
docker-compose ps

# Logs en tiempo real
docker-compose logs -f

# Health check
curl http://localhost:8000/health
```

### **Actualizar Aplicación:**
```bash
# Pull cambios
git pull

# Reconstruir y reiniciar
docker-compose build --no-cache
docker-compose up -d
```

### **Backup Manual:**
```bash
# Crear backup
./scripts/deploy.sh backup

# Ver backups
ls -la /backups/
```

## 🚨 **Solución de Problemas Comunes:**

### **Puerto 8000 no accesible:**
```bash
# Verificar servicios
docker-compose ps

# Ver logs
docker-compose logs fastapi

# Verificar puertos
netstat -tlnp | grep 8000
```

### **Base de datos no conecta:**
```bash
# Verificar MySQL
docker-compose logs mysql

# Conectar a MySQL
docker-compose exec mysql mysql -u root -p
```

### **Nginx no funciona:**
```bash
# Verificar configuración
sudo nginx -t

# Ver logs
sudo tail -f /var/log/nginx/error.log

# Reiniciar
sudo systemctl restart nginx
```

## 📊 **Monitoreo y Logs:**

### **Logs de Aplicación:**
```bash
# Logs de FastAPI
docker-compose logs -f fastapi

# Logs de MySQL
docker-compose logs -f mysql

# Logs de Nginx
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### **Monitoreo de Recursos:**
```bash
# Estadísticas de contenedores
docker stats

# Uso de disco
df -h

# Uso de memoria
free -h

# Procesos
htop
```

## 🔒 **Seguridad:**

### **Firewall Configurado:**
- Puerto 22 (SSH) - Permitido
- Puerto 80 (HTTP) - Permitido
- Puerto 443 (HTTPS) - Permitido
- Puerto 3306 (MySQL) - Solo contenedores

### **SSL/TLS:**
- Certificados Let's Encrypt (gratuito)
- Renovación automática
- Headers de seguridad configurados

### **Backup Automático:**
- Backup diario a las 2 AM
- Retención de 30 días
- Compresión automática

## 💰 **Costos Estimados:**

### **AWS Lightsail:**
- **Plan Nano:** $5-7 USD/mes
- **Transferencia:** 1TB incluida
- **Almacenamiento:** 40GB SSD

### **Costos Adicionales:**
- **Dominio:** $10-15 USD/año
- **SSL:** Gratuito (Let's Encrypt)
- **Backup:** Incluido en Lightsail

### **Total Estimado:**
- **~$75-100 USD/año**

## ✅ **Checklist Final:**

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

## 🎯 **Próximos Pasos:**

### **Inmediatos:**
1. Crear instancia en AWS Lightsail
2. Conectarse via SSH
3. Usar script de ayuda: `./scripts/manual-setup.sh`
4. Configurar variables de entorno
5. Ejecutar despliegue

### **Opcionales:**
1. Configurar dominio personalizado
2. Configurar SSL con Let's Encrypt
3. Configurar monitoreo avanzado
4. Configurar backup en S3

---

**¡Tu servidor estará listo para producción en 1-2 horas! 🚀**

**Archivos de referencia:**
- `GUIA_CONFIGURACION_MANUAL.md` - Guía completa
- `scripts/manual-setup.sh` - Script de ayuda
- `env.production.example` - Template de variables
- `scripts/deploy.sh` - Script de despliegue
