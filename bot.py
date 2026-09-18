# bot.py - النسخة الكاملة مع تعديلات التسبيح (تعديل الرسالة بدل حذفها)
import os
import asyncio
import logging
import sqlite3
from pyrogram import Client, filters
from pyrogram.enums import ButtonStyle, ParseMode
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import RPCError
from config import (
    API_ID, API_HASH, TOKEN, BOT_IMAGE_URL,
    DEVELOPER_USERNAME, DEVELOPER_USERNAME2,
    CUSTOM_EMOJI_QURAN, CUSTOM_EMOJI_ATHKAR, CUSTOM_EMOJI_TASBEEH,
    CUSTOM_EMOJI_DUA, CUSTOM_EMOJI_RUQYAH, CUSTOM_EMOJI_RECITER,
    CUSTOM_EMOJI_DEVELOPER, CUSTOM_EMOJI_BACK, TASBEEH_WORDS, CUSTOM_EMOJI_HELP,
    CUSTOM_EMOJI_M, CUSTOM_EMOJI_S, CUSTOM_EMOJI_X,
    CUSTOM_EMOJI_NEXT, CUSTOM_EMOJI_Bx, CUSTOM_EMOJI_T,
    CUSTOM_EMOJI_u, CUSTOM_EMOJI_o, CUSTOM_EMOJI_qq
)
from data.quran_api import SURAH_LIST, get_surah
from database import (
    init_database, load_all_data_from_json, get_athkar_by_type,
    get_random_dua, get_ruqyah_reciters, add_active_chat,
    remove_active_chat, is_chat_active, get_all_duas,
    force_add_channel, get_user_last_athkar_time, update_user_last_athkar_time,
    fix_missing_last_sent_for_users, fix_missing_last_sent_for_chats
)
from handlers.ruqyah_handler import show_ruqyah_menu, play_ruqyah_audio
from utils.scheduler import start_scheduler, set_bot_instance

logging.basicConfig(level=logging.WARNING)
logging.getLogger("pyrogram").setLevel(logging.WARNING)

bot = Client("islamic_bot", api_id=API_ID, api_hash=API_HASH, bot_token=TOKEN)

user_tasbeeh = {}
user_quran_pages = {}
user_sura_pages = {}

def init_new_columns():
    conn = sqlite3.connect("islamic_bot.db")
    cursor = conn.cursor()
    
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN last_athkar_sent_at TIMESTAMP')
        print("✅ Added last_athkar_sent_at to users")
    except sqlite3.OperationalError:
        pass
    
    try:
        cursor.execute('ALTER TABLE active_chats ADD COLUMN last_athkar_sent_at TIMESTAMP')
        print("✅ Added last_athkar_sent_at to active_chats")
    except sqlite3.OperationalError:
        pass
    
    try:
        cursor.execute('ALTER TABLE active_chats ADD COLUMN last_dua_sent_at TIMESTAMP')
        print("✅ Added last_dua_sent_at to active_chats")
    except sqlite3.OperationalError:
        pass
    
    try:
        cursor.execute('ALTER TABLE active_chats ADD COLUMN last_quran_sent_at TIMESTAMP')
        print("✅ Added last_quran_sent_at to active_chats")
    except sqlite3.OperationalError:
        pass
    
    try:
        cursor.execute('ALTER TABLE active_chats ADD COLUMN activated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
        print("✅ Added activated_at to active_chats")
    except sqlite3.OperationalError:
        pass
    
    conn.commit()
    conn.close()

MAIN_MENU = InlineKeyboardMarkup([
    [
        InlineKeyboardButton(" الأذكار", callback_data="menu_athkar", style=ButtonStyle.PRIMARY, icon_custom_emoji_id=CUSTOM_EMOJI_ATHKAR),
        InlineKeyboardButton(" المصحف", callback_data="menu_quran", style=ButtonStyle.PRIMARY, icon_custom_emoji_id=CUSTOM_EMOJI_QURAN)
    ],
    [
        InlineKeyboardButton(" التسبيح", callback_data="menu_tasbeeh", style=ButtonStyle.PRIMARY, icon_custom_emoji_id=CUSTOM_EMOJI_TASBEEH),
        InlineKeyboardButton(" الأدعية", callback_data="menu_dua", style=ButtonStyle.PRIMARY, icon_custom_emoji_id=CUSTOM_EMOJI_DUA)
    ],
    [
        InlineKeyboardButton(" الرقية", callback_data="menu_ruqyah", style=ButtonStyle.PRIMARY, icon_custom_emoji_id=CUSTOM_EMOJI_RUQYAH),
        InlineKeyboardButton(" الشيوخ", callback_data="menu_reciters", style=ButtonStyle.PRIMARY, icon_custom_emoji_id=CUSTOM_EMOJI_RECITER)
    ],
    [
        InlineKeyboardButton(" المطورون", callback_data="developer", style=ButtonStyle.SUCCESS, icon_custom_emoji_id=CUSTOM_EMOJI_DEVELOPER)
    ],
    [
        InlineKeyboardButton(" ضفني", callback_data="how_to_add_channel", style=ButtonStyle.PRIMARY, icon_custom_emoji_id=CUSTOM_EMOJI_HELP)
    ]
])

def get_athkar_type_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(" أذكار الصباح", callback_data="athkar_type_morning", style=ButtonStyle.PRIMARY, icon_custom_emoji_id=CUSTOM_EMOJI_M)],
        [InlineKeyboardButton(" أذكار المساء", callback_data="athkar_type_evening", style=ButtonStyle.PRIMARY, icon_custom_emoji_id=CUSTOM_EMOJI_S)],
        [InlineKeyboardButton(" أذكار متنوعة", callback_data="athkar_type_other", style=ButtonStyle.PRIMARY, icon_custom_emoji_id=CUSTOM_EMOJI_X)],
        [InlineKeyboardButton(" رجوع", callback_data="back_main", style=ButtonStyle.DANGER, icon_custom_emoji_id=CUSTOM_EMOJI_BACK)]
    ])

