import aiohttp
import random
from typing import Dict, List, Optional, Tuple

QURAN_API_BASE = "https://api.alquran.cloud/v1"

# قائمة الـ 114 سورة كاملة
SURAH_LIST: List[Tuple[int, str]] = [
    (1, "الفاتحة"), (2, "البقرة"), (3, "آل عمران"), (4, "النساء"), (5, "المائدة"),
    (6, "الأنعام"), (7, "الأعراف"), (8, "الأنفال"), (9, "التوبة"), (10, "يونس"),
    (11, "هود"), (12, "يوسف"), (13, "الرعد"), (14, "إبراهيم"), (15, "الحجر"),
    (16, "النحل"), (17, "الإسراء"), (18, "الكهف"), (19, "مريم"), (20, "طه"),
    (21, "الأنبياء"), (22, "الحج"), (23, "المؤمنون"), (24, "النور"), (25, "الفرقان"),
    (26, "الشعراء"), (27, "النمل"), (28, "القصص"), (29, "العنكبوت"), (30, "الروم"),
    (31, "لقمان"), (32, "السجدة"), (33, "الأحزاب"), (34, "سبإ"), (35, "فاطر"),
    (36, "يس"), (37, "الصافات"), (38, "ص"), (39, "الزمر"), (40, "غافر"),
    (41, "فصلت"), (42, "الشورى"), (43, "الزخرف"), (44, "الدخان"), (45, "الجاثية"),
    (46, "الأحقاف"), (47, "محمد"), (48, "الفتح"), (49, "الحجرات"), (50, "ق"),
    (51, "الذاريات"), (52, "الطور"), (53, "النجم"), (54, "القمر"), (55, "الرحمن"),
    (56, "الواقعة"), (57, "الحديد"), (58, "المجادلة"), (59, "الحشر"), (60, "الممتحنة"),
    (61, "الصف"), (62, "الجمعة"), (63, "المنافقون"), (64, "التغابن"), (65, "الطلاق"),
    (66, "التحريم"), (67, "الملك"), (68, "القلم"), (69, "الحاقة"), (70, "المعارج"),
    (71, "نوح"), (72, "الجن"), (73, "المزمل"), (74, "المدثر"), (75, "القيامة"),
    (76, "الإنسان"), (77, "المرسلات"), (78, "النبإ"), (79, "النازعات"), (80, "عبس"),
    (81, "التكوير"), (82, "الانفطار"), (83, "المطففين"), (84, "الانشقاق"), (85, "البروج"),
    (86, "الطارق"), (87, "الأعلى"), (88, "الغاشية"), (89, "الفجر"), (90, "البلد"),
    (91, "الشمس"), (92, "الليل"), (93, "الضحى"), (94, "الشرح"), (95, "التين"),
    (96, "العلق"), (97, "القدر"), (98, "البينة"), (99, "الزلزلة"), (100, "العاديات"),
    (101, "القارعة"), (102, "التكاثر"), (103, "العصر"), (104, "الهمزة"), (105, "الفيل"),
    (106, "قريش"), (107, "الماعون"), (108, "الكوثر"), (109, "الكافرون"), (110, "النصر"),
    (111, "المسد"), (112, "الإخلاص"), (113, "الفلق"), (114, "الناس")
]

# كاش مؤقت للآيات (لتحسين الأداء)
_verses_cache: Dict[int, List[Dict]] = {}

async def get_surah(surah_number: int, edition: str = "quran-uthmani") -> Optional[Dict]:
    """جلب سورة كاملة مع جميع آياتها"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{QURAN_API_BASE}/surah/{surah_number}/{edition}") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data["code"] == 200 and data["data"]:
                        return data["data"]
    except Exception as e:
        print(f"Error fetching surah {surah_number}: {e}")
    return None

async def get_surah_verses(surah_number: int) -> Optional[List[Dict]]:
    """جلب آيات سورة معينة فقط"""
    if surah_number in _verses_cache:
        return _verses_cache[surah_number]
    
    surah_data = await get_surah(surah_number)
    if surah_data and "ayahs" in surah_data:
        _verses_cache[surah_number] = surah_data["ayahs"]
        return surah_data["ayahs"]
    return None

async def get_random_verse() -> Optional[str]:
    """جلب آية عشوائية من القرآن الكريم"""
    try:
        surah_num = random.randint(1, 114)
        verses = await get_surah_verses(surah_num)
        if verses:
            random_verse = random.choice(verses)
            surah_name = SURAH_LIST[surah_num - 1][1]
            return f"﴿ {random_verse['text']} ﴾ [{surah_name} : {random_verse['numberInSurah']}]"
    except Exception as e:
        print(f"Error fetching random verse: {e}")
    return None

async def get_multiple_random_verses(count: int = 5) -> List[str]:
    """جلب عدة آيات عشوائية"""
    verses = []
    for _ in range(count):
        verse = await get_random_verse()
        if verse:
            verses.append(verse)
    return verses

def get_formatted_sura_text(surah_data: Dict) -> str:
    """تنسيق نص السورة الكامل للعرض"""
    if not surah_data or "ayahs" not in surah_data:
        return "عذراً، حدث خطأ في تحميل السورة."
    
    surah_name = surah_data.get("name", "Unknown")
    verses_text = "\n".join([f"{v['numberInSurah']}. {v['text']}" for v in surah_data["ayahs"]])
    return f"📖 *سورة {surah_name}*\n\n{verses_text}"