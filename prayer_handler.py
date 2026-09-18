import aiohttp
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from config import DEFAULT_CITY, DEFAULT_COUNTRY, PRAYER_REMINDER_MINUTES

PRAYER_API_BASE = "http://api.aladhan.com/v1/timingsByCity"

async def get_prayer_times(city: str = DEFAULT_CITY, country: str = DEFAULT_COUNTRY):
    """جلب مواقيت الصلاة من API"""
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{PRAYER_API_BASE}?city={city}&country={country}&method=5"
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data["code"] == 200:
                        timings = data["data"]["timings"]
                        return {
                            "Fajr": timings["Fajr"],
                            "Dhuhr": timings["Dhuhr"],
                            "Asr": timings["Asr"],
                            "Maghrib": timings["Maghrib"],
                            "Isha": timings["Isha"]
                        }
    except Exception as e:
        print(f"Error fetching prayer times: {e}")
    return None

async def set_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تحديد مدينة المستخدم - /setcity Cairo, Egypt"""
    try:
        args = context.args
        if len(args) >= 2:
            city = args[0]
            country = args[1]
            context.user_data["city"] = city
            context.user_data["country"] = country
            await update.message.reply_text(f"✅ تم تحديد مدينتك: {city}, {country}")
        else:
            await update.message.reply_text("📌 استخدم: /setcity المدينة, البلد\nمثال: /setcity Cairo, Egypt")
    except Exception as e:
        await update.message.reply_text("❌ حدث خطأ، حاول مرة أخرى")