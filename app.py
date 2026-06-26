import os
import google.generativeai as genai
from flask import Flask, jsonify, request
from datetime import datetime
import boto3
import uuid

# ייבוא ספריות ה-DB והאבטחה
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

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
    first_name = db.Column(db.String(50), nullable=True) # 👈 הוחלף מ-full_name
    last_name = db.Column(db.String(50), nullable=True)  # 👈 התווסף

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
    new_user = User(email=email, password_hash=hashed_pw, first_name=first_name, last_name=last_name)
    db.session.add(new_user)
    db.session.commit()

    # 👈 חדש: יוצרים לכלב פרופיל ראשוני מיד בסיום ההרשמה!
    if dog_name:
        new_dog = DogProfile(user_id=new_user.id, name=dog_name)
        db.session.add(new_dog)
        db.session.commit()

    return jsonify({"message": "המשתמש נוצר בהצלחה!"}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(email=data.get('email')).first()

    if not user or not check_password_hash(user.password_hash, data.get('password')):
        return jsonify({"error": "אימייל או סיסמה שגויים"}), 401

    # יצירת טוקן שמכיל את ה-ID של המשתמש
    access_token = create_access_token(identity=str(user.id))
    return jsonify({"access_token": access_token}), 200

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
    filename = f"user_{current_user_id}_{uuid.uuid4().hex[:8]}.{ext}"

    try:
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
# Routes: AI Assistant
# ==========================================
@app.route('/api/chat', methods=['POST'])
@jwt_required()
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