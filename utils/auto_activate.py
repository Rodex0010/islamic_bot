import json
import os
from utils.scheduler import activate_chat, deactivate_chat, is_chat_active

ACTIVE_CHATS_FILE = "active_chats.json"

def save_all_active_chats(active_chats_set):
    """حفظ كل الشاتات المفعلة في ملف"""
    try:
        with open(ACTIVE_CHATS_FILE, "w", encoding="utf-8") as f:
            json.dump({"active_chats": list(active_chats_set)}, f, ensure_ascii=False, indent=2)
        print(f"💾 Saved {len(active_chats_set)} active chats")
    except Exception as e:
        print(f"Error saving: {e}")

def load_all_active_chats():
    """تحميل الشاتات المفعلة من الملف (لما السيرفر يشتغل تاني)"""
    if os.path.exists(ACTIVE_CHATS_FILE):
        try:
            with open(ACTIVE_CHATS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return set(data.get("active_chats", []))
        except:
            return set()
    return set()

# الدالة اللي البوت بيستدعيها
async def check_and_auto_activate(context, chat_id, bot_username):
    """التحقق من صلاحيات البوت وتفعيله تلقائياً"""
    try:
        chat_member = await context.bot.get_chat_member(chat_id, bot_username)
        if chat_member.status in ['administrator', 'member']:
            if not is_chat_active(chat_id):
                activate_chat(chat_id)
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="✅ *تم تفعيل البوت تلقائياً!*\n\n"
                         "⏰ سيتم إرسال التذكيرات الدينية والآيات القرآنية.\n\n"
                         "استخدم /start في الخاص للاستفادة من جميع الميزات.",
                    parse_mode="Markdown"
                )
                return True
    except Exception as e:
        print(f"Error checking auto activate: {e}")
    return False