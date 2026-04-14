@echo off
title Quick Fix for Werkzeug
color 0A

echo ============================================================
echo     Quick Fix for Werkzeug Compatibility
echo ============================================================
echo.

cd /d "%~dp0"

echo Uninstalling problematic packages...
pip uninstall flask werkzeug flask-login -y

echo Installing correct versions...
pip install Werkzeug==2.2.3
pip install Flask==2.2.5
pip install Flask-Login==0.6.2
pip install Jinja2==3.1.2

echo.
echo Testing installation...
python -c "from werkzeug.urls import url_decode; print('✓ Werkzeug OK')"
python -c "from flask_login import LoginManager; print('✓ Flask-Login OK')"
python -c "import flask; print('✓ Flask OK')"

echo.
echo ============================================================
echo Fix complete! You can now run: python app.py
echo ============================================================
echo.
pause