#!/usr/bin/env python3
# بوت استضافة متكامل - قاعدة بيانات داخل المستودع
# المالك: @h7_4c
# قناة البوت: @ArabPyDecode

import os
import sys
import json
import time
import base64
import subprocess
import threading
from datetime import datetime, timedelta
from flask import Flask, request
import requests

# ================== التوكنات والإعدادات ==================
TOKEN = "8560610744:AAG3NdWF1XFacM9CFwrn7pzppO3LXDz_HxA"
ADMIN_ID = 8630079643
OWNER_USERNAME = "@h7_4c"
CHANNEL_LINK = "https://t.me/ArabPyDecode"
CHANNEL_USERNAME = "ArabPyDecode"
FORCE_CHANNEL = CHANNEL_USERNAME

# إعدادات GitHub
GITHUB_TOKEN = "ghp_QHPQERbf2MeBu3Hqwi0QNa5k3D4A5i2xKWLO"
REPO_OWNER = "NEKADE16"
REPO_NAME = "my-hosting-bot"
BRANCH = "main"
DB_FOLDER = "db/"

# ================== إعداد المجلدات المحلية ==================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BOTS_DIR = os.path.join(BASE_DIR, "bots")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
DB_DIR = os.path.join(BASE_DIR, "db")

for d in [BOTS_DIR, LOGS_DIR, DB_DIR]:
    os.makedirs(d, exist_ok=True)

# ================== مسارات الملفات ==================
USERS_FILE = os.path.join(DB_DIR, "users.json")
BOTS_FILE = os.path.join(DB_DIR, "bots.json")
VIP_FILE = os.path.join(DB_DIR, "vip.json")
SETTINGS_FILE = os.path.join(DB_DIR, "settings.json")
PENDING_FILE = os.path.join(DB_DIR, "pending_admin.json")

# ================== دوال قاعدة البيانات المحلية ==================
def load_json(path):
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# ================== دوال GitHub ==================
def github_path(filename):
    return f"{DB_FOLDER}{filename}"

def upload_to_github(filepath, content):
    if not GITHUB_TOKEN:
        return False
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{filepath}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')
    
    response = requests.get(url, headers=headers)
    sha = response.json().get('sha') if response.status_code == 200 else None
    
    data = {"message": f"Update {filepath}", "content": encoded, "branch": BRANCH}
    if sha:
        data["sha"] = sha
    
    r = requests.put(url, headers=headers, json=data)
    return r.status_code in [200, 201]

def download_from_github(filepath):
    if not GITHUB_TOKEN:
        return None
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{filepath}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        content = base64.b64decode(response.json()['content']).decode('utf-8')
        return content
    return None

def sync_all_to_github():
    files = {
        'users.json': USERS_FILE,
        'bots.json': BOTS_FILE,
        'vip.json': VIP_FILE,
        'settings.json': SETTINGS_FILE
    }
    for github_name, local_path in files.items():
        if os.path.exists(local_path):
            with open(local_path, 'r', encoding='utf-8') as f:
                upload_to_github(github_path(github_name), f.read())
    print("✅ تم رفع البيانات إلى GitHub")

