#!/usr/bin/env python3
# بوت استضافة البوتات - النسخة الكاملة المتكاملة
# يعمل على Python 3.6+ مع Render.com أو أي استضافة

import os
import sys
import json
import time
import uuid
import zipfile
import subprocess
import threading
import shutil
import re
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, request, jsonify
import requests

# ================== التوكن والإعدادات ==================
# جلب التوكن من متغيرات البيئة (للأمان)
TOKEN = os.environ.get('BOT_TOKEN', '8502642404:AAGoKelLs33_pp50pVlW_IPdpP0G3BqEfvA')
ADMIN_ID = int(os.environ.get('ADMIN_ID', '8630079643'))
WEBHOOK_URL = os.environ.get('RENDER_EXTERNAL_HOSTNAME', '')

# ================== إعداد المجلدات ==================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BOTS_DIR = os.path.join(BASE_DIR, 'bots')
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
DB_DIR = os.path.join(BASE_DIR, 'database')
TEMP_DIR = os.path.join(BASE_DIR, 'temp')

for d in [BOTS_DIR, LOGS_DIR, DB_DIR, TEMP_DIR]:
    os.makedirs(d, exist_ok=True)

# ================== قاعدة البيانات ==================
USERS_DB = os.path.join(DB_DIR, 'users.json')
BOTS_DB = os.path.join(DB_DIR, 'bots.json')
PENDING_DB = os.path.join(DB_DIR, 'pending.json')
SETTINGS_DB = os.path.join(DB_DIR, 'settings.json')

def load_json(path, default=None):
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return default if default is not None else {}
    return default if default is not None else {}

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# تهيئة قواعد البيانات
if not os.path.exists(USERS_DB):
    save_json(USERS_DB, {})
if not os.path.exists(BOTS_DB):
    save_json(BOTS_DB, {})
if not os.path.exists(PENDING_DB):
    save_json(PENDING_DB, {})
if not os.path.exists(SETTINGS_DB):
    save_json(SETTINGS_DB, {
        'bot_name': 'بوت الاستضافة',
        'bot_image': None,
        'channels': [],
        'auto_approve': True,
        'points_per_hour': 1
    })

# ================== دوال مساعدة ==================
def is_admin(user_id):
    return user_id == ADMIN_ID or user_id in load_json(USERS_DB).get(str(user_id), {}).get('admins', [])

def get_user(user_id):
    users = load_json(USERS_DB)
    return users.get(str(user_id), {})

def save_user(user_id, data):
    users = load_json(USERS_DB)
    users[str(user_id)] = data
    save_json(USERS_DB, users)

def register_user(user_id, username, first_name):
    if str(user_id) not in load_json(USERS_DB):
        save_user(user_id, {
            'username': username,
            'first_name': first_name,
            'join_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'bots': [],
            'points': 10,
            'is_banned': False,
            'admins': []
        })
        return True
    return False

def get_user_bots(user_id):
    bots = load_json(BOTS_DB)
    return {bid: b for bid, b in bots.items() if b.get('user_id') == user_id}

