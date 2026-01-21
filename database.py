import os
import datetime
import bcrypt
import sqlite3
from dotenv import load_dotenv

load_dotenv()

# Database configuration
MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
MYSQL_USER = os.getenv('MYSQL_USER', 'root')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'school_db')
MYSQL_PORT = int(os.getenv('MYSQL_PORT', 3306))
SQLITE_PATH = os.getenv('SQLITE_PATH', os.path.join(os.path.dirname(__file__), 'school.db'))

_mysql_pool = None
_use_sqlite = False

# SQLite adapter class to mimic MySQL connection pool interface
class SQLiteConnectionWrapper:
    def __init__(self, path):
        self.path = path
        self._conn = None
    
    def get_connection(self):
        conn = sqlite3.connect(self.path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return SQLiteConnection(conn)

class SQLiteConnection:
    def __init__(self, conn):
        self._conn = conn
    
    def cursor(self, dictionary=False):
        return SQLiteCursor(self._conn.cursor(), dictionary)
    
    def commit(self):
        self._conn.commit()
    
    def close(self):
        self._conn.close()

class SQLiteCursor:
    def __init__(self, cursor, dictionary=False):
        self._cursor = cursor
        self._dictionary = dictionary
        self.lastrowid = None
        self.rowcount = 0
    
    def execute(self, query, params=None):
        # Convert MySQL placeholders %s to SQLite ?
        query = query.replace('%s', '?')
        # Handle JSON type for SQLite (store as TEXT)
        query = query.replace(' JSON', ' TEXT')
        # Handle MySQL-specific syntax
        query = query.replace('ENGINE=InnoDB DEFAULT CHARSET=utf8mb4', '')
        query = query.replace('ON UPDATE CURRENT_TIMESTAMP', '')
        # Convert MySQL auto-increment to SQLite
        query = query.replace('INT AUTO_INCREMENT PRIMARY KEY', 'INTEGER PRIMARY KEY AUTOINCREMENT')
        query = query.replace('INT AUTO_INCREMENT', 'INTEGER')
        query = query.replace('INT NOT NULL', 'INTEGER NOT NULL')
        
        if params:
            self._cursor.execute(query, params)
        else:
            self._cursor.execute(query)
        self.lastrowid = self._cursor.lastrowid
        self.rowcount = self._cursor.rowcount
    
    def fetchone(self):
        row = self._cursor.fetchone()
        if row is None:
            return None
        if self._dictionary:
            return dict(row)
        return tuple(row)
    
    def fetchall(self):
        rows = self._cursor.fetchall()
        if self._dictionary:
            return [dict(row) for row in rows]
        return [tuple(row) for row in rows]

def get_mysql_pool():
    global _mysql_pool, _use_sqlite
    
    # Return existing pool if available
    if _mysql_pool:
        return _mysql_pool
    
    # If already determined to use SQLite, return SQLite wrapper
    if _use_sqlite:
        return SQLiteConnectionWrapper(SQLITE_PATH)
    
    # Try MySQL first
    try:
        import mysql.connector
        from mysql.connector import pooling
        _mysql_pool = mysql.connector.pooling.MySQLConnectionPool(
            pool_name="school_pool",
            pool_size=10,
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE,
            port=MYSQL_PORT
        )
        print(f"✅ Using MySQL database: {MYSQL_DATABASE} on {MYSQL_HOST}")
        return _mysql_pool
    except Exception as e:
        print(f"⚠️ MySQL connection failed: {e}")
        print(f"✅ Falling back to SQLite: {SQLITE_PATH}")
        _use_sqlite = True
        return SQLiteConnectionWrapper(SQLITE_PATH)

def init_db():
    create_tables()

def create_tables():
    pool = get_mysql_pool()
    if not pool:
        return
    
    conn = pool.get_connection()
    try:
        cursor = conn.cursor()
        
        # Enable foreign keys for SQLite
        try:
            cursor.execute('PRAGMA foreign_keys = ON')
        except:
            pass  # MySQL doesn't support PRAGMA
        
        # Create users table
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
          id INT AUTO_INCREMENT PRIMARY KEY,
          username VARCHAR(255) UNIQUE NOT NULL,
          password_hash VARCHAR(255) NOT NULL,
          role VARCHAR(50) NOT NULL DEFAULT 'admin',
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')

        # Create schools table
        cursor.execute('''CREATE TABLE IF NOT EXISTS schools (
          id INT AUTO_INCREMENT PRIMARY KEY,
          name VARCHAR(255) NOT NULL,
          code VARCHAR(100) UNIQUE NOT NULL,
          study_type VARCHAR(100) NOT NULL,
          level VARCHAR(100) NOT NULL,
          gender_type VARCHAR(50) NOT NULL,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')

        # Create students table
        cursor.execute('''CREATE TABLE IF NOT EXISTS students (
          id INT AUTO_INCREMENT PRIMARY KEY,
          school_id INT NOT NULL,
          full_name VARCHAR(255) NOT NULL,
          student_code VARCHAR(100) UNIQUE NOT NULL,
          grade VARCHAR(50) NOT NULL,
          branch VARCHAR(100),
          room VARCHAR(100) NOT NULL,
          enrollment_date DATE,
          parent_contact VARCHAR(255),
          blood_type VARCHAR(10),
          chronic_disease TEXT,
          detailed_scores JSON,
          daily_attendance JSON,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY(school_id) REFERENCES schools(id) ON DELETE CASCADE
        )''')
        
        # Add new columns to existing students table if they don't exist (for migration)
        try:
            cursor.execute("ALTER TABLE students ADD COLUMN parent_contact VARCHAR(255)")
        except:
            pass  # Column already exists
        try:
            cursor.execute("ALTER TABLE students ADD COLUMN blood_type VARCHAR(10)")
        except:
            pass  # Column already exists
        try:
            cursor.execute("ALTER TABLE students ADD COLUMN chronic_disease TEXT")
        except:
            pass  # Column already exists

        # Create subjects table
        cursor.execute('''CREATE TABLE IF NOT EXISTS subjects (
          id INT AUTO_INCREMENT PRIMARY KEY,
          school_id INT NOT NULL,
          name VARCHAR(255) NOT NULL,
          grade_level VARCHAR(50) NOT NULL,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY(school_id) REFERENCES schools(id) ON DELETE CASCADE
        )''')

        # Create grade_levels table for custom grade levels per school
        cursor.execute('''CREATE TABLE IF NOT EXISTS grade_levels (
          id INT AUTO_INCREMENT PRIMARY KEY,
          school_id INT NOT NULL,
          name VARCHAR(255) NOT NULL,
          display_order INT DEFAULT 0,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY(school_id) REFERENCES schools(id) ON DELETE CASCADE
        )''')

        # Create teachers table for managing teachers and their subjects
        cursor.execute('''CREATE TABLE IF NOT EXISTS teachers (
          id INT AUTO_INCREMENT PRIMARY KEY,
          school_id INT NOT NULL,
          full_name VARCHAR(255) NOT NULL,
          phone VARCHAR(50),
          email VARCHAR(255),
          subject_id INT,
          grade_level VARCHAR(100) NOT NULL,
          specialization VARCHAR(255),
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY(school_id) REFERENCES schools(id) ON DELETE CASCADE,
          FOREIGN KEY(subject_id) REFERENCES subjects(id) ON DELETE SET NULL
        )''')

        # Create system_academic_years table for centralized academic year management
        # This table is managed by the system administrator and applies to ALL schools
        cursor.execute('''CREATE TABLE IF NOT EXISTS system_academic_years (
          id INT AUTO_INCREMENT PRIMARY KEY,
          name VARCHAR(50) NOT NULL UNIQUE,
          start_year INT NOT NULL,
          end_year INT NOT NULL,
          start_date DATE,
          end_date DATE,
          is_current INT DEFAULT 0,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Legacy: Keep academic_years table for backward compatibility during migration
        # New implementations should use system_academic_years
        cursor.execute('''CREATE TABLE IF NOT EXISTS academic_years (
          id INT AUTO_INCREMENT PRIMARY KEY,
          school_id INT NOT NULL,
          name VARCHAR(50) NOT NULL,
          start_year INT NOT NULL,
          end_year INT NOT NULL,
          start_date DATE,
          end_date DATE,
          is_current INT DEFAULT 0,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY(school_id) REFERENCES schools(id) ON DELETE CASCADE
        )''')
        
        # Create student_grades table for storing grades per academic year (uses system_academic_years)
        cursor.execute('''CREATE TABLE IF NOT EXISTS student_grades (
          id INT AUTO_INCREMENT PRIMARY KEY,
          student_id INT NOT NULL,
          academic_year_id INT NOT NULL,
          subject_name VARCHAR(255) NOT NULL,
          month1 INT DEFAULT 0,
          month2 INT DEFAULT 0,
          midterm INT DEFAULT 0,
          month3 INT DEFAULT 0,
          month4 INT DEFAULT 0,
          final INT DEFAULT 0,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE,
          FOREIGN KEY(academic_year_id) REFERENCES system_academic_years(id) ON DELETE CASCADE
        )''')
        
        # Create student_attendance table for storing attendance per academic year (uses system_academic_years)
        cursor.execute('''CREATE TABLE IF NOT EXISTS student_attendance (
          id INT AUTO_INCREMENT PRIMARY KEY,
          student_id INT NOT NULL,
          academic_year_id INT NOT NULL,
          attendance_date DATE NOT NULL,
          status VARCHAR(20) NOT NULL DEFAULT "present",
          notes TEXT,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE,
          FOREIGN KEY(academic_year_id) REFERENCES system_academic_years(id) ON DELETE CASCADE
        )''')

        # Create default admin
        cursor.execute('SELECT * FROM users WHERE username = %s', ('admin',))
        if not cursor.fetchone():
            pwd_hash = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            cursor.execute('INSERT INTO users(username, password_hash, role) VALUES(%s, %s, %s)',
                           ('admin', pwd_hash, 'admin'))
            print('✅ Default admin created (admin / admin123)')
        else:
            # Check if role is admin, update if needed
            cursor.execute('UPDATE users SET role = %s WHERE username = %s', ('admin', 'admin'))
            
        conn.commit()
        print('✅ Database tables created successfully')
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
    finally:
        conn.close()

def generate_school_code():
    import time
    import random
    import string
    timestamp = str(int(time.time() * 1000))[-6:]
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=3))
    return f"SCH-{timestamp}-{random_str}"

def get_unique_school_code():
    code = generate_school_code()
    pool = get_mysql_pool()
    if not pool:
        return code
        
    conn = pool.get_connection()
    try:
        cursor = conn.cursor()
        while True:
            cursor.execute('SELECT code FROM schools WHERE code = %s', (code,))
            if not cursor.fetchone():
                break
            code = generate_school_code()
    finally:
        conn.close()
    
    return code
