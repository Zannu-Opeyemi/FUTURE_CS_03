import os
import io
from flask import Flask, request, render_template, send_file, flash, redirect, url_for
from werkzeug.utils import secure_filename
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

app = Flask(__name__)
app.secret_key = 'super_secret_session_key' 

# 1. SETUP FOLDERS
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
KEY_FILE = 'master.key'

# 2. KEY MANAGEMENT (Get or Create the Key)
def load_key():
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, 'rb') as f:
            return f.read()
    else:
        key = get_random_bytes(32) # Generates a 256-bit key
        with open(KEY_FILE, 'wb') as f:
            f.write(key)
        return key

SYMMETRIC_KEY = load_key()

# 3. ENCRYPTION FUNCTION
def encrypt_data(file_data):
    # Create the cipher engine
    cipher = AES.new(SYMMETRIC_KEY, AES.MODE_GCM)
    # Encrypt the file
    ciphertext, tag = cipher.encrypt_and_digest(file_data)
    # Return: Nonce + Tag + Ciphertext
    return cipher.nonce + tag + ciphertext

# 4. DECRYPTION FUNCTION
def decrypt_data(encrypted_data):
    try:
        nonce = encrypted_data[:16]      # First 16 bytes
        tag = encrypted_data[16:32]      # Next 16 bytes
        ciphertext = encrypted_data[32:] # The rest is data
        
        cipher = AES.new(SYMMETRIC_KEY, AES.MODE_GCM, nonce=nonce)
        return cipher.decrypt_and_verify(ciphertext, tag)
    except:
        return None # Decryption failed (file was tampered with)

# 5. WEBSITE ROUTES
@app.route('/')
def index():
    files = os.listdir(UPLOAD_FOLDER)
    return render_template('index.html', files=files)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files: return redirect(request.url)
    file = request.files['file']
    if file.filename == '': return redirect(request.url)

    # Read -> Encrypt -> Save
    file_data = file.read()
    encrypted_data = encrypt_data(file_data)
    
    filename = secure_filename(file.filename)
    with open(os.path.join(UPLOAD_FOLDER, filename + ".enc"), 'wb') as f:
        f.write(encrypted_data)
        
    flash(f'File uploaded and encrypted!')
    return redirect(url_for('index'))

@app.route('/download/<filename>')
def download_file(filename):
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    with open(file_path, 'rb') as f:
        encrypted_data = f.read()

    # Decrypt
    decrypted_data = decrypt_data(encrypted_data)
    
    if decrypted_data is None:
        return "Error: File integrity check failed! Data was tampered with."

    return send_file(io.BytesIO(decrypted_data), download_name=filename.replace(".enc", ""), as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)