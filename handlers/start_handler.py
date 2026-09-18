# handlers/start_handler.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from utils.keyboards import get_main_menu, get_main_menu_text, BOT_IMAGE_URL
from database import add_user, user_exists
from utils.scheduler import activate_chat, is_chat_active

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name
    username = update.effective_user.username
    
    if not user_exists(user_id):
        add_user(user_id, first_name, username)
        print(f"✅ New user added: {first_name} (@{username}) - ID: {user_id}")
    
    keyboard = get_main_menu()
    
    try:
        await update.message.reply_photo(
            photo=BOT_IMAGE_URL,
            caption=get_main_menu_text(),
            parse_mode="HTML",
            reply_markup=keyboard
        )
    except Exception as e:
        print(f"Error sending photo: {e}")
        await update.message.reply_text(
            get_main_menu_text(),
            parse_mode="HTML",
            reply_markup=keyboard
        )

async def show_how_to_add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    if query is None:
        return
    
    try:
        await query.answer()
    except:
        pass
    
    channel_id = "-1002751482940"
    command = f"/forceadd {channel_id}"
    
    text = f"""<blockquote>
✅ <b>لتفعيل البوت في الجروب:</b>
اكتب كلمة <b>تفعيل</b> في الجروب
</blockquote>

<blockquote>
📢 <b>ضيف البوت أدمن في قناتك؟</b>
✅ <b>بعدها سيتم التفعيل تلقائياً!</b>
</blockquote>

<blockquote>
انسخ الأمر التالي وأرسله في الخاص مع البوت:

<code>{command}</code>
</blockquote>"""
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="back_main")]
    ])
    
    try:
        await query.edit_message_text(
            text=text,
            parse_mode="HTML",
            reply_markup=keyboard
        )
    except Exception as e:
        try:
            await query.message.delete()
        except:
            pass
        
        await query.message.reply_text(
            text=text,
            parse_mode="HTML",
            reply_markup=keyboard
        )

async def activate_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تفعيل الجروب بكلمة تفعيل"""
    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type
    
    if chat_type == "channel":
        await update.message.reply_text(
            "<blockquote>❌ لا يمكن التفعيل بالكتابة في القنوات.\n\n✅ فقط قم برفع البوت أدمن في القناة وسيتم التفعيل تلقائياً.</blockquote>",
            parse_mode="HTML"
        )
        return
    
    if not is_chat_active(chat_id):
        activate_chat(chat_id)
        await update.message.reply_text(
            "<blockquote>✅ تم تفعيل البوت بنجاح!\n\n"
            "🕌 سيتم إرسال:\n"
            "• أذكار قصيرة كل 5 دقائق\n"
            "• أدعية متنوعة كل 10 دقائق\n"
            "• آية قرآنية كل 15 دقيقة\n"
            "• تذكير قبل كل صلاة بـ 10 دقائق\n\n"
            "يمكنك استخدام /start لفتح القائمة الرئيسية</blockquote>",
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            "<blockquote>ℹ️ البوت مفعل بالفعل في هذه المجموعة.\n\n"
            "يتم إرسال الأذكار والأدعية والآيات بشكل تلقائي.</blockquote>",
            parse_mode="HTML"
        )