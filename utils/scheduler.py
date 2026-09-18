# utils/scheduler.py
import re
import random
import asyncio
import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait

from config import SIRA_DAILY_HOUR, SIRA_DAILY_MINUTE, SIRA_TIMEZONE
from database import (
    get_all_active_chats,
    get_all_users,
    get_random_dua,
    get_user_last_athkar_time,
    update_user_last_athkar_time,
    get_chat_last_sent_time,
    update_chat_last_sent_time,
    remove_user,
    remove_active_chat,
)
from data.quran_api import get_random_verse

log = logging.getLogger("scheduler")

scheduler = AsyncIOScheduler()
_bot_instance = None

SHORT_ATHKAR = [
    "سبحان الله",
    "الحمد لله",
    "الله أكبر",
    "لا إله إلا الله",
    "أستغفر الله",
    "صلى الله على نبينا محمد"
]

# الفترة الحقيقية لكل جهة (بالدقائق) - كل مستخدم/جروب بيتحسب له توقيته لوحده
INTERVALS = {
    'user_athkar': 30,
    'group_athkar': 20,
    'group_dua': 15,
    'group_quran': 20,
}

# كل قد إيه الـ scheduler "بيصحى" يشوف مين جه دوره.
# لازم يكون أصغر بكتير من أصغر فترة في INTERVALS، وإلا الفترة الفعلية بتطول.
TICK_MINUTES = 1

# علامات إن المستخدم/الجروب مبقاش يقدر يستقبل رسائل (بلوك / طرد / حذف حساب / قناة خاصة)
# ملحوظة: PEER_ID_INVALID مقصود مش موجودة هنا؛ لأنها بتحصل كمان لو ملف الـ session اتمسح
# ومحتاجش نحذف مستخدمين سليمين بسببها.
_DEAD_MARKERS = (
    "chat not found",
    "forbidden",
    "bot is not a member",
    "user_is_blocked",
    "input_user_deactivated",
    "user_deactivated",
    "channel_private",
)


def set_bot_instance(bot):
    global _bot_instance
    _bot_instance = bot


# ------------------------------------------------------------------ helpers
def _to_datetime(value):
    """بيحوّل القيمة اللي جاية من الداتابيز لـ datetime عادي (بدون timezone)"""
    if value is None:
        return None
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return None
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is not None:
        value = value.astimezone().replace(tzinfo=None)
    return value


def _minutes_since(last_sent: datetime, now: datetime) -> float:
    return (now - last_sent).total_seconds() / 60


def _is_dead_peer(error: Exception) -> bool:
    text = f"{getattr(error, 'ID', '')} {error}".lower()
    return any(marker in text for marker in _DEAD_MARKERS)


async def _send_html(chat_id, text: str) -> str:
    """
    بيبعت رسالة HTML.
    بيرجّع: 'ok' لو اتبعتت، 'dead' لو الجهة مبقتش تستقبل، 'failed' لأي خطأ تاني.
    """
    for _ in range(2):
        try:
            await _bot_instance.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=ParseMode.HTML
            )
            return "ok"
        except FloodWait as e:
            log.warning("FloodWait %ss while sending to %s", e.value, chat_id)
            await asyncio.sleep(e.value + 1)
        except Exception as e:
            if _is_dead_peer(e):
                return "dead"
            if "invalid parse mode" in str(e).lower():
                try:
                    plain = re.sub(r"<[^>]+>", "", text)
                    await _bot_instance.send_message(chat_id=chat_id, text=plain)
                    return "ok"
                except Exception as e2:
                    if _is_dead_peer(e2):
                        return "dead"
                    log.warning("plain send to %s failed: %s", chat_id, e2)
                    return "failed"
            log.warning("send to %s failed: %s", chat_id, e)
            return "failed"
    return "failed"


# ------------------------------------------------------------------ users
async def send_to_users_with_smart_timing():
    if not _bot_instance:
        return

    users = get_all_users()
    if not users:
        return

    now = datetime.now()
    interval_minutes = INTERVALS['user_athkar']

    for user_id in users:
        last_sent = _to_datetime(get_user_last_athkar_time(user_id))

        if last_sent is not None and _minutes_since(last_sent, now) < interval_minutes:
            continue

        athkar = random.choice(SHORT_ATHKAR)
        result = await _send_html(user_id, f"<blockquote>{athkar}</blockquote>")

        if result == "dead":
            remove_user(user_id)
        else:
            # حتى لو فشل الإرسال لسبب مؤقت بنسجل الوقت، عشان ميحاولش كل دقيقة
            update_user_last_athkar_time(user_id)

        await asyncio.sleep(0.2)


