import os
import requests  # 👈 השורה החשובה שהייתה חסרה!
import google.generativeai as genai
from flask import Flask, jsonify, request
import boto3
import uuid
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage  # 👈 הוסף את השורה הזו
from datetime import datetime, timedelta
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask import redirect


# ייבוא ספריות ה-DB והאבטחה
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash

from prometheus_flask_exporter import PrometheusMetrics
from prometheus_client import Counter, Gauge, Histogram # 👈 הוסף את השורה הזו

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

app = Flask(__name__)


limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "ה-CLIENT_ID_שלך_מגוגל.apps.googleusercontent.com")

# 👈 הוסף אתחול של המדדים:
metrics = PrometheusMetrics(app)
metrics.info('app_info', 'DogOps Application info', version='1.0.0')


# ==========================================
# Custom Prometheus Metrics
# ==========================================
# 1. Gauge: עוקב אחרי כמות הפרופילים הקיימים במערכת (מספר שיכול לעלות ולרדת)
DOG_PROFILES_GAUGE = Gauge('dogops_active_profiles', 'Number of dog profiles registered in the system')

# 2. Counter: סופר כמה דיווחים התקבלו, מחולק לפי תווית (טוב/רע)
DOG_EVENTS_COUNTER = Counter('dogops_behavior_events_total', 'Total behavior events logged', ['event_type'])

# 3. Histogram: מודד כמה זמן לוקח למודל ה-AI לענות (עם Buckets משלנו)
AI_LATENCY_HISTOGRAM = Histogram('dogops_ai_response_seconds', 'Time spent waiting for Gemini AI', buckets=(0.5, 1.0, 2.0, 3.0, 5.0, float("inf")))

# 4. Counter: מעקב אחרי שגיאות התחברות (חיוני לזיהוי מתקפות Brute Force)
LOGIN_FAILURES_COUNTER = Counter('dogops_login_failures_total', 'Total failed login attempts')

# 5. Histogram: זמני העלאת תמונות ל-AWS S3
S3_UPLOAD_LATENCY_HISTOGRAM = Histogram('dogops_s3_upload_seconds', 'Time spent uploading to S3')

# 6. Histogram: זמני תגובה של שירות מזג האוויר החיצוני
WEATHER_API_LATENCY_HISTOGRAM = Histogram('dogops_weather_api_seconds', 'Time spent fetching weather')

# הגדרות בסיס נתונים (ייקראו אוטומטית מהסביבה בקוברנטיס)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/dogops')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'super-secret-key-change-in-prod')
# הגדרות חיבור ל-AWS S3 (יימשך אוטומטית בענן או מהסביבה המקומית)
S3_BUCKET = os.getenv('S3_BUCKET_NAME', 'devops-dogops-images')
s3_client = boto3.client('s3', region_name=os.getenv('AWS_REGION', 'us-east-1'))

# אתחול הכלים
db = SQLAlchemy(app)
jwt = JWTManager(app)

# ==========================================
# Database Models (טבלאות בסיס הנתונים)
# ==========================================
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(50), nullable=True) 
    last_name = db.Column(db.String(50), nullable=True)  
    reset_code = db.Column(db.String(10), nullable=True)
    reset_code_expiry = db.Column(db.DateTime, nullable=True)
    last_password_change = db.Column(db.DateTime, default=datetime.utcnow) # מתי שונתה סיסמה אחרונה
    auth_provider = db.Column(db.String(50), default='local')

class PasswordHistory(db.Model):
    __tablename__ = 'password_history'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class DogProfile(db.Model):
    __tablename__ = 'dog_profiles'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100))
    breed = db.Column(db.String(100))
    city = db.Column(db.String(100))
    dob = db.Column(db.String(50))
    gender = db.Column(db.String(50))
    status = db.Column(db.String(50))
    weight = db.Column(db.String(50))
    chip = db.Column(db.String(100))
    allergies = db.Column(db.String(200))
    image_url = db.Column(db.Text)

class Todo(db.Model):
    __tablename__ = 'todos'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.String(50), default=lambda: datetime.now().isoformat())
    priority = db.Column(db.String(50), nullable=True)
    due_date = db.Column(db.String(50), nullable=True)
    location = db.Column(db.String(200), nullable=True)
    gps_link = db.Column(db.String(500), nullable=True)

class Vaccine(db.Model):
    __tablename__ = 'vaccines'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    type = db.Column(db.String(100), nullable=False)
    given_date = db.Column(db.String(50), nullable=False)
    expiry_date = db.Column(db.String(50), nullable=False)

class Summary(db.Model):
    __tablename__ = 'summaries'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date = db.Column(db.String(50), nullable=False)
    text = db.Column(db.Text, nullable=False)
    is_auto = db.Column(db.Boolean, default=False)

# פקודה שמייצרת את הטבלאות ב-Postgres אוטומטית בעליית האפליקציה
with app.app_context():
    db.create_all()

