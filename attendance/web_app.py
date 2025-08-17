from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
import sqlite3
from datetime import datetime
import os
from zk import ZK
import socket
import hashlib
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)  # Generate a secure random secret key

# Database path
DB_PATH = 'attendance.db'

# Device configuration
DEFAULT_DEVICE_IP = '192.168.1.201'
DEFAULT_DEVICE_PORT = 4370

# Admin credentials (you can change these)
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin123'  # Change this to a secure password

# Company branding
COMPANY_NAME = 'Absolute Global Outsourcing'
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
        FOREIGN KEY (userid) REFERENCES users (userid)
    )''')
    
    # Create companies table
    c.execute('''CREATE TABLE IF NOT EXISTS companies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        description TEXT,
        created_date TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Check if working_hours column exists in attendance table
    c.execute("PRAGMA table_info(attendance)")
    columns = [column[1] for column in c.fetchall()]
    
    if 'working_hours' not in columns:
        c.execute('ALTER TABLE attendance ADD COLUMN working_hours REAL DEFAULT 0.0')
        print("Added working_hours column to attendance table")
    
    # Check if company_id column exists in users table
    c.execute("PRAGMA table_info(users)")
    user_columns = [column[1] for column in c.fetchall()]
    
    if 'company_id' not in user_columns:
        c.execute('ALTER TABLE users ADD COLUMN company_id INTEGER')
        print("Added company_id column to users table")
    
    # Insert default companies
    c.execute('INSERT OR IGNORE INTO companies (name, description) VALUES (?, ?)', 
              ('Absolute Global Outsourcing', 'Main company'))
    c.execute('INSERT OR IGNORE INTO companies (name, description) VALUES (?, ?)', 
              ('Default Company', 'Default company for existing users'))
    
    # Update company_id for existing users
    c.execute('''UPDATE users SET company_id = (
        SELECT id FROM companies WHERE companies.name = users.company_name
    ) WHERE company_id IS NULL''')
    
    # Add some sample users if table is empty
    c.execute('SELECT COUNT(*) FROM users')
    if c.fetchone()[0] == 0:
        sample_users = [
            (1, 'Nikhil Sathe', 'Absolute Global Outsourcing', '04:00', '20:00', 'night', 8.0),
            (12, 'Akash Gaikwad', 'Absolute Global Outsourcing', '04:00', '19:00', 'night', 8.0),
            (13, 'Shubham Dabhane', 'Absolute Global Outsourcing', '19:00', '04:00', 'night', 8.0),
            (14, 'Shrutika Gaikwad', 'Absolute Global Outsourcing', '04:00', '20:00', 'night', 8.0),
            (15, 'Manoj Yadav', 'Absolute Global Outsourcing', '04:00', '20:00', 'night', 8.0),
            (41, 'Rohit Sahani', 'Absolute Global Outsourcing', '04:00', '19:00', 'night', 8.0)
        ]
        
        for user in sample_users:
            c.execute('''INSERT OR REPLACE INTO users 
                        (userid, name, company_name, shift_start_time, shift_end_time, shift_type, working_hours_per_day) 
                        VALUES (?, ?, ?, ?, ?, ?, ?)''', user)
        
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
            # Nikhil Sathe - Night shift example
            (1, '2025-08-17 19:30:00', '2025-08-17 19:30:00', '2025-08-18 04:30:00', 9.0),
            # Akash Gaikwad - Night shift example  
            (12, '2025-08-17 19:00:00', '2025-08-17 19:00:00', '2025-08-18 04:00:00', 9.0),
            # Shubham Dabhane - Night shift example
            (13, '2025-08-17 19:30:00', '2025-08-17 19:30:00', '2025-08-18 04:30:00', 9.0),
            # Shrutika Gaikwad - Night shift example
            (14, '2025-08-17 19:00:00', '2025-08-17 19:00:00', '2025-08-18 04:00:00', 9.0),
            # Manoj Yadav - Night shift example
            (15, '2025-08-17 19:30:00', '2025-08-17 19:30:00', '2025-08-18 04:30:00', 9.0),
            # Rohit Sahani - Night shift example
            (41, '2025-08-17 19:00:00', '2025-08-17 19:00:00', '2025-08-18 04:00:00', 9.0),
            
            # Previous day examples
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
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        sock.close()
        return result == 0
    except:
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
        zk = ZK(device_ip, port=device_port, timeout=5)
        conn = zk.connect()
        
        if not conn:
            return False, "Failed to connect to device"
        
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
            
            # Clear existing users and attendance
            cursor.execute('DELETE FROM users')
            cursor.execute('DELETE FROM attendance')
            
            # Insert users
            for user in users:
                cursor.execute('''INSERT INTO users 
                    (userid, name, company_name, shift_start_time, shift_end_time, shift_type, working_hours_per_day, created_date) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', 
                    (user.user_id, user.name, 'Absolute Global Outsourcing', '09:00', '18:00', 'day', 8.0, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            
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
            # Group records by user and date
            cursor.execute('''SELECT userid, DATE(timestamp) as date, 
                             MIN(timestamp) as first_punch, MAX(timestamp) as last_punch
                             FROM attendance 
                             GROUP BY userid, DATE(timestamp)''')
            
            grouped_records = cursor.fetchall()
            
            for group in grouped_records:
                user_id = group['userid']
                date = group['date']
                first_punch = group['first_punch']
                last_punch = group['last_punch']
                
                # Check if this user is a night shift employee
                user_conn = get_db_connection()
                user_info = user_conn.execute('SELECT shift_type FROM users WHERE userid = ?', (user_id,)).fetchone()
                user_conn.close()
                
                is_night_shift = user_info and user_info['shift_type'] == 'night' if user_info else False
                
                if is_night_shift:
                    # For night shifts: swap the logic
                    # Early morning time (before 12:00) = check-out
                    # Evening time (after 12:00) = check-in
                    
                    first_hour = int(first_punch.split(' ')[1].split(':')[0])
                    last_hour = int(last_punch.split(' ')[1].split(':')[0])
                    
                    if first_hour < 12 and last_hour >= 12:
                        # First punch is early morning (check-out), last punch is evening (check-in)
                        check_out_time = first_punch
                        check_in_time = last_punch
                    elif first_hour >= 12 and last_hour < 12:
                        # First punch is evening (check-in), last punch is early morning (check-out)
                        check_in_time = first_punch
                        check_out_time = last_punch
                    else:
                        # Both times are on same side of noon, use standard logic
                        check_in_time = first_punch
                        check_out_time = last_punch
                else:
                    # For day shifts: use standard logic
                    check_in_time = first_punch
                    check_out_time = last_punch
                
                # Update the attendance records
                cursor.execute('''UPDATE attendance 
                                 SET check_in = ?, check_out = ? 
                                 WHERE userid = ? AND DATE(timestamp) = ?''', 
                              (check_in_time, check_out_time, user_id, date))
                
                # Calculate working hours (capped at 10 hours for night shifts)
                if check_in_time and check_out_time:
                    try:
                        from datetime import datetime, timedelta
                        
                        # Parse the times
                        check_in_dt = datetime.strptime(check_in_time, '%Y-%m-%d %H:%M:%S')
                        check_out_dt = datetime.strptime(check_out_time, '%Y-%m-%d %H:%M:%S')
                        
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
                        
                    except Exception as e:
                        print(f"Error calculating working hours for user {user_id}: {e}")
            
            db_conn.commit()
            db_conn.close()
            
            print(f"Successfully processed {len(users)} users and {len(attendance_records)} attendance records")
            print(f"Night shift employees identified: {len(night_shift_employees)}")
            
            return True, f"Successfully pulled {len(users)} users and {len(attendance_records)} attendance records"
            
        except Exception as e:
            return False, f"Error processing device data: {str(e)}"
        finally:
            conn.disconnect()
            
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
                           u.shift_end_time, u.shift_type, u.working_hours_per_day, u.created_date,
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
                                
                                # For night shifts, we need to determine the correct order
                                # Night shift typically: check-in in evening, check-out next morning
                                # But data might show: check-in early morning, check-out evening
                                
                                if user_shift and user_shift['shift_type'] == 'night':
                                    # For night shift, determine if times are in correct order
                                    # If check-in is early morning (before 12) and check-out is evening (after 12)
                                    # This suggests the times are already in correct order for a same-day night shift
                                    
                                    # Create datetime objects for calculation
                                    today = datetime.now().date()
                                    
                                    check_in_dt = datetime.combine(today, datetime.min.time().replace(
                                        hour=check_in_hour, minute=check_in_minute, second=check_in_second
                                    ))
                                    
                                    check_out_dt = datetime.combine(today, datetime.min.time().replace(
                                        hour=check_out_hour, minute=check_out_minute, second=check_out_second
                                    ))
                                    
                                    # For night shift, only add 24 hours if actually crossing midnight
                                    # Check if check-out is earlier than check-in (indicating next day)
                                    if check_out_dt < check_in_dt:
                                        # This is a true night shift crossing midnight
                                        check_out_dt += timedelta(days=1)
                                    # Don't add 24 hours for same-day night shifts
                                    
                                else:
                                    # For day shift, use standard logic
                                    today = datetime.now().date()
                                    
                                    check_in_dt = datetime.combine(today, datetime.min.time().replace(
                                        hour=check_in_hour, minute=check_in_minute, second=check_in_second
                                    ))
                                    
                                    check_out_dt = datetime.combine(today, datetime.min.time().replace(
                                        hour=check_out_hour, minute=check_out_minute, second=check_out_second
                                    ))
                                    
                                    # For day shift, use the existing logic
                                    if check_out_dt < check_in_dt:
                                        # This could be an error or edge case, add 24 hours
                                        check_out_dt += timedelta(days=1)
                                
                                # Calculate the difference
                                time_diff = check_out_dt - check_in_dt
                                working_hours = time_diff.total_seconds() / 3600.0
                                
                                # Cap working hours at 10 for night shifts
                                if user_shift and user_shift['shift_type'] == 'night' and working_hours > 10.0:
                                    working_hours = 10.0
                                
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

@app.route('/api/users', methods=['GET'])
def get_users():
    """API endpoint to get all users"""
    try:
        conn = get_db_connection()
        users = conn.execute('''SELECT u.userid, u.name, u.company_name, u.shift_start_time, 
                               u.shift_end_time, u.shift_type, u.working_hours_per_day, u.created_date,
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
                              u.shift_end_time, u.shift_type, u.working_hours_per_day, u.created_date,
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
                             shift_end_time = ?, shift_type = ?, working_hours_per_day = ?
                         WHERE userid = ?''', 
                      (name, company_name, company_id, shift_start_time, shift_end_time, 
                       shift_type, working_hours_per_day, userid))
        
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
                                           shift_end_time, shift_type, working_hours_per_day)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', 
                      (userid, name, company_name, company_id, shift_start_time, shift_end_time, 
                       shift_type, working_hours_per_day))
        
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
                            # For night shifts, only add 24 hours if actually crossing midnight
                            if check_out_dt < check_in_dt:
                                # This is a true night shift crossing midnight
                                check_out_dt += timedelta(days=1)
                            # Don't add 24 hours for same-day night shifts
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
                    else:
                        working_hours = 0.0
                
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
            # Today's records
            (1, '2025-08-17 19:30:00', '2025-08-17 19:30:00', '2025-08-18 04:30:00', 9.0),
            (12, '2025-08-17 19:00:00', '2025-08-17 19:00:00', '2025-08-18 04:00:00', 9.0),
            (13, '2025-08-17 19:30:00', '2025-08-17 19:30:00', '2025-08-18 04:30:00', 9.0),
            (14, '2025-08-17 19:00:00', '2025-08-17 19:00:00', '2025-08-18 04:00:00', 9.0),
            (15, '2025-08-17 19:30:00', '2025-08-17 19:30:00', '2025-08-18 04:30:00', 9.0),
            (41, '2025-08-17 19:00:00', '2025-08-17 19:00:00', '2025-08-18 04:00:00', 9.0),
            
            # Previous day examples
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

if __name__ == '__main__':
    # Initialize database
    setup_db()
    
    print("Starting Attendance System Web App...")
    print("Open your browser and go to: http://localhost:5000")
    print("Press Ctrl+C to stop the server")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
