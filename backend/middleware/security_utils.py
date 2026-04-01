"""
Security utilities for MediOrbit backend.
Implements HIPAA compliance checks, input validation, and data protection.
"""

import re
from typing import Tuple, Dict, Any
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class SecurityLevel(Enum):
    """Security classification levels"""
    PUBLIC = "public"
    PROTECTED = "protected"  # Medical data
    RESTRICTED = "restricted"  # Patient PII
    CONFIDENTIAL = "confidential"  # Highly sensitive

class SecurityValidator:
    """Validates requests and responses against security policies"""
    
    def __init__(self):
        self.max_input_length = 5000
        self.max_file_size = 50 * 1024 * 1024  # 50MB
        self.allowed_file_types = {'.pdf', '.jpg', '.jpeg', '.png', '.txt', '.dcm'}
        
    def validate_user_input(self, user_input: str) -> Tuple[bool, str]:
        """
        Validate user input for injection attacks and malicious content
        Returns: (is_valid, error_message)
        """
        # Length check
        if len(user_input) > self.max_input_length:
            return False, f"Input exceeds maximum length of {self.max_input_length} characters"
        
        # SQL injection patterns
        sql_injection_patterns = [
            r"(\bDROP\b|\bDELETE\b|\bEXEC\b|\bSCRIPT\b|\bUNION\b)",
            r"--\s*$",
            r"/\*.*\*/",
            r";\s*(DROP|DELETE|ALTER|EXEC)",
        ]
        
        for pattern in sql_injection_patterns:
            if re.search(pattern, user_input, re.IGNORECASE):
                logger.warning(f"Potential SQL injection detected: {user_input[:50]}")
                return False, "Invalid input detected. Please check your query."
        
        # XSS patterns
        xss_patterns = [
            r"<\s*script|javascript:",
            r"on\w+\s*=",  # Event handlers
            r"<\s*iframe",
        ]
        
        for pattern in xss_patterns:
            if re.search(pattern, user_input, re.IGNORECASE):
                logger.warning(f"Potential XSS detected: {user_input[:50]}")
                return False, "Invalid input format detected."
        
        return True, ""
    
    def validate_file_upload(self, filename: str, file_size: int) -> Tuple[bool, str]:
        """
        Validate file uploads for security
        Returns: (is_valid, error_message)
        """
        # Check file size
        if file_size > self.max_file_size:
            return False, f"File size exceeds maximum of {self.max_file_size / (1024*1024):.0f}MB"
        
        # Check file extension
        file_ext = '.' + filename.split('.')[-1].lower() if '.' in filename else ''
        if file_ext not in self.allowed_file_types:
            return False, f"File type {file_ext} is not allowed. Allowed types: {self.allowed_file_types}"
        
        # Check for path traversal
        if '..' in filename or '/' in filename or '\\' in filename:
            return False, "Invalid filename"
        
        return True, ""
    
    def sanitize_output(self, text: str, security_level: SecurityLevel = SecurityLevel.PUBLIC) -> str:
        """
        Sanitize output based on security level
        Removes sensitive data patterns
        """
        if security_level == SecurityLevel.CONFIDENTIAL:
            # Aggressive sanitization
            text = re.sub(r'\b\d{3}[-.]?\d{2}[-.]?\d{4}\b', '[SSN]', text)  # SSN
            text = re.sub(r'\b\d{16}\b', '[CARD]', text)  # Credit card
            text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]', text)  # Phone
            text = re.sub(r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b', '[EMAIL]', text, flags=re.IGNORECASE)  # Email
        
        return text
    
    def validate_api_key(self, api_key: str) -> bool:
        """Validate API key format"""
        if not api_key or len(api_key) < 20:
            return False
        return True
    
    def check_rate_limit(self, user_id: str, limit: int = 30, window: int = 60) -> bool:
        """
        Check if user is within rate limits
        Note: This is a placeholder. In production, use Redis or similar
        """
        # TODO: Implement with Redis or database
        return True
    
    def log_security_event(self, event_type: str, details: Dict[str, Any]):
        """Log security-relevant events"""
        logger.warning(f"SECURITY EVENT: {event_type} - {details}")

class DataProtection:
    """Implements data protection and HIPAA-like compliance"""
    
    @staticmethod
    def mask_patient_data(text: str) -> str:
        """Remove or mask personally identifiable information"""
        # Mask names (simple pattern - in production use NER)
        masked = re.sub(r'\b[A-Z][a-z]+ [A-Z][a-z]+\b', '[PATIENT_NAME]', text)
        
        # Mask dates of birth
        masked = re.sub(r'\b(0[1-9]|[12]\d|3[01])[-/](0[1-9]|1[012])[-/](\d{4})\b', '[DOB]', masked)
        
        # Mask medical record numbers
        masked = re.sub(r'\bMR\s*#?\s*\d+\b', '[MRN]', masked, flags=re.IGNORECASE)
        
        return masked
    
    @staticmethod
    def validate_data_access(user_role: str, data_classification: SecurityLevel) -> bool:
        """Check if user role has access to data classification"""
        access_matrix = {
            'admin': [SecurityLevel.CONFIDENTIAL, SecurityLevel.RESTRICTED, SecurityLevel.PROTECTED, SecurityLevel.PUBLIC],
            'doctor': [SecurityLevel.PROTECTED, SecurityLevel.PUBLIC],
            'patient': [SecurityLevel.PROTECTED, SecurityLevel.PUBLIC],
            'guest': [SecurityLevel.PUBLIC],
        }
        
        allowed_levels = access_matrix.get(user_role, [SecurityLevel.PUBLIC])
        return data_classification in allowed_levels

# Initialize singleton
security_validator = SecurityValidator()
