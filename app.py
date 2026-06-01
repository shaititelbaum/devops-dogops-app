from flask import Flask, jsonify, request

app = Flask(__name__)

todos = [
    {"id": 1, "title": "Learn DevOps fundamentals"},
    {"id": 2, "title": "Build a CI/CD Pipeline"}
]

@app.route('/')
def index():
    return "Welcome to the DevOps Todo API!"

@app.route('/health')
def health_check():
    return jsonify({"status": "healthy"}), 200

@app.route('/api/todos', methods=['GET'])
def get_todos():
    return jsonify(todos), 200

@app.route('/api/todos', methods=['POST'])
def create_todo():
    new_todo = {
        "id": len(todos) + 1,
        "title": request.json['title']
    }
    todos.append(new_todo)
    return jsonify(new_todo), 201

@app.route('/api/todos/<int:todo_id>', methods=['DELETE'])
def delete_todo(todo_id):
    global todos
    todos = [t for t in todos if t['id'] != todo_id]
    return jsonify({"result": True}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)