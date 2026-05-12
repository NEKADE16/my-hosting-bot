#!/usr/bin/env python3
# بوت استضافة متكامل - نسخة مستقرة
# المالك: @h7_4c
# قناة البوت: @ArabPyDecode

import os
import sys
import json
import time
import subprocess
import threading
from datetime import datetime, timedelta
from flask import Flask, request
import requests

# ================== التوكن والإعدادات ==================
TOKEN = os.environ.get('BOT_TOKEN', '8560610744:AAG3NdWF1XFacM9CFwrn7pzppO3LXDz_HxA')
ADMIN_ID = int(os.environ.get('ADMIN_ID', '8630079643'))
OWNER_USERNAME = "@h7_4c"
CHANNEL_LINK = "https://t.me/ArabPyDecode"
CHANNEL_USERNAME = "ArabPyDecode"
FORCE_CHANNEL = CHANNEL_USERNAME

# ================== إعداد المجلدات ==================
BOTS_DIR = 'bots'
LOGS_DIR = 'logs'
DB_DIR = 'database'

for d in [BOTS_DIR, LOGS_DIR, DB_DIR]:
    os.makedirs(d, exist_ok=True)

# ================== قاعدة البيانات ==================
USERS_DB = os.path.join(DB_DIR, 'users.json')
BOTS_DB = os.path.join(DB_DIR, 'bots.json')
VIP_DB = os.path.join(DB_DIR, 'vip.json')
SETTINGS_DB = os.path.join(DB_DIR, 'settings.json')
PENDING_ADMIN_DB = os.path.join(DB_DIR, 'pending_admin.json')

def load_json(path):
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return {}

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=4)

