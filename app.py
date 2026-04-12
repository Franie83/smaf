from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, jsonify, send_from_directory
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
import os
import io
import zipfile
import pandas as pd
from datetime import datetime
from PIL import Image, ImageEnhance, ImageFilter
import base64
import numpy as np
import tempfile

# ==================== CLOUDINARY IMPORTS ====================
import cloudinary
import cloudinary.uploader
from config import Config

# ==================== ENVIRONMENT DETECTION ====================
# Set DISABLE_WHATSAPP=true and DISABLE_REMBG=true on Render only
DISABLE_WHATSAPP = os.environ.get('DISABLE_WHATSAPP', 'False').lower() == 'true'
DISABLE_REMBG = os.environ.get('DISABLE_REMBG', 'False').lower() == 'true'

# Initialize Cloudinary if configured
if Config.CLOUDINARY_CLOUD_NAME:
    cloudinary.config(
        cloud_name=Config.CLOUDINARY_CLOUD_NAME,
        api_key=Config.CLOUDINARY_API_KEY,
        api_secret=Config.CLOUDINARY_API_SECRET
    )
    print("✅ Cloudinary configured")
else:
    print("⚠️ Cloudinary not configured - clean signatures will be stored locally only")

# ==================== WHATSAPP IMPORTS (Conditional) ====================
# ==================== WHATSAPP IMPORTS (Conditional) ====================
kit = None
webbrowser = None

if not DISABLE_WHATSAPP:
    try:
        import pywhatkit as kit
        import webbrowser
        print("✅ WhatsApp sharing enabled")
    except ImportError as e:
        print(f"⚠️ Could not import pywhatkit: {e}")
        kit = None
        webbrowser = None
else:
    print("ℹ️ WhatsApp sharing disabled")
# ==================== REMBG IMPORTS (Conditional) ====================
if not DISABLE_REMBG:
    try:
        from rembg import remove
        from rembg.session_factory import new_session
        REMBG_AVAILABLE = True
        rembg_session = new_session("u2net")
        print("✅ rembg loaded successfully")
    except Exception as e:
        REMBG_AVAILABLE = False
        print(f"❌ rembg not available: {e}")
        def remove(x, session=None):
            return x
else:
    REMBG_AVAILABLE = False
    print("ℹ️ rembg disabled for this environment")
    def remove(x, session=None):
        return x

from config import Config
from models import db, Staff, Admin, ImportLog
from utils import process_imported_staff, download_from_google_drive, save_image_file, clean_filename, init_db

app = Flask(__name__)
app.config.from_object(Config)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'staff_login'

# Create upload folders
os.makedirs(Config.STAFF_IMAGES_FOLDER, exist_ok=True)
os.makedirs(Config.STAFF_SIGNATURES_FOLDER, exist_ok=True)
os.makedirs(Config.CLEAN_SIGNATURES_FOLDER, exist_ok=True)
os.makedirs('temp', exist_ok=True)

@login_manager.user_loader
def load_user(user_id):
    user = db.session.get(Staff, int(user_id))
    if user:
        return user
    return db.session.get(Admin, int(user_id))

def save_image_from_data_url(data_url, folder, filename):
    """Save image from data URL to file"""
    if not data_url or not data_url.startswith('data:image'):
        return None
    
    try:
        header, encoded = data_url.split(',', 1)
        image_data = base64.b64decode(encoded)
        os.makedirs(folder, exist_ok=True)
        filepath = os.path.join(folder, filename)
        with open(filepath, 'wb') as f:
            f.write(image_data)
        return filepath
    except Exception as e:
        print(f"Error saving image from data URL: {e}")
        return None

# ==================== BACKGROUND REMOVAL FUNCTIONS ====================

def remove_signature_background_rembg(image_path, output_path):
    """Remove background using rembg AI"""
    if not REMBG_AVAILABLE:
        print("❌ rembg not available - background removal skipped")
        return False
    
    try:
        with open(image_path, 'rb') as f:
            input_image = f.read()
        
        output_image = remove(input_image, session=rembg_session)
        
        with open(output_path, 'wb') as f:
            f.write(output_image)
        
        # Open and enhance the result
        img = Image.open(output_path)
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # Enhance contrast to make signature darker
        rgb = img.convert('RGB')
        enhancer = ImageEnhance.Contrast(rgb)
        rgb = enhancer.enhance(1.5)
        enhancer = ImageEnhance.Sharpness(rgb)
        rgb = enhancer.enhance(2.0)
        
        # Combine with alpha
        result = Image.new('RGBA', rgb.size)
        result.paste(rgb, (0, 0))
        result.putalpha(img.split()[-1])
        
        # Crop to content
        bbox = result.getbbox()
        if bbox:
            padding = 10
            left = max(0, bbox[0] - padding)
            top = max(0, bbox[1] - padding)
            right = min(result.width, bbox[2] + padding)
            bottom = min(result.height, bbox[3] + padding)
            result = result.crop((left, top, right, bottom))
        
        result.save(output_path, 'PNG')
        return True
        
    except Exception as e:
        print(f"Rembg error: {e}")
        return False

