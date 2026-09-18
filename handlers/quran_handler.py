# handlers/quran_handler.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from data.quran_api import SURAH_LIST, get_surah
from utils.helpers import safe_edit_or_reply

user_quran_pages = {}
user_sura_pages = {}

AYAH_MARKER = "۝"
HIZB_MARKER = "۞"

def format_ayah_with_marks(ayah_text: str, ayah_number: int, is_hizb_start: bool = False) -> str:
    result = ayah_text
    result = f"{result} {AYAH_MARKER}{ayah_number}"
    if is_hizb_start:
        result = f"{HIZB_MARKER} {result}"
    return result

def get_sura_pages(verses: list, verses_per_page: int = 10) -> list:
    pages = []
    total_verses = len(verses)
    for page_num in range(0, total_verses, verses_per_page):
        page_verses = verses[page_num:page_num + verses_per_page]
        formatted_page = []
        for idx, verse in enumerate(page_verses):
            verse_num = verse.get("numberInSurah", idx + 1)
            verse_text = verse.get("text", "")
            is_hizb = (verse_num % 10 == 0)
            formatted_verse = format_ayah_with_marks(verse_text, verse_num, is_hizb)
            formatted_page.append(formatted_verse)
        pages.append(formatted_page)
    return pages

def get_quran_menu_buttons(page: int = 0, items_per_page: int = 10):
    total_suras = len(SURAH_LIST)
    total_pages = (total_suras + items_per_page - 1) // items_per_page
    start_idx = page * items_per_page
    end_idx = min(start_idx + items_per_page, total_suras)
    
    keyboard = []
    for i in range(start_idx, end_idx):
        sura_id, sura_name = SURAH_LIST[i]
        keyboard.append([InlineKeyboardButton(f"{sura_id}. {sura_name}", callback_data=f"sura_{sura_id}")])
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀ السابق", callback_data=f"qpage_{page-1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("التالي ▶", callback_data=f"qpage_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

def get_sura_pagination_buttons(sura_id: int, current_page: int, total_pages: int):
    current_index = next((i for i, (sid, _) in enumerate(SURAH_LIST) if sid == sura_id), 0)
    prev_sura_id = SURAH_LIST[current_index - 1][0] if current_index > 0 else SURAH_LIST[-1][0]
    next_sura_id = SURAH_LIST[current_index + 1][0] if current_index < len(SURAH_LIST) - 1 else SURAH_LIST[0][0]
    prev_sura_name = SURAH_LIST[current_index - 1][1] if current_index > 0 else SURAH_LIST[-1][1]
    next_sura_name = SURAH_LIST[current_index + 1][1] if current_index < len(SURAH_LIST) - 1 else SURAH_LIST[0][1]
    
    keyboard = []
    
    # أزرار التنقل بين صفحات السورة - استخدم أرقام بسيطة
    page_buttons = []
    if current_page > 0:
        page_buttons.append(InlineKeyboardButton("◀️ السابق", callback_data=f"spage_{sura_id}_{current_page - 1}"))
    page_buttons.append(InlineKeyboardButton(f"📄 {current_page + 1}/{total_pages}", callback_data="ignore"))
    if current_page < total_pages - 1:
        page_buttons.append(InlineKeyboardButton("التالي ▶️", callback_data=f"spage_{sura_id}_{current_page + 1}"))
    keyboard.append(page_buttons)
    
    # أزرار التنقل بين السور
    keyboard.append([
        InlineKeyboardButton(f"◀️ {prev_sura_name}", callback_data=f"sura_{prev_sura_id}"), 
        InlineKeyboardButton(f"{next_sura_name} ▶️", callback_data=f"sura_{next_sura_id}")
    ])
    
    keyboard.append([InlineKeyboardButton("📚 قائمة السور", callback_data="menu_quran")])
    keyboard.append([InlineKeyboardButton("🏠 الرئيسية", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

async def show_quran_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    page = user_quran_pages.get(user_id, 0)
    
    await safe_edit_or_reply(
        query,
        f"📖 *المصحف الشريف*\n\nقائمة السور (الصفحة {page + 1})",
        parse_mode="Markdown",
        reply_markup=get_quran_menu_buttons(page)
    )

async def show_sura(update: Update, context: ContextTypes.DEFAULT_TYPE, sura_id: int = None, page: int = 0):
    query = update.callback_query
    
    if sura_id is None and query and query.data.startswith("sura_"):
        try:
            sura_id = int(query.data.split("_")[1])
        except (ValueError, IndexError):
            await query.answer("❌ حدث خطأ في بيانات السورة", show_alert=True)
            return
    
    if not sura_id:
        if query:
            await query.answer("حدث خطأ", show_alert=True)
        return
    
    await query.answer("جاري تحميل السورة...")
    sura_data = await get_surah(sura_id)
    
    if not sura_data or "ayahs" not in sura_data or not sura_data["ayahs"]:
        await safe_edit_or_reply(
            query, 
            f"<blockquote>❌ خطأ في تحميل سورة {sura_id}\nالرجاء المحاولة مرة أخرى</blockquote>", 
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="menu_quran")]])
        )
        return
    
    sura_name = sura_data.get("name", "")
    verses = sura_data["ayahs"]
    
    pages = get_sura_pages(verses, 10)
    total_pages = len(pages)
    
    if total_pages == 0:
        await safe_edit_or_reply(
            query, 
            f"<blockquote>❌ لا توجد آيات في سورة {sura_name}</blockquote>", 
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="menu_quran")]])
        )
        return
    
    # التأكد من أن رقم الصفحة صحيح
    if page < 0:
        page = 0
    if page >= total_pages:
        page = total_pages - 1
    
    # حفظ رقم الصفحة للمستخدم
    user_id = update.effective_user.id
    if user_id not in user_sura_pages:
        user_sura_pages[user_id] = {}
    user_sura_pages[user_id][sura_id] = page
    
    # بناء النص
    text = f"📖 *سورة {sura_name}*\n📄 *الصفحة {page + 1} من {total_pages}*\n\n"
    for verse_text in pages[page]:
        text += f"{verse_text}\n\n"
    
    await safe_edit_or_reply(query, text, parse_mode="Markdown", reply_markup=get_sura_pagination_buttons(sura_id, page, total_pages))

async def sura_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج التنقل بين صفحات السورة"""
    query = update.callback_query
    data = query.data
    
    if data == "ignore":
        await query.answer()
        return
    
    # الصيغة الجديدة: spage_1_2 (سورة 1 صفحة 2)
    if data.startswith("spage_"):
        try:
            parts = data.split("_")
            # parts = ["spage", "1", "2"]
            if len(parts) == 3:
                sura_id = int(parts[1])
                page = int(parts[2])
                print(f"📖 Navigating to sura {sura_id}, page {page}")  # للتأكد
                await show_sura(update, context, sura_id, page)
            else:
                await query.answer("❌ بيانات غير صالحة", show_alert=True)
        except (ValueError, IndexError) as e:
            print(f"Error in spage: {e}")
            await query.answer("❌ حدث خطأ في التنقل", show_alert=True)
    else:
        await query.answer("❌", show_alert=False)

async def change_quran_page(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int):
    query = update.callback_query
    user_id = update.effective_user.id
    user_quran_pages[user_id] = page
    await safe_edit_or_reply(
        query, 
        f"📖 *المصحف الشريف*\n\nقائمة السور (الصفحة {page + 1})", 
        parse_mode="Markdown", 
        reply_markup=get_quran_menu_buttons(page)
    )