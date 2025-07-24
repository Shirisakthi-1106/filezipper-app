from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
import os
import zipfile
from huffman import HuffmanCoding

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 13 * 1024 * 1024  # 15MB max upload

UPLOAD_FOLDER = "uploads"
PROCESSED_FOLDER = "processed"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return render_template('index1.html')

@app.route('/home')
def home():
    return render_template('index.html')


@app.route('/compress', methods=['POST'])
def compress():
    files = request.files.getlist('file')

    if not files or all(file.filename == '' for file in files):
        return redirect(url_for('index'))

    if len(files) == 1:
        file = files[0]
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)
    else:
        combined_filename = "combined_input.txt"
        file_path = os.path.join(UPLOAD_FOLDER, combined_filename)
        with open(file_path, 'w', encoding='utf-8') as combined:
            for file in files:
                filename = file.filename
                content = file.read().decode('utf-8', errors='ignore')
                combined.write(f"\n--- Start of {filename} ---\n")
                combined.write(content)
                combined.write(f"\n--- End of {filename} ---\n")

    print(f"Compressing file: {file_path}")  # Debug print

    try:
        h = HuffmanCoding(file_path)
        compressed_file_path = h.compress()
    except Exception as e:
        print(f"Compression error: {e}")
        return render_template('error.html', message=f"Compression failed: {e}")

    if compressed_file_path:
        zip_filename = os.path.basename(compressed_file_path) + ".zip"
        zip_path = os.path.join(PROCESSED_FOLDER, zip_filename)
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(compressed_file_path, arcname=os.path.basename(compressed_file_path))
        except Exception as e:
            print(f"ZIP creation error: {e}")
            return render_template('error.html', message=f"ZIP creation failed: {e}")
        return redirect(url_for('success', file=zip_filename, action="compressed"))
    else:
        return render_template('error.html', message="Compression failed.")


@app.route('/decompress', methods=['POST'])
def decompress():
    if 'file' not in request.files:
        return render_template('error.html', message="No file uploaded.")

    file = request.files['file']
    if file.filename == '':
        return render_template('error.html', message="No selected file.")

    file_path = os.path.join(UPLOAD_FOLDER, secure_filename(file.filename))
    file.save(file_path)

    extracted_file_path = None

    try:
        with zipfile.ZipFile(file_path, 'r') as zipf:
            extracted_files = zipf.namelist()
            print(f"Files in ZIP: {extracted_files}")

            if len(extracted_files) != 1:
                return render_template('error.html', message="ZIP archive should contain exactly one compressed .bin file.")

            extracted_file = extracted_files[0]

            if not extracted_file.endswith(".bin"):
                return render_template('error.html', message="Invalid file format inside ZIP. Expected a .bin file.")

            zipf.extractall(PROCESSED_FOLDER)
            extracted_file_path = os.path.join(PROCESSED_FOLDER, extracted_file)
            print(f"Extracted File Path: {extracted_file_path}")
    except (zipfile.BadZipFile, ValueError) as e:
        return render_template('error.html', message=f"Invalid ZIP file: {e}")

    if extracted_file_path and os.path.exists(extracted_file_path):
        print(f"Decompressing file: {extracted_file_path}")

        try:
            h = HuffmanCoding(extracted_file_path)
            decompressed_file = h.decompress()
            print(f"Decompressed File Path: {decompressed_file}")
        except Exception as e:
            return render_template('error.html', message=f"Decompression failed: {e}")

        if decompressed_file and os.path.exists(decompressed_file):
            # Optional: Display preview of decompressed content (especially if it's a combined text file)
            with open(decompressed_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read().strip()

            if not content:
                return render_template('error.html', message="Decompression failed. Output file is empty.")

            decompressed_filename = os.path.basename(decompressed_file)
            return redirect(url_for('success', file=decompressed_filename, action="decompressed"))
        else:
            return render_template('error.html', message="Decompression failed.")

    return render_template('error.html', message="ZIP extraction failed or incorrect file format.")


@app.route('/success')
def success():
    file = request.args.get('file')
    action = request.args.get('action')
    files = file.split(',') if file else []
    return render_template('success.html', action=action, files=files)


@app.route('/download/<filename>')
def download(filename):
    return send_from_directory(PROCESSED_FOLDER, filename, as_attachment=True)

@app.errorhandler(RequestEntityTooLarge)

def handle_large_file(e):
    return render_template('error.html', message="File size exceeds the 15MB limit.")


if __name__ == '__main__':
    app.run(debug=True)