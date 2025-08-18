#!/usr/bin/env python3
"""
Build Script for Attendance System Executable
This script creates a standalone .exe file that can run on any Windows PC
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def install_pyinstaller():
    """Install PyInstaller if not already installed"""
    try:
        import PyInstaller
        print("✓ PyInstaller already installed")
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("✓ PyInstaller installed successfully")

def create_spec_file():
    """Create PyInstaller spec file for the Flask app"""
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['web_app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('templates', 'templates'),
        ('static', 'static'),
        ('attendance.db', '.'),
        ('requirements.txt', '.'),
        ('README.md', '.'),
    ],
    hiddenimports=[
        'flask',
        'flask_sqlalchemy',
        'sqlite3',
        'datetime',
        'timedelta',
        'zk',
        'openpyxl',
        'werkzeug',
        'jinja2',
        'markupsafe',
        'itsdangerous',
        'click',
        'blinker',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='AttendanceSystem',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
'''
    
    with open('attendance_system.spec', 'w') as f:
        f.write(spec_content)
    
    print("✓ PyInstaller spec file created")

def build_executable():
    """Build the executable using PyInstaller"""
    print("Building executable... This may take several minutes...")
    
    # Run PyInstaller
    subprocess.check_call([
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--onefile",
        "--console",
        "--name=AttendanceSystem",
        "--add-data=templates;templates",
        "--add-data=static;static",
        "--add-data=attendance.db;.",
        "--add-data=requirements.txt;.",
        "--add-data=README.md;.",
        "--hidden-import=flask",
        "--hidden-import=flask_sqlalchemy", 
        "--hidden-import=sqlite3",
        "--hidden-import=datetime",
        "--hidden-import=timedelta",
        "--hidden-import=zk",
        "--hidden-import=openpyxl",
        "--hidden-import=werkzeug",
        "--hidden-import=jinja2",
        "--hidden-import=markupsafe",
        "--hidden-import=itsdangerous",
        "--hidden-import=click",
        "--hidden-import=blinker",
        "web_app.py"
    ])
    
    print("✓ Executable built successfully!")

def create_installer_script():
    """Create a simple installer script"""
    installer_content = '''@echo off
echo ========================================
echo    Attendance System Installer
echo ========================================
echo.
echo Company: Absolute Global Outsourcing
echo Developer: Nikhil Sathe
echo.
echo Installing Attendance System...
echo.

REM Create installation directory
set INSTALL_DIR=%USERPROFILE%\\Desktop\\AttendanceSystem
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

REM Copy executable and files
echo Copying files...
copy "AttendanceSystem.exe" "%INSTALL_DIR%\\"
copy "attendance.db" "%INSTALL_DIR%\\"
copy "requirements.txt" "%INSTALL_DIR%\\"
copy "README.md" "%INSTALL_DIR%\\"

REM Create desktop shortcut
echo Creating desktop shortcut...
echo @echo off > "%USERPROFILE%\\Desktop\\Start Attendance System.bat"
echo cd /d "%INSTALL_DIR%" >> "%USERPROFILE%\\Desktop\\Start Attendance System.bat"
echo start AttendanceSystem.exe >> "%USERPROFILE%\\Desktop\\Start Attendance System.bat"
echo pause >> "%USERPROFILE%\\Desktop\\Start Attendance System.bat"

echo.
echo ========================================
echo Installation Complete!
echo ========================================
echo.
echo Files installed to: %INSTALL_DIR%
echo Desktop shortcut created: Start Attendance System.bat
echo.
echo To start the system:
echo 1. Double-click "Start Attendance System.bat" on desktop
echo 2. Or go to %INSTALL_DIR% and run AttendanceSystem.exe
echo 3. Open browser and go to: http://localhost:5000
echo 4. Login with: admin / admin123
echo.
echo Press any key to close...
pause >nul
'''
    
    with open('install_attendance_system.bat', 'w') as f:
        f.write(installer_content)
    
    print("✓ Installer script created")

def main():
    """Main build process"""
    print("=" * 50)
    print("Attendance System Executable Builder")
    print("=" * 50)
    print()
    
    try:
        # Step 1: Install PyInstaller
        install_pyinstaller()
        print()
        
        # Step 2: Create spec file
        create_spec_file()
        print()
        
        # Step 3: Build executable
        build_executable()
        print()
        
        # Step 4: Create installer
        create_installer_script()
        print()
        
        print("=" * 50)
        print("BUILD COMPLETE!")
        print("=" * 50)
        print()
        print("Files created:")
        print("✓ AttendanceSystem.exe (in dist/ folder)")
        print("✓ install_attendance_system.bat")
        print()
        print("To distribute to other PCs:")
        print("1. Copy AttendanceSystem.exe to the target PC")
        print("2. Copy install_attendance_system.bat to the target PC")
        print("3. Run install_attendance_system.bat on the target PC")
        print()
        print("The executable will work on any Windows PC without Python installed!")
        
    except Exception as e:
        print(f"❌ Error during build: {e}")
        print("Please check the error message and try again.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

