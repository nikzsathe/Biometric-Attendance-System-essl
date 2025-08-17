import sqlite3
import datetime
import os
import socket

# SQLite DB setup
DB_PATH = 'attendance.db'

def get_db_connection():
    """Create a database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

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

def discover_devices(network_prefix="192.168.1", start_ip=1, end_ip=254, port=4370):
    """Scan network for potential biometric devices"""
    print(f"Scanning network {network_prefix}.{start_ip} to {network_prefix}.{end_ip} for devices...")
    found_devices = []
    
    for i in range(start_ip, end_ip + 1):
        ip = f"{network_prefix}.{i}"
        if test_device_connection(ip, port, timeout=1):
            found_devices.append(ip)
            print(f"Found device at {ip}:{port}")
    
    return found_devices

def pull_users_from_device(conn):
    """Pull all users from the biometric device"""
    try:
        print("Pulling users from device...")
        users = conn.get_users()
        print(f"Found {len(users)} users on device")
        
        # Save users to database
        conn_db = sqlite3.connect(DB_PATH)
        c = conn_db.cursor()
        
        for user in users:
            try:
                c.execute('''INSERT OR REPLACE INTO users 
                            (userid, name, company_name, shift_start_time, shift_end_time, 
                             shift_type, working_hours_per_day) 
                            VALUES (?, ?, ?, ?, ?, ?, ?)''', 
                         (user.user_id, user.name, 'Default Company', '09:00:00', '18:00:00', 
                          'day', 8.0))
                print(f"User: {user.name} (ID: {user.user_id})")
            except Exception as e:
                print(f"Error saving user {user.name}: {e}")
        
        conn_db.commit()
        conn_db.close()
        print("Users saved to database successfully!")
        return True
        
    except Exception as e:
        print(f"Error pulling users: {e}")
        return False

def pull_attendance_from_device(ip, port=4370):
    """Pull attendance records from device"""
    try:
        zk = ZK(ip, port=port, timeout=10)
        conn = zk.connect()
        
        if not conn:
            return False, "Could not connect to device"
        
        # Pull attendance and process check-ins/check-outs
        attendance = conn.get_attendance()
        records_added = 0
        records_updated = 0
        
        db_conn = get_db_connection()
        cursor = db_conn.cursor()
        
        # Group attendance by user and date
        attendance_by_user_date = {}
        
        for record in attendance:
            user_id = record.user_id
            timestamp = record.timestamp
            date_str = timestamp.strftime('%Y-%m-%d')
            time_str = timestamp.strftime('%H:%M:%S')
            
            if user_id not in attendance_by_user_date:
                attendance_by_user_date[user_id] = {}
            if date_str not in attendance_by_user_date[user_id]:
                attendance_by_user_date[user_id][date_str] = []
            
            attendance_by_user_date[user_id][date_str].append({
                'timestamp': timestamp,
                'time': time_str,
                'hour': timestamp.hour,
                'minute': timestamp.minute
            })
        
        # Process each user's daily records
        for user_id, dates in attendance_by_user_date.items():
            for date_str, times in dates.items():
                # Sort times for the day by actual timestamp
                times.sort(key=lambda x: x['timestamp'])
                
                # Find check-in and check-out times
                check_in_time = None
                check_out_time = None
                
                if len(times) == 1:
                    # Single record - this is likely a check-in only
                    check_in_time = times[0]['timestamp']
                    check_out_time = None
                elif len(times) >= 2:
                    # Multiple records - first is check-in, last is check-out
                    check_in_time = times[0]['timestamp']
                    check_out_time = times[-1]['timestamp']
                    
                    # If check-in and check-out are the same time, it's likely a single punch
                    if check_in_time == check_out_time:
                        check_out_time = None
                
                # Check if record already exists for this user and date
                cursor.execute('''SELECT id, check_in, check_out FROM attendance 
                                 WHERE userid = ? AND DATE(timestamp) = ?''', 
                              (user_id, date_str))
                existing_record = cursor.fetchone()
                
                if existing_record:
                    # Update existing record with check-in/check-out times
                    existing_id = existing_record[0]
                    existing_check_in = existing_record[2]  # check_in column
                    existing_check_out = existing_record[3]  # check_out column
                    
                    # Only update if we have new information
                    new_check_in = check_in_time if check_in_time else existing_check_in
                    new_check_out = check_out_time if check_out_time else existing_check_out
                    
                    if new_check_in != existing_check_in or new_check_out != existing_check_out:
                        cursor.execute('''UPDATE attendance 
                                        SET check_in = ?, check_out = ?
                                        WHERE id = ?''', 
                                     (new_check_in, new_check_out, existing_id))
                        records_updated += 1
                else:
                    # Insert new record
                    cursor.execute('''INSERT INTO attendance (userid, timestamp, check_in, check_out) 
                                    VALUES (?, ?, ?, ?)''', 
                                 (user_id, check_in_time or check_out_time, check_in_time, check_out_time))
                    records_added += 1
        
        db_conn.commit()
        db_conn.close()
        conn.disconnect()
        
        return True, f"Successfully pulled and processed {records_added} new + {records_updated} updated attendance records"
        
    except Exception as e:
        return False, f"Error pulling attendance: {str(e)}"

def setup_db():
    """Initialize the database with required tables"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Create users table with enhanced fields
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        userid INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        company_name TEXT DEFAULT 'Default Company',
        shift_start_time TEXT DEFAULT '09:00:00',
        shift_end_time TEXT DEFAULT '18:00:00',
        shift_type TEXT DEFAULT 'day', -- 'day', 'night', 'flexible'
        working_hours_per_day REAL DEFAULT 8.0,
        created_date TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Create attendance table
    c.execute('''CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        userid INTEGER,
        timestamp TEXT,
        check_in TEXT,
        check_out TEXT,
        working_hours REAL DEFAULT 0.0,
        created_date TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (userid) REFERENCES users (userid)
    )''')
    
    # Check if we need to add new columns to existing users table
    try:
        c.execute('SELECT company_name FROM users LIMIT 1')
    except sqlite3.OperationalError:
        # Add new columns to existing users table
        c.execute('ALTER TABLE users ADD COLUMN company_name TEXT DEFAULT "Default Company"')
        c.execute('ALTER TABLE users ADD COLUMN shift_start_time TEXT DEFAULT "09:00:00"')
        c.execute('ALTER TABLE users ADD COLUMN shift_end_time TEXT DEFAULT "18:00:00"')
        c.execute('ALTER TABLE users ADD COLUMN shift_type TEXT DEFAULT "day"')
        c.execute('ALTER TABLE users ADD COLUMN working_hours_per_day REAL DEFAULT 8.0')
        c.execute('ALTER TABLE users ADD COLUMN created_date TEXT DEFAULT CURRENT_TIMESTAMP')
        print("Added new columns to existing users table")
    
    conn.commit()
    conn.close()
    print("Database setup completed!")

