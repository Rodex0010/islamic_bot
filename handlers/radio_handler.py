# handlers/radio_handler.py - إذاعة القرآن الكريم (بث مباشر)
import io
import time
import asyncio
import logging

import aiohttp
from pyrogram.enums import ButtonStyle

from config import RADIO_URL, RADIO_NAME, RADIO_CLIP_SECONDS, CUSTOM_EMOJI_QURAN, CUSTOM_EMOJI_RECITER
from utils.ui import btn, back_btn, kb, safe_edit

log = logging.getLogger("radio")

_clip_sem = asyncio.Semaphore(3)
_busy_users = set()


def radio_markup():
    return kb([
        [btn(" استمع الآن (بث مباشر)", url=RADIO_URL, style=ButtonStyle.SUCCESS, emoji=CUSTOM_EMOJI_QURAN)],
        [btn(f" مقطع مباشر ({RADIO_CLIP_SECONDS} ثانية) هنا في الشات", "radio_clip", emoji=CUSTOM_EMOJI_RECITER)],
        [back_btn("back_main")],
    ])


async def show_radio_menu(client, query):
    await query.answer()
    text = (f"<blockquote><b>📻 {RADIO_NAME}</b>\n\n"
            "• <b>استمع الآن</b>: بيفتحلك البث المباشر في المشغّل/المتصفح.\n"
            f"• <b>مقطع مباشر</b>: البوت بيسجّل {RADIO_CLIP_SECONDS} ثانية من البث ويبعتهالك هنا كملف صوتي.</blockquote>")
    await safe_edit(client, query, text, radio_markup())


async def _record_clip(seconds: int):
    """بيقرأ البث المباشر لمدة seconds ثانية ويرجّع (bytes, extension)"""
    timeout = aiohttp.ClientTimeout(total=seconds + 30, connect=15, sock_read=20)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(RADIO_URL, headers={"User-Agent": "Mozilla/5.0"}) as resp:
            if resp.status != 200:
                raise RuntimeError(f"radio HTTP {resp.status}")
            ctype = (resp.headers.get("Content-Type") or "").lower()
            ext = "aac" if "aac" in ctype else ("ogg" if "ogg" in ctype else "mp3")
            buf = bytearray()
            end = time.monotonic() + seconds
            async for chunk in resp.content.iter_chunked(16384):
                buf.extend(chunk)
                if time.monotonic() >= end:
                    break
    return bytes(buf), ext


async def send_radio_clip(client, query):
    user_id = query.from_user.id
    if user_id in _busy_users:
        await query.answer("⏳ المقطع بيتسجل بالفعل، استنى شوية.", show_alert=True)
        return
    _busy_users.add(user_id)
    await query.answer(f"⏳ جاري تسجيل {RADIO_CLIP_SECONDS} ثانية من البث...", show_alert=False)
    status = await client.send_message(query.message.chat.id, f"⏳ جاري تسجيل مقطع من {RADIO_NAME} ...")
    try:
        async with _clip_sem:
            data, ext = await _record_clip(RADIO_CLIP_SECONDS)
        if len(data) < 10_000:
            raise RuntimeError("clip too small")
        f = io.BytesIO(data)
        f.name = f"quran_radio.{ext}"
        await client.send_audio(
            query.message.chat.id, f,
            title=f"{RADIO_NAME} - بث مباشر",
            performer="إذاعة القرآن الكريم",
            duration=RADIO_CLIP_SECONDS,
        )
        await status.delete()
    except Exception as e:
        log.warning("radio clip failed: %s", e)
        try:
            await status.edit_text("❌ مقدرتش أسجّل من الإذاعة دلوقتي، جرّب زرار «استمع الآن».")
        except Exception:
            pass
    finally:
        _busy_users.discard(user_id)
