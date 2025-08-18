@echo off
echo ========================================
echo    Attendance System Web Application
echo ========================================
echo.
echo Company: Absolute Global Outsourcing
echo Developer: Nikhil Sathe
echo.
echo Starting Flask application...
echo.

REM Change to the attendance directory first
cd /d "%~dp0"

REM Try to use Python from PATH first, then fallback to specific Python path
python --version >nul 2>&1
if %errorlevel% == 0 (
    echo Using Python from PATH...
    python web_app.py
) else (
    echo Python not found in PATH, trying specific Python path...
    "C:\Users\nikhi\AppData\Local\Programs\Python\Python313\python.exe" web_app.py
)

echo.
echo If the application started successfully, open your browser and go to: http://localhost:5000
echo.
echo Default Admin Login:
echo Username: admin
echo Password: admin123
echo.
echo Press any key to close this window...
pause >nul

