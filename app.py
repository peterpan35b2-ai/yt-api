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
        "socket_timeout": 20,  # tránh treo lâu nếu site phản hồi chậm
    }


def _get_stream_type(f):
    """
    Phân loại format theo protocol thật: direct / hls / dash.
    Không dựa vào format_id riêng của từng nền tảng, nên áp dụng
    được cho mọi nền tảng yt-dlp hỗ trợ.
    """
    protocol = (f.get("protocol") or "").lower()
    url = f.get("url") or ""

    if "m3u8" in protocol or ".m3u8" in url:
        return "hls"
    if "dash" in protocol or ".mpd" in url:
        return "dash"
    return "direct"


@app.get("/")
def home():
    return {"status": "ok", "message": "yt-api online"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/info")
def get_info(req: UrlRequest):
    try:
        with yt_dlp.YoutubeDL(_base_opts()) as ydl:
            info = ydl.extract_info(req.url, download=False)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Không lấy được thông tin: {e}")

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
    formats.sort(key=lambda x: x["height"], reverse=True)

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
        raise HTTPException(status_code=400, detail=f"Không lấy được link video: {e}")

    return {
        "title": info.get("title"),
        "download_url": info.get("url"),
        "filesize": info.get("filesize") or info.get("filesize_approx"),
        "ext": info.get("ext"),
    }


@app.post("/audio")
def get_audio(req: UrlRequest):
    """
    Ưu tiên format audio tải trực tiếp được (HTTP thường) bất kể nền tảng nào —
    không hardcode format_id riêng của SoundCloud, nên hoạt động chung cho
    Mixcloud, Bandcamp, và các nền tảng khác yt-dlp hỗ trợ.
    Nếu nền tảng chỉ có HLS/DASH, vẫn trả về nhưng đánh dấu is_hls=True
    để frontend biết mà cảnh báo đúng, không đánh lừa người dùng.
    """
    try:
        with yt_dlp.YoutubeDL(_base_opts()) as ydl:
            info = ydl.extract_info(req.url, download=False)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Không lấy được link audio: {e}")

    formats = info.get("formats", [])
    audio_formats = [
        f for f in formats
        if f.get("acodec") not in (None, "none") and f.get("url")
    ]

    if not audio_formats:
        raise HTTPException(status_code=404, detail="Không tìm thấy audio phù hợp")

    # Trong các format audio có sẵn, ưu tiên bản tải trực tiếp (không HLS/DASH),
    # trong nhóm đó chọn bitrate cao nhất nếu có nhiều lựa chọn.
    direct_formats = [f for f in audio_formats if _get_stream_type(f) == "direct"]

    if direct_formats:
        best = max(direct_formats, key=lambda f: f.get("abr") or 0)
    else:
        # Không có bản trực tiếp nào — đành lấy bản tốt nhất trong số HLS/DASH có sẵn
        best = max(audio_formats, key=lambda f: f.get("abr") or 0)

    stream_type = _get_stream_type(best)

    return {
        "title": info.get("title"),
        "download_url": best.get("url"),
        "format_id": best.get("format_id"),
        "ext": best.get("ext"),
        "stream_type": stream_type,  # "direct" | "hls" | "dash"
        "filesize": best.get("filesize") or best.get("filesize_approx"),
        "abr": best.get("abr"),
    }
