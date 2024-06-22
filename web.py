from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/healthcheck', methods=['GET'])
def healthcheck():
    return jsonify(status='ok'), 200

def run_flask():
    app.run(port=5000)