from flask import Flask, request, jsonify
from ocr import extract_text
from element_detector import find_element

app = Flask(__name__)

@app.route('/ocr', methods=['POST'])
def handle_ocr():
    data = request.json
    if not data or 'image_base64' not in data:
        return jsonify({"error": "Missing image_base64"}), 400
    
    result = extract_text(data['image_base64'])
    return jsonify(result)

@app.route('/find', methods=['POST'])
def handle_find():
    data = request.json
    if not data or 'image_base64' not in data or 'description' not in data:
        return jsonify({"error": "Missing image_base64 or description"}), 400
    
    result = find_element(data['image_base64'], data['description'])
    return jsonify(result)

@app.route('/health', methods=['GET'])
def handle_health():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=7890)
