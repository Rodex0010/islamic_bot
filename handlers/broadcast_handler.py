# handlers/broadcast_handler.py - إذاعة رسالة لكل المستخدمين والجروبات والقنوات (للأدمن فقط)
import asyncio
import logging

from pyrogram import filters
from pyrogram.enums import ButtonStyle
from pyrogram.errors import FloodWait
from pyrogram.handlers import MessageHandler

from config import ADMIN_IDS, CUSTOM_EMOJI_DEVELOPER
from database import get_all_users, get_all_active_chats
from utils.ui import btn, back_btn, kb, safe_edit

log = logging.getLogger("broadcast")

_awaiting = set()          # الأدمن اللي البوت مستني منه الرسالة
_pending = {}              # admin_id -> (from_chat_id, message_id)
_running = False


def is_admin(user_id) -> bool:
    return user_id in ADMIN_IDS


def targets():
    users = list(dict.fromkeys(get_all_users()))
    chats = [c for c in dict.fromkeys(get_all_active_chats()) if c not in set(users)]
    return users, chats


def broadcast_button():
    """الزرار اللي بيتضاف للقائمة الرئيسية للأدمن بس"""
    return btn(" إذاعة رسالة", "menu_broadcast", ButtonStyle.SUCCESS, CUSTOM_EMOJI_DEVELOPER)


async def show_broadcast_menu(client, query):
    if not is_admin(query.from_user.id):
        await query.answer("❌ الزر ده للأدمن بس", show_alert=True)
        return
    await query.answer()
    _awaiting.add(query.from_user.id)
    _pending.pop(query.from_user.id, None)
    users, chats = targets()
    text = (f"<blockquote><b>📢 إذاعة رسالة</b>\n\n"
            f"👤 مستخدمين: {len(users)}\n👥 جروبات/قنوات: {len(chats)}\n\n"
            "ابعتلي دلوقتي الرسالة اللي عايز تذيعها (نص / صورة / فيديو / ملف / صوت ...) "
            "وهتظهرلك معاينة قبل الإرسال.</blockquote>")
    await safe_edit(client, query, text, kb([[btn("❌ إلغاء", "bc_cancel", ButtonStyle.DANGER)]]))


async def _capture(client, message):
    """بيلتقط رسالة الأدمن ويعرضها كمعاينة"""
    uid = message.from_user.id
    _awaiting.discard(uid)
    _pending[uid] = (message.chat.id, message.id)
    users, chats = targets()
    try:
        await message.copy(message.chat.id)  # معاينة
    except Exception:
        pass
    await client.send_message(
        message.chat.id,
        f"<blockquote><b>📢 تأكيد الإذاعة</b>\n\nالمعاينة فوق ⬆️\n"
        f"هتتبعت لـ {len(users)} مستخدم و {len(chats)} جروب/قناة.</blockquote>",
        reply_markup=kb([[btn("✅ تأكيد الإرسال", "bc_confirm", ButtonStyle.SUCCESS),
                          btn("❌ إلغاء", "bc_cancel", ButtonStyle.DANGER)]]),
    )


async def _is_awaiting(_, __, message):
    return bool(message.from_user and message.from_user.id in _awaiting)

awaiting_filter = filters.create(_is_awaiting)


def register(bot):
    """بيسجّل هاندلر التقاط رسالة الأدمن (group=1 عشان ميتعارضش مع باقي الهاندلرز)"""
    bot.add_handler(MessageHandler(
        _capture,
        filters.private & filters.user(ADMIN_IDS) & awaiting_filter & ~filters.command(["start"]),
    ), group=1)


async def cancel_broadcast(client, query):
    if not is_admin(query.from_user.id):
        await query.answer("❌ للأدمن بس", show_alert=True)
        return
    _awaiting.discard(query.from_user.id)
    _pending.pop(query.from_user.id, None)
    await query.answer("تم الإلغاء")
    try:
        await query.message.edit_text("<blockquote>❌ تم إلغاء الإذاعة.</blockquote>",
                                      reply_markup=kb([[back_btn("back_main", " الرئيسية")]]))
    except Exception:
        pass


async def confirm_broadcast(client, query):
    global _running
    uid = query.from_user.id
    if not is_admin(uid):
        await query.answer("❌ للأدمن بس", show_alert=True)
        return
    if _running:
        await query.answer("⏳ في إذاعة شغالة دلوقتي، استنى لحد ما تخلص.", show_alert=True)
        return
    src = _pending.pop(uid, None)
    if not src:
        await query.answer("❌ مفيش رسالة معلّقة، ابدأ من جديد.", show_alert=True)
        return
    await query.answer("🚀 بدأت الإذاعة")
    _running = True
    asyncio.create_task(_run_broadcast(client, query.message, src))


async def _run_broadcast(client, status_msg, src):
    global _running
    from_chat, msg_id = src
    users, chats = targets()
    all_targets = users + chats
    total = len(all_targets)
    sent = failed = 0

    async def status(text):
        try:
            await status_msg.edit_text(text, reply_markup=None)
        except Exception:
            pass

    try:
        for i, chat_id in enumerate(all_targets, 1):
            for _ in range(3):
                try:
                    await client.copy_message(chat_id, from_chat, msg_id)
                    sent += 1
                    break
                except FloodWait as e:
                    await asyncio.sleep(e.value + 1)
                except Exception:
                    failed += 1
                    break
            await asyncio.sleep(0.06)
            if i % 25 == 0:
                await status(f"<blockquote>🚀 جاري الإذاعة... {i}/{total}\n✅ {sent}  ❌ {failed}</blockquote>")
        await status(f"<blockquote><b>✅ انتهت الإذاعة</b>\n\n📨 اتبعتت: {sent}\n❌ فشلت: {failed}\n📊 الإجمالي: {total}</blockquote>")
    except Exception as e:
        log.warning("broadcast crashed: %s", e)
        await status(f"<blockquote>❌ الإذاعة وقفت بخطأ: {e}\n✅ {sent}  ❌ {failed}</blockquote>")
    finally:
        _running = False
