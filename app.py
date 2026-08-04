from fastapi import FastAPI

app = FastAPI()

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
