#!/bin/bash

# 🚀 Attendance System Cloud Deployment Script
# This script helps prepare your application for cloud deployment

echo "🚀 Preparing Attendance System for Cloud Deployment..."

# Create deployment directory
DEPLOY_DIR="attendance-cloud"
echo "📁 Creating deployment directory: $DEPLOY_DIR"
mkdir -p $DEPLOY_DIR

# Copy necessary files
echo "📋 Copying application files..."
cp web_app.py $DEPLOY_DIR/
cp app.py $DEPLOY_DIR/
cp passenger_wsgi.py $DEPLOY_DIR/
cp requirements.txt $DEPLOY_DIR/
cp -r templates $DEPLOY_DIR/
cp attendance.db $DEPLOY_DIR/

# Create .htaccess for cPanel
echo "🔧 Creating .htaccess file..."
cat > $DEPLOY_DIR/.htaccess << 'EOF'
RewriteEngine On
RewriteCond %{REQUEST_FILENAME} !-f
RewriteRule ^(.*)$ passenger_wsgi.py/$1 [QSA,L]

# Security headers
Header always set X-Content-Type-Options nosniff
Header always set X-Frame-Options DENY
Header always set X-XSS-Protection "1; mode=block"
EOF

# Create deployment info file
echo "📝 Creating deployment info..."
cat > $DEPLOY_DIR/DEPLOYMENT_INFO.txt << 'EOF'
ATTENDANCE SYSTEM - CLOUD DEPLOYMENT

Files included:
- web_app.py: Main application
- app.py: Production entry point
- passenger_wsgi.py: cPanel WSGI file
- requirements.txt: Python dependencies
- templates/: HTML templates
- attendance.db: Database file
- .htaccess: Server configuration

Deployment steps:
1. Upload all files to cPanel
2. Set Python version to 3.9 or 3.10
3. Set entry point to passenger_wsgi.py
4. Install dependencies: pip install -r requirements.txt
5. Set environment variables in cPanel
6. Restart application

Environment variables needed:
- SECRET_KEY
- MAIL_SERVER, MAIL_PORT, MAIL_USE_TLS
- MAIL_USERNAME, MAIL_PASSWORD
- DEVICE_IP, DEVICE_PORT

Access URL: yourdomain.com/attendance-system
EOF

# Set permissions
echo "🔐 Setting file permissions..."
chmod 755 $DEPLOY_DIR/passenger_wsgi.py
chmod 644 $DEPLOY_DIR/*.py
chmod 644 $DEPLOY_DIR/*.txt
chmod 644 $DEPLOY_DIR/.htaccess
chmod 666 $DEPLOY_DIR/attendance.db

echo "✅ Deployment package created successfully!"
echo "📦 Upload the '$DEPLOY_DIR' folder to your cPanel"
echo "📖 Check DEPLOYMENT_INFO.txt for detailed instructions"
echo "🌐 Your app will be accessible at: yourdomain.com/attendance-system"

