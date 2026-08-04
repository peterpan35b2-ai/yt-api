from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import yt_dlp

app = FastAPI()


class UrlRequest(BaseModel):
    url: str


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
