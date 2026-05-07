import os
import json
import hashlib
import asyncio
import feedparser
from datetime import datetime, timezone
import re
import random
from telegram import Bot
from telegram.ext import Application

# ========== الإعدادات ==========
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL = os.environ.get("CHANNEL")

# ========== المصادر (28 مصدر) ==========
SOURCES = {
    "الجزيرة": "https://www.aljazeera.net/xml/rss.xml",
    "BBC عربي": "https://feeds.bbci.co.uk/arabic/news/rss.xml",
    "CNN": "https://arabic.cnn.com/rss/me-middle-east.xml",
    "روسيا اليوم": "https://arabic.rt.com/rss/news.xml",
    "سكاي نيوز": "https://www.skynewsarabia.com/web/xml/rss2.xml",
    "فرانس 24": "https://www.france24.com/ar/rss",
    "العربية": "https://www.alarabiya.net/.rss/",
    "الشرق للأخبار": "https://rssfeeds.al-sharq.com/rss.xml",
    "الغد": "https://www.alghad.tv/rss/feed.xml",
    "المصدر": "https://www.almasdar.com/feed/",
    "الخليج": "https://www.alkhaleej.ae/rss",
    "وكالة الأناضول": "https://www.aa.com.tr/ar/rss.xml",
    "وكالة الأنباء السعودية (واس)": "https://www.spa.gov.sa/rss.xml",
    "وكالة الأنباء الإماراتية (وام)": "https://www.wam.ae/ar/rss.xml",
    "الجزيرة مباشر": "https://www.aljazeeramubasher.net/rss",
    "TRT عربي": "https://www.trtarabi.com/rss/",
    "الميادين": "https://www.almayadeen.net/rss",
    "صحيفة القدس": "https://www.alquds.co.uk/feed/",
    "الحدث": "https://www.alhadath.net/.rss/",
    "المشهد": "https://www.almashhad.com/.rss/",
    "إرم نيوز": "https://www.eremnews.com/rss",
    "عربي 21": "https://arabi21.com/rss",
    "المصري اليوم": "https://www.almasryalyoum.com/rss/",
    "القدس العربي": "https://www.alqudsalarabi.com/rss",
    "الشرق الأوسط": "https://aawsat.com/feed",
    "البيان": "https://www.albayan.ae/rss/",
    "الشرق": "https://www.al-sharq.com/rss",
    "الرأي": "https://www.alraimedia.com/rss",
}

# ========== قاعدة بيانات التكرار ==========
DB_FILE = "news_db.json"

def load_db():
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            c = f.read().strip()
            return json.loads(c) if c else {"hashes": [], "ids": []}
    except:
        return {"hashes": [], "ids": []}

def save_db(db):
    if len(db["hashes"]) > 3000:
        db["hashes"] = db["hashes"][-3000:]
        db["ids"] = db["ids"][-3000:]
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False)

def is_new(news_id, db):
    h = hashlib.md5(news_id.encode()).hexdigest()
    if h in db["hashes"] or news_id in db["ids"]:
        return False
    db["hashes"].append(h)
    db["ids"].append(news_id)
    return True

# ========== تنظيف النص ==========
def clean(txt):
    return re.sub(r'<[^>]+>', '', txt).strip()

# ========== تصنيف الأهمية ==========
URGENT_KEYWORDS = ["عاجل", "انفجار", "حرب", "قصف", "غارة", "هجوم", "زلزال", "إعصار", "اغتيال"]
IMPORTANT_KEYWORDS = ["رئيس", "وزير", "انتخابات", "اقتصاد", "نفط", "دولار", "ذهب", "أسهم", "بورصة", "أمم", "قمة", "معاهدة", "استقالة"]

def classify(title, summary):
    text = f"{title} {summary}"
    imp = 5
    urg = "عادي"
    for w in URGENT_KEYWORDS:
        if w in text:
            imp = 9
            urg = "عاجل"
            break
    if urg != "عاجل":
        for w in IMPORTANT_KEYWORDS:
            if w in text:
                imp = 7
                urg = "مهم"
                break
    sm = summary[:200] + "..." if len(summary) > 200 else summary
    return imp, sm, "", urg

