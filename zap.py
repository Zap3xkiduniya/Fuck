import os
import json
import requests
import aiohttp
import asyncio
from datetime import datetime, timedelta, timezone
from dateutil.relativedelta import relativedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
import sqlite3
import random
import string
import time
import warnings
import hashlib
import base64
from collections import defaultdict
from typing import Dict, List, Optional, Tuple
import re
warnings.filterwarnings("ignore")

# ==================== TIME ZONE ====================
IST = timezone(timedelta(hours=5, minutes=30))

def get_ist_now():
    return datetime.now(IST)

def format_ist_time(dt=None):
    if dt is None:
        dt = get_ist_now()
    return dt.strftime("%Y-%m-%d %I:%M:%S %p IST")

def format_time(dt=None):
    if dt is None:
        dt = get_ist_now()
    return dt.strftime("%I:%M:%S %p IST")

def format_numbers(num):
    try:
        return f"{int(num):,}"
    except:
        return str(num)

# ==================== CONFIGURATION ====================
TELEGRAM_BOT_TOKEN = "8856643374:AAEuVYXYsWOqUUqyLk0fkKkryg3O5vlugC0"
LIKE_API_URL = "https://like_api_url.com/like?uid={uid}&server_name={region}"

LIKE_API_TIMEOUT = 60
AUTO_LIKE_TIME = "04:00"
BOT_VERSION = "8.0.0"
BOT_NAME = "ᴀᴜᴛᴏ ʟɪᴋᴇ Ｒ-ʙᴏᴛs"

OWNER_ID = 6325764594
SUPER_ADMIN_IDS = [6325764594]

ALLOWED_GROUP_ID = -1005389602452   # এখানে তোমার Group ID দাও
DEV_USERNAME = "@nur_0_0_19"
SUPPORT_CHANNEL = "https://t.me/autolikegc"
UPDATE_CHANNEL = "https://t.me/+q7BgGaFjWTpjNzll"

# ==================== REGIONS ====================
REGIONS = {
    'ind': {'name': 'India', 'flag': '🇮🇳', 'code': 'in', 'emoji': '🦁', 'color': '#FF9933'},
    'bd': {'name': 'Bangladesh', 'flag': '🇧🇩', 'code': 'bd', 'emoji': '🐅', 'color': '#006747'},
    'sg': {'name': 'Singapore', 'flag': '🇸🇬', 'code': 'sg', 'emoji': '🦁', 'color': '#ED2939'},
    'id': {'name': 'Indonesia', 'flag': '🇮🇩', 'code': 'id', 'emoji': '🦅', 'color': '#FF0000'},
    'th': {'name': 'Thailand', 'flag': '🇹🇭', 'code': 'th', 'emoji': '🐘', 'color': '#2D2A4A'},
    'vn': {'name': 'Vietnam', 'flag': '🇻🇳', 'code': 'vn', 'emoji': '🐉', 'color': '#DA251D'},
    'br': {'name': 'Brazil', 'flag': '🇧🇷', 'code': 'br', 'emoji': '🦜', 'color': '#009C3B'},
    'ru': {'name': 'Russia', 'flag': '🇷🇺', 'code': 'ru', 'emoji': '🐻', 'color': '#0039A6'},
    'pk': {'name': 'Pakistan', 'flag': '🇵🇰', 'code': 'pk', 'emoji': '🐪', 'color': '#01411C'},
    'np': {'name': 'Nepal', 'flag': '🇳🇵', 'code': 'np', 'emoji': '⛰️', 'color': '#003893'},
    'lk': {'name': 'Sri Lanka', 'flag': '🇱🇰', 'code': 'lk', 'emoji': '🦁', 'color': '#FFBE29'},
    'my': {'name': 'Malaysia', 'flag': '🇲🇾', 'code': 'my', 'emoji': '🐯', 'color': '#CC0001'},
    'ph': {'name': 'Philippines', 'flag': '🇵🇭', 'code': 'ph', 'emoji': '🦅', 'color': '#0032A0'},
    'vn': {'name': 'Vietnam', 'flag': '🇻🇳', 'code': 'vn', 'emoji': '🐉', 'color': '#DA251D'},
    'mm': {'name': 'Myanmar', 'flag': '🇲🇲', 'code': 'mm', 'emoji': '🦁', 'color': '#FECB00'},
}

# ==================== PREMIUM EMOJIS ====================
E = {
    # Status
    'online': '🟢', 'offline': '🔴', 'warning': '⚠️', 'error': '❌', 'success': '✅',
    'empty': '📭',
    'info': 'ℹ️', 'question': '❓', 'tip': '💡', 'idea': '💡', 'alert': '🚨',
    
    # Actions
    'rocket': '🚀', 'fire': '🔥', 'zap': '⚡', 'magic': '🪄', 'sparkles': '✨',
    'crown': '👑', 'star': '⭐', 'diamond': '💎', 'gem': '💎', 'trophy': '🏆',
    'medal': '🎖️', 'ribbon': '🎗️', 'badge': '🏅', 'award': '🏆',
    
    # Navigation
    'arrow_up': '⬆️', 'arrow_down': '⬇️', 'arrow_left': '⬅️', 'arrow_right': '➡️',
    'back': '🔙', 'forward': '🔜', 'menu': '📋', 'list': '📃',
    
    # Objects
    'key': '🔑', 'lock': '🔒', 'unlock': '🔓', 'keyboard': '⌨️', 'mouse': '🖱️',
    'computer': '💻', 'phone': '📱', 'tablet': '📲', 'watch': '⌚', 'camera': '📷',
    'video': '🎥', 'music': '🎵', 'mic': '🎤', 'headphone': '🎧', 'game': '🎮',
    
    # Time
    'clock': '⏰', 'alarm': '⏰', 'calendar': '📅', 'hourglass': '⌛', 'timer': '⏲️',
    'stopwatch': '⏱️', 'date': '📆',
    
    # Communication
    'broadcast': '📢', 'megaphone': '📣', 'bell': '🔔', 'mute': '🔕', 'speaker': '🔊',
    'chat': '💬', 'message': '💌', 'mail': '📧', 'inbox': '📥', 'outbox': '📤',
    
    # Users
    'user': '👤', 'users': '👥', 'group': '👥', 'admin': '👑', 'mod': '🛡️',
    'owner': '🤴', 'dev': '👨‍💻', 'bot': '🤖', 'robot': '🤖',
    
    # Statistics
    'stats': '📊', 'chart': '📈', 'graph': '📉', 'analytics': '📐', 'data': '🗃️',
    'database': '🗄️', 'folder': '📁', 'file': '📄', 'document': '📑',
    
    # Actions
    'plus': '➕', 'minus': '➖', 'multiply': '✖️', 'divide': '➗', 'equal': '➰',
    'check': '✅', 'cross': '❌', 'tick': '✔️', 'wrong': '✖️',
    
    # Hearts
    'heart': '❤️', 'broken_heart': '💔', 'sparkling_heart': '💖', 'growing_heart': '💗',
    'beating_heart': '💓', 'two_hearts': '💕', 'revolving_hearts': '💞',
    
    # Weather
    'sun': '☀️', 'moon': '🌙', 'cloud': '☁️', 'rain': '🌧️', 'snow': '❄️',
    'thunder': '⛈️', 'tornado': '🌪️', 'fog': '🌫️',
    
    # Nature
    'tree': '🌲', 'flower': '🌸', 'leaf': '🍃', 'mountain': '⛰️', 'ocean': '🌊',
    'globe': '🌍', 'earth': '🌎', 'world': '🌏',
    
    # Tools
'wrench': '🔧', 'hammer': '🔨', 'screwdriver': '🪛', 'gear': '⚙️', 'settings': '⚙️', 'broom': '🧹',
'scissors': '✂️', 'clipboard': '📋', 'pen': '✒️', 'pencil': '✏️',
    
    # Games
    'dice': '🎲', 'cards': '🃏', 'chess': '♟️', 'target': '🎯', 'joystick': '🕹️',
    
    # Misc
    'gift': '🎁', 'party': '🎉', 'balloon': '🎈', 'confetti': '🎊', 'cake': '🎂',
    'book': '📚', 'magazine': '📰', 'newspaper': '📰', 'label': '🏷️', 'tag': '🏷️',
    'pin': '📌', 'pushpin': '📍', 'link': '🔗', 'chain': '⛓️', 'tool': '🔧',
    'shield': '🛡️', 'armor': '🛡️', 'sword': '⚔️', 'flag': '🏁', 'checkered': '🏁',
    'lab': '🧪', 'microscope': '🔬', 'telescope': '🔭', 'satellite': '🛰️',
    'fuel': '⛽', 'station': '🚉', 'airplane': '✈️', 'helicopter': '🚁', 'rocket_ship': '🚀',
    'car': '🚗', 'truck': '🚚', 'bus': '🚌', 'train': '🚂', 'ship': '🚢', 'boat': '⛵',
    'house': '🏠', 'building': '🏢', 'office': '🏢', 'school': '🏫', 'hospital': '🏥',
    'bank': '🏦', 'hotel': '🏨', 'store': '🏪', 'factory': '🏭',

    'search': '🔍',
    'coin': '🪙',
}

