import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database configuration - supports both Render and local deployment
    # Priority: Render's DATABASE_URL > Neon DATABASE_URL > SQLite fallback
    DATABASE_URL = os.environ.get('DATABASE_URL')
    NEON_DATABASE_URL = os.environ.get('NEON_DATABASE_URL') or 'postgresql://neondb_owner:npg_jdJ2nNyM8mXs@ep-super-heart-abaksv5y-pooler.eu-west-2.aws.neon.tech/neondb?sslmode=require'
    
    if DATABASE_URL:
        # For Render deployment
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
    elif NEON_DATABASE_URL:
        # For local development with Neon
        SQLALCHEMY_DATABASE_URI = NEON_DATABASE_URL
    else:
        # Fallback to SQLite for testing
        SQLALCHEMY_DATABASE_URI = 'sqlite:///staff_management.db'
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Connection pool settings for PostgreSQL
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
    }
    
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max file size
    
    # Folder paths
    STAFF_IMAGES_FOLDER = os.path.join(UPLOAD_FOLDER, 'staff_images')
    STAFF_SIGNATURES_FOLDER = os.path.join(UPLOAD_FOLDER, 'staff_signatures')
    CLEAN_SIGNATURES_FOLDER = os.path.join(UPLOAD_FOLDER, 'staff_signatures_clean')
    
    # Static URL paths for serving files
    STAFF_IMAGES_URL = '/uploads/staff_images'
    STAFF_SIGNATURES_URL = '/uploads/staff_signatures'
    CLEAN_SIGNATURES_URL = '/uploads/staff_signatures_clean'
    
    # Allowed file extensions
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}
    
    # ==================== CLOUDINARY CONFIGURATION ====================
    # Cloudinary cloud name (get from https://cloudinary.com)
    CLOUDINARY_CLOUD_NAME = os.environ.get('CLOUDINARY_CLOUD_NAME')
    CLOUDINARY_API_KEY = os.environ.get('CLOUDINARY_API_KEY')
    CLOUDINARY_API_SECRET = os.environ.get('CLOUDINARY_API_SECRET')