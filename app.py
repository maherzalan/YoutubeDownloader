from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import os
import yt_dlp

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/status', methods=['GET'])
def status():
    return jsonify({'status': 'online'})

def ensure_directory_exists(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def get_formats(url):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            formats = info_dict.get('formats', [])
            return formats
    except Exception as e:
        print(f"Error extracting formats: {str(e)}")
        return []

@app.route('/get_formats', methods=['POST'])
def get_formats_route():
    data = request.get_json()
    url = data.get('url')
    if not url:
        return jsonify({'error': 'Missing URL'}), 400

    formats = get_formats(url)
    if not formats:
        return jsonify({'error': 'No formats found'}), 404

    return jsonify({'formats': formats})

@app.route('/download', methods=['POST'])
def download():
    data = request.get_json()
    url = data.get('url')
    output_dir = data.get('output_dir')
    format_id = data.get('format_id')
    type = data.get('type')

    if not url or not output_dir or not format_id or not type:
        return jsonify({'error': 'Missing parameters'}), 400

    ensure_directory_exists(output_dir)

    def progress_hook(d):
        if d['status'] == 'downloading':
            percentage = d['_percent_str'].strip().replace('\x1b', '').replace('[0;94m', '').replace('[0m', '')
            socketio.emit('progress', {'percentage': percentage})

    ydl_opts = {
        'format': format_id,
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
        'progress_hooks': [progress_hook],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    socketio.run(app, debug=True)
