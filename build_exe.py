import PyInstaller.__main__
import os
import sys

# Get the current directory
current_dir = os.path.dirname(os.path.abspath(__file__))

# PyInstaller options
opts = [
    'app.py',  # Your main Flask app file
    '--name=StaffManagementSystem',  # Name of the executable
    '--onefile',  # Create a single executable file
    '--windowed',  # Don't show console window (use --console for debugging)
    '--add-data=templates;templates',  # Include templates folder
    '--add-data=static;static',  # Include static files
    '--add-data=uploads;uploads',  # Include uploads folder (create if exists)
    '--hidden-import=flask',
    '--hidden-import=flask_sqlalchemy',
    '--hidden-import=flask_login',
    '--hidden-import=cloudinary',
    '--hidden-import=cloudinary.uploader',
    '--hidden-import=requests',
    '--hidden-import=PIL',
    '--hidden-import=PIL.Image',
    '--hidden-import=PIL.ImageEnhance',
    '--hidden-import=PIL.ImageFilter',
    '--hidden-import=numpy',
    '--hidden-import=pandas',
    '--hidden-import=openpyxl',
    '--hidden-import=werkzeug',
    '--hidden-import=jinja2',
    '--hidden-import=dotenv',
    '--collect-all=flask',
    '--collect-all=cloudinary',
    '--collect-all=rembg',  # Optional: only if you want rembg included
    '--collect-all=onnxruntime',  # Required for rembg
    '--clean',
    '--noconfirm',
]

# Add hidden imports for optional packages
try:
    import rembg
    opts.append('--hidden-import=rembg')
    opts.append('--hidden-import=rembg.session_factory')
except ImportError:
    pass

try:
    import qrcode
    opts.append('--hidden-import=qrcode')
except ImportError:
    pass

# Run PyInstaller
PyInstaller.__main__.run(opts)

print("\n✅ Build complete! Executable is in the 'dist' folder.")