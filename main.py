web: python app.py
import feedparser
import requests
import time
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL = os.getenv("CHANNEL")

RSS_FEED = "https://feeds.bbci.co.uk/arabic/rss.xml"

sent = set()

def send(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={
        "chat_id": CHANNEL,
        "text": text
    })

print("Bot started...")

while True:
    feed = feedparser.parse(RSS_FEED)

    for entry in feed.entries:
        if entry.link in sent:
            continue

        sent.add(entry.link)

        msg = f"📰 {entry.title}\n\n🔗 {entry.link}"
        send(msg)

    time.sleep(300)
