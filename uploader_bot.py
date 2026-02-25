import os
import re
import time
import threading
import sys
from flask import Flask, jsonify
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters
from pymongo import MongoClient
from dotenv import load_dotenv

# Force output to show up in Render logs immediately
sys.stdout.reconfigure(line_buffering=True)
load_dotenv()

# --- DATABASE SETUP ---
MONGO_URI = os.getenv("NEW_DB_MONGO_URI")
client = MongoClient(MONGO_URI)
db = client.grandline_live_news
articles_col = db.articles

# --- WEB SERVER (The Antenna for your Website) ---
app = Flask(__name__)

@app.route('/')
def health_check():
    return "✅ Bridge API is Online"

@app.route('/api/news')
def get_news():
    try:
        articles = list(articles_col.find({}, {"_id": 0}).sort("timestamp", -1))
        response = jsonify(articles)
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response
    except Exception as e:
        print(f"❌ API Error: {e}")
        return jsonify([])

def run_flask():
    # Render assigns a port dynamically. If it can't find one, it defaults to 10000.
    port = int(os.environ.get("PORT", 10000))
    print(f"📡 Starting Flask API on port {port}...")
    app.run(host="0.0.0.0", port=port)

# --- TELEGRAM BOT LOGIC ---
def parse_telegram_message(text):
    try:
        title = re.search(r"TITLE: (.*)", text).group(1).strip()
        image = re.search(r"IMAGE: (.*)", text).group(1).strip()
        content = re.search(r"CONTENT: (.*)---END_DATA---", text, re.DOTALL).group(1).strip()
        safe_id = "".join(x for x in title if x.isalnum())[:20]
        return {
            "_id": safe_id,
            "id": safe_id,
            "title": title,
            "imageUrl": image,
            "full_content": content,
            "excerpt": content[:150] + "...",
            "category": "Breaking",
            "date": time.strftime("%b %d, %Y"),
            "timestamp": time.time()
        }
    except Exception as e:
        print(f"⚠️ Parsing failed: {e}")
        return None

async def catch_and_upload(update: Update, context):
    text = update.message.text
    if text and "---NEW_ARTICLE_DATA---" in text:
        data = parse_telegram_message(text)
        if data:
            articles_col.update_one({"_id": data["_id"]}, {"$set": data}, upsert=True)
            await update.message.reply_text(f"✅ Bridge: '{data['title']}' is now LIVE!")

if __name__ == '__main__':
    print("🚀 Initializing Bridge Bot...")
    
    # 1. Start Flask in a separate thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # 2. Start the Telegram Bot
    token = os.getenv("UPLOADER_BOT_TOKEN")
    if not token:
        print("❌ CRITICAL: UPLOADER_BOT_TOKEN is missing!")
        sys.exit(1)

    bot_app = ApplicationBuilder().token(token).build()
    bot_app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), catch_and_upload))
    
    print("🤖 Telegram Polling Started...")
    bot_app.run_polling()