# ========== جلب الأخبار ==========
def fetch_all():
    db = load_db()
    news_list = []
    for src, url in SOURCES.items():
        try:
            feed = feedparser.parse(url)
            for e in feed.entries[:1]:
                title = clean(e.title)
                link = e.link
                summary = clean(e.summary[:350]) if hasattr(e, "summary") else ""
                news_id = f"{link}"
                if is_new(news_id, db):
                    news_list.append({"source": src, "title": title, "link": link, "summary": summary})
        except Exception as ex:
            print(f"⚠️ {src}: {ex}")
    save_db(db)
    return news_list

# ========== تنسيق ==========
FLAGS = {
    "الجزيرة": "🇶🇦", "BBC عربي": "🇬🇧", "CNN": "🇺🇸", "روسيا اليوم": "🇷🇺", "سكاي نيوز": "🇦🇪",
    "فرانس 24": "🇫🇷", "العربية": "🇸🇦", "الشرق للأخبار": "🇶🇦", "الغد": "🇯🇴", "المصدر": "🇾🇪",
    "الخليج": "🇦🇪", "وكالة الأناضول": "🇹🇷", "TRT عربي": "🇹🇷", "الميادين": "🇱🇧",
    "صحيفة القدس": "🇵🇸", "الحدث": "🇸🇦", "المشهد": "🇪🇬", "إرم نيوز": "🇸🇩",
    "عربي 21": "🇬🇧", "المصري اليوم": "🇪🇬", "القدس العربي": "🇬🇧", "الشرق الأوسط": "🇬🇧",
    "البيان": "🇦🇪", "الشرق": "🇶🇦", "الرأي": "🇰🇼", "وكالة الأنباء السعودية (واس)": "🇸🇦",
    "وكالة الأنباء الإماراتية (وام)": "🇦🇪", "الجزيرة مباشر": "🇶🇦"
}

def fmt(news, imp, sm, impact, urg):
    flag = FLAGS.get(news["source"], "🌐")
    if urg == "عاجل":
        hdr = f"🚨{flag} #عاجل {news['source']}:"
    elif urg == "مهم":
        hdr = f"📌{flag} {news['source']}:"
    else:
        hdr = f"📰{flag} {news['source']}:"
    return f"""{hdr}
{news['title']}

{sm[:200]}
🔗 [المصدر]({news['link']})"""

# ========== مهمة النشر مع الرد على آخر خبر ==========
async def job(context):
    print("🔄 جلب الأخبار...")
    all_news = fetch_all()
    if not all_news:
        print("لا أخبار جديدة")
        return

    urgent, important, normal = [], [], []
    for n in all_news:
        imp, sm, impact, urg = classify(n["title"], n["summary"])
        if urg == "عاجل":
            urgent.append((n, imp, sm, impact, urg))
        elif urg == "مهم" or imp >= 7:
            important.append((n, imp, sm, impact, urg))
        else:
            normal.append((n, imp, sm, impact, urg))

    to_pub = urgent + important[:3] + normal[:2]
    random.shuffle(to_pub)

    # جلب آخر رسالة في القناة
    try:
        # إزالة @ من اسم القناة إذا وجد
        chat_id = CHANNEL.replace("@", "")
        updates = await context.bot.get_updates(offset=-1, limit=1)
        last_msg_id = None
        if updates:
            last_msg_id = updates[-1].message.message_id
    except:
        last_msg_id = None

    cnt = 0
    for item in to_pub:
        n, imp, sm, impact, urg = item
        try:
            txt = fmt(n, imp, sm, impact, urg)
            # نشر كرسالة جديدة
            msg = await context.bot.send_message(
                CHANNEL,
                txt,
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
            
            # بعد 5 ثوان، رد على نفس الرسالة بتحليل بسيط
            await asyncio.sleep(5)
            await context.bot.send_message(
                CHANNEL,
                f"💡 تحليل سريع: {n['summary'][:150]}...",
                reply_to_message_id=msg.message_id
            )
            
            cnt += 1
            print(f"✅ {n['source']}: {n['title'][:50]}")
            await asyncio.sleep(2)
        except Exception as e:
            print(f"❌ {e}")

    print(f"📢 {cnt} خبر")

# ========== بدء ==========
def main():
    if not BOT_TOKEN or not CHANNEL:
        print("❌ المتغيرات ناقصة")
        return
    app = Application.builder().token(BOT_TOKEN).build()
    app.job_queue.run_repeating(job, interval=600, first=10)
    print("🚀 Bot started (رد تلقائي على كل خبر)...")
    app.run_polling()

if __name__ == "__main__":
    main()
