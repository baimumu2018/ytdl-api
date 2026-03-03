import os
import tempfile
from flask import Flask, request, jsonify, send_file
import yt_dlp

app = Flask(__name__)

COOKIES_CONTENT = os.environ.get('YOUTUBE_COOKIES', '')

def get_cookies_file():
    if COOKIES_CONTENT:
        # 处理可能被转义的换行符
        content = COOKIES_CONTENT.replace('\\n', '\n')
        f = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
        f.write(content)
        f.close()
        return f.name
    return None

@app.route('/debug', methods=['GET'])
def debug():
    content = COOKIES_CONTENT.replace('\\n', '\n')
    lines = content.split('\n') if content else []
    youtube_lines = [l for l in lines if 'youtube' in l.lower()]
    return jsonify({
        'cookies_set': bool(COOKIES_CONTENT),
        'cookies_length': len(COOKIES_CONTENT),
        'total_lines': len(lines),
        'youtube_lines_count': len(youtube_lines),
        'first_100_chars': COOKIES_CONTENT[:100] if COOKIES_CONTENT else None,
        'has_newlines': '\n' in COOKIES_CONTENT or '\\n' in COOKIES_CONTENT
    })

@app.route('/audio', methods=['POST'])
def download_audio():
    data = request.get_json()
    url = data.get('url')
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    try:
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
            output_path = tmp.name
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': output_path.replace('.mp3', ''),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '64',
            }],
            'quiet': True,
            'no_warnings': True,
        }
        
        cookies_file = get_cookies_file()
        if cookies_file:
            ydl_opts['cookiefile'] = cookies_file
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        return send_file(output_path, mimetype='audio/mpeg')
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/info', methods=['POST'])
def get_info():
    data = request.get_json()
    url = data.get('url')
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }
        
        cookies_file = get_cookies_file()
        if cookies_file:
            ydl_opts['cookiefile'] = cookies_file
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return jsonify({
                'title': info.get('title'),
                'duration': info.get('duration'),
                'channel': info.get('channel'),
            })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
