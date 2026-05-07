import os
import json
import hashlib
import feedparser
import google.generativeai as genai
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application
from datetime import datetime, timezone
import re
import random

# ========== الإعدادات ==========
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL = os.environ.get("CHANNEL")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyAj3swGk1X_9EYVjFC5pHMfCjZZR8YNF1s")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

# ========== المصادر ==========
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
}

# ========== قاعدة البيانات ==========
def load_db():
    try:
        with open("news_db.json", "r") as f:
            return json.load(f)
    except:
        return {"hashes": [], "urls": []}

def save_db(db):
    with open("news_db.json", "w") as f:
        json.dump(db, f)

def is_duplicate(title, url, db):
    h = hashlib.md5(title[:120].encode()).hexdigest()
    if h in db["hashes"] or url in db["urls"]:
        return True
    db["hashes"].append(h)
    db["urls"].append(url)
    if len(db["hashes"]) > 800:
        db["hashes"] = db["hashes"][-800:]
        db["urls"] = db["urls"][-800:]
    return False

# ========== تنظيف ==========
def clean(txt):
    return re.sub(r'<[^>]+>', '', txt).strip()

# ========== تحليل AI ==========
def analyze(title, summary):
    prompt = f"""حلل الخبر التالي وأجب بالصيغة التالية فقط:

السطر 1: تقييم الأهمية (رقم 1-10)
السطر 2: ملخص (2-3 أسطر كحد أقصى)
السطر 3: تحليل سريع (سطر أو سطرين)
السطر 4: تصنيف واحد من (عاجل / مهم / عادي)

العنوان: {title}
الوصف: {summary[:400]}

ابدأ:"""
    try:
        resp = model.generate_content(prompt)
        lines = resp.text.strip().split('\n')
        imp = 5; sm = summary[:180]; impa = ""; urg = "عادي"
        for i, line in enumerate(lines):
            line = line.strip()
            if i == 0:
                try: imp = int(re.search(r'\d+', line).group())
                except: pass
            elif i == 1 and line: sm = line
            elif i == 2 and line: impa = line
            elif i == 3:
                if "عاجل" in line: urg = "عاجل"
                elif "مهم" in line: urg = "مهم"
        return imp, sm, impa, urg
    except:
        return 5, summary[:180], "", "عادي"

# ========== جلب الأخبار ==========
def fetch_all():
    db = load_db()
    news_list = []

    for source_name, url in SOURCES.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:2]:
                title = clean(entry.title)
                link = entry.link
                summary = clean(entry.summary[:300]) if hasattr(entry, "summary") else ""
                
                if not is_duplicate(title, link, db):
                    news_list.append({
                        "source": source_name,
                        "title": title,
                        "link": link,
                        "summary": summary
                    })
        except Exception as e:
            print(f"⚠️ {source_name}: {e}")

    save_db(db)
    return news_list

# ========== تنسيق ==========
def fmt(news, imp, sm, impact, urg):
    flags = {"الجزيرة": "🇶🇦", "BBC عربي": "🇬🇧", "CNN": "🇺🇸", "روسيا اليوم": "🇷🇺",
             "سكاي نيوز": "🇦🇪", "فرانس 24": "🇫🇷", "العربية": "🇸🇦", "الشرق للأخبار": "🇶🇦",
             "الغد": "🇯🇴", "المصدر": "🇾🇪", "الخليج": "🇦🇪", "وكالة الأناضول": "🇹🇷",
             "وكالة الأنباء السعودية (واس)": "🇸🇦", "وكالة الأنباء الإماراتية (وام)": "🇦🇪",
             "الجزيرة مباشر": "🇶🇦", "TRT عربي": "🇹🇷", "الميادين": "🇱🇧", "صحيفة القدس": "🇵🇸",
             "الحدث": "🇸🇦", "المشهد": "🇪🇬", "إرم نيوز": "🇸🇩", "عربي 21": "🇬🇧",
             "المصري اليوم": "🇪🇬", "القدس العربي": "🇬🇧", "الشرق الأوسط": "🇬🇧",
             "البيان": "🇦🇪", "الشرق": "🇶🇦"}
    flag = flags.get(news["source"], "🌐")
    
    if urg == "عاجل":
        header = f"🚨{flag} #عاجل {news['source']}:"
    elif urg == "مهم":
        header = f"📌{flag} {news['source']}:"
    else:
        header = f"📰{flag} {news['source']}:"

    text = f"""{header}
{news['title']}

{sm[:200]}

{"💡 " + impact[:150] if impact else ""}
🔗 [المصدر]({news['link']})"""
    return text

# ========== مهمة ==========
async def job(context):
    print("🔄 جاري جلب الأخبار من 28 مصدر...")
    all_news = fetch_all()
    if not all_news:
        print("لا توجد أخبار جديدة")
        return

    urgent = []; important = []; normal = []
    for n in all_news:
        imp, sm, impact, urg = analyze(n["title"], n["summary"])
        if urg == "عاجل":
            urgent.append((n, imp, sm, impact, urg))
        elif urg == "مهم" or imp >= 7:
            important.append((n, imp, sm, impact, urg))
        else:
            normal.append((n, imp, sm, impact, urg))

    to_publish = urgent + important[:3] + normal[:2]
    random.shuffle(to_publish)

    count = 0
    for item in to_publish:
        n, imp, sm, impact, urg = item
        try:
            txt = fmt(n, imp, sm, impact, urg)
            # زر التعليق
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("💬 علّق", url=n['link'])]
            ])
            await context.bot.send_message(
                CHANNEL,
                txt,
                parse_mode="Markdown",
                disable_web_page_preview=True,
                reply_markup=keyboard
            )
            count += 1
            print(f"✅ {n['source']}: {n['title'][:50]}")
        except Exception as e:
            print(f"❌ {e}")

    print(f"📢 تم نشر {count} خبر")

# ========== بدء ==========
def main():
    if not BOT_TOKEN or not CHANNEL:
        print("❌ خطأ: المتغيرات غير موجودة")
        return

    app = Application.builder().token(BOT_TOKEN).build()
    app.job_queue.run_repeating(job, interval=900, first=15)
    print("🚀 Bot started with 28 sources + Gemini AI + Comments...")
    app.run_polling()

if __name__ == "__main__":
    main()
