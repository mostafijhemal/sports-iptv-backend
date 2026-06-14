from fastapi import FastAPI, HTTPException, File, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor
import re
import requests
from urllib.parse import urlparse

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

DATABASE_URL = "postgresql://neondb_owner:npg_uvE9H6rAMzUx@ep-restless-violet-atmm6jvw.c-9.us-east-1.aws.neon.tech/neondb?sslmode=require"

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
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

# ==========================================
#  অত্যাধুনিক স্মার্ট আইপিটিভি প্রক্সি ইঞ্জিন
# ==========================================
@app.get("/api/proxy")
def proxy_stream(url: str, request: Request):
    try:
        # মূল স্ট্রিমিং সার্ভারকে ধোঁকা দেওয়ার জন্য হেডার তৈরি
        parsed_url = urlparse(url)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": f"{parsed_url.scheme}://{parsed_url.netloc}/",
            "Origin": f"{parsed_url.scheme}://{parsed_url.netloc}"
        }

        # মূল সার্ভার থেকে ডাটা রিকোয়েস্ট করা
        req = requests.get(url, headers=headers, stream=True, timeout=10)
        content_type = req.headers.get("Content-Type", "")

        # যদি এটি মেইন প্লেলিস্ট (.m3u8) ফাইল হয়, তবে এর ভেতরের সব লিংক প্রক্সির আওতায় নিয়ে আসা
        if "mpegurl" in content_type.lower() or url.split('?')[0].endswith(".m3u8"):
            content = req.text
            base_url = url.rsplit('/', 1)[0] + '/'
            base_proxy_url = str(request.base_url) + "api/proxy?url="
            
            rewritten_lines = []
            for line in content.splitlines():
                line_str = line.strip()
                if line_str and not line_str.startswith("#"):
                    # রিলেটিভ পাথ থাকলে সেটিকে ফুল ইউআরএল করা
                    if not line_str.startswith("http"):
                        line_str = base_url + line_str
                    # ভিডিওর টুকরোগুলোকেও (TS chunks) এই প্রক্সির ভেতর দিয়ে পাঠানো
                    line_str = f"{base_proxy_url}{line_str}"
                    rewritten_lines.append(line_str)
                else:
                    rewritten_lines.append(line)

            return StreamingResponse(
                iter([("\n".join(rewritten_lines)).encode('utf-8')]),
                media_type="application/vnd.apple.mpegurl"
            )

        # ভিডিওর ছোট ছোট টুকরো বা বাইনারি ডাটা (.ts chunks) স্ট্রিম করা
        def generate():
            for chunk in req.iter_content(chunk_size=8192):
                yield chunk
                
        return StreamingResponse(generate(), media_type=content_type)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def read_root():
    return {"message": "Welcome to Sports IPTV API - Connected to Cloud DB with Proxy Enabled!"}

@app.get("/api/channels")
def get_channels():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute('SELECT * FROM channels ORDER BY id DESC')
    channels = cursor.fetchall()
    conn.close()
    return channels

@app.post("/api/channels")
def add_channel(channel: ChannelCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO channels (name, category, url) VALUES (%s, %s, %s)', 
                   (channel.name, channel.category, channel.url))
    conn.commit()
    conn.close()
    return {"message": "Channel added successfully!"}

@app.put("/api/channels/{channel_id}")
def update_channel(channel_id: int, channel: ChannelUpdate):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE channels SET name = %s, category = %s, url = %s WHERE id = %s', 
                   (channel.name, channel.category, channel.url, channel_id))
    conn.commit()
    conn.close()
    return {"message": "Channel updated successfully!"}

@app.delete("/api/channels/{channel_id}")
def delete_channel(channel_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM channels WHERE id = %s', (channel_id,))
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