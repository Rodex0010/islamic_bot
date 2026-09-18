# handlers/reciters_handler.py
import os
import aiohttp
import aiofiles
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from data.quran_api import SURAH_LIST
from utils.helpers import safe_edit_or_reply

AUDIO_TEMP_DIR = "temp_audio"
if not os.path.exists(AUDIO_TEMP_DIR):
    os.makedirs(AUDIO_TEMP_DIR)

def load_reciters():
    return [
        {"id": 1, "name": "مشاري العفاسي", "style": "مرتل", "url": "https://server8.mp3quran.net/afs/{surah_id:03d}.mp3"},
        {"id": 2, "name": "فارس عباد", "style": "مجود", "url": "https://server8.mp3quran.net/frs_a/{surah_id:03d}.mp3"},
        {"id": 3, "name": "محمد البنا", "style": "مرتل", "url": "https://server8.mp3quran.net/bna/{surah_id:03d}.mp3"},
        {"id": 4, "name": "ماهر المعيقلي", "style": "مجود", "url": "https://server8.mp3quran.net/m_qari/{surah_id:03d}.mp3"},
        {"id": 5, "name": "أبو بكر الشاطري", "style": "مجود", "url": "https://server8.mp3quran.net/bu_khtr/{surah_id:03d}.mp3"},
    ]

async def download_audio(url: str, file_path: str) -> bool:
    try:
        timeout = aiohttp.ClientTimeout(total=120, connect=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    async with aiofiles.open(file_path, 'wb') as f:
                        await f.write(await resp.read())
                    return True
    except:
        pass
    return False

async def show_reciters_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    reciters = load_reciters()
    
    keyboard = []
    row = []
    for reciter in reciters:
        row.append(InlineKeyboardButton(f"🎧 {reciter['name']}", callback_data=f"reciter_{reciter['id']}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_main")])
    
    text = "<blockquote>🎧 اختر القارئ:\n\n📌 القراء المتوفرين:\n• مشاري العفاسي\n• فارس عباد\n• محمد البنا\n• ماهر المعيقلي\n• أبو بكر الشاطري\n\n⚡ انتظر 30-60 ثانية حسب حجم السورة</blockquote>"
    
    await safe_edit_or_reply(query, text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

async def show_suras_for_reciter(update: Update, context: ContextTypes.DEFAULT_TYPE, reciter_id: int):
    query = update.callback_query
    await query.answer()
    
    context.user_data['selected_reciter'] = reciter_id
    page = context.user_data.get('reciter_sura_page', 0)
    items_per_page = 15
    total_pages = (114 + items_per_page - 1) // items_per_page
    start = page * items_per_page
    end = min(start + items_per_page, 114)
    
    keyboard = []
    for sura_id, sura_name in SURAH_LIST[start:end]:
        keyboard.append([InlineKeyboardButton(f"{sura_id}. {sura_name}", callback_data=f"play_sura_{reciter_id}_{sura_id}")])
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀ السابق", callback_data=f"reciter_page_{page-1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("التالي ▶", callback_data=f"reciter_page_{page+1}"))
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    reciters = load_reciters()
    reciter_name = next((r['name'] for r in reciters if r['id'] == reciter_id), "القارئ")
    keyboard.append([InlineKeyboardButton("🔙 رجوع للشيوخ", callback_data="menu_reciters")])
    keyboard.append([InlineKeyboardButton("🏠 الرئيسية", callback_data="back_main")])
    
    text = f"<blockquote>📖 {reciter_name} - اختر السورة (الصفحة {page + 1} من {total_pages})</blockquote>"
    
    await safe_edit_or_reply(query, text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

async def play_surah(update: Update, context: ContextTypes.DEFAULT_TYPE, reciter_id: int, sura_id: int):
    query = update.callback_query
    await query.answer("⏳ جاري التحميل...", show_alert=False)
    
    reciters = load_reciters()
    reciter = next((r for r in reciters if r['id'] == reciter_id), None)
    if not reciter:
        await safe_edit_or_reply(query, "<blockquote>❌ القارئ غير موجود</blockquote>", parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="menu_reciters")]]))
        return
    
    sura_name = SURAH_LIST[sura_id - 1][1]
    reciter_name = reciter['name']
    audio_url = reciter['url'].format(surah_id=sura_id)
    temp_file = os.path.join(AUDIO_TEMP_DIR, f"{reciter_id}_{sura_id}.mp3")
    
    await safe_edit_or_reply(query, f"<blockquote>⏳ جاري تحميل سورة {sura_name}\n🎙️ للقارئ {reciter_name}\n\n⚡ قد يستغرق 30-60 ثانية...</blockquote>", parse_mode="HTML")
    
    success = await download_audio(audio_url, temp_file)
    
    if success and os.path.exists(temp_file) and os.path.getsize(temp_file) > 0:
        try:
            with open(temp_file, 'rb') as audio:
                await context.bot.send_audio(
                    chat_id=update.effective_chat.id,
                    audio=audio,
                    title=f"سورة {sura_name}",
                    performer=f"الشيخ {reciter_name}",
                    caption=f"<blockquote>🎙️ سورة {sura_name}\n📖 بصوت الشيخ {reciter_name}</blockquote>",
                    parse_mode="HTML",
                    read_timeout=180,
                    write_timeout=180,
                    connect_timeout=180,
                    pool_timeout=180
                )
            
            os.remove(temp_file)
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 رجوع للسور", callback_data=f"reciter_{reciter_id}")],
                [InlineKeyboardButton("🏠 الرئيسية", callback_data="back_main")]
            ])
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="<blockquote>✅ تم إرسال السورة</blockquote>",
                parse_mode="HTML",
                reply_markup=keyboard
            )
        except Exception as e:
            print(f"Send error: {e}")
    else:
        pass

async def reciter_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int):
    query = update.callback_query
    context.user_data['reciter_sura_page'] = page
    reciter_id = context.user_data.get('selected_reciter', 1)
    await show_suras_for_reciter(update, context, reciter_id)