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
    department = db.Column(db.String(200))
    designation = db.Column(db.String(200))
    image_path = db.Column(db.String(500))
    signature_path = db.Column(db.String(500))
    signature_bg_removed_path = db.Column(db.String(500))
    signature_bg_removed_url = db.Column(db.String(500))
    username = db.Column(db.String(80), unique=True, nullable=True)
    password_hash = db.Column(db.String(200))
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.String(100))
    
    # ==================== FIELDS ====================
    ed_password = db.Column(db.String(200))  # Hashed version for security
    ed_password_raw = db.Column(db.String(200))  # Plain text version for display to staff
    mda = db.Column(db.String(200))  # Ministry/Department/Agency field
    
    def set_password(self, password):
        """Hash password using werkzeug security"""
        if password:
            self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password using werkzeug security"""
        if self.password_hash:
            return check_password_hash(self.password_hash, password)
        return False
    
    def set_ed_password(self, password):
        """Set ED password - store both hashed and plain text versions"""
        if password:
            # Store hashed version for potential verification
            self.ed_password = generate_password_hash(password)
            # Store plain text version for display to staff
            self.ed_password_raw = password
        else:
            self.ed_password = None
            self.ed_password_raw = None
    
    def check_ed_password(self, password):
        """Check ED password using hashed version"""
        if self.ed_password:
            return check_password_hash(self.ed_password, password)
        return False
    
    def get_ed_password(self):
        """Get plain text ED password for display/copying"""
        return self.ed_password_raw or ""
    
    def get_id(self):
        return str(self.id)
    
    # Add property to maintain backward compatibility with ministry field
    @property
    def ministry(self):
        """Backward compatibility - returns mda instead of ministry"""
        return self.mda
    
    @ministry.setter
    def ministry(self, value):
        """Backward compatibility - sets mda instead of ministry"""
        self.mda = value
    
    def __repr__(self):
        return f'<Staff {self.full_name}>'

class Admin(db.Model, UserMixin):
    __tablename__ = 'admins'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    full_name = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), default='admin')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # ==================== FIELD ====================
    mda = db.Column(db.String(200))  # MDA restriction for admin
    
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

# ==================== MODEL FOR MDA OPTIONS ====================
class MDAOption(db.Model):
    __tablename__ = 'mda_options'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<MDAOption {self.name}>'