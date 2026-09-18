# handlers/dua_handler.py
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import get_all_duas, get_random_dua, get_duas_paginated
from utils.helpers import safe_edit_or_reply

user_dua_pages = {}
user_dua_index = {}

def get_dua_menu():
    keyboard = [
        [
            InlineKeyboardButton("🤲 أدعية متنوعة", callback_data="dua_random"),
            InlineKeyboardButton("📋 قائمة الأدعية", callback_data="dua_list")
        ],
        [
            InlineKeyboardButton("🔙 رجوع", callback_data="back_main")
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_dua_navigation_buttons(current_index: int, total: int):
    buttons = []
    
    if current_index > 0:
        buttons.append(InlineKeyboardButton("◀️ السابق", callback_data=f"dnav_prev_{current_index}"))
    
    buttons.append(InlineKeyboardButton(f"{current_index + 1}/{total}", callback_data="ignore"))
    
    if current_index < total - 1:
        buttons.append(InlineKeyboardButton("التالي ▶️", callback_data=f"dnav_next_{current_index}"))
    
    keyboard = [buttons]
    keyboard.append([InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="menu_dua")])
    keyboard.append([InlineKeyboardButton("🏠 الرئيسية", callback_data="back_main")])
    
    return InlineKeyboardMarkup(keyboard)

def get_dua_list_buttons(duas, page: int = 0, total: int = 0):
    items_per_page = 5
    total_pages = (total + items_per_page - 1) // items_per_page
    
    keyboard = []
    for dua in duas:
        keyboard.append([InlineKeyboardButton(f"🤲 دعاء {dua['id']}", callback_data=f"dua_{dua['id'] - 1}")])
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀ السابق", callback_data=f"dpage_{page-1}"))
    nav_buttons.append(InlineKeyboardButton(f"📄 {page + 1}/{total_pages}", callback_data="ignore"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("التالي ▶", callback_data=f"dpage_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="menu_dua")])
    return InlineKeyboardMarkup(keyboard)

async def show_dua_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    try:
        await query.answer()
    except:
        pass
    
    total_duas = len(get_all_duas())
    
    text = f"<blockquote>🤲 الأدعية\n\n📋 يوجد {total_duas} دعاء في المكتبة\n\n• اضغط على 'أدعية متنوعة' للحصول على دعاء عشوائي\n• اضغط على 'قائمة الأدعية' لتصفح جميع الأدعية</blockquote>"
    
    await safe_edit_or_reply(query, text, parse_mode="HTML", reply_markup=get_dua_menu())

async def show_random_dua(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    try:
        await query.answer()
    except:
        pass
    
    duas = get_all_duas()
    random_index = random.randint(0, len(duas) - 1)
    
    user_id = update.effective_user.id
    user_dua_index[user_id] = random_index
    
    dua_text = duas[random_index]
    text = f"<blockquote>🤲 دعاء رقم {random_index + 1}:\n\n{dua_text}\n\n✨ اللهم آمين ✨</blockquote>"
    
    await safe_edit_or_reply(query, text, parse_mode="HTML", reply_markup=get_dua_navigation_buttons(random_index, len(duas)))

async def show_dua_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    try:
        await query.answer()
    except:
        pass
    
    user_id = update.effective_user.id
    page = user_dua_pages.get(user_id, 0)
    
    duas, total = get_duas_paginated(page, 5)
    total_pages = (total + 4) // 5
    
    text = f"<blockquote>📋 قائمة الأدعية (الصفحة {page + 1} من {total_pages})\n\nاختر دعاء من القائمة:</blockquote>"
    
    await safe_edit_or_reply(query, text, parse_mode="HTML", reply_markup=get_dua_list_buttons(duas, page, total))

async def show_dua_by_index(update: Update, context: ContextTypes.DEFAULT_TYPE, dua_index: int):
    query = update.callback_query
    
    duas = get_all_duas()
    
    if 0 <= dua_index < len(duas):
        user_id = update.effective_user.id
        user_dua_index[user_id] = dua_index
        
        dua_text = duas[dua_index]
        text = f"<blockquote>🤲 دعاء رقم {dua_index + 1}:\n\n{dua_text}\n\n✨ اللهم تقبل منا إنك أنت السميع العليم ✨</blockquote>"
        
        await safe_edit_or_reply(query, text, parse_mode="HTML", reply_markup=get_dua_navigation_buttons(dua_index, len(duas)))
    else:
        try:
            await query.answer("دعاء غير موجود", show_alert=True)
        except:
            pass

async def change_dua_page(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int):
    query = update.callback_query
    user_id = update.effective_user.id
    user_dua_pages[user_id] = page
    
    duas, total = get_duas_paginated(page, 5)
    total_pages = (total + 4) // 5
    
    text = f"<blockquote>📋 قائمة الأدعية (الصفحة {page + 1} من {total_pages})\n\nاختر دعاء من القائمة:</blockquote>"
    
    await safe_edit_or_reply(query, text, parse_mode="HTML", reply_markup=get_dua_list_buttons(duas, page, total))

async def dua_navigation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    if data == "ignore":
        try:
            await query.answer()
        except:
            pass
        return
    
    parts = data.split('_')
    if len(parts) < 3:
        try:
            await query.answer()
        except:
            pass
        return
    
    action = parts[1]
    current_index = int(parts[2])
    
    user_id = update.effective_user.id
    duas = get_all_duas()
    
    if action == 'prev':
        new_index = current_index - 1
    else:
        new_index = current_index + 1
    
    if new_index < 0 or new_index >= len(duas):
        try:
            await query.answer("🔚 لا يوجد المزيد من الأدعية", show_alert=True)
        except:
            pass
        return
    
    user_dua_index[user_id] = new_index
    
    dua_text = duas[new_index]
    text = f"<blockquote>🤲 دعاء رقم {new_index + 1}:\n\n{dua_text}\n\n✨ اللهم آمين ✨</blockquote>"
    
    await safe_edit_or_reply(query, text, parse_mode="HTML", reply_markup=get_dua_navigation_buttons(new_index, len(duas)))