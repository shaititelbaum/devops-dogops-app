from flask import Flask, jsonify, request
from datetime import datetime

app = Flask(__name__)

todos = [
    {
        "id": 1, 
        "title": "🟢 הכלב הגיב מצוין לפקודת 'אלי'", 
        "created_at": "2026-06-10T14:02:00",
        "priority": None,
        "due_date": None,
        "location": "גינת הכלבים",
        "gps_link": None
    },
    {
        "id": 2, 
        "title": "🔴 אופס... משך חזק ברצועה בגלל חתול", 
        "created_at": "2026-06-10T14:05:00",
        "priority": "חשוב",
        "due_date": "2026-06-15",
        "location": "רחוב הרצל",
        "gps_link": "https://www.google.com/maps?q=31.8903,34.8113"
    }
]

@app.route('/')
def index():
    return "Welcome to the DogOps Behavior Tracker API!"

@app.route('/health')
def health_check():
    return jsonify({"status": "healthy"}), 200

@app.route('/api/todos', methods=['GET'])
def get_todos():
    return jsonify(todos), 200

@app.route('/api/todos', methods=['POST'])
def create_todo():
    current_time = datetime.now().isoformat()
    data = request.json
    
    new_todo = {
        "id": len(todos) + 1,
        "title": data['title'],
        "created_at": current_time,
        "priority": data.get('priority'),
        "due_date": data.get('due_date'),
        "location": data.get('location'),
        "gps_link": data.get('gps_link') # הוספת הקישור מהפרונטאנד
    }
    todos.append(new_todo)
    return jsonify(new_todo), 201

@app.route('/api/todos/<int:todo_id>', methods=['PUT'])
def update_todo(todo_id):
    global todos
    data = request.json
    for todo in todos:
        if todo['id'] == todo_id:
            todo['title'] = data.get('title', todo['title'])
            todo['priority'] = data.get('priority', todo['priority'])
            todo['due_date'] = data.get('due_date', todo['due_date'])
            todo['location'] = data.get('location', todo['location'])
            return jsonify(todo), 200
    return jsonify({"error": "Event not found"}), 404

@app.route('/api/todos/<int:todo_id>', methods=['DELETE'])
def delete_todo(todo_id):
    global todos
    todos = [t for t in todos if t['id'] != todo_id]
    return jsonify({"result": True}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)