def send_dogops_email(to_email, subject, title, body_text):
    smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.getenv('SMTP_PORT', 587))
    smtp_user = os.getenv('SMTP_USERNAME')
    smtp_pass = os.getenv('SMTP_PASSWORD')

    if not smtp_user or not smtp_pass:
        print("אזהרה: פרטי SMTP לא מוגדרים. המייל לא יישלח בפועל.")
        return False

    formatted_body = body_text.replace('\n', '<br>')

    msg = MIMEMultipart('related')
    # 👇 כאן הוספנו את תגית הסלוגן המלאה
    msg['From'] = f"DogOps <{smtp_user}>"
    msg['To'] = to_email
    msg['Subject'] = subject

    # 👇 הסרנו את הרקע הכהה, והגדלנו את התמונה (max-width ל-450)
    html_content = f"""
    <html dir="rtl" lang="he">
    <body style="font-family: Arial, sans-serif; text-align: right; direction: rtl; color: #333; background-color: #f9f9f9; padding: 20px;">
        <div style="background-color: #ffffff; padding: 20px; border-radius: 10px; max-width: 600px; margin: 0 auto; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
            <div style="text-align: center; margin-bottom: 20px;">
                <img src="cid:dog_logo" alt="DogOps Logo" style="width:100%; max-width:100%; height:auto; border-radius:10px; display:block;">
            </div>
            <h2 style="color: #064e3b; text-align: center;">{title}</h2>
            <div style="font-size: 16px; line-height: 1.6; padding: 10px;">
                {formatted_body}
            </div>
            <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e2e8f0; font-size: 12px; color: #94a3b8; text-align: center;">
                נשלח אוטומטית ממערכת האילוף המתקדמת DogOps<br>
                <a href="https://dogops.co" style="color: #3b82f6; text-decoration: none; font-weight: bold; margin-top: 8px; display: inline-block;">www.dogops.co</a>
            </div>
        </div>
    </body>
    </html>
    """
    msg.attach(MIMEText(html_content, 'html', 'utf-8'))
    
    # צירוף התמונה בצורה מוחלטת ובטוחה
    base_dir = os.path.dirname(os.path.abspath(__file__))
    img_path = os.path.join(base_dir, 'frontend', 'assets', 'dogsmailpic.png')
    
    if os.path.exists(img_path):
        try:
            with open(img_path, 'rb') as f:
                img_data = f.read()
            
            # הגדרת סוג הקובץ במפורש (png) קריטית להצגה ב-Gmail
            image = MIMEImage(img_data, _subtype='png', name='dogsmailpic.png')
            image.add_header('Content-ID', '<dog_logo>')
            image.add_header('Content-Disposition', 'inline', filename='dogsmailpic.png')
            msg.attach(image)
        except Exception as img_e:
            print(f"Image attach failed: {img_e}")
    else:
        print(f"CRITICAL ERROR: Image file not found at path: {img_path}")
    
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

