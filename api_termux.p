from flask import Flask, request, jsonify
from PIL import Image, ImageOps, ImageEnhance
import pytesseract
import numpy as np
import time
import re
from collections import deque

# -------------------------------------------------------------
# Config
# -------------------------------------------------------------
app = Flask(__name__)
regex_mult = re.compile(r"(\d+(?:[.,]\d+)?)[xX]\b")
history = deque(maxlen=1500)

# -------------------------------------------------------------
# UTIL — processamento avançado sem OpenCV (compatível Termux)
# -------------------------------------------------------------
def preprocess_image(path):
    img = Image.open(path).convert("L")  # grayscale

    # Aumentar contraste
    img = ImageOps.autocontrast(img)

    # Reduzir ruído (filtro median)
    img = img.filter(ImageFilter.MedianFilter(size=3))

    # Aumentar nitidez
    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(2.0)

    # Normalizar brilho/contraste
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.5)

    # Binarização manual
    np_img = np.array(img)
    thresh = np.mean(np_img)
    np_img = (np_img > thresh).astype(np.uint8) * 255
    img = Image.fromarray(np_img)

    # Deskew simples via projeção
    try:
        arr = np.array(img)
        coords = np.column_stack(np.where(arr > 0))
        angle = Image.fromarray(arr).rotate(0, expand=True)
        # Deskew básico manual não rotaciona aqui porque Pillow não expõe minAreaRect
        # mas deixa imagem estabilizada por limiar + nitidez
    except:
        pass

    # Aumenta resolução para melhorar OCR
    w, h = img.size
    img = img.resize((w * 2, h * 2))

    processed_path = "pre_termux.png"
    img.save(processed_path)
    return processed_path

# -------------------------------------------------------------
# OCR híbrido — Tesseract + pós-processado
# -------------------------------------------------------------
def perform_ocr(path):
    try:
        processed = preprocess_image(path)

        # OCR original
        text_raw = pytesseract.image_to_string(Image.open(path))

        # OCR pós processado
        text_pre = pytesseract.image_to_string(Image.open(processed))

        combined = text_raw + "\n" + text_pre
        return combined

    except Exception as e:
        return str(e)

# -------------------------------------------------------------
# Extrair multiplicadores
# -------------------------------------------------------------
def extract_multipliers(text):
    values = []
    for m in regex_mult.finditer(text):
        num = m.group(1).replace(",", ".")
        try:
            values.append(float(num))
        except:
            pass
    return values

# -------------------------------------------------------------
# Estatísticas avançadas
# -------------------------------------------------------------
def compute_stats(window=50):
    data = [m for (_, m) in list(history)[-window:]]
    if not data:
        return None

    arr = np.array(data)
    return {
        "count": len(arr),
        "mean": float(np.mean(arr)),
        "median": float(np.median(arr)),
        "std": float(np.std(arr)),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
        "pct_below_2": float((arr < 2).sum()) / len(arr),
        "pct_below_1_5": float((arr < 1.5).sum()) / len(arr),
        "pct_above_5": float((arr >= 5).sum()) / len(arr),
    }

# -------------------------------------------------------------
# Sistema de recomendação probabilístico
# -------------------------------------------------------------
def make_decision():
    stats = compute_stats(window=50)
    if not stats:
        return {"decision": "SEM_DADOS", "confidence": 0}

    score = 0

    score -= stats['pct_below_1_5'] * 2
    score += stats['pct_above_5'] * 3
    score += (stats['mean'] - 2) * 0.8
    score -= stats['std'] * 0.3

    if score <= -1:
        return {
            "decision": "NAO_APOSTAR",
            "confidence": round(abs(score), 2),
            "reason": "Alta chance de sequência ruim"
        }

    if -1 < score < 1:
        return {
            "decision": "RISCO_MEDIO",
            "confidence": round(abs(score), 2),
            "reason": "Cenário instável"
        }

    return {
        "decision": "APOSTAR_MODERADO",
        "confidence": round(score, 2),
        "reason": "Probabilidade moderada baseada no histórico"
    }

# -------------------------------------------------------------
# Endpoints
# -------------------------------------------------------------
@app.route('/', methods=['GET'])
def home():
    return "API OCR Termux Avançada rodando!", 200

@app.route('/ocr', methods=['POST'])
def ocr_api():
    if 'image' not in request.files:
        return jsonify({"error": "Imagem não enviada"}), 400

    img = request.files['image']
    img_path = "/data/data/com.termux/files/home/meu_app/api/temp.png"
img.save(img_path)    text = perform_ocr(img_path)
    multipliers = extract_multipliers(text)

    for m in multipliers:
        history.append((int(time.time()), m))

    stats = compute_stats(window=50)
    decision = make_decision()

    return jsonify({
        "raw_text": text,
        "multipliers": multipliers,
        "stats": stats,
        "decision": decision
    })

# -------------------------------------------------------------
# Run
# -------------------------------------------------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
