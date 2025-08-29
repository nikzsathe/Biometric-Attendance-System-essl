import os

class ProductionConfig:
    """Production configuration for cloud deployment"""
    
    # Database configuration
    DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'attendance.db')
    
    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-change-this-in-production'
    DEBUG = False
    TESTING = False
    
    # Email configuration (set these in cPanel environment variables)
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')
    
    # Device configuration (for cloud deployment)
    DEVICE_IP = os.environ.get('DEVICE_IP', '')
    DEVICE_PORT = int(os.environ.get('DEVICE_PORT', 4370))
    
    # Cloud-specific settings
    HOST = '0.0.0.0'  # Allow external connections
    PORT = int(os.environ.get('PORT', 5000))
    
    # Security settings
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