def add_user(userid, name):
    """Add a new user to the system"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute('INSERT INTO users (userid, name) VALUES (?, ?)', (userid, name))
        conn.commit()
        print(f"User {name} (ID: {userid}) added successfully!")
        return True
    except sqlite3.IntegrityError:
        print(f"User ID {userid} already exists!")
        return False
    finally:
        conn.close()

def mark_attendance(userid, check_type="check_in"):
    """Mark attendance for a user (check-in or check-out)"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Check if user exists
    c.execute('SELECT name FROM users WHERE userid = ?', (userid,))
    user = c.fetchone()
    
    if not user:
        print(f"User ID {userid} not found!")
        conn.close()
        return False
    
    current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    if check_type == "check_in":
        # Check if user already checked in today
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        c.execute('''SELECT id FROM attendance 
                    WHERE userid = ? AND DATE(timestamp) = ? AND check_in IS NOT NULL''', 
                 (userid, today))
        
        if c.fetchone():
            print(f"User {user[0]} already checked in today!")
            conn.close()
            return False
        
        # Insert new attendance record
        c.execute('''INSERT INTO attendance (userid, timestamp, check_in) 
                    VALUES (?, ?, ?)''', (userid, current_time, current_time))
        print(f"Check-in recorded for {user[0]} at {current_time}")
    
    elif check_type == "check_out":
        # Find today's check-in record
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        c.execute('''SELECT id FROM attendance 
                    WHERE userid = ? AND DATE(timestamp) = ? AND check_out IS NULL''', 
                 (userid, today))
        
        record = c.fetchone()
        if not record:
            print(f"No check-in record found for {user[0]} today!")
            conn.close()
            return False
        
        # Update check-out time
        c.execute('UPDATE attendance SET check_out = ? WHERE id = ?', (current_time, record[0]))
        print(f"Check-out recorded for {user[0]} at {current_time}")
    
    conn.commit()
    conn.close()
    return True

