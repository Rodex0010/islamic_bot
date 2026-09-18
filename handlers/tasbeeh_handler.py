# handlers/tasbeeh_handler.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import TASBEEH_WORDS, TASBEEH_CHANGE_AFTER
from database import get_tasbeeh, update_tasbeeh, reset_tasbeeh_count
from utils.helpers import safe_edit_or_reply

def get_tasbeeh_buttons(current_word: str, count: int):
    keyboard = [
        [InlineKeyboardButton(f"📿 {current_word}", callback_data="tasbeeh_click")],
        [InlineKeyboardButton("📊 إعادة تعيين العداد", callback_data="tasbeeh_reset_count")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)

async def show_tasbeeh_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    data = get_tasbeeh(user_id)
    current_word = TASBEEH_WORDS[data["word_index"]]
    
    text = (
        f"<blockquote>📿 التسبيح\n\n"
        f"• الذكر الحالي: {current_word}\n"
        f"• عدد التسبيحات: {data['count']}\n\n"
        f"📌 كل {TASBEEH_CHANGE_AFTER} تسبيحات يتغير الذكر تلقائياً\n"
        f"💡 اضغط على الذكر للتسبيح</blockquote>"
    )
    
    await safe_edit_or_reply(query, text, parse_mode="HTML", reply_markup=get_tasbeeh_buttons(current_word, data['count']))

async def tasbeeh_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    
    data = get_tasbeeh(user_id)
    new_count = data["count"] + 1
    word_index = data["word_index"]
    
    if new_count % TASBEEH_CHANGE_AFTER == 0:
        word_index = (word_index + 1) % len(TASBEEH_WORDS)
        new_word = TASBEEH_WORDS[word_index]
        await query.answer(f"🎉 مبارك! تم تغيير الذكر تلقائياً إلى: {new_word}", show_alert=True)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"<blockquote>🎉 تهانينا!\n\nأتممت {TASBEEH_CHANGE_AFTER} تسبيحات\nجزاك الله خيراً</blockquote>",
            parse_mode="HTML"
        )
    else:
        await query.answer(f"📿 تسبيحة رقم {new_count}", show_alert=False)
    
    update_tasbeeh(user_id, new_count, word_index)
    
    current_word = TASBEEH_WORDS[word_index]
    text = (
        f"<blockquote>📿 التسبيح\n\n"
        f"• الذكر الحالي: {current_word}\n"
        f"• عدد التسبيحات: {new_count}\n\n"
        f"📌 كل {TASBEEH_CHANGE_AFTER} تسبيحات يتغير الذكر تلقائياً\n"
        f"💡 اضغط على الذكر للتسبيح</blockquote>"
    )
    
    await safe_edit_or_reply(query, text, parse_mode="HTML", reply_markup=get_tasbeeh_buttons(current_word, new_count))

async def tasbeeh_reset_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("📊 تم إعادة تعيين العداد", show_alert=True)
    user_id = update.effective_user.id
    
    reset_tasbeeh_count(user_id)
    data = get_tasbeeh(user_id)
    current_word = TASBEEH_WORDS[data["word_index"]]
    
    text = (
        f"<blockquote>📿 التسبيح\n\n"
        f"• الذكر الحالي: {current_word}\n"
        f"• عدد التسبيحات: 0\n\n"
        f"📌 كل {TASBEEH_CHANGE_AFTER} تسبيحات يتغير الذكر تلقائياً\n"
        f"💡 اضغط على الذكر للتسبيح</blockquote>"
    )
    
    await safe_edit_or_reply(query, text, parse_mode="HTML", reply_markup=get_tasbeeh_buttons(current_word, 0))