def make_background_transparent_with_edges(image_path, output_path):
    """Make background transparent with smooth edges (fallback method)"""
    try:
        img = Image.open(image_path)
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        img_array = np.array(img)
        
        # Get RGB channels
        r = img_array[:,:,0].astype(float)
        g = img_array[:,:,1].astype(float)
        b = img_array[:,:,2].astype(float)
        
        # Calculate brightness
        brightness = (r + g + b) / 3
        
        # Create mask for background (light pixels)
        background_mask = brightness > 200
        
        # Set alpha to 0 for background
        img_array[background_mask, 3] = 0
        img_array[~background_mask, 3] = 255
        
        result = Image.fromarray(img_array, 'RGBA')
        
        # Apply slight blur to smooth edges
        alpha = result.split()[-1]
        alpha_smooth = alpha.filter(ImageFilter.GaussianBlur(radius=1))
        alpha_smooth = alpha_smooth.point(lambda x: 255 if x > 127 else 0)
        result.putalpha(alpha_smooth)
        
        # Crop to content
        bbox = result.getbbox()
        if bbox:
            padding = 10
            left = max(0, bbox[0] - padding)
            top = max(0, bbox[1] - padding)
            right = min(result.width, bbox[2] + padding)
            bottom = min(result.height, bbox[3] + padding)
            result = result.crop((left, top, right, bottom))
        
        # Enhance
        if result.size[0] > 0:
            rgb = result.convert('RGB')
            enhancer = ImageEnhance.Contrast(rgb)
            rgb = enhancer.enhance(2.0)
            enhancer = ImageEnhance.Sharpness(rgb)
            rgb = enhancer.enhance(2.5)
            
            final = Image.new('RGBA', rgb.size)
            final.paste(rgb, (0, 0))
            final.putalpha(result.split()[-1])
            result = final
        
        result.save(output_path, 'PNG')
        return True
        
    except Exception as e:
        print(f"Edge removal error: {e}")
        return False

# Choose the best available method
if REMBG_AVAILABLE:
    remove_signature_background = remove_signature_background_rembg
else:
    remove_signature_background = make_background_transparent_with_edges

# ==================== SHARING FUNCTIONS ====================

def share_via_whatsapp(phone_number, file_path, caption=""):
    """Share file via WhatsApp"""
    if DISABLE_WHATSAPP or kit is None:
        print("ℹ️ WhatsApp sharing disabled")
        return False
    
    try:
        if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
            kit.sendwhats_image(phone_number, file_path, caption, wait_time=15, close_time=3)
            return True
        else:
            webbrowser.open(f"https://web.whatsapp.com/")
            return True
    except Exception as e:
        print(f"WhatsApp sharing error: {e}")
        return False

# ==================== ROUTES ====================

@app.route('/uploads/<folder>/<path:filename>')
def uploaded_file(folder, filename):
    filename = os.path.basename(filename)
    
    if folder == 'staff_images':
        upload_path = Config.STAFF_IMAGES_FOLDER
    elif folder == 'staff_signatures':
        upload_path = Config.STAFF_SIGNATURES_FOLDER
    elif folder == 'staff_signatures_clean':
        upload_path = Config.CLEAN_SIGNATURES_FOLDER
    else:
        upload_path = 'temp'
    
    return send_from_directory(upload_path, filename)

@app.route('/')
def index():
    return render_template('index.html')

# ==================== STAFF LOGIN/REGISTRATION ====================

