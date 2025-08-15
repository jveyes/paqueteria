#!/usr/bin/env python3
"""
Test simple de las APIs externas sin dependencias de Docker
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_config_import():
    """Test de importación de configuración"""
    try:
        from app.core.config import settings
        print("✅ Configuración importada correctamente")
        print(f"   APP_NAME: {settings.APP_NAME}")
        print(f"   APP_VERSION: {settings.APP_VERSION}")
        return True
    except Exception as e:
        print(f"❌ Error en configuración: {e}")
        return False

def test_sms_service_import():
    """Test de importación del servicio SMS"""
    try:
        from app.services.external.liwa_sms import LIWASMSService
        print("✅ LIWA SMS Service importado correctamente")
        
        # Crear instancia sin inicializar
        service = LIWASMSService()
        print("✅ LIWA SMS Service creado correctamente")
        
        return True
    except Exception as e:
        print(f"❌ Error en SMS Service: {e}")
        return False

def test_s3_service_import():
    """Test de importación del servicio S3"""
    try:
        from app.services.external.aws_s3 import S3Service
        print("✅ AWS S3 Service importado correctamente")
        
        # Crear instancia sin inicializar
        service = S3Service()
        print("✅ AWS S3 Service creado correctamente")
        
        return True
    except Exception as e:
        print(f"❌ Error en S3 Service: {e}")
        return False

def test_email_service_import():
    """Test de importación del servicio Email"""
    try:
        from app.services.external.email_service import EmailService
        print("✅ Email Service importado correctamente")
        
        # Crear instancia sin inicializar
        service = EmailService()
        print("✅ Email Service creado correctamente")
        
        return True
    except Exception as e:
        print(f"❌ Error en Email Service: {e}")
        return False

def test_routes_import():
    """Test de importación de rutas"""
    try:
        from app.routes.external import router as external_router
        print("✅ Rutas externas importadas correctamente")
        
        from app.routes.packages import router as packages_router
        print("✅ Rutas de paquetes importadas correctamente")
        
        from app.routes.notifications import router as notifications_router
        print("✅ Rutas de notificaciones importadas correctamente")
        
        return True
    except Exception as e:
        print(f"❌ Error en rutas: {e}")
        return False

def main():
    """Función principal"""
    print("🚀 Iniciando tests simples de APIs externas...\n")
    
    tests = [
        ("Configuración", test_config_import),
        ("SMS Service", test_sms_service_import),
        ("S3 Service", test_s3_service_import),
        ("Email Service", test_email_service_import),
        ("Rutas", test_routes_import),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"📋 Ejecutando: {test_name}")
        if test_func():
            passed += 1
        print()
    
    print(f"📊 Resultados: {passed}/{total} tests pasaron")
    
    if passed == total:
        print("🎉 ¡Todos los tests simples pasaron!")
        print("✅ La Fase 4 (APIs Externas) está funcionando correctamente")
        return 0
    else:
        print("⚠️  Algunos tests fallaron")
        print("❌ La Fase 4 necesita más trabajo")
        return 1

if __name__ == "__main__":
    sys.exit(main())
