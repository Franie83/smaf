import base64
import json
from datetime import datetime, timedelta
import hashlib
import socket
import platform
import uuid
import os
from dotenv import load_dotenv

load_dotenv()

def generate_system_id():
    try:
        mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) 
                       for elements in range(0, 2*6, 2)][::-1])
        computer_name = socket.gethostname()
        platform_info = platform.platform()
        system_string = f"{mac}-{computer_name}-{platform_info}"
        system_id = hashlib.sha256(system_string.encode()).hexdigest()[:32]
        return system_id
    except:
        return hashlib.sha256(socket.gethostname().encode()).hexdigest()[:32]

# Get settings from .env or use defaults
expiry_days = int(os.environ.get('LICENSE_EXPIRY_DAYS', 365))
max_users = int(os.environ.get('LICENSE_MAX_USERS', 100))

# Create license
license_data = {
    'customer_name': 'Local User',
    'email': 'local@example.com',
    'system_id': generate_system_id(),
    'issue_date': datetime.now().isoformat(),
    'expiry_date': (datetime.now() + timedelta(days=expiry_days)).isoformat(),
    'max_users': max_users,
    'features': ['staff_management', 'background_removal']
}

license_key = base64.b64encode(json.dumps(license_data).encode()).decode()

with open('license.lic', 'w') as f:
    f.write(license_key)

print("="*60)
print("✅ LICENSE CREATED SUCCESSFULLY!")
print("="*60)
print(f"License File: license.lic")
print(f"Customer: {license_data['customer_name']}")
print(f"Email: {license_data['email']}")
print(f"Expiry Date: {license_data['expiry_date']}")
print(f"Days Valid: {expiry_days}")
print(f"Max Users: {max_users}")
print("="*60)
print("\nPlace 'license.lic' in the same directory as your app.")