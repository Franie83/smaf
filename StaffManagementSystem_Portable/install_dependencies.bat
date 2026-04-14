@echo off
echo Installing dependencies from local cache...
pip install --no-index --find-links=packages -r requirements.txt
pause
