# check_features.py - شغّله على السيرفر بتاعك قبل تشغيل البوت للتأكد إن كل مصدر شغال:
#     python check_features.py
import asyncio
import aiohttp

from config import RADIO_URL


async def main():
    from data import sira_api as api
    print("== السيرة النبوية (إسلام ويب) ==")
    items, pages = await api.get_category_page(141, 1)
    print(f"قسم 'من المولد إلى البعثة': {len(items)} مقال، {pages} صفحة")
    for it in items[:3]:
        print("  -", it["id"], it["title"])
    if items:
        art = await api.get_article(items[0]["id"])
        if art:
            print(f"المقال: {art['title']} | {len(art['text'])} حرف | {len(art['pages'])} صفحة")
            print("بداية النص:", art["text"][:150].replace("\n", " "))
        else:
            print("❌ مقدرتش أقرأ المقال")
    else:
        print("❌ مقدرتش أجيب قايمة المقالات")

    print("\n== خطب الشعراوي (يوتيوب) ==")
    try:
        from handlers.sharawi_handler import get_videos
        vids = await get_videos(force=True)
        print(f"عدد الفيديوهات: {len(vids)}")
        for v in vids[:3]:
            print("  -", v["id"], v["title"])
    except Exception as e:
        print("❌ خطأ:", e)

    print("\n== الإذاعة ==")
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as s:
            async with s.get(RADIO_URL) as r:
                print("HTTP", r.status, r.headers.get("Content-Type"))
    except Exception as e:
        print("❌ خطأ:", e)


if __name__ == "__main__":
    asyncio.run(main())