# ================== دوال تشغيل البوتات ==================
def start_bot(bot_id):
    bots = load_json(BOTS_DB)
    if bot_id not in bots:
        return False, "البوت غير موجود"
    
    bot_info = bots[bot_id]
    bot_path = os.path.join(BOTS_DIR, f"{bot_id}.py")
    
    if not os.path.exists(bot_path):
        return False, "ملف البوت غير موجود"
    
    # إيقاف البوت إذا كان يعمل
    stop_bot(bot_id)
    
    # تشغيل البوت
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
            bots[bot_id]['started_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            save_json(BOTS_DB, bots)
            return True, "تم تشغيل البوت بنجاح"
    except Exception as e:
        return False, f"خطأ في التشغيل: {str(e)}"

def stop_bot(bot_id):
    bots = load_json(BOTS_DB)
    if bot_id not in bots:
        return False
    
    pid = bots[bot_id].get('pid')
    if pid:
        try:
            # محاولة إنهاء العملية بلطف أولاً
            os.kill(pid, 15)
            time.sleep(1)
            # ثم بالقوة إذا لزم الأمر
            os.kill(pid, 9)
        except:
            pass
        bots[bot_id]['pid'] = None
        bots[bot_id]['status'] = 'stopped'
        save_json(BOTS_DB, bots)
    return True

def delete_bot(bot_id):
    stop_bot(bot_id)
    
    # حذف الملفات
    bot_path = os.path.join(BOTS_DIR, f"{bot_id}.py")
    log_path = os.path.join(LOGS_DIR, f"{bot_id}.log")
    
    if os.path.exists(bot_path):
        os.remove(bot_path)
    if os.path.exists(log_path):
        os.remove(log_path)
    
    bots = load_json(BOTS_DB)
    if bot_id in bots:
        # حذف من قائمة البوتات عند المستخدم
        user_id = bots[bot_id].get('user_id')
        if user_id:
            user = get_user(user_id)
            if bot_id in user.get('bots', []):
                user['bots'].remove(bot_id)
                save_user(user_id, user)
        
        del bots[bot_id]
        save_json(BOTS_DB, bots)
    
    return True

def get_bot_logs(bot_id, lines=50):
    log_path = os.path.join(LOGS_DIR, f"{bot_id}.log")
    if os.path.exists(log_path):
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            all_lines = f.readlines()
            last_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
            return ''.join(last_lines)
    return "📝 لا توجد سجلات حتى الآن"

# ================== دوال إرسال الرسائل ==================
def send_message(chat_id, text, reply_markup=None, photo=None):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML'
    }
    if reply_markup:
        data['reply_markup'] = json.dumps(reply_markup)
    
    try:
        if photo:
            url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
            data['photo'] = photo
        response = requests.post(url, json=data, timeout=30)
        return response.json()
    except Exception as e:
        print(f"خطأ في الإرسال: {e}")
        return None

