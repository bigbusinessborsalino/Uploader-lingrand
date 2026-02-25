import os
import re
import time
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# --- NEW DATABASE SETUP ---
# Use a DIFFERENT Mongo URI or a different Database Name here to keep it clean!
MONGO_URI = os.getenv("NEW_DB_MONGO_URI") 
client = MongoClient(MONGO_URI)
db = client.grandline_live_news  # New Database
articles_col = db.articles       # New Collection

def parse_telegram_message(text):
    """Extracts data from the AI Writer's tagged format."""
    try:
        title = re.search(r"TITLE: (.*)", text).group(1).strip()
        image = re.search(r"IMAGE: (.*)", text).group(1).strip()
        # Grabs everything between CONTENT: and the end tag
        content = re.search(r"CONTENT: (.*)---END_DATA---", text, re.DOTALL).group(1).strip()
        
        # Create a safe ID for the website URL
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
        print(f"Parsing error: {e}")
        return None

async def catch_and_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Listens for the specific tag and uploads to the new DB."""
    text = update.message.text
    if not text or "---NEW_ARTICLE_DATA---" not in text:
        return

    data = parse_telegram_message(text)
    if data:
        # Save to the new database
        articles_col.update_one({"_id": data["_id"]}, {"$set": data}, upsert=True)
        await update.message.reply_text(f"✅ Website Bridge: '{data['title']}' is now LIVE on the domain!")

if __name__ == '__main__':
    # Use a DIFFERENT bot token for this one so they don't conflict!
    token = os.getenv("UPLOADER_BOT_TOKEN")
    app = ApplicationBuilder().token(token).build()
    
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), catch_and_upload))
    
    print("🚀 Bridge Bot is listening for AI articles...")
    app.run_polling()