# --- הגדרת Gemini AI ---
api_key = os.getenv("GOOGLE_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-pro')

@app.route('/')
def index():
    return "Welcome to the DogOps Behavior Tracker API!"

@app.route('/health')
def health_check():
    return jsonify({"status": "healthy"}), 200

# ==========================================
# Routes: Authentication
# ==========================================
@app.route('/api/check_email', methods=['GET'])
def check_email():
    email = request.args.get('email')
    if not email:
        return jsonify({"error": "No email provided"}), 400
    
    # חיפוש במסד הנתונים אם המייל כבר קיים
    user = User.query.filter_by(email=email).first()
    if user:
        return jsonify({"exists": True}), 200
    return jsonify({"exists": False}), 200

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    first_name = data.get('first_name') # 👈 משיכת שם פרטי
    last_name = data.get('last_name')   # 👈 משיכת שם משפחה
    dog_name = data.get('dog_name')   # 👈 משיכת שם הכלב

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "האימייל כבר קיים במערכת"}), 400

    hashed_pw = generate_password_hash(password)
    # שמירת המשתמש עם השם המלא
    new_user = User(email=email, password_hash=hashed_pw, first_name=first_name, last_name=last_name, auth_provider='local')
    db.session.add(new_user)
    db.session.commit()
    # שמירת הסיסמה הראשונה בהיסטוריה
    history = PasswordHistory(user_id=new_user.id, password_hash=hashed_pw)
    db.session.add(history)
    db.session.commit()

    # 👈 חדש: יוצרים לכלב פרופיל ראשוני מיד בסיום ההרשמה!
    if dog_name:
        new_dog = DogProfile(user_id=new_user.id, name=dog_name)
        db.session.add(new_dog)
        db.session.commit()
    
    body = f"היי {first_name} ו{dog_name}!\n\nברוכים הבאים ל-DogOps, מערכת האילוף והמעקב המובילה בענן.\nשמחים שהצטרפתם לקהילה שלנו!\n\nלנוחיותך, להלן פרטי ההתחברות למערכת:\nשם משתמש: <span dir=\"ltr\">{email}</span>\nסיסמה: <span dir=\"ltr\">{password}</span>\n\nבהצלחה באילוף,\nצוות DogOps 🐾"
    send_dogops_email(email, "ברוכים הבאים ל-DogOps! 🐾", "איזה כיף שהצטרפת!", body)

    # עדכון מד-החום כלפי מעלה כשנוצר כלב חדש
    DOG_PROFILES_GAUGE.inc()

    return jsonify({"message": "המשתמש נוצר בהצלחה!"}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(email=data.get('email')).first()

    if not user or not check_password_hash(user.password_hash, data.get('password')):
        LOGIN_FAILURES_COUNTER.inc() # 👈 סופר כישלון התחברות!
        return jsonify({"error": "אימייל או סיסמה שגויים"}), 401

    # חסימת 90 יום!
    if user.last_password_change and (datetime.utcnow() - user.last_password_change).days >= 90:
        return jsonify({"error": "פג תוקפה של הסיסמה (עברו 90 ימים). חובה עליך לאפס את הסיסמה כעת.", "requires_reset": True}), 403

    # יצירת טוקן שמכיל את ה-ID של המשתמש
    access_token = create_access_token(identity=str(user.id))
    return jsonify({"access_token": access_token}), 200

@app.route('/api/forgot-password', methods=['POST'])
def forgot_password():
    email = request.json.get('email')
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"error": "לא נמצא משתמש עם האימייל הזה"}), 404
    
    code = str(random.randint(100000, 999999))
    user.reset_code = code
    user.reset_code_expiry = datetime.utcnow() + timedelta(minutes=15) # תוקף של 15 דקות
    db.session.commit()
    
    body = f"שלום,\n\nהתקבלה בקשה לאיפוס סיסמה בחשבון ה-DogOps שלך.\nקוד האימות שלך הוא: {code}\n\nהקוד תקף ל-15 דקות.\nאם לא אתה ביקשת לאפס את הסיסמה, אנא התעלם מהודעה זו."
    success = send_dogops_email(user.email, "DogOps - קוד לאיפוס סיסמה", "איפוס סיסמה", body) 

    if not success:
        return jsonify({"error": "שגיאה בשליחת האימייל. בדוק אם השרת מוגדר כראוי."}), 500

    return jsonify({"message": "Code generated and emailed"}), 200

@app.route('/api/reset-password', methods=['POST'])
def reset_password():
    data = request.json
    user = User.query.filter_by(email=data.get('email')).first()
    
    if not user or user.reset_code != data.get('code'):
        return jsonify({"error": "קוד איפוס שגוי"}), 400
        
    if user.reset_code_expiry and datetime.utcnow() > user.reset_code_expiry:
        return jsonify({"error": "קוד האיפוס פג תוקף (עברו 15 דקות). בקש קוד חדש."}), 400

    new_password = data.get('new_password')
    
    # מניעת שימוש ב-3 סיסמאות אחרונות
    history_records = PasswordHistory.query.filter_by(user_id=user.id).order_by(PasswordHistory.created_at.desc()).limit(3).all()
    for record in history_records:
        if check_password_hash(record.password_hash, new_password):
            return jsonify({"error": "מטעמי אבטחה, לא ניתן להשתמש באחת מ-3 הסיסמאות האחרונות שלך."}), 400

    new_hash = generate_password_hash(new_password)
    user.password_hash = new_hash
    user.reset_code = None
    user.reset_code_expiry = None
    user.last_password_change = datetime.utcnow() # איפוס הטיימר של ה-90 יום!
    
    new_history = PasswordHistory(user_id=user.id, password_hash=new_hash)
    db.session.add(new_history)
    db.session.commit()

    return jsonify({"message": "הסיסמה שונתה בהצלחה"}), 200

# ==========================================
# Routes: Account Management
# ==========================================

@app.route('/api/account/email', methods=['PUT'])
@jwt_required()
def change_email():
    current_user_id = get_jwt_identity()
    data = request.json
    user = User.query.get(current_user_id)
    
    if not check_password_hash(user.password_hash, data.get('password')):
        return jsonify({"error": "סיסמה שגויה. פעולה בוטלה."}), 403
        
    new_email = data.get('new_email')
    if User.query.filter_by(email=new_email).first():
        return jsonify({"error": "האימייל כבר קיים במערכת."}), 400
        
    user.email = new_email
    db.session.commit()
    return jsonify({"message": "האימייל עודכן בהצלחה."}), 200

