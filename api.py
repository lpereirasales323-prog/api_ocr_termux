from flask import Flask, request, jsonify
from PIL import Image
import pytesseract
import os

app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return "API funcionando!", 200

@app.route("/ocr", methods=["POST"])
def ocr():
    if "image" not in request.files:
        return jsonify({"error": "Imagem não enviada"}), 400

    img = request.files["image"]

    img_path = "temp.png"
    img.save(img_path)

    try:
        texto = pytesseract.image_to_string(Image.open(img_path))
        os.remove(img_path)
        return jsonify({"texto": texto})
    except:
        return jsonify({"error": "Erro no OCR"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)

