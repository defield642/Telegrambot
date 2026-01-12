import hashlib
import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# CONFIG
BOT_TOKEN = "7905376378:AAFc1PRPMp-lvdSFs3dX5uT3k69yf6WiPTs"
CHECK_INTERVAL = 120
CHAT_IDS = ["8422059495"]  # you can add multiple if you want
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
PRIORITY_KEYWORDS = ["here we go", "official", "confirmed"]

sent_hashes = set()

def hash_text(text):
    return hashlib.md5(text.encode()).hexdigest()

def fetch_tweets(url):
    try:
        resp = requests.get(url, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        tweets = soup.find_all("div", class_="tweet-content")
        return tweets[:7]
    except Exception as e:
        print("Error fetching tweets:", e)
        return []

async def check_news_job(context: ContextTypes.DEFAULT_TYPE):
    global sent_hashes
    for source_name, url in SOURCES.items():
        tweets = fetch_tweets(url)
        for tweet in tweets:
            text = tweet.get_text(" ", strip=True).lower()
            if any(k in text for k in KEYWORDS):
                h = hash_text(text)
                if h not in sent_hashes:
                    priority = any(pk in text for pk in PRIORITY_KEYWORDS)
                    emoji = "🚨🚨" if priority else "⚽"
                    title = "PRIORITY ALERT" if priority else "MAN UNITED NEWS"
                    message = f"{emoji} {title}\n\n📰 Source: {source_name}\n\n{tweet.get_text(strip=True)}"
                    for chat_id in CHAT_IDS:
                        try:
                            await context.bot.send_message(chat_id=chat_id, text=message)
                            print(f"Sent alert from {source_name}")
                        except Exception as e:
                            print("Error sending message:", e)
                    sent_hashes.add(h)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hello! Welcome to your Man Utd News Bot.\n"
        "You will now receive instant alerts for all Manchester United news."
    )

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.job_queue.run_repeating(check_news_job, interval=CHECK_INTERVAL, first=5)
    print("✅ Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
