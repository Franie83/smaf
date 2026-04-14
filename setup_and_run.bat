@echo off
echo Installing required packages...
pip install -r requirements.txt
echo.
echo Starting Staff Management System...
echo.
python app.py
pause