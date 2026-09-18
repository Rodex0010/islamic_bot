# utils/quran_formatter.py
import re

# العلامات
AYAH_MARKER = "۝"
HIZB_MARKER = "۞"
STOP_MARKS = {
    "mandatory": "مـ",
    "preferred": "قلى",
    "allowed": "صلى"
}

def format_ayah_with_marks(ayah_text: str, ayah_number: int, is_hizb_start: bool = False) -> str:
    """تنسيق الآية بعلامات الوقف والحزب - الرقم يظهر بعد ۝ مباشرة"""
    result = ayah_text
    
    # إضافة علامة الآية مع الرقم - بدون مسافة
    result = f"{result} {AYAH_MARKER}{ayah_number}"
    
    # إضافة علامة الحزب لو موجودة
    if is_hizb_start:
        result = f"{HIZB_MARKER} {result}"
    
    # إضافة علامات الوقف
    if "لا" in result or "إن" in result[:50]:
        result = result + f" {STOP_MARKS['mandatory']}"
    elif "و" in result[:30] or "ف" in result[:30]:
        result = result + f" {STOP_MARKS['preferred']}"
    
    return result

def get_sura_pages(verses: list, verses_per_page: int = 10) -> list:
    """تقسيم السورة إلى صفحات مع إضافة العلامات"""
    pages = []
    total_verses = len(verses)
    
    for page_num in range(0, total_verses, verses_per_page):
        page_verses = verses[page_num:page_num + verses_per_page]
        formatted_page = []
        
        for idx, verse in enumerate(page_verses):
            verse_num = verse.get("numberInSurah", idx + 1)
            verse_text = verse.get("text", "")
            
            # كل 10 آيات تعتبر بداية حزب
            is_hizb = (verse_num % 10 == 0)
            
            formatted_verse = format_ayah_with_marks(verse_text, verse_num, is_hizb)
            formatted_page.append(formatted_verse)
        
        pages.append(formatted_page)
    
    return pages