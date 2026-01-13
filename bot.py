import asyncio
import hashlib
import io
import os
import requests
import json
import pyttsx3
from bs4 import BeautifulSoup
from gtts import gTTS
from types import SimpleNamespace
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# CONFIG - use environment variables for sensitive data
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")
CHECK_INTERVAL = 120  # seconds

SOURCES = {
    "Fabrizio Romano": "https://nitter.net/FabrizioRomano",
    "Sky Sports": "https://nitter.net/SkySportsPL",
    "BBC Sport": "https://nitter.net/BBCSport",
    "ESPN FC": "https://nitter.net/ESPNFC",
    "The Athletic": "https://nitter.net/theathleticuk",
    "Goal.com": "https://nitter.net/goal"
}

KEYWORDS = [
    "man united", "manchester united", "mufc",
    "here we go", "transfer", "signing",
    "interim", "manager", "caretaker",
    "derby", "man city", "pep", "ten hag",
    "carrick", "solskjaer"
]

PRIORITY_KEYWORDS = [
    "here we go",
    "official",
    "confirmed"
]

sent_hashes = set()

# HELPER FUNCTIONS
def hash_text(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()

def fetch_tweets(url: str):
    """
    Fetch news from multiple sources using NewsAPI and web scraping.
    Returns a list of news items/tweets.
    """
    try:
        # Try NewsAPI for general football news
        if "goal" in url or "sky" in url or "bbc" in url or "espn" in url:
            api_key = "9554871c4a5d4fd9ad67a4a042d68c73"
            search_query = "manchester united transfer"
            api_url = f"https://newsapi.org/v2/everything?q={search_query}&sortBy=publishedAt&apiKey={api_key}"
            
            resp = requests.get(api_url, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                articles = data.get("articles", [])
                return articles[:7]
        
        # Fallback: Try direct website scraping
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        resp = requests.get(url, timeout=15, headers=headers)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Try multiple possible selectors
        tweets = soup.find_all("article")
        if not tweets:
            tweets = soup.find_all("div", class_="tweet")
        if not tweets:
            tweets = soup.find_all("div", class_="tweet-content")
        if not tweets:
            tweets = soup.find_all("p", class_="status-content-text")
        
        return tweets[:7]
    except requests.exceptions.RequestException as e:
        print(f"Network error fetching from {url}: {e}")
        return []
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        return []
    except Exception as e:
        print(f"Error fetching/parsing: {e}")
        return []

async def send_voice_alert(bot, chat_id, text: str):
    """
    Generate professional football presenter voice alert using gTTS.
    Prioritizes gTTS for reliability in cloud environments like Replit/Railway.
    """
    try:
        # Limit text to 300 chars to keep audio short
        if len(text) > 300:
            text = text[:297] + "..."
        
        # Clean text
        text = text.replace("\n", " ").replace("\r", " ")
        
        print(f"🎙️  Generating presenter voice alert: {text[:50]}...")
        
        # Use gTTS for reliable voice generation without system dependencies
        tts = gTTS(text=text, lang='en', slow=False)
        bio = io.BytesIO()
        tts.write_to_fp(bio)
        bio.seek(0)
        
        print(f"📤 Sending voice alert to {chat_id}...")
        await bot.send_audio(chat_id=chat_id, audio=bio, filename="alert.mp3")
        print("✅ Voice alert sent successfully")
            
    except Exception as e:
        print(f"❌ Error sending voice alert: {e}")

async def test_voice_alert(bot, chat_id):
    """
    Test function to send a sample voice alert.
    Useful for verifying voice alert functionality.
    """
    test_message = "Testing voice alert. This is a sample Manchester United news alert."
    print("\n🔔 Testing voice alert functionality...")
    await send_voice_alert(bot, chat_id, test_message)
    print("✅ Voice alert test complete\n")

async def verify_news_fetch():
    """
    Test function to verify if news can be fetched from sources.
    Returns True if at least one source has tweets, False otherwise.
    """
    print("\\n🔍 Verifying news fetch capability...")
    for source_name, url in SOURCES.items():
        tweets = fetch_tweets(url)
        if tweets:
            print(f"✅ {source_name}: Successfully fetched {len(tweets)} tweets")
            return True
        else:
            print(f"❌ {source_name}: No tweets fetched")
    print("⚠️  Could not fetch news from any source.\\n")
    return False

from types import SimpleNamespace

# JOB FUNCTION
async def check_news_job(context: ContextTypes.DEFAULT_TYPE):
    global sent_hashes
    for source_name, url in SOURCES.items():
        tweets = fetch_tweets(url)
        for tweet in tweets:
            # Handle both BeautifulSoup objects (with get_text) and NewsAPI dictionaries
            if isinstance(tweet, dict):
                # NewsAPI article format
                text = (tweet.get("title", "") + " " + tweet.get("description", "")).lower()
                article_text = f"{tweet.get('title', '')}\n{tweet.get('description', '')}"
                image_url = tweet.get("urlToImage", "")
            else:
                # BeautifulSoup object
                text = tweet.get_text(" ", strip=True).lower()
                article_text = tweet.get_text(strip=True)
                image_url = ""
            
            if any(k in text for k in KEYWORDS):
                h = hash_text(text)
                if h not in sent_hashes:
                    priority = any(pk in text for pk in PRIORITY_KEYWORDS)
                    emoji = "🚨🚨" if priority else "⚽"
                    title = "*PRIORITY ALERT*" if priority else "*MAN UNITED NEWS*"
                    message = f"{emoji} {title}\n\n📰 *Source* {source_name}\n\n{article_text[:300]}"
                    try:
                        # Send message with formatting
                        await context.bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="Markdown")
                        
                        # Send image if available
                        if image_url:
                            try:
                                await context.bot.send_photo(chat_id=CHAT_ID, photo=image_url)
                            except Exception as img_err:
                                print(f"Could not send image: {img_err}")
                        
                        # Send voice alert
                        voice_snippet = f"{('Priority' if priority else 'Update')} from {source_name}: {article_text[:200]}"
                        await send_voice_alert(context.bot, CHAT_ID, voice_snippet)
                        sent_hashes.add(h)
                        print(f"✅ Sent alert and voice from {source_name}")
                    except Exception as e:
                        print("Error sending message:", e)


# Background news loop for environments without JobQueue extras
async def news_loop(app):
    await asyncio.sleep(5)
    while True:
        try:
            # Re-fetch the current loop to avoid issues with closed loops
            await check_news_job(SimpleNamespace(bot=app.bot))
        except Exception as e:
            print("Error in news loop:", e)
        # Sleep for CHECK_INTERVAL (120 seconds) as defined in config
        await asyncio.sleep(CHECK_INTERVAL)

async def test_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /test_voice command to test voice alert."""
    await update.message.reply_text("🔊 Testing voice alert...")
    await test_voice_alert(context.bot, update.effective_chat.id)

# /start COMMAND
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔴 Welcome to Manchester United Pro News\n\n"
        "You're subscribed to real time Man Utd updates for transfers, confirmations, and breaking stories ⚽\n\n"
        "🔔 Professional voice alerts enabled\n\n"
        "Commands:\n"
        "/start  Welcome\n"
        "/test_voice  Test voice"
    )

# MAIN
def main():
    if not BOT_TOKEN:
        print("ERROR: BOT_TOKEN environment variable is not set.")
        print("Please set the BOT_TOKEN secret in your Replit environment.")
        return
    
    if not CHAT_ID:
        print("WARNING: CHAT_ID environment variable is not set.")
        print("The bot will run but automatic news updates won't be sent.")
    
    # Build bot app
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Add command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("test_voice", test_voice))

    # Schedule news check every CHECK_INTERVAL seconds (internal loop)
    try:
        # Preferred: schedule with Application's task handler
        app.create_task(news_loop(app))
    except Exception:
        # Fallback: schedule on current running loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(news_loop(app))
        else:
            asyncio.run(news_loop(app))

    print("Bot is running. Press /start in Telegram to get a welcome message.")
    print("Commands available: /start, /test_voice")
    app.run_polling()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        print("Testing news fetch capability...")
        asyncio.run(verify_news_fetch())
    else:
        main()
