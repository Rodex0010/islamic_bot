# config.py
import os
from dotenv import load_dotenv

load_dotenv()

# Bot tokens
TOKEN = os.getenv("BOT_TOKEN", "8698339782:AAFXdptMANtoKdQnSsqkqoFxEZ052yVvnMM")
API_ID = int(os.getenv("API_ID", "20426895"))
API_HASH = os.getenv("API_HASH", "541a6e1c10c23083356cad0611912b29")

# Developers
DEVELOPER_USERNAME = "xcode000"
DEVELOPER_USERNAME2 = "j_e_g"
DEVELOPER_IDS = []

# Custom Emoji IDs
CUSTOM_EMOJI_QURAN = int(os.getenv("CUSTOM_EMOJI_QURAN", "5936287102546221713"))
CUSTOM_EMOJI_ATHKAR = int(os.getenv("CUSTOM_EMOJI_ATHKAR", "5767390464273552025"))
CUSTOM_EMOJI_TASBEEH = int(os.getenv("CUSTOM_EMOJI_TASBEEH", "5409092030309623305"))
CUSTOM_EMOJI_DUA = int(os.getenv("CUSTOM_EMOJI_DUA", "5411180629955992821"))
CUSTOM_EMOJI_RUQYAH = int(os.getenv("CUSTOM_EMOJI_RUQYAH", "5890787069415922563"))
CUSTOM_EMOJI_RECITER = int(os.getenv("CUSTOM_EMOJI_RECITER", "6048434745958732422"))
CUSTOM_EMOJI_DEVELOPER = int(os.getenv("CUSTOM_EMOJI_DEVELOPER", "5980821811711972473"))
CUSTOM_EMOJI_BACK = int(os.getenv("CUSTOM_EMOJI_BACK", "5301111093584738499"))
CUSTOM_EMOJI_PRAYER = int(os.getenv("CUSTOM_EMOJI_PRAYER", "5312531058317448061"))
CUSTOM_EMOJI_HELP = int(os.getenv("CUSTOM_EMOJI_PRAYER", "4956368164817470478"))
CUSTOM_EMOJI_M = int(os.getenv("CUSTOM_EMOJI_PRAYER", "5789734400270800684"))
CUSTOM_EMOJI_S = int(os.getenv("CUSTOM_EMOJI_PRAYER", "5873157491386226821"))
CUSTOM_EMOJI_X = int(os.getenv("CUSTOM_EMOJI_PRAYER", "6003336962285505904"))
CUSTOM_EMOJI_NEXT = int(os.getenv("CUSTOM_EMOJI_PRAYER", "6051029979947340571"))
CUSTOM_EMOJI_Bx = int(os.getenv("CUSTOM_EMOJI_PRAYER", "6050603223406874700"))
CUSTOM_EMOJI_T = int(os.getenv("CUSTOM_EMOJI_PRAYER", "5965516493889212881"))
CUSTOM_EMOJI_u = int(os.getenv("CUSTOM_EMOJI_PRAYER", "5875373479762597696"))
CUSTOM_EMOJI_o = int(os.getenv("CUSTOM_EMOJI_PRAYER", "5872890623593290366"))
CUSTOM_EMOJI_qq = int(os.getenv("CUSTOM_EMOJI_PRAYER", "5872748674924159388"))

# Bot image
BOT_IMAGE_URL = "tito3.jpg"

# Reminder intervals
REMINDER_INTERVAL_MINUTES = 1
QURAN_INTERVAL_MINUTES = 20

# Tasbeeh words
TASBEEH_WORDS = ["سُبْحَانَ اللَّهِ", "الْحَمْدُ لِلَّهِ", "اللَّهُ أَكْبَرُ", "لا إِلَهَ إِلَّا اللَّهُ", "اللَّهُ رَبِّي لا أُشْرِكُ بِهِ شَيْئًا"]
TASBEEH_CHANGE_AFTER = 33

# Files
USER_DATA_FILE = "user_data.json"
USER_PROGRESS_FILE = "user_progress.json"
ACTIVE_CHATS_FILE = "active_chats.json"

# Prayer
DEFAULT_CITY = "Cairo"
DEFAULT_COUNTRY = "Egypt"
PRAYER_REMINDER_MINUTES = 5

# Quran
VERSES_PER_PAGE = 10

# الأدمن (الزر الخاص بالإذاعة بيظهر للأيديهات دي بس)
ADMIN_IDS = [7876741744]
 
# إذاعة القرآن الكريم (بث مباشر)
RADIO_URL = "https://stream.radiojar.com/8s5u5tpdtwzuv"
RADIO_NAME = "إذاعة القرآن الكريم - القاهرة"
RADIO_CLIP_SECONDS = 60          # مدة المقطع المباشر اللي بيتسجل ويتبعت
 
# السيرة النبوية (إسلام ويب)
ISLAMWEB_BASE = "https://www.islamweb.net"
SIRA_DAILY_HOUR = 9              # ساعة إرسال قصة اليوم (بتوقيت القاهرة)
SIRA_DAILY_MINUTE = 0
SIRA_TIMEZONE = "Africa/Cairo"
SIRA_PAGE_CHARS = 3000           # عدد الحروف في الصفحة الواحدة
 
# خطب الشيخ الشعراوي (يوتيوب)
SHARAWI_CHANNEL_URL = "https://www.youtube.com/@alsharawiofficial/videos"
SHARAWI_PER_PAGE = 8
SHARAWI_MAX_PARALLEL = 2         # أقصى عدد تحميلات في نفس الوقت
SHARAWI_MAX_HEIGHT = 480         # جودة الفيديو (480 = حجم معقول)
SHARAWI_MAX_FILESIZE = 1_900_000_000   # ~1.9GB حد تيليجرام
YT_COOKIES_FILE = os.getenv("YT_COOKIES_FILE", "cookies.txt")  # اختياري لو يوتيوب رفض التحميل من السيرفر
DOWNLOAD_DIR = "downloads"
CACHE_DIR = "cache"
