# =============================================================================
# DOCKERFILE - Sistema de Paquetería v1.1
# =============================================================================

# Etapa de construcción
FROM python:3.11-slim as builder

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio de trabajo
WORKDIR /app

# Copiar archivos de dependencias
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir --user -r requirements.txt

# =============================================================================
# Etapa de producción
# =============================================================================
FROM python:3.11-slim as production

# Instalar dependencias del sistema para producción
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Crear usuario no-root para seguridad
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Crear directorio de trabajo
WORKDIR /app

# Copiar dependencias instaladas desde la etapa de construcción
COPY --from=builder /root/.local /home/appuser/.local

# Copiar código fuente
COPY src/ ./src/
COPY scripts/ ./scripts/

# Crear directorios necesarios
RUN mkdir -p logs uploads static templates \
    && chown -R appuser:appuser /app

# Cambiar al usuario no-root
USER appuser

# Agregar el directorio local de Python al PATH
ENV PATH=/home/appuser/.local/bin:$PATH

# Variables de entorno por defecto
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Exponer puerto
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Comando por defecto
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

# =============================================================================
# Etapa de desarrollo (opcional)
# =============================================================================
FROM python:3.11-slim as development

# Instalar dependencias del sistema para desarrollo
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    curl \
    git \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio de trabajo
WORKDIR /app

# Copiar archivos de dependencias
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Variables de entorno para desarrollo
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV DEBUG=True

# Exponer puerto
EXPOSE 8000

# Comando por defecto para desarrollo
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
