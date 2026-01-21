import os
import datetime
import secrets
import jwt
import bcrypt
import json
from functools import wraps
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from database import init_db, get_mysql_pool, get_unique_school_code

load_dotenv()

app = Flask(__name__, static_folder='public')
CORS(app, supports_credentials=True)

PORT = int(os.getenv('PORT', 1111))
JWT_SECRET = os.getenv('JWT_SECRET', secrets.token_hex(32))
NODE_ENV = os.getenv('NODE_ENV', 'development')

# Initialize database
init_db()

# Uploads directory configuration
if NODE_ENV == 'production':
    UPLOADS_DIR = '/tmp/uploads'
else:
    UPLOADS_DIR = os.path.join(os.path.dirname(__file__), 'uploads')

if not os.path.exists(UPLOADS_DIR):
    os.makedirs(UPLOADS_DIR, mode=0o755, exist_ok=True)

# Helper function to determine if a grade is elementary grades 1-4
def is_elementary_grades_1_to_4(grade_string):
    """
    Check if a grade string represents elementary (ابتدائي) grades 1-4.
    These grades use a 10-point scale, while all others use 100-point scale.
    
    Args:
        grade_string: Full grade string like "ابتدائي - الأول الابتدائي"
    Returns:
        bool: True if grade is elementary 1-4, False otherwise
    """
    if not grade_string:
        return False
    
    grade_parts = grade_string.split(' - ')
    if len(grade_parts) < 2:
        return False
    
    educational_level = grade_parts[0].strip()  # e.g., "ابتدائي"
    grade_level = grade_parts[1].strip()  # e.g., "الأول الابتدائي"
    
    # Check if this is an elementary (ابتدائي) school level
    is_elementary = ('ابتدائي' in educational_level or 
                     'ابتدائي' in grade_level or 
                     'الابتدائي' in grade_level)
    
    if not is_elementary:
        return False
    
    # Check if grade is first, second, third, or fourth
    grades_1_to_4 = ['الأول', 'الثاني', 'الثالث', 'الرابع', 'اول', 'ثاني', 'ثالث', 'رابع', 'الاول']
    is_grades_1_to_4 = any(x in grade_level for x in grades_1_to_4)
    
    # Make sure it's NOT fifth or sixth grade (which should use 100-point scale)
    grades_5_or_6 = ['الخامس', 'السادس', 'خامس', 'سادس']
    is_grades_5_or_6 = any(x in grade_level for x in grades_5_or_6)
    
    return is_grades_1_to_4 and not is_grades_5_or_6

# Authentication Decorator
def authenticate_token(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify({
                'error': 'Access token required',
                'error_ar': 'مطلوب رمز الوصول'
            }), 401
        
        try:
            data = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            request.user = data
        except jwt.ExpiredSignatureError:
            return jsonify({
                'error': 'Token expired',
                'error_ar': 'انتهت صلاحية الرمز'
            }), 403
        except jwt.InvalidTokenError:
            return jsonify({
                'error': 'Invalid token',
                'error_ar': 'رمز غير صالح'
            }), 403
            
        return f(*args, **kwargs)
    return decorated

# Global Error Handlers for JSON Responses
@app.errorhandler(404)
def not_found_error(error):
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Not Found', 'error_ar': 'غير موجود'}), 404
    return send_from_directory(app.static_folder, 'index.html')

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal Server Error', 'error_ar': 'خطأ داخلي في الخادم'}), 500

@app.errorhandler(Exception)
def handle_exception(e):
    print(f"Unhandled Exception: {e}")
    return jsonify({'error': str(e), 'error_ar': 'حدث خطأ غير متوقع'}), 500

def roles_required(*roles):
    def decorator(f):
        @wraps(f)
        @authenticate_token
        def decorated(*args, **kwargs):
            if request.user.get('role') not in roles:
                return jsonify({
                    'error': 'Unauthorized access',
                    'error_ar': 'دخول غير مصرح به'
                }), 403
            return f(*args, **kwargs)
        return decorated
    return decorator

@app.route('/health', methods=['GET'])
def health_check():
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.datetime.now().isoformat(),
        'environment': NODE_ENV,
        'database': 'MySQL',
        'platform': {
            'render': bool(os.getenv('RENDER')),
            'railway': bool(os.getenv('RAILWAY_ENVIRONMENT')),
            'vercel': bool(os.getenv('VERCEL')),
            'detected': 'Render.com' if os.getenv('RENDER') else 
                         'Railway.app' if os.getenv('RAILWAY_ENVIRONMENT') else 
                         'Vercel.com' if os.getenv('VERCEL') else 'Unknown/Local'
        },
        'configuration': {
            'hasMySQL': bool(os.getenv('MYSQL_HOST')),
            'hasJWTSecret': bool(os.getenv('JWT_SECRET')),
            'isProduction': NODE_ENV == 'production'
        },
        'warnings': []
    }
    
    if NODE_ENV != 'production' and (os.getenv('RENDER') or os.getenv('RAILWAY_ENVIRONMENT') or os.getenv('VERCEL')):
        health_status['warnings'].append('NODE_ENV should be set to "production" for hosting platforms')
    
    if not os.getenv('MYSQL_HOST') and NODE_ENV == 'production':
        health_status['warnings'].append('MYSQL_HOST not configured')
        
    return jsonify(health_status)

