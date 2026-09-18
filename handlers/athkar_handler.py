# handlers/athkar_handler.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import get_athkar_by_type
from utils.helpers import safe_edit_or_reply

def get_athkar_menu():
    keyboard = [
        [
            InlineKeyboardButton("🌅 أذكار الصباح", callback_data="athkar_morning"),
            InlineKeyboardButton("🌙 أذكار المساء", callback_data="athkar_evening")
        ],
        [
            InlineKeyboardButton("📜 أذكار متنوعة", callback_data="athkar_other")
        ],
        [
            InlineKeyboardButton("🔙 رجوع", callback_data="back_main")
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_navigation_buttons(athkar_type: str, current_index: int, total: int):
    buttons = []
    
    if current_index > 0:
        buttons.append(InlineKeyboardButton("◀️ السابق", callback_data=f"{athkar_type}_prev_{current_index}"))
    
    buttons.append(InlineKeyboardButton(f"{current_index + 1}/{total}", callback_data="ignore"))
    
    if current_index < total - 1:
        buttons.append(InlineKeyboardButton("التالي ▶️", callback_data=f"{athkar_type}_next_{current_index}"))
    
    keyboard = [buttons]
    keyboard.append([
        InlineKeyboardButton("🔙 قائمة الأذكار", callback_data="menu_athkar"),
        InlineKeyboardButton("🏠 الرئيسية", callback_data="back_main")
    ])
    
    return InlineKeyboardMarkup(keyboard)

async def show_athkar_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = "<blockquote>🕋 اختر نوع الأذكار:\n\n🌅 أذكار الصباح - تُقال عند الاستيقاظ\n🌙 أذكار المساء - تُقال عند المساء\n📜 أذكار متنوعة - أدعية وأذكار عامة</blockquote>"
    
    await safe_edit_or_reply(query, text, parse_mode="HTML", reply_markup=get_athkar_menu())

async def show_morning(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    athkar_list = get_athkar_by_type("morning")
    
    if not athkar_list:
        await safe_edit_or_reply(query, "<blockquote>❌ لا توجد أذكار صباح حالياً</blockquote>", parse_mode="HTML", reply_markup=get_athkar_menu())
        return
    
    context.user_data['morning_list'] = athkar_list
    current_zikr = athkar_list[0]
    text = f"<blockquote>🌅 أذكار الصباح\n\n{current_zikr}</blockquote>"
    
    await safe_edit_or_reply(query, text, parse_mode="HTML", reply_markup=get_navigation_buttons("morning", 0, len(athkar_list)))

async def show_evening(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    athkar_list = get_athkar_by_type("evening")
    
    if not athkar_list:
        await safe_edit_or_reply(query, "<blockquote>❌ لا توجد أذكار مساء حالياً</blockquote>", parse_mode="HTML", reply_markup=get_athkar_menu())
        return
    
    context.user_data['evening_list'] = athkar_list
    current_zikr = athkar_list[0]
    text = f"<blockquote>🌙 أذكار المساء\n\n{current_zikr}</blockquote>"
    
    await safe_edit_or_reply(query, text, parse_mode="HTML", reply_markup=get_navigation_buttons("evening", 0, len(athkar_list)))

async def show_other(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    athkar_list = get_athkar_by_type("other")
    
    if not athkar_list:
        await safe_edit_or_reply(query, "<blockquote>❌ لا توجد أذكار متنوعة حالياً</blockquote>", parse_mode="HTML", reply_markup=get_athkar_menu())
        return
    
    context.user_data['other_list'] = athkar_list
    current_zikr = athkar_list[0]
    text = f"<blockquote>📜 أذكار متنوعة\n\n{current_zikr}</blockquote>"
    
    await safe_edit_or_reply(query, text, parse_mode="HTML", reply_markup=get_navigation_buttons("other", 0, len(athkar_list)))

async def navigation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    if data == "ignore":
        await query.answer()
        return
    
    parts = data.split('_')
    if len(parts) < 3:
        await query.answer()
        return
    
    athkar_type = parts[0]
    action = parts[1]
    current_index = int(parts[2])
    
    if action == 'prev':
        new_index = current_index - 1
    else:
        new_index = current_index + 1
    
    athkar_list = get_athkar_by_type(athkar_type)
    
    if new_index < 0 or new_index >= len(athkar_list):
        await query.answer("🔚 لا يوجد المزيد من الأذكار", show_alert=True)
        return
    
    titles = {
        "morning": "🌅 أذكار الصباح",
        "evening": "🌙 أذكار المساء",
        "other": "📜 أذكار متنوعة"
    }
    title = titles.get(athkar_type, "📖 أذكار")
    
    current_zikr = athkar_list[new_index]
    text = f"<blockquote>{title}\n\n{current_zikr}</blockquote>"
    
    await safe_edit_or_reply(query, text, parse_mode="HTML", reply_markup=get_navigation_buttons(athkar_type, new_index, len(athkar_list)))