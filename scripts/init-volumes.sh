#!/bin/bash

# =============================================================================
# SCRIPT DE INICIALIZACIÓN DE VOLÚMENES - Sistema de Paquetería v1.1
# =============================================================================

set -e

echo "🚀 Inicializando volúmenes externos para Sistema de Paquetería v1.1..."

# =============================================================================
# CONFIGURACIÓN
# =============================================================================

# Directorio base de volúmenes
VOLUMES_DIR="./volumes"

# Usuario y grupo para los volúmenes (ajustar según tu sistema)
VOLUME_USER="1000"
VOLUME_GROUP="1000"

# =============================================================================
# FUNCIÓN PARA CREAR DIRECTORIO CON PERMISOS
# =============================================================================

create_volume_dir() {
    local dir="$1"
    local description="$2"
    
    echo "📁 Creando: $description"
    mkdir -p "$dir"
    chown -R $VOLUME_USER:$VOLUME_GROUP "$dir"
    chmod -R 755 "$dir"
    
    # Para directorios de datos críticos, permisos más restrictivos
    if [[ "$dir" == *"/data"* ]] || [[ "$dir" == *"/uploads"* ]] || [[ "$dir" == *"/backups"* ]]; then
        chmod -R 750 "$dir"
        echo "   🔒 Permisos restrictivos aplicados (750)"
    else
        echo "   📝 Permisos estándar aplicados (755)"
    fi
}

# =============================================================================
# CREACIÓN DE DIRECTORIOS DE VOLÚMENES
# =============================================================================

echo ""
echo "📂 Creando estructura de volúmenes..."

# Base de datos MySQL
create_volume_dir "$VOLUMES_DIR/mysql/data" "Datos de MySQL (CRÍTICO)"
create_volume_dir "$VOLUMES_DIR/mysql/logs" "Logs de MySQL"
create_volume_dir "$VOLUMES_DIR/mysql/config" "Configuración de MySQL"

# Redis
create_volume_dir "$VOLUMES_DIR/redis/data" "Datos de Redis (CRÍTICO)"
create_volume_dir "$VOLUMES_DIR/redis/logs" "Logs de Redis"
create_volume_dir "$VOLUMES_DIR/redis/config" "Configuración de Redis"

# Aplicación
create_volume_dir "$VOLUMES_DIR/logs" "Logs de la aplicación"
create_volume_dir "$VOLUMES_DIR/uploads" "Archivos subidos por usuarios (CRÍTICO)"
create_volume_dir "$VOLUMES_DIR/config" "Configuración de la aplicación"
create_volume_dir "$VOLUMES_DIR/ssl" "Certificados SSL"

# Nginx
create_volume_dir "$VOLUMES_DIR/nginx/config" "Configuración de Nginx"
create_volume_dir "$VOLUMES_DIR/nginx/logs" "Logs de Nginx"
create_volume_dir "$VOLUMES_DIR/nginx/ssl" "SSL de Nginx"

# Archivos estáticos
create_volume_dir "$VOLUMES_DIR/static" "Archivos estáticos"

# Celery
create_volume_dir "$VOLUMES_DIR/celery/temp" "Archivos temporales de Celery"

# Flower
create_volume_dir "$VOLUMES_DIR/flower/logs" "Logs de Flower"

# Prometheus
create_volume_dir "$VOLUMES_DIR/prometheus/config" "Configuración de Prometheus"
create_volume_dir "$VOLUMES_DIR/prometheus/data" "Datos de métricas (CRÍTICO)"
create_volume_dir "$VOLUMES_DIR/prometheus/logs" "Logs de Prometheus"

# Grafana
create_volume_dir "$VOLUMES_DIR/grafana/data" "Datos de Grafana (CRÍTICO)"
create_volume_dir "$VOLUMES_DIR/grafana/config" "Configuración de Grafana"
create_volume_dir "$VOLUMES_DIR/grafana/logs" "Logs de Grafana"

# Backups
create_volume_dir "$VOLUMES_DIR/backups" "Backups de la base de datos (CRÍTICO)"

# =============================================================================
# CONFIGURACIÓN INICIAL DE ARCHIVOS
# =============================================================================

echo ""
echo "⚙️  Configurando archivos iniciales..."

# Configuración de Redis
if [ ! -f "$VOLUMES_DIR/redis/config/redis.conf" ]; then
    echo "📝 Creando configuración de Redis..."
    cat > "$VOLUMES_DIR/redis/config/redis.conf" << 'EOF'