# API Routes
@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({
            'error': 'Username and password required',
            'error_ar': 'اسم المستخدم وكلمة المرور مطلوبان'
        }), 400
    
    query = 'SELECT * FROM users WHERE username = %s AND role = %s'
    params = (username, 'admin')
    
    user = None
    pool = get_mysql_pool()
    if not pool:
        return jsonify({'error': 'Database connection failed', 'error_ar': 'فشل الاتصال بقاعدة البيانات'}), 500
        
    conn = pool.get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(query, params)
        user = cur.fetchone()
    finally:
        conn.close()
        
    if not user or not bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
        return jsonify({
            'error': 'Invalid credentials',
            'error_ar': 'بيانات دخول غير صحيحة'
        }), 401
    
    token = jwt.encode({
        'id': user['id'],
        'username': user['username'],
        'role': user['role'],
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, JWT_SECRET, algorithm='HS256')
    
    return jsonify({
        'success': True,
        'token': token,
        'user': {'id': user['id'], 'username': user['username'], 'role': user['role']}
    })

@app.route('/api/school/login', methods=['POST'])
def school_login():
    data = request.json
    code = data.get('code')
    
    if not code:
        return jsonify({
            'error': 'School code is required',
            'error_ar': 'رمز المدرسة مطلوب'
        }), 400
    
    query = 'SELECT * FROM schools WHERE code = %s'
    
    school = None
    pool = get_mysql_pool()
    if not pool:
        return jsonify({'error': 'Database connection failed', 'error_ar': 'فشل الاتصال بقاعدة البيانات'}), 500
        
    conn = pool.get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(query, (code,))
        school = cur.fetchone()
    finally:
        conn.close()
        
    if not school:
        return jsonify({
            'error': 'School not found',
            'error_ar': 'لم يتم العثور على المدرسة'
        }), 404
    
    token = jwt.encode({
        'id': school['id'],
        'code': school['code'],
        'name': school['name'],
        'role': 'school',
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, JWT_SECRET, algorithm='HS256')
    
    return jsonify({
        'success': True,
        'token': token,
        'school': dict(school)
    })

@app.route('/api/student/login', methods=['POST'])
def student_login():
    data = request.json
    code = data.get('code')
    
    if not code:
        return jsonify({
            'error': 'Student code is required',
            'error_ar': 'رمز الطالب مطلوب'
        }), 400
    
    query = """SELECT s.*, sch.name as school_name FROM students s 
               JOIN schools sch ON s.school_id = sch.id 
               WHERE s.student_code = %s"""
               
    student = None
    pool = get_mysql_pool()
    if not pool:
        return jsonify({'error': 'Database connection failed', 'error_ar': 'فشل الاتصال بقاعدة البيانات'}), 500
        
    conn = pool.get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(query, (code,))
        student = cur.fetchone()
    finally:
        conn.close()
        
    if not student:
        return jsonify({
            'error': 'Student not found',
            'error_ar': 'لم يتم العثور على الطالب'
        }), 404
        
    token = jwt.encode({
        'id': student['id'],
        'code': student['student_code'],
        'name': student['full_name'],
        'role': 'student',
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, JWT_SECRET, algorithm='HS256')
    
    return jsonify({
        'success': True,
        'token': token,
        'student': dict(student)
    })

@app.route('/api/schools', methods=['GET'])
def get_schools():
    query = 'SELECT * FROM schools ORDER BY created_at DESC'
    schools = []
    pool = get_mysql_pool()
    if not pool:
        return jsonify({'error': 'Database connection failed', 'error_ar': 'فشل الاتصال بقاعدة البيانات'}), 500
        
    conn = pool.get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(query)
        schools = cur.fetchall()
    finally:
        conn.close()
    return jsonify({'success': True, 'schools': schools})

STAGE_TO_LEVEL_MAPPING = {
    "ابتدائي": "ابتدائي",
    "متوسط": "متوسطة",
    "ثانوي": "ثانوية",
    "إعدادي": "إعدادية"
}

@app.route('/api/schools', methods=['POST'])
@roles_required('admin')
def add_school():
    data = request.json
    name = data.get('name')
    study_type = data.get('study_type')
    level = data.get('level')
    gender_type = data.get('gender_type')
    
    if level and level not in STAGE_TO_LEVEL_MAPPING.values():
        level = STAGE_TO_LEVEL_MAPPING.get(level, level)
        
    if not all([name, study_type, level, gender_type]):
        return jsonify({
            'error': 'All fields are required',
            'error_ar': 'جميع الحقول مطلوبة'
        }), 400
        
    code = get_unique_school_code()
    
    query = """INSERT INTO schools (name, code, study_type, level, gender_type) 
               VALUES (%s, %s, %s, %s, %s)"""
    params = (name, code, study_type, level, gender_type)
    
    school = None
    pool = get_mysql_pool()
    if not pool:
        return jsonify({'error': 'Database connection failed', 'error_ar': 'فشل الاتصال بقاعدة البيانات'}), 500
        
    conn = pool.get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(query, params)
        last_id = cur.lastrowid
        conn.commit()
        cur.execute('SELECT * FROM schools WHERE id = %s', (last_id,))
        school = cur.fetchone()
    finally:
        conn.close()
        
    return jsonify({
        'success': True,
        'message': 'تم إضافة المدرسة بنجاح',
        'school': dict(school)
    }), 201

@app.route('/api/schools/<int:school_id>', methods=['PUT'])
@roles_required('admin')
def update_school(school_id):
    data = request.json
    name = data.get('name')
    study_type = data.get('study_type')
    level = data.get('level')
    gender_type = data.get('gender_type')
    
    if level and level not in STAGE_TO_LEVEL_MAPPING.values():
        level = STAGE_TO_LEVEL_MAPPING.get(level, level)
        
    query = """UPDATE schools SET name = %s, study_type = %s, level = %s, gender_type = %s, updated_at = CURRENT_TIMESTAMP 
               WHERE id = %s"""
    params = (name, study_type, level, gender_type, school_id)
    
    school = None
    pool = get_mysql_pool()
    if not pool:
        return jsonify({'error': 'Database connection failed', 'error_ar': 'فشل الاتصال بقاعدة البيانات'}), 500
        
    conn = pool.get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(query, params)
        conn.commit()
        cur.execute('SELECT * FROM schools WHERE id = %s', (school_id,))
        school = cur.fetchone()
    finally:
        conn.close()
        
    if not school:
        return jsonify({'error': 'School not found', 'error_ar': 'لم يتم العثور على المدرسة'}), 404
        
    return jsonify({
        'success': True,
        'message': 'تم تحديث المدرسة بنجاح',
        'school': dict(school)
    })

@app.route('/api/schools/<int:school_id>', methods=['DELETE'])
@roles_required('admin')
def delete_school(school_id):
    pool = get_mysql_pool()
    if not pool:
        return jsonify({'error': 'Database connection failed', 'error_ar': 'فشل الاتصال بقاعدة البيانات'}), 500
        
    conn = pool.get_connection()
    try:
        cur = conn.cursor()
        cur.execute('DELETE FROM schools WHERE id = %s', (school_id,))
        row_count = cur.rowcount
        conn.commit()
    finally:
        conn.close()
        
    if row_count == 0:
        return jsonify({'error': 'School not found', 'error_ar': 'لم يتم العثور على المدرسة'}), 404
        
    return jsonify({
        'success': True,
        'message': 'تم حذف المدرسة بنجاح',
        'deleted': row_count
    })

@app.route('/api/school/<int:school_id>/students', methods=['GET'])
@roles_required('admin', 'school')
def get_students(school_id):
    query = 'SELECT * FROM students WHERE school_id = %s ORDER BY created_at DESC'
    students = []
    pool = get_mysql_pool()
    if not pool:
        return jsonify({'error': 'Database connection failed', 'error_ar': 'فشل الاتصال بقاعدة البيانات'}), 500
        
    conn = pool.get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(query, (school_id,))
        students = cur.fetchall()
        for s in students:
            # MySQL JSON type might be returned as string or dict depending on driver/version
            for col in ['detailed_scores', 'daily_attendance']:
                if isinstance(s.get(col), str):
                    try:
                        s[col] = json.loads(s[col])
                    except:
                        s[col] = {}
                elif s.get(col) is None:
                    s[col] = {}
    finally:
        conn.close()
    return jsonify({'success': True, 'students': students})

@app.route('/api/school/<int:school_id>/student', methods=['POST'])
@roles_required('admin', 'school')
def add_student(school_id):
    data = request.json
    full_name = data.get('full_name')
    grade = data.get('grade')
    room = data.get('room')
    enrollment_date = data.get('enrollment_date')
    parent_contact = data.get('parent_contact')  # New field: one or two phone numbers
    blood_type = data.get('blood_type')  # New field: blood type selection
    chronic_disease = data.get('chronic_disease')  # New field: optional medical conditions
    
    if not all([full_name, grade, room]):
        return jsonify({
            'error': 'Full name, grade, and room are required',
            'error_ar': 'الاسم الكامل والصف والغرفة مطلوبة'
        }), 400
        
    grade_parts = grade.split(' - ')
    if len(grade_parts) < 2:
        return jsonify({
            'error': 'Invalid grade format',
            'error_ar': 'تنسيق الصف غير صحيح'
        }), 400
        
    level = grade_parts[0].strip()
    if level not in ['ابتدائي', 'متوسطة', 'ثانوية', 'إعدادية']:
        return jsonify({
            'error': 'Invalid educational level',
            'error_ar': 'مستوى تعليمي غير صحيح'
        }), 400
    
    # Validate blood type if provided
    valid_blood_types = ['O+', 'O-', 'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-']
    if blood_type and blood_type not in valid_blood_types:
        return jsonify({
            'error': 'Invalid blood type',
            'error_ar': 'فصيلة دم غير صالحة'
        }), 400

    # Duplicate check
    check_query = "SELECT COUNT(*) FROM students WHERE full_name = %s AND grade = %s AND school_id = %s"
    
    count = 0
    pool = get_mysql_pool()
    if not pool:
        return jsonify({'error': 'Database connection failed', 'error_ar': 'فشل الاتصال بقاعدة البيانات'}), 500
        
    conn = pool.get_connection()
    try:
        cur = conn.cursor()
        cur.execute(check_query, (full_name, grade, school_id))
        count = cur.fetchone()[0]
    finally:
        conn.close()
        
    if count > 0:
        return jsonify({
            'error': 'A student with the same name already exists in this grade',
            'error_ar': 'طالب بنفس الاسم موجود بالفعل في هذا الصف'
        }), 400
        
    student_code = f"STD-{int(datetime.datetime.now().timestamp() * 1000)}-{secrets.token_hex(2).upper()}"
    
    query = """INSERT INTO students (school_id, full_name, student_code, grade, room, enrollment_date, 
               parent_contact, blood_type, chronic_disease, detailed_scores, daily_attendance) 
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
    params = (school_id, full_name, student_code, grade, room, enrollment_date, 
              parent_contact, blood_type, chronic_disease, '{}', '{}')
    
    student = None
    pool = get_mysql_pool() # Use pool from outer scope or re-fetch
    if not pool:
        return jsonify({'error': 'Database connection failed', 'error_ar': 'فشل الاتصال بقاعدة البيانات'}), 500
        
    conn = pool.get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(query, params)
        last_id = cur.lastrowid
        conn.commit()
        cur.execute('SELECT * FROM students WHERE id = %s', (last_id,))
        student = cur.fetchone()
    finally:
        conn.close()
        
    return jsonify({
        'success': True,
        'message': 'تم إضافة الطالب بنجاح',
        'student': dict(student)
    }), 201

# Add more routes as needed (this covers the main ones from server.js first 1000 lines)
# For the sake of the task, I will continue with the rest of the routes logic...

@app.route('/api/student/<int:student_id>', methods=['PUT'])
@roles_required('admin', 'school')
def update_student(student_id):
    data = request.json
    full_name = data.get('full_name')
    grade = data.get('grade')
    room = data.get('room')
    detailed_scores = data.get('detailed_scores')
    daily_attendance = data.get('daily_attendance')
    parent_contact = data.get('parent_contact')  # New field
    blood_type = data.get('blood_type')  # New field
    chronic_disease = data.get('chronic_disease')  # New field
    
    # Validate blood type if provided
    valid_blood_types = ['O+', 'O-', 'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-']
    if blood_type and blood_type not in valid_blood_types:
        return jsonify({
            'error': 'Invalid blood type',
            'error_ar': 'فصيلة دم غير صالحة'
        }), 400
    
    final_detailed_scores = detailed_scores or {}
    
    if detailed_scores and grade:
        cleaned_scores = {}
        for subject, scores in detailed_scores.items():
            if subject == '[object Object]':
                continue
            if isinstance(subject, str) and len(subject) > 0:
                cleaned_scores[subject] = scores
        
        grade_parts = grade.split(' - ')
        if len(grade_parts) >= 2:
            # Use the helper function to check if this is elementary grades 1-4
            is_primary_1_to_4 = is_elementary_grades_1_to_4(grade)
            
            for subject, scores in cleaned_scores.items():
                if not isinstance(scores, dict): continue
                for period, score_val in scores.items():
                    try:
                        score = int(score_val)
                        if is_primary_1_to_4:
                            if score < 0 or score > 10:
                                return jsonify({'error': 'For grades 1-4, scores must be between 0 and 10', 'error_ar': 'للصفوف 1-4، يجب أن تكون الدرجات بين 0 و 10'}), 400
                        else:
                            if score < 0 or score > 100:
                                return jsonify({'error': 'Scores must be between 0 and 100', 'error_ar': 'يجب أن تكون الدرجات بين 0 و 100'}), 400
                    except (ValueError, TypeError):
                        pass
        final_detailed_scores = cleaned_scores

    query = """UPDATE students SET 
               full_name = %s, grade = %s, room = %s, 
               detailed_scores = %s, daily_attendance = %s,
               parent_contact = %s, blood_type = %s, chronic_disease = %s,
               updated_at = CURRENT_TIMESTAMP 
               WHERE id = %s"""
               
    params = (
        full_name, 
        grade, 
        room, 
        json.dumps(final_detailed_scores), 
        json.dumps(daily_attendance or {}),
        parent_contact,
        blood_type,
        chronic_disease,
        student_id
    )
    
    student = None
    pool = get_mysql_pool()
    if not pool:
        return jsonify({'error': 'Database connection failed', 'error_ar': 'فشل الاتصال بقاعدة البيانات'}), 500
        
    conn = pool.get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(query, params)
        conn.commit()
        cur.execute('SELECT * FROM students WHERE id = %s', (student_id,))
        student = cur.fetchone()
    finally:
        conn.close()
        
    if not student:
        return jsonify({'error': 'Student not found', 'error_ar': 'لم يتم العثور على الطالب'}), 404
        
    return jsonify({
        'success': True,
        'message': 'تم تحديث بيانات الطالب بنجاح',
        'student': dict(student)
    })

@app.route('/api/student/<int:student_id>', methods=['DELETE'])
@roles_required('admin', 'school')
def delete_student(student_id):
    pool = get_mysql_pool()
    if not pool:
        return jsonify({'error': 'Database connection failed', 'error_ar': 'فشل الاتصال بقاعدة البيانات'}), 500
        
    conn = pool.get_connection()
    try:
        cur = conn.cursor()
        cur.execute('DELETE FROM students WHERE id = %s', (student_id,))
        row_count = cur.rowcount
        conn.commit()
    finally:
        conn.close()
        
    if row_count == 0:
        return jsonify({'error': 'Student not found', 'error_ar': 'لم يتم العثور على الطالب'}), 404
        
    return jsonify({
        'success': True,
        'message': 'تم حذف الطالب بنجاح',
        'deleted': row_count
    })

@app.route('/api/student/<int:student_id>/detailed', methods=['PUT'])
@roles_required('admin', 'school')
def update_student_detailed(student_id):
    data = request.json
    detailed_scores = data.get('detailed_scores')
    daily_attendance = data.get('daily_attendance')
    
    if not detailed_scores and not daily_attendance:
        return jsonify({
            'error': 'Either detailed_scores or daily_attendance must be provided',
            'error_ar': 'يجب تقديم إما الدرجات التفصيلية أو بيانات الحضور'
        }), 400
        
    # Get current student to check grade
    query_select = "SELECT grade FROM students WHERE id = %s"
    student_grade = None
    pool = get_mysql_pool()
    if not pool:
        return jsonify({'error': 'Database connection failed', 'error_ar': 'فشل الاتصال بقاعدة البيانات'}), 500
        
    conn = pool.get_connection()
    try:
        cur = conn.cursor()
        cur.execute(query_select, (student_id,))
        row = cur.fetchone()
        if row: student_grade = row[0]
    finally:
        conn.close()
        
    if not student_grade:
        return jsonify({'error': 'Student not found', 'error_ar': 'لم يتم العثور على الطالب'}), 404
        
    final_detailed_scores = detailed_scores
    if detailed_scores:
        cleaned_scores = {}
        for subject, scores in detailed_scores.items():
            if subject == '[object Object]': continue
            if isinstance(subject, str) and len(subject) > 0:
                cleaned_scores[subject] = scores
        
        grade_parts = student_grade.split(' - ')
        if len(grade_parts) >= 2:
            # Use the helper function to check if this is elementary grades 1-4
            is_primary_1_to_4 = is_elementary_grades_1_to_4(student_grade)
            
            for subject, scores in cleaned_scores.items():
                if not isinstance(scores, dict): continue
                for period, score_val in scores.items():
                    try:
                        score = int(score_val)
                        if is_primary_1_to_4:
                            if score < 0 or score > 10:
                                return jsonify({'error': 'For grades 1-4, scores must be between 0 and 10', 'error_ar': 'للصفوف 1-4، يجب أن تكون الدرجات بين 0 و 10'}), 400
                        else:
                            if score < 0 or score > 100:
                                return jsonify({'error': 'Scores must be between 0 and 100', 'error_ar': 'يجب أن تكون الدرجات بين 0 و 100'}), 400
                    except (ValueError, TypeError): pass
        final_detailed_scores = cleaned_scores

    update_fields = []
    params = []
    if detailed_scores is not None:
        update_fields.append("detailed_scores = %s")
        params.append(json.dumps(final_detailed_scores))
    if daily_attendance is not None:
        update_fields.append("daily_attendance = %s")
        params.append(json.dumps(daily_attendance))
    
    params.append(student_id)
    query_update = f"UPDATE students SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP WHERE id = %s"
                   
    pool = get_mysql_pool()
    if not pool:
        return jsonify({'error': 'Database connection failed', 'error_ar': 'فشل الاتصال بقاعدة البيانات'}), 500
        
    conn = pool.get_connection()
    try:
        cur = conn.cursor()
        cur.execute(query_update, tuple(params))
        conn.commit()
    finally:
        conn.close()
        
    return jsonify({'success': True, 'message': 'تم تحديث بيانات الطالب بنجاح'})

# ------ Subjects Routes ------
@app.route('/api/school/<int:school_id>/subjects', methods=['GET'])
@roles_required('admin', 'school')
def get_subjects(school_id):
    query = 'SELECT * FROM subjects WHERE school_id = %s ORDER BY grade_level, name'
    subjects = []
    pool = get_mysql_pool()
    if not pool:
        return jsonify({'error': 'Database connection failed', 'error_ar': 'فشل الاتصال بقاعدة البيانات'}), 500
        
    conn = pool.get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(query, (school_id,))
        subjects = cur.fetchall()
    finally:
        conn.close()
    return jsonify({'success': True, 'subjects': subjects})

@app.route('/api/school/<int:school_id>/subject', methods=['POST'])
@roles_required('admin', 'school')
def add_subject(school_id):
    data = request.json
    name = data.get('name')
    grade_level = data.get('grade_level')
    
    if not name or not grade_level:
        return jsonify({'error': 'Subject name and grade level are required', 'error_ar': 'اسم المادة والمستوى الدراسي مطلوبان'}), 400
        
    query = "INSERT INTO subjects (school_id, name, grade_level) VALUES (%s, %s, %s)"
    params = (school_id, name, grade_level)
    
    subject = None
    pool = get_mysql_pool()
    if not pool:
        return jsonify({'error': 'Database connection failed', 'error_ar': 'فشل الاتصال بقاعدة البيانات'}), 500
        
    conn = pool.get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(query, params)
        last_id = cur.lastrowid
        conn.commit()
        cur.execute('SELECT * FROM subjects WHERE id = %s', (last_id,))
        subject = cur.fetchone()
    finally:
        conn.close()
        
    return jsonify({'success': True, 'message': 'تم إضافة المادة بنجاح', 'subject': dict(subject)}), 201

@app.route('/api/subject/<int:subject_id>', methods=['PUT'])
@roles_required('admin', 'school')
def update_subject(subject_id):
    data = request.json
    name = data.get('name')
    grade_level = data.get('grade_level')
    
    query = "UPDATE subjects SET name = %s, grade_level = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s"
    params = (name, grade_level, subject_id)
    
    subject = None
    pool = get_mysql_pool()
    if not pool:
        return jsonify({'error': 'Database connection failed', 'error_ar': 'فشل الاتصال بقاعدة البيانات'}), 500
        
    conn = pool.get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(query, params)
        conn.commit()
        cur.execute('SELECT * FROM subjects WHERE id = %s', (subject_id,))
        subject = cur.fetchone()
    finally:
        conn.close()
        
    if not subject:
        return jsonify({'error': 'Subject not found', 'error_ar': 'لم يتم العثور على المادة'}), 404
        
    return jsonify({'success': True, 'message': 'تم تحديث المادة بنجاح', 'subject': dict(subject)})

@app.route('/api/subject/<int:subject_id>', methods=['DELETE'])
@roles_required('admin', 'school')
def delete_subject(subject_id):
    pool = get_mysql_pool()
    if not pool:
        return jsonify({'error': 'Database connection failed', 'error_ar': 'فشل الاتصال بقاعدة البيانات'}), 500
        
    conn = pool.get_connection()
    try:
        cur = conn.cursor()
        cur.execute('DELETE FROM subjects WHERE id = %s', (subject_id,))
        row_count = cur.rowcount
        conn.commit()
    finally:
        conn.close()
        
    if row_count == 0:
        return jsonify({'error': 'Subject not found', 'error_ar': 'لم يتم العثور على المادة'}), 404
        
    return jsonify({'success': True, 'message': 'تم حذف المادة بنجاح', 'deleted': row_count})

# ------ Grade Levels Routes ------
@app.route('/api/school/<int:school_id>/grade-levels', methods=['GET'])
def get_grade_levels(school_id):
    """Get all grade levels for a school"""
    query = 'SELECT * FROM grade_levels WHERE school_id = %s ORDER BY display_order, name'
    grade_levels = []
    pool = get_mysql_pool()
    if not pool:
        return jsonify({'error': 'Database connection failed', 'error_ar': 'فشل الاتصال بقاعدة البيانات'}), 500
        
    conn = pool.get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(query, (school_id,))
        grade_levels = cur.fetchall()
    finally:
        conn.close()
    return jsonify({'success': True, 'grade_levels': grade_levels})

@app.route('/api/school/<int:school_id>/grade-level', methods=['POST'])
@roles_required('admin', 'school')
def add_grade_level(school_id):
    """Add a new grade level for a school"""
    data = request.json
    name = data.get('name')
    display_order = data.get('display_order', 0)
    
    if not name:
        return jsonify({'error': 'Grade level name is required', 'error_ar': 'اسم المستوى الدراسي مطلوب'}), 400
        
    # Check for duplicate
    check_query = 'SELECT id FROM grade_levels WHERE school_id = %s AND name = %s'
    pool = get_mysql_pool()
    if not pool:
        return jsonify({'error': 'Database connection failed', 'error_ar': 'فشل الاتصال بقاعدة البيانات'}), 500
        
    conn = pool.get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(check_query, (school_id, name))
        if cur.fetchone():
            return jsonify({'error': 'Grade level already exists', 'error_ar': 'هذا المستوى الدراسي موجود بالفعل'}), 400
        
        query = 'INSERT INTO grade_levels (school_id, name, display_order) VALUES (%s, %s, %s)'
        cur.execute(query, (school_id, name, display_order))
        last_id = cur.lastrowid
        conn.commit()
        cur.execute('SELECT * FROM grade_levels WHERE id = %s', (last_id,))
        grade_level = cur.fetchone()
    finally:
        conn.close()
        
    return jsonify({'success': True, 'message': 'تم إضافة المستوى الدراسي بنجاح', 'grade_level': dict(grade_level)}), 201

@app.route('/api/grade-level/<int:grade_level_id>', methods=['PUT'])
@roles_required('admin', 'school')
def update_grade_level(grade_level_id):
    """Update an existing grade level"""
    data = request.json
    name = data.get('name')
    display_order = data.get('display_order')
    
    if not name:
        return jsonify({'error': 'Grade level name is required', 'error_ar': 'اسم المستوى الدراسي مطلوب'}), 400
    
    query = 'UPDATE grade_levels SET name = %s, display_order = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s'
    params = (name, display_order or 0, grade_level_id)
    
    pool = get_mysql_pool()
    if not pool:
        return jsonify({'error': 'Database connection failed', 'error_ar': 'فشل الاتصال بقاعدة البيانات'}), 500
        
    conn = pool.get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(query, params)
        conn.commit()
        cur.execute('SELECT * FROM grade_levels WHERE id = %s', (grade_level_id,))
        grade_level = cur.fetchone()
    finally:
        conn.close()
        
    if not grade_level:
        return jsonify({'error': 'Grade level not found', 'error_ar': 'لم يتم العثور على المستوى الدراسي'}), 404
        
    return jsonify({'success': True, 'message': 'تم تحديث المستوى الدراسي بنجاح', 'grade_level': dict(grade_level)})

@app.route('/api/grade-level/<int:grade_level_id>', methods=['DELETE'])
@roles_required('admin', 'school')
def delete_grade_level(grade_level_id):
    """Delete a grade level"""
    pool = get_mysql_pool()
    if not pool:
        return jsonify({'error': 'Database connection failed', 'error_ar': 'فشل الاتصال بقاعدة البيانات'}), 500
        
    conn = pool.get_connection()
    try:
        cur = conn.cursor()
        cur.execute('DELETE FROM grade_levels WHERE id = %s', (grade_level_id,))
        row_count = cur.rowcount
        conn.commit()
    finally:
        conn.close()
        
    if row_count == 0:
        return jsonify({'error': 'Grade level not found', 'error_ar': 'لم يتم العثور على المستوى الدراسي'}), 404
        
    return jsonify({'success': True, 'message': 'تم حذف المستوى الدراسي بنجاح', 'deleted': row_count})

@app.route('/api/school/<int:school_id>/grade-levels/bulk', methods=['POST'])
@roles_required('admin', 'school')
def add_bulk_grade_levels(school_id):
    """Add multiple grade levels at once"""
    data = request.json
    grade_levels = data.get('grade_levels', [])
    
    if not grade_levels:
        return jsonify({'error': 'Grade levels list is required', 'error_ar': 'قائمة المستويات الدراسية مطلوبة'}), 400
    
    pool = get_mysql_pool()
    if not pool:
        return jsonify({'error': 'Database connection failed', 'error_ar': 'فشل الاتصال بقاعدة البيانات'}), 500
        
    conn = pool.get_connection()
    added = []
    try:
        cur = conn.cursor(dictionary=True)
        for i, gl in enumerate(grade_levels):
            name = gl.get('name') if isinstance(gl, dict) else gl
            if not name:
                continue
            display_order = gl.get('display_order', i) if isinstance(gl, dict) else i
            
            # Check for duplicate
            cur.execute('SELECT id FROM grade_levels WHERE school_id = %s AND name = %s', (school_id, name))
            if cur.fetchone():
                continue
            
            cur.execute('INSERT INTO grade_levels (school_id, name, display_order) VALUES (%s, %s, %s)',
                       (school_id, name, display_order))
            last_id = cur.lastrowid
            cur.execute('SELECT * FROM grade_levels WHERE id = %s', (last_id,))
            added.append(dict(cur.fetchone()))
        conn.commit()
    finally:
        conn.close()
        
    return jsonify({'success': True, 'message': f'تم إضافة {len(added)} مستوى دراسي', 'grade_levels': added}), 201

# ------ Teachers Routes ------
@app.route('/api/school/<int:school_id>/teachers', methods=['GET'])
@roles_required('admin', 'school')
def get_teachers(school_id):
    """Get all teachers for a school, optionally filtered by grade level"""
    grade_level = request.args.get('grade_level')
    
    if grade_level:
        query = '''SELECT t.*, s.name as subject_name 
                   FROM teachers t 
                   LEFT JOIN subjects s ON t.subject_id = s.id 
                   WHERE t.school_id = %s AND t.grade_level = %s 
                   ORDER BY t.full_name'''
        params = (school_id, grade_level)
    else:
        query = '''SELECT t.*, s.name as subject_name 
                   FROM teachers t 
                   LEFT JOIN subjects s ON t.subject_id = s.id 
                   WHERE t.school_id = %s 
                   ORDER BY t.grade_level, t.full_name'''
        params = (school_id,)
    
    teachers = []
    pool = get_mysql_pool()
    if not pool:
        return jsonify({'error': 'Database connection failed', 'error_ar': 'فشل الاتصال بقاعدة البيانات'}), 500
        
    conn = pool.get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(query, params)
        teachers = cur.fetchall()
    finally:
        conn.close()
    return jsonify({'success': True, 'teachers': teachers})

@app.route('/api/school/<int:school_id>/teacher', methods=['POST'])
@roles_required('admin', 'school')
def add_teacher(school_id):
    """Add a new teacher"""
    data = request.json
    full_name = data.get('full_name')
    phone = data.get('phone')
    email = data.get('email')
    subject_id = data.get('subject_id')
    grade_level = data.get('grade_level')
    specialization = data.get('specialization')
    
    if not full_name or not grade_level:
        return jsonify({
            'error': 'Teacher name and grade level are required',
            'error_ar': 'اسم المعلم والمستوى الدراسي مطلوبان'
        }), 400
    
    query = '''INSERT INTO teachers (school_id, full_name, phone, email, subject_id, grade_level, specialization) 
               VALUES (%s, %s, %s, %s, %s, %s, %s)'''
    params = (school_id, full_name, phone, email, subject_id, grade_level, specialization)
    
    teacher = None
    pool = get_mysql_pool()
    if not pool:
        return jsonify({'error': 'Database connection failed', 'error_ar': 'فشل الاتصال بقاعدة البيانات'}), 500
        
    conn = pool.get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(query, params)
        last_id = cur.lastrowid
        conn.commit()
        # Fetch the created teacher with subject name
        cur.execute('''SELECT t.*, s.name as subject_name 
                       FROM teachers t 
                       LEFT JOIN subjects s ON t.subject_id = s.id 
                       WHERE t.id = %s''', (last_id,))
        teacher = cur.fetchone()
    finally:
        conn.close()
        
    return jsonify({
        'success': True,
        'message': 'تم إضافة المعلم بنجاح',
        'teacher': dict(teacher)
    }), 201

@app.route('/api/teacher/<int:teacher_id>', methods=['PUT'])
@roles_required('admin', 'school')
def update_teacher(teacher_id):
    """Update a teacher"""
    data = request.json
    full_name = data.get('full_name')
    phone = data.get('phone')
    email = data.get('email')
    subject_id = data.get('subject_id')
    grade_level = data.get('grade_level')
    specialization = data.get('specialization')
    
    if not full_name or not grade_level:
        return jsonify({
            'error': 'Teacher name and grade level are required',
            'error_ar': 'اسم المعلم والمستوى الدراسي مطلوبان'
        }), 400
    
    query = '''UPDATE teachers SET full_name = %s, phone = %s, email = %s, 
               subject_id = %s, grade_level = %s, specialization = %s, 
               updated_at = CURRENT_TIMESTAMP WHERE id = %s'''
    params = (full_name, phone, email, subject_id, grade_level, specialization, teacher_id)
    
    teacher = None
    pool = get_mysql_pool()
    if not pool:
        return jsonify({'error': 'Database connection failed', 'error_ar': 'فشل الاتصال بقاعدة البيانات'}), 500
        
    conn = pool.get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(query, params)
        conn.commit()
        # Fetch the updated teacher with subject name
        cur.execute('''SELECT t.*, s.name as subject_name 
                       FROM teachers t 
                       LEFT JOIN subjects s ON t.subject_id = s.id 
                       WHERE t.id = %s''', (teacher_id,))
        teacher = cur.fetchone()
    finally:
        conn.close()
        
    if not teacher:
        return jsonify({'error': 'Teacher not found', 'error_ar': 'لم يتم العثور على المعلم'}), 404
        
    return jsonify({
        'success': True,
        'message': 'تم تحديث بيانات المعلم بنجاح',
        'teacher': dict(teacher)
    })

@app.route('/api/teacher/<int:teacher_id>', methods=['DELETE'])
@roles_required('admin', 'school')
def delete_teacher(teacher_id):
    """Delete a teacher"""
    pool = get_mysql_pool()
    if not pool:
        return jsonify({'error': 'Database connection failed', 'error_ar': 'فشل الاتصال بقاعدة البيانات'}), 500
        
    conn = pool.get_connection()
    try:
        cur = conn.cursor()
        cur.execute('DELETE FROM teachers WHERE id = %s', (teacher_id,))
        row_count = cur.rowcount
        conn.commit()
    finally:
        conn.close()
        
    if row_count == 0:
        return jsonify({'error': 'Teacher not found', 'error_ar': 'لم يتم العثور على المعلم'}), 404
        
    return jsonify({'success': True, 'message': 'تم حذف المعلم بنجاح', 'deleted': row_count})

# ------ Academic Years Routes ------

def get_current_academic_year_name():
    """Calculate the current academic year based on the current date.
    Academic year starts in September and ends in June.
    For example: If current date is between Sep 2025 - June 2026, the year is 2025/2026
    """
    now = datetime.datetime.now()
    current_month = now.month
    current_year = now.year
    
    # If we're between September and December, the academic year is current_year/next_year
    # If we're between January and August, the academic year is previous_year/current_year
    if current_month >= 9:  # September to December
        start_year = current_year
        end_year = current_year + 1
    else:  # January to August
        start_year = current_year - 1
        end_year = current_year
    
    return f"{start_year}/{end_year}", start_year, end_year

@app.route('/api/academic-year/current', methods=['GET'])
def get_current_academic_year_info():
    """Get the current academic year information - automatically calculated from system date"""
    # Calculate the current academic year based on the current date
    name, start_year, end_year = get_current_academic_year_name()
    
    pool = get_mysql_pool()
    if pool:
        conn = pool.get_connection()
        try:
            cur = conn.cursor(dictionary=True)
            # Try to find the calculated year in the database
            cur.execute('SELECT * FROM system_academic_years WHERE name = %s', (name,))
            current_year = cur.fetchone()
            
            if current_year:
                return jsonify({
                    'success': True,
                    'academic_year_id': current_year['id'],
                    'academic_year_name': current_year['name'],
                    'current_academic_year': current_year
                })
            else:
                # Create the academic year if it doesn't exist
                start_date = f"{start_year}-09-01"
                end_date = f"{end_year}-06-30"
                cur.execute('''INSERT INTO system_academic_years (name, start_year, end_year, start_date, end_date, is_current) 
                               VALUES (%s, %s, %s, %s, %s, 1)''',
                           (name, start_year, end_year, start_date, end_date))
                last_id = cur.lastrowid
                conn.commit()
                
                cur.execute('SELECT * FROM system_academic_years WHERE id = %s', (last_id,))
                current_year = cur.fetchone()
                
                return jsonify({
                    'success': True,
                    'academic_year_id': current_year['id'],
                    'academic_year_name': current_year['name'],
                    'current_academic_year': current_year
                })
        finally:
            conn.close()
    
    # Fall back to calculated year without database
    start_date = f"{start_year}-09-01"
    end_date = f"{end_year}-06-30"
    
    return jsonify({
        'success': True,
        'academic_year_name': name,
        'current_academic_year': {
            'name': name,
            'start_year': start_year,
            'end_year': end_year,
            'start_date': start_date,
            'end_date': end_date
        }
    })

# ============================================================================
# CENTRALIZED SYSTEM-WIDE ACADEMIC YEAR MANAGEMENT (Admin Only)
# ============================================================================

@app.route('/api/system/academic-years', methods=['GET'])
def get_system_academic_years():
    """Get all system-wide academic years (applies to all schools)
    Automatically marks the current year based on the present date.
    """
    # Calculate the current academic year name based on date
    current_year_name, _, _ = get_current_academic_year_name()
    
    pool = get_mysql_pool()
    if not pool:
        return jsonify({'error': 'Database connection failed', 'error_ar': 'فشل الاتصال بقاعدة البيانات'}), 500
        
    conn = pool.get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute('SELECT * FROM system_academic_years ORDER BY start_year DESC')
        academic_years = cur.fetchall()
        
        # Mark the current year based on date calculation (override database is_current)
        for year in academic_years:
            year['is_current'] = 1 if year['name'] == current_year_name else 0
    finally:
        conn.close()
    return jsonify({'success': True, 'academic_years': academic_years, 'current_year_name': current_year_name})

@app.route('/api/system/academic-year', methods=['POST'])
@roles_required('admin')
def add_system_academic_year():
    """Add a new system-wide academic year (admin only - applies to all schools)"""
    data = request.json
    name = data.get('name')
    start_year = data.get('start_year')
    end_year = data.get('end_year')
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    is_current = data.get('is_current', False)
    
    if not name or not start_year or not end_year:
        return jsonify({
            'error': 'Name, start_year, and end_year are required',
            'error_ar': 'الاسم وسنة البداية وسنة النهاية مطلوبة'
        }), 400
    
    # Validate that end_year is start_year + 1
    if int(end_year) != int(start_year) + 1:
        return jsonify({
            'error': 'End year must be start year + 1',
            'error_ar': 'سنة النهاية يجب أن تكون سنة البداية + 1'
        }), 400
    
    pool = get_mysql_pool()
    if not pool:
        return jsonify({'error': 'Database connection failed', 'error_ar': 'فشل الاتصال بقاعدة البيانات'}), 500
        
    conn = pool.get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        
        # Check for duplicate
        cur.execute('SELECT id FROM system_academic_years WHERE name = %s', (name,))
        if cur.fetchone():
            return jsonify({
                'error': 'Academic year already exists',
                'error_ar': 'هذه السنة الدراسية موجودة بالفعل'
            }), 400
        
        # If this year should be current, unset other current years
        if is_current:
            cur.execute('UPDATE system_academic_years SET is_current = 0')
        
        # Set default dates if not provided
        if not start_date:
            start_date = f"{start_year}-09-01"
        if not end_date:
            end_date = f"{end_year}-06-30"
        
        query = '''INSERT INTO system_academic_years (name, start_year, end_year, start_date, end_date, is_current) 
                   VALUES (%s, %s, %s, %s, %s, %s)'''
        cur.execute(query, (name, start_year, end_year, start_date, end_date, 1 if is_current else 0))
        last_id = cur.lastrowid
        conn.commit()
        
        cur.execute('SELECT * FROM system_academic_years WHERE id = %s', (last_id,))
        academic_year = cur.fetchone()
    finally:
        conn.close()
        
    return jsonify({
        'success': True,
        'message': 'تم إضافة السنة الدراسية بنجاح',
        'academic_year': dict(academic_year)
    }), 201

@app.route('/api/system/academic-year/<int:year_id>/set-current', methods=['POST'])
@roles_required('admin')
def set_system_current_academic_year(year_id):
    """Set a system-wide academic year as the current year (admin only)"""
    pool = get_mysql_pool()
    if not pool:
        return jsonify({'error': 'Database connection failed', 'error_ar': 'فشل الاتصال بقاعدة البيانات'}), 500
        
    conn = pool.get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        
        # Check if year exists
        cur.execute('SELECT id FROM system_academic_years WHERE id = %s', (year_id,))
        if not cur.fetchone():
            return jsonify({'error': 'Academic year not found', 'error_ar': 'لم يتم العثور على السنة الدراسية'}), 404
        
        # Unset all current years
        cur.execute('UPDATE system_academic_years SET is_current = 0')
        
        # Set this year as current
        cur.execute('UPDATE system_academic_years SET is_current = 1 WHERE id = %s', (year_id,))
        conn.commit()
        
        cur.execute('SELECT * FROM system_academic_years WHERE id = %s', (year_id,))
        academic_year = cur.fetchone()
    finally:
        conn.close()
        
    return jsonify({
        'success': True,
        'message': 'تم تعيين السنة الدراسية الحالية بنجاح',
        'academic_year': dict(academic_year)
    })

@app.route('/api/system/academic-year/<int:year_id>', methods=['DELETE'])
@roles_required('admin')
def delete_system_academic_year(year_id):
    """Delete a system-wide academic year (admin only)"""
    pool = get_mysql_pool()
    if not pool:
        return jsonify({'error': 'Database connection failed', 'error_ar': 'فشل الاتصال بقاعدة البيانات'}), 500
        
    conn = pool.get_connection()
    try:
        cur = conn.cursor()
        # First delete related records in student_grades and student_attendance
        # (These will be automatically deleted via foreign key CASCADE, but we do it explicitly for clarity)
        cur.execute('DELETE FROM student_grades WHERE academic_year_id = %s', (year_id,))
        cur.execute('DELETE FROM student_attendance WHERE academic_year_id = %s', (year_id,))
        
        # Then delete the academic year itself
        cur.execute('DELETE FROM system_academic_years WHERE id = %s', (year_id,))
        row_count = cur.rowcount
        conn.commit()
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'error': 'Failed to delete academic year due to related data', 'error_ar': 'فشل حذف السنة الدراسية بسبب وجود بيانات مرتبطة'}), 500
    finally:
        conn.close()
        
    if row_count == 0:
        return jsonify({'error': 'Academic year not found', 'error_ar': 'لم يتم العثور على السنة الدراسية'}), 404
        
    return jsonify({'success': True, 'message': 'تم حذف السنة الدراسية بنجاح', 'deleted': row_count})

@app.route('/api/system/academic-years/generate', methods=['POST'])
@roles_required('admin')
def generate_system_academic_years():
    """Generate upcoming system-wide academic years (admin only)"""
    data = request.json
    count = data.get('count', 5)  # Generate 5 years by default
    
    pool = get_mysql_pool()
    if not pool:
        return jsonify({'error': 'Database connection failed', 'error_ar': 'فشل الاتصال بقاعدة البيانات'}), 500
        
    conn = pool.get_connection()
    added = []
    try:
        cur = conn.cursor(dictionary=True)
        
        # Get the current academic year info
        _, current_start_year, _ = get_current_academic_year_name()
        
        # Check if any current year is set
        cur.execute('SELECT id FROM system_academic_years WHERE is_current = 1')
        has_current = cur.fetchone() is not None
        
        # Generate academic years starting from current year
        for i in range(count):
            start_year = current_start_year + i
            end_year = start_year + 1
            name = f"{start_year}/{end_year}"
            start_date = f"{start_year}-09-01"
            end_date = f"{end_year}-06-30"
            is_current = 1 if (i == 0 and not has_current) else 0
            
            # Check if already exists
            cur.execute('SELECT id FROM system_academic_years WHERE name = %s', (name,))
            if cur.fetchone():
                continue
            
            cur.execute('''INSERT INTO system_academic_years (name, start_year, end_year, start_date, end_date, is_current) 
                           VALUES (%s, %s, %s, %s, %s, %s)''',
                       (name, start_year, end_year, start_date, end_date, is_current))
            last_id = cur.lastrowid
            cur.execute('SELECT * FROM system_academic_years WHERE id = %s', (last_id,))
            added.append(dict(cur.fetchone()))
        
        conn.commit()
    finally:
        conn.close()
        
    return jsonify({
        'success': True,
        'message': f'تم إنشاء {len(added)} سنوات دراسية',
        'academic_years': added
    })

# ============================================================================
# LEGACY PER-SCHOOL ENDPOINTS (Redirected to System Academic Years)
# These endpoints now read from the centralized system_academic_years table
# ============================================================================

@app.route('/api/school/<int:school_id>/academic-years', methods=['GET'])
def get_academic_years(school_id):
    """Get all academic years (now returns system-wide years for all schools)"""
    # Redirect to system-wide academic years
    pool = get_mysql_pool()
    if not pool:
        return jsonify({'error': 'Database connection failed', 'error_ar': 'فشل الاتصال بقاعدة البيانات'}), 500
        
    conn = pool.get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute('SELECT * FROM system_academic_years ORDER BY start_year DESC')
        academic_years = cur.fetchall()
        
        # Mark current year based on date calculation
        current_year_name, _, _ = get_current_academic_year_name()
        for year in academic_years:
            year['is_current'] = 1 if year['name'] == current_year_name else 0
    finally:
        conn.close()
    return jsonify({'success': True, 'academic_years': academic_years})

@app.route('/api/school/<int:school_id>/academic-year/current', methods=['GET'])
def get_school_current_academic_year(school_id):
    """Get the current academic year - automatically calculated from system date"""
    # Calculate the current academic year based on the current date
    name, start_year, end_year = get_current_academic_year_name()
    
    pool = get_mysql_pool()
    if not pool:
        return jsonify({'error': 'Database connection failed', 'error_ar': 'فشل الاتصال بقاعدة البيانات'}), 500
        
    conn = pool.get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        # Try to find the calculated year in the database
        cur.execute('SELECT * FROM system_academic_years WHERE name = %s', (name,))
        academic_year = cur.fetchone()
        
        # If not found, create it automatically
        if not academic_year:
            start_date = f"{start_year}-09-01"
            end_date = f"{end_year}-06-30"
            
            cur.execute('''INSERT INTO system_academic_years (name, start_year, end_year, start_date, end_date, is_current) 
                           VALUES (%s, %s, %s, %s, %s, 1)''',
                       (name, start_year, end_year, start_date, end_date))
            last_id = cur.lastrowid
            conn.commit()
            
            cur.execute('SELECT * FROM system_academic_years WHERE id = %s', (last_id,))
            academic_year = cur.fetchone()
        
        # Ensure is_current is set correctly
        academic_year['is_current'] = 1
    finally:
        conn.close()
        
    return jsonify({'success': True, 'academic_year': academic_year})

# Legacy endpoint - academic year creation is now admin-only via /api/system/academic-year
# This endpoint is kept for backward compatibility but redirects to error
@app.route('/api/school/<int:school_id>/academic-year', methods=['POST'])
def add_academic_year(school_id):
    """Legacy endpoint - academic year management is now centralized at system level"""
    return jsonify({
        'error': 'Academic year management is now centralized. Please contact system administrator.',
        'error_ar': 'إدارة السنوات الدراسية أصبحت مركزية. يرجى التواصل مع مدير النظام.'
    }), 403

# Legacy endpoint - academic year update is now admin-only via system endpoints
@app.route('/api/academic-year/<int:year_id>', methods=['PUT'])
def update_academic_year(year_id):
    """Legacy endpoint - academic year management is now centralized at system level"""
    return jsonify({
        'error': 'Academic year management is now centralized. Please contact system administrator.',
        'error_ar': 'إدارة السنوات الدراسية أصبحت مركزية. يرجى التواصل مع مدير النظام.'
    }), 403

# Legacy endpoint - setting current year is now admin-only via system endpoints
@app.route('/api/academic-year/<int:year_id>/set-current', methods=['POST'])
def set_current_academic_year(year_id):
    """Legacy endpoint - academic year management is now centralized at system level"""
    return jsonify({
        'error': 'Academic year management is now centralized. Please contact system administrator.',
        'error_ar': 'إدارة السنوات الدراسية أصبحت مركزية. يرجى التواصل مع مدير النظام.'
    }), 403

# Legacy endpoint - academic year deletion is now admin-only via system endpoints
@app.route('/api/academic-year/<int:year_id>', methods=['DELETE'])
def delete_academic_year(year_id):
    """Legacy endpoint - academic year management is now centralized at system level"""
    return jsonify({
        'error': 'Academic year management is now centralized. Please contact system administrator.',
        'error_ar': 'إدارة السنوات الدراسية أصبحت مركزية. يرجى التواصل مع مدير النظام.'
    }), 403

# Legacy endpoint - generating years is now admin-only via system endpoints
@app.route('/api/school/<int:school_id>/academic-year/generate-upcoming', methods=['POST'])
def generate_upcoming_academic_years(school_id):
    """Legacy endpoint - academic year management is now centralized at system level"""
    return jsonify({
        'error': 'Academic year management is now centralized. Please contact system administrator.',
        'error_ar': 'إدارة السنوات الدراسية أصبحت مركزية. يرجى التواصل مع مدير النظام.'
    }), 403

@app.route('/api/student/<int:student_id>/grades/<int:academic_year_id>', methods=['GET'])
@roles_required('admin', 'school', 'student')
def get_student_grades_by_year(student_id, academic_year_id):
    """Get student grades for a specific academic year"""
    query = 'SELECT * FROM student_grades WHERE student_id = %s AND academic_year_id = %s ORDER BY subject_name'
    grades = []
    pool = get_mysql_pool()
    if not pool:
        return jsonify({'error': 'Database connection failed', 'error_ar': 'فشل الاتصال بقاعدة البيانات'}), 500
        
    conn = pool.get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(query, (student_id, academic_year_id))
        grades = cur.fetchall()
    finally:
        conn.close()
        
    # Convert to the format expected by the frontend
    grades_dict = {}
    for grade in grades:
        grades_dict[grade['subject_name']] = {
            'month1': grade['month1'],
            'month2': grade['month2'],
            'midterm': grade['midterm'],
            'month3': grade['month3'],
            'month4': grade['month4'],
            'final': grade['final']
        }
    
    return jsonify({'success': True, 'grades': grades_dict, 'raw_grades': grades})

@app.route('/api/student/<int:student_id>/grades/<int:academic_year_id>', methods=['PUT'])
@roles_required('admin', 'school')
def update_student_grades_by_year(student_id, academic_year_id):
    """Update student grades for a specific academic year"""
    data = request.json
    grades = data.get('grades', {})
    
    pool = get_mysql_pool()
    if not pool:
        return jsonify({'error': 'Database connection failed', 'error_ar': 'فشل الاتصال بقاعدة البيانات'}), 500
        
    conn = pool.get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        
        for subject_name, subject_grades in grades.items():
            if subject_name == '[object Object]' or not subject_name:
                continue
                
            # Check if grade record exists
            cur.execute('SELECT id FROM student_grades WHERE student_id = %s AND academic_year_id = %s AND subject_name = %s',
                       (student_id, academic_year_id, subject_name))
            existing = cur.fetchone()
            
            month1 = int(subject_grades.get('month1', 0) or 0)
            month2 = int(subject_grades.get('month2', 0) or 0)
            midterm = int(subject_grades.get('midterm', 0) or 0)
            month3 = int(subject_grades.get('month3', 0) or 0)
            month4 = int(subject_grades.get('month4', 0) or 0)
            final = int(subject_grades.get('final', 0) or 0)
            
            if existing:
                cur.execute('''UPDATE student_grades SET 
                               month1 = %s, month2 = %s, midterm = %s, month3 = %s, month4 = %s, final = %s,
                               updated_at = CURRENT_TIMESTAMP
                               WHERE id = %s''',
                           (month1, month2, midterm, month3, month4, final, existing['id']))
            else:
                cur.execute('''INSERT INTO student_grades 
                               (student_id, academic_year_id, subject_name, month1, month2, midterm, month3, month4, final)
                               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                           (student_id, academic_year_id, subject_name, month1, month2, midterm, month3, month4, final))
        
        conn.commit()
    finally:
        conn.close()
        
    return jsonify({'success': True, 'message': 'تم حفظ الدرجات بنجاح'})

@app.route('/api/student/<int:student_id>/attendance/<int:academic_year_id>', methods=['GET'])
@roles_required('admin', 'school', 'student')
def get_student_attendance_by_year(student_id, academic_year_id):
    """Get student attendance for a specific academic year"""
    query = 'SELECT * FROM student_attendance WHERE student_id = %s AND academic_year_id = %s ORDER BY attendance_date DESC'
    attendance_records = []
    pool = get_mysql_pool()
    if not pool:
        return jsonify({'error': 'Database connection failed', 'error_ar': 'فشل الاتصال بقاعدة البيانات'}), 500
        
    conn = pool.get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(query, (student_id, academic_year_id))
        attendance_records = cur.fetchall()
    finally:
        conn.close()
        
    # Convert to the format expected by the frontend
    attendance_dict = {}
    for record in attendance_records:
        date_str = record['attendance_date'].strftime('%Y-%m-%d') if hasattr(record['attendance_date'], 'strftime') else str(record['attendance_date'])
        attendance_dict[date_str] = {
            'status': record['status'],
            'notes': record['notes']
        }
    
    return jsonify({'success': True, 'attendance': attendance_dict, 'raw_attendance': attendance_records})

@app.route('/api/student/<int:student_id>/attendance/<int:academic_year_id>', methods=['PUT'])
@roles_required('admin', 'school')
def update_student_attendance_by_year(student_id, academic_year_id):
    """Update student attendance for a specific academic year"""
    data = request.json
    attendance = data.get('attendance', {})
    
    pool = get_mysql_pool()
    if not pool:
        return jsonify({'error': 'Database connection failed', 'error_ar': 'فشل الاتصال بقاعدة البيانات'}), 500
        
    conn = pool.get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        
        for date_str, record in attendance.items():
            status = record.get('status', 'present')
            notes = record.get('notes', '')
            
            # Check if attendance record exists
            cur.execute('SELECT id FROM student_attendance WHERE student_id = %s AND academic_year_id = %s AND attendance_date = %s',
                       (student_id, academic_year_id, date_str))
            existing = cur.fetchone()
            
            if existing:
                cur.execute('UPDATE student_attendance SET status = %s, notes = %s WHERE id = %s',
                           (status, notes, existing['id']))
            else:
                cur.execute('''INSERT INTO student_attendance (student_id, academic_year_id, attendance_date, status, notes)
                               VALUES (%s, %s, %s, %s, %s)''',
                           (student_id, academic_year_id, date_str, status, notes))
        
        conn.commit()
    finally:
        conn.close()
        
    return jsonify({'success': True, 'message': 'تم حفظ سجل الحضور بنجاح'})

@app.route('/api/student/<int:student_id>/attendance/<int:academic_year_id>/add', methods=['POST'])
@roles_required('admin', 'school')
def add_student_attendance_record(student_id, academic_year_id):
    """Add a single attendance record for a student"""
    data = request.json
    date_str = data.get('date')
    status = data.get('status', 'present')
    notes = data.get('notes', '')
    
    if not date_str:
        return jsonify({'error': 'Date is required', 'error_ar': 'التاريخ مطلوب'}), 400
    
    pool = get_mysql_pool()
    if not pool:
        return jsonify({'error': 'Database connection failed', 'error_ar': 'فشل الاتصال بقاعدة البيانات'}), 500
        
    conn = pool.get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        
        # Check if attendance record exists
        cur.execute('SELECT id FROM student_attendance WHERE student_id = %s AND academic_year_id = %s AND attendance_date = %s',
                   (student_id, academic_year_id, date_str))
        existing = cur.fetchone()
        
        if existing:
            cur.execute('UPDATE student_attendance SET status = %s, notes = %s WHERE id = %s',
                       (status, notes, existing['id']))
        else:
            cur.execute('''INSERT INTO student_attendance (student_id, academic_year_id, attendance_date, status, notes)
                           VALUES (%s, %s, %s, %s, %s)''',
                       (student_id, academic_year_id, date_str, status, notes))
        
        conn.commit()
    finally:
        conn.close()
        
    return jsonify({'success': True, 'message': 'تم إضافة سجل الحضور بنجاح'})

# ============================================================================
# STUDENT PROMOTION FUNCTIONALITY
# ============================================================================

@app.route('/api/student/<int:student_id>/promote', methods=['POST'])
@roles_required('admin', 'school')
def promote_student(student_id):
    """Promote a student to the next grade level, preserving historical grades and creating new records for the new grade level.
    This endpoint ensures that:
    1. The student's current grade level is updated to the next grade
    2. All historical grades remain intact in the database
    3. New grade records are created for the new academic year
    """
    data = request.json
    new_grade = data.get('new_grade')
    new_academic_year_id = data.get('new_academic_year_id')
    
    if not new_grade:
        return jsonify({'error': 'New grade is required', 'error_ar': 'المستوى الدراسي الجديد مطلوب'}), 400
    
    # Verify the student exists
    pool = get_mysql_pool()
    if not pool:
        return jsonify({'error': 'Database connection failed', 'error_ar': 'فشل الاتصال بقاعدة البيانات'}), 500
    
    conn = pool.get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        
        # Get current student data
        cur.execute('SELECT * FROM students WHERE id = %s', (student_id,))
        student = cur.fetchone()
        
        if not student:
            return jsonify({'error': 'Student not found', 'error_ar': 'لم يتم العثور على الطالب'}), 404
        
        # Get current academic year if not provided
        if not new_academic_year_id:
            cur.execute('SELECT id FROM system_academic_years WHERE is_current = 1 ORDER BY start_year DESC LIMIT 1')
            current_year = cur.fetchone()
            if current_year:
                new_academic_year_id = current_year['id']
            else:
                # If no current year is set, get the latest academic year
                cur.execute('SELECT id FROM system_academic_years ORDER BY start_year DESC LIMIT 1')
                year = cur.fetchone()
                if year:
                    new_academic_year_id = year['id']
        
        # Update the student's grade level
        cur.execute('UPDATE students SET grade = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s', 
                   (new_grade, student_id))
        
        # If a new academic year is specified, ensure all subjects from the previous grade are available in the new grade
        if new_academic_year_id:
            # Copy grades from the previous academic year to the new one if they don't exist yet
            # This prevents loss of grade data when promoting students
            
            # Get all subjects from the previous grade year (from detailed_scores if available)
            if student.get('detailed_scores'):
                detailed_scores = json.loads(student['detailed_scores']) if isinstance(student['detailed_scores'], str) else student['detailed_scores']
                
                for subject_name, subject_grades in detailed_scores.items():
                    # Check if this subject already exists for the new academic year
                    cur.execute('''SELECT id FROM student_grades 
                                   WHERE student_id = %s AND academic_year_id = %s AND subject_name = %s''',
                               (student_id, new_academic_year_id, subject_name))
                    existing_grade = cur.fetchone()
                    
                    if not existing_grade:
                        # Insert the subject grades for the new academic year
                        # Initially set to 0 as these are for the new grade level
                        cur.execute('''INSERT INTO student_grades 
                                       (student_id, academic_year_id, subject_name, month1, month2, midterm, month3, month4, final) 
                                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                                   (student_id, new_academic_year_id, subject_name, 0, 0, 0, 0, 0, 0))
        
        conn.commit()
        
        # Return updated student info
        cur.execute('SELECT * FROM students WHERE id = %s', (student_id,))
        updated_student = cur.fetchone()
        
        # Convert JSON fields back to dict for response
        if isinstance(updated_student.get('detailed_scores'), str):
            try:
                updated_student['detailed_scores'] = json.loads(updated_student['detailed_scores'])
            except:
                updated_student['detailed_scores'] = {}
        
        if isinstance(updated_student.get('daily_attendance'), str):
            try:
                updated_student['daily_attendance'] = json.loads(updated_student['daily_attendance'])
            except:
                updated_student['daily_attendance'] = {}
                
    finally:
        conn.close()
    
    return jsonify({
        'success': True,
        'message': 'تم ترقية الطالب بنجاح',
        'student': updated_student
    })

@app.route('/api/students/promote-many', methods=['POST'])
@roles_required('admin', 'school')
def promote_multiple_students():
    """Promote multiple students to the next grade level at once"""
    data = request.json
    student_ids = data.get('student_ids', [])
    new_grade = data.get('new_grade')
    new_academic_year_id = data.get('new_academic_year_id')
    
    if not student_ids or not new_grade:
        return jsonify({'error': 'Student IDs and new grade are required', 'error_ar': 'معرّفات الطلاب والمستوى الدراسي الجديد مطلوبة'}), 400
    
    pool = get_mysql_pool()
    if not pool:
        return jsonify({'error': 'Database connection failed', 'error_ar': 'فشل الاتصال بقاعدة البيانات'}), 500
    
    conn = pool.get_connection()
    promoted_count = 0
    failed_promotions = []
    
    try:
        cur = conn.cursor(dictionary=True)
        
        for student_id in student_ids:
            try:
                # Get current student data
                cur.execute('SELECT * FROM students WHERE id = %s FOR UPDATE', (student_id,))
                student = cur.fetchone()
                
                if not student:
                    failed_promotions.append({'id': student_id, 'reason': 'Student not found'})
                    continue
                
                # Get current academic year if not provided
                current_academic_year_id = new_academic_year_id
                if not current_academic_year_id:
                    cur.execute('SELECT id FROM system_academic_years WHERE is_current = 1 ORDER BY start_year DESC LIMIT 1')
                    current_year = cur.fetchone()
                    if current_year:
                        current_academic_year_id = current_year['id']
                    else:
                        # If no current year is set, get the latest academic year
                        cur.execute('SELECT id FROM system_academic_years ORDER BY start_year DESC LIMIT 1')
                        year = cur.fetchone()
                        if year:
                            current_academic_year_id = year['id']
                
                # Update the student's grade level
                cur.execute('UPDATE students SET grade = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s', 
                           (new_grade, student_id))
                
                # Handle grade copying for the new academic year if needed
                if current_academic_year_id:
                    if student.get('detailed_scores'):
                        detailed_scores = json.loads(student['detailed_scores']) if isinstance(student['detailed_scores'], str) else student['detailed_scores']
                        
                        for subject_name, subject_grades in detailed_scores.items():
                            # Check if this subject already exists for the new academic year
                            cur.execute('''SELECT id FROM student_grades 
                                           WHERE student_id = %s AND academic_year_id = %s AND subject_name = %s''',
                                       (student_id, current_academic_year_id, subject_name))
                            existing_grade = cur.fetchone()
                            
                            if not existing_grade:
                                # Insert the subject grades for the new academic year
                                cur.execute('''INSERT INTO student_grades 
                                               (student_id, academic_year_id, subject_name, month1, month2, midterm, month3, month4, final) 
                                               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                                           (student_id, current_academic_year_id, subject_name, 0, 0, 0, 0, 0, 0))
                
                promoted_count += 1
            except Exception as e:
                failed_promotions.append({'id': student_id, 'reason': str(e)})
        
        conn.commit()
        
    finally:
        conn.close()
    
    return jsonify({
        'success': True,
        'message': f'تم ترقية {promoted_count} طلاب بنجاح',
        'promoted_count': promoted_count,
        'failed_count': len(failed_promotions),
        'failed_promotions': failed_promotions
    })

@app.route('/api/student/<int:student_id>/history', methods=['GET'])
@roles_required('admin', 'school', 'student')
def get_student_history(student_id):
    """Get complete academic history for a student across all grade levels and academic years"""
    pool = get_mysql_pool()
    if not pool:
        return jsonify({'error': 'Database connection failed', 'error_ar': 'فشل الاتصال بقاعدة البيانات'}), 500
    
    conn = pool.get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        
        # Get student basic info
        cur.execute('SELECT * FROM students WHERE id = %s', (student_id,))
        student = cur.fetchone()
        
        if not student:
            return jsonify({'error': 'Student not found', 'error_ar': 'لم يتم العثور على الطالب'}), 404
        
        # Get all grades for this student across all academic years
        cur.execute('''SELECT sg.*, say.name as academic_year_name, say.start_year, say.end_year 
                       FROM student_grades sg 
                       JOIN system_academic_years say ON sg.academic_year_id = say.id 
                       WHERE sg.student_id = %s 
                       ORDER BY say.start_year DESC, sg.subject_name''', (student_id,))
        all_grades = cur.fetchall()
        
        # Group grades by academic year
        grades_by_year = {}
        for grade in all_grades:
            year_name = grade['academic_year_name']
            if year_name not in grades_by_year:
                grades_by_year[year_name] = {
                    'year_info': {
                        'id': grade['academic_year_id'],
                        'name': grade['academic_year_name'],
                        'start_year': grade['start_year'],
                        'end_year': grade['end_year']
                    },
                    'subjects': {}
                }
            
            grades_by_year[year_name]['subjects'][grade['subject_name']] = {
                'month1': grade['month1'],
                'month2': grade['month2'],
                'midterm': grade['midterm'],
                'month3': grade['month3'],
                'month4': grade['month4'],
                'final': grade['final']
            }
        
        # Get all attendance for this student across all academic years
        cur.execute('''SELECT sa.*, say.name as academic_year_name, say.start_year, say.end_year 
                       FROM student_attendance sa 
                       JOIN system_academic_years say ON sa.academic_year_id = say.id 
                       WHERE sa.student_id = %s 
                       ORDER BY sa.attendance_date DESC''', (student_id,))
        all_attendance = cur.fetchall()
        
        # Group attendance by academic year
        attendance_by_year = {}
        for record in all_attendance:
            year_name = record['academic_year_name']
            date_str = record['attendance_date'].strftime('%Y-%m-%d') if hasattr(record['attendance_date'], 'strftime') else str(record['attendance_date'])
            
            if year_name not in attendance_by_year:
                attendance_by_year[year_name] = {}
            
            attendance_by_year[year_name][date_str] = {
                'status': record['status'],
                'notes': record['notes']
            }
        
        # Convert JSON fields if needed
        if isinstance(student.get('detailed_scores'), str):
            try:
                student['detailed_scores'] = json.loads(student['detailed_scores'])
            except:
                student['detailed_scores'] = {}
        
        if isinstance(student.get('daily_attendance'), str):
            try:
                student['daily_attendance'] = json.loads(student['daily_attendance'])
            except:
                student['daily_attendance'] = {}
                
    finally:
        conn.close()
    
    return jsonify({
        'success': True,
        'student': student,
        'academic_history': {
            'grades': grades_by_year,
            'attendance': attendance_by_year
        }
    })

# Serve Static Files & Catch-all for SPA
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_static(path):
    if path.startswith('api/'):
        return jsonify({'error': 'API endpoint not found', 'error_ar': 'نقطة نهاية API غير موجودة'}), 404
        
    if path != "" and os.path.exists(app.static_folder + '/' + path):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

@app.route('/uploads/<filename>')
def serve_upload(filename):
    return send_from_directory(UPLOADS_DIR, filename)

if __name__ == '__main__':
    print(f"🚀 Server starting on http://localhost:{PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=(NODE_ENV != 'production'))
