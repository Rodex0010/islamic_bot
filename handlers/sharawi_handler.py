# handlers/sharawi_handler.py - خطب الشيخ الشعراوي من يوتيوب (تحميل وإرسال فيديو)
import os
import time
import json
import asyncio
import logging
import threading
from typing import Dict, List, Optional

from pyrogram.enums import ButtonStyle

from config import (
    SHARAWI_CHANNEL_URL, SHARAWI_PER_PAGE, SHARAWI_MAX_PARALLEL, SHARAWI_MAX_HEIGHT,
    SHARAWI_MAX_FILESIZE, YT_COOKIES_FILE, DOWNLOAD_DIR, CACHE_DIR,
    CUSTOM_EMOJI_RECITER, CUSTOM_EMOJI_NEXT, CUSTOM_EMOJI_Bx, CUSTOM_EMOJI_BACK,
)
from utils.ui import btn, back_btn, kb, esc, short, safe_edit

log = logging.getLogger("sharawi")

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

VIDEOS_CACHE = os.path.join(CACHE_DIR, "sharawi_videos.json")
FILEID_CACHE = os.path.join(CACHE_DIR, "sharawi_file_ids.json")
LIST_TTL = 6 * 3600

_sem = asyncio.Semaphore(SHARAWI_MAX_PARALLEL)
_list_lock = asyncio.Lock()
_file_ids: Dict[str, str] = {}

# التحميلات الشغالة:  (chat_id, message_id) -> {"cancel": Event, "user": id}
_jobs: Dict[tuple, dict] = {}
_user_busy: Dict[int, tuple] = {}


try:
    from yt_dlp.utils import DownloadCancelled as _CancelBase
except Exception:  # yt-dlp مش متسطب لسه
    _CancelBase = Exception


class Cancelled(_CancelBase):
    """بيتفعّل لما المستخدم يدوس إلغاء"""


# ------------------------------------------------------------------ helpers
def _load_file_ids():
    global _file_ids
    try:
        with open(FILEID_CACHE, "r", encoding="utf-8") as f:
            _file_ids = json.load(f)
    except Exception:
        _file_ids = {}


def _save_file_ids():
    try:
        with open(FILEID_CACHE, "w", encoding="utf-8") as f:
            json.dump(_file_ids, f)
    except Exception as e:
        log.warning("file_id cache: %s", e)


_load_file_ids()


