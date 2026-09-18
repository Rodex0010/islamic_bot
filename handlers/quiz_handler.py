# handlers/quiz_handler.py
import random
import json
import os
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.enums import ButtonStyle, ParseMode

# المسار لملف الأسئلة
QUESTIONS_FILE = "data/questions.json"

# تخزين مؤقت للسؤال الحالي لكل مستخدم
user_current_question = {}
user_answered = {}

def load_questions():
    """تحميل الأسئلة من ملف JSON"""
    if os.path.exists(QUESTIONS_FILE):
        try:
            with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
                questions = json.load(f)
                if questions:
                    return questions
        except Exception as e:
            print(f"خطأ في تحميل الأسئلة: {e}")
    
    return [
        {
            "question": "ما هي أول سورة نزلت في القرآن الكريم؟",
            "options": ["الفاتحة", "العلق", "المدثر", "يس"],
            "correct": 1
        },
        {
            "question": "كم عدد أركان الإسلام؟",
            "options": ["3", "4", "5", "6"],
            "correct": 2
        },
        {
            "question": "ما هي السورة التي تسمى قلب القرآن؟",
            "options": ["الفاتحة", "الإخلاص", "يس", "الملك"],
            "correct": 2
        },
        {
            "question": "كم عدد سور القرآن الكريم؟",
            "options": ["113", "114", "115", "116"],
            "correct": 1
        },
        {
            "question": "من هو أول الخلفاء الراشدين؟",
            "options": ["عمر بن الخطاب", "عثمان بن عفان", "أبو بكر الصديق", "علي بن أبي طالب"],
            "correct": 2
        },
        {
            "question": "ما هي السورة التي تسمى فاتحة الكتاب؟",
            "options": ["الإخلاص", "الفاتحة", "البقرة", "يس"],
            "correct": 1
        }
    ]

def get_random_question():
    questions = load_questions()
    return random.choice(questions)

def get_quiz_buttons(question_data):
    """أزرار السؤال - بدون علامات"""
    options = question_data["options"]
    correct_index = question_data["correct"]
    keyboard = []
    for i, option in enumerate(options):
        keyboard.append([InlineKeyboardButton(
            f"{option}", 
            callback_data=f"quiz_ans_{i}_{correct_index}",
            style=ButtonStyle.PRIMARY
        )])
    return InlineKeyboardMarkup(keyboard)

def get_result_buttons(question_data, selected_index, is_correct):
    """أزرار النتيجة - فقط تغيير الألوان بدون أي علامات أو حروف"""
    options = question_data["options"]
    correct_index = question_data["correct"]
    
    keyboard = []
    for i, option in enumerate(options):
        if i == correct_index:
            # الإجابة الصحيحة باللون الأخضر - بدون علامة ✅
            keyboard.append([InlineKeyboardButton(
                f"{option}", 
                callback_data="done", 
                style=ButtonStyle.SUCCESS
            )])
        elif i == selected_index and not is_correct:
            # الإجابة الخاطئة باللون الأحمر - بدون علامة ❌
            keyboard.append([InlineKeyboardButton(
                f"{option}", 
                callback_data="done", 
                style=ButtonStyle.DANGER
            )])
        else:
            # باقي الخيارات باللون الأزرق
            keyboard.append([InlineKeyboardButton(
                f"{option}", 
                callback_data="done", 
                style=ButtonStyle.PRIMARY
            )])
    
    return InlineKeyboardMarkup(keyboard)

async def send_random_quiz(client, message):
    """إرسال سؤال عشوائي"""
    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else chat_id
    
    question_data = get_random_question()
    
    # تخزين السؤال
    user_current_question[user_id] = question_data
    user_answered[user_id] = False
    
    text = f"<blockquote>📖❓ {question_data['question']}</blockquote>"
    
    await client.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_quiz_buttons(question_data)
    )

async def check_quiz_answer(client, query: CallbackQuery):
    """التحقق من إجابة المستخدم - تغيير الألوان فقط"""
    data = query.data
    user_id = query.from_user.id
    
    if data == "ignore" or data == "done":
        await query.answer()
        return
    
    # منع الإجابة أكثر من مرة
    if user_answered.get(user_id, False):
        await query.answer()
        return
    
    if data.startswith("quiz_ans_"):
        parts = data.split("_")
        selected_index = int(parts[2])
        correct_index = int(parts[3])
        
        # جلب السؤال المخزن
        question_data = user_current_question.get(user_id)
        
        if not question_data:
            question_data = get_random_question()
            user_current_question[user_id] = question_data
            correct_index = question_data["correct"]
        
        is_correct = (selected_index == correct_index)
        
        # تأشير أن المستخدم أجاب
        user_answered[user_id] = True
        
        # نفس السؤال
        text = f"<blockquote>📖❓ {question_data['question']}</blockquote>"
        
        try:
            await query.message.edit_text(
                text=text,
                parse_mode=ParseMode.HTML,
                reply_markup=get_result_buttons(question_data, selected_index, is_correct)
            )
        except Exception as e:
            print(f"Edit error: {e}")
        
        # من غير أي تنبيه
        await query.answer()

def is_quiz_trigger(text: str) -> bool:
    """التحقق من أن النص هو 'كت' أو '.' فقط"""
    text_stripped = text.strip()
    if text_stripped == "كت" or text_stripped == "ك ت" or text_stripped == ".":
        return True
    return False