def view_attendance(userid=None, date=None):
    """View attendance records"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    if userid:
        # View specific user's attendance
        c.execute('''SELECT u.name, a.timestamp, a.check_in, a.check_out 
                    FROM attendance a 
                    JOIN users u ON a.userid = u.userid 
                    WHERE a.userid = ? 
                    ORDER BY a.timestamp DESC''', (userid,))
    elif date:
        # View attendance for specific date
        c.execute('''SELECT u.name, a.timestamp, a.check_in, a.check_out 
                    FROM attendance a 
                    JOIN users u ON a.userid = u.userid 
                    WHERE DATE(a.timestamp) = ? 
                    ORDER BY a.timestamp DESC''', (date,))
    else:
        # View all attendance records
        c.execute('''SELECT u.name, a.timestamp, a.check_in, a.check_out 
                    FROM attendance a 
                    JOIN users u ON a.userid = u.userid 
                    ORDER BY a.timestamp DESC 
                    LIMIT 20''')
    
    records = c.fetchall()
    conn.close()
    
    if not records:
        print("No attendance records found!")
        return
    
    print("\n" + "="*80)
    print(f"{'Name':<20} {'Date':<12} {'Check In':<20} {'Check Out':<20}")
    print("="*80)
    
    for record in records:
        name, timestamp, check_in, check_out = record
        date_str = timestamp.split()[0] if timestamp else "N/A"
        check_in_str = check_in.split()[1] if check_in else "N/A"
        check_out_str = check_out.split()[1] if check_out else "N/A"
        
        print(f"{name:<20} {date_str:<12} {check_in_str:<20} {check_out_str:<20}")
    print("="*80)

def list_users():
    """List all users in the system"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT userid, name FROM users ORDER BY userid')
    users = c.fetchall()
    conn.close()
    
    if not users:
        print("No users found!")
        return
    
    print("\n" + "="*50)
    print(f"{'ID':<8} {'Name':<20}")
    print("="*50)
    
    for user in users:
        userid, name = user
        print(f"{userid:<8} {name:<20}")
    print("="*50)

def device_mode():
    """Run the system in device mode for biometric device management"""
    print("\n=== DEVICE MODE ===")
    print("This mode allows you to manage biometric devices and pull data.")
    
    while True:
        print("\nDevice Options:")
        print("1. Test device connection")
        print("2. Discover devices on network")
        print("3. Pull users from device")
        print("4. Pull attendance from device")
        print("5. Pull both users and attendance")
        print("6. Return to main menu")
        
        choice = input("\nEnter your choice (1-6): ").strip()
        
        if choice == '1':
            ip = input("Enter device IP address: ").strip()
            port = input("Enter device port (default 4370): ").strip()
            port = int(port) if port.isdigit() else 4370
            
            if test_device_connection(ip, port):
                print(f"✅ Device at {ip}:{port} is reachable!")
            else:
                print(f"❌ Device at {ip}:{port} is not reachable!")
        
        elif choice == '2':
            network = input("Enter network prefix (e.g., 192.168.1): ").strip()
            if not network:
                network = "192.168.1"
            
            devices = discover_devices(network)
            if devices:
                print(f"\nFound {len(devices)} devices:")
                for device in devices:
                    print(f"  - {device}:4370")
            else:
                print("No devices found on the network.")
        
        elif choice == '3':
            ip = input("Enter device IP address: ").strip()
            port = input("Enter device port (default 4370): ").strip()
            port = int(port) if port.isdigit() else 4370
            
            try:
                # Import zk here to avoid issues
                from zk import ZK
                zk = ZK(ip, port=port, timeout=10)
                conn = zk.connect()
                
                if conn:
                    pull_users_from_device(conn)
                    conn.disconnect()
                else:
                    print("Could not connect to device!")
            except ImportError:
                print("ZK library not available. Please install it with: pip install pyzk")
            except Exception as e:
                print(f"Error: {e}")
        
        elif choice == '4':
            ip = input("Enter device IP address: ").strip()
            port = input("Enter device port (default 4370): ").strip()
            port = int(port) if port.isdigit() else 4370
            
            try:
                # Import zk here to avoid issues
                from zk import ZK
                zk = ZK(ip, port=port, timeout=10)
                conn = zk.connect()
                
                if conn:
                    pull_attendance_from_device(ip, port)
                    conn.disconnect()
                else:
                    print("Could not connect to device!")
            except ImportError:
                print("ZK library not available. Please install it with: pip install pyzk")
            except Exception as e:
                print(f"Error: {e}")
        
        elif choice == '5':
            ip = input("Enter device IP address: ").strip()
            port = input("Enter device port (default 4370): ").strip()
            port = int(port) if port.isdigit() else 4370
            
            try:
                # Import zk here to avoid issues
                from zk import ZK
                zk = ZK(ip, port=port, timeout=10)
                conn = zk.connect()
                
                if conn:
                    print("Pulling users and attendance...")
                    pull_users_from_device(conn)
                    pull_attendance_from_device(ip, port)
                    conn.disconnect()
                    print("Data pull completed!")
                else:
                    print("Could not connect to device!")
            except ImportError:
                print("ZK library not available. Please install it with: pip install pyzk")
            except Exception as e:
                print(f"Error: {e}")
        
        elif choice == '6':
            print("Returning to main menu...")
            break
        
        else:
            print("Invalid choice! Please enter 1-6.")

