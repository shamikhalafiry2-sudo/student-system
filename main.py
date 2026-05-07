import os
import json
import feedparser
import requests
from telegram import Bot
from telegram.ext import Application
from datetime import datetime, timezone

# ========== الإعدادات ==========
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL = os.environ.get("CHANNEL")

# ========== منع تكرار الأخبار ==========
posted_news = set()

def load_posted():
    global posted_news
    try:
        with open("posted.json", "r") as f:
            posted_news = set(json.load(f))
    except:
        posted_news = set()

def save_posted():
    with open("posted.json", "w") as f:
        json.dump(list(posted_news), f)

# ========== جلب الأخبار من RSS ==========
def fetch_news():
    feeds = {
        "سياسة": [
            "https://feeds.bbci.co.uk/arabic/news/rss.xml",
            "https://www.aljazeera.net/xml/rss.xml"
        ],
        "تقنية": [
            "https://feeds.feedburner.com/TechCrunch/arabic"
        ]
    }

    all_news = []
    for category, urls in feeds.items():
        for url in urls:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:3]:  # 3 أخبار من كل مصدر
                    news_id = entry.link or entry.title
                    if news_id not in posted_news:
                        posted_news.add(news_id)
                        all_news.append({
                            "category": category,
                            "title": entry.title,
                            "link": entry.link,
                            "summary": entry.summary[:200] if hasattr(entry, "summary") else ""
                        })
            except Exception as e:
                print(f"خطأ في جلب {url}: {e}")
    return all_news

# ========== تنسيق الخبر ==========
def format_news(news):
    emojis = {"سياسة": "🔴", "تقنية": "💻", "اقتصاد": "💰", "رياضة": "⚽"}
    emoji = emojis.get(news["category"], "📰")

    # إزالة HTML tags بسيطة
    import re
    summary = re.sub(r'<[^>]+>', '', news["summary"])
    summary = summary[:150] + "..." if len(summary) > 150 else summary

    text = f"""{emoji} **{news['category']}**
📌 {news['title']}

{summary}

🔗 [المصدر]({news['link']})"""
    return text

# ========== المهمة الرئيسية ==========
async def job_publish(context):
    load_posted()
    news_list = fetch_news()
    bot = context.bot

    if not news_list:
        print("لا توجد أخبار جديدة")
        return

    for news in news_list:
        try:
            text = format_news(news)
            await bot.send_message(chat_id=CHANNEL, text=text, parse_mode="Markdown", disable_web_page_preview=True)
            print(f"تم نشر: {news['title'][:50]}")
        except Exception as e:
            print(f"خطأ في النشر: {e}")

    save_posted()
    print(f"تم نشر {len(news_list)} خبر جديد")

# ========== بدء البوت ==========
def main():
    if not BOT_TOKEN or not CHANNEL:
        print("خطأ: تأكد من تعيين BOT_TOKEN و CHANNEL في Environment Variables")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    # تشغيل كل 10 دقائق
    app.job_queue.run_repeating(job_publish, interval=600, first=10)

    print("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
