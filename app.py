import os
import io
import random
import hashlib
import struct
import base64
from flask import Flask, render_template, request, send_file, jsonify
from PIL import Image
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max upload

DOGS_DIR = os.path.join(os.path.dirname(__file__), 'dogs')

# ─────────────────────────────────────────────
#  AES HELPERS  (CBC + PBKDF2)
# ─────────────────────────────────────────────
SALT_SIZE   = 16
IV_SIZE     = 16
KEY_SIZE    = 32   # AES-256
ITERATIONS  = 200_000

def derive_key(password: str, salt: bytes) -> bytes:
    return PBKDF2(password.encode(), salt, dkLen=KEY_SIZE, count=ITERATIONS)

def aes_encrypt(data: bytes, password: str) -> bytes:
    salt = get_random_bytes(SALT_SIZE)
    iv   = get_random_bytes(IV_SIZE)
    key  = derive_key(password, salt)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    ct = cipher.encrypt(pad(data, AES.block_size))
    return salt + iv + ct

def aes_decrypt(blob: bytes, password: str) -> bytes:
    salt, iv, ct = blob[:SALT_SIZE], blob[SALT_SIZE:SALT_SIZE+IV_SIZE], blob[SALT_SIZE+IV_SIZE:]
    key = derive_key(password, salt)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return unpad(cipher.decrypt(ct), AES.block_size)

# ─────────────────────────────────────────────
#  LSB STEGANOGRAPHY
# ─────────────────────────────────────────────
MAGIC = b'PAWCRYPT'

def encode_lsb(img: Image.Image, payload: bytes) -> Image.Image:
    img = img.convert('RGB')
    pixels = list(img.getdata())
    # header = MAGIC (8 bytes) + payload length (4 bytes big-endian)
    header  = MAGIC + struct.pack('>I', len(payload))
    bitstream = []
    for byte in header + payload:
        for bit in range(7, -1, -1):
            bitstream.append((byte >> bit) & 1)

    if len(bitstream) > len(pixels) * 3:
        raise ValueError("Image trop petite pour cacher ces données.")

    new_pixels = []
    bit_idx = 0
    for r, g, b in pixels:
        if bit_idx < len(bitstream):
            r = (r & ~1) | bitstream[bit_idx]; bit_idx += 1
        if bit_idx < len(bitstream):
            g = (g & ~1) | bitstream[bit_idx]; bit_idx += 1
        if bit_idx < len(bitstream):
            b = (b & ~1) | bitstream[bit_idx]; bit_idx += 1
        new_pixels.append((r, g, b))

    out = Image.new('RGB', img.size)
    out.putdata(new_pixels)
    return out

def decode_lsb(img: Image.Image) -> bytes:
    img = img.convert('RGB')
    pixels = list(img.getdata())
    bits = []
    for r, g, b in pixels:
        bits += [r & 1, g & 1, b & 1]

    def bits_to_bytes(b_list):
        result = bytearray()
        for i in range(0, len(b_list) - 7, 8):
            val = 0
            for j in range(8):
                val = (val << 1) | b_list[i + j]
            result.append(val)
        return bytes(result)

    header_bits = bits[:96]   # 12 bytes
    header = bits_to_bytes(header_bits)

    if not header.startswith(MAGIC):
        raise ValueError("Aucune donnée PawCrypt détectée dans cette image.")

    length = struct.unpack('>I', header[8:12])[0]
    payload_bits = bits[96: 96 + length * 8]
    if len(payload_bits) < length * 8:
        raise ValueError("Données corrompues ou incomplètes.")

    return bits_to_bytes(payload_bits)

