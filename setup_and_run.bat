@echo off
title Staff Management System - Setup and Launch
color 0A

echo ============================================================
echo     Staff Management System - Setup and Launch
echo ============================================================
echo.

REM Get the directory where this batch file is located
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo [INFO] Working directory: %CD%
echo.

REM Step 1: Check if Python is installed
echo [1/6] Checking Python installation...
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] Python is not installed!
    echo.
    echo Please install Python 3.10 or higher from:
    echo https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [SUCCESS] Found %PYTHON_VERSION%
echo.

REM Step 2: Upgrade pip
echo [2/6] Upgrading pip...
python -m pip install --upgrade pip --quiet
echo [SUCCESS] pip upgraded
echo.

REM Step 3: Fix Werkzeug compatibility
echo [3/6] Fixing package compatibility...
pip uninstall flask werkzeug flask-login -y >nul 2>&1
pip install Werkzeug==2.2.3 --quiet
pip install Flask==2.2.5 --quiet
pip install Flask-Login==0.6.2 --quiet
pip install Jinja2==3.1.2 --quiet
echo [SUCCESS] Core packages fixed
echo.

REM Step 4: Install other dependencies
echo [4/6] Installing other dependencies...
pip install Flask-SQLAlchemy==3.0.5 --quiet
pip install SQLAlchemy==2.0.21 --quiet
pip install psycopg2-binary==2.9.9 --quiet
pip install pandas==2.0.3 --quiet
pip install openpyxl==3.1.2 --quiet
pip install Pillow==10.0.1 --quiet
pip install numpy==1.24.3 --quiet
pip install cloudinary==1.36.0 --quiet
pip install requests==2.31.0 --quiet
pip install python-dotenv==1.0.0 --quiet
pip install python-dateutil==2.8.2 --quiet
pip install pywhatkit==5.4 --quiet
pip install rembg==2.0.50 --quiet
pip install onnxruntime==1.15.1 --quiet
pip install uvicorn==0.23.2 --quiet
echo [SUCCESS] All dependencies installed
echo.

REM Step 5: Create required folders
echo [5/6] Creating required folders...
if not exist "staff_images" mkdir staff_images
if not exist "staff_signatures" mkdir staff_signatures
if not exist "clean_signatures" mkdir clean_signatures
if not exist "temp" mkdir temp
if not exist "uploads" mkdir uploads
if not exist "logs" mkdir logs
if not exist "instance" mkdir instance
echo [SUCCESS] Folders created
echo.

REM Step 6: Check config and license
echo [6/6] Checking configuration...

if exist "config.py" (
    echo [SUCCESS] config.py found
) else (
    echo [WARNING] config.py not found, creating default...
    (
        echo import os
        echo.
        echo class Config:
        echo     SECRET_KEY = 'dev-secret-key-change-in-production'
        echo     SQLALCHEMY_DATABASE_URI = 'sqlite:///staff_management.db'
        echo     SQLALCHEMY_TRACK_MODIFICATIONS = False
        echo     STAFF_IMAGES_FOLDER = 'staff_images'
        echo     STAFF_SIGNATURES_FOLDER = 'staff_signatures'
        echo     CLEAN_SIGNATURES_FOLDER = 'clean_signatures'
        echo     CLOUDINARY_CLOUD_NAME = ''
        echo     CLOUDINARY_API_KEY = ''
        echo     CLOUDINARY_API_SECRET = ''
        echo     MAX_CONTENT_LENGTH = 50 * 1024 * 1024
    ) > config.py
    echo [SUCCESS] Default config.py created
)

if exist "license.lic" (
    echo [SUCCESS] License file found
) else (
    echo [WARNING] License file not found. You may need to activate.
)

echo.
echo ============================================================
echo Starting Staff Management System...
echo ============================================================
echo.

REM Open a new window to run the server (fixed quotes)
start "Staff Management Server" cmd /k "cd /d %SCRIPT_DIR% && python app.py"

REM Wait for server to start
echo Waiting for server to start (5 seconds)...
timeout /t 5 /nobreak >nul

REM Open browser and make it active
echo Opening browser at http://localhost:5000
start "" "http://localhost:5000"

echo.
echo ============================================================
echo Server is running at: http://localhost:5000
echo.
echo A new window opened for the server. Do NOT close it.
echo Close that window to stop the server.
echo ============================================================
echo.

exit