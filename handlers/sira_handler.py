# handlers/sira_handler.py - السيرة النبوية (إسلام ويب) + قصة اليوم
import os
import json
import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from pyrogram.enums import ButtonStyle
from pyrogram.errors import FloodWait
from pyrogram.types import LinkPreviewOptions

from config import (
    SIRA_TIMEZONE, CACHE_DIR, ISLAMWEB_BASE,
    CUSTOM_EMOJI_QURAN, CUSTOM_EMOJI_NEXT, CUSTOM_EMOJI_Bx, CUSTOM_EMOJI_ATHKAR,
)
from data.sira_api import (
    SIRA_CATEGORIES, get_category_page, get_article, build_daily_index,
)
from database import get_all_users, get_all_active_chats
from utils.ui import btn, back_btn, kb, esc, short, safe_edit

log = logging.getLogger("sira")

STATE_PATH = os.path.join(CACHE_DIR, "sira", "daily_state.json")
_state_lock = asyncio.Lock()

# بديل disable_web_page_preview (اللي بقى deprecated في pyrogram)
NO_PREVIEW = LinkPreviewOptions(is_disabled=True)


# ------------------------------------------------------------------ menus
def sira_menu_markup():
    return kb([
        [btn(" قصة اليوم", "sira_today", emoji=CUSTOM_EMOJI_ATHKAR)],
        [btn(" تصفح السيرة النبوية", "sira_cats", emoji=CUSTOM_EMOJI_QURAN)],
        [back_btn("back_main")],
    ])


async def show_sira_menu(client, query):
    await query.answer()
    text = "<blockquote><b>🕌 السيرة النبوية</b>\n\nقصة جديدة كل يوم من سيرة النبي ﷺ، أو تصفّح الأقسام واختار اللي يعجبك.</blockquote>"
    await safe_edit(client, query, text, sira_menu_markup())


async def show_categories(client, query):
    await query.answer()
    rows = [[btn(name, f"sira_c_{cid}_1")] for cid, name in SIRA_CATEGORIES]
    rows.append([back_btn("menu_sira")])
    await safe_edit(client, query, "<blockquote><b>📚 أقسام السيرة النبوية</b></blockquote>", kb(rows))


async def show_category(client, query, cid: int, page: int):
    await query.answer("⏳ جاري التحميل...")
    name = next((n for c, n in SIRA_CATEGORIES if c == cid), "السيرة")
    items, pages = await get_category_page(cid, page)
    if not items:
        await safe_edit(client, query, "<blockquote>❌ مقدرتش أجيب الموضوعات دلوقتي، جرّب بعد شوية.</blockquote>",
                        kb([[back_btn("sira_cats")]]))
        return

    rows = [[btn(short(it["title"], 50), f"sira_a_{it['id']}_0_{cid}_{page}")] for it in items]
    nav = []
    if page > 1:
        nav.append(btn(" السابق", f"sira_c_{cid}_{page-1}", ButtonStyle.SUCCESS, CUSTOM_EMOJI_NEXT))
    nav.append(btn(f"{page}/{pages}", "ignore"))
    if page < pages:
        nav.append(btn("التالي ", f"sira_c_{cid}_{page+1}", ButtonStyle.SUCCESS, CUSTOM_EMOJI_Bx))
    rows.append(nav)
    rows.append([back_btn("sira_cats", " الأقسام")])
    await safe_edit(client, query, f"<blockquote><b>📖 {esc(name)}</b></blockquote>", kb(rows))


# ------------------------------------------------------------------ reader
def reader_text(art: dict, pg: int) -> str:
    pages = art["pages"]
    pg = max(0, min(pg, len(pages) - 1))
    return (f"<b>📖 {esc(art['title'])}</b>\n\n"
            f"<blockquote>{esc(pages[pg])}</blockquote>\n\n"
            f"📄 الصفحة {pg + 1} من {len(pages)}")


def reader_markup(aid: int, pg: int, total: int, cid: int, lp: int):
    nav = []
    if pg > 0:
        nav.append(btn(" السابق", f"sira_a_{aid}_{pg-1}_{cid}_{lp}", ButtonStyle.SUCCESS, CUSTOM_EMOJI_NEXT))
    nav.append(btn(f"{pg+1}/{total}", "ignore"))
    if pg < total - 1:
        nav.append(btn("التالي ", f"sira_a_{aid}_{pg+1}_{cid}_{lp}", ButtonStyle.SUCCESS, CUSTOM_EMOJI_Bx))
    back = back_btn(f"sira_c_{cid}_{lp}" if cid else "menu_sira", " رجوع")
    return kb([nav, [back], [btn(" الرئيسية", "back_main", ButtonStyle.SUCCESS)]])


async def show_article(client, query, aid: int, pg: int, cid: int, lp: int):
    await query.answer("⏳ جاري التحميل..." if pg == 0 else None)
    await _render_article(client, query, aid, pg, cid, lp)


