import os
import tempfile
import json
from flask import Flask, request, jsonify, send_file
import yt_dlp

app = Flask(__name__)

COOKIES_CONTENT = os.environ.get('YOUTUBE_COOKIES', '')

def get_cookies_file():
    if COOKIES_CONTENT:
        f = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
        f.write(COOKIES_CONTENT)
        f.close()
        return f.name
    return None

def get_ydl_opts(cookies_file=None):
    """获取 yt-dlp 配置选项"""
    opts = {
        'quiet': False,
        'no_warnings': False,
        'socket_timeout': 30,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        },
        # YouTube 特定选项
        'extractor_args': {
            'youtube': {
                'player_client': ['web'],
                'player_skip': ['js', 'configs'],
            }
        },
        # 重试选项
        'retries': 5,
        'fragment_retries': 5,
        'skip_unavailable_fragments': True,
    }
    
    if cookies_file:
        opts['cookiefile'] = cookies_file
    
    return opts

@app.route('/health', methods=['GET'])
def health():
    """健康检查"""
    return jsonify({"status": "ok"})

@app.route('/info', methods=['POST'])
def get_info():
    """获取视频信息（不下载）"""
    data = request.get_json()
    url = data.get('url')
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    try:
        cookies_file = get_cookies_file()
        ydl_opts = get_ydl_opts(cookies_file)
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return jsonify({
                "title": info.get('title'),
                "duration": info.get('duration'),
                "duration_string": info.get('duration_string'),
                "uploader": info.get('uploader'),
                "description": info.get('description', '')[:500],
                "thumbnail": info.get('thumbnail'),
                "view_count": info.get('view_count'),
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/audio', methods=['POST'])
def download_audio():
    """下载音频并返回文件"""
    data = request.get_json()
    url = data.get('url')
    quality = data.get('quality', '64')
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    try:
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
            output_path = tmp.name
        
        cookies_file = get_cookies_file()
        ydl_opts = get_ydl_opts(cookies_file)
        
        ydl_opts.update({
            'format': 'bestaudio/best',
            'outtmpl': output_path.replace('.mp3', ''),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': quality,
            }],
        })
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        audio_file = output_path.replace('.mp3', '') + '.mp3'
        return send_file(audio_file, mimetype='audio/mpeg')
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/video', methods=['POST'])
def download_video():
    """下载视频"""
    data = request.get_json()
    url = data.get('url')
    quality = data.get('quality', 'best')
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    try:
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp:
            output_path = tmp.name
        
        cookies_file = get_cookies_file()
        ydl_opts = get_ydl_opts(cookies_file)
        
        ydl_opts.update({
            'format': f'best[height<={quality}]/best' if quality != 'best' else 'best',
            'outtmpl': output_path.replace('.mp4', ''),
        })
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        video_file = output_path.replace('.mp4', '') + '.mp4'
        return send_file(video_file, mimetype='video/mp4')
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
