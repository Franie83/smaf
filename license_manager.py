import hashlib
import json
import os
import sys
import platform
import socket
import uuid
import time
from datetime import datetime, timedelta
from cryptography.fernet import Fernet

class LicenseManager:
    def __init__(self, license_file='license.lic'):
        self.license_file = license_file
        self.system_id = self.generate_system_id()
        
    def generate_system_id(self):
        """Generate a unique system ID based on hardware"""
        try:
            # Get MAC address
            mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) 
                           for elements in range(0, 2*6, 2)][::-1])
            
            # Get computer name
            computer_name = socket.gethostname()
            
            # Get platform info
            platform_info = platform.platform()
            
            # Combine to create unique ID
            system_string = f"{mac}-{computer_name}-{platform_info}"
            system_id = hashlib.sha256(system_string.encode()).hexdigest()[:32]
            
            return system_id
        except:
            return hashlib.sha256(socket.gethostname().encode()).hexdigest()[:32]
    
    def generate_license(self, customer_name, email, expiry_days=30, max_users=5):
        """Generate a license key (for admin use)"""
        # Create license data
        license_data = {
            'customer_name': customer_name,
            'email': email,
            'system_id': self.system_id,
            'issue_date': datetime.now().isoformat(),
            'expiry_date': (datetime.now() + timedelta(days=expiry_days)).isoformat(),
            'max_users': max_users,
            'features': ['staff_management', 'background_removal', 'whatsapp_sharing']
        }
        
        # Convert to JSON
        license_json = json.dumps(license_data)
        
        # Create a simple encryption (you can use a more secure method)
        license_key = base64.b64encode(license_json.encode()).decode()
        
        # Save license file
        with open(self.license_file, 'w') as f:
            f.write(license_key)
        
        return license_key
    
    def validate_license(self):
        """Validate the license and return status"""
        if not os.path.exists(self.license_file):
            return {
                'valid': False,
                'error': 'License file not found',
                'code': 'NO_LICENSE'
            }
        
        try:
            # Read license file
            with open(self.license_file, 'r') as f:
                license_key = f.read().strip()
            
            # Decode license
            license_json = base64.b64decode(license_key).decode()
            license_data = json.loads(license_json)
            
            # Check system ID
            if license_data.get('system_id') != self.system_id:
                return {
                    'valid': False,
                    'error': 'This license is not valid for this computer',
                    'code': 'INVALID_SYSTEM'
                }
            
            # Check expiry
            expiry_date = datetime.fromisoformat(license_data['expiry_date'])
            if datetime.now() > expiry_date:
                return {
                    'valid': False,
                    'error': f'License expired on {expiry_date.strftime("%Y-%m-%d")}',
                    'code': 'EXPIRED'
                }
            
            # Calculate days remaining
            days_remaining = (expiry_date - datetime.now()).days
            
            return {
                'valid': True,
                'customer_name': license_data['customer_name'],
                'email': license_data['email'],
                'expiry_date': expiry_date,
                'days_remaining': days_remaining,
                'max_users': license_data.get('max_users', 5),
                'features': license_data.get('features', [])
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': f'Invalid license file: {str(e)}',
                'code': 'INVALID_FILE'
            }
    
    def create_trial_license(self, days=30):
        """Create a trial license for testing"""
        license_data = {
            'customer_name': 'Trial User',
            'email': 'trial@example.com',
            'system_id': self.system_id,
            'issue_date': datetime.now().isoformat(),
            'expiry_date': (datetime.now() + timedelta(days=days)).isoformat(),
            'max_users': 3,
            'features': ['staff_management'],
            'is_trial': True
        }
        
        license_json = json.dumps(license_data)
        license_key = base64.b64encode(license_json.encode()).decode()
        
        with open(self.license_file, 'w') as f:
            f.write(license_key)
        
        return license_key