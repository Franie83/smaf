from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class Staff(db.Model, UserMixin):
    __tablename__ = 'staff'
    
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    ministry = db.Column(db.String(200), default='Ministry of Communication')
    department = db.Column(db.String(200))
    designation = db.Column(db.String(200))
    image_path = db.Column(db.String(500))
    signature_path = db.Column(db.String(500))
    signature_bg_removed_path = db.Column(db.String(500))
    username = db.Column(db.String(80), unique=True, nullable=True)
    password_hash = db.Column(db.String(200))  # Renamed from 'password' to avoid confusion
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.String(100))
    
    def set_password(self, password):
        """Hash password using werkzeug security"""
        if password:
            self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password using werkzeug security"""
        if self.password_hash:
            return check_password_hash(self.password_hash, password)
        return False
    
    def get_id(self):
        return str(self.id)
    
    def __repr__(self):
        return f'<Staff {self.full_name}>'

class Admin(db.Model, UserMixin):
    __tablename__ = 'admins'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)  # Renamed from 'password'
    email = db.Column(db.String(120), unique=True, nullable=False)
    full_name = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), default='admin')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        """Hash password using werkzeug security"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password using werkzeug security"""
        return check_password_hash(self.password_hash, password)
    
    def is_super_admin(self):
        return self.role == 'super_admin'
    
    def get_id(self):
        return str(self.id)
    
    def __repr__(self):
        return f'<Admin {self.username}>'

class ImportLog(db.Model):
    __tablename__ = 'import_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200))
    records_imported = db.Column(db.Integer)
    records_failed = db.Column(db.Integer)
    import_date = db.Column(db.DateTime, default=datetime.utcnow)
    imported_by = db.Column(db.String(100))
    error_log = db.Column(db.Text)
    
    def __repr__(self):
        return f'<ImportLog {self.filename}>'