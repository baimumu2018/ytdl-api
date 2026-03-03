from flask import Flask, request, jsonify, send_file
import yt_dlp
import os
import uuid
import tempfile

app = Flask(__name__)

# 临时文件目录
TEMP_DIR = tempfile.gettempdir()

@app.route('/health', methods=['GET'])
def health():
    """健康检查"""
    return jsonify({"status": "ok"})

@app.route('/info', methods=['POST'])
def get_info():
    """获取视频信息（不下载）"""
    data = request.json
    url = data.get('url')
    
    if not url:
        return jsonify({"error": "缺少url参数"}), 400
    
    try:
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            return jsonify({
                "title": info.get('title'),
                "duration": info.get('duration'),
                "duration_string": info.get('duration_string'),
                "uploader": info.get('uploader'),
                "description": info.get('description', '')[:500]
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/audio', methods=['POST'])
def extract_audio():
    """下载音频并返回文件"""
    data = request.json
    url = data.get('url')
    quality = data.get('quality', '64')  # 默认64kbps，控制文件大小
    
    if not url:
        return jsonify({"error": "缺少url参数"}), 400
    
    # 生成唯一文件名
    file_id = str(uuid.uuid4())
    output_path = os.path.join(TEMP_DIR, file_id)
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_path + '.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': quality,
        }],
        'quiet': True,
        'no_warnings': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'audio')
        
        audio_file = output_path + '.mp3'
        
        if not os.path.exists(audio_file):
            return jsonify({"error": "音频提取失败"}), 500
        
        # 返回文件
        response = send_file(
            audio_file,
            mimetype='audio/mpeg',
            as_attachment=True,
            download_name=f"{title}.mp3"
        )
        
        # 注册清理回调
        @response.call_on_close
        def cleanup():
            if os.path.exists(audio_file):
                os.remove(audio_file)
        
        return response
        
    except Exception as e:
        # 清理可能的残留文件
        for ext in ['.mp3', '.webm', '.m4a', '.opus']:
            f = output_path + ext
            if os.path.exists(f):
                os.remove(f)
        return jsonify({"error": str(e)}), 500

@app.route('/audio/url', methods=['POST'])
def get_audio_url():
    """只返回音频直链（不下载，让客户端自己下载）"""
    data = request.json
    url = data.get('url')
    
    if not url:
        return jsonify({"error": "缺少url参数"}), 400
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # 找到音频格式
            formats = info.get('formats', [])
            audio_formats = [f for f in formats if f.get('acodec') != 'none' and f.get('vcodec') == 'none']
            
            if audio_formats:
                best_audio = audio_formats[-1]  # 通常最后一个质量最好
            else:
                best_audio = formats[-1]
            
            return jsonify({
                "title": info.get('title'),
                "duration": info.get('duration'),
                "audio_url": best_audio.get('url'),
                "ext": best_audio.get('ext'),
                "filesize": best_audio.get('filesize'),
                "abr": best_audio.get('abr'),  # 音频比特率
            })
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
