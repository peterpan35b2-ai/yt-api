from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import yt_dlp

app = FastAPI()


class UrlRequest(BaseModel):
    url: str


class VideoRequest(BaseModel):
    url: str
    format_id: str


def _base_opts():
    return {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
    }


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
    try:
        with yt_dlp.YoutubeDL(_base_opts()) as ydl:
            info = ydl.extract_info(req.url, download=False)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Không lấy được thông tin: {e}"
        )

    formats = []
    seen_heights = set()

    for f in info.get("formats", []):
        has_video = f.get("vcodec") not in (None, "none")
        has_audio = f.get("acodec") not in (None, "none")
        height = f.get("height")

        if has_video and has_audio and height:
            if height in seen_heights:
                continue

            seen_heights.add(height)

            formats.append({
                "format_id": f.get("format_id"),
                "label": f"{height}p",
                "height": height,
                "ext": f.get("ext"),
                "filesize": f.get("filesize") or f.get("filesize_approx"),
            })

    formats.sort(
        key=lambda x: x["height"],
        reverse=True
    )

    return {
        "title": info.get("title"),
        "thumbnail": info.get("thumbnail"),
        "duration": info.get("duration"),
        "formats": formats,
    }


@app.post("/video")
def get_video(req: VideoRequest):
    opts = _base_opts()
    opts["format"] = req.format_id

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(req.url, download=False)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Không lấy được link video: {e}"
        )

    return {
        "title": info.get("title"),
        "download_url": info.get("url"),
    }


@app.post("/audio")
def get_audio(req: UrlRequest):
    try:
        with yt_dlp.YoutubeDL(_base_opts()) as ydl:
            info = ydl.extract_info(req.url, download=False)

        formats = info.get("formats", [])

        # Ưu tiên MP3 HTTP trực tiếp (SoundCloud)
        preferred_ids = [
            "http_mp3_1_0",
            "http_mp3_128",
            "http_mp3",
            "hls_mp3_1_0",
            "hls_aac_160k",
            "hls_aac_96k",
        ]

        for fmt_id in preferred_ids:
            for f in formats:
                if (
                    f.get("format_id") == fmt_id
                    and f.get("url")
                ):
                    return {
                        "title": info.get("title"),
                        "download_url": f.get("url"),
                        "format_id": fmt_id,
                    }

        # fallback audio bất kỳ
        for f in formats:
            if (
                f.get("acodec")
                and f.get("acodec") != "none"
                and f.get("url")
            ):
                return {
                    "title": info.get("title"),
                    "download_url": f.get("url"),
                    "format_id": f.get("format_id"),
                }

        if info.get("url"):
            return {
                "title": info.get("title"),
                "download_url": info.get("url"),
                "format_id": "default",
            }

        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy audio phù hợp"
        )

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Không lấy được link audio: {e}"
        )