def edit_message(chat_id, message_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{TOKEN}/editMessageText"
    data = {
        'chat_id': chat_id,
        'message_id': message_id,
        'text': text,
        'parse_mode': 'HTML'
    }
    if reply_markup:
        data['reply_markup'] = json.dumps(reply_markup)
    
    try:
        response = requests.post(url, json=data, timeout=30)
        return response.json()
    except:
        return None

def answer_callback(callback_id, text, show_alert=False):
    url = f"https://api.telegram.org/bot{TOKEN}/answerCallbackQuery"
    data = {
        'callback_query_id': callback_id,
        'text': text,
        'show_alert': show_alert
    }
    try:
        requests.post(url, json=data, timeout=30)
    except:
        pass

def send_document(chat_id, file_path, caption=''):
    url = f"https://api.telegram.org/bot{TOKEN}/sendDocument"
    with open(file_path, 'rb') as f:
        files = {'document': f}
        data = {'chat_id': chat_id, 'caption': caption, 'parse_mode': 'HTML'}
        try:
            response = requests.post(url, data=data, files=files, timeout=60)
            return response.json()
        except Exception as e:
            print(f"خطأ في إرسال الملف: {e}")
            return None

# ================== لوحات المفاتيح ==================
def main_keyboard(user_id):
    user = get_user(user_id)
    points = user.get('points', 0)
    
    keyboard = {
        'inline_keyboard': [
            [{'text': f'💰 الرصيد: {points} نقطة', 'callback_data': 'balance'}],
            [{'text': '📤 رفع بوت جديد', 'callback_data': 'upload_bot'}],
            [{'text': '📁 بوتاتي', 'callback_data': 'my_bots'}],
            [{'text': '👤 معلومات حسابي', 'callback_data': 'my_info'}],
            [{'text': '🔗 رابط الإحالة', 'callback_data': 'referral'}]
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
            [{'text': '⏳ الطلبات المعلقة', 'callback_data': 'admin_pending'}],
            [{'text': '📢 إذاعة', 'callback_data': 'admin_broadcast'}],
            [{'text': '⚙️ الإعدادات', 'callback_data': 'admin_settings'}],
            [{'text': '🔙 رجوع للرئيسية', 'callback_data': 'back_main'}]
        ]
    }

def back_keyboard(callback_data='back_main'):
    return {'inline_keyboard': [[{'text': '🔙 رجوع', 'callback_data': callback_data}]]}

# ================== دوال عرض البيانات ==================
def show_my_bots(chat_id, message_id, user_id):
    bots = get_user_bots(user_id)
    
    if not bots:
        text = "📁 **لا يوجد لديك بوتات بعد**\n\nاضغط على 'رفع بوت جديد' لرفع أول بوت لك"
        keyboard = back_keyboard('back_main')
        edit_message(chat_id, message_id, text, keyboard)
        return
    
    keyboard = {'inline_keyboard': []}
    for bid, b in bots.items():
        status = "🟢" if b.get('status') == 'running' else "🔴"
        name = b.get('name', 'بوت')[:25]
        keyboard['inline_keyboard'].append([{'text': f'{status} {name}', 'callback_data': f'bot_{bid}'}])
    
    keyboard['inline_keyboard'].append([{'text': '🔙 رجوع', 'callback_data': 'back_main'}])
    
    text = f"📁 **بوتاتي** ({len(bots)})\n\nاختر بوتاً لإدارته:"
    edit_message(chat_id, message_id, text, keyboard)

def show_bot_panel(chat_id, message_id, user_id, bot_id):
    bots = load_json(BOTS_DB)
    bot_info = bots.get(bot_id, {})
    
    if bot_info.get('user_id') != user_id and not is_admin(user_id):
        edit_message(chat_id, message_id, "❌ هذا البوت ليس ملكك")
        return
    
    is_running = bot_info.get('status') == 'running'
    
    keyboard = {
        'inline_keyboard': [
            [{'text': '⏹️ إيقاف' if is_running else '▶️ تشغيل', 'callback_data': f'startstop_{bot_id}'}],
            [{'text': '📋 السجلات', 'callback_data': f'logs_{bot_id}'}],
            [{'text': '📥 تحميل', 'callback_data': f'download_{bot_id}'}],
            [{'text': '🗑️ حذف', 'callback_data': f'delete_{bot_id}'}],
            [{'text': '🔙 رجوع', 'callback_data': 'my_bots'}]
        ]
    }
    
    text = f"""🤖 **{bot_info.get('name', 'بوت')}**

📅 تاريخ الرفع: {bot_info.get('created_at', 'غير معروف')}
🟢 الحالة: {'يعمل ✅' if is_running else 'متوقف ❌'}
📁 الملف: {bot_info.get('filename', '')}
{'🕐 بدء التشغيل: ' + bot_info.get('started_at', '') if is_running else ''}"""
    
    edit_message(chat_id, message_id, text, keyboard)

def show_user_info(chat_id, message_id, user_id, target_id=None):
    if target_id:
        user = get_user(target_id)
        if not user:
            edit_message(chat_id, message_id, "❌ المستخدم غير موجود")
            return
    else:
        user = get_user(user_id)
        target_id = user_id
    
    bots = get_user_bots(target_id)
    
    text = f"""👤 **معلومات المستخدم**

🆔 الايدي: <code>{target_id}</code>
👤 الاسم: {user.get('first_name', '')}
🔗 المعرف: @{user.get('username', 'لا يوجد')}
📅 تاريخ التسجيل: {user.get('join_date', '')}
💰 النقاط: {user.get('points', 0)}
📁 عدد البوتات: {len(bots)}"""
    
    keyboard = back_keyboard('back_main')
    edit_message(chat_id, message_id, text, keyboard)

def show_admin_users(chat_id, message_id, page=0):
    users = load_json(USERS_DB)
    user_list = list(users.items())
    items_per_page = 8
    total_pages = (len(user_list) + items_per_page - 1) // items_per_page
    start = page * items_per_page
    end = start + items_per_page
    
    keyboard = {'inline_keyboard': []}
    for uid, u in user_list[start:end]:
        name = u.get('first_name', '?')[:15]
        keyboard['inline_keyboard'].append([{'text': f'👤 {name}', 'callback_data': f'user_{uid}'}])
    
    # أزرار التنقل
    nav_buttons = []
    if page > 0:
        nav_buttons.append({'text': '◀️ السابق', 'callback_data': f'users_page_{page-1}'})
    if page < total_pages - 1:
        nav_buttons.append({'text': 'التالي ▶️', 'callback_data': f'users_page_{page+1}'})
    if nav_buttons:
        keyboard['inline_keyboard'].append(nav_buttons)
    
    keyboard['inline_keyboard'].append([{'text': '🔙 رجوع', 'callback_data': 'admin_panel'}])
    
    text = f"👥 **المستخدمين** ({len(user_list)})\n📄 الصفحة {page+1}/{total_pages}"
    edit_message(chat_id, message_id, text, keyboard)

def show_admin_bots(chat_id, message_id, page=0):
    bots = load_json(BOTS_DB)
    bot_list = list(bots.items())
    items_per_page = 8
    total_pages = (len(bot_list) + items_per_page - 1) // items_per_page
    start = page * items_per_page
    end = start + items_per_page
    
    keyboard = {'inline_keyboard': []}
    for bid, b in bot_list[start:end]:
        status = "🟢" if b.get('status') == 'running' else "🔴"
        name = b.get('name', '?')[:20]
        keyboard['inline_keyboard'].append([{'text': f'{status} {name}', 'callback_data': f'admin_bot_{bid}'}])
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append({'text': '◀️ السابق', 'callback_data': f'bots_page_{page-1}'})
    if page < total_pages - 1:
        nav_buttons.append({'text': 'التالي ▶️', 'callback_data': f'bots_page_{page+1}'})
    if nav_buttons:
        keyboard['inline_keyboard'].append(nav_buttons)
    
    keyboard['inline_keyboard'].append([{'text': '🔙 رجوع', 'callback_data': 'admin_panel'}])
    
    text = f"📁 **جميع البوتات** ({len(bot_list)})\n📄 الصفحة {page+1}/{total_pages}"
    edit_message(chat_id, message_id, text, keyboard)

# ================== دوال معالجة الملفات ==================
def save_bot_file(file_id, user_id, filename):
    # تحميل الملف من تليجرام
    url = f"https://api.telegram.org/bot{TOKEN}/getFile"
    response = requests.get(url, params={'file_id': file_id})
    if response.status_code != 200:
        return None
    
    file_path = response.json().get('result', {}).get('file_path')
    if not file_path:
        return None
    
    # تحميل محتوى الملف
    file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
    content = requests.get(file_url).content
    
    # إنشاء معرف فريد للبوت
    bot_id = f"bot_{user_id}_{int(time.time())}"
    save_path = os.path.join(BOTS_DIR, f"{bot_id}.py")
    
    with open(save_path, 'wb') as f:
        f.write(content)
    
    # حفظ المعلومات
    bots = load_json(BOTS_DB)
    bots[bot_id] = {
        'user_id': user_id,
        'name': filename.replace('.py', '')[:30],
        'filename': filename,
        'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'status': 'stopped',
        'pid': None
    }
    save_json(BOTS_DB, bots)
    
    # إضافة للقائمة عند المستخدم
    user = get_user(user_id)
    user['bots'] = user.get('bots', []) + [bot_id]
    save_user(user_id, user)
    
    # خصم النقاط إذا كان المستخدم ليس أدمن
    if not is_admin(user_id):
        points_per_hour = load_json(SETTINGS_DB).get('points_per_hour', 1)
        user['points'] = user.get('points', 0) - points_per_hour
        save_user(user_id, user)
    
    return bot_id

# ================== خادم الويب ==================
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return jsonify({
        'status': 'running',
        'bot': 'Hosting Bot',
        'version': '1.0.0'
    })

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
        
        # تسجيل المستخدم
        register_user(user_id, msg['from'].get('username'), msg['from'].get('first_name', ''))
        
        # معالمة النص
        if 'text' in msg:
            text = msg['text']
            
            if text == '/start':
                # التحقق من رابط الإحالة
                if len(text.split()) > 1:
                    ref_id = text.split()[1]
                    if ref_id.isdigit() and int(ref_id) != user_id:
                        referrer = get_user(int(ref_id))
                        if referrer:
                            referrer['points'] = referrer.get('points', 0) + 10
                            save_user(int(ref_id), referrer)
                            send_message(int(ref_id), f"🎉 حصلت على 10 نقاط من إحالة مستخدم جديد!")
                
                settings = load_json(SETTINGS_DB)
                bot_name = settings.get('bot_name', 'بوت الاستضافة')
                text = f"""🎉 **مرحباً {msg['from'].get('first_name', '')}**

🚀 **{bot_name}**
يمكنك رفع وتشغيل بوتاتك الخاصة بسهولة!

📌 **المميزات:**
• رفع ملفات .py وتشغيلها فوراً
• عرض سجلات البوت
• إيقاف وتشغيل البوتات
• نظام نقاط للإحالات

🔗 **رابط الإحالة الخاص بك:**
<code>https://t.me/{os.environ.get('BOT_USERNAME', 'bot')}?start={user_id}</code>"""
                
                send_message(chat_id, text, main_keyboard(user_id))
            
            elif text == '/id':
                send_message(chat_id, f"🆔 ايديك: <code>{user_id}</code>")
            
            elif text == '/admin' and is_admin(user_id):
                text = "⚙️ **لوحة التحكم**\n\nاختر من القائمة:"
                send_message(chat_id, text, admin_keyboard())
        
        # معالجة الملفات
        elif 'document' in msg:
            doc = msg['document']
            if doc['file_name'].endswith('.py'):
                # حفظ الملف
                bot_id = save_bot_file(doc['file_id'], user_id, doc['file_name'])
                if bot_id:
                    text = f"✅ **تم رفع البوت بنجاح!**\n\n📁 الاسم: {doc['file_name']}\n🆔 المعرف: <code>{bot_id}</code>\n\nيمكنك تشغيله من قائمة 'بوتاتي'"
                    send_message(chat_id, text, main_keyboard(user_id))
                else:
                    send_message(chat_id, "❌ **خطأ في رفع الملف**\nحاول مرة أخرى", main_keyboard(user_id))
            else:
                send_message(chat_id, "❌ **نوع ملف غير مدعوم**\nالرجاء إرسال ملف <code>.py</code> فقط", main_keyboard(user_id))
    
    # معالجة الأزرار
    elif 'callback_query' in update:
        callback = update['callback_query']
        callback_id = callback['id']
        user_id = callback['from']['id']
        message = callback['message']
        chat_id = message['chat']['id']
        message_id = message['message_id']
        data = callback['data']
        
        # تسجيل المستخدم
        register_user(user_id, callback['from'].get('username'), callback['from'].get('first_name', ''))
        
        # معالجة البيانات
        if data == 'back_main':
            send_message(chat_id, "🏠 **القائمة الرئيسية**", main_keyboard(user_id))
            try:
                requests.get(f"https://api.telegram.org/bot{TOKEN}/deleteMessage?chat_id={chat_id}&message_id={message_id}")
            except:
                pass
        
        elif data == 'balance':
            user = get_user(user_id)
            answer_callback(callback_id, f"💰 رصيدك: {user.get('points', 0)} نقطة", True)
        
        elif data == 'my_info':
            show_user_info(chat_id, message_id, user_id)
        
        elif data == 'referral':
            bot_info = requests.get(f"https://api.telegram.org/bot{TOKEN}/getMe").json()
            bot_username = bot_info.get('result', {}).get('username', 'bot')
            link = f"https://t.me/{bot_username}?start={user_id}"
            text = f"🔗 **رابط الإحالة الخاص بك**\n\n<code>{link}</code>\n\n💰 كل مستخدم يدخل عبر رابطك يمنحك 10 نقاط!"
            edit_message(chat_id, message_id, text, back_keyboard('back_main'))
        
        elif data == 'upload_bot':
            text = "📤 **رفع بوت جديد**\n\nأرسل ملف <code>.py</code> الخاص بالبوت:"
            edit_message(chat_id, message_id, text, back_keyboard('back_main'))
        
        elif data == 'my_bots':
            show_my_bots(chat_id, message_id, user_id)
        
        elif data.startswith('bot_'):
            bot_id = data.split('_')[1]
            show_bot_panel(chat_id, message_id, user_id, bot_id)
        
        elif data.startswith('startstop_'):
            bot_id = data.split('_')[1]
            bots = load_json(BOTS_DB)
            if bot_id in bots:
                if bots[bot_id].get('status') == 'running':
                    stop_bot(bot_id)
                    answer_callback(callback_id, "✅ تم إيقاف البوت")
                else:
                    success, msg = start_bot(bot_id)
                    answer_callback(callback_id, msg)
            show_bot_panel(chat_id, message_id, user_id, bot_id)
        
        elif data.startswith('logs_'):
            bot_id = data.split('_')[1]
            logs = get_bot_logs(bot_id)
            text = f"📋 **سجلات البوت**\n\n<code>{logs[:3500]}</code>"
            edit_message(chat_id, message_id, text, back_keyboard(f'bot_{bot_id}'))
        
        elif data.startswith('download_'):
            bot_id = data.split('_')[1]
            bot_path = os.path.join(BOTS_DIR, f"{bot_id}.py")
            if os.path.exists(bot_path):
                send_document(chat_id, bot_path, f"📄 {bot_id}.py")
                answer_callback(callback_id, "✅ جاري التحميل...")
            else:
                answer_callback(callback_id, "❌ الملف غير موجود", True)
            show_bot_panel(chat_id, message_id, user_id, bot_id)
        
        elif data.startswith('delete_'):
            bot_id = data.split('_')[1]
            delete_bot(bot_id)
            answer_callback(callback_id, "✅ تم حذف البوت")
            show_my_bots(chat_id, message_id, user_id)
        
        # ================== لوحة الأدمن ==================
        elif data == 'admin_panel' and is_admin(user_id):
            edit_message(chat_id, message_id, "⚙️ **لوحة التحكم**", admin_keyboard())
        
        elif data == 'admin_users' and is_admin(user_id):
            show_admin_users(chat_id, message_id)
        
        elif data.startswith('users_page_') and is_admin(user_id):
            page = int(data.split('_')[2])
            show_admin_users(chat_id, message_id, page)
        
        elif data.startswith('user_') and is_admin(user_id):
            target_id = int(data.split('_')[1])
            user = get_user(target_id)
            if user:
                text = f"""👤 **معلومات المستخدم**

🆔 الايدي: <code>{target_id}</code>
👤 الاسم: {user.get('first_name', '')}
🔗 المعرف: @{user.get('username', 'لا يوجد')}
💰 النقاط: {user.get('points', 0)}
📁 البوتات: {len(user.get('bots', []))}
🚫 الحظر: {'نعم ❌' if user.get('is_banned') else 'لا ✅'}"""
                
                keyboard = {
                    'inline_keyboard': [
                        [{'text': '💰 إضافة نقاط', 'callback_data': f'add_points_{target_id}'}],
                        [{'text': '🚫 حظر' if not user.get('is_banned') else '✅ فك الحظر', 'callback_data': f'ban_{target_id}'}],
                        [{'text': '🔙 رجوع', 'callback_data': 'admin_users'}]
                    ]
                }
                edit_message(chat_id, message_id, text, keyboard)
            else:
                answer_callback(callback_id, "❌ المستخدم غير موجود", True)
                show_admin_users(chat_id, message_id)
        
        elif data == 'admin_bots' and is_admin(user_id):
            show_admin_bots(chat_id, message_id)
        
        elif data.startswith('bots_page_') and is_admin(user_id):
            page = int(data.split('_')[2])
            show_admin_bots(chat_id, message_id, page)
        
        elif data.startswith('admin_bot_') and is_admin(user_id):
            bot_id = data.split('_')[2]
            show_bot_panel(chat_id, message_id, user_id, bot_id)
        
        elif data == 'admin_pending' and is_admin(user_id):
            text = "⏳ **الطلبات المعلقة**\n\nلا توجد طلبات حالياً"
            edit_message(chat_id, message_id, text, back_keyboard('admin_panel'))
        
        elif data == 'admin_broadcast' and is_admin(user_id):
            text = "📢 **إذاعة**\n\nأرسل الرسالة التي تريد إذاعتها لجميع المستخدمين:"
            edit_message(chat_id, message_id, text, back_keyboard('admin_panel'))
            # حفظ حالة الانتظار
            pending = load_json(PENDING_DB)
            pending[str(user_id)] = {'action': 'broadcast', 'step': 'waiting'}
            save_json(PENDING_DB, pending)
        
        elif data == 'admin_settings' and is_admin(user_id):
            settings = load_json(SETTINGS_DB)
            text = f"""⚙️ **الإعدادات**

🤖 اسم البوت: {settings.get('bot_name', '')}
💰 النقاط لكل ساعة: {settings.get('points_per_hour', 1)}
✅ الموافقة التلقائية: {'مفعّلة' if settings.get('auto_approve') else 'معطّلة'}"""
            
            keyboard = {
                'inline_keyboard': [
                    [{'text': '✏️ تغيير الاسم', 'callback_data': 'set_bot_name'}],
                    [{'text': '💰 تغيير سعر الساعة', 'callback_data': 'set_points_per_hour'}],
                    [{'text': '✅ الموافقة التلقائية', 'callback_data': 'toggle_auto_approve'}],
                    [{'text': '🔙 رجوع', 'callback_data': 'admin_panel'}]
                ]
            }
            edit_message(chat_id, message_id, text, keyboard)
        
        elif data.startswith('add_points_') and is_admin(user_id):
            target_id = int(data.split('_')[2])
            pending = load_json(PENDING_DB)
            pending[str(user_id)] = {'action': 'add_points', 'target': target_id, 'step': 'waiting'}
            save_json(PENDING_DB, pending)
            text = f"💰 أرسل عدد النقاط للمستخدم <code>{target_id}</code>:"
            edit_message(chat_id, message_id, text, back_keyboard('admin_users'))
        
        elif data.startswith('ban_') and is_admin(user_id):
            target_id = int(data.split('_')[1])
            user = get_user(target_id)
            if user:
                user['is_banned'] = not user.get('is_banned', False)
                save_user(target_id, user)
                answer_callback(callback_id, f"✅ {'تم حظر' if user['is_banned'] else 'تم فك الحظر'} المستخدم")
            show_admin_users(chat_id, message_id, 0)
    
    return 'OK', 200

# ================== التوكنات المؤقتة ==================
pending_messages = {}
waiting_for_reply = {}

def process_pending_messages():
    while True:
        time.sleep(1)
        # المعالجة تتم في الويب هوك مباشرة

# ================== مراقبة البوتات ==================
def monitor_bots():
    while True:
        time.sleep(30)
        bots = load_json(BOTS_DB)
        settings = load_json(SETTINGS_DB)
        points_per_hour = settings.get('points_per_hour', 1)
        
        for bid, b in bots.items():
            # التحقق من أن البوت لا يزال يعمل
            if b.get('pid'):
                try:
                    os.kill(b['pid'], 0)
                except OSError:
                    b['status'] = 'stopped'
                    b['pid'] = None
                    save_json(BOTS_DB, bots)
            
            # خصم النقاط كل ساعة للمستخدمين العاديين
            if b.get('status') == 'running' and not is_admin(b.get('user_id')):
                user = get_user(b.get('user_id'))
                if user:
                    # التحقق من وجود نقاط كافية
                    if user.get('points', 0) < points_per_hour:
                        stop_bot(bid)
                        send_message(b.get('user_id'), f"⚠️ **تم إيقاف البوت {b.get('name')}**\n\nلا يوجد نقاط كافية للاستمرار")
                    else:
                        # خصم نقطة كل ساعة (يتم في دالة منفصلة)
                        pass

# تشغيل المراقبة في خلفية
threading.Thread(target=monitor_bots, daemon=True).start()

# ================== تشغيل الخادم ==================
if __name__ == '__main__':
    # تعيين الويب هوك
    if WEBHOOK_URL:
        webhook_url = f"https://{WEBHOOK_URL}/webhook/{TOKEN}"
    else:
        # للاستخدام المحلي أو Render
        port = int(os.environ.get('PORT', 8080))
        webhook_url = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'localhost')}/webhook/{TOKEN}"
    
    # تعيين الويب هوك
    try:
        requests.get(f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={webhook_url}")
        print(f"✅ تم تعيين Webhook: {webhook_url}")
    except Exception as e:
        print(f"⚠️ خطأ في تعيين Webhook: {e}")
    
    print("=" * 50)
    print("🚀 بوت الاستضافة يعمل الآن")
    print("=" * 50)
    print(f"✅ التوكن: {TOKEN[:10]}...")
    print(f"👑 الأدمن: {ADMIN_ID}")
    print(f"🌐 المنفذ: {os.environ.get('PORT', 8080)}")
    print("=" * 50)
    
    # تشغيل الخادم
    flask_app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))