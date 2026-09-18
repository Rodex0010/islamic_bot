# utils/ui.py - أدوات مشتركة للأزرار وتعديل الرسائل بشكل آمن
import html
from pyrogram.enums import ButtonStyle
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from config import CUSTOM_EMOJI_BACK


def btn(text, data=None, style=ButtonStyle.PRIMARY, emoji=None, url=None):
    """زرار بنفس ستايل البوت (لون + ايموجي بريميوم اختياري)"""
    kw = {"style": style}
    if emoji:
        kw["icon_custom_emoji_id"] = emoji
    if url:
        kw["url"] = url
    else:
        kw["callback_data"] = data
    return InlineKeyboardButton(text, **kw)


def back_btn(data="back_main", text=" رجوع"):
    return btn(text, data, style=ButtonStyle.DANGER, emoji=CUSTOM_EMOJI_BACK)


def kb(rows):
    return InlineKeyboardMarkup(rows)


def esc(text: str) -> str:
    return html.escape(text or "", quote=False)


def short(text: str, n: int = 55) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= n else text[: n - 1] + "…"


async def safe_edit(client, query, text: str, markup=None):
    """يعدّل رسالة الزرار (نص أو صورة بكابشن) وإلا يمسحها ويبعت جديدة"""
    msg = query.message
    text = text[:4090]
    try:
        if msg.photo or msg.video or msg.audio or msg.document or msg.animation:
            if len(text) > 1024:
                raise ValueError("caption too long")
            await msg.edit_caption(text, reply_markup=markup)
        else:
            await msg.edit_text(text, reply_markup=markup, disable_web_page_preview=True)
        return msg
    except Exception as e:
        if "MESSAGE_NOT_MODIFIED" in str(e):
            return msg
    try:
        await msg.delete()
    except Exception:
        pass
    return await client.send_message(msg.chat.id, text, reply_markup=markup,
                                     disable_web_page_preview=True)
