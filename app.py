from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import os

app = Flask(__name__)
CORS(app)

DOWNLOAD_FOLDER = "downloads"
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# Shared progress tracker
progress_data = {
    "progress": 0,
    "downloaded": 0,
    "total": 1,
    "eta": 0
}

# Progress hook function
def progress_hook(d):
    if d['status'] == 'downloading':
        progress_data['progress'] = float(d.get('progress', 0))
        progress_data['downloaded'] = d.get('downloaded_bytes', 0)
        progress_data['total'] = d.get('total_bytes', 1)
        progress_data['eta'] = d.get('eta', 0)

@app.route("/download", methods=["POST"])
def download_video():
    data = request.get_json()
    url = data.get("url")
    type_ = data.get("type", "both")
    quality = data.get("quality", "high")

    if not url:
        return jsonify({"error": "No URL provided"}), 400

    # Format mapping based on quality
    quality_map = {
        "high": "bestvideo[height>=1080]+bestaudio/best",
        "medium": "bestvideo[height<=720]+bestaudio/best",
        "low": "bestvideo[height<=360]+bestaudio/best"
    }

    # Base options
    ydl_opts = {
        "outtmpl": os.path.join(DOWNLOAD_FOLDER, "%(title)s.%(ext)s"),
        "cookiefile": "cookies.txt",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [progress_hook]
    }

    if type_ == "audio":
        ydl_opts["format"] = "bestaudio/best"
        ydl_opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192"
        }]
    elif type_ == "video":
        ydl_opts["format"] = quality_map.get(quality, "bestvideo+bestaudio")
        ydl_opts["merge_output_format"] = "mp4"
    else:  # both = video+audio
        ydl_opts["format"] = quality_map.get(quality, "bestvideo+bestaudio")
        ydl_opts["merge_output_format"] = "mp4"

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            # Some processors change ext (like .webm -> .mp3)
            if type_ == "audio":
                filename = os.path.splitext(filename)[0] + ".mp3"
            elif type_ == "video":
                filename = os.path.splitext(filename)[0] + ".mp4"
            return send_file(filename, as_attachment=True)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/progress", methods=["GET"])
def get_progress():
    return jsonify(progress_data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