def get_athkar_nav_buttons(athkar_type: str, current_index: int, total: int):
    buttons = []
    nav_row = []
    if current_index > 0:
        nav_row.append(InlineKeyboardButton(" السابق", callback_data=f"athkar_nav_{athkar_type}_prev_{current_index}", style=ButtonStyle.SUCCESS, icon_custom_emoji_id=CUSTOM_EMOJI_NEXT))
    
    nav_row.append(InlineKeyboardButton(f"{current_index + 1}/{total}", callback_data="ignore", style=ButtonStyle.PRIMARY))
    
    if current_index < total - 1:
        nav_row.append(InlineKeyboardButton("التالي ", callback_data=f"athkar_nav_{athkar_type}_next_{current_index}", style=ButtonStyle.SUCCESS, icon_custom_emoji_id=CUSTOM_EMOJI_Bx))
    buttons.append(nav_row)
    
    buttons.append([
        InlineKeyboardButton(" قائمة الأذكار", callback_data="menu_athkar", style=ButtonStyle.PRIMARY, icon_custom_emoji_id=CUSTOM_EMOJI_ATHKAR),
        InlineKeyboardButton(" رجوع", callback_data="back_main", style=ButtonStyle.DANGER, icon_custom_emoji_id=CUSTOM_EMOJI_BACK)
    ])
    
    return InlineKeyboardMarkup(buttons)

def get_athkar_title(athkar_type: str) -> str:
    titles = {
        "morning": " **أذكار الصباح**",
        "evening": " **أذكار المساء**",
        "other": " **أذكار متنوعة**"
    }
    return titles.get(athkar_type, " أذكار")

async def send_athkar_message(client, chat_id, message_id, athkar_type: str, index: int):
    athkar_list = get_athkar_by_type(athkar_type)
    if not athkar_list or index >= len(athkar_list):
        return False
    text = f"<blockquote>{get_athkar_title(athkar_type)}\n\n{athkar_list[index]}</blockquote>"
    try:
        await client.edit_message_text(chat_id, message_id, text, reply_markup=get_athkar_nav_buttons(athkar_type, index, len(athkar_list)))
        return True
    except Exception as e:
        if "MESSAGE_NOT_MODIFIED" in str(e):
            return True
        return False

def get_quran_menu_buttons(page=0):
    items_per_page = 10
    total_pages = (114 + items_per_page - 1) // items_per_page
    start = page * items_per_page
    end = min(start + items_per_page, 114)
    
    keyboard = []
    for i in range(start, end):
        sura_id, sura_name = SURAH_LIST[i]
        keyboard.append([InlineKeyboardButton(f"{sura_id}. {sura_name}", callback_data=f"sura_{sura_id}", style=ButtonStyle.PRIMARY)])
    
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(" السابق", callback_data=f"qpage_{page-1}", style=ButtonStyle.SUCCESS, icon_custom_emoji_id=CUSTOM_EMOJI_NEXT))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("التالي ", callback_data=f"qpage_{page+1}", style=ButtonStyle.SUCCESS, icon_custom_emoji_id=CUSTOM_EMOJI_Bx))
    if nav:
        keyboard.append(nav)
    
    keyboard.append([InlineKeyboardButton(" رجوع", callback_data="back_main", style=ButtonStyle.DANGER, icon_custom_emoji_id=CUSTOM_EMOJI_BACK)])
    return InlineKeyboardMarkup(keyboard)

