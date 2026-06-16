import os
import google.generativeai as genai
from flask import Flask, jsonify, request
from datetime import datetime

# ייבוא ספריות ה-DB והאבטחה
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager

app = Flask(__name__)

# הגדרות בסיס נתונים (ייקראו אוטומטית מהסביבה בקוברנטיס)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/dogops')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'super-secret-key-change-in-prod')

# אתחול הכלים
db = SQLAlchemy(app)
jwt = JWTManager(app)

# ==========================================
# Database Models (טבלאות בסיס הנתונים)
# ==========================================
class Todo(db.Model):
    __tablename__ = 'todos'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.String(50), default=lambda: datetime.now().isoformat())
    priority = db.Column(db.String(50), nullable=True)
    due_date = db.Column(db.String(50), nullable=True)
    location = db.Column(db.String(200), nullable=True)
    gps_link = db.Column(db.String(500), nullable=True)

class Vaccine(db.Model):
    __tablename__ = 'vaccines'
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(100), nullable=False)
    given_date = db.Column(db.String(50), nullable=False)
    expiry_date = db.Column(db.String(50), nullable=False)

class Summary(db.Model):
    __tablename__ = 'summaries'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(50), nullable=False, unique=True)
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
# Routes: AI Assistant
# ==========================================
@app.route('/api/chat', methods=['POST'])
def chat_with_ai():
    if not api_key:
        return jsonify({"response": "מפתח ה-API של ה-AI לא הוגדר בשרת."}), 500
    
    data = request.json
    user_message = data.get('message', '')
    
    try:
        valid_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        if not valid_models:
            return jsonify({"error": "המפתח תקין, אך לא נמצאו מודלי טקסט שפתוחים עבורו."}), 500
            
        chosen_model = valid_models[0]
        model = genai.GenerativeModel(chosen_model)
        
        prompt = f"אתה מאלף כלבים מומחה. המשתמש שאל: {user_message}. ענה בצורה תמציתית ומקצועית."
        response = model.generate_content(prompt)
        
        return jsonify({"response": response.text}), 200
    except Exception as e:
        return jsonify({"error": f"שגיאת תקשורת עם גוגל: {str(e)}"}), 500

# ==========================================
# Routes: Todos (עבודה מול DB)
# ==========================================
@app.route('/api/todos', methods=['GET'])
def get_todos():
    all_todos = Todo.query.all()
    result = []
    for t in all_todos:
        result.append({
            "id": t.id,
            "title": t.title,
            "created_at": t.created_at,
            "priority": t.priority,
            "due_date": t.due_date,
            "location": t.location,
            "gps_link": t.gps_link
        })
    return jsonify(result), 200

@app.route('/api/todos', methods=['POST'])
def create_todo():
    data = request.json
    new_todo = Todo(
        title=data['title'],
        priority=data.get('priority'),
        due_date=data.get('due_date'),
        location=data.get('location'),
        gps_link=data.get('gps_link')
    )
    db.session.add(new_todo)
    db.session.commit()
    
    return jsonify({
        "id": new_todo.id,
        "title": new_todo.title,
        "created_at": new_todo.created_at
    }), 201

@app.route('/api/todos/<int:todo_id>', methods=['PUT'])
def update_todo(todo_id):
    todo = Todo.query.get(todo_id)
    if not todo:
        return jsonify({"error": "Event not found"}), 404
        
    data = request.json
    todo.title = data.get('title', todo.title)
    todo.priority = data.get('priority', todo.priority)
    todo.due_date = data.get('due_date', todo.due_date)
    todo.location = data.get('location', todo.location)
    
    db.session.commit()
    return jsonify({"message": "Updated successfully"}), 200

@app.route('/api/todos/<int:todo_id>', methods=['DELETE'])
def delete_todo(todo_id):
    todo = Todo.query.get(todo_id)
    if not todo:
        return jsonify({"error": "Not found"}), 404
    db.session.delete(todo)
    db.session.commit()
    return jsonify({"result": True}), 200

# ==========================================
# Routes: Vaccines (עבודה מול DB)
# ==========================================
@app.route('/api/vaccines', methods=['GET'])
def get_vaccines():
    all_vaccines = Vaccine.query.all()
    result = []
    for v in all_vaccines:
        result.append({
            "id": v.id,
            "type": v.type,
            "given_date": v.given_date,
            "expiry_date": v.expiry_date
        })
    return jsonify(result), 200

@app.route('/api/vaccines', methods=['POST'])
def create_vaccine():
    data = request.json
    expiry_date = data.get('expiry_date')
    if not expiry_date:
        given_date_obj = datetime.strptime(data['given_date'], '%Y-%m-%d')
        expiry_date = (given_date_obj.replace(year=given_date_obj.year + 1)).strftime('%Y-%m-%d')

    new_vaccine = Vaccine(
        type=data['type'],
        given_date=data['given_date'],
        expiry_date=expiry_date
    )
    db.session.add(new_vaccine)
    db.session.commit()
    return jsonify({"id": new_vaccine.id, "type": new_vaccine.type}), 201

@app.route('/api/vaccines/<int:vaccine_id>', methods=['DELETE'])
def delete_vaccine(vaccine_id):
    vaccine = Vaccine.query.get(vaccine_id)
    if not vaccine:
        return jsonify({"error": "Not found"}), 404
    db.session.delete(vaccine)
    db.session.commit()
    return jsonify({"result": True}), 200

# ==========================================
# Routes: Daily Summaries (עבודה מול DB)
# ==========================================
@app.route('/api/summaries', methods=['GET'])
def get_summaries():
    all_summaries = Summary.query.all()
    result = []
    for s in all_summaries:
        result.append({
            "id": s.id,
            "date": s.date,
            "text": s.text,
            "is_auto": s.is_auto
        })
    return jsonify(result), 200

@app.route('/api/summaries', methods=['POST'])
def create_summary():
    data = request.json
    
    # מחיקת סיכום קודם אם קיים לאותו תאריך (כדי למנוע כפילויות)
    existing = Summary.query.filter_by(date=data['date']).first()
    if existing:
        db.session.delete(existing)
        
    new_summary = Summary(
        date=data['date'],
        text=data['text'],
        is_auto=data.get('is_auto', False)
    )
    db.session.add(new_summary)
    db.session.commit()
    return jsonify({"id": new_summary.id, "date": new_summary.date}), 201

@app.route('/api/summaries/generate', methods=['POST'])
def generate_summary():
    if not api_key:
        return jsonify({"error": "API Key missing"}), 500
    
    events = request.json.get('events', [])
    if not events:
        return jsonify({"error": "No events provided"}), 400
        
    events_text = "\n".join([f"- {e}" for e in events])
    prompt = f"אתה מאלף כלבים מקצועי. להלן רשימת הדיווחים שנאספו היום על הכלב. כתוב סיכום יומי מקצועי, קצר ותמציתי (עד 3 משפטים) שמשקף את ההתנהגות שלו היום. \nהדיווחים:\n{events_text}"
    
    try:
        valid_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        model = genai.GenerativeModel(valid_models[0])
        response = model.generate_content(prompt)
        return jsonify({"summary": response.text}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)