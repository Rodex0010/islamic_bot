# handlers/extras.py - ربط الميزات الجديدة (السيرة / الشعراوي / الإذاعة / إذاعة الأدمن) ببوت.py
import logging

from handlers import sira_handler, sharawi_handler, radio_handler, broadcast_handler

log = logging.getLogger("extras")


def _split_vid_page(payload: str):
    """'<videoId>_<page>' - الـ videoId ممكن يحتوي على _ فبنقسم من اليمين"""
    vid, page = payload.rsplit("_", 1)
    return vid, int(page)


async def handle_extra_callback(client, query) -> bool:
    """بيرجّع True لو الكولباك ده بتاع الميزات الجديدة وتم التعامل معاه"""
    d = query.data or ""
    if isinstance(d, bytes):
        d = d.decode()

    try:
        # ---------------- السيرة النبوية
        if d == "menu_sira":
            await sira_handler.show_sira_menu(client, query)
        elif d == "sira_today":
            await sira_handler.show_today(client, query)
        elif d == "sira_cats":
            await sira_handler.show_categories(client, query)
        elif d.startswith("sira_c_"):
            _, _, cid, page = d.split("_")
            await sira_handler.show_category(client, query, int(cid), int(page))
        elif d.startswith("sira_a_"):
            _, _, aid, pg, cid, lp = d.split("_")
            await sira_handler.show_article(client, query, int(aid), int(pg), int(cid), int(lp))

        # ---------------- الشعراوي
        elif d == "menu_sharawi":
            await sharawi_handler.show_sharawi_list(client, query, 0)
        elif d.startswith("shw_p_"):
            await sharawi_handler.show_sharawi_list(client, query, int(d[len("shw_p_"):]))
        elif d.startswith("shw_v_"):
            vid, page = _split_vid_page(d[len("shw_v_"):])
            await sharawi_handler.show_video_card(client, query, vid, page)
        elif d.startswith("shw_d_"):
            vid, page = _split_vid_page(d[len("shw_d_"):])
            await sharawi_handler.start_download(client, query, vid, page)
        elif d.startswith("shw_c_"):
            vid, page = _split_vid_page(d[len("shw_c_"):])
            await sharawi_handler.cancel_download(client, query, vid, page)

        # ---------------- الإذاعة (بث القرآن)
        elif d == "menu_radio":
            await radio_handler.show_radio_menu(client, query)
        elif d == "radio_clip":
            await radio_handler.send_radio_clip(client, query)

        # ---------------- إذاعة رسالة (أدمن)
        elif d == "menu_broadcast":
            await broadcast_handler.show_broadcast_menu(client, query)
        elif d == "bc_confirm":
            await broadcast_handler.confirm_broadcast(client, query)
        elif d == "bc_cancel":
            await broadcast_handler.cancel_broadcast(client, query)
        else:
            return False
    except Exception as e:
        if "MESSAGE_NOT_MODIFIED" in str(e):
            return True
        log.exception("extra callback failed: %s", d)
        try:
            await query.answer("❌ حصل خطأ، جرّب تاني", show_alert=True)
        except Exception:
            pass
    return True


def register_extra_handlers(bot):
    broadcast_handler.register(bot)


async def open_from_start(client, message, payload: str) -> bool:
    """deep-link: /start sira_<id>  (بيتفتح من زرار «اقرأ القصة كاملة» في الجروبات)"""
    if payload.startswith("sira_"):
        try:
            aid = int(payload[5:])
        except ValueError:
            return False
        sent = await sira_handler.send_article_message(client, message.chat.id, aid)
        return sent is not None
    return False
