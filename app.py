from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import yt_dlp

app = FastAPI()


class UrlRequest(BaseModel):
    url: str


class VideoRequest(BaseModel):
    url: str
    quality: str = "best"


@app.get("/")
def home():
    return {
        "status": "ok",
        "message": "yt-api online"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


@app.post("/info")
def get_info(req: UrlRequest):
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(req.url, download=False)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Không lấy được thông tin: {e}")

    return {
        "title": info.get("title"),
        "thumbnail": info.get("thumbnail"),
        "duration": info.get("duration"),
    }


@app.post("/video")
def get_video(req: VideoRequest):
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
    }

    if req.quality and req.quality != "best":
        height = "".join(filter(str.isdigit, req.quality))
        opts["format"] = f"bestvideo[height<={height}]+bestaudio/best[height<={height}]"
    else:
        opts["format"] = "best"  # ưu tiên progressive (1 file gộp sẵn) để tránh phải merge 2 link

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(req.url, download=False)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Không lấy được link video: {e}")

    if info.get("requested_formats"):
        download_url = [f["url"] for f in info["requested_formats"]]
    else:
        download_url = info.get("url")

    return {
        "title": info.get("title"),
        "download_url": download_url,
    }


@app.post("/audio")
def get_audio(req: UrlRequest):
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        "format": "bestaudio/best",
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(req.url, download=False)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Không lấy được link audio: {e}")

    return {
        "title": info.get("title"),
        "download_url": info.get("url"),
    }
