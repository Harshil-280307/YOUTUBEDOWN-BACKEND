from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import yt_dlp
import os
import uuid

app = Flask(__name__)
CORS(app)

DOWNLOAD_FOLDER = "downloads"
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

@app.route("/progress", methods=["GET"])
def get_progress():
    return jsonify(progress_data)


@app.route("/download", methods=["POST"])
def download_video():
    data = request.get_json()
    url = data.get("url")
    media_type = data.get("type", "both")
    quality = data.get("quality", "high")

    if not url:
        return jsonify({"error": "No URL provided"}), 400

    # Generate unique filename
    filename_base = str(uuid.uuid4())
    output_path = os.path.join(DOWNLOAD_FOLDER, f"{filename_base}.%(ext)s")

    # Format mapping
    format_map = {
        "high": "bestvideo[height>=1080]+bestaudio/best[height>=1080]",
        "medium": "bestvideo[height<=720]+bestaudio/best[height<=720]",
        "low": "bestvideo[height<=360]+bestaudio/best[height<=360]",
    }

    # Media type logic
    postprocessors = []
    if media_type == "audio":
        postprocessors.append({
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        })
        format_code = "bestaudio"
    elif media_type == "video":
        format_code = format_map.get(quality, "bestvideo+bestaudio/best")
    else:  # both
        format_code = format_map.get(quality, "bestvideo+bestaudio/best")
        postprocessors.append({
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4'
        })

    progress_data = {}

    def progress_hook(d):
        if d['status'] == 'downloading':
            progress_data['downloaded'] = d.get('downloaded_bytes', 0)
            progress_data['total'] = d.get('total_bytes') or d.get('total_bytes_estimate', 1)
            progress_data['speed'] = d.get('speed', 0)
            progress_data['eta'] = d.get('eta', 0)
            progress_data['progress'] = round((progress_data['downloaded'] / progress_data['total']) * 100, 2)


    ydl_opts = {
        "outtmpl": output_path,
        "format": format_code,
        "cookiefile": "cookies.txt",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "merge_output_format": "mp4",
         "progress_hooks": [progress_hook],
        "postprocessors": postprocessors,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            # Get correct final file path
            downloaded_file = ydl.prepare_filename(info)
            if media_type == "audio":
                downloaded_file = downloaded_file.rsplit(".", 1)[0] + ".mp3"
            else:
                downloaded_file = downloaded_file.rsplit(".", 1)[0] + ".mp4"
            
            if not os.path.exists(downloaded_file):
                return jsonify({"error": "File not downloaded properly"}), 500

            return send_file(downloaded_file, as_attachment=True)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