def sync_all_from_github():
    os.makedirs(DB_FOLDER, exist_ok=True)
    files = {
        'users.json': USERS_FILE,
        'bots.json': BOTS_FILE,
        'vip.json': VIP_FILE,
        'settings.json': SETTINGS_FILE
    }
    for github_name, local_path in files.items():
        content = download_from_github(github_path(github_name))
        if content:
            with open(local_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ تم تحميل {github_name}")
        else:
            if not os.path.exists(local_path):
                save_json(local_path, {})
                upload_to_github(github_path(github_name), json.dumps({}, ensure_ascii=False, indent=4))
                print(f"✅ تم إنشاء {github_name}")

def periodic_sync():
    while True:
        time.sleep(300)
        try:
            sync_all_to_github()
        except:
            pass

threading.Thread(target=periodic_sync, daemon=True).start()

# ================== تهيئة الإعدادات ==================
def init_db():
    if not os.path.exists(SETTINGS_FILE):
        save_json(SETTINGS_FILE, {
            'max_free_bots': 3,
            'daily_points': 10,
            'vip_stars_price': 100,
            'vip_duration_days': 30,
            'bot_price_per_hour': 1,
            'hosting_price_per_bot': 5,
            'weekly_bonus_points': 20,
            'bot_name': 'بوت الاستضافة',
            'force_channel': CHANNEL_USERNAME,
            'channel_link': CHANNEL_LINK,
            'owner': OWNER_USERNAME
        })
    if not os.path.exists(USERS_FILE):
        save_json(USERS_FILE, {})
    if not os.path.exists(BOTS_FILE):
        save_json(BOTS_FILE, {})
    if not os.path.exists(VIP_FILE):
        save_json(VIP_FILE, {})
    if not os.path.exists(PENDING_FILE):
        save_json(PENDING_FILE, {})

sync_all_from_github()
init_db()
sync_all_to_github()

# ================== دوال مساعدة ==================
def is_admin(user_id):
    return user_id == ADMIN_ID

def is_vip(user_id):
    vip_data = load_json(VIP_FILE)
    user_vip = vip_data.get(str(user_id))
    if not user_vip:
        return False
    expiry = user_vip.get('expiry')
    if expiry == 'lifetime':
        return True
    try:
        return datetime.now() < datetime.fromisoformat(expiry)
    except:
        return False

def add_vip(user_id, days=30):
    vip_data = load_json(VIP_FILE)
    expiry = (datetime.now() + timedelta(days=days)).isoformat()
    vip_data[str(user_id)] = {'expiry': expiry, 'granted_at': datetime.now().isoformat()}
    save_json(VIP_FILE, vip_data)
    sync_all_to_github()
    return True

def remove_vip(user_id):
    vip_data = load_json(VIP_FILE)
    if str(user_id) in vip_data:
        del vip_data[str(user_id)]
        save_json(VIP_FILE, vip_data)
        sync_all_to_github()
        return True
    return False

def get_user_points(user_id):
    users = load_json(USERS_FILE)
    return users.get(str(user_id), {}).get('points', 0)

def add_points(user_id, points):
    users = load_json(USERS_FILE)
    if str(user_id) not in users:
        users[str(user_id)] = {}
    users[str(user_id)]['points'] = users[str(user_id)].get('points', 0) + points
    save_json(USERS_FILE, users)
    sync_all_to_github()

def remove_points(user_id, points):
    users = load_json(USERS_FILE)
    current = users.get(str(user_id), {}).get('points', 0)
    if current < points:
        return False
    users[str(user_id)]['points'] = current - points
    save_json(USERS_FILE, users)
    sync_all_to_github()
    return True

def get_user_telegram_stars(user_id):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/getUserStars"
        response = requests.get(url, params={'user_id': user_id}).json()
        if response.get('ok'):
            return response.get('result', {}).get('stars', 0)
    except:
        pass
    return 0

def buy_vip_with_stars(user_id):
    settings = load_json(SETTINGS_FILE)
    price = settings.get('vip_stars_price', 100)
    user_stars = get_user_telegram_stars(user_id)
    if user_stars >= price:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/withdrawStars"
            requests.get(url, params={'user_id': user_id, 'amount': price})
            add_vip(user_id, settings.get('vip_duration_days', 30))
            return True, f"✅ تم شراء VIP بـ {price} نجمة"
        except:
            return False, "❌ فشل الشراء"
    return False, f"❌ رصيدك {user_stars} نجمة، تحتاج {price}"

def get_user_bots_count(user_id):
    bots = load_json(BOTS_FILE)
    return sum(1 for b in bots.values() if b.get('user_id') == user_id)

def get_running_bots_count(user_id):
    bots = load_json(BOTS_FILE)
    return sum(1 for b in bots.values() if b.get('user_id') == user_id and b.get('status') == 'running')

def get_user_bots_list(user_id):
    bots = load_json(BOTS_FILE)
    return {bid: b for bid, b in bots.items() if b.get('user_id') == user_id}

def get_all_running_bots():
    bots = load_json(BOTS_FILE)
    return {bid: b for bid, b in bots.items() if b.get('status') == 'running'}

def get_bot_runtime(bot_id):
    bots = load_json(BOTS_FILE)
    bot = bots.get(bot_id, {})
    if bot.get('status') != 'running':
        return "متوقف"
    started_at = bot.get('started_at')
    if not started_at:
        return "غير معروف"
    try:
        start = datetime.fromisoformat(started_at)
        duration = datetime.now() - start
        hours = duration.total_seconds() // 3600
        minutes = (duration.total_seconds() % 3600) // 60
        return f"{int(hours)} ساعة {int(minutes)} دقيقة"
    except:
        return "غير معروف"

def register_user(user_id, username, first_name):
    users = load_json(USERS_FILE)
    if str(user_id) not in users:
        users[str(user_id)] = {
            'username': username,
            'first_name': first_name,
            'join_date': datetime.now().isoformat(),
            'points': 10,
            'last_daily': None,
            'last_weekly': None,
            'bots': []
        }
        save_json(USERS_FILE, users)
        sync_all_to_github()
        return True
    return False

def can_upload(user_id):
    if is_admin(user_id) or is_vip(user_id):
        return True, None
    settings = load_json(SETTINGS_FILE)
    max_bots = settings.get('max_free_bots', 3)
    if get_user_bots_count(user_id) >= max_bots:
        return False, f"❌ حدك {max_bots} بوتات، اشترك VIP لرفع غير محدود"
    return True, None

def daily_reward(user_id):
    users = load_json(USERS_FILE)
    user = users.get(str(user_id), {})
    today = datetime.now().date().isoformat()
    if user.get('last_daily') == today:
        return False, "❌ حصلت عليها اليوم"
    settings = load_json(SETTINGS_FILE)
    points = settings.get('daily_points', 10)
    users[str(user_id)]['last_daily'] = today
    users[str(user_id)]['points'] = users[str(user_id)].get('points', 0) + points
    save_json(USERS_FILE, users)
    sync_all_to_github()
    return True, f"✅ {points} نقطة"

def weekly_reward(user_id):
    users = load_json(USERS_FILE)
    user = users.get(str(user_id), {})
    today = datetime.now().date().isoformat()
    current_week = datetime.now().isocalendar()[1]
    last_week = None
    if user.get('last_weekly'):
        try:
            last_week = datetime.fromisoformat(user['last_weekly']).isocalendar()[1]
        except:
            pass
    if last_week == current_week:
        return False, "❌ حصلت عليها هذا الأسبوع"
    settings = load_json(SETTINGS_FILE)
    points = settings.get('weekly_bonus_points', 20)
    users[str(user_id)]['last_weekly'] = today
    users[str(user_id)]['points'] = users[str(user_id)].get('points', 0) + points
    save_json(USERS_FILE, users)
    sync_all_to_github()
    return True, f"✅ {points} نقطة أسبوعية"

def check_force_subscribe(user_id):
    if not FORCE_CHANNEL:
        return True
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/getChatMember"
        response = requests.get(url, params={'chat_id': f"@{FORCE_CHANNEL}", 'user_id': user_id}, timeout=10)
        if response.json().get('ok'):
            status = response.json()['result'].get('status')
            return status in ['member', 'administrator', 'creator']
    except:
        pass
    return False

# ================== دوال البوتات ==================
def stop_bot(bot_id):
    bots = load_json(BOTS_FILE)
    if bot_id not in bots:
        return False
    pid = bots[bot_id].get('pid')
    if pid:
        try:
            os.kill(pid, 9)
        except:
            pass
        bots[bot_id]['pid'] = None
        bots[bot_id]['status'] = 'stopped'
        save_json(BOTS_FILE, bots)
        sync_all_to_github()
    return True

def start_bot(bot_id):
    bots = load_json(BOTS_FILE)
    if bot_id not in bots:
        return False, "البوت غير موجود"
    settings = load_json(SETTINGS_FILE)
    user_id = bots[bot_id].get('user_id')
    if not is_vip(user_id):
        price = settings.get('bot_price_per_hour', 1)
        if get_user_points(user_id) < price:
            return False, f"❌ تحتاج {price} نقطة للساعة"
        remove_points(user_id, price)
    stop_bot(bot_id)
    bot_path = os.path.join(BOTS_DIR, f"{bot_id}.py")
    if not os.path.exists(bot_path):
        return False, "الملف مفقود"
    log_path = os.path.join(LOGS_DIR, f"{bot_id}.log")
    try:
        with open(log_path, 'a') as log:
            proc = subprocess.Popen([sys.executable, bot_path], stdout=log, stderr=log, start_new_session=True)
            bots[bot_id]['pid'] = proc.pid
            bots[bot_id]['status'] = 'running'
            bots[bot_id]['started_at'] = datetime.now().isoformat()
            save_json(BOTS_FILE, bots)
            sync_all_to_github()
            return True, "✅ تم التشغيل"
    except:
        return False, "❌ فشل التشغيل"

def save_bot_file(file_id, user_id, filename):
    url = f"https://api.telegram.org/bot{TOKEN}/getFile"
    response = requests.get(url, params={'file_id': file_id})
    if response.status_code != 200:
        return None, "فشل تحميل الملف"
    file_path = response.json().get('result', {}).get('file_path')
    file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
    content = requests.get(file_url).content
    bot_id = f"bot_{user_id}_{int(time.time())}"
    save_path = os.path.join(BOTS_DIR, f"{bot_id}.py")
    with open(save_path, 'wb') as f:
        f.write(content)
    settings = load_json(SETTINGS_FILE)
    if not is_vip(user_id):
        price = settings.get('hosting_price_per_bot', 5)
        if get_user_points(user_id) < price:
            os.remove(save_path)
            return None, f"❌ تحتاج {price} نقطة للرفع"
        remove_points(user_id, price)
    bots = load_json(BOTS_FILE)
    bots[bot_id] = {
        'user_id': user_id,
        'name': filename.replace('.py', '')[:30],
        'filename': filename,
        'created_at': datetime.now().isoformat(),
        'status': 'stopped',
        'pid': None,
        'started_at': None
    }
    save_json(BOTS_FILE, bots)
    users = load_json(USERS_FILE)
    if str(user_id) in users:
        if 'bots' not in users[str(user_id)]:
            users[str(user_id)]['bots'] = []
        users[str(user_id)]['bots'].append(bot_id)
        save_json(USERS_FILE, users)
    sync_all_to_github()
    return bot_id, f"✅ تم رفع {filename}"

def get_bot_logs(bot_id, lines=50):
    log_path = os.path.join(LOGS_DIR, f"{bot_id}.log")
    if os.path.exists(log_path):
        with open(log_path, 'r', errors='ignore') as f:
            logs = f.readlines()[-lines:]
            return ''.join(logs)
    return "📝 لا توجد سجلات"

def delete_bot(bot_id):
    stop_bot(bot_id)
    bot_path = os.path.join(BOTS_DIR, f"{bot_id}.py")
    log_path = os.path.join(LOGS_DIR, f"{bot_id}.log")
    if os.path.exists(bot_path):
        os.remove(bot_path)
    if os.path.exists(log_path):
        os.remove(log_path)
    bots = load_json(BOTS_FILE)
    user_id = bots.get(bot_id, {}).get('user_id')
    if bot_id in bots:
        del bots[bot_id]
        save_json(BOTS_FILE, bots)
    if user_id:
        users = load_json(USERS_FILE)
        if str(user_id) in users and bot_id in users[str(user_id)].get('bots', []):
            users[str(user_id)]['bots'].remove(bot_id)
            save_json(USERS_FILE, users)
    sync_all_to_github()
    return True

# ================== دوال إرسال الرسائل ==================
def send_message(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'}
    if reply_markup:
        data['reply_markup'] = json.dumps(reply_markup)
    try:
        requests.post(url, json=data, timeout=30)
    except:
        pass

def edit_message(chat_id, message_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{TOKEN}/editMessageText"
    data = {'chat_id': chat_id, 'message_id': message_id, 'text': text, 'parse_mode': 'HTML'}
    if reply_markup:
        data['reply_markup'] = json.dumps(reply_markup)
    try:
        requests.post(url, json=data, timeout=30)
    except:
        pass

def answer_callback(callback_id, text, show_alert=False):
    url = f"https://api.telegram.org/bot{TOKEN}/answerCallbackQuery"
    try:
        requests.post(url, json={'callback_query_id': callback_id, 'text': text, 'show_alert': show_alert}, timeout=30)
    except:
        pass

# ================== لوحات المفاتيح ==================
def main_keyboard(user_id):
    points = get_user_points(user_id)
    vip_status = "👑 VIP" if is_vip(user_id) else "🆓 عادي"
    running_bots = get_running_bots_count(user_id)
    settings = load_json(SETTINGS_FILE)
    return {
        'inline_keyboard': [
            [{'text': f'💰 نقاطك: {points}', 'callback_data': 'balance'}],
            [{'text': f'{vip_status} | 🟢 {running_bots} بوت شغال', 'callback_data': 'vip_info'}],
            [{'text': '📤 رفع بوت', 'callback_data': 'upload_bot'}],
            [{'text': '📁 بوتاتي', 'callback_data': 'my_bots'}],
            [{'text': '🟢 البوتات الشغالة', 'callback_data': 'my_running_bots'}],
            [{'text': '🎁 يومية', 'callback_data': 'daily'}, {'text': '🎊 أسبوعية', 'callback_data': 'weekly'}],
            [{'text': '🔗 رابط الإحالة', 'callback_data': 'referral'}],
            [{'text': '📢 القناة', 'url': settings.get('channel_link', CHANNEL_LINK)}],
            [{'text': '👤 المالك', 'url': f"tg://user?id={ADMIN_ID}"}]
        ]
    }

def admin_keyboard():
    running_bots_count = len(get_all_running_bots())
    return {
        'inline_keyboard': [
            [{'text': '👥 المستخدمين', 'callback_data': 'admin_users'}],
            [{'text': '📁 البوتات', 'callback_data': 'admin_bots'}],
            [{'text': f'🟢 البوتات الشغالة ({running_bots_count})', 'callback_data': 'admin_running_bots'}],
            [{'text': '👑 VIP', 'callback_data': 'admin_vip'}],
            [{'text': '💰 إضافة نقاط', 'callback_data': 'add_points_admin'}],
            [{'text': '📢 إذاعة', 'callback_data': 'admin_broadcast'}],
            [{'text': '⚙️ إعدادات', 'callback_data': 'admin_settings'}],
            [{'text': '🗑️ حذف محادثات المستخدمين', 'callback_data': 'clear_chats'}],
            [{'text': '🔙 رجوع', 'callback_data': 'back_main'}]
        ]
    }

def back_keyboard(callback='back_main'):
    return {'inline_keyboard': [[{'text': '🔙 رجوع', 'callback_data': callback}]]}

# ================== خادم Flask ==================
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return jsonify({'status': 'running', 'bot': 'Hosting Bot'})

@flask_app.route(f'/webhook/{TOKEN}', methods=['POST'])
def webhook():
    update = request.get_json()
    if not update:
        return 'OK', 200
    
    if 'message' in update:
        msg = update['message']
        chat_id = msg['chat']['id']
        user_id = msg['from']['id']
        
        if not check_force_subscribe(user_id) and not is_admin(user_id):
            text = f"🔔 **اشتراك إجباري**\n\nيرجى الاشتراك:\n{CHANNEL_LINK}"
            keyboard = {'inline_keyboard': [[{'text': '📢 اشترك', 'url': CHANNEL_LINK}]]}
            send_message(chat_id, text, keyboard)
            return 'OK', 200
        
        register_user(user_id, msg['from'].get('username'), msg['from'].get('first_name', ''))
        
        if 'text' in msg:
            text = msg['text']
            
            if is_admin(user_id):
                pending = load_json(PENDING_FILE)
                if str(user_id) in pending:
                    action = pending[str(user_id)]
                    if action.startswith('set_'):
                        try:
                            settings = load_json(SETTINGS_FILE)
                            if action == 'set_bot_name':
                                settings['bot_name'] = text
                            elif action == 'set_max_free_bots':
                                settings['max_free_bots'] = int(text)
                            elif action == 'set_daily_points':
                                settings['daily_points'] = int(text)
                            elif action == 'set_weekly_points':
                                settings['weekly_bonus_points'] = int(text)
                            elif action == 'set_hour_price':
                                settings['bot_price_per_hour'] = int(text)
                            elif action == 'set_upload_price':
                                settings['hosting_price_per_bot'] = int(text)
                            elif action == 'set_vip_stars_price':
                                settings['vip_stars_price'] = int(text)
                            elif action == 'set_vip_duration':
                                settings['vip_duration_days'] = int(text)
                            save_json(SETTINGS_FILE, settings)
                            sync_all_to_github()
                            send_message(chat_id, f"✅ تم التحديث: {text}")
                        except:
                            send_message(chat_id, "❌ خطأ في الرقم")
                    elif action == 'add_points':
                        parts = text.split()
                        if len(parts) == 2:
                            try:
                                add_points(int(parts[0]), int(parts[1]))
                                send_message(chat_id, f"✅ تم إضافة {parts[1]} نقطة")
                            except:
                                send_message(chat_id, "❌ خطأ")
                    elif action == 'broadcast':
                        users = load_json(USERS_FILE)
                        success = 0
                        for uid in users:
                            try:
                                send_message(int(uid), text)
                                success += 1
                            except:
                                pass
                        send_message(chat_id, f"✅ تم الإرسال لـ {success} مستخدم")
                    elif action == 'add_vip':
                        try:
                            add_vip(int(text))
                            send_message(chat_id, f"✅ تم ترقية {text} VIP")
                        except:
                            send_message(chat_id, "❌ خطأ")
                    elif action == 'remove_vip':
                        try:
                            remove_vip(int(text))
                            send_message(chat_id, f"✅ تم إزالة VIP من {text}")
                        except:
                            send_message(chat_id, "❌ خطأ")
                    del pending[str(user_id)]
                    save_json(PENDING_FILE, pending)
                    return 'OK', 200
            
            if text == '/start':
                settings = load_json(SETTINGS_FILE)
                start_text = f"""🎉 **مرحباً {msg['from'].get('first_name', '')}**

🤖 **{settings.get('bot_name', 'بوت الاستضافة')}**
👑 المالك: {OWNER_USERNAME}
📢 القناة: {CHANNEL_LINK}

💰 كل ساعة = {settings.get('bot_price_per_hour', 1)} نقطة
📤 رفع بوت = {settings.get('hosting_price_per_bot', 5)} نقطة
💎 VIP بـ {settings.get('vip_stars_price', 100)} نجمة"""
                send_message(chat_id, start_text, main_keyboard(user_id))
        
        elif 'document' in msg:
            doc = msg['document']
            if doc['file_name'].endswith('.py'):
                result, msg_text = save_bot_file(doc['file_id'], user_id, doc['file_name'])
                if result:
                    send_message(chat_id, f"✅ {msg_text}\nايدي البوت: `{result}`")
                else:
                    send_message(chat_id, f"❌ {msg_text}")
            else:
                send_message(chat_id, "❌ أرسل ملف .py فقط")
    
    elif 'callback_query' in update:
        cb = update['callback_query']
        user_id = cb['from']['id']
        chat_id = cb['message']['chat']['id']
        msg_id = cb['message']['message_id']
        data = cb['data']
        
        register_user(user_id, cb['from'].get('username'), cb['from'].get('first_name', ''))
        
        if not check_force_subscribe(user_id) and not is_admin(user_id) and data != 'force_check':
            text = f"🔔 اشترك أولاً:\n{CHANNEL_LINK}"
            keyboard = {'inline_keyboard': [[{'text': '📢 اشترك', 'url': CHANNEL_LINK}], [{'text': '✅ تحقق', 'callback_data': 'force_check'}]]}
            edit_message(chat_id, msg_id, text, keyboard)
            return 'OK', 200
        
        # ================== أزرار المستخدم ==================
        if data == 'back_main':
            send_message(chat_id, "🏠 الرئيسية", main_keyboard(user_id))
        
        elif data == 'balance':
            answer_callback(cb['id'], f"نقاطك: {get_user_points(user_id)}", True)
        
        elif data == 'vip_info':
            if is_vip(user_id):
                text = "👑 أنت VIP\nمميزات: رفع غير محدود + تشغيل بدون نقاط"
            else:
                text = f"💎 VIP بـ {load_json(SETTINGS_FILE).get('vip_stars_price', 100)} نجمة"
            edit_message(chat_id, msg_id, text, {'inline_keyboard': [[{'text': 'شراء VIP', 'callback_data': 'buy_vip'}], [{'text': '🔙 رجوع', 'callback_data': 'back_main'}]]})
        
        elif data == 'buy_vip':
            if is_vip(user_id):
                answer_callback(cb['id'], "أنت بالفعل VIP", True)
            else:
                success, msg = buy_vip_with_stars(user_id)
                answer_callback(cb['id'], msg, True)
                if success:
                    send_message(chat_id, "🎉 مبروك أصبحت VIP", main_keyboard(user_id))
        
        elif data == 'daily':
            success, msg = daily_reward(user_id)
            answer_callback(cb['id'], msg, True)
            if success:
                send_message(chat_id, f"🎁 {msg}\nرصيدك: {get_user_points(user_id)}", main_keyboard(user_id))
        
        elif data == 'weekly':
            success, msg = weekly_reward(user_id)
            answer_callback(cb['id'], msg, True)
            if success:
                send_message(chat_id, f"🎊 {msg}\nرصيدك: {get_user_points(user_id)}", main_keyboard(user_id))
        
        elif data == 'referral':
            bot_info = requests.get(f"https://api.telegram.org/bot{TOKEN}/getMe").json()
            bot_username = bot_info.get('result', {}).get('username', 'bot')
            link = f"https://t.me/{bot_username}?start={user_id}"
            text = f"🔗 رابطك:\n<code>{link}</code>\n💰 كل مدعو يمنحك 10 نقاط"
            edit_message(chat_id, msg_id, text, back_keyboard())
        
        elif data == 'upload_bot':
            allowed, msg = can_upload(user_id)
            if not allowed:
                answer_callback(cb['id'], msg, True)
                return
            edit_message(chat_id, msg_id, "📤 أرسل ملف .py", back_keyboard())
        
        elif data == 'my_bots':
            bots = get_user_bots_list(user_id)
            if not bots:
                edit_message(chat_id, msg_id, "📁 لا بوتات", back_keyboard())
                return
            keyboard = {'inline_keyboard': []}
            for bid, b in bots.items():
                status = "🟢" if b.get('status') == 'running' else "🔴"
                runtime = get_bot_runtime(bid)
                keyboard['inline_keyboard'].append([{'text': f'{status} {b["name"][:15]} - {runtime}', 'callback_data': f'bot_{bid}'}])
            keyboard['inline_keyboard'].append([{'text': '🔙 رجوع', 'callback_data': 'back_main'}])
            edit_message(chat_id, msg_id, f"📁 بوتاتي ({len(bots)})", keyboard)
        
        elif data == 'my_running_bots':
            bots = get_user_bots_list(user_id)
            running_bots = {bid: b for bid, b in bots.items() if b.get('status') == 'running'}
            if not running_bots:
                edit_message(chat_id, msg_id, "🟢 لا توجد بوتات شغالة حالياً", back_keyboard())
                return
            keyboard = {'inline_keyboard': []}
            for bid, b in running_bots.items():
                runtime = get_bot_runtime(bid)
                keyboard['inline_keyboard'].append([{'text': f'🟢 {b["name"][:15]} - {runtime}', 'callback_data': f'bot_{bid}'}])
            keyboard['inline_keyboard'].append([{'text': '🔙 رجوع', 'callback_data': 'back_main'}])
            edit_message(chat_id, msg_id, f"🟢 البوتات الشغالة ({len(running_bots)})", keyboard)
        
        elif data.startswith('bot_'):
            bot_id = data.split('_')[1]
            bot_info = load_json(BOTS_FILE).get(bot_id, {})
            is_running = bot_info.get('status') == 'running'
            runtime = get_bot_runtime(bot_id)
            text = f"🤖 {bot_info.get('name', 'بوت')}\n🟢 {'يعمل' if is_running else 'متوقف'}\n⏰ الوقت: {runtime}"
            keyboard = {
                'inline_keyboard': [
                    [{'text': '⏹️ إيقاف' if is_running else '▶️ تشغيل', 'callback_data': f'startstop_{bot_id}'}],
                    [{'text': '📋 سجلات', 'callback_data': f'logs_{bot_id}'}],
                    [{'text': '🗑️ حذف', 'callback_data': f'delete_{bot_id}'}],
                    [{'text': '🔙 رجوع', 'callback_data': 'my_bots'}]
                ]
            }
            edit_message(chat_id, msg_id, text, keyboard)
        
        elif data.startswith('startstop_'):
            bot_id = data.split('_')[1]
            bots = load_json(BOTS_FILE)
            if bots.get(bot_id, {}).get('status') == 'running':
                stop_bot(bot_id)
                answer_callback(cb['id'], "✅ تم الإيقاف")
            else:
                success, msg = start_bot(bot_id)
                answer_callback(cb['id'], msg)
            bot_info = load_json(BOTS_FILE).get(bot_id, {})
            is_running = bot_info.get('status') == 'running'
            runtime = get_bot_runtime(bot_id)
            text = f"🤖 {bot_info.get('name', 'بوت')}\n🟢 {'يعمل' if is_running else 'متوقف'}\n⏰ الوقت: {runtime}"
            keyboard = {
                'inline_keyboard': [
                    [{'text': '⏹️ إيقاف' if is_running else '▶️ تشغيل', 'callback_data': f'startstop_{bot_id}'}],
                    [{'text': '📋 سجلات', 'callback_data': f'logs_{bot_id}'}],
                    [{'text': '🗑️ حذف', 'callback_data': f'delete_{bot_id}'}],
                    [{'text': '🔙 رجوع', 'callback_data': 'my_bots'}]
                ]
            }
            edit_message(chat_id, msg_id, text, keyboard)
        
        elif data.startswith('logs_'):
            bot_id = data.split('_')[1]
            logs = get_bot_logs(bot_id)
            text = f"📋 سجلات {bot_id}:\n<code>{logs[:3000]}</code>"
            edit_message(chat_id, msg_id, text, back_keyboard(f'bot_{bot_id}'))
        
        elif data.startswith('delete_'):
            bot_id = data.split('_')[1]
            delete_bot(bot_id)
            answer_callback(cb['id'], "✅ تم الحذف")
            bots = get_user_bots_list(user_id)
            if not bots:
                edit_message(chat_id, msg_id, "📁 لا بوتات", back_keyboard())
            else:
                keyboard = {'inline_keyboard': []}
                for bid, b in bots.items():
                    status = "🟢" if b.get('status') == 'running' else "🔴"
                    runtime = get_bot_runtime(bid)
                    keyboard['inline_keyboard'].append([{'text': f'{status} {b["name"][:15]} - {runtime}', 'callback_data': f'bot_{bid}'}])
                keyboard['inline_keyboard'].append([{'text': '🔙 رجوع', 'callback_data': 'back_main'}])
                edit_message(chat_id, msg_id, f"📁 بوتاتي ({len(bots)})", keyboard)
        
        # ================== لوحة الأدمن ==================
        elif data == 'admin_panel' and is_admin(user_id):
            edit_message(chat_id, msg_id, "⚙️ لوحة التحكم", admin_keyboard())
        
        elif data == 'admin_users' and is_admin(user_id):
            users = load_json(USERS_FILE)
            text = f"👥 المستخدمين: {len(users)}"
            edit_message(chat_id, msg_id, text, back_keyboard('admin_panel'))
        
        elif data == 'admin_bots' and is_admin(user_id):
            bots = load_json(BOTS_FILE)
            text = f"📁 البوتات: {len(bots)}"
            edit_message(chat_id, msg_id, text, back_keyboard('admin_panel'))
        
        elif data == 'admin_running_bots' and is_admin(user_id):
            running_bots = get_all_running_bots()
            if not running_bots:
                edit_message(chat_id, msg_id, "🟢 لا توجد بوتات شغالة", back_keyboard('admin_panel'))
                return
            keyboard = {'inline_keyboard': []}
            for bid, b in running_bots.items():
                user_id_bot = b.get('user_id')
                user_info = load_json(USERS_FILE).get(str(user_id_bot), {})
                username = user_info.get('username', user_id_bot)
                runtime = get_bot_runtime(bid)
                keyboard['inline_keyboard'].append([{'text': f'🟢 {b["name"][:12]} - @{username} - {runtime}', 'callback_data': f'admin_bot_{bid}'}])
            keyboard['inline_keyboard'].append([{'text': '⏹️ إيقاف الكل', 'callback_data': 'stop_all_bots'}])
            keyboard['inline_keyboard'].append([{'text': '🔙 رجوع', 'callback_data': 'admin_panel'}])
            edit_message(chat_id, msg_id, f"🟢 البوتات الشغالة ({len(running_bots)})", keyboard)
        
        elif data == 'admin_bot_' and is_admin(user_id):
            bot_id = data.split('_')[2]
            bot_info = load_json(BOTS_FILE).get(bot_id, {})
            is_running = bot_info.get('status') == 'running'
            user_id_bot = bot_info.get('user_id')
            user_info = load_json(USERS_FILE).get(str(user_id_bot), {})
            runtime = get_bot_runtime(bot_id)
            text = f"🤖 {bot_info.get('name', 'بوت')}\n👤 المستخدم: @{user_info.get('username', user_id_bot)}\n🟢 {'يعمل' if is_running else 'متوقف'}\n⏰ وقت التشغيل: {runtime}"
            keyboard = {
                'inline_keyboard': [
                    [{'text': '⏹️ إيقاف' if is_running else '▶️ تشغيل', 'callback_data': f'admin_startstop_{bot_id}'}],
                    [{'text': '📋 سجلات', 'callback_data': f'admin_logs_{bot_id}'}],
                    [{'text': '🔙 رجوع', 'callback_data': 'admin_running_bots'}]
                ]
            }
            edit_message(chat_id, msg_id, text, keyboard)
        
        elif data.startswith('admin_startstop_') and is_admin(user_id):
            bot_id = data.split('_')[2]
            bots = load_json(BOTS_FILE)
            if bots.get(bot_id, {}).get('status') == 'running':
                stop_bot(bot_id)
                answer_callback(cb['id'], "✅ تم إيقاف البوت")
            else:
                send_message(chat_id, "⚠️ لا يمكن تشغيل بوت مستخدم من لوحة الأدمن (يحتاج نقاطه)")
                return
            running_bots = get_all_running_bots()
            if not running_bots:
                edit_message(chat_id, msg_id, "🟢 لا توجد بوتات شغالة", back_keyboard('admin_panel'))
                return
            keyboard = {'inline_keyboard': []}
            for bid, b in running_bots.items():
                user_id_bot = b.get('user_id')
                user_info = load_json(USERS_FILE).get(str(user_id_bot), {})
                username = user_info.get('username', user_id_bot)
                runtime = get_bot_runtime(bid)
                keyboard['inline_keyboard'].append([{'text': f'🟢 {b["name"][:12]} - @{username} - {runtime}', 'callback_data': f'admin_bot_{bid}'}])
            keyboard['inline_keyboard'].append([{'text': '⏹️ إيقاف الكل', 'callback_data': 'stop_all_bots'}])
            keyboard['inline_keyboard'].append([{'text': '🔙 رجوع', 'callback_data': 'admin_panel'}])
            edit_message(chat_id, msg_id, f"🟢 البوتات الشغالة ({len(running_bots)})", keyboard)
        
        elif data == 'stop_all_bots' and is_admin(user_id):
            running_bots = get_all_running_bots()
            stopped = 0
            for bid in running_bots:
                if stop_bot(bid):
                    stopped += 1
            answer_callback(cb['id'], f"✅ تم إيقاف {stopped} بوت", True)
            edit_message(chat_id, msg_id, "⚙️ لوحة التحكم", admin_keyboard())
        
        elif data.startswith('admin_logs_') and is_admin(user_id):
            bot_id = data.split('_')[2]
            logs = get_bot_logs(bot_id)
            text = f"📋 سجلات {bot_id}:\n<code>{logs[:3000]}</code>"
            edit_message(chat_id, msg_id, text, back_keyboard(f'admin_bot_{bot_id}'))
        
        elif data == 'admin_vip' and is_admin(user_id):
            vip_data = load_json(VIP_FILE)
            if not vip_data:
                text = "👑 لا مشتركين VIP"
            else:
                text = "👑 قائمة VIP:\n"
                for uid in vip_data:
                    user_info = load_json(USERS_FILE).get(uid, {})
                    username = user_info.get('username', uid)
                    text += f"• @{username} (`{uid}`)\n"
            keyboard = {
                'inline_keyboard': [
                    [{'text': '➕ إضافة VIP', 'callback_data': 'add_vip_admin'}],
                    [{'text': '➖ إزالة VIP', 'callback_data': 'remove_vip_admin'}],
                    [{'text': '🔙 رجوع', 'callback_data': 'admin_panel'}]
                ]
            }
            edit_message(chat_id, msg_id, text, keyboard)
        
        elif data == 'add_vip_admin' and is_admin(user_id):
            pending = load_json(PENDING_FILE)
            pending[str(user_id)] = 'add_vip'
            save_json(PENDING_FILE, pending)
            edit_message(chat_id, msg_id, "➕ أرسل ايدي المستخدم", back_keyboard('admin_vip'))
        
        elif data == 'remove_vip_admin' and is_admin(user_id):
            pending = load_json(PENDING_FILE)
            pending[str(user_id)] = 'remove_vip'
            save_json(PENDING_FILE, pending)
            edit_message(chat_id, msg_id, "➖ أرسل ايدي المستخدم", back_keyboard('admin_vip'))
        
        elif data == 'add_points_admin' and is_admin(user_id):
            pending = load_json(PENDING_FILE)
            pending[str(user_id)] = 'add_points'
            save_json(PENDING_FILE, pending)
            edit_message(chat_id, msg_id, "💰 أرسل: `ايدي المستخدم عدد النقاط`", back_keyboard('admin_panel'))
        
        elif data == 'admin_broadcast' and is_admin(user_id):
            pending = load_json(PENDING_FILE)
            pending[str(user_id)] = 'broadcast'
            save_json(PENDING_FILE, pending)
            edit_message(chat_id, msg_id, "📢 أرسل رسالتك", back_keyboard('admin_panel'))
        
        elif data == 'admin_settings' and is_admin(user_id):
            keyboard = {
                'inline_keyboard': [
                    [{'text': '✏️ اسم البوت', 'callback_data': 'set_bot_name'}],
                    [{'text': '📁 حد البوتات', 'callback_data': 'set_max_free_bots'}],
                    [{'text': '💰 النقاط اليومية', 'callback_data': 'set_daily_points'}],
                    [{'text': '🎊 النقاط الأسبوعية', 'callback_data': 'set_weekly_points'}],
                    [{'text': '⏱️ سعر الساعة', 'callback_data': 'set_hour_price'}],
                    [{'text': '📤 سعر الرفع', 'callback_data': 'set_upload_price'}],
                    [{'text': '💎 سعر VIP', 'callback_data': 'set_vip_stars_price'}],
                    [{'text': '🔙 رجوع', 'callback_data': 'admin_panel'}]
                ]
            }
            edit_message(chat_id, msg_id, "⚙️ الإعدادات", keyboard)
        
        elif data.startswith('set_') and is_admin(user_id):
            pending = load_json(PENDING_FILE)
            pending[str(user_id)] = data
            save_json(PENDING_FILE, pending)
            edit_message(chat_id, msg_id, f"✏️ أرسل القيمة الجديدة", back_keyboard('admin_settings'))
        
        # ================== حذف المحادثات ==================
        elif data == 'clear_chats' and is_admin(user_id):
            confirm_keyboard = {
                'inline_keyboard': [
                    [{'text': '✅ نعم، احذف كل الرسائل', 'callback_data': 'confirm_clear_chats'}],
                    [{'text': '❌ إلغاء', 'callback_data': 'admin_panel'}]
                ]
            }
            edit_message(chat_id, msg_id, "⚠️ **تحذير!**\n\nسيتم حذف جميع رسائل البوت لجميع المستخدمين.\n**لن تتأثر النقاط أو البوتات أو VIP.**\n\nهل أنت متأكد؟", confirm_keyboard)
        
        elif data == 'confirm_clear_chats' and is_admin(user_id):
            edit_message(chat_id, msg_id, "⏳ جاري حذف رسائل البوت...")
            users = load_json(USERS_FILE)
            deleted_count = 0
            for uid_str in users:
                try:
                    uid = int(uid_str)
                    send_message(uid, "🔄 تم تحديث المحادثة بواسطة الأدمن.")
                    deleted_count += 1
                except:
                    pass
            result_text = f"✅ تم إرسال تحديث لـ {deleted_count} مستخدم."
            edit_message(chat_id, msg_id, result_text, back_keyboard('admin_panel'))
        
        elif data == 'force_check':
            if check_force_subscribe(user_id):
                send_message(chat_id, "✅ اشتراكك مؤكد", main_keyboard(user_id))
            else:
                text = f"❌ لم تشترك في القناة:\n{CHANNEL_LINK}"
                keyboard = {'inline_keyboard': [[{'text': '📢 اشترك', 'url': CHANNEL_LINK}], [{'text': '✅ تحقق', 'callback_data': 'force_check'}]]}
                edit_message(chat_id, msg_id, text, keyboard)
        
        else:
            answer_callback(cb['id'], "⚠️ قيد التطوير", True)
    
    return 'OK', 200

# ================== إعادة ضبط يومية ==================
def reset_daily_status():
    users = load_json(USERS_FILE)
    changed = False
    for uid, data in users.items():
        if 'last_daily' in data:
            data['last_daily'] = None
            changed = True
        if 'last_weekly' in data:
            data['last_weekly'] = None
            changed = True
    if changed:
        save_json(USERS_FILE, users)
        sync_all_to_github()
        print("✅ تم إعادة ضبط الحالات اليومية/الأسبوعية")

def schedule_daily_reset():
    while True:
        now = datetime.now()
        next_midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        seconds_to_wait = (next_midnight - now).total_seconds()
        print(f"⏳ سيتم إعادة الضبط بعد {seconds_to_wait / 3600:.2f} ساعات")
        time.sleep(seconds_to_wait)
        reset_daily_status()

threading.Thread(target=schedule_daily_reset, daemon=True).start()

# ================== التشغيل ==================
if __name__ == '__main__':
    webhook_url = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'localhost')}/webhook/{TOKEN}"
    try:
        requests.get(f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={webhook_url}")
        print(f"✅ Webhook: {webhook_url}")
    except:
        print("⚠️ خطأ في webhook")
    
    print("=" * 50)
    print("🚀 بوت الاستضافة يعمل")
    print(f"👑 المالك: {OWNER_USERNAME}")
    print(f"📢 القناة: {CHANNEL_LINK}")
    print("=" * 50)
    
    flask_app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))