# Configuración de Redis para Sistema de Paquetería v1.1
bind 0.0.0.0
port 6379
timeout 0
tcp-keepalive 300
daemonize no
supervised no
pidfile /var/run/redis_6379.pid
loglevel notice
logfile ""
databases 16
save 900 1
save 300 10
save 60 10000
stop-writes-on-bgsave-error yes
rdbcompression yes
rdbchecksum yes
dbfilename dump.rdb
dir /data
maxmemory 256mb
maxmemory-policy allkeys-lru
appendonly yes
appendfilename "appendonly.aof"
appendfsync everysec
no-appendfsync-on-rewrite no
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb
EOF
    chown $VOLUME_USER:$VOLUME_GROUP "$VOLUMES_DIR/redis/config/redis.conf"
    chmod 644 "$VOLUMES_DIR/redis/config/redis.conf"
fi

# Configuración de MySQL
if [ ! -f "$VOLUMES_DIR/mysql/config/custom.cnf" ]; then
    echo "📝 Creando configuración de MySQL..."
    cat > "$VOLUMES_DIR/mysql/config/custom.cnf" << 'EOF'
[mysqld]
# Configuración de MySQL para Sistema de Paquetería v1.1
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci
default-authentication-plugin = mysql_native_password

# Configuración de rendimiento
innodb_buffer_pool_size = 256M
innodb_log_file_size = 64M
innodb_flush_log_at_trx_commit = 2
innodb_flush_method = O_DIRECT

# Configuración de conexiones
max_connections = 200
max_connect_errors = 1000000

# Configuración de logs
log-error = /var/log/mysql/error.log
slow_query_log = 1
slow_query_log_file = /var/log/mysql/slow.log
long_query_time = 2

# Configuración de seguridad
sql_mode = STRICT_TRANS_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO

[mysql]
default-character-set = utf8mb4

[client]
default-character-set = utf8mb4
EOF
    chown $VOLUME_USER:$VOLUME_GROUP "$VOLUMES_DIR/mysql/config/custom.cnf"
    chmod 644 "$VOLUMES_DIR/mysql/config/custom.cnf"
fi

# Configuración de Nginx
if [ ! -f "$VOLUMES_DIR/nginx/config/default.conf" ]; then
    echo "📝 Creando configuración de Nginx..."
    cat > "$VOLUMES_DIR/nginx/config/default.conf" << 'EOF'
