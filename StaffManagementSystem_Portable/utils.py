import os
import re
import io
import base64
import gdown
import pandas as pd
from PIL import Image, ImageEnhance
from werkzeug.utils import secure_filename
from flask import current_app
from werkzeug.security import generate_password_hash, check_password_hash

def clean_filename(name):
    """Clean filename for saving"""
    name = re.sub(r'[^\w\s-]', '', name)
    return name.strip().replace(' ', '_')

def download_from_google_drive(url):
    """Download file from Google Drive"""
    if not url or pd.isna(url) or str(url).strip() == '':
        return None
    
    url = str(url).strip()
    try:
        file_id = None
        if 'open?id=' in url:
            file_id = url.split('open?id=')[-1].split('&')[0]
        elif '/file/d/' in url:
            file_id = url.split('/file/d/')[1].split('/')[0]
        elif 'uc?id=' in url:
            file_id = url.split('uc?id=')[-1].split('&')[0]
        
        if file_id:
            output = io.BytesIO()
            gdown.download(f"https://drive.google.com/uc?id={file_id}", output, quiet=True)
            output.seek(0)
            return output.getvalue()
    except Exception as e:
        print(f"Download error: {e}")
    return None

def save_image_file(file_bytes, filename, folder):
    """Save image file to disk"""
    if not file_bytes:
        return None
    
    os.makedirs(folder, exist_ok=True)
    filepath = os.path.join(folder, filename)
    
    with open(filepath, 'wb') as f:
        f.write(file_bytes)
    
    return filepath

def save_image_from_data_url(data_url, folder, filename):
    """Save image from data URL to file"""
    if not data_url or not data_url.startswith('data:image'):
        return None
    
    try:
        # Extract base64 data
        header, encoded = data_url.split(',', 1)
        
        # Decode base64
        image_data = base64.b64decode(encoded)
        
        # Save to file
        os.makedirs(folder, exist_ok=True)
        filepath = os.path.join(folder, filename)
        
        with open(filepath, 'wb') as f:
            f.write(image_data)
        
        return filepath
    except Exception as e:
        print(f"Error saving image from data URL: {e}")
        return None

def process_imported_staff(df, admin_name):
    """Process imported staff data"""
    from models import db, Staff, ImportLog
    
    if df.empty:
        return 0, 0, "No data found"
    
    successful = 0
    failed = 0
    errors = []
    
    for idx, row in df.iterrows():
        try:
            # Get basic info
            full_name = None
            for col in ['NAME', 'Full Name', 'name', 'full_name']:
                if col in df.columns and pd.notna(row[col]):
                    full_name = str(row[col])
                    break
            
            email = None
            for col in ['EMAIL', 'Email', 'email']:
                if col in df.columns and pd.notna(row[col]):
                    email = str(row[col])
                    break
            
            phone = None
            for col in ['PHONE NUMBER', 'Phone', 'phone', 'PHONE']:
                if col in df.columns and pd.notna(row[col]):
                    phone = str(row[col])
                    break
            
            if not full_name or not email:
                failed += 1
                errors.append(f"Row {idx+1}: Missing NAME or EMAIL")
                continue
            
            # Check if email exists
            if Staff.query.filter_by(email=email).first():
                failed += 1
                errors.append(f"Row {idx+1}: Email {email} already exists")
                continue
            
            # Get signature URL
            signature_url = None
            for col in ['SIGNATURE', 'Signature', 'signature']:
                if col in df.columns and pd.notna(row[col]):
                    signature_url = row[col]
                    break
            
            # Get image URL
            image_url = None
            for col in ['IMAGE OR PICTURE', 'Photo', 'photo', 'IMAGE', 'image']:
                if col in df.columns and pd.notna(row[col]):
                    image_url = row[col]
                    break
            
            # Download signature
            signature_path = None
            if signature_url:
                sig_bytes = download_from_google_drive(signature_url)
                if sig_bytes:
                    from config import Config
                    filename = f"signature_{full_name}_{idx}.png"
                    signature_path = save_image_file(sig_bytes, filename, Config.STAFF_SIGNATURES_FOLDER)
            
            # Download photo
            image_path = None
            if image_url:
                img_bytes = download_from_google_drive(image_url)
                if img_bytes:
                    from config import Config
                    filename = f"staff_{full_name}_{idx}.png"
                    image_path = save_image_file(img_bytes, filename, Config.STAFF_IMAGES_FOLDER)
            
            # Get other fields
            department = ''
            for col in ['DEPARTMENT', 'Department', 'dept']:
                if col in df.columns and pd.notna(row[col]):
                    department = str(row[col])
                    break
            
            designation = ''
            for col in ['DESIGNATION', 'Designation', 'title']:
                if col in df.columns and pd.notna(row[col]):
                    designation = str(row[col])
                    break
            
            ministry = 'Ministry of Communication'
            for col in ['MINISTRY', 'Ministry', 'ministry']:
                if col in df.columns and pd.notna(row[col]):
                    ministry = str(row[col])
                    break
            
            username = None
            for col in ['USERNAME', 'Username', 'username', 'USENAME']:
                if col in df.columns and pd.notna(row[col]):
                    username = str(row[col])
                    break
            
            password = None
            for col in ['PASSWORD', 'Password', 'password']:
                if col in df.columns and pd.notna(row[col]):
                    password = str(row[col])
                    break
            
            # Create staff record
            staff = Staff(
                full_name=full_name,
                email=email,
                phone_number=phone if phone else '',
                ministry=ministry,
                department=department,
                designation=designation,
                image_path=image_path,
                signature_path=signature_path,
                username=username,
                updated_by=admin_name
            )
            
            if password:
                staff.set_password(password)
            
            db.session.add(staff)
            successful += 1
            
        except Exception as e:
            failed += 1
            errors.append(f"Row {idx+1}: {str(e)}")
    
    # Save import log
    log = ImportLog(
        filename=f"import_{admin_name}_{pd.Timestamp.now()}",
        records_imported=successful,
        records_failed=failed,
        imported_by=admin_name,
        error_log='\n'.join(errors[:20]) if errors else None
    )
    db.session.add(log)
    db.session.commit()
    
    return successful, failed, errors

def init_db():
    """Initialize database with default admin users for PostgreSQL"""
    from models import db, Admin
    
    try:
        # Check if any admin exists
        if Admin.query.count() == 0:
            print("📝 Creating default admin users...")
            
            # Create super admin
            super_admin = Admin(
                username='superadmin',
                email='superadmin@system.com',
                full_name='Super Administrator',
                role='super_admin'
            )
            super_admin.set_password('superadmin123')
            db.session.add(super_admin)
            
            # Create regular admin
            admin = Admin(
                username='admin',
                email='admin@system.com',
                full_name='System Administrator',
                role='admin'
            )
            admin.set_password('admin123')
            db.session.add(admin)
            
            db.session.commit()
            print("✅ Default admin users created successfully!")
            print("   - Username: superadmin | Password: superadmin123")
            print("   - Username: admin | Password: admin123")
        else:
            print("✅ Admin users already exist")
            
    except Exception as e:
        print(f"❌ Error creating admin users: {e}")
        db.session.rollback()