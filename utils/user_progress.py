import json
import os
from config import USER_PROGRESS_FILE

def load_progress():
    if os.path.exists(USER_PROGRESS_FILE):
        try:
            with open(USER_PROGRESS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_progress(data):
    try:
        with open(USER_PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except:
        pass

def get_last_sura(user_id):
    data = load_progress()
    user_data = data.get(str(user_id), {})
    return {
        "sura": user_data.get("sura", 1),
        "page": user_data.get("page", 0),
        "verse": user_data.get("verse", 0)
    }

def set_last_sura(user_id, sura_id, page=0, verse=0):
    data = load_progress()
    data[str(user_id)] = {
        "sura": sura_id,
        "page": page,
        "verse": verse,
        "timestamp": str(__import__('datetime').datetime.now())
    }
    save_progress(data)

def clear_user_progress(user_id):
    data = load_progress()
    if str(user_id) in data:
        del data[str(user_id)]
        save_progress(data)