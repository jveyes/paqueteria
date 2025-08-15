#!/usr/bin/env python3
"""
Test básico de las APIs externas
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_imports():
    """Test de importaciones básicas"""
    try:
        from app.core.config import settings
        print("✅ Configuración importada correctamente")
        
        from app.services.external.liwa_sms import LIWASMSService
        print("✅ LIWA SMS Service importado correctamente")
        
        from app.services.external.aws_s3 import S3Service
        print("✅ AWS S3 Service importado correctamente")
        
        from app.services.external.email_service import EmailService
        print("✅ Email Service importado correctamente")
        
        return True
    except Exception as e:
        print(f"❌ Error en importaciones: {e}")
        return False

def test_config():
    """Test de configuración"""
    try:
        from app.core.config import settings
        
        print(f"✅ APP_NAME: {settings.APP_NAME}")
        print(f"✅ APP_VERSION: {settings.APP_VERSION}")
        print(f"✅ DEBUG: {settings.DEBUG}")
        print(f"✅ LIWA_ENABLED: {settings.LIWA_ENABLED}")
        print(f"✅ S3_ENABLED: {settings.S3_ENABLED}")
        
        return True
    except Exception as e:
        print(f"❌ Error en configuración: {e}")
        return False

def test_sms_service():
    """Test básico del servicio SMS"""
    try:
        from app.services.external.liwa_sms import LIWASMSService
        
        service = LIWASMSService()
        print("✅ LIWA SMS Service creado correctamente")
        
        # Test de formateo de teléfono
        formatted = service._format_phone_number("3001234567")
        print(f"✅ Formateo de teléfono: 3001234567 -> {formatted}")
        
        # Test de validación de mensaje
        is_valid = service._validate_message("Test message")
        print(f"✅ Validación de mensaje: {is_valid}")
        
        return True
    except Exception as e:
        print(f"❌ Error en SMS Service: {e}")
        return False

def test_s3_service():
    """Test básico del servicio S3"""
    try:
        from app.services.external.aws_s3 import S3Service
        
        service = S3Service()
        print("✅ AWS S3 Service creado correctamente")
        
        # Test de generación de clave de archivo
        file_key = service._generate_file_key("test.jpg", 123)
        print(f"✅ Generación de clave: {file_key}")
        
        return True
    except Exception as e:
        print(f"❌ Error en S3 Service: {e}")
        return False

def main():
    """Función principal"""
    print("🚀 Iniciando tests básicos de APIs externas...\n")
    
    tests = [
        ("Importaciones", test_imports),
        ("Configuración", test_config),
        ("SMS Service", test_sms_service),
        ("S3 Service", test_s3_service),
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
        print("🎉 ¡Todos los tests básicos pasaron!")
        return 0
    else:
        print("⚠️  Algunos tests fallaron")
        return 1

if __name__ == "__main__":
    sys.exit(main())
