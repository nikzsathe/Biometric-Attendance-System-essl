@echo off
echo 🚀 Preparing Attendance System for Cloud Deployment...

REM Create deployment directory
set DEPLOY_DIR=attendance-cloud
echo 📁 Creating deployment directory: %DEPLOY_DIR%
if exist %DEPLOY_DIR% rmdir /s /q %DEPLOY_DIR%
mkdir %DEPLOY_DIR%

REM Copy necessary files
echo 📋 Copying application files...
copy web_app.py %DEPLOY_DIR%\
copy app.py %DEPLOY_DIR%\
copy passenger_wsgi.py %DEPLOY_DIR%\
copy requirements.txt %DEPLOY_DIR%\
xcopy templates %DEPLOY_DIR%\templates\ /E /I /Y
copy attendance.db %DEPLOY_DIR%\

REM Create .htaccess for cPanel
echo 🔧 Creating .htaccess file...
echo RewriteEngine On > %DEPLOY_DIR%\.htaccess
echo RewriteCond %%{REQUEST_FILENAME} !-f >> %DEPLOY_DIR%\.htaccess
echo RewriteRule ^(.*)$ passenger_wsgi.py/$1 [QSA,L] >> %DEPLOY_DIR%\.htaccess
echo. >> %DEPLOY_DIR%\.htaccess
echo # Security headers >> %DEPLOY_DIR%\.htaccess
echo Header always set X-Content-Type-Options nosniff >> %DEPLOY_DIR%\.htaccess
echo Header always set X-Frame-Options DENY >> %DEPLOY_DIR%\.htaccess
echo Header always set X-XSS-Protection "1; mode=block" >> %DEPLOY_DIR%\.htaccess

REM Create deployment info file
echo 📝 Creating deployment info...
echo ATTENDANCE SYSTEM - CLOUD DEPLOYMENT > %DEPLOY_DIR%\DEPLOYMENT_INFO.txt
echo. >> %DEPLOY_DIR%\DEPLOYMENT_INFO.txt
echo Files included: >> %DEPLOY_DIR%\DEPLOYMENT_INFO.txt
echo - web_app.py: Main application >> %DEPLOY_DIR%\DEPLOYMENT_INFO.txt
echo - app.py: Production entry point >> %DEPLOY_DIR%\DEPLOYMENT_INFO.txt
echo - passenger_wsgi.py: cPanel WSGI file >> %DEPLOY_DIR%\DEPLOYMENT_INFO.txt
echo - requirements.txt: Python dependencies >> %DEPLOY_DIR%\DEPLOYMENT_INFO.txt
echo - templates/: HTML templates >> %DEPLOY_DIR%\DEPLOYMENT_INFO.txt
echo - attendance.db: Database file >> %DEPLOY_DIR%\DEPLOYMENT_INFO.txt
echo - .htaccess: Server configuration >> %DEPLOY_DIR%\DEPLOYMENT_INFO.txt
echo. >> %DEPLOY_DIR%\DEPLOYMENT_INFO.txt
echo Deployment steps: >> %DEPLOY_DIR%\DEPLOYMENT_INFO.txt
echo 1. Upload all files to cPanel >> %DEPLOY_DIR%\DEPLOYMENT_INFO.txt
echo 2. Set Python version to 3.9 or 3.10 >> %DEPLOY_DIR%\DEPLOYMENT_INFO.txt
echo 3. Set entry point to passenger_wsgi.py >> %DEPLOY_DIR%\DEPLOYMENT_INFO.txt
echo 4. Install dependencies: pip install -r requirements.txt >> %DEPLOY_DIR%\DEPLOYMENT_INFO.txt
echo 5. Set environment variables in cPanel >> %DEPLOY_DIR%\DEPLOYMENT_INFO.txt
echo 6. Restart application >> %DEPLOY_DIR%\DEPLOYMENT_INFO.txt
echo. >> %DEPLOY_DIR%\DEPLOYMENT_INFO.txt
echo Environment variables needed: >> %DEPLOY_DIR%\DEPLOYMENT_INFO.txt
echo - SECRET_KEY >> %DEPLOY_DIR%\DEPLOYMENT_INFO.txt
echo - MAIL_SERVER, MAIL_PORT, MAIL_USE_TLS >> %DEPLOY_DIR%\DEPLOYMENT_INFO.txt
echo - MAIL_USERNAME, MAIL_PASSWORD >> %DEPLOY_DIR%\DEPLOYMENT_INFO.txt
echo - DEVICE_IP, DEVICE_PORT >> %DEPLOY_DIR%\DEPLOYMENT_INFO.txt
echo. >> %DEPLOY_DIR%\DEPLOYMENT_INFO.txt
echo Access URL: yourdomain.com/attendance-system >> %DEPLOY_DIR%\DEPLOYMENT_INFO.txt

echo ✅ Deployment package created successfully!
echo 📦 Upload the '%DEPLOY_DIR%' folder to your cPanel
echo 📖 Check DEPLOYMENT_INFO.txt for detailed instructions
echo 🌐 Your app will be accessible at: yourdomain.com/attendance-system
pause

