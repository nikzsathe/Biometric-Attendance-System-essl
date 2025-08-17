# Attendance Management System

A comprehensive attendance management system built with Python Flask, featuring biometric device integration and a modern web interface.

## Company Information
- **Company Name**: Absolute Global Outsourcing
- **Developer**: Nikhil Sathe

## Features

### 🔐 **Admin Authentication System**
- Secure admin login with session management
- Protected routes requiring authentication
- Admin logout functionality
- Default credentials: `admin` / `admin123`

### 👥 **User Management**
- View all employees with detailed information
- Edit employee details (name, company, shift times, shift type)
- Add new employees
- Delete employees (with attendance record cleanup)
- Company name and shift configuration

### 📊 **Attendance Tracking**
- Real-time attendance data from biometric devices
- Check-in/check-out time pairing
- Working hours calculation (including night shift support)
- Filter attendance by employee or date
- Comprehensive attendance history

### 🖥️ **Device Integration**
- ZK biometric device support
- Device connection testing
- Pull users and attendance data from devices
- Network device discovery
- Real-time data synchronization

### 🎨 **Modern Web Interface**
- Responsive Bootstrap 5 design
- Interactive data tables with search/filter
- Real-time updates and notifications
- Professional company branding
- Mobile-friendly design

## Installation & Setup

### Prerequisites
- Python 3.7+
- pip package manager

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Application
```bash
# Option 1: Direct Python execution
python web_app.py

# Option 2: Use the batch file (Windows)
start_web.bat
```

### 3. Access the System
- Open your browser and go to: `http://localhost:5000`
- You'll be redirected to the admin login page
- Use the default credentials: `admin` / `admin123`

## Configuration

### Admin Credentials
You can change the default admin credentials in `web_app.py`:
```python
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin123'  # Change this to a secure password
```

### Device Configuration
Update the default device settings in `web_app.py`:
```python
DEFAULT_DEVICE_IP = '192.168.1.201'
DEFAULT_DEVICE_PORT = 4370
```

## Database Schema

### Users Table
- `userid`: Primary key
- `name`: Employee name
- `company_name`: Company name
- `shift_start_time`: Shift start time
- `shift_end_time`: Shift end time
- `shift_type`: Day/Night shift
- `working_hours_per_day`: Daily working hours
- `created_date`: Account creation date

### Attendance Table
- `id`: Primary key
- `userid`: Foreign key to users
- `timestamp`: Attendance timestamp
- `check_in`: Check-in time
- `check_out`: Check-out time
- `working_hours`: Calculated working hours
- `created_date`: Record creation date

## Usage

### 1. **Admin Login**
- Access the system at `http://localhost:5000`
- Login with admin credentials
- Manage users and view attendance data

### 2. **User Management**
- Navigate to Users page
- Edit employee shift configurations
- Set night shift parameters for accurate working hours

### 3. **Device Integration**
- Go to Device page
- Test device connectivity
- Pull latest data from biometric devices

### 4. **Attendance Monitoring**
- View attendance records on Dashboard
- Filter attendance by employee or date
- Monitor working hours and shift compliance

## Security Features

- **Session Management**: Secure admin sessions
- **Route Protection**: All main routes require authentication
- **Password Hashing**: Secure password storage (SHA-256)
- **CSRF Protection**: Built-in Flask security features

## File Structure

```
attendance/
├── web_app.py              # Main Flask application
├── main.py                 # Command-line interface
├── attendance.db           # SQLite database
├── requirements.txt        # Python dependencies
├── start_web.bat          # Windows startup script
├── README.md              # This file
└── templates/             # HTML templates
    ├── admin_login.html   # Admin login page
    ├── base.html          # Base template
    ├── index.html         # Dashboard
    ├── users.html         # User management
    ├── attendance.html    # Attendance view
    └── device.html        # Device management
```

## Troubleshooting

### Common Issues

1. **ModuleNotFoundError: No module named 'zk'**
   - Install the correct library: `pip install pyzk`

2. **Database Connection Errors**
   - Ensure the application has write permissions
   - Check if the database file is locked

3. **Device Connection Issues**
   - Verify device IP and port settings
   - Check network connectivity
   - Ensure device is powered on and accessible

### Support
For technical support or questions, contact the development team.

---

**Developed by**: Nikhil Sathe  
**Company**: Absolute Global Outsourcing  
**Version**: 2.0 (with Admin Authentication)
