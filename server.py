import os
import ssl
import yt_dlp
from flask import Flask, render_template, request, send_file, abort, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()
# Disable SSL verification (use with caution)
ssl._create_default_https_context = ssl._create_unverified_context

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

BACKEND_URL = os.getenv('backendUrl', 'http://127.0.0.1:5000')

# Ensure downloads directory exists
DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), 'downloads')
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html', backend_url=BACKEND_URL)

@app.route('/video-info', methods=['POST'])
def video_info():
    url = request.form.get('url')
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    try:
        with yt_dlp.YoutubeDL() as ydl:
            info = ydl.extract_info(url, download=False)
            return jsonify({
                "title": info.get('title', ''),
                "thumbnail": info.get('thumbnail', ''),
                "duration": info.get('duration', 0),
                "channel": info.get('uploader', '')
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/download', methods=['POST'])
def download():
    url = request.form.get('url')
    download_type = request.form.get('type')

    if not url:
        return jsonify({"error": "No URL provided"}), 400

    # Specific configuration for MP3 and MP4
    if download_type == 'video':
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',
            'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
            'merge_output_format': 'mp4',
            'nooverwrites': True,
            'no_color': True
        }
    else:  # audio
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
            'nooverwrites': True,
            'no_color': True
        }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            
            # Determine the final filename
            if download_type == 'video':
                filename = ydl.prepare_filename(info_dict).replace('.webm', '.mp4').replace('.mkv', '.mp4')
            else:
                # For audio, the post-processor changes the extension to .mp3
                filename = ydl.prepare_filename(info_dict).rsplit('.', 1)[0] + '.mp3'
        
        return send_file(filename, as_attachment=True)

    except yt_dlp.utils.DownloadError as e:
        return jsonify({"error": f"Download failed: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)