@app.route('/api/account/password', methods=['PUT'])
@jwt_required()
def change_password():
    current_user_id = get_jwt_identity()
    data = request.json
    user = User.query.get(current_user_id)
    
    if not check_password_hash(user.password_hash, data.get('current_password')):
        return jsonify({"error": "סיסמה נוכחית שגויה."}), 403
        
    new_password = data.get('new_password')
    
    # בדיקת היסטוריית סיסמאות
    history_records = PasswordHistory.query.filter_by(user_id=user.id).order_by(PasswordHistory.created_at.desc()).limit(3).all()
    for record in history_records:
        if check_password_hash(record.password_hash, new_password):
            return jsonify({"error": "לא ניתן למחזר את 3 הסיסמאות האחרונות."}), 400
            
    new_hash = generate_password_hash(new_password)
    user.password_hash = new_hash
    user.last_password_change = datetime.utcnow()
    
    new_history = PasswordHistory(user_id=user.id, password_hash=new_hash)
    db.session.add(new_history)
    db.session.commit()
    
    return jsonify({"message": "הסיסמה עודכנה בהצלחה."}), 200

@app.route('/api/account', methods=['DELETE'])
@jwt_required()
def delete_account():
    current_user_id = get_jwt_identity()
    data = request.json
    password = data.get('password')
    user = User.query.get(current_user_id)

    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"error": "סיסמה שגויה. לא ניתן למחוק את החשבון."}), 403

    email_to_send = user.email
    first_name = user.first_name or ""

    # מחיקת התמונה מ-S3 (אם קיימת)
    prefix = f"user_{current_user_id}_profile"
    try:
        response_list = s3_client.list_objects_v2(Bucket=S3_BUCKET, Prefix=prefix)
        if 'Contents' in response_list:
            objects_to_delete = [{'Key': obj['Key']} for obj in response_list['Contents']]
            s3_client.delete_objects(Bucket=S3_BUCKET, Delete={'Objects': objects_to_delete})
    except Exception as e:
        pass # ממשיכים במחיקה גם אם יש שגיאה מול אמזון

    # מחיקת כל המידע מהטבלאות (Cascade ידני כי לא הגדרנו Relationship cascade)
    Todo.query.filter_by(user_id=current_user_id).delete()
    Vaccine.query.filter_by(user_id=current_user_id).delete()
    Summary.query.filter_by(user_id=current_user_id).delete()
    DogProfile.query.filter_by(user_id=current_user_id).delete()
    PasswordHistory.query.filter_by(user_id=current_user_id).delete()

    db.session.delete(user)
    db.session.commit()

    # שליחת אימייל פרידה
    body = f"שלום {first_name},\n\nחשבונך במערכת DogOps וכל המידע המקושר אליו נמחקו בהצלחה לבקשתך.\nנשמח לראותך שוב בעתיד!\n\nצוות DogOps 🐾"
    send_dogops_email(email_to_send, "DogOps - אישור מחיקת חשבון", "פרידה מ-DogOps", body)

    # עדכון מד-החום כלפי מטה כשמוחקים חשבון
    DOG_PROFILES_GAUGE.dec()

    return jsonify({"message": "החשבון נמחק לצמיתות"}), 200


# ==========================================
# Routes: LinkedIn SSO
# ==========================================
LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID", "ה-CLIENT_ID_מלינקדאין")
LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET", "ה-SECRET_מלינקדאין")
LINKEDIN_REDIRECT_URI = os.getenv("LINKEDIN_REDIRECT_URI", "http://localhost:8080/api/auth/linkedin/callback")

@app.route('/api/auth/linkedin/login')
def linkedin_login():
    # מפנה את המשתמש לדף ההתחברות הרשמי של לינקדאין
    linkedin_auth_url = (
        f"https://www.linkedin.com/oauth/v2/authorization?"
        f"response_type=code&"
        f"client_id={LINKEDIN_CLIENT_ID}&"
        f"redirect_uri={LINKEDIN_REDIRECT_URI}&"
        f"scope=openid%20profile%20email"
    )
    return redirect(linkedin_auth_url)

