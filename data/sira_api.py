# data/sira_api.py
# جلب السيرة النبوية من إسلام ويب  (https://www.islamweb.net/ar/articles/138/)
import os
import re
import json
import time
import asyncio
import logging
from typing import List, Dict, Optional, Tuple

import aiohttp
from bs4 import BeautifulSoup

from config import ISLAMWEB_BASE, CACHE_DIR, SIRA_PAGE_CHARS

log = logging.getLogger("sira")

SIRA_CACHE_DIR = os.path.join(CACHE_DIR, "sira")
os.makedirs(SIRA_CACHE_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept-Language": "ar,en;q=0.8",
}

# أقسام السيرة (من صفحة السيرة النبوية في إسلام ويب) - مرتبة زمنياً
SIRA_CATEGORIES: List[Tuple[int, str]] = [
    (140, "مقدمات في السيرة النبوية"),
    (139, "الجزيرة العربية قبل البعثة"),
    (141, "من المولد إلى البعثة"),
    (143, "من البعثة إلى الهجرة"),
    (144, "من الهجرة إلى بدر"),
    (193, "من بدر إلى الحديبية"),
    (194, "من الحديبية إلى تبوك"),
    (195, "من تبوك إلى الوفاة"),
    (145, "شمائل الرسول ﷺ"),
    (159, "خصوصيات الرسول ﷺ"),
    (429, "أزواج النبي ﷺ"),
    (450, "آيات ومعجزات النبوة"),
    (1028, "مواقف نبوية"),
    (2746, "فقه السيرة"),
]
# الأقسام اللي بتتحكي منها "قصة اليوم" بالترتيب
DAILY_CATEGORIES = [141, 143, 144, 193, 194, 195, 1028]

# روابط بتظهر في فوتر الموقع (مش مقالات سيرة)
_IGNORE_IDS = {"226930", "226933", "13341"}

_ARTICLE_HREF = re.compile(r"/ar/article/(\d+)")
_PAGENO = re.compile(r"pageno=(\d+)")

_session: Optional[aiohttp.ClientSession] = None
_sem = asyncio.Semaphore(3)


async def _get_session() -> aiohttp.ClientSession:
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession(headers=HEADERS, timeout=aiohttp.ClientTimeout(total=30))
    return _session


async def _fetch_html(url: str, retries: int = 3) -> Optional[str]:
    session = await _get_session()
    for attempt in range(retries):
        try:
            async with _sem:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        raw = await resp.read()
                        # إسلام ويب أحياناً بيرجّع بايتات UTF-8 مقطوعة في نص الصفحة
                        # (مثلاً مقتطفات بتتقص بالبايت). resp.text() كان بيرمي UnicodeDecodeError
                        # وبيفشل الصفحة كلها؛ هنا بنستبدل البايت التالف بس ونكمّل.
                        return raw.decode("utf-8", errors="replace")
                    log.warning("HTTP %s for %s", resp.status, url)
                    # أخطاء الـ 4xx (غير 429) الإعادة مش هتفيد
                    if 400 <= resp.status < 500 and resp.status != 429:
                        return None
        except Exception as e:
            log.warning("fetch error (%r) %s", e, url)
        if attempt < retries - 1:
            await asyncio.sleep(1.5 * (attempt + 1))
    return None


# ------------------------------------------------------------------ cache
def _read_json(path: str, max_age: Optional[float] = None):
    try:
        if max_age is not None and time.time() - os.path.getmtime(path) > max_age:
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _write_json(path: str, data):
    try:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        os.replace(tmp, path)
    except Exception as e:
        log.warning("cache write failed: %s", e)


# ------------------------------------------------------------------ listing
def _clean(text: str) -> str:
    text = (text or "").replace("\ufffd", "")  # رمز الاستبدال الناتج عن بايتات تالفة
    return re.sub(r"\s+", " ", text).strip()


def parse_listing(html: str) -> Tuple[List[Dict], int]:
    """يرجّع (قائمة المقالات [{id,title}], عدد الصفحات)"""
    soup = BeautifulSoup(html, "html.parser")

    total_pages = 1
    for a in soup.find_all("a", href=True):
        m = _PAGENO.search(a["href"])
        if m:
            total_pages = max(total_pages, int(m.group(1)))

    def collect(anchors) -> List[Dict]:
        items, seen = [], set()
        for a in anchors:
            m = _ARTICLE_HREF.search(a.get("href", ""))
            if not m:
                continue
            aid = m.group(1)
            if aid in seen or aid in _IGNORE_IDS:
                continue
            title = _clean(a.get_text(" "))
            if not title or title == "المزيد" or title.isdigit():
                continue
            seen.add(aid)
            items.append({"id": int(aid), "title": title})
        return items

    # العناوين في الموقع جوّه h2/h3
    heading_anchors = []
    for h in soup.find_all(["h2", "h3"]):
        heading_anchors.extend(h.find_all("a", href=True))
    items = collect(heading_anchors)
    if not items:  # fallback: أي لينك مقال
        items = collect(soup.find_all("a", href=True))
    return items, total_pages


async def get_category_page(cat_id: int, page: int = 1) -> Tuple[List[Dict], int]:
    path = os.path.join(SIRA_CACHE_DIR, f"list_{cat_id}_{page}.json")
    cached = _read_json(path, max_age=12 * 3600)
    if cached:
        return cached["items"], cached["pages"]

    url = f"{ISLAMWEB_BASE}/ar/articles/{cat_id}/"
    if page > 1:
        url += f"?pageno={page}"
    html = await _fetch_html(url)
    if not html:
        stale = _read_json(path)
        return (stale["items"], stale["pages"]) if stale else ([], 1)

    items, pages = parse_listing(html)
    if items:
        _write_json(path, {"items": items, "pages": pages})
    return items, pages


