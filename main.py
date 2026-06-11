from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChannelCreate(BaseModel):
    name: str
    category: str
    url: str

class LoginData(BaseModel):
    password: str

class CategoryRename(BaseModel):
    old_name: str
    new_name: str

def get_db_connection():
    conn = sqlite3.connect('sports_iptv.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT,
            url TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.get("/")
def read_root():
    return {"message": "Welcome to Sports IPTV API"}

@app.get("/api/channels")
def get_channels():
    conn = get_db_connection()
    channels = conn.execute('SELECT * FROM channels ORDER BY id DESC').fetchall()
    conn.close()
    return [dict(ix) for ix in channels]

@app.post("/api/channels")
def add_channel(channel: ChannelCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO channels (name, category, url) VALUES (?, ?, ?)', 
                   (channel.name, channel.category, channel.url))
    conn.commit()
    conn.close()
    return {"message": "Channel added successfully!"}

@app.delete("/api/channels/{channel_id}")
def delete_channel(channel_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM channels WHERE id = ?', (channel_id,))
    conn.commit()
    conn.close()
    return {"message": "Channel deleted successfully!"}

@app.delete("/api/channels/all/delete")
def delete_all_channels():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM channels')
    conn.commit()
    conn.close()
    return {"message": "All channels deleted successfully!"}

# --- ক্যাটাগরি ম্যানেজমেন্ট API ---
@app.put("/api/categories")
def rename_category(data: CategoryRename):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE channels SET category = ? WHERE category = ?', (data.new_name, data.old_name))
    conn.commit()
    conn.close()
    return {"message": f"Category renamed to {data.new_name}!"}

@app.delete("/api/categories/{category_name}")
def delete_category(category_name: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM channels WHERE category = ?', (category_name,))
    conn.commit()
    conn.close()
    return {"message": f"Category '{category_name}' and its channels deleted!"}

@app.post("/api/login")
def login(data: LoginData):
    if data.password == "admin123":
        return {"success": True, "message": "Login successful"}
    else:
        raise HTTPException(status_code=401, detail="Invalid password")

@app.post("/api/upload-m3u")
async def upload_m3u(file: UploadFile = File(...)):
    content = await file.read()
    content_str = content.decode("utf-8", errors="ignore")
    lines = content_str.splitlines()

    conn = get_db_connection()
    cursor = conn.cursor()

    current_name = "Unknown Channel"
    current_category = "General"

    for line in lines:
        line = line.strip()
        if line.startswith("#EXTINF"):
            name_match = re.search(r',(.*)$', line)
            if name_match:
                current_name = name_match.group(1).strip()
            
            # tvg-group বা group-title দুটোই স্ক্যান করবে
            cat_match = re.search(r'(?:group-title|tvg-group)="([^"]+)"', line, re.IGNORECASE)
            if cat_match:
                current_category = cat_match.group(1).strip()
                
        elif line.startswith("http"):
            cursor.execute('INSERT INTO channels (name, category, url) VALUES (?, ?, ?)',
                           (current_name, current_category, line))
            current_name = "Unknown Channel"
            current_category = "General"

    conn.commit()
    conn.close()
    return {"message": "Playlist uploaded and channels extracted successfully!"}