@app.route('/api/auth/linkedin/callback')
def linkedin_callback():
    code = request.args.get('code')
    if not code:
        return jsonify({"error": "לא התקבל קוד אימות מלינקדאין"}), 400

    # המרת הקוד לטוקן גישה מול השרתים של לינקדאין
    token_url = "https://www.linkedin.com/oauth/v2/accessToken"
    token_data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": LINKEDIN_REDIRECT_URI,
        "client_id": LINKEDIN_CLIENT_ID,
        "client_secret": LINKEDIN_CLIENT_SECRET
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    token_r = requests.post(token_url, data=token_data, headers=headers)
    token_json = token_r.json()
    access_token = token_json.get("access_token")

    if not access_token:
        return jsonify({"error": "שגיאה במשיכת טוקן מלינקדאין", "details": token_json}), 400

    # משיכת פרופיל המשתמש דרך פרוטוקול OpenID של לינקדאין
    userinfo_url = "https://api.linkedin.com/v2/userinfo"
    userinfo_headers = {"Authorization": f"Bearer {access_token}"}
    userinfo_r = requests.get(userinfo_url, headers=userinfo_headers)
    user_info = userinfo_r.json()

    email = user_info.get("email")
    if not email:
        return jsonify({"error": "לא ניתן לקרוא את כתובת האימייל מהפרופיל"}), 400

    first_name = user_info.get("given_name", "")
    last_name = user_info.get("family_name", "")

    # לוגיקת התחברות או יצירת משתמש במערכת שלנו
    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(email=email, password_hash="LINKEDIN_SSO_USER", first_name=first_name, last_name=last_name)
        db.session.add(user)
        db.session.commit()
        
        # יצירת פרופיל כלב ריק למשתמש חדש
        new_dog = DogProfile(user_id=user.id, name="כלב חדש")
        db.session.add(new_dog)
        db.session.commit()

    # יצירת הטוקן הפנימי של המערכת שלנו והפניה חזרה לפרונט-אנד
    jwt_token = create_access_token(identity=str(user.id))
    return redirect(f"/?token={jwt_token}")


# ==========================================
# Routes: Microsoft SSO
# ==========================================
MS_CLIENT_ID = os.getenv("MICROSOFT_CLIENT_ID", "ה-CLIENT_ID_ממיקרוסופט")
MS_CLIENT_SECRET = os.getenv("MICROSOFT_CLIENT_SECRET", "ה-SECRET_ממיקרוסופט")
MS_REDIRECT_URI = os.getenv("MICROSOFT_REDIRECT_URI", "http://localhost:8080/api/auth/microsoft/callback")

@app.route('/api/auth/microsoft/login')
def microsoft_login():
    # מפנה את המשתמש לדף ההתחברות הרשמי של מיקרוסופט
    ms_auth_url = (
        f"https://login.microsoftonline.com/common/oauth2/v2.0/authorize?"
        f"client_id={MS_CLIENT_ID}&"
        f"response_type=code&"
        f"redirect_uri={MS_REDIRECT_URI}&"
        f"response_mode=query&"
        f"scope=openid%20email%20profile%20User.Read"
    )
    return redirect(ms_auth_url)

@app.route('/api/auth/microsoft/callback')
def microsoft_callback():
    code = request.args.get('code')
    if not code:
        return jsonify({"error": "לא התקבל קוד אימות ממיקרוסופט"}), 400

    # המרת הקוד לטוקן גישה מול השרתים של מיקרוסופט
    token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    token_data = {
        "client_id": MS_CLIENT_ID,
        "client_secret": MS_CLIENT_SECRET,
        "code": code,
        "redirect_uri": MS_REDIRECT_URI,
        "grant_type": "authorization_code"
    }
    token_r = requests.post(token_url, data=token_data)
    token_json = token_r.json()
    access_token = token_json.get("access_token")

    if not access_token:
        return jsonify({"error": "שגיאה במשיכת טוקן הגישה ממיקרוסופט"}), 400

    # משיכת פרופיל המשתמש
    graph_url = "https://graph.microsoft.com/v1.0/me"
    headers = {"Authorization": f"Bearer {access_token}"}
    graph_r = requests.get(graph_url, headers=headers)
    user_info = graph_r.json()

    # מיקרוסופט יכולה להחזיר את המייל תחת 'mail' או תחת 'userPrincipalName'
    email = user_info.get("mail") or user_info.get("userPrincipalName")
    if not email:
        return jsonify({"error": "לא ניתן לקרוא את כתובת האימייל מהפרופיל"}), 400

    first_name = user_info.get("givenName", "")
    last_name = user_info.get("surname", "")

    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(email=email, password_hash="MICROSOFT_SSO_USER", first_name=first_name, last_name=last_name, auth_provider="microsoft")
        db.session.add(user)
        db.session.flush()
        
        new_dog = DogProfile(user_id=user.id, name="כלב חדש")
        db.session.add(new_dog)
        db.session.commit()

    # יצירת הטוקן הפנימי של המערכת שלנו
    jwt_token = create_access_token(identity=str(user.id))
    
    # הפניה חזרה לעמוד הראשי של האפליקציה יחד עם הטוקן ב-URL כדי שהפרונט-אנד יוכל לשמור אותו
    return redirect(f"/?token={jwt_token}")



