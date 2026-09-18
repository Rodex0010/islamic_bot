# utils/keyboards.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from data.quran_api import SURAH_LIST
from config import EMOJI_BACK

BOT_IMAGE_URL = "tito3.jpg"


def get_main_menu():
    """القائمة الرئيسية - بدون إيموجي عادي"""
    keyboard = [
        [
            InlineKeyboardButton("الأذكار", callback_data="menu_athkar"),
            InlineKeyboardButton("المصحف", callback_data="menu_quran")
        ],
        [
            InlineKeyboardButton("التسبيح", callback_data="menu_tasbeeh"),
            InlineKeyboardButton("الأدعية", callback_data="menu_dua")
        ],
        [
            InlineKeyboardButton("الرقية", callback_data="menu_ruqyah"),
            InlineKeyboardButton("الشيوخ", callback_data="menu_reciters")
        ],
        [
            InlineKeyboardButton("المطورون", callback_data="developer")
        ],
        [
            InlineKeyboardButton("كيف أضيف البوت لقناتي؟", callback_data="how_to_add_channel")
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_main_menu_text() -> str:
    return "<blockquote>✨ قرأن كريم ✨</blockquote>"


def get_athkar_menu():
    """قائمة الأذكار - بدون إيموجي عادي"""
    keyboard = [
        [
            InlineKeyboardButton("أذكار الصباح", callback_data="athkar_morning"),
            InlineKeyboardButton("أذكار المساء", callback_data="athkar_evening")
        ],
        [
            InlineKeyboardButton("أذكار متنوعة", callback_data="athkar_other")
        ],
        [
            InlineKeyboardButton(f"{EMOJI_BACK} رجوع", callback_data="back_main")
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_dua_menu():
    """قائمة الأدعية - بدون إيموجي عادي"""
    keyboard = [
        [
            InlineKeyboardButton("أدعية متنوعة", callback_data="dua_random"),
            InlineKeyboardButton("قائمة الأدعية", callback_data="dua_list")
        ],
        [
            InlineKeyboardButton(f"{EMOJI_BACK} رجوع", callback_data="back_main")
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_back_button(callback_data: str = "back_main"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{EMOJI_BACK} رجوع", callback_data=callback_data)]
    ])


def get_quran_menu_buttons(page: int = 0, items_per_page: int = 20):
    """قائمة سور القرآن - بدون إيموجي عادي"""
    total_suras = len(SURAH_LIST)
    total_pages = (total_suras + items_per_page - 1) // items_per_page
    start_idx = page * items_per_page
    end_idx = min(start_idx + items_per_page, total_suras)
    
    keyboard = []
    row = []
    for i in range(start_idx, end_idx):
        sura_id, sura_name = SURAH_LIST[i]
        row.append(
            InlineKeyboardButton(
                f"{sura_id}", 
                callback_data=f"sura_{sura_id}"
            )
        )
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton("◀ السابق", callback_data=f"qpage_{page-1}")
        )
    if page < total_pages - 1:
        nav_buttons.append(
            InlineKeyboardButton("التالي ▶", callback_data=f"qpage_{page+1}")
        )
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([
        InlineKeyboardButton(f"{EMOJI_BACK} رجوع", callback_data="back_main")
    ])
    return InlineKeyboardMarkup(keyboard)


def get_dua_list_buttons(duas, page: int = 0, total: int = 0):
    """قائمة الأدعية - بدون إيموجي عادي"""
    items_per_page = 10
    total_pages = (total + items_per_page - 1) // items_per_page
    
    keyboard = []
    row = []
    for dua in duas:
        row.append(
            InlineKeyboardButton(
                f"{dua['id']}", 
                callback_data=f"dua_{dua['id'] - 1}"
            )
        )
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton("◀ السابق", callback_data=f"dua_page_{page-1}")
        )
    if page < total_pages - 1:
        nav_buttons.append(
            InlineKeyboardButton("التالي ▶", callback_data=f"dua_page_{page+1}")
        )
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([
        InlineKeyboardButton(f"{EMOJI_BACK} رجوع", callback_data="menu_dua")
    ])
    return InlineKeyboardMarkup(keyboard)


def get_tasbeeh_buttons(current_word: str, count: int):
    """أزرار التسبيح - بدون إيموجي عادي"""
    keyboard = [
        [
            InlineKeyboardButton(
                f"{current_word} ({count})", 
                callback_data="tasbeeh_click"
            )
        ],
        [
            InlineKeyboardButton(
                "إعادة تعيين العداد", 
                callback_data="tasbeeh_reset_count"
            )
        ],
        [
            InlineKeyboardButton(
                f"{EMOJI_BACK} رجوع", 
                callback_data="back_main"
            )
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_reciters_menu(reciters):
    """قائمة القراء - بدون إيموجي عادي"""
    keyboard = []
    row = []
    for reciter in reciters:
        row.append(
            InlineKeyboardButton(
                f"{reciter['name']}", 
                callback_data=f"reciter_{reciter['id']}"
            )
        )
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([
        InlineKeyboardButton(f"{EMOJI_BACK} رجوع", callback_data="back_main")
    ])
    return InlineKeyboardMarkup(keyboard)


def get_ruqyah_menu(ruqyah_data):
    """قائمة الرقية - بدون إيموجي عادي"""
    keyboard = []
    row = []
    for reciter in ruqyah_data.get("reciters", []):
        row.append(
            InlineKeyboardButton(
                f"{reciter['name']}", 
                callback_data=f"ruqyah_reciter_{reciter['id']}"
            )
        )
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([
        InlineKeyboardButton(f"{EMOJI_BACK} رجوع", callback_data="back_main")
    ])
    return InlineKeyboardMarkup(keyboard)