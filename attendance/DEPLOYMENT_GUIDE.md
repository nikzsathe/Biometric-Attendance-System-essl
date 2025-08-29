# 🚀 Cloud Deployment Guide for Attendance System

## **cPanel Python App Deployment (Namecheap)**

### **Step 1: Prepare Your Local Files**

1. **Create a deployment folder:**
   ```bash
   mkdir attendance-cloud
   cd attendance-cloud
   ```

2. **Copy these files to the deployment folder:**
   - `web_app.py` - Main application
   - `app.py` - Production entry point
   - `passenger_wsgi.py` - cPanel WSGI file
   - `requirements.txt` - Python dependencies
   - `templates/` folder - HTML templates
   - `static/` folder - CSS, JS, images (if any)
   - `attendance.db` - Your database file

### **Step 2: cPanel Setup**

1. **Login to cPanel**
2. **Find "Python App" or "Python Selector"**
3. **Click "Create Application"**

### **Step 3: Application Configuration**

1. **Application Name:** `attendance-system`
2. **Python Version:** `3.9` or `3.10` (latest available)
3. **Application Root:** `/home/username/attendance-system`
4. **Application URL:** `yourdomain.com/attendance-system`
5. **Application Entry Point:** `passenger_wsgi.py`

### **Step 4: Upload Files**

1. **Use File Manager or FTP to upload your files**
2. **Upload to:** `/home/username/attendance-system/`
3. **Ensure file permissions:**
   - Files: `644`
   - Folders: `755`
   - `passenger_wsgi.py`: `755`

### **Step 5: Install Dependencies**

1. **In cPanel, go to "Terminal" or "SSH Access"**
2. **Navigate to your app directory:**
   ```bash
   cd /home/username/attendance-system
   ```

3. **Create virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

4. **Install requirements:**
   ```bash
   pip install -r requirements.txt
   ```

### **Step 6: Environment Variables**

**In cPanel, set these environment variables:**

1. **Go to "Environment Variables"**
2. **Add these variables:**
   ```
   SECRET_KEY=your-very-secure-secret-key-here
   MAIL_SERVER=smtp.gmail.com
   MAIL_PORT=587
   MAIL_USE_TLS=true
   MAIL_USERNAME=your-email@gmail.com
   MAIL_PASSWORD=your-app-password
   MAIL_DEFAULT_SENDER=your-email@gmail.com
   DEVICE_IP=your-device-ip
   DEVICE_PORT=4370
   ```

### **Step 7: Database Setup**

1. **Upload your `attendance.db` file**
2. **Ensure it's in the app directory**
3. **Set proper permissions:**
   ```bash
   chmod 666 attendance.db
   ```

### **Step 8: Start Application**

1. **In cPanel, go to "Python App"**
2. **Click "Restart" on your application**
3. **Check the logs for any errors**

### **Step 9: Access Your Application**

- **URL:** `https://yourdomain.com/attendance-system`
- **Default login:** Check your database for admin credentials

---

## **🌐 Making Machine Accessible on Cloud**

### **Option 1: Port Forwarding (Recommended)**

1. **Configure your router to forward port 4370**
2. **Set external port to internal IP of your machine**
3. **Use your public IP address in the app**

### **Option 2: VPN Solution**

1. **Set up a VPN server on your cloud**
2. **Connect your local machine to the VPN**
3. **Use local IP addresses within the VPN**

### **Option 3: Cloud-Based Device Management**

1. **Deploy a device management service on your cloud**
2. **Use web-based device configuration**
3. **Store device settings in the cloud database**

---

## **🔧 Troubleshooting**

### **Common Issues:**

1. **500 Internal Server Error:**
   - Check `passenger_wsgi.py` syntax
   - Verify Python version compatibility
   - Check application logs

2. **Module Not Found:**
   - Ensure all dependencies are installed
   - Check virtual environment activation
   - Verify `requirements.txt` contents

3. **Database Connection Error:**
   - Check file permissions on `attendance.db`
   - Verify database file path
   - Ensure database file is uploaded

4. **Application Won't Start:**
   - Check Python version compatibility
   - Verify entry point file name
   - Check application logs in cPanel

### **Logs Location:**
- **cPanel:** Python App → View Logs
- **File system:** `/home/username/attendance-system/logs/`

---

## **📱 Testing Your Cloud Deployment**

1. **Test basic functionality:**
   - Login system
   - User management
   - Attendance viewing

2. **Test device connectivity:**
   - Update device IP in environment variables
   - Test device pull/push operations

3. **Test email functionality:**
   - Verify SMTP settings
   - Test email notifications

---

## **🔒 Security Considerations**

1. **Change default secret key**
2. **Use HTTPS (SSL certificate)**
3. **Set strong admin passwords**
4. **Regular security updates**
5. **Database backup strategy**

---

## **📞 Support**

If you encounter issues:
1. Check cPanel error logs
2. Verify Python version compatibility
3. Ensure all dependencies are installed
4. Check file permissions
5. Verify environment variables

**Your attendance system should now be accessible from anywhere in the world!** 🌍✨