@app.route('/api/auth/google', methods=['POST'])
def google_sso():
    token = request.json.get('token')
    if not token:
        return jsonify({"error": "No token provided"}), 400
        
    try:
        # 1. אימות הטוקן מול השרתים של גוגל
        idinfo = id_token.verify_oauth2_token(token, google_requests.Request(), GOOGLE_CLIENT_ID)
        
        # 2. שליפת האימייל מהטוקן המאומת
        email = idinfo.get('email')
        first_name = idinfo.get('given_name', '')
        last_name = idinfo.get('family_name', '')
        
        # 3. בדיקה אם המשתמש קיים ב-DB שלך
        user = User.query.filter_by(email=email).first()
        if not user:
            # אם הוא לא קיים, ניצור אותו אוטומטית
            user = User(email=email, password_hash="GOOGLE_SSO_USER", first_name=first_name, last_name=last_name, auth_provider="google")
            db.session.add(user)
            db.session.flush()
            
            new_dog = DogProfile(user_id=user.id, name="כלב חדש")
            db.session.add(new_dog)
            db.session.commit()
            
        # 4. הנפקת ה-JWT של המערכת שלך כדי ששאר הראוטים יעבדו!
        access_token = create_access_token(identity=str(user.id))
        return jsonify(access_token=access_token), 200
        
    except ValueError:
        # טוקן שגוי, פג תוקף או ניסיון זיוף
        return jsonify({"error": "Invalid or expired Google token"}), 401

# ==========================================
# Routes: Dog Profile & S3 Image Upload
# ==========================================
@app.route('/api/profile', methods=['GET', 'PUT'])
@jwt_required()
def dog_profile():
    current_user_id = get_jwt_identity()
    profile = DogProfile.query.filter_by(user_id=current_user_id).first()
    
    if request.method == 'GET':
        user = User.query.filter_by(id=current_user_id).first()
        if not profile:
            return jsonify({
                "owner_first_name": user.first_name if user else "",
                "owner_last_name": user.last_name if user else ""
            }), 200
        return jsonify({
            "owner_first_name": user.first_name if user else "",
            "owner_last_name": user.last_name if user else "",
            "name": profile.name, "breed": profile.breed, "city": profile.city,
            "dob": profile.dob, "gender": profile.gender, "status": profile.status,
            "weight": profile.weight, "chip": profile.chip, "allergies": profile.allergies,
            "image_url": profile.image_url
        }), 200
        
    if request.method == 'PUT':
        data = request.json
        if not profile:
            profile = DogProfile(user_id=current_user_id)
            db.session.add(profile)
            
        user = User.query.filter_by(id=current_user_id).first()
        if user:
            if 'owner_first_name' in data:
                user.first_name = data['owner_first_name']
            if 'owner_last_name' in data:
                user.last_name = data['owner_last_name']
        
        was_new = (profile.name == "כלב חדש")
        
        profile.name = data.get('name', profile.name)
        profile.breed = data.get('breed', profile.breed)
        profile.city = data.get('city', profile.city)
        profile.dob = data.get('dob', profile.dob)
        profile.gender = data.get('gender', profile.gender)
        profile.status = data.get('status', profile.status)
        profile.weight = data.get('weight', profile.weight)
        profile.chip = data.get('chip', profile.chip)
        profile.allergies = data.get('allergies', profile.allergies)
        
        db.session.commit()
        
        if was_new and user and user.auth_provider in ['google', 'microsoft', 'linkedin']:
            provider_name = user.auth_provider.capitalize()
            body = f"היי {user.first_name} ו{profile.name}!\n\nברוכים הבאים ל-DogOps, מערכת האילוף והמעקב המובילה בענן.\nשמחים שהצטרפתם לקהילה שלנו!\n\nהתחברתם בהצלחה באמצעות חשבון ה-{provider_name} שלכם.\n\nבהצלחה באילוף,\nצוות DogOps 🐾"
            send_dogops_email(user.email, "ברוכים הבאים ל-DogOps! 🐾", "איזה כיף שהצטרפת!", body)
            
        return jsonify({"message": "Profile updated successfully"}), 200

