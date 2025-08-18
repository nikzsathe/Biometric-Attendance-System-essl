@echo off
echo ========================================
echo    Simple EXE Builder
echo ========================================
echo.
echo Installing PyInstaller...
pip install pyinstaller

echo.
echo Building executable...
pyinstaller --onefile --console --name=AttendanceSystem --add-data="templates;templates" --add-data="attendance.db;." web_app.py

echo.
echo ========================================
echo BUILD COMPLETE!
echo ========================================
echo.
echo Your executable is in the 'dist' folder:
echo - AttendanceSystem.exe
echo.
echo To use on other PCs:
echo 1. Copy AttendanceSystem.exe to target PC
echo 2. Copy attendance.db to target PC  
echo 3. Run AttendanceSystem.exe
echo 4. Open browser to http://localhost:5000
echo.
pause

