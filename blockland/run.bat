@echo off
REM Starts Blockland at http://127.0.0.1:8000  (Ganache and CouchDB must be running)
cd /d "%~dp0"
call venv\Scripts\activate.bat
python manage.py runserver
pause