def get_sura_view_buttons(sura_id, current_page, total_pages):
    page_buttons = []
    if current_page > 0:
        page_buttons.append(InlineKeyboardButton(" السابق", callback_data=f"spage_{sura_id}_{current_page-1}", style=ButtonStyle.SUCCESS, icon_custom_emoji_id=CUSTOM_EMOJI_NEXT))
    page_buttons.append(InlineKeyboardButton(f"{current_page+1}/{total_pages}", callback_data="ignore", style=ButtonStyle.PRIMARY))
    if current_page < total_pages - 1:
        page_buttons.append(InlineKeyboardButton("التالي ", callback_data=f"spage_{sura_id}_{current_page+1}", style=ButtonStyle.SUCCESS, icon_custom_emoji_id=CUSTOM_EMOJI_Bx))
    
    current_index = next(i for i, (sid, _) in enumerate(SURAH_LIST) if sid == sura_id)
    prev_sura = SURAH_LIST[current_index - 1][0] if current_index > 0 else SURAH_LIST[-1][0]
    next_sura = SURAH_LIST[current_index + 1][0] if current_index < 113 else SURAH_LIST[0][0]
    prev_name = SURAH_LIST[current_index - 1][1] if current_index > 0 else SURAH_LIST[-1][1]
    next_name = SURAH_LIST[current_index + 1][1] if current_index < 113 else SURAH_LIST[0][1]
    
    keyboard = [
        page_buttons,
        [
            InlineKeyboardButton(f" {prev_name}", callback_data=f"sura_{prev_sura}", style=ButtonStyle.PRIMARY, icon_custom_emoji_id=CUSTOM_EMOJI_NEXT),
            InlineKeyboardButton(f"{next_name} ", callback_data=f"sura_{next_sura}", style=ButtonStyle.PRIMARY, icon_custom_emoji_id=CUSTOM_EMOJI_Bx)
        ],
        [InlineKeyboardButton(" قائمة السور", callback_data="menu_quran", style=ButtonStyle.PRIMARY, icon_custom_emoji_id=CUSTOM_EMOJI_QURAN)],
        [InlineKeyboardButton(" رجوع", callback_data="back_main", style=ButtonStyle.DANGER, icon_custom_emoji_id=CUSTOM_EMOJI_BACK)]
    ]
    return InlineKeyboardMarkup(keyboard)

async def send_sura_pages(client, chat_id, sura_name, pages, current_page, sura_id, old_message_id=None):
    if not pages:
        return None
    
    page_verses = pages[current_page]
    verses_text = "\n\n".join([f"۝{v['numberInSurah']} {v['text']}" for v in page_verses])
    text = f"<blockquote> سورة {sura_name}\n\n{verses_text}\n\n📄 الصفحة {current_page + 1} من {len(pages)}</blockquote>"
    
    if old_message_id:
        try:
            await client.delete_messages(chat_id, old_message_id)
        except:
            pass
    
    return await client.send_message(chat_id, text, reply_markup=get_sura_view_buttons(sura_id, current_page, len(pages)))

def get_tasbeeh_buttons(word, count):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f" {word} ({count})", callback_data="tasbeeh_click", style=ButtonStyle.PRIMARY, icon_custom_emoji_id=CUSTOM_EMOJI_TASBEEH)],
        [InlineKeyboardButton(" إعادة تعيين", callback_data="tasbeeh_reset", style=ButtonStyle.PRIMARY, icon_custom_emoji_id=CUSTOM_EMOJI_RUQYAH)],
        [InlineKeyboardButton(" رجوع", callback_data="back_main", style=ButtonStyle.DANGER, icon_custom_emoji_id=CUSTOM_EMOJI_BACK)]
    ])

def get_dua_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(" دعاء عشوائي", callback_data="dua_random", style=ButtonStyle.PRIMARY, icon_custom_emoji_id=CUSTOM_EMOJI_DUA)],
        [InlineKeyboardButton(" قائمة الأدعية", callback_data="dua_list", style=ButtonStyle.PRIMARY, icon_custom_emoji_id=CUSTOM_EMOJI_RUQYAH)],
        [InlineKeyboardButton(" رجوع", callback_data="back_main", style=ButtonStyle.DANGER, icon_custom_emoji_id=CUSTOM_EMOJI_BACK)]
    ])

def get_ruqyah_menu():
    reciters = get_ruqyah_reciters()
    keyboard = []
    for r in reciters:
        keyboard.append([InlineKeyboardButton(f"🎙️ {r['name']}", callback_data=f"ruqyah_reciter_{r['id']}", style=ButtonStyle.PRIMARY)])
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_main", style=ButtonStyle.DANGER, icon_custom_emoji_id=CUSTOM_EMOJI_BACK)])
    return InlineKeyboardMarkup(keyboard)

RECITERS = [
    {"id": 1, "name": "مشاري العفاسي", "url": "https://server8.mp3quran.net/afs/{surah_id:03d}.mp3"},
    {"id": 2, "name": "فارس عباد", "url": "https://server8.mp3quran.net/frs_a/{surah_id:03d}.mp3"},
    {"id": 3, "name": "محمد البنا", "url": "https://server8.mp3quran.net/bna/{surah_id:03d}.mp3"},
    {"id": 4, "name": "ماهر المعيقلي", "url": "https://server8.mp3quran.net/m_qari/{surah_id:03d}.mp3"},
    {"id": 5, "name": "أبو بكر الشاطري", "url": "https://server8.mp3quran.net/bu_khtr/{surah_id:03d}.mp3"},
]

