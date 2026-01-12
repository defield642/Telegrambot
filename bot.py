import asyncio
import requests
import hashlib
from bs4 import BeautifulSoup
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ========= CONFIG =========
BOT_TOKEN = "7905376378:AAFc1PRPMp-lvdSFs3dX5uT3k69yf6WiPTs"
CHAT_ID = "8422059495"

CHECK_INTERVAL = 120  # seconds

SOURCES = {
    "Fabrizio Romano": "https://nitter.net/FabrizioRomano",
    "Man United": "https://nitter.net/ManUtd",
    "Sky Sports": "https://nitter.net/SkySportsPL",
    "BBC Sport": "https://nitter.net/BBCSport"
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

bot = Bot(token=BOT_TOKEN)
sent_hashes = set()

# ========= FUNCTIONS =========
def hash_text(text):
    return hashlib.md5(text.encode()).hexdigest()

def fetch_tweets(source_name, url):
    try:
        response = requests.get(url, timeout=15)
        soup = BeautifulSoup(response.text, "html.parser")
        tweets = soup.find_all("div", class_="tweet-content")
        return tweets[:7]
    except Exception as e:
        print(f"Error fetching tweets from {source_name}: {e}")
        return []

async def check_news_loop():
    while True:
        for source, url in SOURCES.items():
            tweets = fetch_tweets(source, url)
            for tweet in tweets:
                text = tweet.get_text(" ", strip=True).lower()
                if any(keyword in text for keyword in KEYWORDS):
                    h = hash_text(text)
                    if h not in sent_hashes:
                        priority = any(pk in text for pk in PRIORITY_KEYWORDS)
                        emoji = "🚨🚨" if priority else "⚽"
                        title = "PRIORITY ALERT" if priority else "MAN UNITED NEWS"
                        message = f"{emoji} {title}\n\n📰 Source: {source}\n\n{tweet.get_text(strip=True)}"
                        try:
                            await bot.send_message(chat_id=CHAT_ID, text=message)
                            print(f"Sent alert from {source}")
                            sent_hashes.add(h)
                        except Exception as e:
                            print(f"Error sending message: {e}")
        await asyncio.sleep(CHECK_INTERVAL)

# ========= COMMANDS =========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hello! Welcome to your Man Utd News Bot.\n"
        "You will now receive instant alerts for all Manchester United news.\n"
        "⚽ Transfers, manager updates, derby news, and more!"
    )

# ========= MAIN =========
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))

    # Start background news loop
    app.job_queue.run_repeating(lambda _: asyncio.create_task(check_news_loop()), interval=CHECK_INTERVAL, first=1)

    print("✅ Bot is running. Press /start in Telegram to get a welcome message.")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