# ------------------------------------------------------------------ article
_BAD_TAGS = ["script", "style", "nav", "footer", "header", "form", "noscript", "aside", "button", "select"]
_CUT_MARKERS = ("مواد ذات الصله", "مواد ذات الصلة")


def _score(el) -> int:
    """أكتر عنصر فيه نص مباشر (نص + فقرات <p>) هو غالباً جسم المقال"""
    total = 0
    for child in el.children:
        if isinstance(child, str):
            total += len(child.strip())
        elif child.name == "p":
            total += len(child.get_text(" ", strip=True))
    return total


def parse_article(html: str) -> Dict:
    soup = BeautifulSoup(html, "html.parser")

    title = ""
    og = soup.find("meta", property="og:title")
    if og and og.get("content"):
        title = _clean(og["content"])
    if not title:
        h = soup.find("h1") or soup.find("h2")
        title = _clean(h.get_text(" ")) if h else ""

    for t in soup.find_all(_BAD_TAGS):
        t.decompose()

    best, best_score = None, 0
    for el in soup.find_all(["div", "article", "section", "td"]):
        sc = _score(el)
        if sc > best_score:
            best, best_score = el, sc

    text = ""
    if best is not None:
        for br in best.find_all("br"):
            br.replace_with("\n")
        parts = []
        for child in best.children:
            if isinstance(child, str):
                parts.append(child)
            elif child.name in ("p", "div", "blockquote"):
                parts.append("\n" + child.get_text() + "\n")
            elif child.name == "br":
                parts.append("\n")
            else:
                parts.append(child.get_text())
        text = "".join(parts)

    text = _normalize_text(text)
    for marker in _CUT_MARKERS:
        if marker in text:
            text = text.split(marker)[0].strip()

    # fallback: وصف الصفحة
    if len(text) < 200:
        meta = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", property="og:description")
        if meta and meta.get("content") and len(meta["content"]) > len(text):
            text = _normalize_text(meta["content"])

    return {"title": title, "text": text}


def _normalize_text(text: str) -> str:
    text = text.replace("\ufffd", "")  # رمز الاستبدال الناتج عن بايتات تالفة
    text = text.replace("\r", "")
    text = re.sub(r"[ \t\u00a0]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


async def get_article(article_id: int) -> Optional[Dict]:
    path = os.path.join(SIRA_CACHE_DIR, f"article_{article_id}.json")
    cached = _read_json(path)
    if cached and cached.get("text"):
        if not cached.get("pages"):  # كاش قديم من غير صفحات
            cached["pages"] = split_pages(cached["text"])
        return cached

    html = await _fetch_html(f"{ISLAMWEB_BASE}/ar/article/{article_id}/")
    if not html:
        return None
    art = parse_article(html)
    if not art["text"]:
        return None
    art["id"] = article_id
    art["pages"] = split_pages(art["text"])
    _write_json(path, art)
    return art


def split_pages(text: str, limit: int = SIRA_PAGE_CHARS) -> List[str]:
    """تقسيم النص لصفحات على حدود الفقرات/الجُمل عشان تنفع رسائل تيليجرام"""
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    pages, cur = [], ""

    def flush():
        nonlocal cur
        if cur.strip():
            pages.append(cur.strip())
        cur = ""

    for p in paragraphs:
        # فقرة أطول من الحد → نقسمها على الجُمل
        while len(p) > limit:
            cut = max(p.rfind(sep, 0, limit) for sep in ("۔", ".", "،", "؟", "!", " "))
            if cut < limit // 2:
                cut = limit - 1  # كان limit فبيطلع جزء أطول من الحد بحرف
            chunk, p = p[:cut + 1], p[cut + 1:].strip()
            if len(cur) + len(chunk) + 2 > limit:
                flush()
            cur += chunk + "\n\n"
        if len(cur) + len(p) + 2 > limit:
            flush()
        cur += p + "\n\n"
    flush()
    return pages or [text[:limit]]


# ------------------------------------------------------------------ daily story
INDEX_PATH = os.path.join(SIRA_CACHE_DIR, "daily_index.json")


async def build_daily_index(force: bool = False) -> List[Dict]:
    """قائمة مقالات (بالترتيب الزمني للأقسام) بتتبني مرة وتتحدث كل أسبوع"""
    if not force:
        cached = _read_json(INDEX_PATH, max_age=7 * 24 * 3600)
        if cached:
            return cached

    result, seen = [], set()
    complete = True  # لو أي صفحة فشلت مش هنحفظ الفهرس الناقص لأسبوع كامل
    for cat in DAILY_CATEGORIES:
        items, pages = await get_category_page(cat, 1)
        if not items:
            complete = False
        # الموقع بيرتب الأحدث أولاً؛ بنجمع أول 5 صفحات من كل قسم كحد أقصى
        for p in range(2, min(pages, 5) + 1):
            more, _ = await get_category_page(cat, p)
            if not more:
                complete = False
            items += more
            await asyncio.sleep(0.5)
        for it in items:
            if it["id"] not in seen:
                seen.add(it["id"])
                result.append(it)

    if result and complete:
        _write_json(INDEX_PATH, result)
        return result

    # فهرس ناقص: نفضّل آخر فهرس كامل محفوظ لو موجود، وإلا نستخدم الناقص من غير ما نحفظه
    stale = _read_json(INDEX_PATH)
    if stale and len(stale) >= len(result):
        return stale
    return result
