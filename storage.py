import json
import shutil
from pathlib import Path
from datetime import date, datetime

USERS_DIR = Path(__file__).parent / "users"
MAX_USERS = 10

# Ebbinghaus review intervals (days)
REVIEW_INTERVALS = [1, 3, 7, 15, 30]

def init():
    global USERS_DIR
    try:
        from kivy.app import App
        app = App.get_running_app()
        if app:
            USERS_DIR = Path(app.user_data_dir) / "users"
    except Exception:
        pass
    USERS_DIR.mkdir(parents=True, exist_ok=True)

def get_user_list():
    files = list(USERS_DIR.glob("*.json"))
    users = []
    for f in files:
        try:
            data = json.loads(f.read_text(encoding='utf-8'))
            users.append({
                'name': data.get('name', f.stem),
                'filename': f.name,
                'total_score': data.get('total_score', 0),
            })
        except:
            pass
    users.sort(key=lambda u: u['name'])
    return users

def create_user(name):
    users = get_user_list()
    if len(users) >= MAX_USERS:
        return None
    safe = name.strip()
    if not safe:
        return None
    filename = f"{safe}.json"
    path = USERS_DIR / filename
    if path.exists():
        return None
    data = {
        'name': safe,
        'created': str(date.today()),
        'total_score': 0,
        'book_progress': {
            1: {'unlocked_lessons': 1},
            2: {'unlocked_lessons': 1},
        },
        'lesson_stars': {
        },
        'word_weights': {
        },
        'wrong_words': {
        },
        'review_queue': {
        },
        'last_play_date': str(date.today()),
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    return safe

def load_user(name):
    path = USERS_DIR / f"{name}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding='utf-8'))

def save_user(name, data):
    path = USERS_DIR / f"{name}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

def get_word_weight(data, book_id, lesson, word_text):
    key = f"{book_id}_{lesson}_{word_text}"
    ww = data.get('word_weights', {})
    entry = ww.get(key, {})
    return entry.get('weight', 1.0), entry.get('last_review_date'), entry.get('next_review_dates', [])

def set_word_weight(data, book_id, lesson, word_text, weight, next_review_dates=None):
    key = f"{book_id}_{lesson}_{word_text}"
    if 'word_weights' not in data:
        data['word_weights'] = {}
    entry = data['word_weights'].get(key, {})
    entry['weight'] = weight
    entry['last_review_date'] = str(date.today())
    if next_review_dates is not None:
        entry['next_review_dates'] = next_review_dates
    data['word_weights'][key] = entry

def add_wrong_word(data, book_id, lesson, word_text, phonetic, chinese):
    key = f"{book_id}_{lesson}_{word_text}"
    if 'wrong_words' not in data:
        data['wrong_words'] = {}
    if key not in data['wrong_words']:
        data['wrong_words'][key] = {
            'book_id': book_id,
            'lesson': lesson,
            'word': word_text,
            'phonetic': phonetic,
            'chinese': chinese,
            'consecutive_correct': 0,
            'wrong_count': 0,
        }

def record_wrong_attempt(data, book_id, lesson, word_text):
    key = f"{book_id}_{lesson}_{word_text}"
    ww = data.get('wrong_words', {})
    if key in ww:
        ww[key]['consecutive_correct'] = 0
        ww[key]['wrong_count'] = ww[key].get('wrong_count', 0) + 1

def record_correct_attempt(data, book_id, lesson, word_text):
    key = f"{book_id}_{lesson}_{word_text}"
    ww = data.get('wrong_words', {})
    if key in ww:
        ww[key]['consecutive_correct'] = ww[key].get('consecutive_correct', 0) + 1
        if ww[key]['consecutive_correct'] >= 2:
            del ww[key]
            return True
    return False

def is_in_wrong_words(data, book_id, lesson, word_text):
    key = f"{book_id}_{lesson}_{word_text}"
    return key in data.get('wrong_words', {})

def get_wrong_words_list(data):
    result = []
    for key, info in data.get('wrong_words', {}).items():
        result.append(info)
    return result

def add_to_review_queue(data, book_id, lesson, word_text, phonetic, chinese):
    key = f"{book_id}_{lesson}_{word_text}"
    if 'review_queue' not in data:
        data['review_queue'] = {}
    if key not in data['review_queue']:
        data['review_queue'][key] = {
            'book_id': book_id,
            'lesson': lesson,
            'word': word_text,
            'phonetic': phonetic,
            'chinese': chinese,
            'added': str(date.today()),
        }

def get_today_review(data):
    today = str(date.today())
    queue = {}
    for key, info in data.get('review_queue', {}).items():
        queue[key] = info
    for key, info in data.get('word_weights', {}).items():
        for nd in info.get('next_review_dates', []):
            if nd == today:
                parts = key.split('_', 2)
                if len(parts) == 3:
                    bid, les, wd = int(parts[0]), int(parts[1]), parts[2]
                    if key not in queue:
                        queue[key] = {
                            'book_id': bid,
                            'lesson': les,
                            'word': wd,
                            'phonetic': '',
                            'chinese': '',
                            'added': today,
                        }
    return list(queue.values())

def delete_user(name):
    path = USERS_DIR / f"{name}.json"
    if path.exists():
        path.unlink()
        return True
    return False

def update_last_play_date(data):
    data['last_play_date'] = str(date.today())

def check_accumulated_reviews(data, book_id, lesson, word_text):
    today = str(date.today())
    key = f"{book_id}_{lesson}_{word_text}"
    ww = data.get('word_weights', {}).get(key, {})
    due = []
    for nd in ww.get('next_review_dates', []):
        if nd <= today:
            due.append(nd)
    return due
