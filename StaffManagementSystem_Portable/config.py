import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def get_base_path():
    """Get correct base path whether running as script or compiled EXE"""
    if getattr(sys, 'frozen', False):
        # Running as compiled EXE
        return os.path.dirname(sys.executable)
    else:
        # Running as normal Python script
        return os.path.dirname(os.path.abspath(__file__))

def get_uploads_path():
    """Get uploads folder path (creates if doesn't exist)"""
    base_path = get_base_path()
    uploads_path = os.path.join(base_path, 'uploads')
    os.makedirs(uploads_path, exist_ok=True)
    return uploads_path

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
        # Fallback to SQLite for testing (store in executable directory)
        base_path = get_base_path()
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(base_path, "staff_management.db")}'
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Connection pool settings for PostgreSQL
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
    }
    
    # Upload folders - dynamic path for EXE compatibility
    BASE_DIR = get_base_path()
    UPLOAD_FOLDER = get_uploads_path()
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max file size
    
    # Folder paths (absolute paths for reliability)
    STAFF_IMAGES_FOLDER = os.path.join(UPLOAD_FOLDER, 'staff_images')
    STAFF_SIGNATURES_FOLDER = os.path.join(UPLOAD_FOLDER, 'staff_signatures')
    CLEAN_SIGNATURES_FOLDER = os.path.join(UPLOAD_FOLDER, 'staff_signatures_clean')
    
    # Create all necessary folders
    os.makedirs(STAFF_IMAGES_FOLDER, exist_ok=True)
    os.makedirs(STAFF_SIGNATURES_FOLDER, exist_ok=True)
    os.makedirs(CLEAN_SIGNATURES_FOLDER, exist_ok=True)
    
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
    
    # ==================== EXE COMPATIBILITY SETTINGS ====================
    # Whether running as compiled executable
    IS_COMPILED = getattr(sys, 'frozen', False)
    
    # For debugging - print paths on startup (optional)
    @classmethod
    def print_paths(cls):
        """Print configuration paths for debugging"""
        print(f"Base directory: {cls.BASE_DIR}")
        print(f"Upload folder: {cls.UPLOAD_FOLDER}")
        print(f"Database URL: {cls.SQLALCHEMY_DATABASE_URI[:50]}...")
        print(f"Running as EXE: {cls.IS_COMPILED}")
        print(f"Cloudinary configured: {bool(cls.CLOUDINARY_CLOUD_NAME)}")