def get_reciters_menu():
    keyboard = []
    for reciter in RECITERS:
        keyboard.append([
            InlineKeyboardButton(
                f" {reciter['name']}", 
                callback_data=f"reciter_{reciter['id']}", 
                style=ButtonStyle.PRIMARY, 
                icon_custom_emoji_id=CUSTOM_EMOJI_RECITER
            )
        ])
    keyboard.append([
        InlineKeyboardButton(" رجوع", callback_data="back_main", style=ButtonStyle.DANGER, icon_custom_emoji_id=CUSTOM_EMOJI_BACK)
    ])
    return InlineKeyboardMarkup(keyboard)

def get_suras_for_reciter(reciter_id, page=0):
    items_per_page = 10
    total_pages = (114 + items_per_page - 1) // items_per_page
    start = page * items_per_page
    end = min(start + items_per_page, 114)
    
    keyboard = []
    for i in range(start, end):
        sura_id, sura_name = SURAH_LIST[i]
        keyboard.append([InlineKeyboardButton(f"{sura_id}. {sura_name}", callback_data=f"play_{reciter_id}_{sura_id}", style=ButtonStyle.PRIMARY, icon_custom_emoji_id=CUSTOM_EMOJI_QURAN)])
    
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(" السابق", callback_data=f"reciter_page_{reciter_id}_{page-1}", style=ButtonStyle.SUCCESS, icon_custom_emoji_id=CUSTOM_EMOJI_NEXT))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("التالي ", callback_data=f"reciter_page_{reciter_id}_{page+1}", style=ButtonStyle.SUCCESS, icon_custom_emoji_id=CUSTOM_EMOJI_Bx))
    if nav:
        keyboard.append(nav)
    
    keyboard.append([InlineKeyboardButton(" رجوع للشيوخ", callback_data="menu_reciters", style=ButtonStyle.DANGER, icon_custom_emoji_id=CUSTOM_EMOJI_BACK)])
    keyboard.append([InlineKeyboardButton(" الرئيسية", callback_data="back_main", style=ButtonStyle.SUCCESS, icon_custom_emoji_id=CUSTOM_EMOJI_BACK)])
    return InlineKeyboardMarkup(keyboard)

async def send_welcome_message(client, chat_id, edit_mode=False, message=None, reply_markup=MAIN_MENU):
    caption = f"""
    <blockquote expandable>
    <emoji id={CUSTOM_EMOJI_QURAN}>💚</emoji> <b>أهلاً بيك في البوت الإسلامي</b>

<b>نسأل الله لنا ولكم الثبات والهداية والتوفيق</b> <emoji id={CUSTOM_EMOJI_RUQYAH}>✨</emoji>
    </blockquote>
    """  

    try:
        if edit_mode and message:
            try:
                await message.edit_text(caption, reply_markup=reply_markup)
                return
            except Exception as e:
                if "MESSAGE_NOT_MODIFIED" not in str(e):
                    try:
                        await client.send_photo(
                            chat_id=chat_id, 
                            photo=BOT_IMAGE_URL, 
                            caption=caption, 
                            reply_markup=reply_markup
                        )
                    except:
                        await client.send_message(
                            chat_id=chat_id, 
                            text=caption, 
                            reply_markup=reply_markup
                        )
                return
        
        try:
            await client.send_photo(
                chat_id=chat_id, 
                photo=BOT_IMAGE_URL, 
                caption=caption, 
                reply_markup=reply_markup
            )
        except:
            await client.send_message(
                chat_id=chat_id, 
                text=caption, 
                reply_markup=reply_markup
            )
            
    except Exception as e:
        try:
            await client.send_message(
                chat_id=chat_id, 
                text=caption, 
                reply_markup=reply_markup
            )
        except:
            print(f"❌ Failed to send welcome message: {e}")

async def send_text_message(client, chat_id, edit_mode=False, message=None, text="\u200C", reply_markup=None, image_url=None):
    if not text or text.strip() == "":
        text = "\u200C"
    
    if edit_mode and message:
        try:
            await message.edit_text(text, reply_markup=reply_markup)
        except Exception as e:
            if "MESSAGE_NOT_MODIFIED" not in str(e):
                try:
                    await message.delete()
                except:
                    pass
                if image_url:
                    await client.send_photo(
                        chat_id=chat_id,
                        photo=image_url,
                        caption=text,
                        reply_markup=reply_markup
                    )
                else:
                    await client.send_message(chat_id, text, reply_markup=reply_markup)
    else:
        if image_url:
            await client.send_photo(
                chat_id=chat_id,
                photo=image_url,
                caption=text,
                reply_markup=reply_markup
            )
        else:
            await client.send_message(chat_id, text, reply_markup=reply_markup)

