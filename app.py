## app.py
## Flask server for the HAAS NWEA Data Agent.
## Serves the terminal UI and routes chat messages to queryagent.

from flask import Flask, request, jsonify, render_template
import queryagent

app = Flask(__name__)

# Conversation history persists for the lifetime of the server process.
# Each entry is a user/assistant message dict; tool call internals are
# tracked inside queryagent.run() and not stored here.
conversation_history = []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message', '').strip()
    if not user_message:
        return jsonify({'error': 'No message provided.'}), 400
    try:
        response = queryagent.run(user_message, conversation_history)
        return jsonify({'response': response})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
