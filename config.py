import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # PostgreSQL Database URI (Neon)
    # You can also use environment variable: DATABASE_URL
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'postgresql://neondb_owner:npg_jdJ2nNyM8mXs@ep-super-heart-abaksv5y-pooler.eu-west-2.aws.neon.tech/neondb?sslmode=require'
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Connection pool settings for PostgreSQL
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
    }
    
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max file size (increased for images)
    
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