from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor
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

class ChannelUpdate(BaseModel):
    name: str
    category: str
    url: str

class LoginData(BaseModel):
    password: str

class CategoryRename(BaseModel):
    old_name: str
    new_name: str

# আপনার Neon.tech ক্লাউড ডেটাবেসের লিংক
DATABASE_URL = "postgresql://neondb_owner:npg_uvE9H6rAMzUx@ep-restless-violet-atmm6jvw.c-9.us-east-1.aws.neon.tech/neondb?sslmode=require"

def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    # SQLite এর AUTOINCREMENT এর বদলে PostgreSQL এ SERIAL ব্যবহার হয়
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS channels (
            id SERIAL PRIMARY KEY,
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
    return {"message": "Welcome to Sports IPTV API - Connected to Cloud DB!"}

@app.get("/api/channels")
def get_channels():
    conn = get_db_connection()
    # ডেটা ডিকশনারি হিসেবে পাওয়ার জন্য RealDictCursor ব্যবহার করা হলো
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute('SELECT * FROM channels ORDER BY id DESC')
    channels = cursor.fetchall()
    conn.close()
    return channels

@app.post("/api/channels")
def add_channel(channel: ChannelCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    # PostgreSQL এ '?' এর বদলে '%s' ব্যবহার হয়
    cursor.execute('INSERT INTO channels (name, category, url) VALUES (%s, %s, %s)', 
                   (channel.name, channel.category, channel.url))
    conn.commit()
    conn.close()
    return {"message": "Channel added successfully!"}

@app.delete("/api/channels/{channel_id}")
def delete_channel(channel_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM channels WHERE id = %s', (channel_id,))
    conn.commit()
    conn.close()
    return {"message": "Channel deleted successfully!"}

@app.put("/api/channels/{channel_id}")
def update_channel(channel_id: int, channel: ChannelUpdate):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE channels SET name = %s, category = %s, url = %s WHERE id = %s', 
                   (channel.name, channel.category, channel.url, channel_id))
    conn.commit()
    conn.close()
    return {"message": "Channel updated successfully!"}

@app.delete("/api/channels/all/delete")
def delete_all_channels():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM channels')
    conn.commit()
    conn.close()
    return {"message": "All channels deleted successfully!"}

@app.put("/api/categories")
def rename_category(data: CategoryRename):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE channels SET category = %s WHERE category = %s', (data.new_name, data.old_name))
    conn.commit()
    conn.close()
    return {"message": f"Category renamed to {data.new_name}!"}

@app.delete("/api/categories/{category_name}")
def delete_category(category_name: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM channels WHERE category = %s', (category_name,))
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
            
            cat_match = re.search(r'(?:group-title|tvg-group)="([^"]+)"', line, re.IGNORECASE)
            if cat_match:
                current_category = cat_match.group(1).strip()
                
        elif line.startswith("http"):
            cursor.execute('INSERT INTO channels (name, category, url) VALUES (%s, %s, %s)',
                           (current_name, current_category, line))
            current_name = "Unknown Channel"
            current_category = "General"

    conn.commit()
    conn.close()
    return {"message": "Playlist uploaded and channels extracted successfully!"}