def init_db():
    if not os.path.exists(USERS_DB):
        save_json(USERS_DB, {})
    if not os.path.exists(BOTS_DB):
        save_json(BOTS_DB, {})
    if not os.path.exists(VIP_DB):
        save_json(VIP_DB, {})
    if not os.path.exists(PENDING_ADMIN_DB):
        save_json(PENDING_ADMIN_DB, {})
    if not os.path.exists(SETTINGS_DB):
        save_json(SETTINGS_DB, {
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

init_db()

# ================== دوال مساعدة ==================
def is_admin(user_id):
    return user_id == ADMIN_ID

def is_vip(user_id):
    vip_data = load_json(VIP_DB)
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

def get_vip_list():
    vip_data = load_json(VIP_DB)
    return vip_data

def add_vip(user_id, days=30):
    vip_data = load_json(VIP_DB)
    expiry = (datetime.now() + timedelta(days=days)).isoformat()
    vip_data[str(user_id)] = {
        'expiry': expiry,
        'granted_at': datetime.now().isoformat(),
        'granted_by': 'admin'
    }
    save_json(VIP_DB, vip_data)
    return True

def remove_vip(user_id):
    vip_data = load_json(VIP_DB)
    if str(user_id) in vip_data:
        del vip_data[str(user_id)]
        save_json(VIP_DB, vip_data)
        return True
    return False

def get_user_points(user_id):
    users = load_json(USERS_DB)
    return users.get(str(user_id), {}).get('points', 0)

def add_points(user_id, points):
    users = load_json(USERS_DB)
    if str(user_id) not in users:
        users[str(user_id)] = {}
    users[str(user_id)]['points'] = users[str(user_id)].get('points', 0) + points
    save_json(USERS_DB, users)

def remove_points(user_id, points):
    users = load_json(USERS_DB)
    current = users.get(str(user_id), {}).get('points', 0)
    if current < points:
        return False
    users[str(user_id)]['points'] = current - points
    save_json(USERS_DB, users)
    return True

def get_user_telegram_stars(user_id):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/getUserStars"
        params = {'user_id': user_id}
        response = requests.get(url, params=params).json()
        if response.get('ok'):
            return response.get('result', {}).get('stars', 0)
    except:
        pass
    return 0

def buy_vip_with_stars(user_id):
    settings = load_json(SETTINGS_DB)
    price = settings.get('vip_stars_price', 100)
    user_stars = get_user_telegram_stars(user_id)
    
    if user_stars >= price:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/withdrawStars"
            params = {'user_id': user_id, 'amount': price}
            response = requests.get(url, params=params).json()
            if response.get('ok'):
                add_vip(user_id, settings.get('vip_duration_days', 30))
                return True, f"✅ تم شراء VIP بنجاح بـ {price} نجمة!"
            else:
                return False, f"❌ فشل سحب النجوم: {response.get('description', 'خطأ غير معروف')}"
        except Exception as e:
            return False, f"❌ خطأ: {str(e)}"
    return False, f"❌ رصيدك من النجوم غير كافٍ\nتحتاج {price} نجمة\nرصيدك: {user_stars} نجمة"

def get_user_bots_count(user_id):
    bots = load_json(BOTS_DB)
    return sum(1 for b in bots.values() if b.get('user_id') == user_id)

def register_user(user_id, username, first_name):
    users = load_json(USERS_DB)
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
        save_json(USERS_DB, users)
        return True
    return False

def can_upload(user_id):
    if is_admin(user_id) or is_vip(user_id):
        return True, None
    settings = load_json(SETTINGS_DB)
    max_bots = settings.get('max_free_bots', 3)
    current_bots = get_user_bots_count(user_id)
    if current_bots >= max_bots:
        return False, f"❌ لقد وصلت للحد الأقصى ({max_bots}) من البوتات للمستخدم العادي\n💎 اشترك VIP بـ {settings.get('vip_stars_price', 100)} نجمة لرفع غير محدود"
    return True, None

def daily_reward(user_id):
    users = load_json(USERS_DB)
    user = users.get(str(user_id), {})
    last_daily = user.get('last_daily')
    today = datetime.now().date().isoformat()
    
    if last_daily == today:
        return False, "❌ لقد حصلت على مكافأتك اليومية مسبقاً"
    
    settings = load_json(SETTINGS_DB)
    points = settings.get('daily_points', 10)
    
    users[str(user_id)]['last_daily'] = today
    users[str(user_id)]['points'] = users[str(user_id)].get('points', 0) + points
    save_json(USERS_DB, users)
    return True, f"✅ حصلت على {points} نقطة"

def weekly_reward(user_id):
    users = load_json(USERS_DB)
    user = users.get(str(user_id), {})
    last_weekly = user.get('last_weekly')
    today = datetime.now().date().isoformat()
    
    current_week = datetime.now().isocalendar()[1]
    last_week = None
    if last_weekly:
        try:
            last_week = datetime.fromisoformat(last_weekly).isocalendar()[1]
        except:
            pass
    
    if last_week == current_week:
        return False, "❌ لقد حصلت على مكافأتك الأسبوعية مسبقاً"
    
    settings = load_json(SETTINGS_DB)
    points = settings.get('weekly_bonus_points', 20)
    
    users[str(user_id)]['last_weekly'] = today
    users[str(user_id)]['points'] = users[str(user_id)].get('points', 0) + points
    save_json(USERS_DB, users)
    return True, f"✅ حصلت على {points} نقطة (مكافأة أسبوعية)"

def check_force_subscribe(user_id):
    if not FORCE_CHANNEL:
        return True
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/getChatMember"
        params = {'chat_id': f"@{FORCE_CHANNEL}", 'user_id': user_id}
        response = requests.get(url, params=params, timeout=10).json()
        if response.get('ok'):
            status = response['result'].get('status')
            if status in ['member', 'administrator', 'creator']:
                return True
    except Exception as e:
        print(f"Force subscribe check error: {e}")
    return False

# ================== دوال البوتات ==================
def stop_bot(bot_id):
    bots = load_json(BOTS_DB)
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
        save_json(BOTS_DB, bots)
    return True

def start_bot(bot_id):
    bots = load_json(BOTS_DB)
    if bot_id not in bots:
        return False, "البوت غير موجود"
    
    settings = load_json(SETTINGS_DB)
    if not is_vip(bots[bot_id].get('user_id')):
        user_points = get_user_points(bots[bot_id].get('user_id'))
        price = settings.get('bot_price_per_hour', 1)
        if user_points < price:
            return False, f"❌ لا يوجد نقاط كافية\n⭐ كل ساعة تشغيل = {price} نقطة\n💎 اشترك VIP لتشغيل بدون خصم"
        remove_points(bots[bot_id].get('user_id'), price)
    
    stop_bot(bot_id)
    bot_path = os.path.join(BOTS_DIR, f"{bot_id}.py")
    if not os.path.exists(bot_path):
        return False, "ملف البوت غير موجود"
    
    log_path = os.path.join(LOGS_DIR, f"{bot_id}.log")
    try:
        with open(log_path, 'a', encoding='utf-8') as log:
            proc = subprocess.Popen(
                [sys.executable, bot_path],
                stdout=log,
                stderr=log,
                stdin=subprocess.PIPE,
                start_new_session=True,
                cwd=BOTS_DIR
            )
            bots[bot_id]['pid'] = proc.pid
            bots[bot_id]['status'] = 'running'
            bots[bot_id]['started_at'] = datetime.now().isoformat()
            save_json(BOTS_DB, bots)
            return True, "✅ تم تشغيل البوت"
    except Exception as e:
        return False, f"❌ خطأ: {str(e)}"

def save_bot_file(file_id, user_id, filename):
    url = f"https://api.telegram.org/bot{TOKEN}/getFile"
    response = requests.get(url, params={'file_id': file_id})
    if response.status_code != 200:
        return None
    
    file_path = response.json().get('result', {}).get('file_path')
    if not file_path:
        return None
    
    file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
    content = requests.get(file_url).content
    
    bot_id = f"bot_{user_id}_{int(time.time())}"
    save_path = os.path.join(BOTS_DIR, f"{bot_id}.py")
    
    with open(save_path, 'wb') as f:
        f.write(content)
    
    bots = load_json(BOTS_DB)
    settings = load_json(SETTINGS_DB)
    
    if not is_vip(user_id):
        price = settings.get('hosting_price_per_bot', 5)
        if get_user_points(user_id) >= price:
            remove_points(user_id, price)
        else:
            os.remove(save_path)
            return None, f"❌ لا يوجد نقاط كافية\nرفع بوت جديد يحتاج {price} نقطة"
    
    bots[bot_id] = {
        'user_id': user_id,
        'name': filename.replace('.py', '')[:30],
        'filename': filename,
        'created_at': datetime.now().isoformat(),
        'status': 'stopped',
        'pid': None
    }
    save_json(BOTS_DB, bots)
    
    users = load_json(USERS_DB)
    if str(user_id) in users:
        if 'bots' not in users[str(user_id)]:
            users[str(user_id)]['bots'] = []
        users[str(user_id)]['bots'].append(bot_id)
        save_json(USERS_DB, users)
    
    return bot_id, None

def get_bot_logs(bot_id, lines=50):
    log_path = os.path.join(LOGS_DIR, f"{bot_id}.log")
    if os.path.exists(log_path):
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            all_lines = f.readlines()
            last_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
            return ''.join(last_lines)
    return "📝 لا توجد سجلات"

def delete_bot(bot_id):
    stop_bot(bot_id)
    bot_path = os.path.join(BOTS_DIR, f"{bot_id}.py")
    log_path = os.path.join(LOGS_DIR, f"{bot_id}.log")
    if os.path.exists(bot_path):
        os.remove(bot_path)
    if os.path.exists(log_path):
        os.remove(log_path)
    bots = load_json(BOTS_DB)
    user_id = bots.get(bot_id, {}).get('user_id')
    if bot_id in bots:
        del bots[bot_id]
        save_json(BOTS_DB, bots)
    if user_id:
        users = load_json(USERS_DB)
        if str(user_id) in users and 'bots' in users[str(user_id)]:
            if bot_id in users[str(user_id)]['bots']:
                users[str(user_id)]['bots'].remove(bot_id)
            save_json(USERS_DB, users)
    return True

# ================== دوال إرسال الرسائل ==================
def send_message(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'}
    if reply_markup:
        data['reply_markup'] = json.dumps(reply_markup)
    try:
        requests.post(url, json=data, timeout=30)
    except Exception as e:
        print(f"خطأ: {e}")

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
    data = {'callback_query_id': callback_id, 'text': text, 'show_alert': show_alert}
    try:
        requests.post(url, json=data, timeout=30)
    except:
        pass

# ================== لوحات المفاتيح ==================
def main_keyboard(user_id):
    points = get_user_points(user_id)
    vip_status = "👑 VIP" if is_vip(user_id) else "🆓 عادي"
    settings = load_json(SETTINGS_DB)
    
    keyboard = {
        'inline_keyboard': [
            [{'text': f'💰 نقاط البوت: {points}', 'callback_data': 'balance'}],
            [{'text': f'{vip_status}', 'callback_data': 'vip_info'}],
            [{'text': '📤 رفع بوت', 'callback_data': 'upload_bot'}],
            [{'text': '📁 بوتاتي', 'callback_data': 'my_bots'}],
            [{'text': '🎁 مكافأة يومية', 'callback_data': 'daily'}, {'text': '🎊 مكافأة أسبوعية', 'callback_data': 'weekly'}],
            [{'text': '🔗 رابط الإحالة', 'callback_data': 'referral'}],
            [{'text': '📢 قناة البوت', 'url': settings.get('channel_link', CHANNEL_LINK)}],
            [{'text': '👤 المالك', 'url': f"tg://user?id={ADMIN_ID}"}]
        ]
    }
    if is_admin(user_id):
        keyboard['inline_keyboard'].append([{'text': '⚙️ لوحة الإدارة', 'callback_data': 'admin_panel'}])
    return keyboard

def admin_keyboard():
    return {
        'inline_keyboard': [
            [{'text': '👥 المستخدمين', 'callback_data': 'admin_users'}],
            [{'text': '📁 جميع البوتات', 'callback_data': 'admin_bots'}],
            [{'text': '👑 إدارة VIP', 'callback_data': 'admin_vip'}],
            [{'text': '💰 إضافة نقاط', 'callback_data': 'add_points_admin'}],
            [{'text': '📢 إذاعة', 'callback_data': 'admin_broadcast'}],
            [{'text': '⚙️ إعدادات البوت', 'callback_data': 'admin_settings'}],
            [{'text': '🔙 رجوع', 'callback_data': 'back_main'}]
        ]
    }

def admin_settings_keyboard():
    return {
        'inline_keyboard': [
            [{'text': '✏️ اسم البوت', 'callback_data': 'set_bot_name'}],
            [{'text': '📁 حد البوتات المجانية', 'callback_data': 'set_max_free_bots'}],
            [{'text': '💰 النقاط اليومية', 'callback_data': 'set_daily_points'}],
            [{'text': '🎊 النقاط الأسبوعية', 'callback_data': 'set_weekly_points'}],
            [{'text': '⏱️ سعر الساعة', 'callback_data': 'set_hour_price'}],
            [{'text': '📤 سعر رفع البوت', 'callback_data': 'set_upload_price'}],
            [{'text': '💎 سعر VIP (نجوم)', 'callback_data': 'set_vip_stars_price'}],
            [{'text': '⏰ مدة VIP (يوم)', 'callback_data': 'set_vip_duration'}],
            [{'text': '🔙 رجوع', 'callback_data': 'admin_panel'}]
        ]
    }

def vip_info_keyboard():
    settings = load_json(SETTINGS_DB)
    return {
        'inline_keyboard': [
            [{'text': f'💎 شراء VIP بـ {settings.get("vip_stars_price", 100)} نجمة', 'callback_data': 'buy_vip'}],
            [{'text': '🔙 رجوع', 'callback_data': 'back_main'}]
        ]
    }

def back_keyboard(callback_data='back_main'):
    return {'inline_keyboard': [[{'text': '🔙 رجوع', 'callback_data': callback_data}]]}

# ================== معالجة البوت ==================
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return jsonify({'status': 'running', 'bot': 'Hosting Bot', 'owner': OWNER_USERNAME})

@flask_app.route(f'/webhook/{TOKEN}', methods=['POST'])
def webhook():
    update = request.get_json()
    if not update:
        return 'OK', 200
    
    # معالجة الرسائل
    if 'message' in update:
        msg = update['message']
        chat_id = msg['chat']['id']
        user_id = msg['from']['id']
        
        # التحقق من الاشتراك الإجباري
        if not check_force_subscribe(user_id) and not is_admin(user_id):
            settings = load_json(SETTINGS_DB)
            text = f"🔔 **اشتراك إجباري**\n\nيرجى الاشتراك في القناة أولاً:\n{settings.get('channel_link', CHANNEL_LINK)}"
            keyboard = {'inline_keyboard': [[{'text': '📢 اشترك الآن', 'url': settings.get('channel_link', CHANNEL_LINK)}], [{'text': '✅ تحقق', 'callback_data': 'force_check'}]]}
            send_message(chat_id, text, keyboard)
            return 'OK', 200
        
        register_user(user_id, msg['from'].get('username'), msg['from'].get('first_name', ''))
        
        if 'text' in msg:
            text = msg['text']
            
            # معالجة إعدادات الأدمن
            if is_admin(user_id):
                pending = load_json(PENDING_ADMIN_DB)
                if str(user_id) in pending:
                    action = pending[str(user_id)]
                    
                    if action.startswith('set_'):
                        try:
                            settings = load_json(SETTINGS_DB)
                            if action == 'set_bot_name':
                                settings['bot_name'] = text
                                save_json(SETTINGS_DB, settings)
                                send_message(chat_id, f"✅ تم تغيير اسم البوت إلى: {text}")
                            elif action == 'set_max_free_bots':
                                settings['max_free_bots'] = int(text)
                                save_json(SETTINGS_DB, settings)
                                send_message(chat_id, f"✅ تم تغيير حد البوتات المجانية إلى: {text}")
                            elif action == 'set_daily_points':
                                settings['daily_points'] = int(text)
                                save_json(SETTINGS_DB, settings)
                                send_message(chat_id, f"✅ تم تغيير النقاط اليومية إلى: {text}")
                            elif action == 'set_weekly_points':
                                settings['weekly_bonus_points'] = int(text)
                                save_json(SETTINGS_DB, settings)
                                send_message(chat_id, f"✅ تم تغيير النقاط الأسبوعية إلى: {text}")
                            elif action == 'set_hour_price':
                                settings['bot_price_per_hour'] = int(text)
                                save_json(SETTINGS_DB, settings)
                                send_message(chat_id, f"✅ تم تغيير سعر الساعة إلى: {text} نقطة")
                            elif action == 'set_upload_price':
                                settings['hosting_price_per_bot'] = int(text)
                                save_json(SETTINGS_DB, settings)
                                send_message(chat_id, f"✅ تم تغيير سعر رفع البوت إلى: {text} نقطة")
                            elif action == 'set_vip_stars_price':
                                settings['vip_stars_price'] = int(text)
                                save_json(SETTINGS_DB, settings)
                                send_message(chat_id, f"✅ تم تغيير سعر VIP إلى: {text} نجمة")
                            elif action == 'set_vip_duration':
                                settings['vip_duration_days'] = int(text)
                                save_json(SETTINGS_DB, settings)
                                send_message(chat_id, f"✅ تم تغيير مدة VIP إلى: {text} يوم")
                            
                            pending.pop(str(user_id))
                            save_json(PENDING_ADMIN_DB, pending)
                            
                        except ValueError:
                            send_message(chat_id, "❌ الرجاء إرسال رقم صحيح")
                    
                    elif action == 'add_points':
                        parts = text.split()
                        if len(parts) == 2:
                            try:
                                target_id = int(parts[0])
                                points = int(parts[1])
                                add_points(target_id, points)
                                send_message(chat_id, f"✅ تم إضافة {points} نقطة للمستخدم {target_id}")
                            except:
                                send_message(chat_id, "❌ ايدي أو رقم غير صحيح")
                        else:
                            send_message(chat_id, "❌ استخدم: `ايدي المستخدم عدد النقاط`")
                        pending.pop(str(user_id))
                        save_json(PENDING_ADMIN_DB, pending)
                    
                    elif action == 'broadcast':
                        users = load_json(USERS_DB)
                        success = 0
                        for uid in users.keys():
                            try:
                                send_message(int(uid), text)
                                success += 1
                            except:
                                pass
                        send_message(chat_id, f"✅ تم الإذاعة\nتم الإرسال لـ {success} مستخدم")
                        pending.pop(str(user_id))
                        save_json(PENDING_ADMIN_DB, pending)
                    
                    elif action == 'add_vip':
                        try:
                            add_vip(int(text), load_json(SETTINGS_DB).get('vip_duration_days', 30))
                            send_message(chat_id, f"✅ تم ترقية {text} إلى VIP")
                        except:
                            send_message(chat_id, "❌ ايدي غير صحيح")
                        pending.pop(str(user_id))
                        save_json(PENDING_ADMIN_DB, pending)
                    
                    elif action == 'remove_vip':
                        try:
                            remove_vip(int(text))
                            send_message(chat_id, f"✅ تم إزالة VIP من {text}")
                        except:
                            send_message(chat_id, "❌ ايدي غير صحيح")
                        pending.pop(str(user_id))
                        save_json(PENDING_ADMIN_DB, pending)
                    
                    return 'OK', 200
            
            if text == '/start':
                settings = load_json(SETTINGS_DB)
                start_text = f"""🎉 **مرحباً {msg['from'].get('first_name', '')}**

🤖 **{settings.get('bot_name', 'بوت الاستضافة')}**
👑 المالك: {settings.get('owner', OWNER_USERNAME)}
📢 القناة: {settings.get('channel_link', CHANNEL_LINK)}

📌 **المميزات:**
• رفع وتشغيل البوتات
• نقاط يومية وأسبوعية مجانية
• نظام VIP بنجوم تيليجرام
• اشتراك إجباري للقناة

💰 **أسعار الاستضافة:**
• كل ساعة تشغيل = {settings.get('bot_price_per_hour', 1)} نقطة
• رفع بوت جديد = {settings.get('hosting_price_per_bot', 5)} نقطة
• رفع غير محدود للـ VIP

💎 **VIP:** {settings.get('vip_stars_price', 100)} نجمة تيليجرام = {settings.get('vip_duration_days', 30)} يوم مميزات غير محدودة"""
                send_message(chat_id, start_text, main_keyboard(user_id))
    
    # معالجة الأزرار
    elif 'callback_query' in update:
        callback = update['callback_query']
        user_id = callback['from']['id']
        message = callback['message']
        chat_id = message['chat']['id']
        message_id = message['message_id']
        data = callback['data']
        
        register_user(user_id, callback['from'].get('username'), callback['from'].get('first_name', ''))
        
        if not check_force_subscribe(user_id) and not is_admin(user_id) and data != 'force_check':
            settings = load_json(SETTINGS_DB)
            text = f"🔔 **اشتراك إجباري**\n\nيرجى الاشتراك في القناة أولاً:\n{settings.get('channel_link', CHANNEL_LINK)}"
            keyboard = {'inline_keyboard': [[{'text': '📢 اشترك الآن', 'url': settings.get('channel_link', CHANNEL_LINK)}], [{'text': '✅ تحقق', 'callback_data': 'force_check'}]]}
            edit_message(chat_id, message_id, text, keyboard)
            return 'OK', 200
        
        if data == 'back_main':
            send_message(chat_id, "🏠 **القائمة الرئيسية**", main_keyboard(user_id))
        
        elif data == 'balance':
            points = get_user_points(user_id)
            answer_callback(callback['id'], f"💰 نقاط البوت: {points}\n⭐ كل نقطة = ساعة تشغيل", True)
        
        elif data == 'vip_info':
            if is_vip(user_id):
                vip_data = load_json(VIP_DB).get(str(user_id), {})
                expiry = vip_data.get('expiry', 'غير معروف')
                if expiry != 'lifetime':
                    try:
                        exp_date = datetime.fromisoformat(expiry)
                        days_left = (exp_date - datetime.now()).days
                        expiry = f"{days_left} يوم متبقي"
                    except:
                        pass
                text = f"👑 **أنت مشترك VIP**\n\n⏰ الصلاحية: {expiry}\n✨ مميزات VIP:\n• رفع غير محدود للبوتات\n• تشغيل بدون خصم نقاط\n• أيقونة VIP\n• دعم أولوية"
            else:
                settings = load_json(SETTINGS_DB)
                text = f"💎 **نظام VIP**\n\nالسعر: {settings.get('vip_stars_price', 100)} نجمة تيليجرام\nالمدة: {settings.get('vip_duration_days', 30)} يوم\n\n✨ **المميزات:**\n• رفع غير محدود للبوتات\n• تشغيل بدون خصم نقاط\n• أيقونة VIP\n• دعم أولوية\n• حد أعلى للبوتات"
            edit_message(chat_id, message_id, text, vip_info_keyboard())
        
        elif data == 'buy_vip':
            if is_vip(user_id):
                answer_callback(callback['id'], "❌ أنت بالفعل مشترك VIP", True)
                return
            success, msg = buy_vip_with_stars(user_id)
            answer_callback(callback['id'], msg, True)
            if success:
                send_message(chat_id, "🎉 **مبروك! أنت الآن مشترك VIP**\n\nتم ترقيتك واستمتع بالمميزات", main_keyboard(user_id))
        
        elif data == 'daily':
            success, msg = daily_reward(user_id)
            answer_callback(callback['id'], msg, True)
            if success:
                points = get_user_points(user_id)
                send_message(chat_id, f"🎁 **المكافأة اليومية**\n\n{msg}\n💰 رصيدك الحالي: {points} نقطة", main_keyboard(user_id))
        
        elif data == 'weekly':
            success, msg = weekly_reward(user_id)
            answer_callback(callback['id'], msg, True)
            if success:
                points = get_user_points(user_id)
                send_message(chat_id, f"🎊 **المكافأة الأسبوعية**\n\n{msg}\n💰 رصيدك الحالي: {points} نقطة", main_keyboard(user_id))
        
        elif data == 'referral':
            bot_info = requests.get(f"https://api.telegram.org/bot{TOKEN}/getMe").json()
            bot_username = bot_info.get('result', {}).get('username', 'bot')
            link = f"https://t.me/{bot_username}?start={user_id}"
            text = f"🔗 **رابط الإحالة الخاص بك**\n\n<code>{link}</code>\n\n💰 كل مستخدم يدخل عبر رابطك يمنحك 10 نقاط!"
            edit_message(chat_id, message_id, text, back_keyboard('back_main'))
        
        elif data == 'upload_bot':
            allowed, msg = can_upload(user_id)
            if not allowed:
                answer_callback(callback['id'], msg, True)
                return
            edit_message(chat_id, message_id, "📤 **رفع بوت جديد**\n\nأرسل ملف <code>.py</code>", back_keyboard('back_main'))
        
        elif data == 'my_bots':
            bots = load_json(BOTS_DB)
            user_bots = {bid: b for bid, b in bots.items() if b.get('user_id') == user_id}
            if not user_bots:
                edit_message(chat_id, message_id, "📁 **لا يوجد لديك بوتات**\n\nاضغط على 'رفع بوت' لرفع أول بوت لك", back_keyboard('back_main'))
                return
            keyboard = {'inline_keyboard': []}
            for bid, b in user_bots.items():
                status = "🟢" if b.get('status') == 'running' else "🔴"
                name = b.get('name', 'بوت')[:25]
                keyboard['inline_keyboard'].append([{'text': f'{status} {name}', 'callback_data': f'bot_{bid}'}])
            keyboard['inline_keyboard'].append([{'text': '🔙 رجوع', 'callback_data': 'back_main'}])
            edit_message(chat_id, message_id, f"📁 **بوتاتي** ({len(user_bots)})", keyboard)
        
        elif data.startswith('bot_'):
            bot_id = data.split('_')[1]
            bots = load_json(BOTS_DB)
            bot_info = bots.get(bot_id, {})
            is_running = bot_info.get('status') == 'running'
            text = f"""🤖 **{bot_info.get('name', 'بوت')}**

📅 الرفع: {bot_info.get('created_at', 'غير معروف')[:16]}
🟢 الحالة: {'يعمل ✅' if is_running else 'متوقف ❌'}
📁 الملف: {bot_info.get('filename', '')}"""
            keyboard = {
                'inline_keyboard': [
                    [{'text': '⏹️ إيقاف' if is_running else '▶️ تشغيل', 'callback_data': f'startstop_{bot_id}'}],
                    [{'text': '📋 سجلات', 'callback_data': f'logs_{bot_id}'}],
                    [{'text': '🗑️ حذف', 'callback_data': f'delete_{bot_id}'}],
                    [{'text': '🔙 رجوع', 'callback_data': 'my_bots'}]
                ]
            }
            edit_message(chat_id, message_id, text, keyboard)
        
        elif data.startswith('startstop_'):
            bot_id = data.split('_')[1]
            bots = load_json(BOTS_DB)
            if bots.get(bot_id, {}).get('status') == 'running':
                stop_bot(bot_id)
                answer_callback(callback['id'], "✅ تم إيقاف البوت")
            else:
                success, msg = start_bot(bot_id)
                answer_callback(callback['id'], msg)
            bots = load_json(BOTS_DB)
            bot_info = bots.get(bot_id, {})
            is_running = bot_info.get('status') == 'running'
            text = f"""🤖 **{bot_info.get('name', 'بوت')}**

📅 الرفع: {bot_info.get('created_at', 'غير معروف')[:16]}
🟢 الحالة: {'يعمل ✅' if is_running else 'متوقف ❌'}"""
            keyboard = {
                'inline_keyboard': [
                    [{'text': '⏹️ إيقاف' if is_running else '▶️ تشغيل', 'callback_data': f'startstop_{bot_id}'}],
                    [{'text': '📋 سجلات', 'callback_data': f'logs_{bot_id}'}],
                    [{'text': '🗑️ حذف', 'callback_data': f'delete_{bot_id}'}],
                    [{'text': '🔙 رجوع', 'callback_data': 'my_bots'}]
                ]
            }
            edit_message(chat_id, message_id, text, keyboard)
        
        elif data.startswith('logs_'):
            bot_id = data.split('_')[1]
            logs = get_bot_logs(bot_id)
            text = f"📋 **سجلات البوت**\n\n<code>{logs[:3000]}</code>"
            edit_message(chat_id, message_id, text, back_keyboard(f'bot_{bot_id}'))
        
        elif data.startswith('delete_'):
            bot_id = data.split('_')[1]
            delete_bot(bot_id)
            answer_callback(callback['id'], "✅ تم حذف البوت")
            bots = load_json(BOTS_DB)
            user_bots = {bid: b for bid, b in bots.items() if b.get('user_id') == user_id}
            if not user_bots:
                edit_message(chat_id, message_id, "📁 **لا يوجد لديك بوتات**", back_keyboard('back_main'))
            else:
                keyboard = {'inline_keyboard': []}
                for bid, b in user_bots.items():
                    status = "🟢" if b.get('status') == 'running' else "🔴"
                    name = b.get('name', 'بوت')[:25]
                    keyboard['inline_keyboard'].append([{'text': f'{status} {name}', 'callback_data': f'bot_{bid}'}])
                keyboard['inline_keyboard'].append([{'text': '🔙 رجوع', 'callback_data': 'back_main'}])
                edit_message(chat_id, message_id, f"📁 **بوتاتي** ({len(user_bots)})", keyboard)
        
        # ================== لوحة الأدمن ==================
        elif data == 'admin_panel' and is_admin(user_id):
            edit_message(chat_id, message_id, "⚙️ **لوحة التحكم**", admin_keyboard())
        
        elif data == 'admin_vip' and is_admin(user_id):
            keyboard = {
                'inline_keyboard': [
                    [{'text': '➕ إضافة VIP', 'callback_data': 'add_vip_admin'}],
                    [{'text': '➖ إزالة VIP', 'callback_data': 'remove_vip_admin'}],
                    [{'text': '👑 قائمة VIP', 'callback_data': 'list_vip_admin'}],
                    [{'text': '🔙 رجوع', 'callback_data': 'admin_panel'}]
                ]
            }
            edit_message(chat_id, message_id, "👑 **إدارة VIP**", keyboard)
        
        elif data == 'add_vip_admin' and is_admin(user_id):
            pending = load_json(PENDING_ADMIN_DB)
            pending[str(user_id)] = 'add_vip'
            save_json(PENDING_ADMIN_DB, pending)
            edit_message(chat_id, message_id, "➕ **إضافة VIP**\n\nأرسل ايدي المستخدم:", back_keyboard('admin_vip'))
        
        elif data == 'remove_vip_admin' and is_admin(user_id):
            pending = load_json(PENDING_ADMIN_DB)
            pending[str(user_id)] = 'remove_vip'
            save_json(PENDING_ADMIN_DB, pending)
            edit_message(chat_id, message_id, "➖ **إزالة VIP**\n\nأرسل ايدي المستخدم:", back_keyboard('admin_vip'))
        
        elif data == 'list_vip_admin' and is_admin(user_id):
            vip_data = get_vip_list()
            if not vip_data:
                text = "👑 **قائمة VIP**\n\nلا يوجد مشتركين VIP"
            else:
                text = "👑 **قائمة مشتركين VIP**\n\n"
                for uid, info in vip_data.items():
                    expiry = info.get('expiry', 'غير معروف')
                    if expiry != 'lifetime':
                        try:
                            days = (datetime.fromisoformat(expiry) - datetime.now()).days
                            expiry = f"{days} يوم متبقي"
                        except:
                            pass
                    text += f"• <code>{uid}</code> - {expiry}\n"
            edit_message(chat_id, message_id, text, back_keyboard('admin_vip'))
        
        elif data == 'admin_settings' and is_admin(user_id):
            edit_message(chat_id, message_id, "⚙️ **إعدادات البوت**\n\nاختر الإعداد الذي تريد تعديله:", admin_settings_keyboard())
        
        elif data == 'set_bot_name' and is_admin(user_id):
            pending = load_json(PENDING_ADMIN_DB)
            pending[str(user_id)] = 'set_bot_name'
            save_json(PENDING_ADMIN_DB, pending)
            edit_message(chat_id, message_id, "✏️ **تغيير اسم البوت**\n\nأرسل الاسم الجديد:", back_keyboard('admin_settings'))
        
        elif data == 'set_max_free_bots' and is_admin(user_id):
            pending = load_json(PENDING_ADMIN_DB)
            pending[str(user_id)] = 'set_max_free_bots'
            save_json(PENDING_ADMIN_DB, pending)
            edit_message(chat_id, message_id, "📁 **تحديد حد البوتات المجانية**\n\nأرسل الرقم (مثال: 3):", back_keyboard('admin_settings'))
        
        elif data == 'set_daily_points' and is_admin(user_id):
            pending = load_json(PENDING_ADMIN_DB)
            pending[str(user_id)] = 'set_daily_points'
            save_json(PENDING_ADMIN_DB, pending)
            edit_message(chat_id, message_id, "💰 **تحديد النقاط اليومية**\n\nأرسل الرقم (مثال: 10):", back_keyboard('admin_settings'))
        
        elif data == 'set_weekly_points' and is_admin(user_id):
            pending = load_json(PENDING_ADMIN_DB)
            pending[str(user_id)] = 'set_weekly_points'
            save_json(PENDING_ADMIN_DB, pending)
            edit_message(chat_id, message_id, "🎊 **تحديد النقاط الأسبوعية**\n\nأرسل الرقم (مثال: 20):", back_keyboard('admin_settings'))
        
        elif data == 'set_hour_price' and is_admin(user_id):
            pending = load_json(PENDING_ADMIN_DB)
            pending[str(user_id)] = 'set_hour_price'
            save_json(PENDING_ADMIN_DB, pending)
            edit_message(chat_id, message_id, "⏱️ **تحديد سعر الساعة**\n\nأرسل الرقم (مثال: 1):", back_keyboard('admin_settings'))
        
        elif data == 'set_upload_price' and is_admin(user_id):
            pending = load_json(PENDING_ADMIN_DB)
            pending[str(user_id)] = 'set_upload_price'
            save_json(PENDING_ADMIN_DB, pending)
            edit_message(chat_id, message_id, "📤 **تحديد سعر رفع البوت**\n\nأرسل الرقم (مثال: 5):", back_keyboard('admin_settings'))
        
        elif data == 'set_vip_stars_price' and is_admin(user_id):
            pending = load_json(PENDING_ADMIN_DB)
            pending[str(user_id)] = 'set_vip_stars_price'
            save_json(PENDING_ADMIN_DB, pending)
            edit_message(chat_id, message_id, "💎 **تحديد سعر VIP بالنجوم**\n\nأرسل الرقم (مثال: 100):", back_keyboard('admin_settings'))
        
        elif data == 'set_vip_duration' and is_admin(user_id):
            pending = load_json(PENDING_ADMIN_DB)
            pending[str(user_id)] = 'set_vip_duration'
            save_json(PENDING_ADMIN_DB, pending)
            edit_message(chat_id, message_id, "⏰ **تحديد مدة VIP بالأيام**\n\nأرسل الرقم (مثال: 30):", back_keyboard('admin_settings'))
        
        elif data == 'add_points_admin' and is_admin(user_id):
            pending = load_json(PENDING_ADMIN_DB)
            pending[str(user_id)] = 'add_points'
            save_json(PENDING_ADMIN_DB, pending)
            edit_message(chat_id, message_id, "💰 **إضافة نقاط**\n\nأرسل (ايدي المستخدم) (عدد النقاط)\nمثال: `8630079643 100`", back_keyboard('admin_panel'))
        
        elif data == 'admin_broadcast' and is_admin(user_id):
            pending = load_json(PENDING_ADMIN_DB)
            pending[str(user_id)] = 'broadcast'
            save_json(PENDING_ADMIN_DB, pending)
            edit_message(chat_id, message_id, "📢 **إذاعة**\n\nأرسل الرسالة:", back_keyboard('admin_panel'))
        
        elif data == 'admin_users' and is_admin(user_id):
            users = load_json(USERS_DB)
            text = f"👥 **المستخدمين**\n\nالعدد: {len(users)}"
            edit_message(chat_id, message_id, text, back_keyboard('admin_panel'))
        
        elif data == 'admin_bots' and is_admin(user_id):
            bots = load_json(BOTS_DB)
            text = f"📁 **جميع البوتات**\n\nالعدد: {len(bots)}"
            edit_message(chat_id, message_id, text, back_keyboard('admin_panel'))
        
        elif data == 'force_check':
            if check_force_subscribe(user_id):
                send_message(chat_id, "✅ **تم التحقق من اشتراكك**\n\nمرحباً بك في البوت", main_keyboard(user_id))
            else:
                settings = load_json(SETTINGS_DB)
                text = f"❌ **لم تشترك بعد**\n\nيرجى الاشتراك في القناة:\n{settings.get('channel_link', CHANNEL_LINK)}"
                keyboard = {'inline_keyboard': [[{'text': '📢 اشترك الآن', 'url': settings.get('channel_link', CHANNEL_LINK)}], [{'text': '✅ تحقق مجدداً', 'callback_data': 'force_check'}]]}
                edit_message(chat_id, message_id, text, keyboard)
        
        else:
            answer_callback(callback['id'], "⚠️ جاري التطوير", True)
    
    return 'OK', 200

# ================== تشغيل الخادم ==================
if __name__ == '__main__':
    # تعيين الويب هوك
    webhook_url = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'localhost')}/webhook/{TOKEN}"
    try:
        requests.get(f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={webhook_url}")
        print(f"✅ تم تعيين Webhook: {webhook_url}")
    except Exception as e:
        print(f"⚠️ خطأ في تعيين Webhook: {e}")
    
    print("=" * 50)
    print("🚀 بوت الاستضافة مع نظام VIP ونقاط متكامل")
    print("=" * 50)
    print(f"👑 المالك: {OWNER_USERNAME}")
    print(f"📢 القناة: {CHANNEL_LINK}")
    print(f"✅ التوكن: {TOKEN[:15]}...")
    print("=" * 50)
    print("\n📋 الإعدادات الحالية:")
    settings = load_json(SETTINGS_DB)
    print(f"   📁 حد البوتات المجانية: {settings.get('max_free_bots', 3)}")
    print(f"   💰 النقاط اليومية: {settings.get('daily_points', 10)}")
    print(f"   🎊 النقاط الأسبوعية: {settings.get('weekly_bonus_points', 20)}")
    print(f"   ⏱️ سعر الساعة: {settings.get('bot_price_per_hour', 1)} نقطة")
    print(f"   📤 سعر رفع البوت: {settings.get('hosting_price_per_bot', 5)} نقطة")
    print(f"   💎 سعر VIP: {settings.get('vip_stars_price', 100)} نجمة")
    print(f"   ⏰ مدة VIP: {settings.get('vip_duration_days', 30)} يوم")
    print("=" * 50)
    
    flask_app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))