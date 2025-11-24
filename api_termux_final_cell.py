# -------------------------------------------------------------
# API OCR Cloud com OCR.Space (sem Tesseract)
# -------------------------------------------------------------
from flask import Flask, request, jsonify
from PIL import Image
import os, time, re
from collections import deque
import requests
import io

# -------------------------------------------------------------
# App
# -------------------------------------------------------------
app = Flask(__name__)

regex_mult = re.compile(r"(\d+(?:[.,]\d+)?)[xX]\b")
history = deque(maxlen=1500)

# -------------------------------------------------------------
# Configurações OCR.Space
# -------------------------------------------------------------
OCR_SPACE_API_KEY = "K86489254288957"  # sua chave
OCR_SPACE_API_URL = "https://api.ocr.space/parse/image"

def ocr_space_file(file_bytes, filename=None, language='por'):
    files = {'file': (filename or 'image.png', file_bytes)}
    data = {'apikey': OCR_SPACE_API_KEY, 'language': language, 'isOverlayRequired': False}
    try:
        resp = requests.post(OCR_SPACE_API_URL, files=files, data=data, timeout=60)
        resp.raise_for_status()
        result = resp.json()
        if result.get('IsErroredOnProcessing'):
            return None, result
        parsed = result.get('ParsedResults')
        if parsed and len(parsed) > 0:
            text = parsed[0].get('ParsedText','')
            return text, result
        return None, result
    except Exception as e:
        return None, {"error": str(e)}

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
# Estatísticas simples em Python puro
# -------------------------------------------------------------
def compute_stats(window=50):
    data = [m for (_, m) in list(history)[-window:]]
    if not data:
        return None
    n = len(data)
    sorted_data = sorted(data)
    mean = sum(data)/n
    median = sorted_data[n//2] if n%2==1 else sum(sorted_data[n//2-1:n//2+1])/2
    std = (sum((x-mean)**2 for x in data)/n)**0.5
    min_val = min(data)
    max_val = max(data)
    pct_below_2 = sum(1 for x in data if x<2)/n
    pct_below_1_5 = sum(1 for x in data if x<1.5)/n
    pct_above_5 = sum(1 for x in data if x>=5)/n
    return {
        "count": n,
        "mean": mean,
        "median": median,
        "std": std,
        "min": min_val,
        "max": max_val,
        "pct_below_2": pct_below_2,
        "pct_below_1_5": pct_below_1_5,
        "pct_above_5": pct_above_5
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
# Função para pegar último screenshot (Termux)
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
    return "API OCR.Space Celular rodando!", 200

@app.route('/ocr', methods=['POST'])
def ocr_api():
    if 'image' not in request.files:
        return jsonify({"error": "Imagem não enviada"}), 400
    img = request.files['image']
    img_bytes = img.read()
    text, raw = ocr_space_file(img_bytes, filename=img.filename)
    multipliers = extract_multipliers(text or "")
    for m in multipliers:
        history.append((int(time.time()), m))
    stats = compute_stats(window=50)
    decision = make_decision()
    return jsonify({
        "raw_text": text,
        "multipliers": multipliers,
        "stats": stats,
        "decision": decision,
        "ocr_space_raw": raw
    })

@app.route('/ocr_last', methods=['GET'])
def ocr_last_screenshot():
    img_path = get_last_screenshot()
    if not img_path:
        return jsonify({"error": "Nenhuma imagem encontrada na pasta Downloads"}), 404
    with open(img_path, "rb") as f:
        img_bytes = f.read()
    text, raw = ocr_space_file(img_bytes, filename=os.path.basename(img_path))
    multipliers = extract_multipliers(text or "")
    for m in multipliers:
        history.append((int(time.time()), m))
    stats = compute_stats(window=50)
    decision = make_decision()
    return jsonify({
        "file_used": img_path,
        "raw_text": text,
        "multipliers": multipliers,
        "stats": stats,
        "decision": decision,
        "ocr_space_raw": raw
    })

# -------------------------------------------------------------
# Rodar API
# -------------------------------------------------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)