# ------------------------------------------------------------------ chats
async def _build_group_text(msg_type: str):
    if msg_type == 'athkar':
        content = random.choice(SHORT_ATHKAR)
        return f"<blockquote>{content}</blockquote>"

    if msg_type == 'dua':
        dua = get_random_dua()
        return f"<blockquote>🤲 {dua}</blockquote>"

    if msg_type == 'quran':
        try:
            verse = await get_random_verse()
        except Exception as e:
            log.warning("get_random_verse failed: %s", e)
            verse = None
        if not verse:
            verse = "﴿ إِنَّ اللَّهَ مَعَ الصَّابِرِينَ ﴾"
        return f"<blockquote>{verse}</blockquote>"

    return None


async def send_to_chats_with_smart_timing(msg_type: str = 'athkar'):
    if not _bot_instance:
        return
    if msg_type not in ('athkar', 'dua', 'quran'):
        return

    chats = get_all_active_chats()
    if not chats:
        return

    now = datetime.now()
    interval_minutes = INTERVALS.get(f'group_{msg_type}', 20)

    # الأول نحدد مين جه دوره، ومنجيبش آية/دعاء جديد من الـ API إلا لو فيه حد محتاجه
    due_chats = []
    for chat_id in chats:
        last_sent = _to_datetime(get_chat_last_sent_time(chat_id, msg_type))
        if last_sent is None or _minutes_since(last_sent, now) >= interval_minutes:
            due_chats.append(chat_id)

    if not due_chats:
        return

    text = await _build_group_text(msg_type)
    if not text:
        return

    for chat_id in due_chats:
        result = await _send_html(chat_id, text)

        if result == "dead":
            remove_active_chat(chat_id)
        else:
            update_chat_last_sent_time(chat_id, msg_type)

        await asyncio.sleep(0.2)


# ------------------------------------------------------------------ jobs
async def user_athkar_smart_job():
    await send_to_users_with_smart_timing()


async def group_athkar_smart_job():
    await send_to_chats_with_smart_timing('athkar')


async def group_dua_smart_job():
    await send_to_chats_with_smart_timing('dua')


async def group_quran_smart_job():
    await send_to_chats_with_smart_timing('quran')


async def daily_sira_job():
    """قصة اليوم من السيرة النبوية (مرة كل يوم)"""
    from handlers.sira_handler import daily_sira_broadcast
    if _bot_instance:
        await daily_sira_broadcast(_bot_instance)


def start_scheduler(bot):
    global _bot_instance
    _bot_instance = bot

    # ملحوظة: إصلاح last_sent للمستخدمين والجروبات بيتعمل في bot.py قبل ما نيجي هنا،
    # فمحتاجش نكرره (كان بيتطبع مرتين في اللوج).

    if not scheduler.running:
        common = dict(
            trigger=IntervalTrigger(minutes=TICK_MINUTES),
            replace_existing=True,
            max_instances=1,   # نسخة واحدة بس عشان مفيش رسائل مكررة لو الدورة اتأخرت
            coalesce=True,
        )

        scheduler.add_job(user_athkar_smart_job, id="user_athkar_smart", **common)
        scheduler.add_job(group_athkar_smart_job, id="group_athkar_smart", **common)
        scheduler.add_job(group_dua_smart_job, id="group_dua_smart", **common)
        scheduler.add_job(group_quran_smart_job, id="group_quran_smart", **common)

        scheduler.add_job(
            daily_sira_job,
            trigger=CronTrigger(hour=SIRA_DAILY_HOUR, minute=SIRA_DAILY_MINUTE, timezone=SIRA_TIMEZONE),
            id="daily_sira",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=6 * 3600
        )

        scheduler.start()
        print("✅ Smart Scheduler started successfully!")
        print(f"📌 قصة اليوم (السيرة) كل يوم الساعة {SIRA_DAILY_HOUR:02d}:{SIRA_DAILY_MINUTE:02d} ({SIRA_TIMEZONE})")
        print(f"📌 أذكار المستخدمين كل {INTERVALS['user_athkar']} دقيقة (موزعة)")
        print(f"📌 أذكار المجموعات كل {INTERVALS['group_athkar']} دقيقة (موزعة)")
        print(f"📌 أدعية المجموعات كل {INTERVALS['group_dua']} دقيقة (موزعة)")
        print(f"📌 آيات المجموعات كل {INTERVALS['group_quran']} دقيقة (موزعة)")
        print("📌 كل جهة لها توقيت مستقل حسب وقت الانضمام")
