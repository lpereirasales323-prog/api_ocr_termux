# -------------------------------------------------------------
# API OCR Termux Final Otimizada - Celular (Tesseract + Pillow + NumPy)
# Endpoint para último screenshot e melhorias no pré-processamento
# -------------------------------------------------------------
from flask import Flask, request, jsonify
from PIL import Image, ImageFilter, ImageOps
import pytesseract
import numpy as np
import os
import time
import re
from collections import deque

# -------------------------------------------------------------
# App
# -------------------------------------------------------------
app = Flask(__name__)

regex_mult = re.compile(r"(\d+(?:[.,]\d+)?)[xX]\b")
history = deque(maxlen=1500)

# -------------------------------------------------------------
# UTIL — ajuste de imagem com Pillow (sem OpenCV)
# -------------------------------------------------------------
def preprocess_image(path):
    img = Image.open(path).convert("L")  # cinza
    img = img.filter(ImageFilter.MedianFilter(size=3))  # remover ruído
    img = ImageOps.autocontrast(img, cutoff=2)  # melhorar contraste
    img = img.filter(ImageFilter.SHARPEN)  # aumentar nitidez
    img = img.point(lambda x: 0 if x < 128 else 255, '1')  # binarização simples
    return img

# -------------------------------------------------------------
# OCR avançado (Tesseract)
# -------------------------------------------------------------
def perform_ocr(path):
    try:
        pre = preprocess_image(path)
        pre.save("/data/data/com.termux/files/home/meu_app/api/pre_temp.png")
        # PSM 6 = Assume um bloco uniforme de texto
        text_tess = pytesseract.image_to_string(Image.open(path), config='--psm 6')
        text_tess_pre = pytesseract.image_to_string(pre, config='--psm 6')
        combined = text_tess + "\n" + text_tess_pre
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
# Estatísticas
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
# Decisão probabilística
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
        return {"decision": "NAO_APOSTAR", "confidence": round(abs(score),2), "reason": "Alta chance de sequência ruim"}
    if -1 < score < 1:
        return {"decision": "RISCO_MEDIO", "confidence": round(abs(score),2), "reason": "Cenário instável"}
    return {"decision": "APOSTAR_MODERADO", "confidence": round(score,2), "reason": "Probabilidade moderada baseada no histórico"}

# -------------------------------------------------------------
# Função para pegar último screenshot
# -------------------------------------------------------------
def get_last_screenshot():
    downloads_path = "/data/data/com.termux/files/home/storage/downloads/"
    files = [f for f in os.listdir(downloads_path)
             if os.path.isfile(os.path.join(downloads_path, f)) and f.lower().endswith(('.png','.jpg','.jpeg'))]
    if not files:
        return None
    files = sorted(files, key=lambda x: os.path.getmtime(os.path.join(downloads_path, x)), reverse=True)
    return os.path.join(downloads_path, files[0])

# -------------------------------------------------------------
# Endpoints
# -------------------------------------------------------------
@app.route('/', methods=['GET'])
def home():
    return "API OCR Termux Celular rodando!", 200

@app.route('/ocr', methods=['POST'])
def ocr_api():
    if 'image' not in request.files:
        return jsonify({"error": "Imagem não enviada"}), 400
    img = request.files['image']
    img_path = "/data/data/com.termux/files/home/meu_app/api/temp.png"
    img.save(img_path)
    text = perform_ocr(img_path)
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

@app.route('/ocr_last', methods=['GET'])
def ocr_last_screenshot():
    img_path = get_last_screenshot()
    if not img_path:
        return jsonify({"error": "Nenhuma imagem encontrada na pasta Downloads"}), 404
    text = perform_ocr(img_path)
    multipliers = extract_multipliers(text)
    for m in multipliers:
        history.append((int(time.time()), m))
    stats = compute_stats(window=50)
    decision = make_decision()
    return jsonify({
        "file_used": img_path,
        "raw_text": text,
        "multipliers": multipliers,
        "stats": stats,
        "decision": decision
    })

# -------------------------------------------------------------
# Rodar API
# -------------------------------------------------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)