async def _render_article(client, query, aid: int, pg: int, cid: int, lp: int):
    art = await get_article(aid)
    if not art:
        await safe_edit(client, query, "<blockquote>❌ مقدرتش أجيب الموضوع دلوقتي، جرّب تاني.</blockquote>",
                        kb([[back_btn(f"sira_c_{cid}_{lp}" if cid else "menu_sira")]]))
        return
    pg = max(0, min(pg, len(art["pages"]) - 1))
    await safe_edit(client, query, reader_text(art, pg), reader_markup(aid, pg, len(art["pages"]), cid, lp))


async def send_article_message(client, chat_id: int, aid: int):
    """بيبعت المقال كرسالة جديدة (للـ deep-link وقصة اليوم)"""
    art = await get_article(aid)
    if not art:
        return None
    return await client.send_message(
        chat_id, reader_text(art, 0),
        reply_markup=reader_markup(aid, 0, len(art["pages"]), 0, 1),
        link_preview_options=NO_PREVIEW)


# ------------------------------------------------------------------ daily story
def _today_str() -> str:
    return datetime.now(ZoneInfo(SIRA_TIMEZONE)).strftime("%Y-%m-%d")


def _load_state() -> dict:
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_state(st: dict):
    """بنكتب في ملف مؤقت وبعدين نبدّل، عشان لو البوت وقف في نص الكتابة الملف ميبوظش"""
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    tmp_path = STATE_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False)
    os.replace(tmp_path, STATE_PATH)


async def get_today_article_id():
    async with _state_lock:
        st = _load_state()
        today = _today_str()
        if st.get("date") == today and st.get("id"):
            return st["id"]
        index = await build_daily_index()
        if not index:
            return st.get("id")  # آخر قصة معروفة لو الموقع مش شغال
        counter = st.get("counter", -1) + 1
        item = index[counter % len(index)]
        st.update({"date": today, "id": item["id"], "counter": counter, "broadcast_done": False})
        _save_state(st)
        return item["id"]


async def show_today(client, query):
    await query.answer("⏳ جاري التحميل...")
    aid = await get_today_article_id()
    if not aid:
        await safe_edit(client, query, "<blockquote>❌ مفيش قصة متاحة دلوقتي، جرّب بعد شوية.</blockquote>",
                        kb([[back_btn("menu_sira")]]))
        return
    await _render_article(client, query, aid, 0, 0, 1)


async def daily_sira_broadcast(bot):
    """بتتشغل كل يوم من الـ scheduler: ترسل قصة اليوم للمستخدمين والجروبات والقنوات"""
    aid = await get_today_article_id()
    if not aid:
        log.warning("daily sira: no article")
        return

    async with _state_lock:
        if _load_state().get("broadcast_done"):
            return

    art = await get_article(aid)
    if not art:
        return

    # بنعلّم إن البث اتعمل قبل الإرسال عشان مفيش رسائل مكررة لو حصل خطأ في النص
    async with _state_lock:
        st = _load_state()
        if st.get("broadcast_done"):
            return
        st["broadcast_done"] = True
        _save_state(st)

    me = await bot.get_me()
    deep = f"https://t.me/{me.username}?start=sira_{aid}"

    # المستخدمين: القصة كاملة بصفحات
    user_text = reader_text(art, 0)
    user_markup = reader_markup(aid, 0, len(art["pages"]), 0, 1)

    # الجروبات/القنوات: مقتطف + زرار يفتح القصة في البوت (عشان الصفحات متتغيرش للكل)
    first_page = art["pages"][0]
    if len(first_page) > 600:
        excerpt = first_page[:600].rsplit(" ", 1)[0] + " ..."
    else:
        excerpt = first_page  # الصفحة قصيرة، مفيش داعي نقص آخر كلمة
    chat_text = (f"<b>🕌 قصة اليوم من السيرة النبوية</b>\n\n<b>📖 {esc(art['title'])}</b>\n\n"
                 f"<blockquote>{esc(excerpt)}</blockquote>")
    chat_markup = kb([[btn(" اقرأ القصة كاملة", url=deep, emoji=CUSTOM_EMOJI_QURAN)]])

    async def _send(chat_id, text, markup):
        for _ in range(3):
            try:
                await bot.send_message(chat_id, text, reply_markup=markup,
                                       link_preview_options=NO_PREVIEW)
                return True
            except FloodWait as e:
                await asyncio.sleep(e.value + 1)
            except Exception as e:
                log.warning("daily sira: send to %s failed: %s", chat_id, e)
                return False
        return False

    ok = 0
    for uid in get_all_users():
        ok += await _send(uid, user_text, user_markup)
        await asyncio.sleep(0.08)
    for cid in get_all_active_chats():
        ok += await _send(cid, chat_text, chat_markup)
        await asyncio.sleep(0.08)
    log.warning("daily sira sent to %s chats", ok)
    print(f"✅ قصة اليوم اتبعتت لـ {ok}")