@app.route('/api/profile/image', methods=['POST'])
@jwt_required()
def upload_image():
    current_user_id = get_jwt_identity()
    if 'image' not in request.files:
        return jsonify({"error": "No image provided"}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # יצירת שם קובץ ייחודי וקצר כדי למנוע דריסות ב-S3
    ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'jpg'
    prefix = f"user_{current_user_id}_profile"
    filename = f"{prefix}.{ext}" # הסרנו את ה-UUID!

    try:
        # 1. חיפוש ומחיקה של תמונות קודמות של אותו משתמש כדי למנוע הצטברות זבל ב-S3
        response_list = s3_client.list_objects_v2(Bucket=S3_BUCKET, Prefix=prefix)
        if 'Contents' in response_list:
            objects_to_delete = [{'Key': obj['Key']} for obj in response_list['Contents']]
            s3_client.delete_objects(Bucket=S3_BUCKET, Delete={'Objects': objects_to_delete})
            
        # 2. העלאת התמונה החדשה לאמזון
        with S3_UPLOAD_LATENCY_HISTOGRAM.time(): # 👈 מודד כמה זמן זה לוקח!
            s3_client.upload_fileobj(
                file,
                S3_BUCKET,
                filename,
                ExtraArgs={'ContentType': file.content_type}
            )
        region = os.getenv('AWS_REGION', 'us-east-1')
        image_url = f"https://{S3_BUCKET}.s3.{region}.amazonaws.com/{filename}"
        
        profile = DogProfile.query.filter_by(user_id=current_user_id).first()
        if not profile:
            profile = DogProfile(user_id=current_user_id)
            db.session.add(profile)
        profile.image_url = image_url
        db.session.commit()
        
        return jsonify({"image_url": image_url}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==========================================
# Routes: Weather API (Trainer Optimized)
# ==========================================
@app.route('/api/weather', methods=['GET'])
@jwt_required()
def get_weather():
    lat = request.args.get('lat')
    lon = request.args.get('lon')
    
    if not lat or not lon:
        return jsonify({"error": "Missing coordinates"}), 400
        
    try:
        with WEATHER_API_LATENCY_HISTOGRAM.time(): # 👈 מודד עיכובי רשת
            # פנייה ישירה ל-Open-Meteo עם המיקום החי, כולל לחות ומהירות רוח החשובים לאימון
            weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&hourly=relative_humidity_2m"
            weather_res = requests.get(weather_url, timeout=5).json()
        
        current = weather_res['current_weather']
        temp = round(current['temperature'])
        code = current['weathercode']
        wind = current['windspeed']
        
        # מפות קודים ואימוג'ים
        weather_map = {
            0: ("שמיים בהירים נוחים לאימון", "☀️"),
            1: ("מעונן חלקית", "🌤️"),
            2: ("מעונן עדין", "⛅"),
            3: ("מעונן לגמרי", "☁️"),
            61: ("גשם קל - מומלץ מחסה", "🌧️"),
            63: ("גשם שוטף - העבר אימון למקום מקורה", "🌧️"),
            95: ("סופת רעמים - סכנה בשטח פתוח", "🌩️")
        }
        desc, emoji = weather_map.get(code, ("מזג אוויר משתנה", "🌡️"))
        
        # לוגיקה חכמה למאלף הכלבים (התראות בטיחות לכלבים)
        trainer_tip = "🟢 תנאים מעולים לעבודה בשטח!"
        if temp >= 30:
            trainer_tip = "🚨 אזהרת עומס חום! סכנת כוויות בכפות הרגליים מהאספלט ומכת חום לכלב. קחו הפסקות מים מרובות."
        elif temp <= 10:
            trainer_tip = "❄️ קר בחוץ. כלבים קטנים או בעלי שיער קצר צריכים תנועה מתמדת כדי לא לקפוא."
        elif code in [61, 63, 80, 95]:
            trainer_tip = "🌧️ גשם בשטח. מומלץ להתמקד בתוך מבנה או לעבוד על פקודות משמעת בבית הלקוח."

        return jsonify({
            "temp": temp,
            "description": desc,
            "emoji": emoji,
            "wind_speed": wind,
            "tip": trainer_tip
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==========================================
# Routes: AI Assistant
# ==========================================
@app.route('/api/chat', methods=['POST'])
@jwt_required()
@limiter.limit("5 per minute") # 👈 שורת ההגנה החדשה
def chat_with_ai():
    if not api_key:
        return jsonify({"response": "מפתח ה-API של ה-AI לא הוגדר בשרת."}), 500
    
    data = request.json
    user_message = data.get('message', '')
    
    try:
        valid_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        if not valid_models:
            return jsonify({"error": "המפתח תקין, אך לא נמצאו מודלי טקסט שפתוחים עבורו."}), 500
            
        model = genai.GenerativeModel(valid_models[0])
        prompt = f"אתה מאלף כלבים מומחה. המשתמש שאל: {user_message}. ענה בצורה תמציתית ומקצועית."
        
        # 👇 תפיסת זמן התגובה לתוך ההיסטוגרמה!
        with AI_LATENCY_HISTOGRAM.time():
            response = model.generate_content(prompt)

        return jsonify({"response": response.text}), 200
    except Exception as e:
        return jsonify({"error": f"שגיאת תקשורת: {str(e)}"}), 500

# ==========================================
# Routes: Todos
# ==========================================
@app.route('/api/todos', methods=['GET'])
@jwt_required()
def get_todos():
    current_user_id = get_jwt_identity()
    all_todos = Todo.query.filter_by(user_id=current_user_id).all()
    result = [{
        "id": t.id, "title": t.title, "created_at": t.created_at,
        "priority": t.priority, "due_date": t.due_date,
        "location": t.location, "gps_link": t.gps_link
    } for t in all_todos]
    return jsonify(result), 200

@app.route('/api/todos', methods=['POST'])
@jwt_required()
def create_todo():
    current_user_id = get_jwt_identity()
    data = request.json
    new_todo = Todo(
        user_id=current_user_id,
        title=data['title'], priority=data.get('priority'),
        due_date=data.get('due_date'), location=data.get('location'),
        gps_link=data.get('gps_link')
    )
    db.session.add(new_todo)
    db.session.commit()
    # קידום המונה עם תווית חכמה לפי סוג האירוע
    if "🔴" in new_todo.title:
        DOG_EVENTS_COUNTER.labels(event_type='oops').inc()
    elif "🟢" in new_todo.title:
        DOG_EVENTS_COUNTER.labels(event_type='good').inc()
    return jsonify({"id": new_todo.id, "title": new_todo.title, "created_at": new_todo.created_at}), 201

@app.route('/api/todos/<int:todo_id>', methods=['PUT'])
@jwt_required()
def update_todo(todo_id):
    current_user_id = get_jwt_identity()
    todo = Todo.query.filter_by(id=todo_id, user_id=current_user_id).first()
    if not todo:
        return jsonify({"error": "Not found"}), 404
        
    data = request.json
    todo.title = data.get('title', todo.title)
    todo.priority = data.get('priority', todo.priority)
    todo.due_date = data.get('due_date', todo.due_date)
    todo.location = data.get('location', todo.location)
    db.session.commit()
    return jsonify({"message": "Updated successfully"}), 200

@app.route('/api/todos/<int:todo_id>', methods=['DELETE'])
@jwt_required()
def delete_todo(todo_id):
    current_user_id = get_jwt_identity()
    todo = Todo.query.filter_by(id=todo_id, user_id=current_user_id).first()
    if not todo:
        return jsonify({"error": "Not found"}), 404
    db.session.delete(todo)
    db.session.commit()
    return jsonify({"result": True}), 200

# ==========================================
# Routes: Vaccines
# ==========================================
@app.route('/api/vaccines', methods=['GET'])
@jwt_required()
def get_vaccines():
    current_user_id = get_jwt_identity()
    all_vaccines = Vaccine.query.filter_by(user_id=current_user_id).all()
    result = [{"id": v.id, "type": v.type, "given_date": v.given_date, "expiry_date": v.expiry_date} for v in all_vaccines]
    return jsonify(result), 200

@app.route('/api/vaccines', methods=['POST'])
@jwt_required()
def create_vaccine():
    current_user_id = get_jwt_identity()
    data = request.json
    expiry_date = data.get('expiry_date')
    if not expiry_date:
        given_date_obj = datetime.strptime(data['given_date'], '%Y-%m-%d')
        expiry_date = (given_date_obj.replace(year=given_date_obj.year + 1)).strftime('%Y-%m-%d')

    new_vaccine = Vaccine(
        user_id=current_user_id, type=data['type'],
        given_date=data['given_date'], expiry_date=expiry_date
    )
    db.session.add(new_vaccine)
    db.session.commit()
    return jsonify({"id": new_vaccine.id, "type": new_vaccine.type}), 201

@app.route('/api/vaccines/<int:vaccine_id>', methods=['DELETE'])
@jwt_required()
def delete_vaccine(vaccine_id):
    current_user_id = get_jwt_identity()
    vaccine = Vaccine.query.filter_by(id=vaccine_id, user_id=current_user_id).first()
    if not vaccine:
        return jsonify({"error": "Not found"}), 404
    db.session.delete(vaccine)
    db.session.commit()
    return jsonify({"result": True}), 200

# ==========================================
# Routes: Daily Summaries
# ==========================================
@app.route('/api/summaries', methods=['GET'])
@jwt_required()
def get_summaries():
    current_user_id = get_jwt_identity()
    all_summaries = Summary.query.filter_by(user_id=current_user_id).all()
    result = [{"id": s.id, "date": s.date, "text": s.text, "is_auto": s.is_auto} for s in all_summaries]
    return jsonify(result), 200

@app.route('/api/summaries', methods=['POST'])
@jwt_required()
def create_summary():
    current_user_id = get_jwt_identity()
    data = request.json
    existing = Summary.query.filter_by(date=data['date'], user_id=current_user_id).first()
    if existing:
        db.session.delete(existing)
        
    new_summary = Summary(
        user_id=current_user_id, date=data['date'],
        text=data['text'], is_auto=data.get('is_auto', False)
    )
    db.session.add(new_summary)
    db.session.commit()
    return jsonify({"id": new_summary.id, "date": new_summary.date}), 201

@app.route('/api/summaries/generate', methods=['POST'])
@jwt_required()
def generate_summary():
    if not api_key:
        return jsonify({"error": "API Key missing"}), 500
    
    events = request.json.get('events', [])
    if not events:
        return jsonify({"error": "No events provided"}), 400
        
    events_text = "\n".join([f"- {e}" for e in events])
    prompt = f"אתה מאלף כלבים מקצועי. להלן דיווחי היום:\n{events_text}\nכתוב סיכום יומי מקצועי וקצר (עד 3 משפטים)."
    
    try:
        valid_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        model = genai.GenerativeModel(valid_models[0])
        response = model.generate_content(prompt)
        return jsonify({"summary": response.text}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)