def fmt_duration(sec) -> str:
    try:
        sec = int(sec or 0)
    except Exception:
        return ""
    if sec <= 0:
        return ""
    h, r = divmod(sec, 3600)
    m, s = divmod(r, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def fmt_size(n) -> str:
    n = float(n or 0)
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def _ydl_base_opts() -> dict:
    opts = {"quiet": True, "no_warnings": True, "noplaylist": True,
            "socket_timeout": 30, "retries": 5, "fragment_retries": 5}
    if YT_COOKIES_FILE and os.path.isfile(YT_COOKIES_FILE):
        opts["cookiefile"] = YT_COOKIES_FILE
    return opts


# ------------------------------------------------------------------ video list
def _fetch_list_blocking() -> List[dict]:
    import yt_dlp
    opts = _ydl_base_opts()
    opts.update({"extract_flat": True, "skip_download": True, "playlistend": 1000})
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(SHARAWI_CHANNEL_URL, download=False)

    videos, seen = [], set()

    def walk(entries):
        for e in entries or []:
            if not e:
                continue
            if e.get("entries"):          # تاب داخل تاب
                walk(e["entries"])
                continue
            vid = e.get("id")
            title = e.get("title")
            if not vid or not title or len(vid) != 11 or vid in seen:
                continue
            if title in ("[Private video]", "[Deleted video]"):
                continue
            seen.add(vid)
            videos.append({"id": vid, "title": title, "duration": e.get("duration")})

    walk(info.get("entries") if info else [])
    return videos


async def get_videos(force: bool = False) -> List[dict]:
    async with _list_lock:
        if not force:
            try:
                if time.time() - os.path.getmtime(VIDEOS_CACHE) < LIST_TTL:
                    with open(VIDEOS_CACHE, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if data:
                            return data
            except Exception:
                pass
        try:
            loop = asyncio.get_running_loop()
            videos = await loop.run_in_executor(None, _fetch_list_blocking)
            if videos:
                with open(VIDEOS_CACHE, "w", encoding="utf-8") as f:
                    json.dump(videos, f, ensure_ascii=False)
                return videos
        except Exception as e:
            log.warning("yt list error: %s", e)
        # لو فشل: نستخدم آخر نسخة محفوظة (حتى لو قديمة)
        try:
            with open(VIDEOS_CACHE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []


async def _find(vid: str) -> Optional[dict]:
    return next((v for v in await get_videos() if v["id"] == vid), None)


# ------------------------------------------------------------------ menus
def _list_view(videos: List[dict], page: int, note: str = ""):
    total_pages = max(1, (len(videos) + SHARAWI_PER_PAGE - 1) // SHARAWI_PER_PAGE)
    page = max(0, min(page, total_pages - 1))
    chunk = videos[page * SHARAWI_PER_PAGE:(page + 1) * SHARAWI_PER_PAGE]

    rows = [[btn(short(v["title"], 55), f"shw_v_{v['id']}_{page}", emoji=CUSTOM_EMOJI_RECITER)] for v in chunk]
    nav = []
    if page > 0:
        nav.append(btn(" السابق", f"shw_p_{page-1}", ButtonStyle.SUCCESS, CUSTOM_EMOJI_NEXT))
    nav.append(btn(f"{page+1}/{total_pages}", "ignore"))
    if page < total_pages - 1:
        nav.append(btn("التالي ", f"shw_p_{page+1}", ButtonStyle.SUCCESS, CUSTOM_EMOJI_Bx))
    rows.append(nav)
    rows.append([back_btn("back_main")])

    text = (f"<blockquote>{note}<b>🎙️ خطب الشيخ الشعراوي</b>\n"
            f"اختار الخطبة اللي عايزها وهتتحمّل وتتبعتلك فيديو هنا.\n"
            f"عدد الخطب: {len(videos)}</blockquote>")
    return text, kb(rows)


async def show_sharawi_list(client, query, page: int = 0, answered: bool = False):
    if not answered:
        await query.answer("⏳ جاري تحميل القائمة..." if page == 0 else None)
    videos = await get_videos()
    if not videos:
        await safe_edit(client, query,
                        "<blockquote>❌ مقدرتش أجيب قائمة الخطب دلوقتي، جرّب بعد شوية.</blockquote>",
                        kb([[back_btn("back_main")]]))
        return
    text, markup = _list_view(videos, page)
    await safe_edit(client, query, text, markup)


async def show_video_card(client, query, vid: str, page: int):
    await query.answer()
    v = await _find(vid)
    if not v:
        await query.answer("❌ الخطبة مش موجودة", show_alert=True)
        return
    dur = fmt_duration(v.get("duration"))
    text = f"<blockquote><b>🎙️ {esc(v['title'])}</b>" + (f"\n⏱ المدة: {dur}" if dur else "") + "</blockquote>"
    rows = [[btn("⬇️ تحميل", f"shw_d_{vid}_{page}", ButtonStyle.SUCCESS),
             btn("❌ إلغاء", f"shw_p_{page}", ButtonStyle.DANGER)]]
    await safe_edit(client, query, text, kb(rows))


# ------------------------------------------------------------------ download
def _download_blocking(vid: str, state: dict, cancel: threading.Event) -> dict:
    import yt_dlp

    def hook(d):
        if cancel.is_set():
            raise Cancelled()
        if d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            state["done"] = d.get("downloaded_bytes") or 0
            state["total"] = total
            state["speed"] = d.get("speed") or 0
        elif d.get("status") == "finished":
            state["stage"] = "processing"

    opts = _ydl_base_opts()
    fmt = (f"best[height<={SHARAWI_MAX_HEIGHT}][ext=mp4]/"
           f"bv*[height<={SHARAWI_MAX_HEIGHT}][ext=mp4]+ba[ext=m4a]/"
           f"best[height<={SHARAWI_MAX_HEIGHT}]/bv*[height<={SHARAWI_MAX_HEIGHT}]+ba/worst")
    opts.update({
        "format": fmt,
        "outtmpl": os.path.join(DOWNLOAD_DIR, "%(id)s.%(ext)s"),
        "merge_output_format": "mp4",
        "max_filesize": SHARAWI_MAX_FILESIZE,
        "progress_hooks": [hook],
        "concurrent_fragment_downloads": 4,
    })
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"https://www.youtube.com/watch?v={vid}", download=True)
        path = None
        if info.get("requested_downloads"):
            path = info["requested_downloads"][0].get("filepath")
        if not path or not os.path.isfile(path):
            path = os.path.join(DOWNLOAD_DIR, f"{vid}.mp4")
    return {"path": path, "width": info.get("width"), "height": info.get("height"),
            "duration": info.get("duration")}


def _progress_text(title: str, stage: str, pct: float, extra: str = "") -> str:
    bar_len = 12
    filled = int(bar_len * pct / 100)
    bar = "▓" * filled + "░" * (bar_len - filled)
    return (f"<blockquote><b>🎙️ {esc(title)}</b>\n\n{stage}\n{bar} {pct:.0f}%"
            + (f"\n{extra}" if extra else "") + "</blockquote>")


async def start_download(client, query, vid: str, page: int):
    user_id = query.from_user.id
    key = (query.message.chat.id, query.message.id)

    if user_id in _user_busy:
        await query.answer("⏳ عندك تحميل شغال بالفعل، استنى لحد ما يخلص أو الغيه.", show_alert=True)
        return
    v = await _find(vid)
    if not v:
        await query.answer("❌ الخطبة مش موجودة", show_alert=True)
        return

    await query.answer("✅ بدأ التحميل")
    cancel = threading.Event()
    _jobs[key] = {"cancel": cancel, "user": user_id}
    _user_busy[user_id] = key
    asyncio.create_task(_run_job(client, query.message, key, v, page, cancel, user_id))


async def cancel_download(client, query, vid: str, page: int):
    """زر إلغاء التحميل: بيوقف التحميل/الرفع ويرجّعه لقايمة الخطب"""
    key = (query.message.chat.id, query.message.id)
    job = _jobs.get(key)
    if job:
        job["cancel"].set()
        await query.answer("❌ جاري الإلغاء...")
    else:  # البوت اتعمله restart مثلاً - نرجّع للقايمة بس
        await query.answer()
        await show_sharawi_list(client, query, page, answered=True)


async def _acquire_slot(cancel: threading.Event):
    """استنى دورك في الطابور، ولو المستخدم لغى وهو مستني نخرج فوراً"""
    while True:
        if cancel.is_set():
            raise Cancelled()
        try:
            await asyncio.wait_for(_sem.acquire(), timeout=2)
            return
        except asyncio.TimeoutError:
            continue


async def _run_job(client, msg, key, v, page, cancel: threading.Event, user_id: int):
    vid, title = v["id"], v["title"]
    cancel_markup = kb([[btn("❌ إلغاء التحميل", f"shw_c_{vid}_{page}", ButtonStyle.DANGER)]])
    done_markup = kb([[btn(" باقي الخطب", f"shw_p_{page}", emoji=CUSTOM_EMOJI_RECITER)],
                      [btn(" الرئيسية", "back_main", ButtonStyle.SUCCESS, CUSTOM_EMOJI_BACK)]])
    last_edit = {"t": 0.0}

    async def edit(text, markup=cancel_markup):
        try:
            if msg.photo:
                await msg.edit_caption(text, reply_markup=markup)
            else:
                await msg.edit_text(text, reply_markup=markup)
        except Exception as e:
            if "MESSAGE_NOT_MODIFIED" not in str(e):
                log.debug("edit fail: %s", e)

    async def send_cached() -> bool:
        await edit(_progress_text(title, "⚡ الفيديو جاهز، جاري الإرسال...", 100), None)
        try:
            await client.send_video(msg.chat.id, _file_ids[vid], caption=f"🎙️ {title}")
            await edit(f"<blockquote>✅ تم إرسال الخطبة\n<b>{esc(title)}</b></blockquote>", done_markup)
            return True
        except Exception as e:
            log.warning("cached file_id failed (%s) → re-download", e)
            _file_ids.pop(vid, None)
            _save_file_ids()
            return False

    async def download_and_send():
        state = {"done": 0, "total": 0, "speed": 0, "stage": "downloading"}
        loop = asyncio.get_running_loop()
        fut = loop.run_in_executor(None, _download_blocking, vid, state, cancel)
        while not fut.done():
            await asyncio.wait({fut}, timeout=4)   # بيصحى فوراً لما التحميل يخلص
            if fut.done():
                break
            if state["stage"] == "processing":
                await edit(_progress_text(title, "⚙️ جاري تجهيز الفيديو...", 100))
            else:
                total = state["total"]
                pct = (state["done"] / total * 100) if total else 0
                extra = f"{fmt_size(state['done'])} / {fmt_size(total)}" if total else fmt_size(state["done"])
                if state["speed"]:
                    extra += f" • {fmt_size(state['speed'])}/s"
                await edit(_progress_text(title, "⬇️ جاري التحميل...", pct, extra))
        result = await fut
        if cancel.is_set():
            raise Cancelled()

        path = result["path"]
        if not os.path.isfile(path):  # yt-dlp بيتخطى الملفات الأكبر من max_filesize
            raise RuntimeError("file larger than max-filesize or missing")
        if os.path.getsize(path) > SHARAWI_MAX_FILESIZE:
            await edit("<blockquote>❌ الفيديو أكبر من الحد المسموح بيه في تيليجرام.</blockquote>", done_markup)
            return

        await edit(_progress_text(title, "📤 جاري الرفع...", 0))

        async def progress(current, total):
            if cancel.is_set():
                client.stop_transmission()
                return
            now = time.time()
            if now - last_edit["t"] < 4:
                return
            last_edit["t"] = now
            await edit(_progress_text(title, "📤 جاري الرفع...", current / total * 100 if total else 0))

        sent = await client.send_video(
            msg.chat.id, path,
            caption=f"🎙️ {title}",
            duration=int(result.get("duration") or v.get("duration") or 0),
            width=int(result.get("width") or 0),
            height=int(result.get("height") or 0),
            supports_streaming=True,
            progress=progress,
        )
        try:
            _file_ids[vid] = sent.video.file_id
            _save_file_ids()
        except Exception:
            pass
        await edit(f"<blockquote>✅ تم إرسال الخطبة\n<b>{esc(title)}</b></blockquote>", done_markup)

    try:
        if vid in _file_ids and await send_cached():
            return
        await edit(_progress_text(title, "🕓 في الانتظار...", 0))
        await _acquire_slot(cancel)
        try:
            await download_and_send()
        finally:
            _sem.release()

    except asyncio.CancelledError:
        raise
    except Exception as e:
        if cancel.is_set() or isinstance(e, Cancelled):
            await _cancelled_ui(msg, page)
        else:
            log.warning("sharawi job failed: %s", e)
            reason = str(e)
            if "larger than" in reason or "max-filesize" in reason or "max_filesize" in reason:
                txt = "❌ حجم الفيديو أكبر من الحد المسموح."
            elif "Sign in" in reason or "confirm you" in reason.lower():
                txt = "❌ يوتيوب رفض التحميل من السيرفر (محتاج ملف cookies.txt)."
            else:
                txt = "❌ حصل خطأ أثناء التحميل، جرّب تاني بعد شوية."
            await edit(f"<blockquote>{txt}</blockquote>", done_markup)
    finally:
        _jobs.pop(key, None)
        _user_busy.pop(user_id, None)
        try:  # تنظيف أي ملفات متبقية للفيديو ده (حتى الـ .part)
            for f in os.listdir(DOWNLOAD_DIR):
                if f.startswith(vid):
                    os.remove(os.path.join(DOWNLOAD_DIR, f))
        except Exception:
            pass


async def _cancelled_ui(msg, page: int = 0):
    """بعد الإلغاء نرجّع قايمة الخطب"""
    videos = await get_videos()
    text, markup = _list_view(videos, page, note="❌ تم إلغاء التحميل.\n\n")
    try:
        if msg.photo:
            await msg.edit_caption(text, reply_markup=markup)
        else:
            await msg.edit_text(text, reply_markup=markup)
    except Exception:
        pass