@app.route('/staff-login', methods=['GET', 'POST'])
def staff_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = Staff.query.filter(
            (Staff.email == username) | 
            (Staff.username == username) | 
            (Staff.phone_number == username)
        ).first()
        
        if user and user.check_password(password):
            login_user(user)
            session['user_type'] = 'staff'
            flash(f'Welcome {user.full_name}!', 'success')
            return redirect(url_for('staff_dashboard'))
        else:
            flash('Invalid credentials. Please check your email/username and password.', 'danger')
    
    return render_template('staff_login.html')

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = Admin.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            session['user_role'] = user.role
            session['user_type'] = 'admin'
            flash(f'Welcome Admin {user.full_name}!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid admin credentials', 'danger')
    
    return render_template('admin_login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        ministry = request.form.get('ministry')
        department = request.form.get('department')
        designation = request.form.get('designation')
        
        image_url = None
        photo_data = request.form.get('photo_data')
        photo_file = request.files.get('photo')
        
        # Handle photo upload to Cloudinary
        if photo_file and photo_file.filename:
            try:
                upload_result = cloudinary.uploader.upload(
                    photo_file,
                    folder="staff_photos",
                    public_id=f"staff_{full_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_photo",
                    overwrite=True
                )
                image_url = upload_result['secure_url']
                print(f"✅ Photo uploaded to Cloudinary: {image_url}")
            except Exception as e:
                print(f"Cloudinary photo error: {e}")
                flash(f'Photo upload failed: {str(e)}', 'danger')
                return render_template('register.html')
        elif photo_data and photo_data.startswith('data:image'):
            try:
                # Save temp file from camera capture
                header, encoded = photo_data.split(',', 1)
                image_bytes = base64.b64decode(encoded)
                temp_path = os.path.join('temp', f"temp_photo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                with open(temp_path, 'wb') as f:
                    f.write(image_bytes)
                upload_result = cloudinary.uploader.upload(temp_path, folder="staff_photos")
                image_url = upload_result['secure_url']
                os.remove(temp_path)
                print(f"✅ Camera photo uploaded to Cloudinary: {image_url}")
            except Exception as e:
                print(f"Camera upload error: {e}")
                flash(f'Photo upload failed: {str(e)}', 'danger')
                return render_template('register.html')
        
        signature_url = None
        signature_data = request.form.get('signature_data')
        signature_file = request.files.get('signature')
        
        # Handle signature upload to Cloudinary
        if signature_file and signature_file.filename:
            try:
                upload_result = cloudinary.uploader.upload(
                    signature_file,
                    folder="staff_signatures",
                    public_id=f"signature_{full_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    overwrite=True
                )
                signature_url = upload_result['secure_url']
                print(f"✅ Signature uploaded to Cloudinary: {signature_url}")
            except Exception as e:
                print(f"Cloudinary signature error: {e}")
                flash(f'Signature upload failed: {str(e)}', 'danger')
                return render_template('register.html')
        elif signature_data and signature_data.startswith('data:image'):
            try:
                header, encoded = signature_data.split(',', 1)
                image_bytes = base64.b64decode(encoded)
                temp_path = os.path.join('temp', f"temp_signature_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                with open(temp_path, 'wb') as f:
                    f.write(image_bytes)
                upload_result = cloudinary.uploader.upload(temp_path, folder="staff_signatures")
                signature_url = upload_result['secure_url']
                os.remove(temp_path)
                print(f"✅ Camera signature uploaded to Cloudinary: {signature_url}")
            except Exception as e:
                print(f"Camera upload error: {e}")
                flash(f'Signature upload failed: {str(e)}', 'danger')
                return render_template('register.html')
        
        if all([full_name, email, phone]):
            staff = Staff(
                full_name=full_name,
                email=email,
                phone_number=phone,
                ministry=ministry,
                department=department,
                designation=designation,
                image_path=image_url,  # Now stores Cloudinary URL
                signature_path=signature_url  # Now stores Cloudinary URL
            )
            
            db.session.add(staff)
            db.session.commit()
            
            flash('Registration submitted successfully! Admin will set your credentials.', 'success')
            return redirect(url_for('staff_login'))
        else:
            flash('Please fill all required fields', 'danger')
    
    return render_template('register.html')
@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect(url_for('index'))
# ==================== IMAGE UPLOAD ROUTES ====================

@app.route('/save-edited-image', methods=['POST'])
@login_required
def save_edited_image():
    """Save edited image from editor"""
    if session.get('user_type') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.json
        staff_id = data.get('staff_id')
        image_type = data.get('type')
        image_data = data.get('image_data')
        
        staff = Staff.query.get_or_404(staff_id)
        
        if image_data and image_data.startswith('data:image'):
            header, encoded = image_data.split(',', 1)
            image_bytes = base64.b64decode(encoded)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            clean_name = clean_filename(staff.full_name)
            
            if image_type == 'photo':
                filename = f"{clean_name}_photo_{timestamp}.png"
                folder = Config.STAFF_IMAGES_FOLDER
                if staff.image_path and os.path.exists(staff.image_path):
                    os.remove(staff.image_path)
                staff.image_path = os.path.join(folder, filename)
            else:
                filename = f"{clean_name}_signature_{timestamp}.png"
                folder = Config.STAFF_SIGNATURES_FOLDER
                if staff.signature_path and os.path.exists(staff.signature_path):
                    os.remove(staff.signature_path)
                staff.signature_path = os.path.join(folder, filename)
            
            os.makedirs(folder, exist_ok=True)
            filepath = os.path.join(folder, filename)
            with open(filepath, 'wb') as f:
                f.write(image_bytes)
            
            db.session.commit()
            return jsonify({'success': True})
        
        return jsonify({'error': 'Invalid image data'}), 400
        
    except Exception as e:
        print(f"Error saving edited image: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/upload-staff-photo', methods=['POST'])
@login_required
def upload_staff_photo():
    """Upload new staff photo to Cloudinary"""
    if session.get('user_type') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        staff_id = request.form.get('staff_id')
        photo = request.files.get('photo')
        
        if not photo:
            return jsonify({'error': 'No photo provided'}), 400
        
        staff = Staff.query.get_or_404(staff_id)
        clean_name = clean_filename(staff.full_name)
        
        # Upload to Cloudinary
        upload_result = cloudinary.uploader.upload(
            photo,
            folder="staff_photos",
            public_id=f"staff_{staff.id}_photo",
            overwrite=True
        )
        cloudinary_url = upload_result['secure_url']
        
        # Delete old photo from local storage if it exists and is a local file
        if staff.image_path and not staff.image_path.startswith('http'):
            if os.path.exists(staff.image_path):
                os.remove(staff.image_path)
        
        # Save Cloudinary URL to database
        staff.image_path = cloudinary_url
        db.session.commit()
        
        return jsonify({'success': True, 'image_url': cloudinary_url})
        
    except Exception as e:
        print(f"Error uploading photo: {e}")
        return jsonify({'error': str(e)}), 500
@app.route('/upload-staff-signature', methods=['POST'])
@login_required
def upload_staff_signature():
    """Upload new staff signature to Cloudinary"""
    if session.get('user_type') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        staff_id = request.form.get('staff_id')
        signature = request.files.get('signature')
        
        if not signature:
            return jsonify({'error': 'No signature provided'}), 400
        
        staff = Staff.query.get_or_404(staff_id)
        clean_name = clean_filename(staff.full_name)
        
        # Upload to Cloudinary
        upload_result = cloudinary.uploader.upload(
            signature,
            folder="staff_signatures",
            public_id=f"staff_{staff.id}_signature",
            overwrite=True
        )
        cloudinary_url = upload_result['secure_url']
        
        # Delete old signature from local storage if it exists and is a local file
        if staff.signature_path and not staff.signature_path.startswith('http'):
            if os.path.exists(staff.signature_path):
                os.remove(staff.signature_path)
        
        # Save Cloudinary URL to database
        staff.signature_path = cloudinary_url
        db.session.commit()
        
        return jsonify({'success': True, 'signature_url': cloudinary_url})
        
    except Exception as e:
        print(f"Error uploading signature: {e}")
        return jsonify({'error': str(e)}), 500# ==================== BACKGROUND REMOVAL ROUTES ====================

@app.route('/admin/staff/remove-bg/<int:id>')
@login_required
def remove_single_background(id):
    """Remove background from a single signature and upload to Cloudinary"""
    if session.get('user_type') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    if not REMBG_AVAILABLE:
        return jsonify({'error': 'Background removal is disabled in this environment'}), 503
    
    staff = Staff.query.get_or_404(id)
    
    if not staff.signature_path:
        return jsonify({'error': 'No signature found'}), 404
    
    try:
        sig_filename = os.path.basename(staff.signature_path)
        sig_path = os.path.join(Config.STAFF_SIGNATURES_FOLDER, sig_filename)
        
        if os.path.exists(sig_path):
            clean_filename = f"clean_{sig_filename}"
            clean_path = os.path.join(Config.CLEAN_SIGNATURES_FOLDER, clean_filename)
            
            success = remove_signature_background(sig_path, clean_path)
            
            if success:
                # Save local path as fallback
                staff.signature_bg_removed_path = clean_filename
                
                # Upload to Cloudinary if configured
                if Config.CLOUDINARY_CLOUD_NAME:
                    try:
                        upload_result = cloudinary.uploader.upload(
                            clean_path,
                            folder="staff_signatures_clean",
                            public_id=f"staff_{staff.id}_signature_clean",
                            overwrite=True
                        )
                        cloudinary_url = upload_result['secure_url']
                        staff.signature_bg_removed_url = cloudinary_url
                        print(f"✅ Uploaded to Cloudinary: {cloudinary_url}")
                    except Exception as cloud_error:
                        print(f"⚠️ Cloudinary upload error: {cloud_error}")
                        print("Continuing with local storage only")
                else:
                    print("ℹ️ Cloudinary not configured - saving locally only")
                
                db.session.commit()
                return jsonify({'success': True, 'message': 'Background removed successfully!'})
            else:
                return jsonify({'error': 'Background removal failed'}), 500
        else:
            return jsonify({'error': 'Signature file not found'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/admin/bulk-remove-bg', methods=['POST'])
@login_required
def bulk_remove_backgrounds():
    """Remove backgrounds for signatures based on current filters"""
    if session.get('user_type') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    if not REMBG_AVAILABLE:
        return jsonify({'error': 'Background removal is disabled in this environment'}), 503
    
    # Get filter parameters from request args
    search = request.args.get('search', '')
    ministry_filter = request.args.get('ministry_filter', '')
    
    # Build query with filters
    query = Staff.query.filter(
        Staff.signature_path.isnot(None),
        Staff.signature_bg_removed_path.is_(None)
    )
    
    # Apply search filter
    if search:
        query = query.filter(
            Staff.full_name.contains(search) | 
            Staff.email.contains(search) | 
            Staff.phone_number.contains(search)
        )
    
    # Apply ministry filter
    if ministry_filter:
        query = query.filter(Staff.ministry == ministry_filter)
    
    staff_members = query.all()
    
    if not staff_members:
        return jsonify({'processed': 0, 'failed': 0, 'total': 0, 'message': 'No signatures to process with current filters'})
    
    processed = 0
    failed = 0
    
    for staff in staff_members:
        try:
            sig_filename = os.path.basename(staff.signature_path)
            sig_path = os.path.join(Config.STAFF_SIGNATURES_FOLDER, sig_filename)
            
            if os.path.exists(sig_path):
                clean_filename = f"clean_{sig_filename}"
                clean_path = os.path.join(Config.CLEAN_SIGNATURES_FOLDER, clean_filename)
                
                success = remove_signature_background(sig_path, clean_path)
                
                if success:
                    staff.signature_bg_removed_path = clean_filename
                    
                    # Upload to Cloudinary if configured
                    if Config.CLOUDINARY_CLOUD_NAME:
                        try:
                            upload_result = cloudinary.uploader.upload(
                                clean_path,
                                folder="staff_signatures_clean",
                                public_id=f"staff_{staff.id}_signature_clean",
                                overwrite=True
                            )
                            staff.signature_bg_removed_url = upload_result['secure_url']
                        except Exception as cloud_error:
                            print(f"⚠️ Cloudinary upload error for {staff.full_name}: {cloud_error}")
                    
                    processed += 1
                else:
                    failed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"Error processing {staff.full_name}: {e}")
            failed += 1
    
    db.session.commit()
    return jsonify({'processed': processed, 'failed': failed, 'total': len(staff_members)})

# ==================== SHARING ROUTES ====================

@app.route('/get-staff-details/<int:staff_id>')
@login_required
def get_staff_details(staff_id):
    """Get staff details for preview modal"""
    staff = Staff.query.get_or_404(staff_id)
    
    photo_url = None
    if staff.image_path and os.path.exists(staff.image_path):
        photo_url = url_for('uploaded_file', folder='staff_images', filename=os.path.basename(staff.image_path), _external=True)
    
    signature_url = None
    has_clean = False
    
    # Priority: Cloudinary URL > local clean path > original signature
    if staff.signature_bg_removed_url:
        signature_url = staff.signature_bg_removed_url
        has_clean = True
    elif staff.signature_bg_removed_path:
        clean_path = os.path.join(Config.CLEAN_SIGNATURES_FOLDER, staff.signature_bg_removed_path)
        if os.path.exists(clean_path):
            signature_url = url_for('uploaded_file', folder='staff_signatures_clean', filename=staff.signature_bg_removed_path, _external=True)
            has_clean = True
    elif staff.signature_path and os.path.exists(staff.signature_path):
        signature_url = url_for('uploaded_file', folder='staff_signatures', filename=os.path.basename(staff.signature_path), _external=True)
    
    return jsonify({
        'success': True,
        'id': staff.id,
        'full_name': staff.full_name,
        'email': staff.email,
        'phone_number': staff.phone_number,
        'ministry': staff.ministry,
        'department': staff.department,
        'designation': staff.designation,
        'photo_url': photo_url,
        'signature_url': signature_url,
        'has_clean': has_clean
    })

@app.route('/get-share-info/<int:staff_id>/<string:type>')
@login_required
def get_share_info(staff_id, type):
    """Get shareable URL for photo or signature"""
    staff = Staff.query.get_or_404(staff_id)
    
    if type == 'photo':
        if not staff.image_path or not os.path.exists(staff.image_path):
            return jsonify({'error': 'No photo found'}), 404
        filename = os.path.basename(staff.image_path)
        url = url_for('uploaded_file', folder='staff_images', filename=filename, _external=True)
        return jsonify({
            'success': True,
            'url': url,
            'name': f"{staff.full_name}'s Photo"
        })
    
    elif type == 'signature':
        # Priority: Cloudinary URL > local clean path > original signature
        if staff.signature_bg_removed_url:
            return jsonify({
                'success': True,
                'url': staff.signature_bg_removed_url,
                'name': f"{staff.full_name}'s Signature (Clean - Cloud)"
            })
        elif staff.signature_bg_removed_path:
            clean_path = os.path.join(Config.CLEAN_SIGNATURES_FOLDER, staff.signature_bg_removed_path)
            if os.path.exists(clean_path):
                url = url_for('uploaded_file', folder='staff_signatures_clean', filename=staff.signature_bg_removed_path, _external=True)
                return jsonify({
                    'success': True,
                    'url': url,
                    'name': f"{staff.full_name}'s Signature (Clean)"
                })
        
        if staff.signature_path and os.path.exists(staff.signature_path):
            filename = os.path.basename(staff.signature_path)
            url = url_for('uploaded_file', folder='staff_signatures', filename=filename, _external=True)
            return jsonify({
                'success': True,
                'url': url,
                'name': f"{staff.full_name}'s Signature"
            })
        
        return jsonify({'error': 'No signature found'}), 404
    
    return jsonify({'error': 'Invalid type'}), 400

@app.route('/share-whatsapp', methods=['POST'])
@login_required
def share_whatsapp():
    """Share photo or signature via WhatsApp"""
    if DISABLE_WHATSAPP or kit is None:
        return jsonify({'error': 'WhatsApp sharing is disabled in this environment'}), 503
    
    data = request.json
    staff_id = data.get('staff_id')
    share_type = data.get('type')
    phone_number = data.get('phone_number')
    
    if not phone_number:
        return jsonify({'error': 'Phone number required'}), 400
    
    if not phone_number.startswith('+'):
        phone_number = '+' + phone_number
    
    staff = Staff.query.get_or_404(staff_id)
    
    if share_type == 'photo':
        if not staff.image_path or not os.path.exists(staff.image_path):
            return jsonify({'error': 'No photo found'}), 404
        file_path = staff.image_path
        caption = f"Photo of {staff.full_name}\nMinistry: {staff.ministry or 'N/A'}\nDepartment: {staff.department or 'N/A'}"
    else:
        # Priority: Cloudinary URL > local clean path > original signature
        if staff.signature_bg_removed_url:
            file_path = staff.signature_bg_removed_url
        elif staff.signature_bg_removed_path:
            file_path = os.path.join(Config.CLEAN_SIGNATURES_FOLDER, staff.signature_bg_removed_path)
        elif staff.signature_path:
            file_path = staff.signature_path
        else:
            return jsonify({'error': 'No signature found'}), 404
        caption = f"Signature of {staff.full_name}\nMinistry: {staff.ministry or 'N/A'}\nDepartment: {staff.department or 'N/A'}"
    
    if isinstance(file_path, str) and not file_path.startswith('http') and not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404
    
    try:
        kit.sendwhats_image(phone_number, file_path, caption, wait_time=15, close_time=3)
        return jsonify({'success': True, 'message': 'WhatsApp sharing initiated! Check your WhatsApp.'})
    except Exception as e:
        print(f"WhatsApp error: {e}")
        whatsapp_url = f"https://web.whatsapp.com/send?phone={phone_number}&text={caption}"
        webbrowser.open(whatsapp_url)
        return jsonify({'success': True, 'message': 'WhatsApp Web opened. Please send the file manually.'})

# ==================== DOWNLOAD ROUTES ====================

@app.route('/admin/download-filtered-signatures')
@login_required
def download_filtered_signatures():
    """Download all background-removed signatures based on current filters"""
    if session.get('user_type') != 'admin':
        return redirect(url_for('staff_dashboard'))
    
    search = request.args.get('search', '')
    ministry_filter = request.args.get('ministry_filter', '')
    
    query = Staff.query.filter(Staff.signature_bg_removed_path.isnot(None))
    
    if search:
        query = query.filter(
            Staff.full_name.contains(search) | 
            Staff.email.contains(search) | 
            Staff.phone_number.contains(search)
        )
    
    if ministry_filter:
        query = query.filter(Staff.ministry == ministry_filter)
    
    staff_members = query.all()
    
    if not staff_members:
        flash('No background-removed signatures found with current filters', 'warning')
        return redirect(url_for('admin_staff', search=search, ministry_filter=ministry_filter))
    
    zip_buffer = io.BytesIO()
    count = 0
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for staff in staff_members:
            if staff.signature_bg_removed_path:
                clean_path = os.path.join(Config.CLEAN_SIGNATURES_FOLDER, staff.signature_bg_removed_path)
                if os.path.exists(clean_path):
                    filename = f"{clean_filename(staff.full_name)}_signature_clean.png"
                    with open(clean_path, 'rb') as f:
                        zf.writestr(filename, f.read())
                        count += 1
    
    zip_buffer.seek(0)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    return send_file(zip_buffer, as_attachment=True, 
                    download_name=f'clean_signatures_{timestamp}.zip',
                    mimetype='application/zip')

@app.route('/admin/download-filtered-photos')
@login_required
def download_filtered_photos():
    """Download all staff photos based on current filters"""
    if session.get('user_type') != 'admin':
        return redirect(url_for('staff_dashboard'))
    
    search = request.args.get('search', '')
    ministry_filter = request.args.get('ministry_filter', '')
    
    query = Staff.query.filter(Staff.image_path.isnot(None))
    
    if search:
        query = query.filter(
            Staff.full_name.contains(search) | 
            Staff.email.contains(search) | 
            Staff.phone_number.contains(search)
        )
    
    if ministry_filter:
        query = query.filter(Staff.ministry == ministry_filter)
    
    staff_members = query.all()
    
    if not staff_members:
        flash('No photos found with current filters', 'warning')
        return redirect(url_for('admin_staff', search=search, ministry_filter=ministry_filter))
    
    zip_buffer = io.BytesIO()
    count = 0
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for staff in staff_members:
            if staff.image_path and os.path.exists(staff.image_path):
                filename = f"{clean_filename(staff.full_name)}_photo.png"
                with open(staff.image_path, 'rb') as f:
                    zf.writestr(filename, f.read())
                    count += 1
    
    zip_buffer.seek(0)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    return send_file(zip_buffer, as_attachment=True, 
                    download_name=f'staff_photos_{timestamp}.zip',
                    mimetype='application/zip')

@app.route('/admin/download-filtered-all')
@login_required
def download_filtered_all():
    """Download all staff data (photos and signatures) based on current filters"""
    if session.get('user_type') != 'admin':
        return redirect(url_for('staff_dashboard'))
    
    search = request.args.get('search', '')
    ministry_filter = request.args.get('ministry_filter', '')
    
    query = Staff.query
    
    if search:
        query = query.filter(
            Staff.full_name.contains(search) | 
            Staff.email.contains(search) | 
            Staff.phone_number.contains(search)
        )
    
    if ministry_filter:
        query = query.filter(Staff.ministry == ministry_filter)
    
    staff_members = query.all()
    
    if not staff_members:
        flash('No staff members found with current filters', 'warning')
        return redirect(url_for('admin_staff', search=search, ministry_filter=ministry_filter))
    
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for staff in staff_members:
            clean_name = clean_filename(staff.full_name)
            folder_name = f"{clean_name}_{staff.id}"
            
            if staff.image_path and os.path.exists(staff.image_path):
                with open(staff.image_path, 'rb') as f:
                    zf.writestr(f"{folder_name}/photo.png", f.read())
            
            if staff.signature_bg_removed_path:
                clean_path = os.path.join(Config.CLEAN_SIGNATURES_FOLDER, staff.signature_bg_removed_path)
                if os.path.exists(clean_path):
                    with open(clean_path, 'rb') as f:
                        zf.writestr(f"{folder_name}/signature_clean.png", f.read())
            
            if staff.signature_path and os.path.exists(staff.signature_path):
                with open(staff.signature_path, 'rb') as f:
                    zf.writestr(f"{folder_name}/signature_original.png", f.read())
            
            info = f"""Staff Information
================
Name: {staff.full_name}
Email: {staff.email}
Phone: {staff.phone_number}
Username: {staff.username or 'Not set'}
Ministry: {staff.ministry or 'N/A'}
Department: {staff.department or 'N/A'}
Designation: {staff.designation or 'N/A'}
Has Clean Signature: {'Yes' if staff.signature_bg_removed_path else 'No'}
"""
            zf.writestr(f"{folder_name}/staff_info.txt", info)
    
    zip_buffer.seek(0)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    return send_file(zip_buffer, as_attachment=True, 
                    download_name=f'all_staff_data_{timestamp}.zip',
                    mimetype='application/zip')

# ==================== ADMIN ROUTES ====================

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if session.get('user_type') != 'admin':
        return redirect(url_for('staff_dashboard'))
    
    total_staff = Staff.query.count()
    total_admins = Admin.query.count()
    recent_imports = ImportLog.query.order_by(ImportLog.import_date.desc()).limit(5).all()
    
    return render_template('admin_dashboard.html', 
                         total_staff=total_staff, 
                         total_admins=total_admins,
                         recent_imports=recent_imports)

@app.route('/admin/staff')
@login_required
def admin_staff():
    if session.get('user_type') != 'admin':
        return redirect(url_for('staff_dashboard'))
    
    search = request.args.get('search', '')
    ministry_filter = request.args.get('ministry_filter', '')
    
    query = Staff.query
    
    if search:
        query = query.filter(
            Staff.full_name.contains(search) | 
            Staff.email.contains(search) | 
            Staff.phone_number.contains(search)
        )
    
    if ministry_filter:
        query = query.filter(Staff.ministry == ministry_filter)
    
    staff_list = query.all()
    
    all_ministries = Staff.query.with_entities(Staff.ministry).distinct().all()
    ministries = sorted([m[0] for m in all_ministries if m[0] and m[0] != ''])
    
    return render_template('staff_list.html', 
                         staff=staff_list, 
                         search=search,
                         ministry_filter=ministry_filter,
                         ministries=ministries)

@app.route('/admin/staff/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_staff(id):
    if session.get('user_type') != 'admin':
        return redirect(url_for('staff_dashboard'))
    
    staff = Staff.query.get_or_404(id)
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        ministry = request.form.get('ministry')
        department = request.form.get('department')
        designation = request.form.get('designation')
        new_password = request.form.get('password')
        
        if username == '':
            username = None
        
        if username is not None and username != staff.username:
            existing_staff = Staff.query.filter(Staff.username == username).first()
            if existing_staff and existing_staff.id != staff.id:
                flash(f'Username "{username}" is already taken. Please choose another.', 'danger')
                return render_template('edit_staff.html', staff=staff)
        
        staff.username = username
        staff.ministry = ministry
        staff.department = department
        staff.designation = designation
        staff.updated_by = current_user.full_name
        
        if new_password and new_password.strip():
            staff.set_password(new_password.strip())
        
        # Handle photo upload if a new photo is provided
        photo_file = request.files.get('photo')
        if photo_file and photo_file.filename:
            try:
                upload_result = cloudinary.uploader.upload(
                    photo_file,
                    folder="staff_photos",
                    public_id=f"staff_{staff.id}_photo",
                    overwrite=True
                )
                staff.image_path = upload_result['secure_url']
                print(f"✅ Photo uploaded to Cloudinary for {staff.full_name}")
            except Exception as e:
                print(f"Cloudinary photo error: {e}")
                flash(f'Photo upload failed: {str(e)}', 'danger')
                return render_template('edit_staff.html', staff=staff)
        
        # Handle signature upload if a new signature is provided
        signature_file = request.files.get('signature')
        if signature_file and signature_file.filename:
            try:
                upload_result = cloudinary.uploader.upload(
                    signature_file,
                    folder="staff_signatures",
                    public_id=f"staff_{staff.id}_signature",
                    overwrite=True
                )
                staff.signature_path = upload_result['secure_url']
                print(f"✅ Signature uploaded to Cloudinary for {staff.full_name}")
            except Exception as e:
                print(f"Cloudinary signature error: {e}")
                flash(f'Signature upload failed: {str(e)}', 'danger')
                return render_template('edit_staff.html', staff=staff)
        
        try:
            db.session.commit()
            flash('Staff updated successfully!', 'success')
            return redirect(url_for('admin_staff'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating staff: {str(e)}', 'danger')
            return render_template('edit_staff.html', staff=staff)
    
    return render_template('edit_staff.html', staff=staff)
@app.route('/admin/staff/delete/<int:id>')
@login_required
def delete_staff(id):
    if session.get('user_type') != 'admin' or session.get('user_role') != 'super_admin':
        flash('Permission denied', 'danger')
        return redirect(url_for('admin_staff'))
    
    staff = Staff.query.get_or_404(id)
    
    if staff.image_path and os.path.exists(staff.image_path):
        os.remove(staff.image_path)
    if staff.signature_path and os.path.exists(staff.signature_path):
        os.remove(staff.signature_path)
    if staff.signature_bg_removed_path:
        clean_path = os.path.join(Config.CLEAN_SIGNATURES_FOLDER, staff.signature_bg_removed_path)
        if os.path.exists(clean_path):
            os.remove(clean_path)
    
    db.session.delete(staff)
    db.session.commit()
    flash('Staff deleted successfully', 'success')
    return redirect(url_for('admin_staff'))

@app.route('/admin/import', methods=['GET', 'POST'])
@login_required
def import_data():
    if session.get('user_type') != 'admin':
        return redirect(url_for('staff_dashboard'))
    
    if request.method == 'POST':
        file = request.files.get('file')
        sheet_url = request.form.get('sheet_url')
        
        df = None
        
        if file and file.filename:
            if file.filename.endswith('.csv'):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)
        elif sheet_url:
            try:
                if '/d/' in sheet_url:
                    sheet_id = sheet_url.split('/d/')[1].split('/')[0]
                    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
                    df = pd.read_csv(csv_url)
                elif 'pub?output=csv' in sheet_url:
                    df = pd.read_csv(sheet_url)
                else:
                    flash('Invalid Google Sheet URL', 'danger')
                    return redirect(url_for('import_data'))
            except Exception as e:
                flash(f'Error reading Google Sheet: {str(e)}', 'danger')
                return redirect(url_for('import_data'))
        
        if df is not None and not df.empty:
            successful, failed, errors = process_imported_staff(df, current_user.full_name)
            flash(f'Import completed! {successful} imported, {failed} failed', 'success')
            return redirect(url_for('admin_staff'))
        else:
            flash('No data found in file/sheet', 'danger')
    
    return render_template('import_data.html')

@app.route('/admin/signature-remover', methods=['GET', 'POST'])
@login_required
def signature_remover():
    if session.get('user_type') != 'admin':
        return redirect(url_for('staff_dashboard'))
    
    if not REMBG_AVAILABLE:
        flash('Background removal is disabled in this environment.', 'warning')
        return render_template('signature_remover.html')
    
    if request.method == 'POST':
        files = request.files.getlist('signatures')
        results = []
        
        for file in files:
            if file:
                temp_filename = f"temp_{file.filename}"
                temp_path = os.path.join(Config.CLEAN_SIGNATURES_FOLDER, temp_filename)
                file.save(temp_path)
                
                clean_filename = f"clean_{file.filename}"
                clean_path = os.path.join(Config.CLEAN_SIGNATURES_FOLDER, clean_filename)
                
                success = remove_signature_background(temp_path, clean_path)
                
                if success and os.path.exists(clean_path):
                    results.append({'name': file.filename, 'path': clean_path})
                
                if os.path.exists(temp_path):
                    os.remove(temp_path)
        
        if results:
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                for r in results:
                    if os.path.exists(r['path']):
                        with open(r['path'], 'rb') as f:
                            zf.writestr(f"clean_{r['name']}", f.read())
            
            zip_buffer.seek(0)
            return send_file(zip_buffer, as_attachment=True, download_name='cleaned_signatures.zip')
    
    return render_template('signature_remover.html')

@app.route('/admin/download-all-signatures')
@login_required
def download_all_signatures():
    if session.get('user_type') != 'admin':
        return redirect(url_for('staff_dashboard'))
    
    zip_buffer = io.BytesIO()
    count = 0
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        staff_members = Staff.query.all()
        for staff in staff_members:
            sig_path = None
            if staff.signature_bg_removed_path:
                sig_path = os.path.join(Config.CLEAN_SIGNATURES_FOLDER, staff.signature_bg_removed_path)
            elif staff.signature_path:
                sig_path = staff.signature_path
            
            if sig_path and os.path.exists(sig_path):
                with open(sig_path, 'rb') as f:
                    filename = f"{clean_filename(staff.full_name)}_signature.png"
                    zf.writestr(filename, f.read())
                    count += 1
    
    zip_buffer.seek(0)
    if count > 0:
        return send_file(zip_buffer, as_attachment=True, download_name=f'signatures_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip')
    else:
        flash('No signatures found to download', 'warning')
        return redirect(url_for('admin_staff'))

@app.route('/admin/admins')
@login_required
def manage_admins():
    if session.get('user_type') != 'admin' or session.get('user_role') != 'super_admin':
        flash('Permission denied', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    admins = Admin.query.all()
    return render_template('manage_admins.html', admins=admins)

@app.route('/admin/admins/create', methods=['POST'])
@login_required
def create_admin():
    if session.get('user_role') != 'super_admin':
        return jsonify({'error': 'Permission denied'}), 403
    
    username = request.form.get('username')
    email = request.form.get('email')
    full_name = request.form.get('full_name')
    password = request.form.get('password')
    role = request.form.get('role', 'admin')
    
    if Admin.query.filter_by(username=username).first():
        flash('Username already exists', 'danger')
        return redirect(url_for('manage_admins'))
    
    admin = Admin(username=username, email=email, full_name=full_name, role=role)
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()
    
    flash('Admin created successfully', 'success')
    return redirect(url_for('manage_admins'))

@app.route('/admin/admins/reset-password/<int:id>', methods=['POST'])
@login_required
def reset_admin_password(id):
    if session.get('user_role') != 'super_admin':
        return jsonify({'error': 'Permission denied'}), 403
    
    admin = Admin.query.get_or_404(id)
    new_password = request.form.get('password')
    
    if new_password:
        admin.set_password(new_password)
        db.session.commit()
        flash('Password reset successfully', 'success')
    
    return redirect(url_for('manage_admins'))

@app.route('/admin/admins/delete/<int:id>', methods=['POST'])
@login_required
def delete_admin(id):
    if session.get('user_role') != 'super_admin':
        return jsonify({'error': 'Permission denied'}), 403
    
    admin = Admin.query.get_or_404(id)
    if admin.username == current_user.username:
        flash('Cannot delete your own account', 'danger')
        return redirect(url_for('manage_admins'))
    
    db.session.delete(admin)
    db.session.commit()
    flash('Admin deleted successfully', 'success')
    return redirect(url_for('manage_admins'))

# ==================== STAFF ROUTES ====================

@app.route('/staff/dashboard')
@login_required
def staff_dashboard():
    if session.get('user_type') != 'staff':
        return redirect(url_for('admin_dashboard'))
    
    return render_template('staff_dashboard.html', staff=current_user)

@app.route('/migrate-to-cloudinary')
@login_required
def migrate_to_cloudinary():
    """Temporary route to migrate existing images to Cloudinary"""
    if session.get('user_role') != 'super_admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    from config import Config
    import cloudinary.uploader
    import os
    
    cloudinary.config(
        cloud_name=Config.CLOUDINARY_CLOUD_NAME,
        api_key=Config.CLOUDINARY_API_KEY,
        api_secret=Config.CLOUDINARY_API_SECRET
    )
    
    staff_members = Staff.query.all()
    results = []
    
    for staff in staff_members:
        result = {
            'name': staff.full_name, 
            'id': staff.id,
            'photo': False, 
            'signature': False
        }
        
        # Migrate photo
        if staff.image_path and not staff.image_path.startswith('http'):
            if os.path.exists(staff.image_path):
                try:
                    upload = cloudinary.uploader.upload(
                        staff.image_path,
                        folder="staff_photos",
                        public_id=f"staff_{staff.id}_photo",
                        overwrite=True
                    )
                    staff.image_path = upload['secure_url']
                    result['photo'] = True
                    result['photo_url'] = upload['secure_url']
                except Exception as e:
                    result['photo_error'] = str(e)
            else:
                result['photo_error'] = f"File not found: {staff.image_path}"
        elif staff.image_path and staff.image_path.startswith('http'):
            result['photo'] = 'already_cloud'
        
        # Migrate signature
        if staff.signature_path and not staff.signature_path.startswith('http'):
            if os.path.exists(staff.signature_path):
                try:
                    upload = cloudinary.uploader.upload(
                        staff.signature_path,
                        folder="staff_signatures",
                        public_id=f"staff_{staff.id}_signature",
                        overwrite=True
                    )
                    staff.signature_path = upload['secure_url']
                    result['signature'] = True
                    result['signature_url'] = upload['secure_url']
                except Exception as e:
                    result['signature_error'] = str(e)
            else:
                result['signature_error'] = f"File not found: {staff.signature_path}"
        elif staff.signature_path and staff.signature_path.startswith('http'):
            result['signature'] = 'already_cloud'
        
        results.append(result)
    
    db.session.commit()
    return jsonify({
        'success': True, 
        'message': f'Processed {len(staff_members)} staff members',
        'results': results
    })

# ==================== RUN APP ====================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)