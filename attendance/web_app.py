from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
import sqlite3
from datetime import datetime, timedelta
import os
from zk import ZK
import socket
import hashlib
import secrets

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this in production

# Company name constant
COMPANY_NAME = "Absolute Global Outsourcing"

# Context processor to make COMPANY_NAME available in all templates
@app.context_processor
def inject_company_name():
    return {'COMPANY_NAME': COMPANY_NAME}

# Database path
DB_PATH = 'attendance.db'

# Device configuration
DEFAULT_DEVICE_IP = '192.168.1.201'
DEFAULT_DEVICE_PORT = 4370

# Admin credentials (you can change these)
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin123'  # Change this to a secure password

# Developer name
DEVELOPER_NAME = 'Nikhil Sathe'

def hash_password(password):
    """Hash a password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_admin(username, password):
    """Verify admin credentials"""
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        return True
    return False

def login_required(f):
    """Decorator to require admin login for protected routes"""
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

def get_db_connection():
    """Create a database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def setup_db():
    """Initialize database and create tables if they don't exist"""
    conn = get_db_connection()
    c = conn.cursor()
    
    # Create users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        userid INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        company_name TEXT DEFAULT 'Absolute Global Outsourcing',
        shift_start_time TEXT DEFAULT '09:00',
        shift_end_time TEXT DEFAULT '18:00',
        shift_type TEXT DEFAULT 'day',
        working_hours_per_day REAL DEFAULT 8.0,
        monthly_salary REAL DEFAULT 15000.0,
        created_date TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Create attendance table
    c.execute('''CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        userid INTEGER NOT NULL,
        timestamp TEXT NOT NULL,
        check_in TEXT,
        check_out TEXT,
        working_hours REAL DEFAULT 0.0,
        status TEXT DEFAULT 'present',
        FOREIGN KEY (userid) REFERENCES users (userid)
    )''')
    
    # Create companies table
    c.execute('''CREATE TABLE IF NOT EXISTS companies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        description TEXT,
        created_date TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Create holidays table
    c.execute('''CREATE TABLE IF NOT EXISTS holidays (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        is_public_holiday BOOLEAN DEFAULT 1,
        created_date TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Create attendance_marking table
    c.execute('''CREATE TABLE IF NOT EXISTS attendance_marking (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        userid INTEGER NOT NULL,
        date TEXT NOT NULL,
        status TEXT NOT NULL,
        working_hours REAL DEFAULT 0.0,
        overtime_hours REAL DEFAULT 0.0,
        late_minutes INTEGER DEFAULT 0,
        remarks TEXT,
        marked_by TEXT DEFAULT 'system',
        created_date TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (userid) REFERENCES users (userid),
        UNIQUE(userid, date)
    )''')
    
    # Create salary_calculations table
    c.execute('''CREATE TABLE IF NOT EXISTS salary_calculations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        userid INTEGER NOT NULL,
        month TEXT NOT NULL,
        year INTEGER NOT NULL,
        total_days INTEGER DEFAULT 0,
        present_days INTEGER DEFAULT 0,
        absent_days INTEGER DEFAULT 0,
        leave_days INTEGER DEFAULT 0,
        total_working_hours REAL DEFAULT 0.0,
        overtime_hours REAL DEFAULT 0.0,
        basic_salary REAL DEFAULT 0.0,
        overtime_pay REAL DEFAULT 0.0,
        deductions REAL DEFAULT 0.0,
        net_salary REAL DEFAULT 0.0,
        calculated_date TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (userid) REFERENCES users (userid),
        UNIQUE(userid, month, year)
    )''')
    
    # Check if working_hours column exists in attendance table
    c.execute("PRAGMA table_info(attendance)")
    columns = [column[1] for column in c.fetchall()]
    
    if 'working_hours' not in columns:
        c.execute('ALTER TABLE attendance ADD COLUMN working_hours REAL DEFAULT 0.0')
        print("Added working_hours column to attendance table")
    
    if 'status' not in columns:
        c.execute('ALTER TABLE attendance ADD COLUMN status TEXT DEFAULT "present"')
        print("Added status column to attendance table")
    
    # Check if company_id column exists in users table
    c.execute("PRAGMA table_info(users)")
    user_columns = [column[1] for column in c.fetchall()]
    
    if 'company_id' not in user_columns:
        c.execute('ALTER TABLE users ADD COLUMN company_id INTEGER')
        print("Added company_id column to users table")
    
    if 'monthly_salary' not in user_columns:
        c.execute('ALTER TABLE users ADD COLUMN monthly_salary REAL DEFAULT 15000.0')
        print("Added monthly_salary column to users table")
    
    # Insert default companies
    c.execute('INSERT OR IGNORE INTO companies (name, description) VALUES (?, ?)', 
              ('Absolute Global Outsourcing', 'Main company'))
    c.execute('INSERT OR IGNORE INTO companies (name, description) VALUES (?, ?)', 
              ('Default Company', 'Default company for existing users'))
    
    # Update company_id for existing users
    c.execute('''UPDATE users SET company_id = (
        SELECT id FROM companies WHERE companies.name = users.company_name
    ) WHERE company_id IS NULL''')
    
    # Insert default holidays (2025)
    default_holidays = [
        ('2025-01-26', 'Republic Day', 'National Holiday'),
        ('2025-08-15', 'Independence Day', 'National Holiday'),
        ('2025-10-02', 'Gandhi Jayanti', 'National Holiday'),
        ('2025-12-25', 'Christmas Day', 'Public Holiday'),
        ('2025-01-01', 'New Year Day', 'Public Holiday'),
        ('2025-05-01', 'Labour Day', 'Public Holiday'),
    ]
    
    for holiday in default_holidays:
        c.execute('INSERT OR IGNORE INTO holidays (date, name, description) VALUES (?, ?, ?)', holiday)
    
    # Add some sample users if table is empty
    c.execute('SELECT COUNT(*) FROM users')
    if c.fetchone()[0] == 0:
        sample_users = [
            (1, 'Nikhil Sathe', 'Absolute Global Outsourcing', '04:00', '20:00', 'night', 8.0, 25000.0),
            (12, 'Akash Gaikwad', 'Absolute Global Outsourcing', '04:00', '19:00', 'night', 8.0, 20000.0),
            (13, 'Shubham Dabhane', 'Absolute Global Outsourcing', '19:00', '04:00', 'night', 8.0, 22000.0),
            (14, 'Shrutika Gaikwad', 'Absolute Global Outsourcing', '04:00', '20:00', 'night', 8.0, 18000.0),
            (15, 'Manoj Yadav', 'Absolute Global Outsourcing', '04:00', '20:00', 'night', 8.0, 21000.0),
            (41, 'Rohit Sahani', 'Absolute Global Outsourcing', '04:00', '19:00', 'night', 8.0, 23000.0)
        ]
        
        for user in sample_users:
            c.execute('''INSERT OR REPLACE INTO users 
                        (userid, name, company_name, shift_start_time, shift_end_time, shift_type, working_hours_per_day, monthly_salary) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', user)
        
        # Set company_id for sample users
        c.execute('''UPDATE users SET company_id = (
            SELECT id FROM companies WHERE companies.name = 'Absolute Global Outsourcing'
        )''')
        
        print("Added sample users to database")
    
    # Add sample attendance records if table is empty
    c.execute('SELECT COUNT(*) FROM attendance')
    if c.fetchone()[0] == 0:
        # Sample attendance records for demonstration
        sample_attendance = [
            # Today's records - Night shift pattern
            (1, '2025-08-17 19:30:00', '2025-08-17 19:30:00', '2025-08-18 04:30:00', 9.0),
            (12, '2025-08-17 19:00:00', '2025-08-17 19:00:00', '2025-08-18 04:00:00', 9.0),
            (13, '2025-08-17 19:30:00', '2025-08-17 19:30:00', '2025-08-18 04:30:00', 9.0),
            (14, '2025-08-17 19:00:00', '2025-08-17 19:00:00', '2025-08-18 04:00:00', 9.0),
            (15, '2025-08-17 19:30:00', '2025-08-17 19:30:00', '2025-08-18 04:30:00', 9.0),
            (41, '2025-08-17 19:00:00', '2025-08-17 19:00:00', '2025-08-18 04:00:00', 9.0),
            
            # Previous day examples - Night shift pattern
            (1, '2025-08-16 19:30:00', '2025-08-16 19:30:00', '2025-08-17 04:30:00', 9.0),
            (12, '2025-08-16 19:00:00', '2025-08-16 19:00:00', '2025-08-17 04:00:00', 9.0),
            (13, '2025-08-16 19:30:00', '2025-08-16 19:30:00', '2025-08-17 04:30:00', 9.0),
            (14, '2025-08-16 19:00:00', '2025-08-16 19:00:00', '2025-08-17 04:00:00', 9.0),
            (15, '2025-08-16 19:30:00', '2025-08-16 19:30:00', '2025-08-17 04:30:00', 9.0),
            (41, '2025-08-16 19:00:00', '2025-08-16 19:00:00', '2025-08-17 04:00:00', 9.0),
        ]
        
        for record in sample_attendance:
            c.execute('''INSERT INTO attendance 
                        (userid, timestamp, check_in, check_out, working_hours) 
                        VALUES (?, ?, ?, ?, ?)''', record)
        
        print("Added sample attendance records to database")
    
    conn.commit()
    conn.close()
    print("Database setup completed!")

def test_device_connection(ip, port=4370, timeout=5):
    """Test if a device is reachable at the given IP and port"""
    try:
        print(f"Testing connection to {ip}:{port}...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        sock.close()
        
        if result == 0:
            print(f"✓ Connection to {ip}:{port} successful")
            return True
        else:
            print(f"✗ Connection to {ip}:{port} failed (error code: {result})")
            return False
    except Exception as e:
        print(f"✗ Connection test error: {e}")
        return False

def pull_data_from_device(device_ip, device_port):
    """Pull users and attendance data from device"""
    try:
        # Test connection first
        if not test_device_connection(device_ip, device_port):
            return False, "Device connection failed"
        
        # Import ZK library
        try:
            from zk import ZK, const
        except ImportError:
            return False, "ZK library not available. Please install it with: pip install pyzk"
        
        # Connect to device
        print(f"Attempting to connect to ZK device at {device_ip}:{device_port}...")
        zk = ZK(device_ip, port=device_port, timeout=5)
        
        try:
            conn = zk.connect()
            if not conn:
                return False, f"Failed to establish ZK connection to {device_ip}:{device_port}"
            print(f"✓ ZK connection established successfully")
        except Exception as e:
            return False, f"ZK connection error: {str(e)}"
        
        try:
            # Get users
            users = conn.get_users()
            print(f"Found {len(users)} users on device")
            
            # Get attendance records
            attendance_records = conn.get_attendance()
            print(f"Found {len(attendance_records)} attendance records on device")
            
            # Process users
            db_conn = get_db_connection()
            cursor = db_conn.cursor()
            
            # Clear existing attendance only (preserve user data)
            cursor.execute('DELETE FROM attendance')
            
            # Insert or update users (preserve existing custom data)
            for user in users:
                # Check if user already exists
                existing_user = cursor.execute('SELECT * FROM users WHERE userid = ?', (user.user_id,)).fetchone()
                
                if existing_user:
                    # User exists - only update name if it changed, preserve all other custom data
                    if existing_user['name'] != user.name:
                        cursor.execute('UPDATE users SET name = ? WHERE userid = ?', (user.name, user.user_id))
                        print(f"Updated name for user {user.user_id}: {user.name}")
                else:
                    # New user - insert with default values
                    cursor.execute('''INSERT INTO users 
                        (userid, name, company_name, shift_start_time, shift_end_time, shift_type, working_hours_per_day, monthly_salary, created_date) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                        (user.user_id, user.name, 'Absolute Global Outsourcing', '09:00', '18:00', 'day', 8.0, 15000.0, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                    print(f"Added new user: {user.name} (ID: {user.user_id})")
            
            # Process attendance records for night shift employees
            # For night shifts: early morning times are check-out, evening times are check-in
            night_shift_employees = set()  # Track which employees are night shifts
            
            for record in attendance_records:
                user_id = record.user_id
                timestamp = record.timestamp
                
                # Check if this user is a night shift employee
                user_conn = get_db_connection()
                user_info = user_conn.execute('SELECT shift_type FROM users WHERE userid = ?', (user_id,)).fetchone()
                user_conn.close()
                
                is_night_shift = user_info and user_info['shift_type'] == 'night' if user_info else False
                
                if is_night_shift:
                    night_shift_employees.add(user_id)
                
                # Insert raw attendance record
                cursor.execute('''INSERT INTO attendance 
                    (userid, timestamp, check_in, check_out, working_hours) 
                    VALUES (?, ?, ?, ?, ?)''', 
                    (user_id, timestamp.strftime('%Y-%m-%d %H:%M:%S'), 
                     timestamp.strftime('%Y-%m-%d %H:%M:%S'), None, 0.0))
            
            # Now process the attendance records to properly assign check-in/check-out
            # Group records by user and date, but handle multiple punches intelligently
            cursor.execute('''SELECT userid, DATE(timestamp) as date, timestamp
                             FROM attendance 
                             ORDER BY userid, DATE(timestamp), timestamp''')
            
            all_records = cursor.fetchall()
            
            # Group records by user and date
            user_date_punches = {}
            for record in all_records:
                user_id = record['userid']
                date = record['date']
                timestamp = record['timestamp']
                
                if user_id not in user_date_punches:
                    user_date_punches[user_id] = {}
                if date not in user_date_punches[user_id]:
                    user_date_punches[user_id][date] = []
                
                user_date_punches[user_id][date].append({'timestamp': timestamp})
            
            # Process each user's daily punches
            for user_id, dates in user_date_punches.items():
                for date, punches in dates.items():
                    # Use intelligent punch processing
                    check_in_time, check_out_time = process_multiple_punches(user_id, date, punches)
                    
                    if check_in_time and check_out_time:
                        # Update the attendance records with proper check-in/check-out times
                        cursor.execute('''UPDATE attendance 
                                         SET check_in = ?, check_out = ? 
                                         WHERE userid = ? AND DATE(timestamp) = ?''', 
                                      (check_in_time, check_out_time, user_id, date))
                        
                        # Calculate working hours
                        try:
                            check_in_dt = datetime.strptime(check_in_time, '%Y-%m-%d %H:%M:%S')
                            check_out_dt = datetime.strptime(check_out_time, '%Y-%m-%d %H:%M:%S')
                            
                            # Get user's shift information
                            user_conn = get_db_connection()
                            user_info = user_conn.execute('SELECT shift_type FROM users WHERE userid = ?', (user_id,)).fetchone()
                            user_conn.close()
                            
                            is_night_shift = user_info and user_info['shift_type'] == 'night' if user_info else False
                            
                            # For night shifts, if check-out is earlier than check-in, add 24 hours
                            if is_night_shift and check_out_dt < check_in_dt:
                                check_out_dt += timedelta(days=1)
                            
                            # Calculate working hours
                            time_diff = check_out_dt - check_in_dt
                            working_hours = time_diff.total_seconds() / 3600.0
                            
                            # Cap working hours at 10 for night shifts
                            if is_night_shift and working_hours > 10.0:
                                working_hours = 10.0
                            
                            # Update working hours
                            cursor.execute('''UPDATE attendance 
                                             SET working_hours = ? 
                                             WHERE userid = ? AND DATE(timestamp) = ?''', 
                                          (working_hours, user_id, date))
                            
                            print(f"Calculated working hours for user {user_id}: {working_hours:.2f} hours")
                            
                        except Exception as e:
                            print(f"Error calculating working hours for user {user_id}: {e}")
            
            db_conn.commit()
            db_conn.close()
            
            # Properly disconnect from device
            if conn and hasattr(conn, 'disconnect'):
                try:
                    conn.disconnect()
                except:
                    pass
            
            if zk and hasattr(zk, 'disconnect'):
                try:
                    zk.disconnect()
                except:
                    pass
            
            return True, f"Successfully pulled {len(users)} users and {len(attendance_records)} attendance records"
            
        except Exception as e:
            # Properly disconnect from device on error
            if conn and hasattr(conn, 'disconnect'):
                try:
                    conn.disconnect()
                except:
                    pass
            
            if zk and hasattr(zk, 'disconnect'):
                try:
                    zk.disconnect()
                except:
                    pass
            
            return False, f"Error processing device data: {str(e)}"
            
    except Exception as e:
        return False, f"Error connecting to device: {str(e)}"

def sync_users_from_device(device_ip, device_port):
    """Sync only user data from device (preserve existing custom data)"""
    try:
        # Test connection first
        if not test_device_connection(device_ip, device_port):
            return False, "Device connection failed"
        
        # Import ZK library
        try:
            from zk import ZK, const
        except ImportError:
            return False, "ZK library not available. Please install it with: pip install pyzk"
        
        # Connect to device
        zk = ZK(device_ip, port=device_port, timeout=5)
        conn = zk.connect()
        
        if not conn:
            return False, "Failed to connect to device"
        
        try:
            # Get users from device
            users = conn.get_users()
            print(f"Found {len(users)} users on device")
            
            # Process users
            db_conn = get_db_connection()
            cursor = db_conn.cursor()
            
            users_added = 0
            users_updated = 0
            
            # Insert or update users (preserve existing custom data)
            for user in users:
                # Check if user already exists
                existing_user = cursor.execute('SELECT * FROM users WHERE userid = ?', (user.user_id,)).fetchone()
                
                if existing_user:
                    # User exists - only update name if it changed, preserve all other custom data
                    if existing_user['name'] != user.name:
                        cursor.execute('UPDATE users SET name = ? WHERE userid = ?', (user.name, user.user_id))
                        print(f"Updated name for user {user.user_id}: {user.name}")
                        users_updated += 1
                else:
                    # New user - insert with default values
                    cursor.execute('''INSERT INTO users 
                        (userid, name, company_name, shift_start_time, shift_end_time, shift_type, working_hours_per_day, monthly_salary, created_date) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                        (user.user_id, user.name, 'Absolute Global Outsourcing', '09:00', '18:00', 'day', 8.0, 15000.0, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                    print(f"Added new user: {user.name} (ID: {user.user_id})")
                    users_added += 1
            
            db_conn.commit()
            db_conn.close()
            
            # Properly disconnect from device
            if conn and hasattr(conn, 'disconnect'):
                try:
                    conn.disconnect()
                except:
                    pass
            
            if zk and hasattr(zk, 'disconnect'):
                try:
                    zk.disconnect()
                except:
                    pass
            
            return True, f"Successfully synced users: {users_added} added, {users_updated} updated"
            
        except Exception as e:
            # Properly disconnect from device on error
            if conn and hasattr(conn, 'disconnect'):
                try:
                    conn.disconnect()
                except:
                    pass
            
            if zk and hasattr(zk, 'disconnect'):
                try:
                    zk.disconnect()
                except:
                    pass
            
            return False, f"Error processing device data: {str(e)}"
            
    except Exception as e:
        return False, f"Error connecting to device: {str(e)}"

def pull_latest_data_from_device():
    """Pull latest data from the default device"""
    try:
        # Test connection first
        if not test_device_connection(DEFAULT_DEVICE_IP, DEFAULT_DEVICE_PORT):
            return False, f"Device at {DEFAULT_DEVICE_IP}:{DEFAULT_DEVICE_PORT} is not reachable"
        
        # Pull data
        success, message = pull_data_from_device(DEFAULT_DEVICE_IP, DEFAULT_DEVICE_PORT)
        return success, message
        
    except Exception as e:
        return False, f"Error pulling latest data: {str(e)}"

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if verify_admin(username, password):
            session['admin_logged_in'] = True
            session['admin_username'] = username
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password!', 'error')
    
    return render_template('admin_login.html', company_name=COMPANY_NAME, developer_name=DEVELOPER_NAME)

@app.route('/admin/logout')
def admin_logout():
    """Admin logout"""
    session.pop('admin_logged_in', None)
    session.pop('admin_username', None)
    flash('You have been logged out successfully!', 'success')
    return redirect(url_for('admin_login'))

@app.route('/')
def root():
    """Root route - redirect to admin login or dashboard"""
    if 'admin_logged_in' in session:
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('admin_login'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard page"""
    conn = get_db_connection()
    
    # Get total counts
    total_users = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    total_attendance = conn.execute('SELECT COUNT(*) FROM attendance').fetchone()[0]
    
    # Get today's attendance
    today = datetime.now().strftime('%Y-%m-%d')
    today_attendance = conn.execute('''SELECT COUNT(*) FROM attendance 
                                     WHERE DATE(timestamp) = ?''', (today,)).fetchone()[0]
    
    # Get recent attendance records
    recent_records = conn.execute('''SELECT u.name, a.timestamp, a.check_in 
                                   FROM attendance a 
                                   JOIN users u ON a.userid = u.userid 
                                   ORDER BY a.timestamp DESC LIMIT 10''').fetchall()
    
    # Check device status
    device_status = test_device_connection(DEFAULT_DEVICE_IP, DEFAULT_DEVICE_PORT)
    
    conn.close()
    
    return render_template('index.html', 
                         total_users=total_users,
                         total_attendance=total_attendance,
                         today_attendance=today_attendance,
                         recent_records=recent_records,
                         device_status=device_status,
                         device_ip=DEFAULT_DEVICE_IP,
                         device_port=DEFAULT_DEVICE_PORT,
                         company_name=COMPANY_NAME,
                         developer_name=DEVELOPER_NAME,
                         admin_username=session.get('admin_username'))

@app.route('/users')
@login_required
def users():
    """Users page"""
    conn = get_db_connection()
    users = conn.execute('''SELECT u.userid, u.name, u.company_name, u.shift_start_time, 
                           u.shift_end_time, u.shift_type, u.working_hours_per_day, u.monthly_salary, u.created_date,
                           c.name as company_display_name
                           FROM users u 
                           LEFT JOIN companies c ON u.company_id = c.id
                           ORDER BY u.name''').fetchall()
    
    # Get companies for the filter dropdown
    companies = conn.execute('SELECT * FROM companies ORDER BY name').fetchall()
    conn.close()
    
    return render_template('users.html', 
                         users=users, 
                         companies=companies,
                         company_name=COMPANY_NAME, 
                         developer_name=DEVELOPER_NAME, 
                         admin_username=session.get('admin_username'))

@app.route('/attendance')
@login_required
def attendance():
    """Attendance page"""
    # Import datetime at the function level to avoid scope issues
    from datetime import datetime, timedelta
    
    conn = get_db_connection()
    
    # Get filter parameters
    user_id = request.args.get('user_id', '')
    date = request.args.get('date', '')
    company_id = request.args.get('company_id', '')
    
    # Get attendance records based on filters
    if user_id:
        records = conn.execute('''SELECT u.name, u.userid, a.timestamp, a.check_in, a.check_out, 
                                   a.working_hours, c.name as company_name
                                   FROM attendance a 
                                   JOIN users u ON a.userid = u.userid 
                                   LEFT JOIN companies c ON u.company_id = c.id
                                   WHERE DATE(a.timestamp) = ? AND u.userid = ?
                                   ORDER BY a.timestamp DESC''', (date, user_id)).fetchall()
    elif company_id:
        records = conn.execute('''SELECT u.name, u.userid, a.timestamp, a.check_in, a.check_out, 
                                   a.working_hours, c.name as company_name
                                   FROM attendance a 
                                   JOIN users u ON a.userid = u.userid 
                                   LEFT JOIN companies c ON u.company_id = c.id
                                   WHERE DATE(a.timestamp) = ? AND u.company_id = ?
                                   ORDER BY a.timestamp DESC''', (date, company_id)).fetchall()
    else:
        records = conn.execute('''SELECT u.name, u.userid, a.timestamp, a.check_in, a.check_out, 
                                   a.working_hours, c.name as company_name
                                   FROM attendance a 
                                   JOIN users u ON a.userid = u.userid 
                                   LEFT JOIN companies c ON u.company_id = c.id
                                   WHERE DATE(a.timestamp) = ?
                                   ORDER BY a.timestamp DESC''', (date,)).fetchall()
    
    # Process records to add working hours and format data
    processed_records = []
    for record in records:
        record_dict = dict(record)
        
        # Use working hours from database if available, otherwise calculate
        if record_dict.get('working_hours') is not None and record_dict['working_hours'] > 0:
            # Use the stored working hours from database
            working_hours = record_dict['working_hours']
        else:
            # Calculate working hours if not available in database
            working_hours = 0.0
            
            if record_dict['check_in'] and record_dict['check_out']:
                try:
                    # Parse check-in and check-out times
                    check_in_str = str(record_dict['check_in'])
                    check_out_str = str(record_dict['check_out'])
                    
                    # Extract time part if it's a full datetime
                    if ' ' in check_in_str:
                        check_in_time = check_in_str.split(' ')[1]
                    else:
                        check_in_time = check_in_str
                        
                    if ' ' in check_out_str:
                        check_out_time = check_out_str.split(' ')[1]
                    else:
                        check_out_time = check_out_str
                    
                    # Check if check-in and check-out are the same time
                    if check_in_time == check_out_time:
                        # Same time means 0 working hours (single punch or incomplete record)
                        working_hours = 0.0
                    else:
                        # Parse times
                        check_in_parts = check_in_time.split(':')
                        check_out_parts = check_out_time.split(':')
                        
                        if len(check_in_parts) >= 2 and len(check_out_parts) >= 2:
                            try:
                                # Get user's shift information first
                                user_conn = get_db_connection()
                                user_shift = user_conn.execute('''SELECT shift_type, shift_start_time, shift_end_time 
                                                               FROM users WHERE userid = ?''', 
                                                            (record_dict['userid'],)).fetchone()
                                user_conn.close()
                                
                                # Parse time components
                                check_in_hour = int(check_in_parts[0])
                                check_in_minute = int(check_in_parts[1])
                                check_in_second = int(check_in_parts[2]) if len(check_in_parts) > 2 else 0
                                
                                check_out_hour = int(check_out_parts[0])
                                check_out_minute = int(check_out_parts[1])
                                check_out_second = int(check_out_parts[2]) if len(check_out_parts) > 2 else 0
                                
                                # For night shifts, the biometric device ALWAYS flips check-in and check-out
                                # So we need to ALWAYS swap them, not just when we detect a reversal
                                if user_shift and user_shift['shift_type'] == 'night':
                                    # For night shifts, ALWAYS swap the times:
                                    # What device shows as "check-in" (evening) is actually check-out
                                    # What device shows as "check-out" (morning) is actually check-in
                                    
                                    # Swap the times
                                    temp_hour = check_in_hour
                                    temp_minute = check_in_minute
                                    temp_second = check_in_second
                                    
                                    check_in_hour = check_out_hour
                                    check_in_minute = check_out_minute
                                    check_in_second = check_out_second
                                    
                                    check_out_hour = temp_hour
                                    check_out_minute = temp_minute
                                    check_out_second = temp_second
                                    
                                    print(f"Swapped times for night shift user {record_dict['userid']}: "
                                          f"Device check-in ({temp_hour:02d}:{temp_minute:02d}:{temp_second:02d}) → Real check-out, "
                                          f"Device check-out ({check_in_hour:02d}:{check_in_minute:02d}:{check_in_second:02d}) → Real check-in")
                                    
                                    # Now create proper datetime objects with correct dates
                                    # Check-in is on current day (morning, but actually evening after swap)
                                    check_in_date = datetime.now().date()
                                    # Check-out is on next day (evening, but actually morning after swap)
                                    check_out_date = check_in_date + timedelta(days=1)
                                    
                                    check_in_dt = datetime.combine(check_in_date, datetime.min.time().replace(
                                        hour=check_in_hour, minute=check_in_minute, second=check_in_second
                                    ))
                                    
                                    check_out_dt = datetime.combine(check_out_date, datetime.min.time().replace(
                                        hour=check_out_hour, minute=check_out_minute, second=check_out_second
                                    ))
                                    
                                    # For night shift, if check-out is earlier than check-in, add 1 day
                                    if check_out_dt < check_in_dt:
                                        check_out_dt += timedelta(days=1)
                                    
                                else:
                                    # For day shifts, use standard logic
                                    today = datetime.now().date()
                                    
                                    check_in_dt = datetime.combine(today, datetime.min.time().replace(
                                        hour=check_in_hour, minute=check_in_minute, second=check_in_second
                                    ))
                                    
                                    check_out_dt = datetime.combine(today, datetime.min.time().replace(
                                        hour=check_out_hour, minute=check_out_minute, second=check_out_second
                                    ))
                                    
                                    # For day shift, if check-out is earlier than check-in, it's likely next day
                                    if check_out_dt < check_in_dt:
                                        check_out_dt += timedelta(days=1)
                                
                                # Calculate the difference
                                time_diff = check_out_dt - check_in_dt
                                working_hours = time_diff.total_seconds() / 3600.0
                                
                                # Cap working hours at 10 for night shifts
                                if user_shift and user_shift['shift_type'] == 'night' and working_hours > 10.0:
                                    working_hours = 10.0
                                
                                # Format working hours to 2 decimal places
                                working_hours = round(working_hours, 2)
                                
                                # Store formatted time strings for display
                                record_dict['check_in_formatted'] = f"{check_in_hour:02d}:{check_in_minute:02d}:{check_in_second:02d}"
                                record_dict['check_out_formatted'] = f"{check_out_hour:02d}:{check_out_minute:02d}:{check_out_second:02d}"
                                
                            except Exception as e:
                                print(f"Error calculating working hours for user {record_dict['userid']}: {e}")
                                working_hours = 0.0
                                
                except Exception as e:
                    print(f"Error processing check-in/check-out times for user {record_dict['userid']}: {e}")
                    working_hours = 0.0
        
        # Add working hours to record
        record_dict['working_hours'] = working_hours
        
        # Format the record for display
        if record_dict['check_in']:
            if ' ' in str(record_dict['check_in']):
                record_dict['check_in_time'] = str(record_dict['check_in']).split(' ')[1]
            else:
                record_dict['check_in_time'] = str(record_dict['check_in'])
        else:
            record_dict['check_in_time'] = None
            
        if record_dict['check_out']:
            if ' ' in str(record_dict['check_out']):
                record_dict['check_out_time'] = str(record_dict['check_out']).split(' ')[1]
            else:
                record_dict['check_out_time'] = str(record_dict['check_out'])
        else:
            record_dict['check_out_time'] = None
        
        processed_records.append(record_dict)
    
    # Get all users for filter dropdown
    users = conn.execute('SELECT * FROM users ORDER BY name').fetchall()
    
    # Get all companies for filter dropdown
    companies = conn.execute('SELECT * FROM companies ORDER BY name').fetchall()
    
    # Get today's date for the template
    today_date = datetime.now().strftime('%Y-%m-%d')
    
    conn.close()
    
    return render_template('attendance.html', 
                         records=processed_records, 
                         users=users, 
                         companies=companies,
                         selected_user=user_id, 
                         selected_date=date,
                         selected_company=company_id,
                         today=today_date,
                         company_name=COMPANY_NAME,
                         developer_name=DEVELOPER_NAME,
                         admin_username=session.get('admin_username'))

@app.route('/device')
@login_required
def device():
    """Device management page"""
    return render_template('device.html', company_name=COMPANY_NAME, developer_name=DEVELOPER_NAME, admin_username=session.get('admin_username'))

@app.route('/companies')
@login_required
def companies():
    """Companies management page"""
    conn = get_db_connection()
    companies_list = conn.execute('SELECT * FROM companies ORDER BY name').fetchall()
    conn.close()
    return render_template('companies.html', companies=companies_list, company_name=COMPANY_NAME, developer_name=DEVELOPER_NAME, admin_username=session.get('admin_username'))

@app.route('/api/test_connection', methods=['POST'])
def test_connection():
    """API endpoint to test device connection"""
    data = request.get_json()
    ip = data.get('ip')
    port = int(data.get('port', 4370))
    
    if test_device_connection(ip, port):
        return jsonify({'success': True, 'message': f'Device at {ip}:{port} is reachable!'})
    else:
        return jsonify({'success': False, 'message': f'Device at {ip}:{port} is not reachable!'})

@app.route('/api/pull_data', methods=['POST'])
def api_pull_data():
    """API endpoint to pull data from device"""
    try:
        data = request.get_json()
        device_ip = data.get('device_ip', DEFAULT_DEVICE_IP)
        device_port = data.get('device_port', DEFAULT_DEVICE_PORT)
        
        success, message = pull_data_from_device(device_ip, device_port)
        
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'message': message})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/pull_latest_data', methods=['POST'])
def pull_latest_data():
    """API endpoint to pull latest data from default device"""
    success, message = pull_latest_data_from_device()
    return jsonify({'success': success, 'message': message})

@app.route('/api/sync_users_only', methods=['POST'])
def sync_users_only():
    """API endpoint to sync only user data from device (preserve existing custom data)"""
    try:
        device_ip = request.form.get('device_ip', DEFAULT_DEVICE_IP)
        device_port = int(request.form.get('device_port', DEFAULT_DEVICE_PORT))
        
        success, message = sync_users_from_device(device_ip, device_port)
        
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'message': message})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/users', methods=['GET'])
def get_users():
    """API endpoint to get all users"""
    try:
        conn = get_db_connection()
        users = conn.execute('''SELECT u.userid, u.name, u.company_name, u.shift_start_time, 
                               u.shift_end_time, u.shift_type, u.working_hours_per_day, u.monthly_salary, u.created_date,
                               c.name as company_display_name
                               FROM users u 
                               LEFT JOIN companies c ON u.company_id = c.id
                               ORDER BY u.name''').fetchall()
        conn.close()
        
        users_list = []
        for user in users:
            users_list.append({
                'userid': user['userid'],
                'name': user['name'],
                'company_name': user['company_name'],
                'company_display_name': user['company_display_name'] or user['company_name'],
                'shift_start_time': user['shift_start_time'],
                'shift_end_time': user['shift_end_time'],
                'shift_type': user['shift_type'],
                'working_hours_per_day': user['working_hours_per_day'],
                'monthly_salary': user['monthly_salary'],
                'created_date': user['created_date']
            })
        
        return jsonify({'success': True, 'users': users_list})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/users/<int:userid>', methods=['GET'])
def get_user(userid):
    """API endpoint to get a specific user"""
    try:
        conn = get_db_connection()
        user = conn.execute('''SELECT u.userid, u.name, u.company_name, u.shift_start_time, 
                              u.shift_end_time, u.shift_type, u.working_hours_per_day, u.monthly_salary, u.created_date,
                              c.name as company_display_name
                              FROM users u 
                              LEFT JOIN companies c ON u.company_id = c.id
                              WHERE u.userid = ?''', (userid,)).fetchone()
        conn.close()
        
        if user:
            return jsonify({
                'success': True, 
                'user': {
                    'userid': user['userid'],
                    'name': user['name'],
                    'company_name': user['company_name'],
                    'company_display_name': user['company_display_name'] or user['company_name'],
                    'shift_start_time': user['shift_start_time'],
                    'shift_end_time': user['shift_end_time'],
                                    'shift_type': user['shift_type'],
                'working_hours_per_day': user['working_hours_per_day'],
                'monthly_salary': user['monthly_salary'],
                'created_date': user['created_date']
                }
            })
        else:
            return jsonify({'success': False, 'message': 'User not found'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/users/<int:userid>', methods=['PUT'])
def update_user(userid):
    """API endpoint to update a user"""
    try:
        data = request.get_json()
        name = data.get('name')
        company_name = data.get('company_name', 'Default Company')
        shift_start_time = data.get('shift_start_time', '09:00:00')
        shift_end_time = data.get('shift_end_time', '18:00:00')
        shift_type = data.get('shift_type', 'day')
        working_hours_per_day = data.get('working_hours_per_day', 8.0)
        monthly_salary = data.get('monthly_salary', 15000.0)
        
        if not name:
            return jsonify({'success': False, 'message': 'Name is required'})
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute('SELECT userid FROM users WHERE userid = ?', (userid,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'message': 'User not found'})
        
        # Get or create company
        cursor.execute('SELECT id FROM companies WHERE name = ?', (company_name,))
        company = cursor.fetchone()
        
        if company:
            company_id = company['id']
        else:
            # Create new company if it doesn't exist
            cursor.execute('INSERT INTO companies (name, description) VALUES (?, ?)', 
                         (company_name, f'Company for user {name}'))
            company_id = cursor.lastrowid
        
        # Update user
        cursor.execute('''UPDATE users 
                         SET name = ?, company_name = ?, company_id = ?, shift_start_time = ?, 
                             shift_end_time = ?, shift_type = ?, working_hours_per_day = ?, monthly_salary = ?
                         WHERE userid = ?''', 
                      (name, company_name, company_id, shift_start_time, shift_end_time, 
                       shift_type, working_hours_per_day, monthly_salary, userid))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': f'User {name} updated successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/users/<int:userid>', methods=['DELETE'])
def delete_user(userid):
    """API endpoint to delete a user"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute('SELECT name FROM users WHERE userid = ?', (userid,))
        user = cursor.fetchone()
        if not user:
            conn.close()
            return jsonify({'success': False, 'message': 'User not found'})
        
        # Delete user's attendance records first
        cursor.execute('DELETE FROM attendance WHERE userid = ?', (userid,))
        cursor.execute('DELETE FROM attendance_marking WHERE userid = ?', (userid,))
        cursor.execute('DELETE FROM salary_calculations WHERE userid = ?', (userid,))
        
        # Delete user
        cursor.execute('DELETE FROM users WHERE userid = ?', (userid,))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': f'User {user["name"]} deleted successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/users', methods=['POST'])
def create_user():
    """API endpoint to create a new user"""
    try:
        data = request.get_json()
        userid = data.get('userid')
        name = data.get('name')
        company_name = data.get('company_name', 'Default Company')
        shift_start_time = data.get('shift_start_time', '09:00:00')
        shift_end_time = data.get('shift_end_time', '18:00:00')
        shift_type = data.get('shift_type', 'day')
        working_hours_per_day = data.get('working_hours_per_day', 8.0)
        monthly_salary = data.get('monthly_salary', 15000.0)
        
        if not userid or not name:
            return jsonify({'success': False, 'message': 'User ID and Name are required'})
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if user ID already exists
        cursor.execute('SELECT userid FROM users WHERE userid = ?', (userid,))
        if cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'message': 'User ID already exists'})
        
        # Get or create company
        cursor.execute('SELECT id FROM companies WHERE name = ?', (company_name,))
        company = cursor.fetchone()
        
        if company:
            company_id = company['id']
        else:
            # Create new company if it doesn't exist
            cursor.execute('INSERT INTO companies (name, description) VALUES (?, ?)', 
                         (company_name, f'Company for user {name}'))
            company_id = cursor.lastrowid
        
        # Create user
        cursor.execute('''INSERT INTO users (userid, name, company_name, company_id, shift_start_time, 
                                           shift_end_time, shift_type, working_hours_per_day, monthly_salary)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                      (userid, name, company_name, company_id, shift_start_time, shift_end_time, 
                       shift_type, working_hours_per_day, monthly_salary))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': f'User {name} created successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/stats')
def get_stats():
    """API endpoint to get statistics"""
    conn = get_db_connection()
    
    total_users = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    total_attendance = conn.execute('SELECT COUNT(*) FROM attendance').fetchone()[0]
    
    # Get today's attendance
    today = datetime.now().strftime('%Y-%m-%d')
    today_attendance = conn.execute('''SELECT COUNT(*) FROM attendance 
                                     WHERE DATE(timestamp) = ?''', (today,)).fetchone()[0]
    
    conn.close()
    
    return jsonify({
        'total_users': total_users,
        'total_attendance': total_attendance,
        'today_attendance': today_attendance
    })

@app.route('/api/companies', methods=['GET'])
def get_companies():
    """API endpoint to get all companies"""
    try:
        conn = get_db_connection()
        companies = conn.execute('SELECT * FROM companies ORDER BY name').fetchall()
        conn.close()
        
        companies_list = []
        for company in companies:
            companies_list.append({
                'id': company['id'],
                'name': company['name'],
                'description': company['description'],
                'created_date': company['created_date']
            })
        
        return jsonify({'success': True, 'companies': companies_list})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/companies/<int:company_id>', methods=['GET'])
def get_company(company_id):
    """API endpoint to get a specific company"""
    try:
        conn = get_db_connection()
        company = conn.execute('SELECT * FROM companies WHERE id = ?', (company_id,)).fetchone()
        conn.close()
        
        if company:
            return jsonify({
                'success': True, 
                'company': {
                    'id': company['id'],
                    'name': company['name'],
                    'description': company['description'],
                    'created_date': company['created_date']
                }
            })
        else:
            return jsonify({'success': False, 'message': 'Company not found'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/companies/<int:company_id>', methods=['PUT'])
def update_company(company_id):
    """API endpoint to update a company"""
    try:
        data = request.get_json()
        name = data.get('name')
        description = data.get('description', '')
        
        if not name:
            return jsonify({'success': False, 'message': 'Company name is required'})
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if company exists
        cursor.execute('SELECT id FROM companies WHERE id = ?', (company_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'message': 'Company not found'})
        
        # Check if name already exists for another company
        cursor.execute('SELECT id FROM companies WHERE name = ? AND id != ?', (name, company_id))
        if cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'message': 'Company name already exists'})
        
        # Update company
        cursor.execute('''UPDATE companies 
                         SET name = ?, description = ?
                         WHERE id = ?''', 
                      (name, description, company_id))
        
        # Update users with this company
        cursor.execute('''UPDATE users 
                         SET company_name = ?
                         WHERE company_id = ?''', (name, company_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': f'Company {name} updated successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/companies/<int:company_id>', methods=['DELETE'])
def delete_company(company_id):
    """API endpoint to delete a company"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if company exists
        cursor.execute('SELECT name FROM companies WHERE id = ?', (company_id,))
        company = cursor.fetchone()
        if not company:
            conn.close()
            return jsonify({'success': False, 'message': 'Company not found'})
        
        # Check if any users are using this company
        cursor.execute('SELECT COUNT(*) FROM users WHERE company_id = ?', (company_id,))
        user_count = cursor.fetchone()[0]
        
        if user_count > 0:
            conn.close()
            return jsonify({'success': False, 'message': f'Cannot delete company. {user_count} users are still assigned to this company.'})
        
        # Delete company
        cursor.execute('DELETE FROM companies WHERE id = ?', (company_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': f'Company {company["name"]} deleted successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/companies', methods=['POST'])
def create_company():
    """API endpoint to create a new company"""
    try:
        data = request.get_json()
        name = data.get('name')
        description = data.get('description', '')
        
        if not name:
            return jsonify({'success': False, 'message': 'Company name is required'})
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if company name already exists
        cursor.execute('SELECT id FROM companies WHERE name = ?', (name,))
        if cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'message': 'Company name already exists'})
        
        # Create company
        cursor.execute('''INSERT INTO companies (name, description)
                         VALUES (?, ?)''', 
                      (name, description))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': f'Company {name} created successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/recalculate_working_hours', methods=['POST'])
def recalculate_working_hours():
    """Recalculate working hours for all attendance records"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all attendance records with check-in and check-out times
        records = cursor.execute('''SELECT a.id, a.userid, a.check_in, a.check_out, u.shift_type
                                   FROM attendance a 
                                   JOIN users u ON a.userid = u.userid 
                                   WHERE a.check_in IS NOT NULL AND a.check_out IS NOT NULL''').fetchall()
        
        updated_count = 0
        
        for record in records:
            try:
                check_in_str = str(record['check_in'])
                check_out_str = str(record['check_out'])
                shift_type = record['shift_type']
                
                # Parse times
                if ' ' in check_in_str:
                    check_in_time = check_in_str.split(' ')[1]
                else:
                    check_in_time = check_in_str
                    
                if ' ' in check_out_str:
                    check_out_time = check_out_str.split(' ')[1]
                else:
                    check_out_time = check_out_str
                
                # Check if check-in and check-out are the same time
                if check_in_time == check_out_time:
                    working_hours = 0.0
                else:
                    # Parse time components
                    check_in_parts = check_in_time.split(':')
                    check_out_parts = check_out_time.split(':')
                    
                    if len(check_in_parts) >= 2 and len(check_out_parts) >= 2:
                        # Create datetime objects for calculation
                        today = datetime.now().date()
                        
                        check_in_hour = int(check_in_parts[0])
                        check_in_minute = int(check_in_parts[1])
                        check_in_second = int(check_in_parts[2]) if len(check_in_parts) > 2 else 0
                        
                        check_out_hour = int(check_out_parts[0])
                        check_out_minute = int(check_out_parts[1])
                        check_out_second = int(check_out_parts[2]) if len(check_out_parts) > 2 else 0
                        
                        check_in_dt = datetime.combine(today, datetime.min.time().replace(
                            hour=check_in_hour, minute=check_in_minute, second=check_in_second
                        ))
                        
                        check_out_dt = datetime.combine(today, datetime.min.time().replace(
                            hour=check_out_hour, minute=check_out_minute, second=check_out_second
                        ))
                        
                        # Handle night shift logic
                        if shift_type == 'night':
                            # For night shifts, the biometric device ALWAYS flips check-in and check-out
                            # So we need to ALWAYS swap them, not just when we detect a reversal
                            
                            # Swap the times
                            temp_hour = check_in_hour
                            temp_minute = check_in_minute
                            temp_second = check_in_second
                            
                            check_in_hour = check_out_hour
                            check_in_minute = check_out_minute
                            check_in_second = check_out_second
                            
                            check_out_hour = temp_hour
                            check_out_minute = temp_minute
                            check_out_second = temp_second
                            
                            print(f"Swapped times for night shift user in recalc: "
                                  f"Device check-in ({temp_hour:02d}:{temp_minute:02d}:{temp_second:02d}) → Real check-out, "
                                  f"Device check-out ({check_in_hour:02d}:{check_in_minute:02d}:{check_in_second:02d}) → Real check-in")
                            
                            # Now create proper datetime objects with correct dates
                            # Check-in is on current day (morning, but actually evening after swap)
                            check_in_date = datetime.now().date()
                            # Check-out is on next day (evening, but actually morning after swap)
                            check_out_date = check_in_date + timedelta(days=1)
                            
                            check_in_dt = datetime.combine(check_in_date, datetime.min.time().replace(
                                hour=check_in_hour, minute=check_in_minute, second=check_in_second
                            ))
                            
                            check_out_dt = datetime.combine(check_out_date, datetime.min.time().replace(
                                hour=check_out_hour, minute=check_out_minute, second=check_out_second
                            ))
                            
                            # For night shift, if check-out is earlier than check-in, add 1 day
                            if check_out_dt < check_in_dt:
                                check_out_dt += timedelta(days=1)
                        else:
                            # For day shifts, if check-out is earlier than check-in, it's likely next day
                            if check_out_dt < check_in_dt:
                                check_out_dt += timedelta(days=1)
                        
                        # Calculate working hours
                        time_diff = check_out_dt - check_in_dt
                        working_hours = time_diff.total_seconds() / 3600.0
                        
                        # Cap working hours at 10 for night shifts
                        if shift_type == 'night' and working_hours > 10.0:
                            working_hours = 10.0
                        
                        # Format working hours to 2 decimal places
                        working_hours = round(working_hours, 2)
                
                # Update working hours in database
                cursor.execute('UPDATE attendance SET working_hours = ? WHERE id = ?', 
                             (working_hours, record['id']))
                updated_count += 1
                
            except Exception as e:
                print(f"Error processing record {record['id']}: {e}")
                continue
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True, 
            'message': f'Successfully recalculated working hours for {updated_count} records'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/add_sample_data', methods=['POST'])
def add_sample_data():
    """Add sample attendance data for testing"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Sample attendance records for demonstration
        sample_attendance = [
            # Today's records - Night shift pattern
            (1, '2025-08-17 19:30:00', '2025-08-17 19:30:00', '2025-08-18 04:30:00', 9.0),
            (12, '2025-08-17 19:00:00', '2025-08-17 19:00:00', '2025-08-18 04:00:00', 9.0),
            (13, '2025-08-17 19:30:00', '2025-08-17 19:30:00', '2025-08-18 04:30:00', 9.0),
            (14, '2025-08-17 19:00:00', '2025-08-17 19:00:00', '2025-08-18 04:00:00', 9.0),
            (15, '2025-08-17 19:30:00', '2025-08-17 19:30:00', '2025-08-18 04:30:00', 9.0),
            (41, '2025-08-17 19:00:00', '2025-08-17 19:00:00', '2025-08-18 04:00:00', 9.0),
            
            # Previous day examples - Night shift pattern
            (1, '2025-08-16 19:30:00', '2025-08-16 19:30:00', '2025-08-17 04:30:00', 9.0),
            (12, '2025-08-16 19:00:00', '2025-08-16 19:00:00', '2025-08-17 04:00:00', 9.0),
            (13, '2025-08-16 19:30:00', '2025-08-16 19:30:00', '2025-08-17 04:30:00', 9.0),
            (14, '2025-08-16 19:00:00', '2025-08-16 19:00:00', '2025-08-17 04:00:00', 9.0),
            (15, '2025-08-16 19:30:00', '2025-08-16 19:30:00', '2025-08-17 04:30:00', 9.0),
            (41, '2025-08-16 19:00:00', '2025-08-16 19:00:00', '2025-08-17 04:00:00', 9.0),
        ]
        
        # Clear existing attendance records first
        cursor.execute('DELETE FROM attendance')
        
        # Insert new sample records
        for record in sample_attendance:
            cursor.execute('''INSERT INTO attendance 
                            (userid, timestamp, check_in, check_out, working_hours) 
                            VALUES (?, ?, ?, ?, ?)''', record)
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True, 
            'message': f'Added {len(sample_attendance)} sample attendance records'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/clear_sample_data', methods=['POST'])
def clear_sample_data():
    """Clear sample attendance data"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Clear all attendance records
        cursor.execute('DELETE FROM attendance')
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True, 
            'message': 'All attendance records cleared successfully'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/push_data_to_device', methods=['POST'])
def push_data_to_device():
    """Push updated user data back to the biometric device"""
    try:
        data = request.get_json()
        device_ip = data.get('device_ip', DEFAULT_DEVICE_IP)
        device_port = data.get('device_port', DEFAULT_DEVICE_PORT)
        
        # Test connection first
        if not test_device_connection(device_ip, device_port):
            return jsonify({'success': False, 'message': f"Device at {device_ip}:{device_port} is not reachable"})
        
        # Import ZK library
        try:
            from zk import ZK, const
        except ImportError:
            return jsonify({'success': False, 'message': "ZK library not available. Please install it with: pip install pyzk"})
        
        # Connect to device
        print(f"Attempting to connect to ZK device at {device_ip}:{device_port}...")
        zk = ZK(device_ip, port=device_port, timeout=5)
        
        try:
            conn = zk.connect()
            if not conn:
                return jsonify({'success': False, 'message': f"Failed to establish ZK connection to {device_ip}:{device_port}"})
            print(f"✓ ZK connection established successfully")
        except Exception as e:
            return jsonify({'success': False, 'message': f"ZK connection error: {str(e)}"})
        
        try:
            # Get all users from database
            db_conn = get_db_connection()
            cursor = db_conn.cursor()
            cursor.execute('''SELECT userid, name, company_name, shift_start_time, shift_end_time, 
                                    shift_type, working_hours_per_day, monthly_salary 
                             FROM users ORDER BY userid''')
            users = cursor.fetchall()
            db_conn.close()
            
            if not users:
                return jsonify({'success': False, 'message': 'No users found in database'})
            
            # Push users to device
            users_updated = 0
            users_added = 0
            
            for user in users:
                try:
                    # Check if user exists on device
                    device_users = conn.get_users()
                    existing_device_user = None
                    
                    for device_user in device_users:
                        if device_user.user_id == user['userid']:
                            existing_device_user = device_user
                            break
                    
                    if existing_device_user:
                        # Update existing user on device
                        if existing_device_user.name != user['name']:
                            # Update name on device
                            conn.set_user(uid=user['userid'], name=user['name'])
                            print(f"Updated user {user['userid']} name on device: {user['name']}")
                            users_updated += 1
                    else:
                        # Add new user to device
                        conn.set_user(uid=user['userid'], name=user['name'])
                        print(f"Added user {user['userid']} to device: {user['name']}")
                        users_added += 1
                        
                except Exception as e:
                    print(f"Error processing user {user['userid']}: {e}")
                    continue
            
            # Properly disconnect from device
            if conn and hasattr(conn, 'disconnect'):
                try:
                    conn.disconnect()
                except:
                    pass
            
            if zk and hasattr(zk, 'disconnect'):
                try:
                    zk.disconnect()
                except:
                    pass
            
            return jsonify({
                'success': True, 
                'message': f'Successfully pushed data to device: {users_updated} updated, {users_added} added'
            })
            
        except Exception as e:
            # Properly disconnect from device on error
            if conn and hasattr(conn, 'disconnect'):
                try:
                    conn.disconnect()
                except:
                    pass
            
            if zk and hasattr(zk, 'disconnect'):
                try:
                    zk.disconnect()
                except:
                    pass
            
            return jsonify({'success': False, 'message': f'Error pushing data to device: {str(e)}'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/push_user_to_device', methods=['POST'])
def push_user_to_device():
    """Push a specific user's updated data to the biometric device"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        device_ip = data.get('device_ip', DEFAULT_DEVICE_IP)
        device_port = data.get('device_port', DEFAULT_DEVICE_PORT)
        
        if not user_id:
            return jsonify({'success': False, 'message': 'User ID is required'})
        
        # Test connection first
        if not test_device_connection(device_ip, device_port):
            return jsonify({'success': False, 'message': f"Device at {device_ip}:{device_port} is not reachable"})
        
        # Import ZK library
        try:
            from zk import ZK, const
        except ImportError:
            return jsonify({'success': False, 'message': "ZK library not available. Please install it with: pip install pyzk"})
        
        # Connect to device
        print(f"Attempting to connect to ZK device at {device_ip}:{device_port}...")
        zk = ZK(device_ip, port=device_port, timeout=5)
        
        try:
            conn = zk.connect()
            if not conn:
                return jsonify({'success': False, 'message': f"Failed to establish ZK connection to {device_ip}:{device_port}"})
            print(f"✓ ZK connection established successfully")
        except Exception as e:
            return jsonify({'success': False, 'message': f"ZK connection error: {str(e)}"})
        
        try:
            # Get user data from database
            db_conn = get_db_connection()
            cursor = db_conn.cursor()
            cursor.execute('''SELECT userid, name, company_name, shift_start_time, shift_end_time, 
                                    shift_type, working_hours_per_day, monthly_salary 
                             FROM users WHERE userid = ?''', (user_id,))
            user = cursor.fetchone()
            db_conn.close()
            
            if not user:
                return jsonify({'success': False, 'message': f'User {user_id} not found in database'})
            
            # Check if user exists on device
            device_users = conn.get_users()
            existing_device_user = None
            
            for device_user in device_users:
                if device_user.user_id == user['userid']:
                    existing_device_user = device_user
                    break
            
            if existing_device_user:
                # Update existing user on device
                if existing_device_user.name != user['name']:
                    conn.set_user(uid=user['userid'], name=user['name'])
                    print(f"Updated user {user['userid']} name on device: {user['name']}")
                    message = f"Updated user {user['name']} on device"
                else:
                    message = f"User {user['name']} already up to date on device"
            else:
                # Add new user to device
                conn.set_user(uid=user['userid'], name=user['name'])
                print(f"Added user {user['userid']} to device: {user['name']}")
                message = f"Added user {user['name']} to device"
            
            # Properly disconnect from device
            if conn and hasattr(conn, 'disconnect'):
                try:
                    conn.disconnect()
                except:
                    pass
            
            if zk and hasattr(zk, 'disconnect'):
                try:
                    zk.disconnect()
                except:
                    pass
            
            return jsonify({
                'success': True, 
                'message': message
            })
            
        except Exception as e:
            # Properly disconnect from device on error
            if conn and hasattr(conn, 'disconnect'):
                try:
                    conn.disconnect()
                except:
                    pass
            
            if zk and hasattr(zk, 'disconnect'):
                try:
                    zk.disconnect()
                except:
                    pass
            
            return jsonify({'success': False, 'message': f'Error pushing user to device: {str(e)}'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/test_reversed_times', methods=['POST'])
def test_reversed_times():
    """Test the night shift time swapping logic"""
    try:
        from datetime import datetime, timedelta
        
        # Test case: Biometric device shows flipped times for night shift
        # Device shows: Check-in: 04:30 (morning), Check-out: 19:30 (evening)
        # Reality: Check-in: 19:30 (evening), Check-out: 04:30 (next morning)
        
        device_check_in_hour = 4   # 04:30 AM (what device shows as check-in)
        device_check_in_minute = 30
        device_check_out_hour = 19 # 19:30 PM (what device shows as check-out)
        device_check_out_minute = 30
        
        # For night shifts, ALWAYS swap the times
        # Swap the times
        temp_hour = device_check_in_hour
        temp_minute = device_check_in_minute
        
        real_check_in_hour = device_check_out_hour
        real_check_in_minute = device_check_out_minute
        
        real_check_out_hour = temp_hour
        real_check_out_minute = temp_minute
        
        # Create proper datetime objects with correct dates
        check_in_date = datetime.now().date()
        check_out_date = check_in_date + timedelta(days=1)
        
        real_check_in_dt = datetime.combine(check_in_date, datetime.min.time().replace(
            hour=real_check_in_hour, minute=real_check_in_minute, second=0
        ))
        
        real_check_out_dt = datetime.combine(check_out_date, datetime.min.time().replace(
            hour=real_check_out_hour, minute=real_check_out_minute, second=0
        ))
        
        # For night shift, if check-out is earlier than check-in, add 1 day
        if real_check_out_dt < real_check_in_dt:
            real_check_out_dt += timedelta(days=1)
        
        # Calculate working hours
        time_diff = real_check_out_dt - real_check_in_dt
        working_hours = time_diff.total_seconds() / 3600.0
        
        result = {
            'success': True,
            'device_shows': {
                'check_in': f"{device_check_in_hour:02d}:{device_check_in_minute:02d}",
                'check_out': f"{device_check_out_hour:02d}:{device_check_out_minute:02d}"
            },
            'times_swapped': True,
            'corrected_times': {
                'check_in': f"{real_check_in_hour:02d}:{real_check_in_minute:02d}",
                'check_out': f"{real_check_out_hour:02d}:{real_check_out_minute:02d}"
            },
            'working_hours': round(working_hours, 2),
            'explanation': 'For night shifts, device times are ALWAYS swapped. Morning time (04:30) becomes check-out, evening time (19:30) becomes check-in.'
        }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

def process_multiple_punches(user_id, date, punches):
    """Process multiple punches for a user on a given date to determine check-in/check-out"""
    try:
        # Get user's shift information
        user_conn = get_db_connection()
        user_info = user_conn.execute('SELECT shift_type FROM users WHERE userid = ?', (user_id,)).fetchone()
        user_conn.close()
        
        is_night_shift = user_info and user_info['shift_type'] == 'night' if user_info else False
        
        if not punches:
            return None, None
        
        # Sort punches by timestamp
        sorted_punches = sorted(punches, key=lambda x: x['timestamp'])
        
        if len(sorted_punches) == 1:
            # Single punch - treat as check-in only
            return sorted_punches[0]['timestamp'], None
        
        if is_night_shift:
            # For night shifts, biometric device ALWAYS flips times
            # First punch (morning) = check-out, last punch (evening) = check-in
            
            # Find the earliest morning punch (before 12:00) and latest evening punch (after 12:00)
            morning_punches = [p for p in sorted_punches if int(p['timestamp'].split(' ')[1].split(':')[0]) < 12]
            evening_punches = [p for p in sorted_punches if int(p['timestamp'].split(' ')[1].split(':')[0]) >= 12]
            
            if morning_punches and evening_punches:
                # Use earliest morning punch as check-out, latest evening punch as check-in
                check_out_time = min(morning_punches, key=lambda x: x['timestamp'])
                check_in_time = max(evening_punches, key=lambda x: x['timestamp'])
                
                print(f"Night shift multiple punches for user {user_id}: "
                      f"Check-in: {check_in_time['timestamp']} (evening), "
                      f"Check-out: {check_out_time['timestamp']} (morning)")
                
                return check_in_time['timestamp'], check_out_time['timestamp']
            else:
                # Fallback: use first and last punches
                return sorted_punches[-1]['timestamp'], sorted_punches[0]['timestamp']
        else:
            # For day shifts, use standard logic
            # First punch = check-in, last punch = check-out
            check_in_time = sorted_punches[0]['timestamp']
            check_out_time = sorted_punches[-1]['timestamp']
            
            print(f"Day shift multiple punches for user {user_id}: "
                  f"Check-in: {check_in_time}, Check-out: {check_out_time}")
            
            return check_in_time, check_out_time
            
    except Exception as e:
        print(f"Error processing multiple punches for user {user_id}: {e}")
        return None, None

@app.route('/holidays')
@login_required
def holidays():
    """Holidays management page"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get all holidays
    cursor.execute('SELECT * FROM holidays ORDER BY date DESC')
    holidays = cursor.fetchall()
    
    conn.close()
    return render_template('holidays.html', holidays=holidays)

@app.route('/attendance_marking')
@login_required
def attendance_marking():
    """Attendance marking page"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get date filter
    date_filter = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    company_filter = request.args.get('company_id', '')
    
    # Build query
    query = '''
        SELECT u.userid, u.name, u.company_name, u.shift_start_time, u.shift_end_time, 
               u.shift_type, u.working_hours_per_day, u.monthly_salary,
               am.status as marked_status, am.working_hours as marked_hours,
               am.overtime_hours, am.late_minutes, am.remarks,
               a.check_in, a.check_out, a.working_hours as actual_hours
        FROM users u
        LEFT JOIN attendance_marking am ON u.userid = am.userid AND am.date = ?
        LEFT JOIN attendance a ON u.userid = a.userid AND DATE(a.timestamp) = ?
    '''
    
    params = [date_filter, date_filter]
    
    if company_filter:
        query += ' WHERE u.company_id = ?'
        params.append(company_filter)
    
    query += ' ORDER BY u.userid'
    
    cursor.execute(query, params)
    users = cursor.fetchall()
    
    # Get companies for filter
    cursor.execute('SELECT * FROM companies ORDER BY name')
    companies = cursor.fetchall()
    
    # Check if date is weekend or holiday
    date_obj = datetime.strptime(date_filter, '%Y-%m-%d')
    is_weekend = date_obj.weekday() >= 5  # Saturday = 5, Sunday = 6
    
    cursor.execute('SELECT * FROM holidays WHERE date = ?', (date_filter,))
    holiday = cursor.fetchone()
    
    conn.close()
    
    return render_template('attendance_marking.html', 
                         users=users, 
                         companies=companies,
                         selected_date=date_filter,
                         selected_company=company_filter,
                         is_weekend=is_weekend,
                         holiday=holiday)

@app.route('/salary')
@login_required
def salary():
    """Salary calculation page"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get filters
    month_filter = request.args.get('month', datetime.now().strftime('%B'))
    year_filter = request.args.get('year', datetime.now().year)
    company_filter = request.args.get('company_id', '')
    
    # Build query
    query = '''
        SELECT u.userid, u.name, u.company_name, u.monthly_salary,
               sc.total_days, sc.present_days, sc.absent_days, sc.leave_days,
               sc.total_working_hours, sc.overtime_hours,
               sc.basic_salary, sc.overtime_pay, sc.deductions, sc.net_salary
        FROM users u
        LEFT JOIN salary_calculations sc ON u.userid = sc.userid 
            AND sc.month = ? AND sc.year = ?
    '''
    
    params = [month_filter, year_filter]
    
    if company_filter:
        query += ' WHERE u.company_id = ?'
        params.append(company_filter)
    
    query += ' ORDER BY u.userid'
    
    cursor.execute(query, params)
    users = cursor.fetchall()
    
    # Get companies for filter
    cursor.execute('SELECT * FROM companies ORDER BY name')
    companies = cursor.fetchall()
    
    # Get available months and years
    cursor.execute('SELECT DISTINCT month, year FROM salary_calculations ORDER BY year DESC, month')
    available_periods = cursor.fetchall()
    
    conn.close()
    
    return render_template('salary.html', 
                         users=users, 
                         companies=companies,
                         selected_month=month_filter,
                         selected_year=year_filter,
                         selected_company=company_filter,
                         available_periods=available_periods)

@app.route('/api/attendance_marking', methods=['POST'])
@login_required
def api_attendance_marking():
    """Mark attendance for a user"""
    try:
        data = request.get_json()
        userid = data.get('userid')
        date = data.get('date')
        status = data.get('status')
        working_hours = data.get('working_hours', 0.0)
        overtime_hours = data.get('overtime_hours', 0.0)
        late_minutes = data.get('late_minutes', 0)
        remarks = data.get('remarks', '')
        
        if not userid or not date or not status:
            return jsonify({'success': False, 'message': 'Missing required fields'})
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if marking already exists
        cursor.execute('SELECT * FROM attendance_marking WHERE userid = ? AND date = ?', (userid, date))
        existing = cursor.fetchone()
        
        if existing:
            # Update existing marking
            cursor.execute('''UPDATE attendance_marking 
                             SET status = ?, working_hours = ?, overtime_hours = ?, 
                                 late_minutes = ?, remarks = ?, marked_by = ?
                             WHERE userid = ? AND date = ?''', 
                          (status, working_hours, overtime_hours, late_minutes, remarks, 'admin', userid, date))
        else:
            # Create new marking
            cursor.execute('''INSERT INTO attendance_marking 
                             (userid, date, status, working_hours, overtime_hours, late_minutes, remarks, marked_by)
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', 
                          (userid, date, status, working_hours, overtime_hours, late_minutes, remarks, 'admin'))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Attendance marked successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/holidays', methods=['GET', 'POST'])
@login_required
def api_holidays():
    """Get or create holidays"""
    if request.method == 'GET':
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM holidays ORDER BY date DESC')
        holidays = cursor.fetchall()
        conn.close()
        
        # Convert to list of dictionaries
        holidays_list = []
        for holiday in holidays:
            holidays_list.append({
                'id': holiday['id'],
                'date': holiday['date'],
                'name': holiday['name'],
                'description': holiday['description'],
                'is_public_holiday': holiday['is_public_holiday']
            })
        
        return jsonify({'success': True, 'holidays': holidays_list})
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            date = data.get('date')
            name = data.get('name')
            description = data.get('description', '')
            is_public_holiday = data.get('is_public_holiday', True)
            
            if not date or not name:
                return jsonify({'success': False, 'message': 'Missing required fields'})
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''INSERT INTO holidays (date, name, description, is_public_holiday)
                             VALUES (?, ?, ?, ?)''', (date, name, description, is_public_holiday))
            
            conn.commit()
            conn.close()
            
            return jsonify({'success': True, 'message': 'Holiday added successfully'})
            
        except Exception as e:
            return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/holidays/<int:holiday_id>', methods=['PUT', 'DELETE'])
@login_required
def api_holiday_management(holiday_id):
    """Update or delete a holiday"""
    if request.method == 'PUT':
        try:
            data = request.get_json()
            date = data.get('date')
            name = data.get('name')
            description = data.get('description', '')
            is_public_holiday = data.get('is_public_holiday', True)
            
            if not date or not name:
                return jsonify({'success': False, 'message': 'Missing required fields'})
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''UPDATE holidays 
                             SET date = ?, name = ?, description = ?, is_public_holiday = ?
                             WHERE id = ?''', (date, name, description, is_public_holiday, holiday_id))
            
            conn.commit()
            conn.close()
            
            return jsonify({'success': True, 'message': 'Holiday updated successfully'})
            
        except Exception as e:
            return jsonify({'success': False, 'message': f'Error: {str(e)}'})
    
    elif request.method == 'DELETE':
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM holidays WHERE id = ?', (holiday_id,))
            
            conn.commit()
            conn.close()
            
            return jsonify({'success': True, 'message': 'Holiday deleted successfully'})
            
        except Exception as e:
            return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/calculate_salary', methods=['POST'])
@login_required
def api_calculate_salary():
    """Calculate salary for all users for a given month"""
    try:
        data = request.get_json()
        month = data.get('month')
        year = data.get('year')
        
        if not month or not year:
            return jsonify({'success': False, 'message': 'Missing month or year'})
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all users
        cursor.execute('SELECT userid, monthly_salary, working_hours_per_day FROM users')
        users = cursor.fetchall()
        
        # Calculate working days in month
        start_date = datetime(int(year), datetime.strptime(month, '%B').month, 1)
        if start_date.month == 12:
            end_date = datetime(int(year) + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = datetime(int(year), start_date.month + 1, 1) - timedelta(days=1)
        
        working_days = 0
        current_date = start_date
        while current_date <= end_date:
            # Skip weekends
            if current_date.weekday() < 5:  # Monday to Friday
                # Check if it's a holiday
                cursor.execute('SELECT * FROM holidays WHERE date = ?', (current_date.strftime('%Y-%m-%d'),))
                if not cursor.fetchone():
                    working_days += 1
            current_date += timedelta(days=1)
        
        # Process each user
        for user in users:
            userid = user['userid']
            monthly_salary = user['monthly_salary']
            daily_hours = user['working_hours_per_day']
            
            # Get attendance marking for the month
            cursor.execute('''SELECT status, working_hours, overtime_hours, late_minutes
                             FROM attendance_marking 
                             WHERE userid = ? AND strftime('%Y-%m', date) = ?''', 
                          (userid, f"{year:04d}-{datetime.strptime(month, '%B').month:02d}"))
            
            monthly_attendance = cursor.fetchall()
            
            present_days = 0
            absent_days = 0
            leave_days = 0
            total_working_hours = 0.0
            overtime_hours = 0.0
            
            for record in monthly_attendance:
                if record['status'] == 'present':
                    present_days += 1
                    total_working_hours += record['working_hours'] or daily_hours
                    overtime_hours += record['overtime_hours'] or 0.0
                elif record['status'] == 'absent':
                    absent_days += 1
                elif record['status'] == 'leave':
                    leave_days += 1
            
            # Calculate salary based on monthly salary
            daily_salary = monthly_salary / working_days if working_days > 0 else 0
            basic_salary = present_days * daily_salary
            overtime_pay = (overtime_hours / daily_hours) * daily_salary * 0.5  # 0.5x daily salary for overtime
            deductions = absent_days * daily_salary  # Deduct for absent days
            
            net_salary = basic_salary + overtime_pay - deductions
            
            # Insert or update salary calculation
            cursor.execute('''INSERT OR REPLACE INTO salary_calculations 
                             (userid, month, year, total_days, present_days, absent_days, leave_days,
                              total_working_hours, overtime_hours, basic_salary, overtime_pay, 
                              deductions, net_salary)
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                          (userid, month, year, working_days, present_days, absent_days, leave_days,
                           total_working_hours, overtime_hours, basic_salary, overtime_pay, 
                           deductions, net_salary))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': f'Salary calculated for {month} {year}'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/auto_mark_attendance', methods=['POST'])
@login_required
def api_auto_mark_attendance():
    """Automatically mark attendance based on biometric data"""
    try:
        data = request.get_json()
        date = data.get('date', datetime.now().strftime('%Y-%m-%d'))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all users
        cursor.execute('SELECT userid, shift_start_time, shift_end_time, shift_type, working_hours_per_day FROM users')
        users = cursor.fetchall()
        
        # Check if date is weekend or holiday
        date_obj = datetime.strptime(date, '%Y-%m-%d')
        is_weekend = date_obj.weekday() >= 5
        
        cursor.execute('SELECT * FROM holidays WHERE date = ?', (date,))
        holiday = cursor.fetchone()
        
        marked_count = 0
        
        for user in users:
            userid = user['userid']
            
            # Skip if weekend or holiday (unless user is marked as working)
            if (is_weekend or holiday) and not holiday:
                # Mark as weekend/holiday
                cursor.execute('''INSERT OR REPLACE INTO attendance_marking 
                                 (userid, date, status, working_hours, remarks)
                                 VALUES (?, ?, ?, ?, ?)''', 
                              (userid, date, 'weekend' if is_weekend else 'holiday', 0.0, 
                               'Weekend' if is_weekend else f"Holiday: {holiday['name']}"))
                marked_count += 1
                continue
            
            # Get biometric attendance for this user and date
            cursor.execute('''SELECT check_in, check_out, working_hours 
                             FROM attendance 
                             WHERE userid = ? AND DATE(timestamp) = ?''', (userid, date))
            
            attendance_record = cursor.fetchone()
            
            if attendance_record and attendance_record['check_in'] and attendance_record['check_out']:
                # User has biometric attendance
                working_hours = attendance_record['working_hours'] or 0.0
                daily_hours = user['working_hours_per_day']
                
                # Determine status based on working hours
                if working_hours >= daily_hours * 0.8:  # 80% of required hours
                    status = 'present'
                elif working_hours >= daily_hours * 0.5:  # 50% of required hours
                    status = 'half_day'
                else:
                    status = 'late'
                
                # Calculate overtime
                overtime_hours = max(0, working_hours - daily_hours)
                
                # Calculate late minutes
                late_minutes = 0
                if status == 'late':
                    late_minutes = int((daily_hours - working_hours) * 60)
                
                cursor.execute('''INSERT OR REPLACE INTO attendance_marking 
                                 (userid, date, status, working_hours, overtime_hours, late_minutes, remarks)
                                 VALUES (?, ?, ?, ?, ?, ?, ?)''', 
                              (userid, date, status, working_hours, overtime_hours, late_minutes, 'Auto-marked from biometric'))
                
                marked_count += 1
            else:
                # No biometric attendance - mark as absent
                cursor.execute('''INSERT OR REPLACE INTO attendance_marking 
                                 (userid, date, status, working_hours, remarks)
                                 VALUES (?, ?, ?, ?, ?)''', 
                              (userid, date, 'absent', 0.0, 'No biometric attendance'))
                
                marked_count += 1
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': f'Automatically marked attendance for {marked_count} users'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/monthly_attendance')
@login_required
def api_monthly_attendance():
    """Get monthly attendance data for the monthly sheet view"""
    try:
        year = request.args.get('year', type=int)
        month = request.args.get('month', type=int)
        company_id = request.args.get('company_id', type=int)
        
        if not year or not month:
            return jsonify({'success': False, 'message': 'Missing year or month'})
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Build query for users
        user_query = 'SELECT userid, name, company_name FROM users'
        user_params = []
        
        if company_id:
            user_query += ' WHERE company_id = ?'
            user_params.append(company_id)
        
        user_query += ' ORDER BY userid'
        
        cursor.execute(user_query, user_params)
        users = cursor.fetchall()
        
        # Get holidays for the month
        month_start = f"{year:04d}-{month:02d}-01"
        if month == 12:
            month_end = f"{year+1:04d}-01-01"
        else:
            month_end = f"{year:04d}-{month+1:02d}-01"
        
        cursor.execute('''SELECT date, name FROM holidays 
                         WHERE date >= ? AND date < ?''', (month_start, month_end))
        holidays = cursor.fetchall()
        
        # Get attendance marking for the month
        attendance_data = []
        for user in users:
            user_attendance = {
                'userid': user['userid'],
                'name': user['name'],
                'company_name': user['company_name'],
                'year': year,
                'month': month,
                'daily_attendance': []
            }
            
            # Get attendance for each day of the month
            days_in_month = (datetime(year, month + 1, 1) - datetime(year, month, 1)).days
            
            for day in range(1, days_in_month + 1):
                date_str = f"{year:04d}-{month:02d}-{day:02d}"
                
                cursor.execute('''SELECT status, working_hours, overtime_hours, late_minutes, remarks
                                 FROM attendance_marking 
                                 WHERE userid = ? AND date = ?''', (user['userid'], date_str))
                
                day_attendance = cursor.fetchone()
                
                if day_attendance:
                    user_attendance['daily_attendance'].append({
                        'date': date_str,
                        'status': day_attendance['status'],
                        'working_hours': day_attendance['working_hours'],
                        'overtime_hours': day_attendance['overtime_hours'],
                        'late_minutes': day_attendance['late_minutes'],
                        'remarks': day_attendance['remarks']
                    })
                else:
                    user_attendance['daily_attendance'].append({
                        'date': date_str,
                        'status': '',
                        'working_hours': 0.0,
                        'overtime_hours': 0.0,
                        'late_minutes': 0,
                        'remarks': ''
                    })
            
            attendance_data.append(user_attendance)
        
        conn.close()
        
        return jsonify({
            'success': True,
            'attendance': attendance_data,
            'holidays': [{'date': h['date'], 'name': h['name']} for h in holidays]
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

if __name__ == '__main__':
    # Initialize database
    setup_db()
    
    print("Starting Attendance System Web App...")
    print("Open your browser and go to: http://localhost:5000")
    print("Press Ctrl+C to stop the server")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
