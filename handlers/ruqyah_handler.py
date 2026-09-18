# handlers/ruqyah_handler.py
import os
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.enums import ButtonStyle, ParseMode
from database import get_ruqyah_reciters
from config import (CUSTOM_EMOJI_RUQYAH)

EMPTY_TEXT = f'<blockquote>الرقية الشرعية <emoji id="{CUSTOM_EMOJI_RUQYAH}">🎙️</emoji> </blockquote>'

async def show_ruqyah_menu(client, query: CallbackQuery):
    """عرض قائمة قراء الرقية الشرعية"""
    await query.answer()
    
    reciters = get_ruqyah_reciters()
    
    if not reciters:
        await query.message.edit_text(
            "<blockquote>❌ لا توجد رقية شرعية متاحة حالياً</blockquote>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="back_main", style=ButtonStyle.DANGER)]])
        )
        return
    
    keyboard = []
    for reciter in reciters:
        name = reciter.get('name', 'غير معروف')
        reciter_id = reciter.get('id')
        keyboard.append([InlineKeyboardButton(f"🎙️ {name}", callback_data=f"ruqyah_reciter_{reciter_id}", style=ButtonStyle.PRIMARY)])
    
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_main", style=ButtonStyle.DANGER)])
    
    text = EMPTY_TEXT  # ✅ حرف غير ظاهر بدل <blockquote></blockquote>
    
    try:
        await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        if "MESSAGE_EMPTY" in str(e):
            # لو الرسالة فاضية، نبعت رسالة جديدة
            await query.message.delete()
            await client.send_message(query.message.chat.id, text, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            print(f"Error in show_ruqyah_menu: {e}")

async def play_ruqyah_audio(client, query: CallbackQuery, reciter_id: int):
    """تشغيل وإرسال ملف الرقية الصوتية"""
    await query.answer("⏳ جاري التحميل...", show_alert=False)
    
    reciters = get_ruqyah_reciters()
    reciter = next((r for r in reciters if r['id'] == reciter_id), None)
    
    if not reciter:
        await query.message.edit_text(
            "<blockquote>❌ عذراً، هذا الشيخ غير متوفر حالياً.</blockquote>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="menu_ruqyah", style=ButtonStyle.DANGER)]])
        )
        return
    
    # البحث عن الملف
    possible_files = [
        "02-maher.mp3",
        "Rqa_iiih6.mp3",
        "maher_ruqyah.mp3",
        "ruqyah.mp3",
    ]
    
    # إضافة الملف من قاعدة البيانات
    file_from_db = reciter.get('file') or reciter.get('file_path') or ""
    if file_from_db and file_from_db not in possible_files:
        possible_files.insert(0, file_from_db)
    
    file_path = None
    for file_name in possible_files:
        if file_name and os.path.exists(file_name) and os.path.isfile(file_name) and file_name.endswith('.mp3'):
            file_size = os.path.getsize(file_name)
            if file_size > 0:
                file_path = file_name
                print(f"✅ Found ruqyah file: {file_path} (Size: {file_size} bytes)")
                break
    
    if not file_path:
        print(f"❌ File not found. Searched: {possible_files}")
        await query.message.edit_text(
            "<blockquote>⚠️ عذراً، الملف الصوتي غير موجود.\n\n📌 الملفات المطلوبة:\n• 02-maher.mp3\n• Rqa_iiih6.mp3\n\n📌 الرجاء وضع الملفات في نفس مجلد البوت</blockquote>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="menu_ruqyah", style=ButtonStyle.DANGER)]])
        )
        return
    
    await query.message.edit_text(
        f"<blockquote>🎙️ جاري إرسال {reciter.get('title', 'الرقية الشرعية')}</blockquote>",
        parse_mode=ParseMode.HTML
    )
    
    try:
        # إرسال الملف الصوتي
        await client.send_audio(
            chat_id=query.message.chat.id,
            audio=file_path,
            title=reciter.get('title', 'الرقية الشرعية'),
            performer=f"الشيخ {reciter['name']}",
            caption="ㅤ",  # ✅ حرف غير ظاهر بدل <blockquote></blockquote>
            parse_mode=ParseMode.HTML
        )
        
        # حذف رسالة "جاري الإرسال"
        try:
            await query.message.delete()
        except:
            pass
        
        # رسالة تأكيد
        await client.send_message(
            chat_id=query.message.chat.id,
            text="<blockquote>✅ تم إرسال الرقية الشرعية</blockquote>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 رجوع للرقية", callback_data="menu_ruqyah", style=ButtonStyle.DANGER)],
                [InlineKeyboardButton("🏠 الرئيسية", callback_data="back_main", style=ButtonStyle.PRIMARY)]
            ])
        )
        
    except Exception as e:
        print(f"Ruqyah error: {e}")
        await client.send_message(
            chat_id=query.message.chat.id,
            text=f"<blockquote>❌ حدث خطأ في إرسال الرقية\n\n{str(e)[:150]}</blockquote>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="menu_ruqyah", style=ButtonStyle.DANGER)]])
        )