from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import yt_dlp

app = FastAPI()


class UrlRequest(BaseModel):
    url: str


class VideoRequest(BaseModel):
    url: str
    format_id: str  # lấy từ danh sách "formats" trả về bởi /info


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
        raise HTTPException(status_code=400, detail=f"Không lấy được thông tin: {e}")

    # Chỉ lấy các format PROGRESSIVE: đã có sẵn cả video+audio trong 1 file.
    # Bỏ format tách riêng (chỉ video hoặc chỉ audio) để tránh trường hợp
    # người dùng chọn quality nhưng nhận về 2 link phải tự ghép.
    formats = []
    seen_heights = set()
    for f in info.get("formats", []):
        has_video = f.get("vcodec") not in (None, "none")
        has_audio = f.get("acodec") not in (None, "none")
        height = f.get("height")

        if has_video and has_audio and height:
            if height in seen_heights:
                continue  # tránh liệt kê trùng cùng 1 độ phân giải nhiều lần
            seen_heights.add(height)
            formats.append({
                "format_id": f.get("format_id"),
                "label": f"{height}p",
                "height": height,
                "ext": f.get("ext"),
                "filesize": f.get("filesize") or f.get("filesize_approx"),
            })

    # Sắp xếp giảm dần theo độ phân giải, dễ hiển thị lên dropdown
    formats.sort(key=lambda x: x["height"], reverse=True)

    return {
        "title": info.get("title"),
        "thumbnail": info.get("thumbnail"),
        "duration": info.get("duration"),
        "formats": formats,  # danh sách quality THẬT có sẵn cho video này
    }


@app.post("/video")
def get_video(req: VideoRequest):
    opts = _base_opts()
    opts["format"] = req.format_id  # dùng đúng format_id user đã chọn từ /info

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(req.url, download=False)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Không lấy được link video: {e}")

    # Vì format_id được chọn từ danh sách progressive ở /info,
    # sẽ không bao giờ rơi vào trường hợp requested_formats (2 link tách rời)
    download_url = info.get("url")

    return {
        "title": info.get("title"),
        "download_url": download_url,
    }


@app.post("/audio")
def get_audio(req: UrlRequest):
    opts = _base_opts()
    opts["format"] = "bestaudio/best"
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(req.url, download=False)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Không lấy được link audio: {e}")

    return {
        "title": info.get("title"),
        "download_url": info.get("url"),
    }