# ─────────────────────────────────────────────
#  ROUTES
# ─────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/encode', methods=['POST'])
def encode():
    password = request.form.get('password', '')
    if not password:
        return jsonify({'error': 'Mot de passe requis.'}), 400

    # Payload: either uploaded file or text message
    if 'file' in request.files and request.files['file'].filename:
        f = request.files['file']
        raw = f.read()
        # prefix with filename so we can restore it
        fname = f.filename.encode()
        payload_raw = struct.pack('>H', len(fname)) + fname + raw
        is_file = True
    else:
        msg = request.form.get('message', '')
        if not msg:
            return jsonify({'error': 'Message ou fichier requis.'}), 400
        raw = msg.encode('utf-8')
        payload_raw = struct.pack('>H', 0) + raw   # 0 = text
        is_file = False

    # AES encrypt
    try:
        encrypted = aes_encrypt(payload_raw, password)
    except Exception as e:
        return jsonify({'error': f'Erreur chiffrement: {e}'}), 500

    # Pick random dog image
    dogs = [f for f in os.listdir(DOGS_DIR) if f.lower().endswith(('.png','.jpg','.jpeg'))]
    if not dogs:
        return jsonify({'error': 'Aucune image de chien disponible.'}), 500

    dog_path = os.path.join(DOGS_DIR, random.choice(dogs))
    try:
        img = Image.open(dog_path)
        stego = encode_lsb(img, encrypted)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Erreur stéganographie: {e}'}), 500

    buf = io.BytesIO()
    stego.save(buf, format='PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png', as_attachment=True, download_name='pawcrypt_output.png')

@app.route('/decode', methods=['POST'])
def decode():
    password = request.form.get('password', '')
    if not password:
        return jsonify({'error': 'Mot de passe requis.'}), 400

    if 'image' not in request.files or not request.files['image'].filename:
        return jsonify({'error': 'Image requise.'}), 400

    try:
        img = Image.open(request.files['image'])
        encrypted = decode_lsb(img)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Erreur extraction: {e}'}), 500

    try:
        payload_raw = aes_decrypt(encrypted, password)
    except Exception:
        return jsonify({'error': 'Mot de passe incorrect ou données corrompues.'}), 400

    # Parse header
    fname_len = struct.unpack('>H', payload_raw[:2])[0]
    if fname_len == 0:
        # Text message
        text = payload_raw[2:].decode('utf-8')
        return jsonify({'type': 'text', 'message': text})
    else:
        fname = payload_raw[2:2+fname_len].decode('utf-8')
        file_data = payload_raw[2+fname_len:]
        b64 = base64.b64encode(file_data).decode()
        return jsonify({'type': 'file', 'filename': fname, 'data': b64})

@app.route('/analyze', methods=['POST'])
def analyze():
    if 'original' not in request.files or 'encoded' not in request.files:
        return jsonify({'error': 'Les deux images sont requises.'}), 400

    orig_bytes = request.files['original'].read()
    enc_bytes  = request.files['encoded'].read()

    h1 = hashlib.sha256(orig_bytes).hexdigest()
    h2 = hashlib.sha256(enc_bytes).hexdigest()

    # Pixel-level diff
    try:
        img1 = Image.open(io.BytesIO(orig_bytes)).convert('RGB')
        img2 = Image.open(io.BytesIO(enc_bytes)).convert('RGB')

        if img1.size != img2.size:
            diff_pixels = None
            diff_percent = None
        else:
            p1 = list(img1.getdata())
            p2 = list(img2.getdata())
            diffs = sum(1 for a, b in zip(p1, p2) if a != b)
            total = len(p1)
            diff_percent = round(diffs / total * 100, 4)
            diff_pixels = diffs
    except Exception:
        diff_pixels = None
        diff_percent = None

    return jsonify({
        'original_size': len(orig_bytes),
        'encoded_size':  len(enc_bytes),
        'size_diff':     len(enc_bytes) - len(orig_bytes),
        'hash_original': h1,
        'hash_encoded':  h2,
        'hashes_match':  h1 == h2,
        'diff_pixels':   diff_pixels,
        'diff_percent':  diff_percent,
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
