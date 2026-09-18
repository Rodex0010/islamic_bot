# handlers/activate_handler.py
from telegram import Update
from telegram.ext import ContextTypes
from utils.scheduler import activate_chat, start_scheduler, is_chat_active

scheduler_started = False

async def activate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global scheduler_started
    
    chat_id = update.effective_chat.id
    
    if not scheduler_started:
        start_scheduler(context.application)
        scheduler_started = True
    
    if not is_chat_active(chat_id):
        activate_chat(chat_id)
        await update.message.reply_text(
            "<blockquote>✅ تم تفعيل البوت بنجاح!\n\n"
            "🕌 سيتم إرسال:\n"
            "• أذكار قصيرة (سبحان الله - الحمد لله - صلي على النبي) كل 1 دقيقة\n"
            "• أدعية متنوعة كل 30 ثانية\n"
            "• آية قرآنية كل 3 دقائق\n\n"
            "📌 لإلغاء التفعيل، قم بطرد البوت من المجموعة.\n\n"
            "يمكنك استخدام /start لفتح القائمة الرئيسية.</blockquote>",
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            "<blockquote>ℹ️ البوت مفعل بالفعل في هذه المجموعة/القناة.\n\n"
            "يتم إرسال الأذكار والأدعية والآيات بشكل تلقائي.</blockquote>",
            parse_mode="HTML"
        )