# Configuración de Nginx para Sistema de Paquetería v1.1
server {
    listen 80;
    server_name localhost;
    
    # Redirigir a HTTPS en producción
    # return 301 https://$server_name$request_uri;
    
    # Proxy a FastAPI
    location / {
        proxy_pass http://fastapi:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Archivos estáticos
    location /static/ {
        alias /var/www/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Health check
    location /health {
        proxy_pass http://fastapi:8000/health;
        access_log off;
    }
}
EOF
    chown $VOLUME_USER:$VOLUME_GROUP "$VOLUMES_DIR/nginx/config/default.conf"
    chmod 644 "$VOLUMES_DIR/nginx/config/default.conf"
fi

# Configuración de Prometheus
if [ ! -f "$VOLUMES_DIR/prometheus/config/prometheus.yml" ]; then
    echo "📝 Creando configuración de Prometheus..."
    cat > "$VOLUMES_DIR/prometheus/config/prometheus.yml" << 'EOF'
# Configuración de Prometheus para Sistema de Paquetería v1.1
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  # - "first_rules.yml"
  # - "second_rules.yml"

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'fastapi'
    static_configs:
      - targets: ['fastapi:8000']
    metrics_path: '/metrics'
    scrape_interval: 30s

  - job_name: 'nginx'
    static_configs:
      - targets: ['nginx:80']
    metrics_path: '/nginx_status'
    scrape_interval: 30s

  - job_name: 'mysql'
    static_configs:
      - targets: ['mysql:3306']
    scrape_interval: 60s

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']
    scrape_interval: 30s
EOF
    chown $VOLUME_USER:$VOLUME_GROUP "$VOLUMES_DIR/prometheus/config/prometheus.yml"
    chmod 644 "$VOLUMES_DIR/prometheus/config/prometheus.yml"
fi

# =============================================================================
# ARCHIVOS DE MARCADOR
# =============================================================================

echo ""
echo "🏷️  Creando archivos de marcador..."

# Crear archivos .gitkeep para mantener los directorios en Git
find "$VOLUMES_DIR" -type d -empty -exec touch {}/.gitkeep \;

# Crear archivo de información del volumen
cat > "$VOLUMES_DIR/README.md" << 'EOF'
# Volúmenes Externos - Sistema de Paquetería v1.1

Este directorio contiene todos los volúmenes externos para garantizar la persistencia de datos.

## Estructura de Volúmenes

### Datos Críticos (CRÍTICO)
- `mysql/data/` - Datos de la base de datos MySQL
- `redis/data/` - Datos de cache Redis
- `uploads/` - Archivos subidos por usuarios
- `backups/` - Backups de la base de datos
- `prometheus/data/` - Métricas de monitoreo
- `grafana/data/` - Dashboards y configuraciones de Grafana

### Logs
- `logs/` - Logs de la aplicación
- `mysql/logs/` - Logs de MySQL
- `redis/logs/` - Logs de Redis
- `nginx/logs/` - Logs de Nginx
- `prometheus/logs/` - Logs de Prometheus
- `grafana/logs/` - Logs de Grafana
- `flower/logs/` - Logs de Flower

### Configuración
- `config/` - Configuración de la aplicación
- `mysql/config/` - Configuración de MySQL
- `redis/config/` - Configuración de Redis
- `nginx/config/` - Configuración de Nginx
- `prometheus/config/` - Configuración de Prometheus
- `grafana/config/` - Configuración de Grafana

### Otros
- `ssl/` - Certificados SSL
- `static/` - Archivos estáticos
- `celery/temp/` - Archivos temporales de Celery

## Backup y Restauración

Para hacer backup de los datos críticos:

```bash
# Backup de MySQL
docker-compose exec mysql mysqldump -u root -p paqueteria > backup_$(date +%Y%m%d_%H%M%S).sql

# Backup de volúmenes
tar -czf volumes_backup_$(date +%Y%m%d_%H%M%S).tar.gz volumes/
```

## Permisos

Los volúmenes están configurados con los siguientes permisos:
- Datos críticos: 750 (más restrictivos)
- Logs y configuración: 755 (estándar)

## Notas Importantes

- NO eliminar estos directorios sin hacer backup
- Los datos persisten entre reinicios de contenedores
- En caso de problemas, solo ejecutar `docker-compose down && docker-compose up -d`
EOF

chown $VOLUME_USER:$VOLUME_GROUP "$VOLUMES_DIR/README.md"
chmod 644 "$VOLUMES_DIR/README.md"

# =============================================================================
# VERIFICACIÓN FINAL
# =============================================================================

echo ""
echo "✅ Verificando estructura de volúmenes..."

# Verificar que todos los directorios existen
for dir in \
    "$VOLUMES_DIR/mysql/data" \
    "$VOLUMES_DIR/mysql/logs" \
    "$VOLUMES_DIR/mysql/config" \
    "$VOLUMES_DIR/redis/data" \
    "$VOLUMES_DIR/redis/logs" \
    "$VOLUMES_DIR/redis/config" \
    "$VOLUMES_DIR/logs" \
    "$VOLUMES_DIR/uploads" \
    "$VOLUMES_DIR/config" \
    "$VOLUMES_DIR/ssl" \
    "$VOLUMES_DIR/nginx/config" \
    "$VOLUMES_DIR/nginx/logs" \
    "$VOLUMES_DIR/nginx/ssl" \
    "$VOLUMES_DIR/static" \
    "$VOLUMES_DIR/celery/temp" \
    "$VOLUMES_DIR/flower/logs" \
    "$VOLUMES_DIR/prometheus/config" \
    "$VOLUMES_DIR/prometheus/data" \
    "$VOLUMES_DIR/prometheus/logs" \
    "$VOLUMES_DIR/grafana/data" \
    "$VOLUMES_DIR/grafana/config" \
    "$VOLUMES_DIR/grafana/logs" \
    "$VOLUMES_DIR/backups"; do
    
    if [ -d "$dir" ]; then
        echo "   ✅ $dir"
    else
        echo "   ❌ $dir (FALTANTE)"
        exit 1
    fi
done

# =============================================================================
# RESUMEN
# =============================================================================

echo ""
echo "🎉 ¡Inicialización de volúmenes completada!"
echo ""
echo "📊 Resumen:"
echo "   📁 Directorios creados: $(find $VOLUMES_DIR -type d | wc -l)"
echo "   📄 Archivos de configuración: $(find $VOLUMES_DIR -name "*.conf" -o -name "*.yml" | wc -l)"
echo "   💾 Espacio total: $(du -sh $VOLUMES_DIR | cut -f1)"
echo ""
echo "🚀 Próximos pasos:"
echo "   1. Ejecutar: docker-compose up -d"
echo "   2. Verificar logs: docker-compose logs -f"
echo "   3. Acceder a la aplicación: http://localhost:8000"
echo ""
echo "💡 Nota: Los datos ahora persisten entre reinicios de contenedores."
echo "   En caso de problemas, solo ejecutar: docker-compose down && docker-compose up -d"