@bot.on_message(filters.command("start") & filters.private)
async def start_bot(client: Client, message: Message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    username = message.from_user.username
    
    from database import add_user, user_exists, update_user_last_athkar_time, get_user_last_athkar_time
    from utils.scheduler import SHORT_ATHKAR
    import random
    from datetime import datetime, timedelta
    
    is_new_user = not user_exists(user_id)
    
    if is_new_user:
        add_user(user_id, first_name, username)
        past_time = datetime.now() - timedelta(minutes=60)
        update_user_last_athkar_time(user_id, force_time=past_time)
        print(f"✅ New user added: {first_name} (@{username}) - ID: {user_id}")
    else:
        last_sent = get_user_last_athkar_time(user_id)
        if last_sent is None:
            past_time = datetime.now() - timedelta(minutes=60)
            update_user_last_athkar_time(user_id, force_time=past_time)
            print(f"✅ Fixed missing time for user: {user_id}")
    
    await send_welcome_message(client, message.chat.id, edit_mode=False, message=message)
    
    if is_new_user:
        athkar = random.choice(SHORT_ATHKAR)
        try:
            await message.reply_text(
                f"<blockquote>{athkar}</blockquote>",
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            print(f"Error sending first athkar: {e}")
            try:
                await message.reply_text(f"{athkar}")
            except:
                pass

@bot.on_message(filters.command("forceadd") & filters.private)
async def force_add_channel_command(client: Client, message: Message):
    try:
        args = message.text.split()
        if len(args) != 2:
            await message.reply("<blockquote> استخدم: /forceadd -100xxxxxx</blockquote>")
            return
        
        chat_id = int(args[1])
        force_add_channel(chat_id)
        await message.reply(f"<blockquote>✅ تم إضافة القناة {chat_id} بنجاح\nسيتم إرسال التذكيرات تلقائياً</blockquote>")
    except Exception as e:
        await message.reply(f"<blockquote>❌ خطأ: {e}</blockquote>")

@bot.on_message(filters.text & (filters.group | filters.channel))
async def handle_activation(client: Client, message: Message):
    chat_id = message.chat.id
    text = message.text or ""
    
    if text.strip() == "تفعيل":
        try:
            await message.delete()
        except:
            pass
        
        if not is_chat_active(chat_id):
            add_active_chat(chat_id)
            print(f"✅ Activated chat {chat_id} via 'تفعيل'")
        
        from utils.scheduler import INTERVALS
        
        try:
            await client.send_message(
                chat_id, 
                f"""<blockquote><emoji id={CUSTOM_EMOJI_o}>✅</emoji> <b>تم تفعيل البوت بنجاح!</b>

🕌 سيتم إرسال:
• أذكار قصيرة كل {INTERVALS['group_athkar']} دقيقة
• أدعية متنوعة كل {INTERVALS['group_dua']} دقيقة
• آية قرآنية كل {INTERVALS['group_quran']} دقيقة

نسأل الله القبول <emoji id={CUSTOM_EMOJI_qq}>🤲</emoji></blockquote>""",
                parse_mode=ParseMode.HTML
            )
        except:
            pass
        return
    
    if not is_chat_active(chat_id):
        add_active_chat(chat_id)
        print(f"✅ Auto-activated chat: {chat_id}")

@bot.on_message(filters.text & filters.group)
async def quiz_keyword_handler(client: Client, message: Message):
    if not message.from_user or message.from_user.is_bot:
        return
    
    text = message.text or ""
    
    if text.strip() == "تفعيل":
        return
    
    from handlers.quiz_handler import is_quiz_trigger, send_random_quiz
    
    if is_quiz_trigger(text):
        await send_random_quiz(client, message)

@bot.on_callback_query()
async def handle_callback(client: Client, query: CallbackQuery):
    data = query.data
    user_id = query.from_user.id
    
    if data == "back_main":
        await send_welcome_message(client, query.message.chat.id, edit_mode=True, message=query.message)
        return
    
    if data == "developer":
        text = "\u200C"
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("تيتو", url=f"https://t.me/{DEVELOPER_USERNAME}", style=ButtonStyle.PRIMARY, icon_custom_emoji_id=CUSTOM_EMOJI_DEVELOPER)],
            [InlineKeyboardButton("تركي", url=f"https://t.me/{DEVELOPER_USERNAME2}", style=ButtonStyle.PRIMARY, icon_custom_emoji_id=CUSTOM_EMOJI_DEVELOPER)],
            [InlineKeyboardButton(" رجوع", callback_data="back_main", style=ButtonStyle.DANGER, icon_custom_emoji_id=CUSTOM_EMOJI_BACK)]
        ])
        await send_text_message(client, query.message.chat.id, edit_mode=True, message=query.message, text=text, reply_markup=reply_markup)
        return
    
    if data == "how_to_add_channel":
        text = f"""<blockquote>
<emoji id={CUSTOM_EMOJI_o}>✅</emoji> <b>لتفعيل البوت في الجروب:</b>

<emoji id={CUSTOM_EMOJI_u}>📝</emoji> ارفع البوت ادمن
<emoji id={CUSTOM_EMOJI_u}>📝</emoji> اكتب كلمة <b>تفعيل</b> في الجروب

<emoji id={CUSTOM_EMOJI_o}>📢</emoji> <b>ضيف البوت في قناتك؟</b>
<emoji id={CUSTOM_EMOJI_u}>📝</emoji> ارفع البوت ادمن
<emoji id={CUSTOM_EMOJI_u}>📝</emoji> اكتب كلمة <b>تفعيل</b> في القناه

</blockquote>"""
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton(" رجوع", callback_data="back_main", style=ButtonStyle.DANGER, icon_custom_emoji_id=CUSTOM_EMOJI_BACK)]
        ])
        await send_text_message(client, query.message.chat.id, edit_mode=True, message=query.message, text=text, reply_markup=reply_markup)
        return
    
    if data == "menu_athkar":
        await send_text_message(
            client, 
            query.message.chat.id, 
            edit_mode=True, 
            message=query.message, 
            text="ㅤ", 
            reply_markup=get_athkar_type_menu(),
            image_url=BOT_IMAGE_URL
        )
        return
    
    if data == "athkar_type_morning":
        athkar_list = get_athkar_by_type("morning")
        if athkar_list:
            await send_athkar_message(client, query.message.chat.id, query.message.id, "morning", 0)
        else:
            await send_text_message(client, query.message.chat.id, edit_mode=True, message=query.message, text="❌ لا توجد أذكار صباح", reply_markup=get_athkar_type_menu())
        return
    
    if data == "athkar_type_evening":
        athkar_list = get_athkar_by_type("evening")
        if athkar_list:
            await send_athkar_message(client, query.message.chat.id, query.message.id, "evening", 0)
        else:
            await send_text_message(client, query.message.chat.id, edit_mode=True, message=query.message, text="❌ لا توجد أذكار مساء", reply_markup=get_athkar_type_menu())
        return
    
    if data == "athkar_type_other":
        athkar_list = get_athkar_by_type("other")
        if athkar_list:
            await send_athkar_message(client, query.message.chat.id, query.message.id, "other", 0)
        else:
            await send_text_message(client, query.message.chat.id, edit_mode=True, message=query.message, text="❌ لا توجد أذكار متنوعة", reply_markup=get_athkar_type_menu())
        return
    
    if data.startswith("athkar_nav_"):
        parts = data.split("_")
        if len(parts) >= 5:
            athkar_type = parts[2]
            action = parts[3]
            current_index = int(parts[4])
            athkar_list = get_athkar_by_type(athkar_type)
            if action == "prev":
                new_index = current_index - 1
            else:
                new_index = current_index + 1
            if 0 <= new_index < len(athkar_list):
                await send_athkar_message(client, query.message.chat.id, query.message.id, athkar_type, new_index)
        return
    
    if data == "menu_quran":
        page = user_quran_pages.get(user_id, 0)
        await send_text_message(
            client, 
            query.message.chat.id, 
            edit_mode=True, 
            message=query.message, 
            text="ㅤ",
            reply_markup=get_quran_menu_buttons(page)
        )
        return
    
    if data.startswith("qpage_"):
        page = int(data.split("_")[1])
        user_quran_pages[user_id] = page
        await send_text_message(
            client, 
            query.message.chat.id, 
            edit_mode=True, 
            message=query.message, 
            text="ㅤ",
            reply_markup=get_quran_menu_buttons(page)
        )
        return
    
    if data.startswith("sura_"):
        sura_id = int(data.split("_")[1])
        await send_text_message(client, query.message.chat.id, edit_mode=True, message=query.message, text="🔄 جاري تحميل السورة...")
        sura_data = await get_surah(sura_id)
        if sura_data and "ayahs" in sura_data:
            verses = sura_data["ayahs"]
            pages = []
            for i in range(0, len(verses), 10):
                pages.append(verses[i:i+10])
            sura_name = sura_data.get("name", "")
            user_sura_pages[user_id] = {sura_id: 0}
            await query.message.delete()
            await send_sura_pages(client, query.message.chat.id, sura_name, pages, 0, sura_id)
        else:
            await send_text_message(client, query.message.chat.id, edit_mode=True, message=query.message, text="❌ خطأ في تحميل السورة", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(" رجوع", callback_data="menu_quran", style=ButtonStyle.DANGER)]]))
        return
    
    if data.startswith("spage_"):
        parts = data.split("_")
        sura_id = int(parts[1])
        page = int(parts[2])
        sura_data = await get_surah(sura_id)
        if sura_data and "ayahs" in sura_data:
            verses = sura_data["ayahs"]
            pages = []
            for i in range(0, len(verses), 10):
                pages.append(verses[i:i+10])
            if 0 <= page < len(pages):
                sura_name = sura_data.get("name", "")
                page_verses = pages[page]
                verses_text = "\n\n".join([f"۝{v['numberInSurah']} {v['text']}" for v in page_verses])
                text = f"<blockquote> سورة {sura_name}\n\n{verses_text}\n\n📄 الصفحة {page + 1} من {len(pages)}</blockquote>"
                try:
                    await query.message.edit_text(text, reply_markup=get_sura_view_buttons(sura_id, page, len(pages)))
                except Exception as e:
                    if "MESSAGE_NOT_MODIFIED" not in str(e):
                        pass
        return
    
    if data == "menu_tasbeeh":
        if user_id not in user_tasbeeh:
            user_tasbeeh[user_id] = {"count": 0, "word_index": 0}
        w_idx = user_tasbeeh[user_id]["word_index"]
        word = TASBEEH_WORDS[w_idx]
        count = user_tasbeeh[user_id]["count"]
        text = f"<blockquote><emoji id={CUSTOM_EMOJI_T}></emoji> <b>التسبيح</b>\n\n<emoji id={CUSTOM_EMOJI_T}>✨</emoji> الذكر الحالي: {word}\n<emoji id={CUSTOM_EMOJI_TASBEEH}>📊</emoji> عدد التسبيحات: {count}\n\n<emoji id={CUSTOM_EMOJI_T}></emoji> كل 33 تسبيحة يتغير الذكر تلقائياً</blockquote>"
        await send_text_message(
            client, 
            query.message.chat.id, 
            edit_mode=True, 
            message=query.message, 
            text=text, 
            reply_markup=get_tasbeeh_buttons(word, count),
            image_url=BOT_IMAGE_URL
        )
        return

    if data == "tasbeeh_click":
        if user_id not in user_tasbeeh:
            user_tasbeeh[user_id] = {"count": 0, "word_index": 0}
        user_tasbeeh[user_id]["count"] += 1
        new_count = user_tasbeeh[user_id]["count"]
        w_idx = user_tasbeeh[user_id]["word_index"]
        
        if new_count % 33 == 0 and new_count > 0:
            user_tasbeeh[user_id]["word_index"] = (w_idx + 1) % len(TASBEEH_WORDS)
            new_word = TASBEEH_WORDS[user_tasbeeh[user_id]["word_index"]]
            await query.answer(f"🎉 تم تغيير الذكر إلى: {new_word}", show_alert=True)
        
        word = TASBEEH_WORDS[user_tasbeeh[user_id]["word_index"]]
        text = f"<blockquote><emoji id={CUSTOM_EMOJI_T}></emoji> <b>التسبيح</b>\n\n<emoji id={CUSTOM_EMOJI_TASBEEH}>✨</emoji> الذكر الحالي: {word}\n<emoji id={CUSTOM_EMOJI_T}>📊</emoji> عدد التسبيحات: {new_count}\n\n<emoji id={CUSTOM_EMOJI_TASBEEH}>💡</emoji> كل 33 تسبيحة يتغير الذكر تلقائياً</blockquote>"
        
        try:
            await query.message.edit_text(text, reply_markup=get_tasbeeh_buttons(word, new_count))
        except Exception as e:
            if "MESSAGE_NOT_MODIFIED" not in str(e):
                await query.message.delete()
                await client.send_message(
                    query.message.chat.id, 
                    text, 
                    reply_markup=get_tasbeeh_buttons(word, new_count)
                )
        return

    if data == "tasbeeh_reset":
        if user_id not in user_tasbeeh:
            user_tasbeeh[user_id] = {"count": 0, "word_index": 0}
        user_tasbeeh[user_id]["count"] = 0
        w_idx = user_tasbeeh[user_id]["word_index"]
        word = TASBEEH_WORDS[w_idx]
        text = f"<blockquote><emoji id={CUSTOM_EMOJI_TASBEEH}></emoji> <b>التسبيح</b>\n\n<emoji id={CUSTOM_EMOJI_BACK}>✨</emoji> الذكر الحالي: {word}\n<emoji id={CUSTOM_EMOJI_TASBEEH}>📊</emoji> عدد التسبيحات: 0\n\n<emoji id={CUSTOM_EMOJI_BACK}>💡</emoji> كل 33 تسبيحة يتغير الذكر تلقائياً</blockquote>"
        
        try:
            await query.message.edit_text(text, reply_markup=get_tasbeeh_buttons(word, 0))
        except Exception as e:
            if "MESSAGE_NOT_MODIFIED" not in str(e):
                await query.message.delete()
                await client.send_message(
                    query.message.chat.id, 
                    text, 
                    reply_markup=get_tasbeeh_buttons(word, 0)
                )
        return
    
    if data == "menu_dua":
        await send_text_message(
            client, 
            query.message.chat.id, 
            edit_mode=True, 
            message=query.message, 
            text="ㅤ", 
            reply_markup=get_dua_menu(),
            image_url=BOT_IMAGE_URL
        )
        return
    
    if data == "dua_random":
        dua = get_random_dua()
        text = f"<blockquote> <emoji id={CUSTOM_EMOJI_DUA}> 🕌</emoji>  {dua} </blockquote>"
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton(" دعاء آخر ", callback_data="dua_random", style=ButtonStyle.PRIMARY, icon_custom_emoji_id=CUSTOM_EMOJI_DUA)],
            [InlineKeyboardButton(" رجوع", callback_data="menu_dua", style=ButtonStyle.DANGER, icon_custom_emoji_id=CUSTOM_EMOJI_BACK)]
        ])
        await send_text_message(client, query.message.chat.id, edit_mode=True, message=query.message, text=text, reply_markup=reply_markup)
        return
    
    if data == "dua_list":
        duas = get_all_duas()
        text = f"<blockquote><emoji id={CUSTOM_EMOJI_DUA}>📖</emoji> قائمة الأدعية\n\n"
        for i, dua in enumerate(duas[:15]):
            text += f"{i+1}. {dua[:60]}...\n"
        text += "</blockquote>"
        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(" رجوع", callback_data="menu_dua", style=ButtonStyle.DANGER, icon_custom_emoji_id=CUSTOM_EMOJI_BACK)]])
        await send_text_message(client, query.message.chat.id, edit_mode=True, message=query.message, text=text, reply_markup=reply_markup)
        return
    
    if data == "menu_ruqyah":
        await show_ruqyah_menu(client, query)
        return
    
    if data.startswith("ruqyah_reciter_"):
        try:
            reciter_id = int(data.split("_")[2])
            await play_ruqyah_audio(client, query, reciter_id)
        except (IndexError, ValueError) as e:
            print(f"Error parsing ruqyah callback: {e}")
            await query.answer("❌ حدث خطأ", show_alert=True)
        return
    
    if data == "menu_reciters":
        await send_text_message(
            client, 
            query.message.chat.id, 
            edit_mode=True, 
            message=query.message, 
            text="ㅤ", 
            reply_markup=get_reciters_menu(),
            image_url=BOT_IMAGE_URL
        )
        return
    
    if data.startswith("reciter_page_"):
        parts = data.split("_")
        reciter_id = int(parts[2])
        page = int(parts[3])
        await send_text_message(
            client, 
            query.message.chat.id, 
            edit_mode=True, 
            message=query.message, 
            text="ㅤ", 
            reply_markup=get_suras_for_reciter(reciter_id, page),
            image_url=BOT_IMAGE_URL
        )
        return
    
    if data.startswith("reciter_"):
        reciter_id = int(data.split("_")[1])
        await send_text_message(
            client, 
            query.message.chat.id, 
            edit_mode=True, 
            message=query.message, 
            text="ㅤ", 
            reply_markup=get_suras_for_reciter(reciter_id, 0),
            image_url=BOT_IMAGE_URL
        )
        return
    
    if data.startswith("play_"):
        parts = data.split("_")
        reciter_id = int(parts[1])
        sura_id = int(parts[2])
        reciter = next((r for r in RECITERS if r['id'] == reciter_id), None)
        sura_name = SURAH_LIST[sura_id-1][1]
        
        if reciter:
            url = reciter['url'].format(surah_id=sura_id)
            
            waiting_msg = await client.send_message(
                query.message.chat.id,
                f"🔄 جاري تجهيز تلاوة سورة {sura_name}\nللشيخ {reciter['name']}...\n⏱️ قد يستغرق 10-20 ثانية"
            )
            
            try:
                import aiohttp
                import io
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                        if resp.status == 200:
                            audio_data = await resp.read()
                            audio_file = io.BytesIO(audio_data)
                            audio_file.name = f"surah_{sura_id}.mp3"
                            
                            await client.send_audio(
                                chat_id=query.message.chat.id,
                                audio=audio_file,
                                title=f"سورة {sura_name}",
                                performer=f"الشيخ {reciter['name']}",
                                duration=0
                            )
                            
                            audio_file.close()
                            await waiting_msg.delete()
                            await query.message.delete()
                        else:
                            raise Exception(f"فشل التحميل - HTTP {resp.status}")
                            
            except Exception as e:
                print(f"Streaming error: {e}")
                await waiting_msg.edit_text(
                    "❌ حدث خطأ في تشغيل التلاوة\nيرجى المحاولة لاحقاً",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 رجوع", callback_data=f"reciter_{reciter_id}")
                    ]])
                )
            return

    if data == "quiz_new":
        from handlers.quiz_handler import send_random_quiz
        await send_random_quiz(client, query)
        return
    
    if data.startswith("quiz_ans_"):
        from handlers.quiz_handler import check_quiz_answer
        await check_quiz_answer(client, query)
        return

    if data == "ignore":
        await query.answer()

if __name__ == "__main__":
    print("🔄 جاري تهيئة قاعدة البيانات...")
    init_database()
    init_new_columns()
    load_all_data_from_json()
    
    # إصلاح المستخدمين والجروبات اللي مفشلين
    try:
        fix_missing_last_sent_for_users()
        fix_missing_last_sent_for_chats()
    except:
        pass
    
    print("✅ تم تهيئة قاعدة البيانات")
    
    print("🚀 تشغيل البوت بكامل الميزات...")
    
    set_bot_instance(bot)
    start_scheduler(bot)
    
    print("📖 المصحف شغال - 🎧 الشيوخ شغالين - 🕋 الرقية شغالة")
    print("📌 أمر /forceadd جاهز للإستخدام")
    print("✅ التفعيل التلقائي يعمل")
    print("✅ البوت يرسل لجميع المستخدمين والقنوات والجروبات المفعلة")
    print("✅ نظام التوزيع الذكي يعمل - كل جهة لها توقيت مستقل")
    
    bot.run()