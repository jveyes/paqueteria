# 🚀 Guía Rápida - Configuración con Git

## ⚡ **Configuración Ultra Rápida con Git**

### **¿Por qué usar Git?**
- ✅ **Más rápido** - Solo descargas código, no archivos temporales
- ✅ **Actualizaciones fáciles** - `git pull` para actualizar
- ✅ **Control de versiones** - Puedes cambiar entre versiones
- ✅ **Menos transferencia** - Solo archivos necesarios

## 🎯 **Configuración en 5 Pasos**

### **PASO 1: Crear Instancia AWS Lightsail**
1. Ve a [AWS Lightsail Console](https://lightsail.aws.amazon.com/)
2. Crea instancia Ubuntu 22.04 LTS
3. Plan: Nano (1GB RAM, 1 vCPU, 40GB SSD) - $5/mes
4. Configura firewall: puertos 22, 80, 443

### **PASO 2: Conectarse al Servidor**
```bash
ssh ubuntu@[TU_IP_PUBLICA]
```

### **PASO 3: Descargar y Ejecutar Script de Git**
```bash
# Descargar script de configuración con Git
curl -O https://raw.githubusercontent.com/jveyes/paqueteria/main/scripts/git-setup.sh

# Hacer ejecutable
chmod +x git-setup.sh

# Ejecutar configuración automática
./git-setup.sh
```

### **PASO 4: Configurar Variables**
```bash
# Navegar al proyecto (el script te llevará ahí)
cd paqueteria

# Editar variables de entorno
nano .env.production
```

### **PASO 5: Ejecutar Despliegue**
```bash
# Ejecutar despliegue completo
./scripts/deploy.sh deploy
```

## 🔧 **Variables Importantes a Configurar:**

### **Obligatorias:**
```bash
ALLOWED_HOSTS=tu-dominio.com,www.tu-dominio.com
LIWA_API_KEY=tu_clave_api_liwa
AWS_ACCESS_KEY_ID=tu_aws_access_key
AWS_SECRET_ACCESS_KEY=tu_aws_secret_key
SMTP_USER=tu_email@gmail.com
SMTP_PASSWORD=tu_password_email
```

### **Opcionales:**
```bash
SENTRY_DSN=tu_sentry_dsn
BACKUP_S3_BUCKET=tu_bucket_backup
```

## 🔄 **Comandos para Actualizaciones:**

### **Actualizar Código:**
```bash
# Pull cambios del repositorio
git pull origin main

# Reconstruir y reiniciar servicios
docker-compose build --no-cache
docker-compose up -d
```

### **Ver Estado:**
```bash
# Ver estado del repositorio
git status

# Ver cambios recientes
git log --oneline -10

# Ver diferencias
git diff
```

## 📋 **Script de Configuración Automática**

El script `git-setup.sh` hace automáticamente:

1. ✅ Actualiza el sistema
2. ✅ Instala Git y herramientas
3. ✅ Clona el repositorio
4. ✅ Configura variables de entorno
5. ✅ Genera SECRET_KEY automáticamente
6. ✅ Hace scripts ejecutables
7. ✅ Muestra instrucciones

## 🚨 **Solución de Problemas:**

### **Error al clonar:**
```bash
# Verificar conectividad
ping github.com

# Clonar con verbose
git clone -v https://github.com/jveyes/paqueteria.git
```

### **Error de permisos:**
```bash
# Verificar permisos
ls -la scripts/

# Hacer ejecutables
chmod +x scripts/*.sh
```

### **Error de variables:**
```bash
# Verificar archivo
cat .env.production

# Regenerar SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

## ⚡ **Configuración Ultra Rápida (1 comando):**

```bash
# Todo en un comando
curl -s https://raw.githubusercontent.com/jveyes/paqueteria/main/scripts/git-setup.sh | bash
```

## 📊 **Comparación de Métodos:**

| Método | Tiempo | Transferencia | Ventajas |
|--------|--------|---------------|----------|
| **Git Clone** | 5-10 min | ~50MB | ✅ Rápido, actualizable |
| **SCP Manual** | 15-30 min | ~200MB | ❌ Lento, no actualizable |

## 🎯 **Ventajas de Git Clone:**

### **Velocidad:**
- ⚡ **5-10 minutos** vs 15-30 minutos
- 📦 **Solo código** vs archivos temporales
- 🔄 **Actualizaciones instantáneas**

### **Mantenimiento:**
- 📝 **Control de versiones**
- 🔄 **Fácil rollback**
- 📊 **Historial de cambios**

### **Colaboración:**
- 👥 **Múltiples desarrolladores**
- 🌿 **Branches para features**
- 🔀 **Merge automático**

## ✅ **Checklist Rápido:**

- [ ] Instancia AWS Lightsail creada
- [ ] Conectado via SSH
- [ ] Script git-setup.sh ejecutado
- [ ] Variables de entorno configuradas
- [ ] Despliegue ejecutado
- [ ] Aplicación funcionando

## 🚀 **¡Listo en 30 minutos!**

**Con Git Clone:**
1. **Crear instancia:** 5 min
2. **Conectar y clonar:** 5 min
3. **Configurar variables:** 10 min
4. **Desplegar:** 10 min
5. **Total:** ~30 minutos

---

**¡Git Clone es la opción más eficiente! 🚀**