def demo_mode():
    """Run the system in demo mode for testing"""
    print("\n=== DEMO MODE ===")
    print("This mode allows you to test the attendance system without a biometric device.")
    
    while True:
        print("\nOptions:")
        print("1. List all users")
        print("2. Mark check-in")
        print("3. Mark check-out")
        print("4. View attendance records")
        print("5. Add new user")
        print("6. Device management")
        print("7. Exit demo")
        
        choice = input("\nEnter your choice (1-7): ").strip()
        
        if choice == '1':
            list_users()
        
        elif choice == '2':
            userid = input("Enter user ID: ").strip()
            try:
                mark_attendance(int(userid), "check_in")
            except ValueError:
                print("Invalid user ID! Please enter a number.")
        
        elif choice == '3':
            userid = input("Enter user ID: ").strip()
            try:
                mark_attendance(int(userid), "check_out")
            except ValueError:
                print("Invalid user ID! Please enter a number.")
        
        elif choice == '4':
            print("\nView options:")
            print("1. All records")
            print("2. Specific user")
            print("3. Specific date")
            
            view_choice = input("Enter choice (1-3): ").strip()
            
            if view_choice == '1':
                view_attendance()
            elif view_choice == '2':
                userid = input("Enter user ID: ").strip()
                try:
                    view_attendance(int(userid))
                except ValueError:
                    print("Invalid user ID!")
            elif view_choice == '3':
                date = input("Enter date (YYYY-MM-DD): ").strip()
                view_attendance(date=date)
        
        elif choice == '5':
            userid = input("Enter user ID: ").strip()
            name = input("Enter user name: ").strip()
            try:
                add_user(int(userid), name)
            except ValueError:
                print("Invalid user ID! Please enter a number.")
        
        elif choice == '6':
            device_mode()
        
        elif choice == '7':
            print("Exiting demo mode...")
            break
        
        else:
            print("Invalid choice! Please enter 1-7.")

if __name__ == "__main__":
    print("=== ATTENDANCE SYSTEM ===")
    
    # Setup database
    setup_db()
    
    # Check if we can connect to a biometric device
    try:
        # Try to import zk library
        from zk import ZK
        print("\nZK library found. Attempting to connect to biometric device...")
        
        # You can update these settings
        DEVICE_IP = '192.168.1.201'  # Update this to your device IP
        DEVICE_PORT = 4370
        
        # Test device connection first
        if test_device_connection(DEVICE_IP, DEVICE_PORT):
            print(f"Device at {DEVICE_IP}:{DEVICE_PORT} is reachable!")
            
            zk = ZK(DEVICE_IP, port=DEVICE_PORT, timeout=10)
            conn = zk.connect()
            
            if conn:
                print(f"Successfully connected to device at {DEVICE_IP}:{DEVICE_PORT}")
                
                # Pull users and attendance
                pull_users_from_device(conn)
                pull_attendance_from_device(DEVICE_IP, DEVICE_PORT)
                
                conn.disconnect()
                print("Device data processed successfully!")
                
                print("\nWould you like to continue in demo mode? (y/n): ", end="")
                if input().lower().startswith('y'):
                    demo_mode()
            else:
                print("Could not connect to device. Running in demo mode...")
                demo_mode()
        else:
            print(f"Device at {DEVICE_IP}:{DEVICE_PORT} is not reachable.")
            print("Running in demo mode...")
            demo_mode()
            
    except ImportError:
        print("ZK library not available. Running in demo mode...")
        print("To enable device connection, install: pip install pyzk")
        demo_mode()
    except Exception as e:
        print(f"Error connecting to device: {e}")
        print("Running in demo mode instead...")
        demo_mode()