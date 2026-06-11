from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3

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

# --- API Endpoints ---

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

# চ্যানেল ডিলিট করার API
@app.delete("/api/channels/{channel_id}")
def delete_channel(channel_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM channels WHERE id = ?', (channel_id,))
    conn.commit()
    conn.close()
    return {"message": "Channel deleted successfully!"}

# লগইন চেক করার API
@app.post("/api/login")
def login(data: LoginData):
    if data.password == "admin123":  # অ্যাডমিন পাসওয়ার্ড
        return {"success": True, "message": "Login successful"}
    else:
        raise HTTPException(status_code=401, detail="Invalid password")