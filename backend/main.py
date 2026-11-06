import os
import json
import yt_dlp
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="RAKS Video Downloader API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
HISTORY_FILE = "history.json"

# CRITICAL: Mount the downloads folder so Android app can stream and play videos directly via URL!
app.mount("/downloads", StaticFiles(directory=DOWNLOAD_DIR), name="downloads")

class VideoRequest(BaseModel):
    url: str

# Helper to load download history
def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            try:
                return json.load(f)
            except:
                return []
    return []

# Helper to save download history
def save_history(history_list):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history_list, f, indent=4)

@app.get("/")
def home():
    return {"status": "ONLINE", "brand": "JOHNSTONE RAKS.GHOST KERNEL"}

@app.post("/api/download")
def process_video(data: VideoRequest):
    url = data.url.strip()
    
    if not url:
        raise HTTPException(status_code=400, detail="URL cannot be empty")
    
    if "tiktok.com" not in url.lower() and "instagram.com" not in url.lower():
        raise HTTPException(status_code=400, detail="Only TikTok and Instagram links are supported, bro!")
    
    try:
        # Check if cookies.txt exists in either root or backend folder
        cookie_path = 'cookies.txt'
        if not os.path.exists(cookie_path):
            cookie_path = os.path.join(os.path.dirname(__file__), 'cookies.txt')

        ydl_opts = {
            'outtmpl': os.path.join(DOWNLOAD_DIR, '%(id)s.%(ext)s'),
            'format': 'best',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'extractor_args': {'tiktok': {'api_hostname': 'api16-normal-c-useast1a.tiktokv.com'}},
        }
        
        # Attach cookies only if the file is found to prevent file-not-found crashes
        if os.path.exists(cookie_path):
            ydl_opts['cookiefile'] = cookie_path

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            title = info.get('title', 'Downloaded Video')
            
        platform_name = "TikTok" if "tiktok.com" in url.lower() else "Instagram"
        base_filename = os.path.basename(filename)
        
        # Save record to history collection
        history = load_history()
        item = {
            "title": title,
            "platform": platform_name,
            "url": url,
            "filename": base_filename
        }
        history.insert(0, item) # Add newest to top
        save_history(history)
        
        return {
            "success": True,
            "platform": platform_name,
            "target_url": url,
            "message": f"Successfully downloaded {platform_name} video!",
            "filename": base_filename
        }
    except Exception as e:
        print(f"YT-DLP ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

@app.get("/api/downloads")
def get_downloads_collection():
    """Returns the full collection of downloaded videos for the app and website"""
    return {
        "success": True,
        "collection": load_history()
    }

@app.delete("/api/download/{filename}")
def delete_video(filename: str):
    """Deletes the video file from PC storage and removes it from history.json"""
    file_path = os.path.join(DOWNLOAD_DIR, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    
    history = load_history()
    history = [item for item in history if item["filename"] != filename]
    save_history(history)
    
    return {"success": True, "message": "Deleted successfully"}