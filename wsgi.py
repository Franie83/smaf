import sys
import os
from dotenv import load_dotenv

# Add your project directory to the system path
project_home = '/home/yourusername/smaf'  # Change 'yourusername' to your actual PythonAnywhere username
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Load environment variables
load_dotenv(os.path.join(project_home, '.env'))

# Set Flask environment
os.environ['FLASK_APP'] = 'app.py'

# Import your Flask app
from app import app as application