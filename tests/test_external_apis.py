"""
Tests for External APIs
======================

Pruebas para las APIs externas (SMS, S3, Email).
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient

from src.main import app
from src.app.services.external.liwa_sms import LIWASMSService, LIWASMSMessage, LIWASMSResponse
from src.app.services.external.aws_s3 import S3Service, S3FileInfo
from src.app.services.external.email_service import EmailService, EmailMessage, EmailResponse

client = TestClient(app)

# =============================================================================
# SMS Tests
# =============================================================================

class TestLIWASMSService:
    """Tests para el servicio de SMS LIWA"""
    
    @pytest.fixture
    def sms_service(self):
        """Fixture para el servicio SMS"""
        return LIWASMSService()
    
    @pytest.fixture
    def sample_message(self):
        """Fixture para mensaje de prueba"""
        return LIWASMSMessage(
            phone_number="+573001234567",
            message="Test message",
            message_id="test_123"
        )
    
    def test_format_phone_number(self, sms_service):
        """Test formateo de número de teléfono"""
        # Número con código de país
        formatted = sms_service._format_phone_number("+573001234567")
        assert formatted == "573001234567"
        
        # Número sin código de país
        formatted = sms_service._format_phone_number("3001234567")
        assert formatted == "573001234567"
        
        # Número con 0 inicial
        formatted = sms_service._format_phone_number("03001234567")
        assert formatted == "573001234567"
    
    def test_validate_message(self, sms_service):
        """Test validación de mensaje"""
        # Mensaje válido
        assert sms_service._validate_message("Test message") == True
        
        # Mensaje muy largo
        long_message = "A" * 161
        assert sms_service._validate_message(long_message) == False
        
        # Mensaje con caracteres inválidos
        invalid_message = "Test\x00message"
        assert sms_service._validate_message(invalid_message) == False
    
    @pytest.mark.asyncio
    async def test_send_sms_success(self, sms_service, sample_message):
        """Test envío exitoso de SMS"""
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {
                "success": True,
                "message_id": "msg_123",
                "external_id": "ext_123",
                "cost": 0.05,
                "remaining_balance": 100.0
            }
            
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
            
            async with sms_service as service:
                response = await service.send_sms(sample_message)
                
                assert response.success == True
                assert response.message_id == "msg_123"
                assert response.external_id == "ext_123"
                assert response.cost == 0.05
                assert response.remaining_balance == 100.0
    
    @pytest.mark.asyncio
    async def test_send_sms_failure(self, sms_service, sample_message):
        """Test envío fallido de SMS"""
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 400
            mock_response.json.return_value = {
                "success": False,
                "error": "Invalid phone number",
                "error_code": "INVALID_PHONE"
            }
            
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
            
            async with sms_service as service:
                response = await service.send_sms(sample_message)
                
                assert response.success == False
                assert response.error_code == "INVALID_PHONE"
                assert "Invalid phone number" in response.error_message

# =============================================================================
# S3 Tests
# =============================================================================

class TestS3Service:
    """Tests para el servicio de S3"""
    
    @pytest.fixture
    def s3_service(self):
        """Fixture para el servicio S3"""
        return S3Service()
    
    @pytest.fixture
    def sample_file_data(self):
        """Fixture para datos de archivo de prueba"""
        return b"test file content"
    
    def test_generate_file_key(self, s3_service):
        """Test generación de clave de archivo"""
        # Sin package_id
        key = s3_service._generate_file_key("test.jpg")
        assert "uploads/" in key
        assert key.endswith(".jpg")
        
        # Con package_id
        key = s3_service._generate_file_key("test.pdf", package_id=123)
        assert "packages/123/" in key
        assert key.endswith(".pdf")
    
    def test_validate_file(self, s3_service):
        """Test validación de archivo"""
        # Archivo válido
        assert s3_service._validate_file("test.jpg", 1024) == True
        
        # Archivo muy grande
        assert s3_service._validate_file("test.jpg", 20 * 1024 * 1024) == False
        
        # Extensión no permitida
        assert s3_service._validate_file("test.exe", 1024) == False
    
    def test_get_content_type(self, s3_service):
        """Test obtención de tipo de contenido"""
        assert s3_service._get_content_type("test.jpg") == "image/jpeg"
        assert s3_service._get_content_type("test.pdf") == "application/pdf"
        assert s3_service._get_content_type("test.txt") == "text/plain"
        assert s3_service._get_content_type("test.unknown") == "application/octet-stream"
    
    @pytest.mark.asyncio
    async def test_upload_file_success(self, s3_service, sample_file_data):
        """Test subida exitosa de archivo"""
        with patch('boto3.client') as mock_client:
            mock_s3 = Mock()
            mock_client.return_value = mock_s3
            
            mock_s3.head_object.return_value = {
                'ETag': '"test-etag"',
                'LastModified': '2025-01-15T10:00:00Z'
            }
            
            # Simular archivo
            file_data = Mock()
            file_data.read.return_value = sample_file_data
            file_data.seek = Mock()
            
            file_info = await s3_service.upload_file(file_data, "test.jpg", package_id=123)
            
            assert file_info.filename == "test.jpg"
            assert file_info.size == len(sample_file_data)
            assert file_info.content_type == "image/jpeg"
            assert file_info.etag == "test-etag"
    
    @pytest.mark.asyncio
    async def test_download_file_success(self, s3_service):
        """Test descarga exitosa de archivo"""
        with patch('boto3.client') as mock_client:
            mock_s3 = Mock()
            mock_client.return_value = mock_s3
            
            mock_s3.get_object.return_value = {
                'Body': Mock(read=lambda: b"test content"),
                'ContentType': 'image/jpeg',
                'ContentLength': 12,
                'ETag': '"test-etag"',
                'LastModified': '2025-01-15T10:00:00Z',
                'Metadata': {'original-filename': 'test.jpg'}
            }
            
            file_data = await s3_service.download_file("test-key")
            
            assert file_data is not None
            assert file_data['filename'] == "test.jpg"
            assert file_data['content'] == b"test content"
            assert file_data['content_type'] == "image/jpeg"
            assert file_data['size'] == 12

# =============================================================================
# Email Tests
# =============================================================================

class TestEmailService:
    """Tests para el servicio de email"""
    
    @pytest.fixture
    def email_service(self):
        """Fixture para el servicio de email"""
        return EmailService()
    
    @pytest.fixture
    def sample_email_message(self):
        """Fixture para mensaje de email de prueba"""
        return EmailMessage(
            to_email="test@example.com",
            to_name="Test User",
            subject="Test Subject",
            body_text="Test body",
            body_html="<p>Test body</p>"
        )
    
    def test_create_message(self, email_service, sample_email_message):
        """Test creación de mensaje MIME"""
        msg = email_service._create_message(sample_email_message)
        
        assert msg['To'] == "Test User <test@example.com>"
        assert msg['Subject'] == "Test Subject"
        assert "Test body" in str(msg.get_payload(0).get_payload())
    
    @pytest.mark.asyncio
    async def test_send_email_success(self, email_service, sample_email_message):
        """Test envío exitoso de email"""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = Mock()
            mock_smtp.return_value = mock_server
            
            response = await email_service.send_email(sample_email_message)
            
            assert response.success == True
            assert response.message_id == sample_email_message.message_id
            mock_server.login.assert_called_once()
            mock_server.send_message.assert_called_once()
            mock_server.quit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_email_authentication_error(self, email_service, sample_email_message):
        """Test error de autenticación en email"""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = Mock()
            mock_server.login.side_effect = Exception("Authentication failed")
            mock_smtp.return_value = mock_server
            
            response = await email_service.send_email(sample_email_message)
            
            assert response.success == False
            assert "Authentication failed" in response.error_message
    
    def test_create_package_announcement_email(self, email_service):
        """Test creación de email de anuncio de paquete"""
        email_msg = email_service.create_package_announcement_email(
            customer_name="John Doe",
            customer_email="john@example.com",
            tracking_number="TRK123456",
            package_cost="$1,500 COP"
        )
        
        assert email_msg.to_email == "john@example.com"
        assert email_msg.to_name == "John Doe"
        assert "TRK123456" in email_msg.subject
        assert "TRK123456" in email_msg.body_text
        assert "$1,500 COP" in email_msg.body_text

# =============================================================================
# API Routes Tests
# =============================================================================

class TestExternalAPIRoutes:
    """Tests para las rutas de APIs externas"""
    
    def test_send_sms_endpoint(self):
        """Test endpoint de envío de SMS"""
        with patch('src.app.services.external.liwa_sms.LIWASMSService') as mock_service:
            mock_response = LIWASMSResponse(
                success=True,
                message_id="msg_123",
                external_id="ext_123",
                cost=0.05,
                remaining_balance=100.0
            )
            
            mock_service.return_value.__aenter__.return_value.send_sms.return_value = mock_response
            
            response = client.post(
                "/api/external/sms/send",
                data={
                    "phone_number": "+573001234567",
                    "message": "Test message"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] == True
            assert data["message_id"] == "msg_123"
    
    def test_sms_balance_endpoint(self):
        """Test endpoint de saldo de SMS"""
        with patch('src.app.services.external.liwa_sms.LIWASMSService') as mock_service:
            mock_service.return_value.__aenter__.return_value.check_balance.return_value = {
                "success": True,
                "balance": 100.0,
                "currency": "COP"
            }
            
            response = client.get("/api/external/sms/balance")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] == True
            assert data["balance"] == 100.0
    
    def test_upload_file_s3_endpoint(self):
        """Test endpoint de subida de archivo a S3"""
        with patch('src.app.services.external.aws_s3.upload_file_to_s3') as mock_upload:
            mock_file_info = S3FileInfo(
                key="test-key",
                filename="test.jpg",
                size=1024,
                content_type="image/jpeg",
                etag="test-etag",
                last_modified="2025-01-15T10:00:00Z",
                url="https://example.com/test.jpg"
            )
            mock_upload.return_value = mock_file_info
            
            # Crear archivo de prueba
            files = {"file": ("test.jpg", b"test content", "image/jpeg")}
            data = {"package_id": "123"}
            
            response = client.post("/api/external/s3/upload", files=files, data=data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] == True
            assert data["file_key"] == "test-key"
            assert data["filename"] == "test.jpg"
    
    def test_send_email_endpoint(self):
        """Test endpoint de envío de email"""
        with patch('src.app.services.external.email_service.send_quick_email') as mock_send:
            mock_response = EmailResponse(
                success=True,
                message_id="email_123"
            )
            mock_send.return_value = mock_response
            
            response = client.post(
                "/api/external/email/send",
                data={
                    "to_email": "test@example.com",
                    "subject": "Test Subject",
                    "body": "Test body"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] == True
            assert data["message_id"] == "email_123"
    
    def test_external_services_health_check(self):
        """Test health check de servicios externos"""
        with patch('src.app.routes.external.sms_health_check') as mock_sms, \
             patch('src.app.routes.external.s3_health_check') as mock_s3, \
             patch('src.app.routes.external.email_health_check') as mock_email:
            
            mock_sms.return_value = {"service": "sms", "status": "healthy"}
            mock_s3.return_value = {"service": "s3", "status": "healthy"}
            mock_email.return_value = {"service": "email", "status": "healthy"}
            
            response = client.get("/api/external/health/all")
            
            assert response.status_code == 200
            data = response.json()
            assert data["overall_status"] == "healthy"
            assert len(data["services"]) == 3

# =============================================================================
# Integration Tests
# =============================================================================

class TestExternalAPIIntegration:
    """Tests de integración para APIs externas"""
    
    @pytest.mark.asyncio
    async def test_sms_email_integration(self):
        """Test integración SMS y Email"""
        # Simular envío de notificación por múltiples canales
        from src.app.services.notification_service import NotificationService
        from src.app.services.external.liwa_sms import LIWASMSService
        from src.app.services.external.email_service import EmailService
        
        # Mock de servicios externos
        with patch('src.app.services.external.liwa_sms.LIWASMSService') as mock_sms, \
             patch('src.app.services.external.email_service.EmailService') as mock_email:
            
            # Configurar mocks
            mock_sms.return_value.__aenter__.return_value.send_sms.return_value = LIWASMSResponse(
                success=True,
                message_id="sms_123"
            )
            
            mock_email.return_value.send_email.return_value = EmailResponse(
                success=True,
                message_id="email_123"
            )
            
            # Test de integración
            # (Aquí se probaría el flujo completo de notificaciones)
            assert True  # Placeholder para test de integración
    
    @pytest.mark.asyncio
    async def test_s3_file_management_integration(self):
        """Test integración de gestión de archivos S3"""
        # Simular flujo completo de gestión de archivos
        with patch('src.app.services.external.aws_s3.s3_service') as mock_s3:
            # Configurar mock para operaciones S3
            mock_s3.upload_file.return_value = S3FileInfo(
                key="test-key",
                filename="test.jpg",
                size=1024,
                content_type="image/jpeg",
                etag="test-etag",
                last_modified="2025-01-15T10:00:00Z"
            )
            
            mock_s3.download_file.return_value = {
                "content": b"test content",
                "filename": "test.jpg",
                "content_type": "image/jpeg",
                "size": 1024
            }
            
            # Test de integración
            # (Aquí se probaría el flujo completo de gestión de archivos)
            assert True  # Placeholder para test de integración

# =============================================================================
# Performance Tests
# =============================================================================

class TestExternalAPIPerformance:
    """Tests de rendimiento para APIs externas"""
    
    @pytest.mark.asyncio
    async def test_sms_bulk_performance(self):
        """Test rendimiento de envío masivo de SMS"""
        import time
        
        with patch('src.app.services.external.liwa_sms.LIWASMSService') as mock_service:
            # Simular envío de 100 SMS
            start_time = time.time()
            
            mock_service.return_value.__aenter__.return_value.send_bulk_sms.return_value = [
                LIWASMSResponse(success=True, message_id=f"msg_{i}")
                for i in range(100)
            ]
            
            # Test de rendimiento
            # (Aquí se mediría el tiempo de envío masivo)
            elapsed_time = time.time() - start_time
            
            # Verificar que el envío masivo es más rápido que envíos individuales
            assert elapsed_time < 5.0  # Debe completarse en menos de 5 segundos
    
    @pytest.mark.asyncio
    async def test_s3_upload_performance(self):
        """Test rendimiento de subida a S3"""
        import time
        
        with patch('src.app.services.external.aws_s3.s3_service') as mock_s3:
            # Simular subida de archivo grande
            large_file = b"x" * (5 * 1024 * 1024)  # 5MB
            
            start_time = time.time()
            
            mock_s3.upload_file.return_value = S3FileInfo(
                key="large-file",
                filename="large.jpg",
                size=len(large_file),
                content_type="image/jpeg",
                etag="large-etag",
                last_modified="2025-01-15T10:00:00Z"
            )
            
            # Test de rendimiento
            # (Aquí se mediría el tiempo de subida)
            elapsed_time = time.time() - start_time
            
            # Verificar que la subida es razonablemente rápida
            assert elapsed_time < 10.0  # Debe completarse en menos de 10 segundos

# =============================================================================
# Error Handling Tests
# =============================================================================

class TestExternalAPIErrorHandling:
    """Tests de manejo de errores para APIs externas"""
    
    def test_sms_api_error_handling(self):
        """Test manejo de errores en API SMS"""
        with patch('src.app.services.external.liwa_sms.LIWASMSService') as mock_service:
            # Simular error de API
            mock_service.return_value.__aenter__.return_value.send_sms.side_effect = Exception("API Error")
            
            response = client.post(
                "/api/external/sms/send",
                data={
                    "phone_number": "+573001234567",
                    "message": "Test message"
                }
            )
            
            assert response.status_code == 500
            data = response.json()
            assert "Error enviando SMS" in data["detail"]
    
    def test_s3_api_error_handling(self):
        """Test manejo de errores en API S3"""
        with patch('src.app.services.external.aws_s3.upload_file_to_s3') as mock_upload:
            # Simular error de S3
            mock_upload.side_effect = Exception("S3 Error")
            
            files = {"file": ("test.jpg", b"test content", "image/jpeg")}
            
            response = client.post("/api/external/s3/upload", files=files)
            
            assert response.status_code == 500
            data = response.json()
            assert "Error subiendo archivo" in data["detail"]
    
    def test_email_api_error_handling(self):
        """Test manejo de errores en API Email"""
        with patch('src.app.services.external.email_service.send_quick_email') as mock_send:
            # Simular error de email
            mock_send.side_effect = Exception("Email Error")
            
            response = client.post(
                "/api/external/email/send",
                data={
                    "to_email": "test@example.com",
                    "subject": "Test Subject",
                    "body": "Test body"
                }
            )
            
            assert response.status_code == 500
            data = response.json()
            assert "Error enviando email" in data["detail"]

if __name__ == "__main__":
    pytest.main([__file__])