# ==================== DATABASE ====================
class Database:
    def __init__(self):
        self.db_path = 'premium_bot.db'
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.migrate_database()
        print(f"✅ Database connected: {self.db_path}")
    
    def migrate_database(self):
        # Users table
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            join_date TIMESTAMP,
            last_active TIMESTAMP,
            total_commands INTEGER DEFAULT 0,
            is_banned BOOLEAN DEFAULT 0,
            is_premium BOOLEAN DEFAULT 0,
            premium_expiry DATE,
            coins INTEGER DEFAULT 0,
            referral_code TEXT,
            referred_by INTEGER,
            total_referrals INTEGER DEFAULT 0,
            language TEXT DEFAULT 'en'
        )''')
        
        # UIDs table
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS uids (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uid TEXT UNIQUE,
            region TEXT,
            added_by INTEGER,
            added_date TIMESTAMP,
            last_like TIMESTAMP,
            total_likes INTEGER DEFAULT 0,
            remaining_days INTEGER DEFAULT 0,
            auto_expiry DATE,
            status TEXT DEFAULT 'active',
            notes TEXT
        )''')
        
        # Admins table
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            username TEXT,
            added_by INTEGER,
            added_date TIMESTAMP,
            level TEXT DEFAULT 'admin'
        )''')
        self.cursor.execute('''INSERT OR IGNORE INTO admins (user_id, username, added_by, added_date, level) 
            VALUES (?, ?, ?, ?, ?)''', (OWNER_ID, "Owner", OWNER_ID, format_ist_time(), 'super_admin'))
        
        # Allowed groups table
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS allowed_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER UNIQUE,
            chat_title TEXT,
            chat_username TEXT,
            added_by INTEGER,
            added_date TIMESTAMP,
            auto_post BOOLEAN DEFAULT 1
        )''')
        
        # Settings table
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY, 
            value TEXT
        )''')
        
        # Chats table
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER UNIQUE,
            chat_title TEXT,
            chat_type TEXT,
            added_date TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )''')
        
        # Daily stats table
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS daily_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE UNIQUE,
            total_likes INTEGER DEFAULT 0,
            success_count INTEGER DEFAULT 0,
            failed_count INTEGER DEFAULT 0,
            limit_count INTEGER DEFAULT 0,
            active_uids INTEGER DEFAULT 0
        )''')
        
        # Commands stats table
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS command_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            command TEXT,
            user_id INTEGER,
            timestamp TIMESTAMP
        )''')
        
        # Broadcast history
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS broadcast_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message TEXT,
            sent_by INTEGER,
            sent_date TIMESTAMP,
            total_sent INTEGER,
            total_failed INTEGER
        )''')
        
        # Auto like history
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS auto_like_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_date DATE,
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            total_processed INTEGER,
            successful INTEGER,
            failed INTEGER,
            limit_reached INTEGER,
            total_likes INTEGER
        )''')
        
        self.conn.commit()
        print("✅ Database schema complete")
    
    # ============ USER METHODS ============
    def register_user(self, user_id, username, first_name, last_name=""):
        try:
            self.cursor.execute('''INSERT OR IGNORE INTO users 
                (user_id, username, first_name, last_name, join_date, last_active, referral_code)
                VALUES (?, ?, ?, ?, ?, ?, ?)''', 
                (user_id, username, first_name, last_name, format_ist_time(), format_ist_time(), 
                 self.generate_referral_code(user_id)))
            self.conn.commit()
            return True
        except:
            return False
    
    def generate_referral_code(self, user_id):
        return hashlib.md5(f"{user_id}{time.time()}".encode()).hexdigest()[:8]
    
    def update_user_activity(self, user_id):
        try:
            self.cursor.execute("UPDATE users SET last_active = ?, total_commands = total_commands + 1 WHERE user_id = ?", 
                              (format_ist_time(), user_id))
            self.conn.commit()
        except:
            pass
    
    def get_user(self, user_id):
        try:
            self.cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            return self.cursor.fetchone()
        except:
            return None
    
    def add_coins(self, user_id, amount):
        try:
            self.cursor.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?", (amount, user_id))
            self.conn.commit()
            return True
        except:
            return False
    
    def get_top_users(self, limit=10):
        try:
            self.cursor.execute("SELECT user_id, username, total_commands, coins FROM users ORDER BY total_commands DESC LIMIT ?", (limit,))
            return self.cursor.fetchall()
        except:
            return []
    
    # ============ UID METHODS ============
    def get_uids(self):
        try:
            self.cursor.execute("SELECT uid, region, remaining_days FROM uids WHERE status='active' AND remaining_days > 0")
            return [{"uid": row[0], "region": row[1], "remaining_days": row[2]} for row in self.cursor.fetchall()]
        except:
            return []
    
    def add_uid(self, uid, region, added_by, days, notes=""):
        try:
            expiry_date = (get_ist_now() + timedelta(days=days)).strftime("%Y-%m-%d")
            self.cursor.execute('''INSERT OR REPLACE INTO uids 
                (uid, region, added_by, added_date, remaining_days, auto_expiry, status, notes)
                VALUES (?, ?, ?, ?, ?, ?, 'active', ?)''',
                (uid, region, added_by, format_ist_time(), days, expiry_date, notes))
            self.conn.commit()
            return True
        except:
            return False
    
    def remove_uid(self, uid):
        try:
            self.cursor.execute("DELETE FROM uids WHERE uid = ?", (uid,))
            self.conn.commit()
            return True
        except:
            return False
    
    def decrement_days(self, uid):
        try:
            self.cursor.execute("UPDATE uids SET remaining_days = remaining_days - 1 WHERE uid = ? AND remaining_days > 0", (uid,))
            self.conn.commit()
            return True
        except:
            return False
    
    def get_uid_stats(self):
        try:
            self.cursor.execute("SELECT COUNT(*) as total, SUM(remaining_days) as total_days FROM uids WHERE status='active'")
            return self.cursor.fetchone()
        except:
            return {"total": 0, "total_days": 0}
    
    # ============ ADMIN METHODS ============
    def get_admins(self):
        try:
            self.cursor.execute("SELECT user_id, username, level FROM admins ORDER BY level DESC")
            return self.cursor.fetchall()
        except:
            return []
    
    def is_admin(self, user_id):
        try:
            self.cursor.execute("SELECT user_id FROM admins WHERE user_id=?", (user_id,))
            return self.cursor.fetchone() is not None
        except:
            return user_id == OWNER_ID
    
    def is_super_admin(self, user_id):
        try:
            self.cursor.execute("SELECT user_id FROM admins WHERE user_id=? AND level='super_admin'", (user_id,))
            return self.cursor.fetchone() is not None
        except:
            return user_id == OWNER_ID
    
    def add_admin(self, user_id, username, added_by, level='admin'):
        try:
            self.cursor.execute('''INSERT OR IGNORE INTO admins (user_id, username, added_by, added_date, level) 
                VALUES (?, ?, ?, ?, ?)''', (user_id, username, added_by, format_ist_time(), level))
            self.conn.commit()
            return True
        except:
            return False
    
    def remove_admin(self, user_id):
        try:
            self.cursor.execute("DELETE FROM admins WHERE user_id=?", (user_id,))
            self.conn.commit()
            return True
        except:
            return False
    
    # ============ GROUP METHODS ============
    def add_allowed_group(self, chat_id, chat_title, chat_username, added_by):
        try:
            self.cursor.execute('''INSERT OR IGNORE INTO allowed_groups (chat_id, chat_title, chat_username, added_by, added_date) 
                VALUES (?, ?, ?, ?, ?)''', (chat_id, chat_title, chat_username, added_by, format_ist_time()))
            self.conn.commit()
            return True
        except:
            return False
    
    def remove_allowed_group(self, chat_id):
        try:
            self.cursor.execute("DELETE FROM allowed_groups WHERE chat_id = ?", (chat_id,))
            self.conn.commit()
            return True
        except:
            return False
    
    def get_allowed_groups(self):
        try:
            self.cursor.execute("SELECT chat_id, chat_title, chat_username FROM allowed_groups")
            return self.cursor.fetchall()
        except:
            return []
    
    def get_allowed_group_ids(self):
        try:
            self.cursor.execute("SELECT chat_id FROM allowed_groups")
            return [row[0] for row in self.cursor.fetchall()]
        except:
            return []
    
    # ============ CHAT METHODS ============
    def add_chat(self, chat_id, chat_title, chat_type):
        try:
            self.cursor.execute('''INSERT OR IGNORE INTO chats (chat_id, chat_title, chat_type, added_date) 
                VALUES (?, ?, ?, ?)''', (chat_id, chat_title, chat_type, format_ist_time()))
            self.conn.commit()
        except:
            pass
    
    def get_chats(self):
        try:
            self.cursor.execute("SELECT chat_id FROM chats WHERE is_active=1")
            return [row[0] for row in self.cursor.fetchall()]
        except:
            return []
    
    def get_chat_count(self):
        try:
            self.cursor.execute("SELECT COUNT(*) FROM chats WHERE is_active=1")
            return self.cursor.fetchone()[0]
        except:
            return 0
    
    # ============ SETTINGS METHODS ============
    def get_setting(self, key, default=None):
        try:
            self.cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = self.cursor.fetchone()
            return row[0] if row else default
        except:
            return default
    
    def set_setting(self, key, value):
        try:
            self.cursor.execute('''INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)''', (key, value))
            self.conn.commit()
        except:
            pass
    
    # ============ STATS METHODS ============
    def update_daily_stats(self, date, likes=0, success=0, failed=0, limit=0):
        try:
            self.cursor.execute('''INSERT OR REPLACE INTO daily_stats 
                (date, total_likes, success_count, failed_count, limit_count) 
                VALUES (?, total_likes + ?, success_count + ?, failed_count + ?, limit_count + ?)''',
                (date, likes, success, failed, limit))
            self.conn.commit()
        except:
            pass
    
    def get_today_stats(self):
        try:
            today = get_ist_now().strftime("%Y-%m-%d")
            self.cursor.execute("SELECT * FROM daily_stats WHERE date = ?", (today,))
            row = self.cursor.fetchone()
            if row:
                return dict(row)
            return {"total_likes": 0, "success_count": 0, "failed_count": 0, "limit_count": 0}
        except:
            return {"total_likes": 0, "success_count": 0, "failed_count": 0, "limit_count": 0}
    
    # ============ BROADCAST METHODS ============
    def add_broadcast_history(self, message, sent_by, total_sent, total_failed):
        try:
            self.cursor.execute('''INSERT INTO broadcast_history (message, sent_by, sent_date, total_sent, total_failed) 
                VALUES (?, ?, ?, ?, ?)''', (message[:500], sent_by, format_ist_time(), total_sent, total_failed))
            self.conn.commit()
        except:
            pass
    
    # ============ AUTO LIKE HISTORY ============
    def add_auto_like_history(self, run_date, total_processed, successful, failed, limit_reached, total_likes):
        try:
            self.cursor.execute('''INSERT INTO auto_like_history 
                (run_date, start_time, end_time, total_processed, successful, failed, limit_reached, total_likes) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                (run_date, format_ist_time(), format_ist_time(), total_processed, successful, failed, limit_reached, total_likes))
            self.conn.commit()
        except:
            pass

db = Database()

# ==================== LOAD DATA ====================
def load_data():
    uids = db.get_uids()
    auto_time = db.get_setting('auto_time', AUTO_LIKE_TIME)
    maintenance = db.get_setting('maintenance_mode', 'off')
    allowed_groups = db.get_allowed_groups()
    chats = db.get_chats()
    return {
        'uids': uids,
        'auto_time': auto_time,
        'maintenance': maintenance,
        'allowed_groups': allowed_groups,
        'chats': chats,
        'stats': db.get_today_stats()
    }

data = load_data()
start_time = time.time()

# ==================== HELPERS ====================
def can_use_bot(update):
    user_id = update.effective_user.id
    chat = update.effective_chat

    # Owner/Admin সব জায়গায় পারবে
    if user_id == OWNER_ID or user_id in SUPER_ADMIN_IDS:
        return True

    # সাধারণ User শুধু এই Group-এ পারবে
    if chat.id == ALLOWED_GROUP_ID:
        return True

    return False
    
def is_admin(user_id):
    return db.is_admin(user_id) or user_id == OWNER_ID

def is_super_admin(user_id):
    return db.is_super_admin(user_id) or user_id == OWNER_ID

def get_region_info(region_code):
    return REGIONS.get(region_code.lower(), {'name': 'Unknown', 'flag': '🌍', 'emoji': '🌍', 'color': '#FFFFFF'})

def format_number(num):
    try:
        if num >= 1000000:
            return f"{num/1000000:.1f}M"
        elif num >= 1000:
            return f"{num/1000:.1f}K"
        return str(num)
    except:
        return str(num)

# ==================== LIKE FUNCTION ====================
async def send_like(uid, region):
    url = LIKE_API_URL.format(uid=uid, region=region.lower())
    
    try:
        timeout = aiohttp.ClientTimeout(total=LIKE_API_TIMEOUT)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    result = await response.json()
                    
                    likes_given_raw = result.get('LikesGivenByAPI', 0)
                    if isinstance(likes_given_raw, str):
                        likes_given = int(likes_given_raw) if likes_given_raw.isdigit() else 0
                    else:
                        likes_given = int(likes_given_raw) if likes_given_raw else 0
                    
                    status_raw = result.get('status', 0)
                    if isinstance(status_raw, str):
                        status = int(status_raw) if status_raw.isdigit() else 0
                    else:
                        status = int(status_raw) if status_raw else 0
                    
                    if likes_given > 0:
                        result['status'] = 1
                        db.update_daily_stats(get_ist_now().strftime("%Y-%m-%d"), likes=likes_given, success=1)
                    elif status == 2:
                        result['status'] = 2
                        db.update_daily_stats(get_ist_now().strftime("%Y-%m-%d"), limit=1)
                    else:
                        result['status'] = 0
                        db.update_daily_stats(get_ist_now().strftime("%Y-%m-%d"), failed=1)
                    
                    return result
                else:
                    db.update_daily_stats(get_ist_now().strftime("%Y-%m-%d"), failed=1)
                    return {"status": 0, "Note": f"HTTP {response.status}"}
    except Exception as e:
        db.update_daily_stats(get_ist_now().strftime("%Y-%m-%d"), failed=1)
        return {"status": 0, "Note": str(e)}

# ==================== FORMAT FUNCTIONS ====================
def format_result(result, uid, region, result_type="manual", remaining_days=None):
    region_info = get_region_info(region)

    try:
        status = int(result.get("status", 0))
    except:
        status = 0

    try:
        likes = int(result.get("LikesGivenByAPI", 0))
    except:
        likes = 0

    player = result.get("PlayerNickname", "Unknown")
    before = format_numbers(result.get("LikesbeforeCommand", 0))
    after = format_numbers(result.get("LikesafterCommand", 0))
    error = result.get("Note", "Unknown Error")

    mode = "🤖 Auto Like" if result_type == "auto" else "👤 Manual Like"

    if status == 1 or likes > 0:
        msg = f"""```
╭═━──────༺𓆩✧𓆪༻──────━═╮
│  🚀 LIKE SENT SUCCESSFULLY
├─────────────────────────┤
│
│  🎮 PLAYER PROFILE
│  ┌ 👤 Name   : {player}
│  ├ 🆔 UID    : {uid}
│  ├ 🌍 Region : {region_info['name']}
│  └ 📡 Status : 🟢 SUCCESS
│
├─────────────────────────┤
│
│  📊 LIKE METRICS
│  ┌ 💖 Sent Now : +{format_numbers(likes)}
│  ├ 📉 Before   : {before}
│  ├ 📈 After    : {after}
│  └ 🏆 Total    : {after}
"""

        if remaining_days is not None:
            msg += f"│\n│  📅 Days Left : {remaining_days}\n"

        msg += f"""│
├─────────────────────────┤
│
│  ⚙️ SYSTEM INFO
│  ┌ 🔧 Mode   : {mode}
│  ├ ⚡ Speed  : N/A
│  └ 🕒 Time   : {format_time()}
│
╰═━──────༺𓆩✧𓆪༻──────━═╯
```"""
        return msg

    elif status == 2:
        return f"""```
╭═━──────༺𓆩✧𓆪༻──────━═╮
│  ⚠️ LIMIT REACHED TODAY
├─────────────────────────┤
│
│  🆔 UID    : {uid}
│  🌍 Region : {region_info['name']}
│  📡 Status : 🟡 LIMIT
│
├─────────────────────────┤
│
│  🕒 Time : {format_time()}
│
╰═━──────༺𓆩✧𓆪༻──────━═╯
```"""

    else:
        return f"""```
╭═━──────༺𓆩✧𓆪༻──────━═╮
│  ❌ LIKE SEND FAILED
├─────────────────────────┤
│
│  🎮 PLAYER PROFILE
│  ┌ 👤 Name   : {player}
│  ├ 🆔 UID    : {uid}
│  ├ 🌍 Region : {region_info['name']}
│  └ 📡 Status : 🔴 FAILED
│
├─────────────────────────┤
│
│  ⚠️ Error : {error}
│
├─────────────────────────┤
│
│  ⚙️ SYSTEM INFO
│  ┌ 🔧 Mode   : {mode}
│  └ 🕒 Time   : {format_time()}
│
╰═━──────༺𓆩✧𓆪༻──────━═╯
```"""
def format_main_menu(user_id, is_admin_user=False):
    stats = db.get_today_stats()
    uid_stats = db.get_uid_stats()

    keyboard = [
        [InlineKeyboardButton(f"{E['rocket']} RUN NOW", callback_data="run_now"),
         InlineKeyboardButton(f"{E['stats']} STATS", callback_data="show_stats")],
        [InlineKeyboardButton(f"{E['plus']} ADD UID", callback_data="add_uid"),
         InlineKeyboardButton(f"{E['list']} LIST UIDS", callback_data="list_uids")],
        [InlineKeyboardButton(f"{E['calendar']} AUTO LIKE", callback_data="auto_like_settings"),
         InlineKeyboardButton(f"{E['settings']} SETTINGS", callback_data="settings_menu")],
    ]

    if is_admin_user:
        keyboard.append([
            InlineKeyboardButton(
                f"{E['crown']} ADMIN PANEL",
                callback_data="admin_panel"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            f"{E['owner']} OWNER",
            url=f"tg://user?id={OWNER_ID}"
        ),
        InlineKeyboardButton(
            f"{E['dev']} DEV",
            url=f"tg://user?id={SUPER_ADMIN_IDS[0] if SUPER_ADMIN_IDS else OWNER_ID}"
        )
    ])

    keyboard.append([
        InlineKeyboardButton(f"{E['globe']} SUPPORT", url=SUPPORT_CHANNEL),
        InlineKeyboardButton(f"{E['bell']} UPDATES", url=UPDATE_CHANNEL)
    ])

    menu_text = (
        f"{E['sparkles']} *{BOT_NAME}* {E['sparkles']}\n"
        f"*Version:* `{BOT_VERSION}`\n\n"
        f"{E['stats']} *TODAY'S STATS*\n"
        f"└ {E['heart']} Likes: `{format_number(stats.get('total_likes', 0))}`\n"
        f"└ {E['success']} Success: `{stats.get('success_count', 0)}`\n"
        f"└ {E['error']} Failed: `{stats.get('failed_count', 0)}`\n"
        f"└ {E['warning']} Limit: `{stats.get('limit_count', 0)}`\n\n"
        f"{E['database']} *DATABASE*\n"
        f"└ {E['key']} UIDs: `{uid_stats['total'] if uid_stats else 0}`\n"
        f"└ {E['calendar']} Total Days: `{uid_stats['total_days'] if uid_stats else 0}`\n"
        f"└ {E['clock']} Auto Time: `{data['auto_time']}` IST\n\n"
        f"{E['clock']} *Server Time:* `{format_time()}`"
    )

    return menu_text, InlineKeyboardMarkup(keyboard)

# ==================== COMMANDS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not can_use_bot(update):
        return await update.message.reply_text(
            "❌ This Bot can only be used in specific Groups"
        )

    user = update.effective_user
    chat = update.effective_chat
    
    db.register_user(user.id, user.username, user.first_name, user.last_name or "")
    db.add_chat(chat.id, chat.title or "Private", chat.type)
    db.update_user_activity(user.id)
    
    menu_text, reply_markup = format_main_menu(user.id, is_admin(user.id))
    
    await update.message.reply_text(menu_text, reply_markup=reply_markup, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not can_use_bot(update):
        return await update.message.reply_text(
            "❌ This Bot can only be used in specific Groups"
        )

    user_id = update.effective_user.id
    db.update_user_activity(user_id)
    
    text = f"{E['book']} *{BOT_NAME} - HELP MENU*\n\n"
    text += f"{E['star']} *BASIC COMMANDS*\n"
    text += f"├ /start - {E['rocket']} Start the bot\n"
    text += f"├ /help - {E['info']} Show this menu\n"
    text += f"├ /status - {E['stats']} Bot status\n"
    text += f"├ /stats - {E['chart']} Detailed stats\n"
    text += f"├ /regions - {E['globe']} All regions\n"
    text += f"└ /profile - {E['user']} Your profile\n\n"
    
    if is_admin(user_id):
        text += f"{E['crown']} *ADMIN COMMANDS*\n"
        text += f"├ /autolike `<uid> <region> <days>` - {E['calendar']} Add to auto like\n"
        text += f"├ /runnow - {E['rocket']} Manual like check\n"
        text += f"├ /list - {E['folder']} List all UIDs\n"
        text += f"├ /remove `<uid>` - {E['minus']} Remove UID\n"
        text += f"├ /test `<uid> <region>` - {E['lab']} Test like\n"
        text += f"├ /region `<region>` - {E['flag']} Show region UIDs\n"
        text += f"├ /search `<uid>` - {E['search']} Search UID\n"
        text += f"└ /export - {E['file']} Export data\n\n"
    
    if is_super_admin(user_id):
        text += f"{E['diamond']} *SUPER ADMIN COMMANDS*\n"
        text += f"├ /settime `<HH:MM>` - {E['alarm']} Change auto time\n"
        text += f"├ /addgroup - {E['plus']} Allow this group\n"
        text += f"├ /removegroup - {E['minus']} Remove this group\n"
        text += f"├ /listgroups - {E['folder']} List allowed groups\n"
        text += f"├ /broadcast `<msg>` - {E['broadcast']} Broadcast message\n"
        text += f"├ /broadcastpin `<msg>` - {E['pin']} Broadcast + pin\n"
        text += f"├ /maintenance `<on/off>` - {E['wrench']} Maintenance mode\n"
        text += f"├ /addadmin `<id> [super]` - {E['plus']} Add admin\n"
        text += f"├ /radmin `<id>` - {E['minus']} Remove admin\n"
        text += f"├ /admins - {E['users']} List admins\n"
        text += f"├ /system - {E['computer']} System info\n"
        text += f"├ /clearcache - {E['broom']} Clear cache\n"
        text += f"├ /backup - {E['database']} Backup database\n"
        text += f"├ /restore - {E['database']} Restore database\n"
        text += f"└ /resetstats - {E['chart']} Reset daily stats\n\n"
    
    text += f"{E['globe']} *REGIONS:* " + " ".join([f"{REGIONS[r]['flag']}`{r}`" for r in list(REGIONS.keys())[:8]]) + "\n\n"
    text += f"{E['dev']} *Dev:* {DEV_USERNAME} | {E['owner']} *Owner:* {OWNER_ID}"
    
    await context.bot.send_message(
    chat_id=update.effective_chat.id,
    text=text,
    parse_mode="Markdown"
)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not can_use_bot(update):
        return await update.message.reply_text(
            "❌ This Bot can only be used in specific Groups"
        )

    user_id = update.effective_user.id
    db.update_user_activity(user_id)
    
    uptime = time.time() - start_time
    days = int(uptime // 86400)
    hours = int((uptime % 86400) // 3600)
    minutes = int((uptime % 3600) // 60)
    
    uid_stats = db.get_uid_stats()
    stats = db.get_today_stats()
    groups = db.get_allowed_groups()
    chats = db.get_chat_count()
    admins = db.get_admins()
    
    text = f"{E['shield']} *{BOT_NAME} - SYSTEM STATUS*\n\n"
    text += f"{E['online']} *Bot:* `ONLINE`\n"
    text += f"{E['clock']} *Uptime:* `{days}d {hours}h {minutes}m`\n"
    text += f"{E['database']} *Database:* `CONNECTED`\n\n"
    text += f"{E['stats']} *STATISTICS*\n"
    text += f"├ {E['key']} UIDs: `{uid_stats['total']}`\n"
    text += f"├ {E['calendar']} Total Days: `{uid_stats['total_days'] if uid_stats else 0}`\n"
    text += f"├ {E['heart']} Today Likes: `{format_number(stats.get('total_likes', 0))}`\n"
    text += f"├ {E['success']} Today Success: `{stats.get('success_count', 0)}`\n"
    text += f"├ {E['error']} Today Failed: `{stats.get('failed_count', 0)}`\n"
    text += f"├ {E['warning']} Today Limit: `{stats.get('limit_count', 0)}`\n\n"
    text += f"{E['users']} *USERS*\n"
    text += f"├ Chats: `{chats}`\n"
    text += f"├ Groups: `{len(groups)}`\n"
    text += f"├ Admins: `{len(admins)}`\n"
    text += f"└ {E['clock']} Auto Time: `{data['auto_time']}` IST\n\n"
    text += f"{E['clock']} *Current:* `{format_time()}`\n"
    text += f"{E['dev']} *Dev:* {DEV_USERNAME}"
    
    await context.bot.send_message(
    chat_id=update.effective_chat.id,
    text=text,
    parse_mode="Markdown"
)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not can_use_bot(update):
        return await update.message.reply_text(
            "❌ This Bot can only be used in specific Groups"
        )

    user_id = update.effective_user.id
    db.update_user_activity(user_id)
    
    stats = db.get_today_stats()
    uid_stats = db.get_uid_stats()
    top_users = db.get_top_users(5)
    
    text = f"{E['chart']} *DETAILED STATISTICS*\n\n"
    text += f"{E['calendar']} *TODAY ({get_ist_now().strftime('%d %b %Y')})*\n"
    text += f"├ {E['heart']} Likes Sent: `{format_number(stats.get('total_likes', 0))}`\n"
    text += f"├ {E['success']} Success: `{stats.get('success_count', 0)}`\n"
    text += f"├ {E['error']} Failed: `{stats.get('failed_count', 0)}`\n"
    text += f"└ {E['warning']} Limit Reached: `{stats.get('limit_count', 0)}`\n\n"
    text += f"{E['database']} *ALL TIME*\n"
    text += f"├ {E['key']} Total UIDs: `{uid_stats['total'] if uid_stats else 0}`\n"
    text += f"├ {E['calendar']} Total Days: `{uid_stats['total_days'] if uid_stats else 0}`\n"
    text += f"└ {E['clock']} Server Time: `{format_time()}`\n\n"
    
    if top_users:
        text += f"{E['trophy']} *TOP USERS*\n"
        for i, user in enumerate(top_users[:5], 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "📌"
            text += f"{medal} `{user['username'] or ('User_' + str(user['user_id']))}` - {user['total_commands']} commands\n"
    
    await context.bot.send_message(
    chat_id=update.effective_chat.id,
    text=text,
    parse_mode="Markdown"
)

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not can_use_bot(update):
        return await update.message.reply_text(
            "❌ This Bot can only be used in specific Groups"
        )

    user = update.effective_user
    db.update_user_activity(user.id)

    user_data = db.get_user(user.id)
    
    text = f"{E['user']} *YOUR PROFILE*\n\n"
    text += f"{E['star']} *Name:* {user.first_name}\n"
    text += f"{E['key']} *ID:* `{user.id}`\n"
    text += f"{E['clock']} *Joined:* {user_data['join_date'] if user_data else 'Unknown'}\n"
    text += f"{E['stats']} *Commands:* {user_data['total_commands'] if user_data else 0}\n"
    text += f"{E['diamond']} *Premium:* {'✅' if user_data and user_data['is_premium'] else '❌'}\n"
    text += f"{E['coin']} *Coins:* {user_data['coins'] if user_data else 0}\n"
    text += f"{E['link']} *Referral:* `{user_data['referral_code'] if user_data else 'None'}`\n"
    text += f"{E['users']} *Referrals:* {user_data['total_referrals'] if user_data else 0}\n\n"
    text += f"{E['dev']} *Dev:* {DEV_USERNAME}"
    
    await context.bot.send_message(
    chat_id=update.effective_chat.id,
    text=text,
    parse_mode="Markdown"
)

async def regions_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not can_use_bot(update):
        return await update.message.reply_text(
            "❌ This Bot can only be used in specific Groups"
        )

    db.update_user_activity(update.effective_user.id)
    
    text = f"{E['globe']} *SUPPORTED REGIONS*\n\n"
    for code, info in REGIONS.items():
        text += f"{info['flag']} `{code}` - {info['name']} {info['emoji']}\n"
    text += f"\n{E['stats']} *Total:* {len(REGIONS)} regions"
    
    await context.bot.send_message(
    chat_id=update.effective_chat.id,
    text=text,
    parse_mode="Markdown"
)

async def list_uids_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not can_use_bot(update):
        return await update.message.reply_text(
            "❌ This Bot can only be used in specific Groups"
        )

    if not is_admin(update.effective_user.id):
        return await update.message.reply_text(
            f"{E['error']} *Unauthorized!*",
            parse_mode='Markdown'
        )

    db.update_user_activity(update.effective_user.id)
    uids = data['uids']
    
    if not uids:
        return await update.message.reply_text(f"{E['empty']} *No UIDs in database!*", parse_mode='Markdown')
    
    text = f"{E['folder']} *UID DATABASE*\n\n"
    region_groups = defaultdict(list)
    for uid in uids:
        region_groups[uid['region']].append(uid)
    
    for region, region_uids in region_groups.items():
        region_info = get_region_info(region)
        text += f"{region_info['flag']} *{region_info['name']}* ({len(region_uids)})\n"
        for i, uid in enumerate(region_uids[:10], 1):
            text += f"  {i}. `{uid['uid']}` ({uid['remaining_days']} days)\n"
        if len(region_uids) > 10:
            text += f"  ... +{len(region_uids)-10} more\n"
        text += "\n"
    
    text += f"\n{E['stats']} *Total:* {len(uids)} UIDs"
    
    if len(text) > 4000:
        text = text[:4000] + "\n\n*(Truncated. Use /export for full list)*"
    
    await update.callback_query.message.reply_text(
    text,
    parse_mode='Markdown'
)

async def search_uid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not can_use_bot(update):
        return await update.message.reply_text(
            "❌ This Bot can only be used in specific Groups"
        )

    if not is_admin(update.effective_user.id):
        return
    
    try:
        search_uid = context.args[0]
        db.update_user_activity(update.effective_user.id)
        
        uids = data['uids']
        found = [u for u in uids if u['uid'] == search_uid]
        
        if found:
            uid = found[0]
            region_info = get_region_info(uid['region'])
            text = f"{E['success']} *UID FOUND*\n\n"
            text += f"{E['key']} *UID:* `{uid['uid']}`\n"
            text += f"{region_info['flag']} *Region:* {region_info['name']}\n"
            text += f"{E['calendar']} *Days Left:* `{uid['remaining_days']}`\n"
            text += f"{E['clock']} *Added:* {uid.get('added_date', 'Unknown')}\n"
            await context.bot.send_message(
    chat_id=update.effective_chat.id,
    text=text,
    parse_mode="Markdown"
)
        else:
            await update.message.reply_text(f"{E['error']} *UID not found!*", parse_mode='Markdown')
    except:
        await update.message.reply_text(f"Usage: `/search UID`", parse_mode='Markdown')

async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not can_use_bot(update):
        return await update.message.reply_text(
            "❌ This Bot can only be used in specific Groups"
        )

    if not is_admin(update.effective_user.id):
        return
    
    db.update_user_activity(update.effective_user.id)
    uids = data['uids']
    
    if not uids:
        return await update.message.reply_text(f"{E['empty']} *No data to export!*", parse_mode='Markdown')
    
    text = f"{E['file']} *EXPORT DATA*\n\n"
    text += f"Generated: {format_ist_time()}\n\n"
    text += "*UIDs List:*\n"
    for uid in uids:
        text += f"• `{uid['uid']}` - {uid['region']} ({uid['remaining_days']} days)\n"
    
    await update.message.reply_text(text[:4000], parse_mode='Markdown')

# ==================== AUTO LIKE COMMANDS ====================
async def autolike_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not can_use_bot(update):
        return await update.message.reply_text(
            "❌ This Bot can only be used in specific Groups"
        )

    if not is_admin(update.effective_user.id):
        return await update.message.reply_text(
            f"{E['error']} *Unauthorized!*",
            parse_mode='Markdown'
        )
    
    try:
        uid = context.args[0]
        region = context.args[1].lower()
        days = int(context.args[2])
        
        if not uid.isdigit() or len(uid) < 5:
            return await update.message.reply_text(f"{E['error']} *Invalid UID!*", parse_mode='Markdown')
        if region not in REGIONS:
            return await update.message.reply_text(f"{E['error']} *Invalid Region!*", parse_mode='Markdown')
        if days < 1 or days > 365:
            return await update.message.reply_text(f"{E['error']} *Days must be 1-365!*", parse_mode='Markdown')
        
        db.update_user_activity(update.effective_user.id)
        
        if db.add_uid(uid, region, update.effective_user.id, days):
            data['uids'] = db.get_uids()
            region_info = get_region_info(region)
            expiry = (get_ist_now() + timedelta(days=days)).strftime("%d %b %Y")
            
            text = f"{E['success']} *✅ ADDED TO AUTO LIKE ✅*\n\n"
            text += f"{E['key']} *UID:* `{uid}`\n"
            text += f"{region_info['flag']} *Region:* {region_info['name']}\n"
            text += f"{E['calendar']} *Days:* `{days}`\n"
            text += f"{E['date']} *Expiry:* `{expiry}`\n"
            text += f"{E['clock']} *Auto Time:* `{data['auto_time']}` IST\n\n"
            text += f"{E['info']} Auto like will run daily at {data['auto_time']} IST"
            await context.bot.send_message(
    chat_id=update.effective_chat.id,
    text=text,
    parse_mode="Markdown"
)
        else:
            await update.message.reply_text(f"{E['error']} *Failed to add UID!*", parse_mode='Markdown')
    except IndexError:
        await update.message.reply_text(
            f"{E['warning']} *Usage:* `/autolike UID REGION DAYS`\n\n"
            f"*Example:* `/autolike 123456789 ind 30`\n\n"
            f"*Regions:* " + ", ".join(REGIONS.keys()),
            parse_mode='Markdown'
        )
    except ValueError:
        await update.message.reply_text(f"{E['error']} *Days must be a number!*", parse_mode='Markdown')

async def runnow_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg_obj = update.message or update.callback_query.message

    if not can_use_bot(update):
        return await msg_obj.reply_text(
            "❌ This Bot can only be used in specific Groups"
        )

    if not is_admin(update.effective_user.id):
        return await msg_obj.reply_text(
            f"{E['error']} *Unauthorized!*",
            parse_mode='Markdown'
        )

    uids = data['uids']

    if not uids:
        return await msg_obj.reply_text(f"{E['empty']} *No UIDs in database!*", parse_mode='Markdown')

    db.update_user_activity(update.effective_user.id)

    msg = await msg_obj.reply_text(
        f"{E['rocket']} *🚀 STARTING MANUAL LIKE 🚀*\n\n"
        f"{E['key']} *Total UIDs:* `{len(uids)}`\n"
        f"{E['clock']} *Time:* `{format_time()}`",
        parse_mode='Markdown'
    )
    
    success = 0
    limit = 0
    failed = 0
    
    for i, uid_data in enumerate(uids, 1):
        try:
            result = await send_like(uid_data['uid'], uid_data['region'])
            
            try:
                status = int(result.get('status', 0)) if str(result.get('status', 0)).isdigit() else 0
            except:
                status = 0
            
            try:
                likes = int(result.get('LikesGivenByAPI', 0)) if str(result.get('LikesGivenByAPI', 0)).isdigit() else 0
            except:
                likes = 0
            
            if status == 1 or likes > 0:
                success += 1
                db.decrement_days(uid_data['uid'])
                remaining = db.get_remaining_days(uid_data['uid'])
                result_text = format_result(result, uid_data['uid'], uid_data['region'], "manual", remaining)
                await update.message.reply_text(result_text, parse_mode='Markdown')
            elif status == 2:
                limit += 1
                await update.message.reply_text(format_result(result, uid_data['uid'], uid_data['region']), parse_mode='Markdown')
            else:
                failed += 1
                await msg_obj.reply_text(format_result(result, uid_data['uid'], uid_data['region']), parse_mode='Markdown')
            
            if i % 5 == 0:
                await msg.edit_text(
                    f"{E['rocket']} *PROGRESS:* `{i}/{len(uids)}`\n"
                    f"{E['success']} *Success:* `{success}`\n"
                    f"{E['warning']} *Limit:* `{limit}`\n"
                    f"{E['error']} *Failed:* `{failed}`",
                    parse_mode='Markdown'
                )
            
            await asyncio.sleep(1)
        except Exception as e:
            failed += 1
            await msg_obj.reply_text(f"{E['error']} Error: {str(e)[:100]}", parse_mode='Markdown')
    
    stats = db.get_today_stats()
    summary = (
        f"{E['stats']} *📊 MANUAL LIKE COMPLETED 📊*\n\n"
        f"{E['key']} *Processed:* `{len(uids)}`\n"
        f"{E['success']} *Success:* `{success}`\n"
        f"{E['warning']} *Limit:* `{limit}`\n"
        f"{E['error']} *Failed:* `{failed}`\n"
        f"{E['heart']} *Total Likes:* `{format_number(stats.get('total_likes', 0))}`\n\n"
        f"{E['clock']} *Time:* `{format_time()}`\n"
        f"{E['dev']} *Dev:* {DEV_USERNAME}"
    )
    
    await msg.edit_text(summary, parse_mode='Markdown')
    data['stats'] = db.get_today_stats()

async def remove_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not can_use_bot(update):
        return await update.message.reply_text(
            "❌ This Bot can only be used in specific Groups"
        )

    if not is_admin(update.effective_user.id):
        return
    
    try:
        uid = context.args[0]
        db.update_user_activity(update.effective_user.id)
        
        if db.remove_uid(uid):
            data['uids'] = db.get_uids()
            await update.message.reply_text(f"{E['success']} *Removed UID:* `{uid}`", parse_mode='Markdown')
        else:
            await update.message.reply_text(f"{E['error']} *UID not found!*", parse_mode='Markdown')
    except:
        await update.message.reply_text(f"Usage: `/remove UID`", parse_mode='Markdown')

async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not can_use_bot(update):
        return await update.message.reply_text(
            "❌ This Bot can only be used in specific Groups"
        )

    if not is_admin(update.effective_user.id):
        return
    
    try:
        uid = context.args[0]
        region = context.args[1].lower()
        if region not in REGIONS:
            return await update.message.reply_text(f"{E['error']} *Invalid region!*", parse_mode='Markdown')
        
        db.update_user_activity(update.effective_user.id)
        
        msg = await update.message.reply_text(f"{E['lab']} *Testing...*", parse_mode='Markdown')
        result = await send_like(uid, region)
        await msg.edit_text(format_result(result, uid, region), parse_mode='Markdown')
    except:
        await update.message.reply_text(f"Usage: `/test UID REGION`", parse_mode='Markdown')

async def region_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not can_use_bot(update):
        return await update.message.reply_text(
            "❌ This Bot can only be used in specific Groups"
        )

    if not is_admin(update.effective_user.id):
        return
    
    try:
        region = context.args[0].lower()
        if region not in REGIONS:
            return await update.message.reply_text(f"{E['error']} *Invalid region!*", parse_mode='Markdown')
        
        db.update_user_activity(update.effective_user.id)
        
        region_uids = [u for u in data['uids'] if u['region'] == region]
        if not region_uids:
            return await update.message.reply_text(f"{E['empty']} *No UIDs in this region!*", parse_mode='Markdown')
        
        region_info = get_region_info(region)
        text = f"{region_info['flag']} *{region_info['name']} UIDs* ({len(region_uids)})\n\n"
        for i, uid in enumerate(region_uids, 1):
            text += f"{i}. `{uid['uid']}` ({uid['remaining_days']} days)\n"
        
        await context.bot.send_message(
    chat_id=update.effective_chat.id,
    text=text,
    parse_mode="Markdown"
)
    except:
        await update.message.reply_text(f"Usage: `/region REGION`", parse_mode='Markdown')

# ==================== ADMIN SETTINGS COMMANDS ====================
async def settime_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not can_use_bot(update):
        return await update.message.reply_text(
            "❌ This Bot can only be used in specific Groups"
        )

    if not is_super_admin(update.effective_user.id):
        return
    
    try:
        time_str = context.args[0]
        datetime.strptime(time_str, "%H:%M")
        db.set_setting('auto_time', time_str)
        data['auto_time'] = time_str
        db.update_user_activity(update.effective_user.id)
        
        await update.message.reply_text(
            f"{E['success']} *Auto like time updated!*\n\n"
            f"{E['clock']} *New Time:* `{time_str}` IST",
            parse_mode='Markdown'
        )
    except:
        await update.message.reply_text(f"Usage: `/settime HH:MM`\nExample: `/settime 06:30`", parse_mode='Markdown')

async def addgroup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not can_use_bot(update):
        return await update.message.reply_text(
            "❌ This Bot can only be used in specific Groups"
        )

    if not is_super_admin(update.effective_user.id):
        return
    
    chat = update.effective_chat
    if chat.type not in ['group', 'supergroup']:
        return await update.message.reply_text(f"{E['warning']} *Use this command in a group!*", parse_mode='Markdown')
    
    db.update_user_activity(update.effective_user.id)
    
    if db.add_allowed_group(chat.id, chat.title or "Group", chat.username or "", update.effective_user.id):
        data['allowed_groups'] = db.get_allowed_groups()
        await update.message.reply_text(
            f"{E['success']} *Group added to allowed list!*\n\n"
            f"{E['folder']} *Group:* `{chat.title}`\n"
            f"{E['key']} *ID:* `{chat.id}`\n\n"
            f"Auto like will be sent here!",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(f"{E['warning']} *Group already in list!*", parse_mode='Markdown')

async def removegroup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not can_use_bot(update):
        return await update.message.reply_text(
            "❌ This Bot can only be used in specific Groups"
        )

    if not is_super_admin(update.effective_user.id):
        return
    
    chat = update.effective_chat
    if chat.type not in ['group', 'supergroup']:
        return await update.message.reply_text(f"{E['warning']} *Use this command in a group!*", parse_mode='Markdown')
    
    db.update_user_activity(update.effective_user.id)
    
    if db.remove_allowed_group(chat.id):
        data['allowed_groups'] = db.get_allowed_groups()
        await update.message.reply_text(
            f"{E['success']} *Group removed from allowed list!*\n\n"
            f"{E['folder']} *Group:* `{chat.title}`",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(f"{E['warning']} *Group not in list!*", parse_mode='Markdown')

async def listgroups_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not can_use_bot(update):
        return await update.message.reply_text(
            "❌ This Bot can only be used in specific Groups"
        )

    if not is_super_admin(update.effective_user.id):
        return
    
    db.update_user_activity(update.effective_user.id)
    groups = data['allowed_groups']
    
    if not groups:
        return await update.message.reply_text(f"{E['empty']} *No allowed groups!*", parse_mode='Markdown')
    
    text = f"{E['folder']} *ALLOWED GROUPS* ({len(groups)})\n\n"
    for i, group in enumerate(groups, 1):
        text += f"{i}. {E['users']} `{group['chat_title']}`\n"
        text += f"   🆔 `{group['chat_id']}`\n\n"
    
    await context.bot.send_message(
    chat_id=update.effective_chat.id,
    text=text,
    parse_mode="Markdown"
)

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not can_use_bot(update):
        return await update.message.reply_text(
            "❌ This Bot can only be used in specific Groups"
        )

    if not is_super_admin(update.effective_user.id):
        return
    
    if not context.args and not update.message.reply_to_message:
        return await update.message.reply_text(
            f"{E['warning']} *Usage:*\n"
            f"├ `/broadcast message` - Text broadcast\n"
            f"└ Reply to media with `/broadcast caption` - Media broadcast",
            parse_mode='Markdown'
        )
    
    db.update_user_activity(update.effective_user.id)
    chats = db.get_chats()
    
    if not chats:
        return await update.message.reply_text(f"{E['error']} *No chats to broadcast!*", parse_mode='Markdown')
    
    msg = await update.message.reply_text(
        f"{E['broadcast']} *Broadcasting to {len(chats)} chats...*",
        parse_mode='Markdown'
    )
    
    sent = 0
    failed = 0
    
    if update.message.reply_to_message:
        for chat_id in chats:
            try:
                await update.message.reply_to_message.copy(chat_id)
                sent += 1
                await asyncio.sleep(0.05)
            except:
                failed += 1
    else:
        text = ' '.join(context.args)
        for chat_id in chats:
            try:
                await context.bot.send_message(chat_id, f"{E['broadcast']} *BROADCAST*\n\n{text}", parse_mode='Markdown')
                sent += 1
                await asyncio.sleep(0.05)
            except:
                failed += 1
    
    db.add_broadcast_history(text if not update.message.reply_to_message else "Media", update.effective_user.id, sent, failed)
    
    await msg.edit_text(
        f"{E['success']} *Broadcast completed!*\n\n"
        f"{E['check']} *Sent:* `{sent}`\n"
        f"{E['error']} *Failed:* `{failed}`\n"
        f"{E['stats']} *Success Rate:* `{sent/len(chats)*100:.1f}%`",
        parse_mode='Markdown'
    )

async def broadcastpin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not can_use_bot(update):
        return await update.message.reply_text(
            "❌ This Bot can only be used in specific Groups"
        )

    if not is_super_admin(update.effective_user.id):
        return
    
    if not context.args and not update.message.reply_to_message:
        return await update.message.reply_text(
            f"{E['warning']} *Usage:*\n"
            f"├ `/broadcastpin message` - Text broadcast + pin\n"
            f"└ Reply to media with `/broadcastpin caption` - Media + pin",
            parse_mode='Markdown'
        )
    
    db.update_user_activity(update.effective_user.id)
    chats = db.get_chats()
    groups = db.get_allowed_group_ids()
    
    if not chats:
        return await update.message.reply_text(f"{E['error']} *No chats to broadcast!*", parse_mode='Markdown')
    
    msg = await update.message.reply_text(
        f"{E['broadcast']} *Broadcasting to {len(chats)} chats (pin in {len(groups)} groups)...*",
        parse_mode='Markdown'
    )
    
    sent = 0
    pinned = 0
    failed = 0
    
    if update.message.reply_to_message:
        for chat_id in chats:
            try:
                m = await update.message.reply_to_message.copy(chat_id)
                sent += 1
                if chat_id in groups:
                    try:
                        await context.bot.pin_chat_message(chat_id, m.message_id, disable_notification=True)
                        pinned += 1
                    except:
                        pass
                await asyncio.sleep(0.05)
            except:
                failed += 1
    else:
        text = ' '.join(context.args)
        for chat_id in chats:
            try:
                m = await context.bot.send_message(chat_id, f"{E['broadcast']} {E['pin']} *BROADCAST*\n\n{text}", parse_mode='Markdown')
                sent += 1
                if chat_id in groups:
                    try:
                        await context.bot.pin_chat_message(chat_id, m.message_id, disable_notification=True)
                        pinned += 1
                    except:
                        pass
                await asyncio.sleep(0.05)
            except:
                failed += 1
    
    await msg.edit_text(
        f"{E['success']} *BroadcastPin completed!*\n\n"
        f"{E['check']} *Sent:* `{sent}`\n"
        f"{E['pin']} *Pinned:* `{pinned}`\n"
        f"{E['error']} *Failed:* `{failed}`",
        parse_mode='Markdown'
    )

async def maintenance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_super_admin(update.effective_user.id):
        return
    
    try:
        mode = context.args[0].lower()
        if mode in ['on', 'off']:
            db.set_setting('maintenance_mode', mode)
            data['maintenance'] = mode
            status = "ENABLED 🔒" if mode == 'on' else "DISABLED 🔓"
            await update.message.reply_text(
                f"{E['wrench']} *Maintenance Mode*\n\n"
                f"Status: `{status}`",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(f"Usage: `/maintenance on` or `/maintenance off`", parse_mode='Markdown')
    except:
        current = data['maintenance']
        await update.message.reply_text(
            f"{E['wrench']} *Maintenance Mode*\n\n"
            f"Current: `{current.upper()}`",
            parse_mode='Markdown'
        )

async def addadmin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not can_use_bot(update):
        return await update.message.reply_text(
            "❌ This Bot can only be used in specific Groups"
        )

    if not is_super_admin(update.effective_user.id):
        return
    
    try:
        user_id = int(context.args[0])
        if user_id == OWNER_ID:
            return await update.message.reply_text(f"{E['owner']} *Owner is already super admin!*", parse_mode='Markdown')
        
        try:
            user = await context.bot.get_chat(user_id)
            username = f"@{user.username}" if user.username else f"user_{user_id}"
        except:
            username = f"user_{user_id}"
        
        level = 'super_admin' if len(context.args) > 1 and context.args[1].lower() == 'super' else 'admin'
        
        if db.add_admin(user_id, username, update.effective_user.id, level):
            try:
                await context.bot.send_message(user_id, f"{E['party']} *You are now an admin!*\n\nLevel: `{level}`", parse_mode='Markdown')
            except:
                pass
            await update.message.reply_text(
                f"{E['success']} *Admin added!*\n\n"
                f"{E['user']} *User:* `{user_id}`\n"
                f"{E['crown']} *Level:* `{level}`",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(f"{E['warning']} *User is already an admin!*", parse_mode='Markdown')
    except:
        await update.message.reply_text(f"Usage: `/addadmin USER_ID [super]`", parse_mode='Markdown')

async def radmin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not can_use_bot(update):
        return await update.message.reply_text(
            "❌ This Bot can only be used in specific Groups"
        )

    if not is_super_admin(update.effective_user.id):
        return
    
    try:
        user_id = int(context.args[0])
        if user_id == OWNER_ID:
            return await update.message.reply_text(f"{E['owner']} *Cannot remove owner!*", parse_mode='Markdown')
        
        if db.remove_admin(user_id):
            try:
                await context.bot.send_message(user_id, f"{E['warning']} *You are no longer an admin!*", parse_mode='Markdown')
            except:
                pass
            await update.message.reply_text(f"{E['success']} *Admin removed:* `{user_id}`", parse_mode='Markdown')
        else:
            await update.message.reply_text(f"{E['error']} *User is not an admin!*", parse_mode='Markdown')
    except:
        await update.message.reply_text(f"Usage: `/radmin USER_ID`", parse_mode='Markdown')

async def admins_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not can_use_bot(update):
        return await update.message.reply_text(
            "❌ This Bot can only be used in specific Groups"
        )

    if not is_super_admin(update.effective_user.id):
        return
    
    admins = db.get_admins()
    if not admins:
        return await update.message.reply_text(f"{E['empty']} *No admins found!*", parse_mode='Markdown')
    
    text = f"{E['crown']} *ADMIN LIST*\n\n"
    super_admins = [a for a in admins if a['level'] == 'super_admin']
    regular_admins = [a for a in admins if a['level'] == 'admin']
    
    if super_admins:
        text += f"{E['diamond']} *SUPER ADMINS*\n"
        for i, admin in enumerate(super_admins, 1):
            owner = " 👑" if admin['user_id'] == OWNER_ID else ""
            text += f"{i}. `{admin['user_id']}` ({admin['username']}){owner}\n"
        text += "\n"
    
    if regular_admins:
        text += f"{E['star']} *REGULAR ADMINS*\n"
        for i, admin in enumerate(regular_admins, 1):
            text += f"{i}. `{admin['user_id']}` ({admin['username']})\n"
    
    text += f"\n{E['stats']} *Total:* {len(admins)}"
    await context.bot.send_message(
    chat_id=update.effective_chat.id,
    text=text,
    parse_mode="Markdown"
)

async def system_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not can_use_bot(update):
        return await update.message.reply_text(
            "❌ This Bot can only be used in specific Groups"
        )

    if not is_super_admin(update.effective_user.id):
        return
    
    import sys, platform
    
    uptime = time.time() - start_time
    days = int(uptime // 86400)
    hours = int((uptime % 86400) // 3600)
    minutes = int((uptime % 3600) // 60)
    
    uid_stats = db.get_uid_stats()
    
    text = f"{E['computer']} *SYSTEM INFORMATION*\n\n"
    text += f"{E['clock']} *Uptime:* `{days}d {hours}h {minutes}m`\n"
    text += f"{E['computer']} *Python:* `{sys.version.split()[0]}`\n"
    text += f"{E['globe']} *Platform:* `{platform.system()}`\n"
    text += f"{E['database']} *Database:* `SQLite 3`\n\n"
    text += f"{E['stats']} *BOT STATS*\n"
    text += f"├ {E['key']} UIDs: `{uid_stats['total']}`\n"
    text += f"├ {E['calendar']} Total Days: `{uid_stats['total_days'] if uid_stats else 0}`\n"
    text += f"├ {E['users']} Chats: `{db.get_chat_count()}`\n"
    text += f"├ {E['users']} Groups: `{len(data['allowed_groups'])}`\n"
    text += f"└ {E['crown']} Admins: `{len(db.get_admins())}`\n\n"
    text += f"{E['clock']} *Time:* `{format_time()}`\n"
    text += f"{E['dev']} *Version:* `{BOT_VERSION}`"
    
    await context.bot.send_message(
    chat_id=update.effective_chat.id,
    text=text,
    parse_mode="Markdown"
)

async def clearcache_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_super_admin(update.effective_user.id):
        return
    
    global data
    data = load_data()
    await update.message.reply_text(f"{E['broom']} *Cache cleared successfully!*", parse_mode='Markdown')

async def backup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_super_admin(update.effective_user.id):
        return
    
    await update.message.reply_text(f"{E['database']} *Backup feature coming soon!*", parse_mode='Markdown')

async def resetstats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_super_admin(update.effective_user.id):
        return
    
    db.set_setting('reset_stats_date', get_ist_now().strftime("%Y-%m-%d"))
    data['stats'] = db.get_today_stats()
    await update.message.reply_text(f"{E['chart']} *Daily stats reset!*", parse_mode='Markdown')

# ==================== CALLBACK HANDLERS ====================
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    db.update_user_activity(user_id)
    
    if query.data == "run_now":
        await runnow_command(update, context)
    
    elif query.data == "show_stats":
        stats = db.get_today_stats()
        uid_stats = db.get_uid_stats()
        text = f"{E['stats']} *📊 TODAY'S STATS 📊*\n\n"
        text += f"{E['heart']} *Likes:* `{format_number(stats.get('total_likes', 0))}`\n"
        text += f"{E['success']} *Success:* `{stats.get('success_count', 0)}`\n"
        text += f"{E['error']} *Failed:* `{stats.get('failed_count', 0)}`\n"
        text += f"{E['warning']} *Limit:* `{stats.get('limit_count', 0)}`\n\n"
        text += f"{E['database']} *DATABASE*\n"
        text += f"├ {E['key']} UIDs: `{uid_stats['total'] if uid_stats else 0}`\n"
        text += f"└ {E['calendar']} Total Days: `{uid_stats['total_days'] if uid_stats else 0}`"
        await query.edit_message_text(text, parse_mode='Markdown')
    
    elif query.data == "add_uid":
        await query.edit_message_text(
            f"{E['plus']} *ADD UID*\n\n"
            f"Use command: `/autolike UID REGION DAYS`\n\n"
            f"*Example:* `/autolike 123456789 ind 30`\n\n"
            f"*Regions:* " + ", ".join(REGIONS.keys()),
            parse_mode='Markdown'
        )
    
    elif query.data == "list_uids":
        await list_uids_command(update, context)
    
    elif query.data == "auto_like_settings":
        text = f"{E['calendar']} *AUTO LIKE SETTINGS*\n\n"
        text += f"{E['clock']} *Current Time:* `{data['auto_time']}` IST\n"
        text += f"{E['info']} *Status:* {'Enabled' if data['maintenance'] != 'on' else 'Maintenance'}\n\n"
        text += f"To change time: `/settime HH:MM`\n"
        text += f"Example: `/settime 06:30`"
        await query.edit_message_text(text, parse_mode='Markdown')
    
    elif query.data == "settings_menu":
        text = f"{E['settings']} *SETTINGS*\n\n"
        text += f"{E['clock']} *Auto Time:* `{data['auto_time']}` IST\n"
        text += f"{E['wrench']} *Maintenance:* `{data['maintenance'].upper()}`\n"
        text += f"{E['broadcast']} *Auto Post:* Enabled\n\n"
        text += f"Use `/settime` to change auto like time\n"
        text += f"Use `/maintenance` to toggle maintenance mode"
        await query.edit_message_text(text, parse_mode='Markdown')
    
    elif query.data == "admin_panel":
        if not is_admin(user_id):
            await query.edit_message_text(f"{E['error']} *Unauthorized!*", parse_mode='Markdown')
            return
        
        uid_stats = db.get_uid_stats()
        text = f"{E['crown']} *ADMIN PANEL*\n\n"
        text += f"{E['key']} *Total UIDs:* `{uid_stats['total'] if uid_stats else 0}`\n"
        text += f"{E['calendar']} *Total Days:* `{uid_stats['total_days'] if uid_stats else 0}`\n"
        text += f"{E['users']} *Groups:* `{len(data['allowed_groups'])}`\n"
        text += f"{E['crown']} *Admins:* `{len(db.get_admins())}`\n\n"
        text += f"*Commands:*\n"
        text += f"├ /autolike - Add UID\n"
        text += f"├ /runnow - Manual like\n"
        text += f"├ /list - List UIDs\n"
        text += f"├ /remove - Remove UID\n"
        text += f"├ /export - Export data\n"
        text += f"└ /region - Region UIDs"
        await query.edit_message_text(text, parse_mode='Markdown')
    
    else:
        await query.edit_message_text(f"{E['info']} *Unknown command!*", parse_mode='Markdown')

# ==================== AUTO SCHEDULER ====================
async def auto_like_scheduler(app):
    last_run_date = None
    
    while True:
        try:
            now = get_ist_now()
            auto_time = data['auto_time']
            current_time = now.strftime("%H:%M")
            current_date = now.strftime("%Y-%m-%d")
            
            if current_time == auto_time and last_run_date != current_date and data['maintenance'] != 'on':
                if data['uids']:
                    print(f"🚀 Auto like started at {format_time()}")
                    last_run_date = current_date
                    
                    active_uids = db.get_uids()
                    groups = db.get_allowed_group_ids()
                    
                    start_msg = f"{E['rocket']} *DAILY AUTO LIKE STARTED*\n\n{E['key']} Total: {len(active_uids)}\n{E['clock']} Time: {format_time()}"
                    for g in groups:
                        try:
                            await app.bot.send_message(g, start_msg, parse_mode='Markdown')
                        except:
                            pass
                    
                    success = 0
                    limit = 0
                    failed = 0
                    total_likes = 0
                    
                    for uid_data in active_uids:
                        try:
                            result = await send_like(uid_data['uid'], uid_data['region'])
                            
                            status = int(result.get('status', 0)) if str(result.get('status', 0)).isdigit() else 0
                            likes = int(result.get('LikesGivenByAPI', 0)) if str(result.get('LikesGivenByAPI', 0)).isdigit() else 0
                            
                            if status == 1 or likes > 0:
                                success += 1
                                total_likes += likes
                                db.decrement_days(uid_data['uid'])
                                remaining = db.get_remaining_days(uid_data['uid'])
                                result_text = format_result(result, uid_data['uid'], uid_data['region'], "auto", remaining)
                                for g in groups:
                                    try:
                                        await app.bot.send_message(g, result_text, parse_mode='Markdown')
                                    except:
                                        pass
                            elif status == 2:
                                limit += 1
                                result_text = format_result(result, uid_data['uid'], uid_data['region'], "auto")
                                for g in groups:
                                    try:
                                        await app.bot.send_message(g, result_text, parse_mode='Markdown')
                                    except:
                                        pass
                            else:
                                failed += 1
                            
                            await asyncio.sleep(1)
                        except:
                            failed += 1
                    
                    summary = f"{E['stats']} *AUTO LIKE SUMMARY*\n\n{E['check']} Success: {success}\n{E['warning']} Limit: {limit}\n{E['error']} Failed: {failed}\n{E['heart']} Likes: {total_likes}"
                    for g in groups:
                        try:
                            await app.bot.send_message(g, summary, parse_mode='Markdown')
                        except:
                            pass
                    
                    db.add_auto_like_history(current_date, len(active_uids), success, failed, limit, total_likes)
                    data['stats'] = db.get_today_stats()
                    
                    await asyncio.sleep(60)
            await asyncio.sleep(30)
        except Exception as e:
            print(f"Auto like error: {e}")
            await asyncio.sleep(30)

# ==================== MAIN ====================
async def main():
    print("=" * 50)
    print(f"🚀 Starting {BOT_NAME} v{BOT_VERSION}")
    print("=" * 50)
    print(f"✅ Loaded: {len(data['uids'])} UIDs")
    print(f"✅ Groups: {len(data['allowed_groups'])}")
    print(f"✅ Chats: {len(data['chats'])}")
    print(f"⏰ Auto Time: {data['auto_time']} IST")
    print(f"👑 Owner: {OWNER_ID}")
    print(f"⚡ Dev: {DEV_USERNAME}")
    print("=" * 50)
    
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Basic commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("profile", profile_command))
    app.add_handler(CommandHandler("regions", regions_command))
    
    # Admin commands
    app.add_handler(CommandHandler("list", list_uids_command))
    app.add_handler(CommandHandler("search", search_uid_command))
    app.add_handler(CommandHandler("export", export_command))
    app.add_handler(CommandHandler("autolike", autolike_command))
    app.add_handler(CommandHandler("runnow", runnow_command))
    app.add_handler(CommandHandler("remove", remove_command))
    app.add_handler(CommandHandler("test", test_command))
    app.add_handler(CommandHandler("region", region_command))
    
    # Super admin commands
    app.add_handler(CommandHandler("settime", settime_command))
    app.add_handler(CommandHandler("addgroup", addgroup_command))
    app.add_handler(CommandHandler("removegroup", removegroup_command))
    app.add_handler(CommandHandler("listgroups", listgroups_command))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    app.add_handler(CommandHandler("broadcastpin", broadcastpin_command))
    app.add_handler(CommandHandler("maintenance", maintenance_command))
    app.add_handler(CommandHandler("addadmin", addadmin_command))
    app.add_handler(CommandHandler("radmin", radmin_command))
    app.add_handler(CommandHandler("admins", admins_command))
    app.add_handler(CommandHandler("system", system_command))
    app.add_handler(CommandHandler("clearcache", clearcache_command))
    app.add_handler(CommandHandler("backup", backup_command))
    app.add_handler(CommandHandler("resetstats", resetstats_command))
    
    # Callback handler
    app.add_handler(CallbackQueryHandler(button_callback))
    
    # Start scheduler
    asyncio.create_task(auto_like_scheduler(app))

    print("✅ Bot is running!")
    print("=" * 50)

    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())