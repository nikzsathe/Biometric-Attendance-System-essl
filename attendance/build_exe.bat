@echo off
echo ========================================
echo    Building Attendance System EXE
echo ========================================
echo.
echo This will create a standalone executable
echo that can run on any Windows PC!
echo.
echo Press any key to start building...
pause >nul

REM Run the build script
python build_exe.py

echo.
echo Build process completed!
echo Check the output above for results.
echo.
pause

