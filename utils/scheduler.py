# utils/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
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
    get_chat_activation_time,
    fix_missing_last_sent_for_users,
    fix_missing_last_sent_for_chats
)
from data.quran_api import get_random_verse
from pyrogram.enums import ParseMode
import random
import asyncio
from datetime import datetime, timedelta

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

INTERVALS = {
    'user_athkar': 30,
    'group_athkar': 20,
    'group_dua': 15,
    'group_quran': 20,
}

def set_bot_instance(bot):
    global _bot_instance
    _bot_instance = bot

async def send_to_users_with_smart_timing():
    global _bot_instance
    if not _bot_instance:
        return

    users = get_all_users()
    if not users:
        return

    now = datetime.now()
    interval_minutes = INTERVALS['user_athkar']
    
    for user_id in users:
        last_sent = get_user_last_athkar_time(user_id)
        
        if last_sent is None:
            should_send = True
            update_user_last_athkar_time(user_id)
        else:
            time_diff = (now - last_sent).total_seconds() / 60
            should_send = time_diff >= interval_minutes
        
        if should_send:
            athkar = random.choice(SHORT_ATHKAR)
            text = f"<blockquote>{athkar}</blockquote>"
            
            try:
                await _bot_instance.send_message(
                    chat_id=user_id,
                    text=text,
                    parse_mode=ParseMode.HTML
                )
                update_user_last_athkar_time(user_id)
                await asyncio.sleep(0.2)
                
            except Exception as e:
                error_msg = str(e).lower()
                if "chat not found" in error_msg or "forbidden" in error_msg or "bot is not a member" in error_msg:
                    remove_user(user_id)
                elif "invalid parse mode" in error_msg:
                    try:
                        await _bot_instance.send_message(
                            chat_id=user_id,
                            text=text
                        )
                        update_user_last_athkar_time(user_id)
                    except:
                        pass
                else:
                    pass

async def send_to_chats_with_smart_timing(msg_type: str = 'athkar'):
    global _bot_instance
    if not _bot_instance:
        return

    chats = get_all_active_chats()
    if not chats:
        return

    now = datetime.now()
    interval_minutes = INTERVALS.get(f'group_{msg_type}', 20)
    
    if msg_type == 'athkar':
        content = random.choice(SHORT_ATHKAR)
        text = f"<blockquote>{content}</blockquote>"
    elif msg_type == 'dua':
        dua = get_random_dua()
        text = f"<blockquote>🤲 {dua}</blockquote>"
    elif msg_type == 'quran':
        verse = await get_random_verse()
        if not verse:
            verse = "﴿ إِنَّ اللَّهَ مَعَ الصَّابِرِينَ ﴾"
        text = f"<blockquote>{verse}</blockquote>"
    else:
        return
    
    for chat_id in chats:
        last_sent = get_chat_last_sent_time(chat_id, msg_type)
        
        if last_sent is None:
            should_send = True
        else:
            time_diff = (now - last_sent).total_seconds() / 60
            should_send = time_diff >= interval_minutes
        
        if should_send:
            try:
                await _bot_instance.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode=ParseMode.HTML
                )
                update_chat_last_sent_time(chat_id, msg_type)
                await asyncio.sleep(0.2)
                
            except Exception as e:
                error_msg = str(e).lower()
                if "chat not found" in error_msg or "forbidden" in error_msg or "bot is not a member" in error_msg:
                    remove_active_chat(chat_id)
                elif "invalid parse mode" in error_msg:
                    try:
                        await _bot_instance.send_message(
                            chat_id=chat_id,
                            text=text
                        )
                        update_chat_last_sent_time(chat_id, msg_type)
                    except:
                        pass
                else:
                    pass

async def user_athkar_smart_job():
    await send_to_users_with_smart_timing()

async def group_athkar_smart_job():
    await send_to_chats_with_smart_timing('athkar')

async def group_dua_smart_job():
    await send_to_chats_with_smart_timing('dua')

async def group_quran_smart_job():
    await send_to_chats_with_smart_timing('quran')

def start_scheduler(bot):
    global _bot_instance
    _bot_instance = bot

    # إصلاح المستخدمين والجروبات اللي مفشلين
    try:
        fix_missing_last_sent_for_users()
        fix_missing_last_sent_for_chats()
    except:
        pass

    if not scheduler.running:
        scheduler.add_job(
            user_athkar_smart_job,
            trigger=IntervalTrigger(minutes=25),
            id="user_athkar_smart",
            replace_existing=True,
            max_instances=3
        )
        
        scheduler.add_job(
            group_athkar_smart_job,
            trigger=IntervalTrigger(minutes=30),
            id="group_athkar_smart",
            replace_existing=True,
            max_instances=3
        )
        
        scheduler.add_job(
            group_dua_smart_job,
            trigger=IntervalTrigger(minutes=25),
            id="group_dua_smart",
            replace_existing=True,
            max_instances=3
        )
        
        scheduler.add_job(
            group_quran_smart_job,
            trigger=IntervalTrigger(minutes=45),
            id="group_quran_smart",
            replace_existing=True,
            max_instances=3
        )
        
        scheduler.start()
        print("✅ Smart Scheduler started successfully!")
        print(f"📌 أذكار المستخدمين كل {INTERVALS['user_athkar']} دقيقة (موزعة)")
        print(f"📌 أذكار المجموعات كل {INTERVALS['group_athkar']} دقيقة (موزعة)")
        print(f"📌 أدعية المجموعات كل {INTERVALS['group_dua']} دقيقة (موزعة)")
        print(f"📌 آيات المجموعات كل {INTERVALS['group_quran']} دقيقة (موزعة)")
        print("📌 كل جهة لها توقيت مستقل حسب وقت الانضمام")