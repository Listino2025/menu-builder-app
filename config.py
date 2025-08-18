import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///menubuilder.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Fix per PostgreSQL su Heroku/Vercel che usa postgres:// invece di postgresql://
    @staticmethod
    def fix_database_url(url):
        if url and url.startswith('postgres://'):
            return url.replace('postgres://', 'postgresql://', 1)
        return url
    
    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
    REMEMBER_COOKIE_DURATION = timedelta(days=30)
    
    # Upload configuration
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = 'uploads'
    
    # Security headers
    SECURITY_HEADERS = {
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'SAMEORIGIN',
        'X-XSS-Protection': '1; mode=block',
        'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data: https:; font-src 'self' https://cdn.jsdelivr.net;"
    }

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False
    
    def __init__(self):
        super().__init__()
        # Fix per URL PostgreSQL in produzione
        db_url = os.environ.get('DATABASE_URL')
        if db_url:
            self.SQLALCHEMY_DATABASE_URI = self.fix_database_url(db_url)
        else:
            self.SQLALCHEMY_DATABASE_URI = 'sqlite:///menubuilder.db'

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}