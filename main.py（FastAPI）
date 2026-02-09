import os, uuid, glob, subprocess, json
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="yt-dlp audio extractor")

# 将 /tmp 作为静态目录，用于暴露下载好的音频
app.mount("/files", StaticFiles(directory="/tmp"), name="files")

class ExtractRequest(BaseModel):
    url: str
    audio_format: str | None = "m4a"   # 可改为 mp3 等

def run_cmd(cmd):
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr

@app.post("/extract")
async def extract(req: Request, body: ExtractRequest):
    url = body.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="url is required")

    # 生成唯一前缀，避免并发冲突
    uid = uuid.uuid4().hex
    # 先获取元数据，检查时长（可按需限制）
    meta_cmd = [
        "yt-dlp", "-J", "--no-playlist", "--skip-download", url
    ]
    code, out, err = run_cmd(meta_cmd)
    if code != 0:
        raise HTTPException(status_code=500, detail=f"metadata error: {err or out}")

    try:
        meta = json.loads(out)
        duration = meta.get("duration")  # 秒
        title = meta.get("title")
    except Exception:
        duration, title = None, None

    # 下载音频并转码
    fmt = body.audio_format or "m4a"
    out_tpl = f"/tmp/{uid}.%(ext)s"
    dl_cmd = [
        "yt-dlp",
        "-f", "bestaudio/best",
        "-x",
        "--audio-format", fmt,
        "--audio-quality", "5",  # 0(最好)-9(最差)，5≈160kbps，适合转写
        "--no-playlist",
        "-o", out_tpl,
        url
    ]
    code, out, err = run_cmd(dl_cmd)
    if code != 0:
        raise HTTPException(status_code=500, detail=f"download error: {err or out}")

    # 找到生成的文件
    files = glob.glob(f"/tmp/{uid}.*")
    if not files:
        raise HTTPException(status_code=500, detail="audio file not found after download")
    audio_path = files[0]
    filename = os.path.basename(audio_path)

    # 构造可下载 URL：<host>/files/<filename>
    base = str(req.base_url).rstrip("/")
    audio_url = f"{base}/files/{filename}"

    return JSONResponse({
        "audioUrl": audio_url,
        "filename": filename,
        "duration": duration,
        "title": title,
        "format": fmt
    })
