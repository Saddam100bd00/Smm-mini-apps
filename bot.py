import asyncio

# ================= ১. ইভেন্ট লুপ ফিক্স =================
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

import os
import re
import time
from aiohttp import web
from pyrogram import Client, filters, idle
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatJoinRequest, CallbackQuery, Message
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timedelta
import traceback

# ================= ২. কনফিগারেশন =================

def parse_id(val):
    val = str(val).strip()
    if not val or val == "0" or val.lower() == "none":
        return 0
    try:
        return int(val)
    except ValueError:
        if "t.me/" in val:
            username = val.split("t.me/")[-1].strip("/")
            if not username.startswith("+") and not username.startswith("joinchat"):
                return "@" + username
        return val

API_ID = int(os.environ.get("API_ID", 1234567))
API_HASH = os.environ.get("API_HASH", "your_api_hash")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "your_bot_token")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 123456789))
PORT = int(os.environ.get("PORT", 8080))
TRIAL_MINUTES = int(os.environ.get("TRIAL_MINUTES", 5))

PROOF_CHANNEL_ID = parse_id(os.environ.get("PROOF_CHANNEL_ID", 0))
PROMO_CODE = os.environ.get("PROMO_CODE", "VIP50")
PROMO_DISCOUNT = int(os.environ.get("PROMO_DISCOUNT", 20))

PAYMENT_NUMBER = "01985664862"

CHANNELS = {
    "1": parse_id(os.environ.get("CH1_ID", 0)),
    "2": parse_id(os.environ.get("CH2_ID", 0)),
    "3": parse_id(os.environ.get("CH3_ID", 0)),
    "4": parse_id(os.environ.get("CH4_ID", 0))
}
TRIAL_CHANNELS = [v for v in CHANNELS.values() if v != 0]

CHANNEL_NAMES = {
    "1": "বাচ্চাদের ভিডিও",
    "2": "R.P Video",
    "3": "vip Bangla video",
    "4": "Viral Video channel"
}
BN_NUMS = {"1": "১", "2": "২", "3": "৩", "4": "৪"}

app = Client("premium_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

PRICES = {"1": 50, "2": 50, "3": 50, "4": 50, "all": 180}

user_selections = {} 
waiting_for_payment = {} 
pending_approvals = {} 
admin_state = {} 
db = None 

import json

# ইন-মেমোরি ক্যাশ (AutoPayBD অ্যাপ থেকে Webhook আসার সাথে সাথে এখানে সেভ হবে)
received_sms_cache = {}

# ৫ মিনিট ট্রায়াল ট্র্যাকার ও অপ্টিমাইজড ক্যাশ (Firebase 50,000 Quota প্রটেকশন)
ACTIVE_TRIALS = {}      # f"{user_id}_{chat_id}" -> {user_id, chat_id, ch_name, user_name, expire_at, task}
USER_CACHE = {}         # user_id -> {'data': dict, 'time': float}
USER_CACHE_TTL = 3600   # ১ ঘণ্টা মেমোরি ক্যাশ (Firestore ৫০,০০০ কোটা সুরক্ষিত রাখতে)
STATS_CACHE = {'data': None, 'time': 0}

# লোকাল ফাইল ক্যাশ ও রেজিস্টার্ড ইউজার তালিকা (ব্রডকাস্ট ও অটো-পোস্টে Firestore 0 Reads খরচ হবে)
REGISTERED_USERS_FILE = "cached_users.json"
REGISTERED_USERS_SET = set()
FIRESTORE_READS_SAVED = 0

def load_local_registered_users():
    global REGISTERED_USERS_SET
    try:
        if os.path.exists(REGISTERED_USERS_FILE):
            with open(REGISTERED_USERS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    REGISTERED_USERS_SET = set(str(x) for x in data if str(x) != "0")
                    print(f"✅ Loaded {len(REGISTERED_USERS_SET)} users from local cache file!")
    except Exception as e:
        print(f"Error loading local users: {e}")

def save_local_registered_users():
    try:
        with open(REGISTERED_USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(list(REGISTERED_USERS_SET), f)
    except Exception as e:
        print(f"Error saving local users: {e}")

def register_user_id(uid):
    global REGISTERED_USERS_SET
    if not uid:
        return
    uid = str(uid).strip()
    if uid and uid != "0" and uid.lower() != "none" and uid not in REGISTERED_USERS_SET:
        REGISTERED_USERS_SET.add(uid)
        save_local_registered_users()

def get_cached_user(user_id: str) -> dict:
    global FIRESTORE_READS_SAVED
    user_id = str(user_id)
    now = time.time()
    if user_id in USER_CACHE:
        entry = USER_CACHE[user_id]
        if now - entry.get('time', 0) < USER_CACHE_TTL:
            FIRESTORE_READS_SAVED += 1
            return entry.get('data', {})
    if db:
        try:
            doc = db.collection('users').document(user_id).get()
            if doc.exists:
                data = doc.to_dict()
                USER_CACHE[user_id] = {'data': data, 'time': now}
                register_user_id(user_id)
                return data
        except Exception as e:
            print(f"Error reading user {user_id} from db: {e}")
    return USER_CACHE.get(user_id, {}).get('data', {})

def update_cached_user(user_id: str, updates: dict):
    user_id = str(user_id)
    register_user_id(user_id)
    now = time.time()
    if user_id not in USER_CACHE:
        USER_CACHE[user_id] = {'data': {}, 'time': now}
    USER_CACHE[user_id]['data'].update(updates)
    USER_CACHE[user_id]['time'] = now
    
    if db:
        try:
            db.collection('users').document(user_id).set(updates, merge=True)
        except Exception as e:
            print(f"Error updating user {user_id} in db: {e}")

def extract_trx_id(text: str) -> str:
    if not text:
        return ""
    text = text.strip()
    match = re.search(r'\b[A-Za-z0-9]{8,12}\b', text)
    if match:
        return match.group(0).upper()
    return text.replace(" ", "").upper()

# ================= ৩. কীবোর্ড ও কনফিগারেশন =================
SETTINGS_FILE = "bot_settings.json"
COLORFUL_BUTTONS = True

DEFAULT_WELCOME_TEXT = (
    "হ্যালো {name}! 👋\n\n"
    "✨ **আমাদের প্রিমিয়াম ভিআইপি বটে আপনাকে স্বাগতম!** ✨\n\n"
    f"আমাদের যেকোনো চ্যানেলে জয়েন রিকোয়েস্ট দিলে আপনি {TRIAL_MINUTES} মিনিটের জন্য **ফ্রি ট্রায়াল** পাবেন। ট্রায়াল শেষ হলে স্বয়ংক্রিয়ভাবে রিমুভ হয়ে যাবেন।\n\n"
    "🚀 **সারাজীবনের জন্য (Lifetime) অ্যাক্সেস** পেতে নিচের বাটন থেকে আপনার পছন্দের প্যাকেজটি বেছে নিন:"
)

WELCOME_CONFIG = {
    'media_type': None,
    'file_id': None,
    'text': DEFAULT_WELCOME_TEXT
}

DEFAULT_HOW_TO_BUY_TEXT = (
    "📖 **কিভাবে সহজে প্রিমিয়াম প্যাকেজ কিনবেন (টিউটোরিয়াল):**\n\n"
    "১️⃣ **প্যাকেজ নির্বাচন:** প্রধান মেনু থেকে আপনার পছন্দের প্যাকেজটি সিলেক্ট করুন (১টি, ২টি, ৩টি বা ৪টি চ্যানেল বান্ডেল)।\n"
    "২️⃣ **পেমেন্ট মাধ্যম:** বিকাশ, নগদ, রকেট অথবা উপায় নির্বাচন করুন।\n"
    "৩️⃣ **টাকা পাঠান (Send Money):** প্রদর্শিত পার্সোনাল নাম্বারে নির্ধারিত টাকা Send Money করুন।\n"
    "৪️⃣ **TrxID দিন:** টাকা পাঠানোর পর ফিরতি SMS-এর Transaction ID (TrxID) লিখে বটে মেসেজ পাঠান।\n"
    "৫️⃣ **অটোমেটিক এক্সেস:** সেকেন্ডের মধ্যে সিস্টেম স্বয়ংক্রিয়ভাবে আপনার পেমেন্ট ভেরিফাই করে চ্যানেলের ইনভাইট লিংক দিয়ে দিবে এবং জয়েন রিকোয়েস্ট দিলে অটো এপ্রুভ হয়ে যাবে! 🚀\n\n"
    "💬 কোনো অসুবিধা হলে আমাদের লাইভ সাপোর্টে যোগাযোগ করুন: @ItsSaddam9"
)

HOW_TO_BUY_CONFIG = {
    'media_type': None,
    'file_id': None,
    'text': DEFAULT_HOW_TO_BUY_TEXT
}

def load_bot_settings():
    global COLORFUL_BUTTONS, WELCOME_CONFIG, HOW_TO_BUY_CONFIG
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                COLORFUL_BUTTONS = data.get("colorful_buttons", True)
                if "welcome" in data:
                    WELCOME_CONFIG.update(data["welcome"])
                if "how_to_buy" in data:
                    HOW_TO_BUY_CONFIG.update(data["how_to_buy"])
        except Exception as e:
            print(f"Error loading bot settings: {e}")

def save_bot_settings():
    try:
        data = {
            "colorful_buttons": COLORFUL_BUTTONS,
            "welcome": {
                "media_type": WELCOME_CONFIG.get("media_type"),
                "file_id": WELCOME_CONFIG.get("file_id"),
                "text": WELCOME_CONFIG.get("text", DEFAULT_WELCOME_TEXT)
            },
            "how_to_buy": {
                "media_type": HOW_TO_BUY_CONFIG.get("media_type"),
                "file_id": HOW_TO_BUY_CONFIG.get("file_id"),
                "text": HOW_TO_BUY_CONFIG.get("text", DEFAULT_HOW_TO_BUY_TEXT)
            }
        }
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        if db:
            try:
                db.collection("config").document("bot_settings").set(data, merge=True)
            except:
                pass
    except Exception as e:
        print(f"Error saving bot settings: {e}")

load_bot_settings()

def get_bd_time_str():
    # Bangladesh Standard Time (UTC+6)
    utc_now = datetime.utcnow()
    bd_now = utc_now + timedelta(hours=6)
    return bd_now.strftime('%d %b %Y, %I:%M %p')

def get_main_keyboard():
    if COLORFUL_BUTTONS:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton(f"📺 ১টি চ্যানেল - {PRICES['1']} ৳", callback_data="pkg_1"),
             InlineKeyboardButton(f"🎬 ২টি চ্যানেল - {PRICES['2']*2} ৳", callback_data="pkg_2")], 
            [InlineKeyboardButton(f"🔥 ৩টি চ্যানেল - {PRICES['3']*3} ৳", callback_data="pkg_3"),
             InlineKeyboardButton(f"👑 ৪টি চ্যানেল - {PRICES['all']} ৳ (ফুল বান্ডেল)", callback_data="pkg_4")],
            [InlineKeyboardButton("👤 আমার একাউন্ট", callback_data="my_account"),
             InlineKeyboardButton("🎁 রেফার ও টোকেন", callback_data="referral_menu")],
            [InlineKeyboardButton("📖 কিভাবে কিনবেন?", callback_data="how_to_buy")],
            [InlineKeyboardButton("❓ হেল্প ও FAQ", callback_data="faq"),
             InlineKeyboardButton("👨‍💻 লাইভ সাপোর্ট", url="https://t.me/ItsSaddam9")],
            [InlineKeyboardButton("✅ পেমেন্ট প্রুফ চ্যানেল", url="https://t.me/Premium_payment_pruf")]
        ])
    else:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton(f"📺 ১টি চ্যানেল - {PRICES['1']} ৳", callback_data="pkg_1"),
             InlineKeyboardButton(f"🎬 ২টি চ্যানেল - {PRICES['2']*2} ৳", callback_data="pkg_2")], 
            [InlineKeyboardButton(f"🔥 ৩টি চ্যানেল - {PRICES['3']*3} ৳", callback_data="pkg_3"),
             InlineKeyboardButton(f"👑 ৪টি চ্যানেল - {PRICES['all']} ৳", callback_data="pkg_4")],
            [InlineKeyboardButton("👤 আমার একাউন্ট", callback_data="my_account"),
             InlineKeyboardButton("🎁 রেফার ও টোকেন", callback_data="referral_menu")],
            [InlineKeyboardButton("📖 কিভাবে কিনবেন?", callback_data="how_to_buy")],
            [InlineKeyboardButton("❓ হেল্প ও FAQ", callback_data="faq"),
             InlineKeyboardButton("👨‍💻 লাইভ সাপোর্ট", url="https://t.me/ItsSaddam9")],
            [InlineKeyboardButton("✅ পেমেন্ট প্রুফ", url="https://t.me/Premium_payment_pruf")]
        ])

def get_payment_methods_keyboard():
    if COLORFUL_BUTTONS:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🔴 বিকাশ (bKash)", callback_data="method_bkash"),
             InlineKeyboardButton("🟠 নগদ (Nagad)", callback_data="method_nagad")],
            [InlineKeyboardButton("🟣 রকেট (Rocket)", callback_data="method_rocket"),
             InlineKeyboardButton("🟡 উপায় (Upay)", callback_data="method_upay")],
            [InlineKeyboardButton("🔙 প্যাকেজে ফিরে যান", callback_data="back_to_pkg")]
        ])
    else:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🔴 বিকাশ (bKash)", callback_data="method_bkash"),
             InlineKeyboardButton("🟠 নগদ (Nagad)", callback_data="method_nagad")],
            [InlineKeyboardButton("🟣 রকেট (Rocket)", callback_data="method_rocket"),
             InlineKeyboardButton("🟡 উপায় (Upay)", callback_data="method_upay")],
            [InlineKeyboardButton("🔙 প্যাকেজে ফিরে যান", callback_data="back_to_pkg")]
        ])

# ================= অটো পোস্ট ও গ্লোবাল স্টেট কনফিগারেশন =================
AUTO_POST_CONFIG = {
    'running': False,
    'interval': 60,
    'media_type': 'text',
    'file_id': None,
    'caption': '',
    'total_sent': 0,
    'last_sent': None,
    'task': None
}

async def broadcast_vip_purchase(client: Client, user_name: str, pkg_name: str, ch_names: str):
    """বট ইউজারদের কাছে নতুন ভিআইপি মেম্বার যুক্ত হওয়ার অভিনন্দন নোটিফিকেশন পাঠানো (Zero Firestore Reads)"""
    try:
        msg = (
            "🎉 **নতুন ভিআইপি মেম্বার যুক্ত হয়েছেন!** 🌟\n\n"
            f"👤 অভিনন্দন **{user_name}**!\n"
            f"📦 তিনি সফলভাবে **{pkg_name}** ({ch_names}) এর Lifetime VIP এক্সেস নিয়েছেন। 🚀\n\n"
            "💎 আপনিও যেকোনো সময় সব ভিআইপি চ্যানেল আনলিমিটেড দেখতে নিচে ক্লিক করে এখনি প্রিমিয়াম কিনে নিন!"
        )
        btn = InlineKeyboardMarkup([[InlineKeyboardButton("💎 এখুনি প্রিমিয়াম কিনুন", callback_data="back_to_pkg")]])
        target_users = list(REGISTERED_USERS_SET)
        if not target_users and db:
            try:
                users = list(db.collection('users').stream())
                for u in users:
                    register_user_id(u.id)
                target_users = list(REGISTERED_USERS_SET)
            except: pass

        for uid_str in target_users:
            try:
                await client.send_message(int(uid_str), msg, reply_markup=btn)
                await asyncio.sleep(0.04)
            except: pass
    except Exception as e:
        print(f"Broadcast purchase error: {e}")

async def autopost_worker(client: Client):
    """ব্যাকগ্রাউন্ডে নির্দিষ্ট সময় পর পর সবার কাছে ছবি/ভিডিও/টেক্সট অটো পোস্ট পাঠানো (Zero Firestore Reads)"""
    while AUTO_POST_CONFIG.get('running', False):
        try:
            interval_mins = max(1, AUTO_POST_CONFIG.get('interval', 60))
            await asyncio.sleep(interval_mins * 60)
            if not AUTO_POST_CONFIG.get('running', False):
                break
                
            media_type = AUTO_POST_CONFIG.get('media_type', 'text')
            file_id = AUTO_POST_CONFIG.get('file_id')
            caption = AUTO_POST_CONFIG.get('caption', '')
            
            if not file_id and not caption:
                continue
                
            btn = InlineKeyboardMarkup([[InlineKeyboardButton("💎 এখুনি প্রিমিয়াম কিনুন", callback_data="back_to_pkg")]])
            
            target_users = list(REGISTERED_USERS_SET)
            if not target_users and db:
                try:
                    users = list(db.collection('users').stream())
                    for u in users:
                        register_user_id(u.id)
                    target_users = list(REGISTERED_USERS_SET)
                except: pass

            sent_ok = 0
            for uid_str in target_users:
                try:
                    uid = int(uid_str)
                    if media_type == 'photo':
                        await client.send_photo(uid, photo=file_id, caption=caption, reply_markup=btn)
                    elif media_type == 'video':
                        await client.send_video(uid, video=file_id, caption=caption, reply_markup=btn)
                    elif media_type == 'document':
                        await client.send_document(uid, document=file_id, caption=caption, reply_markup=btn)
                    elif media_type == 'animation':
                        await client.send_animation(uid, animation=file_id, caption=caption, reply_markup=btn)
                    else:
                        await client.send_message(uid, caption, reply_markup=btn)
                    sent_ok += 1
                    await asyncio.sleep(0.05)
                except: pass
                    
            AUTO_POST_CONFIG['total_sent'] = AUTO_POST_CONFIG.get('total_sent', 0) + 1
            AUTO_POST_CONFIG['last_sent'] = datetime.now().strftime('%d %b %Y, %I:%M %p')
            if db:
                try:
                    db.collection('config').document('autopost').set({
                        'total_sent': AUTO_POST_CONFIG['total_sent'],
                        'last_sent': AUTO_POST_CONFIG['last_sent']
                    }, merge=True)
                except: pass
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Autopost loop error: {e}")
            await asyncio.sleep(10)

def restart_autopost_worker(client: Client):
    old_task = AUTO_POST_CONFIG.get('task')
    if old_task and not old_task.done():
        old_task.cancel()
    if AUTO_POST_CONFIG.get('running', False):
        new_task = asyncio.create_task(autopost_worker(client))
        AUTO_POST_CONFIG['task'] = new_task

def get_admin_keyboard():
    active_count = len(ACTIVE_TRIALS)
    color_status = "🟢 চালু" if COLORFUL_BUTTONS else "⚪ বন্ধ"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"⏱️ রানিং ট্রায়াল ({active_count} জন)", callback_data="admin_active_trials"),
         InlineKeyboardButton("🧪 কিক ও চ্যানেল টেস্ট", callback_data="admin_test_kick_menu")],
        [InlineKeyboardButton("📊 বট স্ট্যাটাস", callback_data="admin_stats"),
         InlineKeyboardButton("👑 প্রিমিয়াম লিস্ট", callback_data="admin_premium_list")],
        [InlineKeyboardButton("➕ ম্যানুয়াল প্রিমিয়াম", callback_data="admin_manual_prem"),
         InlineKeyboardButton("🚫 প্রিমিয়াম রিমুভ", callback_data="admin_remove_prem")],
        [InlineKeyboardButton("🔄 সব ট্রায়াল রিসেট", callback_data="admin_reset_trials_menu"),
         InlineKeyboardButton("💰 প্রাইস পরিবর্তন", callback_data="admin_change_price")],
        [InlineKeyboardButton("📢 ফুল ব্রডকাস্ট", callback_data="admin_broadcast"),
         InlineKeyboardButton("👤 নির্দিষ্ট ব্রডকাস্ট", callback_data="admin_specific_cast")],
        [InlineKeyboardButton("⏰ অটো পোস্ট (Auto Post)", callback_data="admin_autopost"),
         InlineKeyboardButton("🔗 স্পেশাল লিংক", callback_data="admin_special_link")],
        [InlineKeyboardButton("🔎 ফরোয়ার্ড আইডি বের করুন", callback_data="admin_extract_id"),
         InlineKeyboardButton("🛡️ ফায়ারবেস কোটা শিল্ড", callback_data="admin_quota_shield")],
        [InlineKeyboardButton("👋 ওয়েলকাম মেসেজ সেটিংস", callback_data="admin_welcome_menu"),
         InlineKeyboardButton("📖 কিভাবে কিনবেন সেটিংস", callback_data="admin_howtobuy_menu")],
        [InlineKeyboardButton(f"🌈 বাটন কালার স্টাইল ({color_status})", callback_data="admin_toggle_colors"),
         InlineKeyboardButton("📦 সম্পূর্ণ ডাটা ব্যাকআপ", callback_data="admin_full_backup")]
    ])

async def render_manual_prem_selection(message: Message, uid: str, edit: bool = False):
    state = admin_state.get(ADMIN_ID, {})
    selected = state.get("selected", [])
    
    buttons = []
    for k in ["1", "2", "3", "4"]:
        v = CHANNEL_NAMES.get(k, f"চ্যানেল {k}")
        mark = "✅" if k in selected else "⬜"
        text = f"{mark} {k}. {v}"
        buttons.append([InlineKeyboardButton(text, callback_data=f"mpstoggle_{uid}_{k}")])
    
    buttons.append([InlineKeyboardButton("📦 সবগুলো চ্যানেল (All)", callback_data=f"mpstoggle_{uid}_all")])
    buttons.append([InlineKeyboardButton("✅ কনফার্ম করুন", callback_data=f"mpsconfirm_{uid}")])
    buttons.append([InlineKeyboardButton("❌ বাতিল", callback_data="admin_back")])
    
    text_msg = (
        f"➕ **ম্যানুয়াল প্রিমিয়াম নির্বাচন:**\n\n"
        f"👤 **User ID:** `{uid}`\n\n"
        "যাকে প্রিমিয়াম দিবেন তার জন্য চ্যানেল সিলেক্ট করুন (1-2-3-4) এবং 'কনফার্ম করুন' চাপুন:\n\n"
        "💡 কনফার্ম করলেই তৈরি হওয়া জয়েন লিংক স্বয়ংক্রিয়ভাবে ইউজারের ইনবক্সে পৌঁছে যাবে এবং সে জয়েন রিকোয়েস্ট দিলে অটো এপ্রুভ হবে।"
    )
    
    if edit:
        await message.edit_text(text_msg, reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await message.reply_text(text_msg, reply_markup=InlineKeyboardMarkup(buttons))

async def render_remprem_selection(message: Message, uid: str, edit: bool = False):
    state = admin_state.get(ADMIN_ID, {})
    selected = state.get("selected", [])
    
    user_data = get_cached_user(str(uid))
    prem_dict = user_data.get('premium_channels', {})
    
    active_names = []
    for k in ["1", "2", "3", "4"]:
        if k in prem_dict and prem_dict[k].get('status') == 'ACTIVE':
            active_names.append(f"• {k}. {CHANNEL_NAMES.get(k, f'চ্যানেল {k}')}")
            
    active_str = "\n".join(active_names) if active_names else "⚠️ ডাটাবেজে কোনো একটিভ প্রিমিয়াম রেকর্ড নেই (তবে জোরপূর্বক কিক করতে পারেন)"
    
    buttons = []
    for k in ["1", "2", "3", "4"]:
        v = CHANNEL_NAMES.get(k, f"চ্যানেল {k}")
        mark = "🔴" if k in selected else "⬜"
        is_active = " [ACTIVE]" if (k in prem_dict and prem_dict[k].get('status') == 'ACTIVE') else ""
        text = f"{mark} {k}. {v}{is_active}"
        buttons.append([InlineKeyboardButton(text, callback_data=f"rempremtoggle_{uid}_{k}")])
        
    buttons.append([InlineKeyboardButton("📦 সবগুলো রিমুভ (All)", callback_data=f"rempremtoggle_{uid}_all")])
    buttons.append([InlineKeyboardButton("🚫 কনফার্ম রিমুভ", callback_data=f"confirmrem_{uid}")])
    buttons.append([InlineKeyboardButton("🔙 অ্যাডমিন প্যানেল", callback_data="admin_back")])
    
    text_msg = (
        f"🚫 **প্রিমিয়াম রিমুভ কন্ট্রোল:**\n\n"
        f"👤 **User ID:** `{uid}`\n"
        f"📛 **নাম:** {user_data.get('name', 'N/A')}\n\n"
        f"📺 **বর্তমানে যেগুলোতে যুক্ত আছে:**\n{active_str}\n\n"
        "👉 যে চ্যানেল(গুলো) থেকে রিমুভ করতে চান তা সিলেক্ট করুন (1-2-3-4) এবং 'কনফার্ম রিমুভ' চাপুন। ইউজারের কাছে রিমুভ মেসেজ চলে যাবে এবং চ্যানেল থেকে কিক করা হবে।"
    )
    if edit:
        await message.edit_text(text_msg, reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await message.reply_text(text_msg, reply_markup=InlineKeyboardMarkup(buttons))

async def render_special_link_selection(message: Message, uid: str, edit: bool = False):
    state = admin_state.get(ADMIN_ID, {})
    selected = state.get("selected", [])
    if isinstance(selected, str):
        selected = [selected] if selected else []
    state["selected"] = selected
    
    buttons = []
    for k in ["1", "2", "3", "4"]:
        v = CHANNEL_NAMES.get(k, f"চ্যানেল {k}")
        mark = "✅" if k in selected else "⬜"
        text = f"{mark} {k}. {v}"
        buttons.append([InlineKeyboardButton(text, callback_data=f"splinktoggle_{uid}_{k}")])
    
    buttons.append([InlineKeyboardButton("📦 সবগুলো চ্যানেল (All)", callback_data=f"splinktoggle_{uid}_all")])
    buttons.append([InlineKeyboardButton("✅ কনফার্ম স্পেশাল লিংক", callback_data=f"splinkconfirm_{uid}")])
    buttons.append([InlineKeyboardButton("🔙 অ্যাডমিন প্যানেল", callback_data="admin_back")])
    
    text_msg = (
        f"🔗 **স্পেশাল লিংক নির্বাচন:**\n\n"
        f"👤 **User ID:** `{uid}`\n\n"
        "যেসব চ্যানেলের জন্য স্পেশাল লিংক তৈরি করতে চান তা নির্বাচন করুন (1-2-3-4) এবং 'কনফার্ম স্পেশাল লিংক' চাপুন:\n\n"
        "💡 কনফার্ম করার পর স্পেশাল লিংক অ্যাডমিনকে প্রদান করা হবে। অ্যাডমিন লিংকটি ইউজারকে দিলে ইউজার জয়েন রিকোয়েস্ট দেওয়া মাত্রই বট সাথে সাথে অটো এপ্রুভ করে স্বাগতম মেসেজ পাঠিয়ে দিবে।"
    )
    
    if edit:
        await message.edit_text(text_msg, reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await message.reply_text(text_msg, reply_markup=InlineKeyboardMarkup(buttons))

async def render_trial_reset_menu(message: Message, edit: bool = False):
    state = admin_state.get(ADMIN_ID, {})
    selected = state.get("selected", [])
    counts = state.get("counts", {})
    
    buttons = []
    for k in ["1", "2", "3", "4"]:
        c_name = CHANNEL_NAMES.get(k, f"চ্যানেল {k}")
        cnt = counts.get(k, 0)
        mark = "✅" if k in selected else "⬜"
        buttons.append([InlineKeyboardButton(f"{mark} {k}. {c_name} ({cnt} জন ট্রায়াল নিয়েছে)", callback_data=f"rstoggle_{k}")])
    
    buttons.append([InlineKeyboardButton("📦 সবগুলো চ্যানেল (All)", callback_data="rstoggle_all")])
    buttons.append([InlineKeyboardButton("🔄 কনফার্ম রিসেট (Reset Selected)", callback_data="rsconfirm")])
    buttons.append([InlineKeyboardButton("🔙 অ্যাডমিন প্যানেল", callback_data="admin_back")])
    
    total_in_trials = sum(counts.values())
    text = (
        "🔄 **ট্রায়াল রিসেট কন্ট্রোল (Channel-wise Fast Reset):**\n\n"
        "৪টি চ্যানেলের বর্তমান ট্রায়াল হিস্ট্রি নিচে দেওয়া হলো। যেকোনো চ্যানেল সিলেক্ট করুন (1-2-3-4) এবং কনফার্ম করুন:\n\n"
        f"📊 মোট রেকর্ডকৃত ট্রায়াল এন্ট্রি: **{total_in_trials}** টি\n\n"
        "⚡️ রিসেট করলে পূর্বে ট্রায়াল নেওয়া সবাই আবার নতুন করে ৫ মিনিট ফ্রি ট্রায়াল জয়েন করতে পারবে।"
    )
    if edit:
        await message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))

async def render_autopost_dashboard(message: Message, edit: bool = False):
    is_running = AUTO_POST_CONFIG.get('running', False)
    status_str = "🟢 চালু (Running)" if is_running else "🔴 বন্ধ (Stopped)"
    interval_mins = AUTO_POST_CONFIG.get('interval', 60)
    media_type = AUTO_POST_CONFIG.get('media_type', 'text')
    caption = AUTO_POST_CONFIG.get('caption', '')
    prev = (caption[:90] + "...") if len(caption) > 90 else (caption if caption else "কোনো টেক্সট সেট করা নেই")
    total_sent = AUTO_POST_CONFIG.get('total_sent', 0)
    last_sent = AUTO_POST_CONFIG.get('last_sent') or "এখনো পাঠানো হয়নি"
    
    text = (
        "⏰ **স্বয়ংক্রিয় অটো পোস্ট কন্ট্রোল (Auto Post System):**\n\n"
        f"📊 স্ট্যাটাস: **{status_str}**\n"
        f"⏳ বিরতি (Interval): প্রতি **{interval_mins} মিনিট** পর পর\n"
        f"📁 মিডিয়ার ধরন: **{media_type.upper()}**\n"
        f"📝 মেসেজ প্রিভিউ:\n_{prev}_\n\n"
        f"🚀 মোট ব্রডকাস্ট হয়েছে: **{total_sent}** বার\n"
        f"⏰ সর্বশেষ রান: **{last_sent}**"
    )
    
    toggle_btn_text = "⏹️ অটো পোস্ট বন্ধ করুন" if is_running else "▶️ অটো পোস্ট চালু করুন"
    buttons = [
        [InlineKeyboardButton("➕ নতুন অটো পোস্ট সেট করুন", callback_data="autopost_setup")],
        [InlineKeyboardButton(toggle_btn_text, callback_data="autopost_toggle")],
        [InlineKeyboardButton("⚡️ এখনই একটি টেস্ট পাঠান", callback_data="autopost_test_broadcast"),
         InlineKeyboardButton("🗑️ অটো পোস্ট মুছুন", callback_data="autopost_delete")],
        [InlineKeyboardButton("🔙 অ্যাডমিন প্যানেল", callback_data="admin_back")]
    ]
    if edit:
        await message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))

# ================= ৪. স্টার্ট ও রেফারেল কমান্ড =================
@app.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    user_id = str(message.from_user.id)
    register_user_id(user_id)
    
    fn = message.from_user.first_name or ""
    ln = message.from_user.last_name or ""
    full_name = f"{fn} {ln}".strip() or fn or "VIP User"
    username = message.from_user.username
    
    cached_u = get_cached_user(user_id)
    is_new_user = not cached_u
    
    if is_new_user:
        user_data = {
            'name': full_name, 
            'username': username,
            'trial_channels': [], 
            'premium_channels': {}, 
            'tokens': 0,
            'total_tokens_earned': 0,
            'referrals': 0,
            'join_date': datetime.now().isoformat()
        }
        
        if len(message.command) > 1:
            referrer_id = message.command[1]
            if referrer_id != user_id:
                user_data['referred_by'] = referrer_id
                try:
                    ref_data = get_cached_user(referrer_id)
                    if ref_data:
                        update_cached_user(referrer_id, {
                            'tokens': ref_data.get('tokens', 0) + 50,
                            'total_tokens_earned': ref_data.get('total_tokens_earned', 0) + 50,
                            'referrals': ref_data.get('referrals', 0) + 1
                        })
                        masked_id = user_id[:5] + "*****"
                        await client.send_message(
                            int(referrer_id), 
                            f"🎉 **আপনার Referral থেকে একজন নতুন User বটে প্রবেশ করেছে!**\n\n👤 User ID: `{masked_id}`\n🎁 আপনি পেয়েছেন: +50 Tokens"
                        )
                except Exception:
                    pass
                    
        update_cached_user(user_id, user_data)
    else:
        update_cached_user(user_id, {'name': full_name, 'username': username})

    custom_text = WELCOME_CONFIG.get('text') or DEFAULT_WELCOME_TEXT
    welcome_text = custom_text.replace("{name}", message.from_user.first_name or "User")
    media_id = WELCOME_CONFIG.get('file_id')
    media_type = WELCOME_CONFIG.get('media_type')

    if media_id and media_type == 'photo':
        await message.reply_photo(photo=media_id, caption=welcome_text, reply_markup=get_main_keyboard())
    elif media_id and media_type == 'video':
        await message.reply_video(video=media_id, caption=welcome_text, reply_markup=get_main_keyboard())
    else:
        await message.reply_text(welcome_text, reply_markup=get_main_keyboard())

# ================= ৫. প্রোফাইল, FAQ, টোকেন ও রিডিম =================
@app.on_callback_query(filters.regex("^(my_account|faq|referral_menu|redeem_life|daily_bonus|how_to_buy)$"))
async def handle_extra_menus(client: Client, callback: CallbackQuery):
    user_id = str(callback.from_user.id)
    user_data = get_cached_user(user_id)
    
    if callback.data == "how_to_buy":
        guide_text = HOW_TO_BUY_CONFIG.get('text') or DEFAULT_HOW_TO_BUY_TEXT
        media_id = HOW_TO_BUY_CONFIG.get('file_id')
        media_type = HOW_TO_BUY_CONFIG.get('media_type')

        buttons = [
            [InlineKeyboardButton("💎 এখুনি প্রিমিয়াম কিনুন", callback_data="back_to_pkg")],
            [InlineKeyboardButton("👨‍💻 লাইভ সাপোর্ট", url="https://t.me/ItsSaddam9"),
             InlineKeyboardButton("🔙 মেনুতে ফিরে যান", callback_data="back_to_main")]
        ]
        if media_id and media_type in ['photo', 'video']:
            try:
                await callback.message.delete()
            except: pass
            if media_type == 'photo':
                await client.send_photo(callback.from_user.id, photo=media_id, caption=guide_text, reply_markup=InlineKeyboardMarkup(buttons))
            else:
                await client.send_video(callback.from_user.id, video=media_id, caption=guide_text, reply_markup=InlineKeyboardMarkup(buttons))
        else:
            await callback.message.edit_text(guide_text, reply_markup=InlineKeyboardMarkup(buttons))

    elif callback.data == "my_account":
        trials = len(user_data.get('trial_channels', []))
        prem_channels = user_data.get('premium_channels', {})
        status = "🌟 ভিআইপি মেম্বার" if prem_channels else "সাধারণ ইউজার"
        
        text = (
            "👤 **আপনার একাউন্ট ডিটেইলস:**\n\n"
            f"📛 নাম: {callback.from_user.first_name}\n"
            f"🆔 আইডি: `{user_id}`\n"
            f"📊 ট্রায়াল নিয়েছেন: {trials} টি চ্যানেলে\n"
            f"💎 স্ট্যাটাস: **{status}**\n\n"
            f"💰 টোকেন ব্যালেন্স: **{user_data.get('tokens', 0)}**"
        )
        
        active_channels = [v['channel_name'] for k, v in prem_channels.items() if v.get('status') == 'ACTIVE']
        if active_channels:
            ch_list_text = "\n".join([f"🔹 {ch}" for ch in active_channels])
            text += f"\n\n📺 **আপনার প্রিমিয়াম চ্যানেলসমূহ (Lifetime):**\n{ch_list_text}"
            
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 মেনুতে ফিরে যান", callback_data="back_to_main")]]))
    
    elif callback.data == "referral_menu" or callback.data == "daily_bonus":
        if callback.data == "daily_bonus":
            today = datetime.now().strftime('%Y-%m-%d')
            if user_data.get('last_bonus_date') == today:
                await callback.answer("❌ আপনি আজকের বোনাস আগেই নিয়ে নিয়েছেন! আগামীকাল আবার চেষ্টা করুন।", show_alert=True)
            else:
                new_tokens = user_data.get('tokens', 0) + 10
                new_total = user_data.get('total_tokens_earned', 0) + 10
                update_cached_user(user_id, {
                    'tokens': new_tokens,
                    'total_tokens_earned': new_total,
                    'last_bonus_date': today
                })
                user_data['tokens'] = new_tokens
                await callback.answer("🎉 অভিনন্দন! আপনি আজকের ডেইলি বোনাস হিসেবে 10 টোকেন পেয়েছেন।", show_alert=True)

        bot_info = await client.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
        tokens = user_data.get('tokens', 0)
        total_ref = user_data.get('referrals', 0)
        
        text = (
            "👥 **রেফার ও টোকেন সিস্টেম:**\n\n"
            "আপনার Referral Link অন্যদের সাথে শেয়ার করুন। আপনার link ব্যবহার করে কেউ প্রবেশ করলে আপনি **50 Tokens** পাবেন।\n\n"
            f"🔗 **আপনার রেফার লিংক:**\n`{ref_link}`\n\n"
            f"👥 মোট রেফার করেছেন: **{total_ref}** জন\n"
            f"💰 বর্তমান টোকেন: **{tokens}**\n\n"
            "**টোকেন দিয়ে কী পাবেন?**\n"
            "• 5000 Tokens = Lifetime Premium"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎁 ডেইলি বোনাস (10 টোকেন)", callback_data="daily_bonus")],
            [InlineKeyboardButton("♾️ Redeem 5000 Tokens (Lifetime)", callback_data="redeem_life")],
            [InlineKeyboardButton("🔙 ব্যাক", callback_data="back_to_main")]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard)

    elif callback.data == "redeem_life":
        tokens = user_data.get('tokens', 0)
        req_tokens = 5000
        dur_text = "Lifetime"
        
        if tokens < req_tokens:
            return await callback.answer(f"❌ আপনার পর্যাপ্ত টোকেন নেই! আপনার আছে {tokens} টোকেন।", show_alert=True)
            
        admin_state[int(user_id)] = {"action": "redeem_select", "cost": req_tokens, "duration": dur_text}
        
        buttons = []
        for ch_key, ch_name in CHANNEL_NAMES.items():
            buttons.append([InlineKeyboardButton(f"📺 {ch_name}", callback_data=f"rdmch_{ch_key}")])
        buttons.append([InlineKeyboardButton("❌ ক্যানসেল", callback_data="referral_menu")])
        
        await callback.message.edit_text("📺 **কোন চ্যানেলের প্রিমিয়াম নিতে চান তা নির্বাচন করুন:**", reply_markup=InlineKeyboardMarkup(buttons))

    elif callback.data == "faq":
        text = (
            "❓ **সাধারণ জিজ্ঞাসা ও সাহায্য (FAQ):**\n\n"
            "**১. অটো পেমেন্ট কিভাবে কাজ করে?**\n"
            "উঃ প্যাকেজ ও পেমেন্ট মেথড সিলেক্ট করে নির্ধারিত নাম্বারে Send Money করুন। এরপর TrxID পাঠালেই সিস্টেম সেকেন্ডের মধ্যে ভেরিফাই করে চ্যানেলের জয়েন লিংক দিয়ে দিবে!\n\n"
            f"**২. ফ্রি ট্রায়াল কিভাবে কাজ করে?**\n"
            f"উঃ চ্যানেলে জয়েন রিকোয়েস্ট দিলে সাথে সাথে {TRIAL_MINUTES} মিনিটের জন্য অটো এপ্রুভ হয়ে যাবে। {TRIAL_MINUTES} মিনিট পর বট স্বয়ংক্রিয়ভাবে আপনাকে রিমুভ করে দিবে।\n\n"
            "**৩. টাকার পরিমাণ কি নিজের মতো দেওয়া যাবে?**\n"
            "উঃ না! বাটনে নির্ধারিত মূল্যই পাঠাতে হবে। কম বা বেশি পাঠালে সিস্টেম গ্রহণ করবে না।"
        )
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 মেনুতে ফিরে যান", callback_data="back_to_main")]]))

@app.on_callback_query(filters.regex("^rdmch_"))
async def handle_redeem_channel(client: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    ch_key = callback.data.split("_")[1]
    state = admin_state.get(user_id)
    
    if not state or state.get("action") != "redeem_select":
        return await callback.answer("Session expired!", show_alert=True)
        
    cost = state["cost"]
    dur_text = state["duration"]
    chat_id = CHANNELS[ch_key]
    ch_name = CHANNEL_NAMES[ch_key]
    
    try:
        user_data = get_cached_user(str(user_id))
        new_tokens = max(0, user_data.get('tokens', 0) - cost)
        prem_dict = user_data.get('premium_channels', {})
        prem_dict[ch_key] = {
            'status': 'ACTIVE',
            'type': 'LIFETIME',
            'start_date': datetime.now().isoformat(),
            'expiry_date': None,
            'channel_name': ch_name
        }
        update_cached_user(str(user_id), {'tokens': new_tokens, 'premium_channels': prem_dict})
        
        invite_link = await client.create_chat_invite_link(chat_id=chat_id, creates_join_request=True, name=f"RDM_{user_id}")
        
        text = (
            f"🎉 **টোকেন রিডিম সফল হয়েছে!**\n\n"
            f"আপনি **{ch_name}** এর **{dur_text}** প্রিমিয়াম এক্সেস পেয়েছেন।\n"
            f"নিচের লিংকে ক্লিক করে Join Request দিন, বট আপনাকে অটোমেটিক এপ্রুভ করে নিবে:\n\n"
            f"🔗 {invite_link.invite_link}"
        )
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 মেনুতে ফিরে যান", callback_data="back_to_main")]]))
        admin_state.pop(user_id, None)
        
    except Exception as e:
        await callback.answer(f"Error: {e}", show_alert=True)

# ================= ৬. প্যাকেজ নির্বাচন ও মেথড সিলেকশন =================
@app.on_callback_query(filters.regex("^(pkg|back_to_pkg|back_to_main)"))
async def handle_main_packages(client: Client, callback: CallbackQuery):
    if callback.data == "back_to_main":
        waiting_for_payment.pop(callback.from_user.id, None)
        user_selections.pop(callback.from_user.id, None)
        try:
            await callback.message.delete()
        except: pass
        custom_text = WELCOME_CONFIG.get('text') or DEFAULT_WELCOME_TEXT
        welcome_text = custom_text.replace("{name}", callback.from_user.first_name or "User")
        media_id = WELCOME_CONFIG.get('file_id')
        media_type = WELCOME_CONFIG.get('media_type')

        if media_id and media_type == 'photo':
            return await client.send_photo(callback.from_user.id, photo=media_id, caption=welcome_text, reply_markup=get_main_keyboard())
        elif media_id and media_type == 'video':
            return await client.send_video(callback.from_user.id, video=media_id, caption=welcome_text, reply_markup=get_main_keyboard())
        else:
            return await client.send_message(callback.from_user.id, welcome_text, reply_markup=get_main_keyboard())
        
    if callback.data == "back_to_pkg":
        pkg_prompt = "👇 **যেকোনো একটি প্যাকেজ নির্বাচন করুন:**"
        try:
            return await callback.message.edit_text(pkg_prompt, reply_markup=get_main_keyboard())
        except Exception:
            try:
                await callback.message.delete()
            except: pass
            return await client.send_message(callback.from_user.id, pkg_prompt, reply_markup=get_main_keyboard())

    pkg_num = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    fn = callback.from_user.first_name or ""
    ln = callback.from_user.last_name or ""
    full_name = f"{fn} {ln}".strip() or fn or "VIP User"
    uname = callback.from_user.username

    if pkg_num == 4:
        waiting_for_payment[user_id] = {
            'limit': 4,
            'selected': ['1', '2', '3', '4'],
            'amount': PRICES['all'],
            'pkg_name': "৪টি চ্যানেল (ফুল বান্ডেল)",
            'promo_applied': False,
            'user_name': full_name,
            'username': uname,
            'user_mention': callback.from_user.mention
        }
        update_cached_user(str(user_id), {'name': full_name, 'username': uname})
        await show_method_selection(callback.message, user_id)
    else:
        user_selections[user_id] = {'limit': pkg_num, 'selected': []}
        await render_channel_selection(callback.message, user_id)

async def render_channel_selection(message: Message, user_id: int):
    data = user_selections.get(user_id)
    if not data: return
    limit = data['limit']
    selected = data['selected']
    channel_icons = {
        "1": "👶",
        "2": "🎬",
        "3": "🔥",
        "4": "🌟"
    }
    buttons = []
    for i in range(1, 5):
        ch_str = str(i)
        c_name = CHANNEL_NAMES.get(ch_str, f"চ্যানেল {BN_NUMS.get(ch_str, ch_str)}")
        icon = channel_icons.get(ch_str, "📺")
        text = f"✅ {icon} {c_name}" if ch_str in selected else f"{icon} {c_name}"
        buttons.append(InlineKeyboardButton(text, callback_data=f"toggle_{i}"))
        
    keyboard = InlineKeyboardMarkup([
        [buttons[0]], [buttons[1]], [buttons[2]], [buttons[3]],
        [InlineKeyboardButton("🔙 ব্যাক", callback_data="back_to_pkg")]
    ])
    limit_text = BN_NUMS.get(str(limit), str(limit))
    await message.edit_text(f"📌 **যেকোনো {limit_text} টি চ্যানেল নির্বাচন করুন:**\n\n(যেগুলো নিতে চান তার উপর ক্লিক করুন)", reply_markup=keyboard)

@app.on_callback_query(filters.regex("^toggle_"))
async def handle_channel_toggle(client: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    ch_str = callback.data.split("_")[1]
    data = user_selections.get(user_id)
    if not data: return await callback.answer("সেশন এক্সপায়ার হয়েছে। আবার /start দিন।", show_alert=True)
        
    selected = data['selected']
    limit = data['limit']
    if ch_str in selected: selected.remove(ch_str) 
    else:
        if len(selected) < limit: selected.append(ch_str) 
            
    if len(selected) == limit:
        fn = callback.from_user.first_name or ""
        ln = callback.from_user.last_name or ""
        full_name = f"{fn} {ln}".strip() or fn or "VIP User"
        uname = callback.from_user.username
        total_price = sum([PRICES[ch] for ch in selected])
        waiting_for_payment[user_id] = {
            'limit': limit,
            'selected': selected.copy(),
            'amount': total_price,
            'pkg_name': f"{BN_NUMS.get(str(limit), str(limit))}টি চ্যানেল",
            'promo_applied': False,
            'user_name': full_name,
            'username': uname,
            'user_mention': callback.from_user.mention
        }
        update_cached_user(str(user_id), {'name': full_name, 'username': uname})
        del user_selections[user_id]
        await show_method_selection(callback.message, user_id)
    else:
        await render_channel_selection(callback.message, user_id)

async def show_method_selection(message: Message, user_id: int):
    data = waiting_for_payment.get(user_id)
    if not data: return
    
    if data['limit'] == 4:
        ch_names = "সবগুলো (৪টি চ্যানেল)"
    else:
        ch_names = ", ".join([CHANNEL_NAMES.get(x, f"চ্যানেল {BN_NUMS.get(x, x)}") for x in data['selected']])
        
    text = (
        f"🎯 **নির্বাচিত প্যাকেজ:** {data['pkg_name']}\n"
        f"📺 **চ্যানেলসমূহ:** {ch_names}\n"
        f"💰 **মোট প্রদেয় মূল্য:** **{data['amount']} ৳**\n\n"
        "💳 **পেমেন্ট করার মাধ্যম বেছে নিন:**\n"
        "আপনি কোন মাধ্যমে টাকা পাঠাতে চান তা নিচের বাটন থেকে সিলেক্ট করুন:"
    )
    await message.edit_text(text, reply_markup=get_payment_methods_keyboard())

# ================= ৭. পেমেন্ট মেথড বিবরণ প্রদর্শন =================
@app.on_callback_query(filters.regex("^method_"))
async def handle_payment_method(client: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    method = callback.data.split("_")[1]
    data = waiting_for_payment.get(user_id)
    if not data:
        return await callback.answer("সেশন এক্সপায়ার হয়েছে। আবার /start দিন।", show_alert=True)

    method_details = {
        "bkash": {
            "name": "বিকাশ (bKash)",
            "icon": "🔴",
            "guide": "বিকাশ অ্যাপে লগইন করুন অথবা *247# ডায়াল করে **Send Money** অপশন নির্বাচন করুন।"
        },
        "nagad": {
            "name": "নগদ (Nagad)",
            "icon": "🟠",
            "guide": "নগদ অ্যাপে লগইন করুন অথবা *167# ডায়াল করে **Send Money** অপশন নির্বাচন করুন।"
        },
        "rocket": {
            "name": "রকেট (Rocket)",
            "icon": "🟣",
            "guide": "রকেট অ্যাপে লগইন করুন অথবা *322# ডায়াল করে **Send Money** অপশন নির্বাচন করুন।"
        },
        "upay": {
            "name": "উপায় (Upay)",
            "icon": "🟡",
            "guide": "উপায় অ্যাপে লগইন করুন অথবা *268# ডায়াল করে **Send Money** অপশন নির্বাচন করুন।"
        }
    }
    
    m_info = method_details.get(method, method_details["bkash"])
    data['chosen_method'] = m_info['name']

    text = (
        f"{m_info['icon']} **{m_info['name']} পেমেন্ট নির্দেশিকা:**\n\n"
        f"📋 **ধাপসমূহ:**\n"
        f"১. আপনার {m_info['guide']}\n"
        f"২. প্রাপক নম্বরে এই পার্সোনাল নাম্বারটি দিন:\n"
        f"   👉 `{PAYMENT_NUMBER}` (Personal)\n\n"
        f"৩. টাকার পরিমাণ লিখুন:\n"
        f"   👉 **{data['amount']} ৳**\n\n"
        "⚠️ **কঠোর শর্তাবলী:**\n"
        f"• আপনাকে **অবশ্যই ঠিক {data['amount']} ৳** পাঠাতে হবে।\n"
        "• নির্ধারিত মূল্যের ১ টাকা কম দিলেও বাতিল হবে, বেশি দিলেও বাতিল হবে।\n\n"
        "৪. পিন কোড দিয়ে Send Money সম্পন্ন করুন।\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📥 **টাকা পাঠানোর পর কী করবেন?**\n"
        "টাকা পাঠানোর পর প্রাপ্ত **TrxID (ট্রানজেকশন আইডি)** টি এখানে লিখে মেসেজ করুন, **অথবা পেমেন্টের সম্পূর্ণ স্ক্রিনশট/ভিডিও** পাঠিয়ে দিন।\n\n"
        "⚡️ সিস্টেম স্বয়ংক্রিয়ভাবে সাথে সাথে ভেরিফাই করে চ্যানেলের জয়েন লিংক দিয়ে দিবে!"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 অন্য মাধ্যমে পেমেন্ট", callback_data="back_to_methods")],
        [InlineKeyboardButton("🔙 প্যাকেজ পরিবর্তন", callback_data="back_to_pkg")]
    ])
    await callback.message.edit_text(text, reply_markup=keyboard)

@app.on_callback_query(filters.regex("^back_to_methods$"))
async def back_to_methods(client: Client, callback: CallbackQuery):
    await show_method_selection(callback.message, callback.from_user.id)

# ================= ৮. মেসেজ রিসিভ ও তাৎক্ষণিক সঠিক কারণ জানানো =================
@app.on_message(filters.private & ~filters.bot & ~filters.user(ADMIN_ID))
async def handle_user_submission(client: Client, message: Message):
    user_id = message.from_user.id

    if user_id not in waiting_for_payment:
        return await message.reply_text("দয়া করে প্রথমে /start দিয়ে মেনু থেকে প্যাকেজ সিলেক্ট করুন।", reply_markup=get_main_keyboard())

    data = waiting_for_payment[user_id]
    
    fn = message.from_user.first_name or ""
    ln = message.from_user.last_name or ""
    full_name = f"{fn} {ln}".strip() or fn or "VIP User"
    uname = message.from_user.username
    data['user_name'] = full_name
    data['username'] = uname
    data['user_mention'] = message.from_user.mention
    update_cached_user(str(user_id), {'name': full_name, 'username': uname})
    
    user_text = ""
    photo_id = None
    media_type = "text"

    if message.photo:
        photo_id = message.photo.file_id
        media_type = "photo"
        user_text = message.caption.strip() if message.caption else "পেমেন্ট স্ক্রিনশট"
    elif message.video:
        photo_id = message.video.file_id
        media_type = "video"
        user_text = message.caption.strip() if message.caption else "পেমেন্ট ভিডিও"
    elif message.document:
        photo_id = message.document.file_id
        media_type = "document"
        user_text = message.caption.strip() if message.caption else "পেমেন্ট ফাইল"
    elif message.text:
        user_text = message.text.strip()

    if user_text.upper() == PROMO_CODE.upper():
        if not data['promo_applied']:
            data['amount'] = max(0, data['amount'] - PROMO_DISCOUNT)
            data['promo_applied'] = True
            return await message.reply_text(f"🎉 প্রোমো কোড সফলভাবে যুক্ত হয়েছে! নতুন নির্ধারিত মূল্য: **{data['amount']} ৳**\nএখন TrxID বা স্ক্রিনশট পাঠিয়ে দিন।")
        else:
            return await message.reply_text("⚠️ আপনি ইতিমধ্যে প্রোমো কোড ব্যবহার করেছেন।")

    trx_id = extract_trx_id(user_text)

    # ট্রানজেকশন তথ্য খোঁজা (১. ইন-মেমোরি ক্যাশ, ২. ফায়ারস্টোর)
    payment_info = received_sms_cache.get(trx_id)
    if not payment_info and db and len(trx_id) >= 6:
        try:
            doc = db.collection("sms_payments").document(trx_id).get()
            if doc.exists:
                payment_info = doc.to_dict()
                received_sms_cache[trx_id] = payment_info
        except Exception as e:
            print(f"Db read error: {e}")

    # ================= যদি ট্রানজেকশন পাওয়া যায় =================
    if payment_info:
        if payment_info.get("used") is True:
            return await message.reply_text(
                f"❌ **ভেরিফিকেশন ব্যর্থ!**\n\n"
                f"এই ট্রানজেকশন আইডি (`{trx_id}`) ইতিমধ্যে ব্যবহার করা হয়ে গেছে। একটি TrxID কেবল একবারই প্রযোজ্য।\n"
                "সঠিক নতুন TrxID দিন অথবা কোনো সমস্যা হলে লাইভ সাপোর্টে মেসেজ দিন।",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("👨‍💻 লাইভ সাপোর্ট", url="https://t.me/ItsSaddam9")]])
            )

        received_amount = float(payment_info.get("amount", 0))
        expected_amount = float(data["amount"])

        if received_amount < expected_amount:
            return await message.reply_text(
                f"❌ **টাকার পরিমাণ কম! ভেরিফিকেশন ব্যর্থ!**\n\n"
                f"📦 নির্বাচিত প্যাকেজের মূল্য: **{expected_amount} ৳**\n"
                f"💸 আপনি পাঠিয়েছেন: **{received_amount} ৳**\n\n"
                f"⚠️ নিয়মানুযায়ী নির্ধারিত মূল্যের চেয়ে কম টাকা পাঠানোয় সিস্টেম এটি গ্রহণ করেনি।"
            )

        if received_amount > expected_amount:
            return await message.reply_text(
                f"❌ **টাকার পরিমাণ বেশি! ভেরিফিকেশন ব্যর্থ!**\n\n"
                f"📦 নির্বাচিত প্যাকেজের মূল্য: **{expected_amount} ৳**\n"
                f"💸 আপনি পাঠিয়েছেন: **{received_amount} ৳**\n\n"
                f"⚠️ আপনি নির্ধারিত মূল্যের চেয়ে বেশি টাকা পাঠিয়েছেন। সিস্টেম শুধুমাত্র নির্দিষ্ট মূল্যের সাথে মিল রেখেই অটো এপ্রুভ করে। দয়া করে অ্যাডমিন সাপোর্টে যোগাযোগ করুন।"
            )

        payment_info["used"] = True
        if db:
            try:
                db.collection("sms_payments").document(trx_id).update({
                    "used": True,
                    "used_by": user_id,
                    "used_at": datetime.now().isoformat()
                })
            except Exception as e:
                print(f"Firestore update error: {e}")

        await process_success_approval(client, user_id, data, trx_id, is_auto=True)
        return

    # ================= যদি ট্রানজেকশন সিস্টেমে পাওয়া না যায় (বা স্ক্রিনশট দেয়) =================
    data['submitted_text'] = user_text
    data['media_id'] = photo_id
    data['media_type'] = media_type
    data['trx_id'] = trx_id
    data['user_name'] = message.from_user.first_name
    data['user_mention'] = message.from_user.mention
    pending_approvals[user_id] = data

    admin_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Approve (এপ্রুভ)", callback_data=f"approve_{user_id}"),
            InlineKeyboardButton("❌ Reject (বাতিল)", callback_data=f"reject_{user_id}")
        ],
        [InlineKeyboardButton("💬 ইউজারকে মেসেজ পাঠান", callback_data=f"reply_{user_id}")]
    ])

    ch_names = ", ".join([CHANNEL_NAMES.get(x, f"Ch {x}") for x in data['selected']])
    if data.get('limit') == 4: ch_names = "সবগুলো (৪টি চ্যানেল)"

    admin_caption = (
        "🔔 **নতুন পেমেন্ট রিকোয়েস্ট (Review Required)** 💰\n\n"
        f"👤 ইউজার: {message.from_user.mention} (`{user_id}`)\n"
        f"📦 প্যাকেজ: **{data['pkg_name']}** ({data['amount']} ৳)\n"
        f"💳 মাধ্যম: {data.get('chosen_method', 'বিকাশ/নগদ')}\n"
        f"🎯 চ্যানেল: {ch_names}\n"
        f"🧾 প্রাপ্ত TrxID: `{trx_id if trx_id else 'দেয়নি'}`\n"
        f"📝 ইউজারের মেসেজ:\n_{user_text}_\n\n"
        f"⚠️ স্ট্যাটাস: ট্রানজেকশন এখনো অ্যাপ/সিস্টেম থেকে সিঙ্ক হয়নি বা ম্যানুয়াল রিভিউ দরকার।"
    )

    try:
        if photo_id:
            if media_type == "photo":
                await client.send_photo(ADMIN_ID, photo=photo_id, caption=admin_caption, reply_markup=admin_keyboard)
            elif media_type == "video":
                await client.send_video(ADMIN_ID, video=photo_id, caption=admin_caption, reply_markup=admin_keyboard)
            else:
                await client.send_document(ADMIN_ID, document=photo_id, caption=admin_caption, reply_markup=admin_keyboard)
        else:
            await client.send_message(ADMIN_ID, admin_caption, reply_markup=admin_keyboard)
    except Exception as e:
        print(f"Error forwarding to admin: {e}")

    if trx_id:
        user_feedback = (
            f"⚠️ **ট্রানজেকশন আইডি (`{trx_id}`) এখনো সিস্টেমে আসেনি বা ভুল হয়েছে!**\n\n"
            f"• আপনি টাকা পাঠালে ৩০-৬০ সেকেন্ড অপেক্ষা করে আবার TrxID লিখে মেসেজ দিন।\n"
            f"• অথবা আপনার রিকোয়েস্টটি অ্যাডমিনের কাছে পাঠানো হয়েছে। অ্যাডমিন নিজে চেক করে এখনই এপ্রুভ করে দিবে।\n\n"
            "অনুগ্রহ করে একটু অপেক্ষা করুন... 🙏"
        )
    else:
        user_feedback = (
            "⏳ **আপনার পেমেন্ট স্ক্রিনশট/তথ্য অ্যাডমিনের কাছে পাঠানো হয়েছে!**\n\n"
            "অ্যাডমিন নিজে এটি দেখে এখনই ম্যানুয়ালি এপ্রুভ করে আপনাকে চ্যানেলের জয়েন লিংক পাঠিয়ে দিবে।\n\n"
            "অনুগ্রহ করে একটু অপেক্ষা করুন... 🙏"
        )

    await message.reply_text(user_feedback, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 মেনুতে ফিরে যান", callback_data="back_to_main")]]))

# ================= ৯. সফল পেমেন্ট ও প্রুফ পোস্ট প্রসেসর =================
async def process_success_approval(client: Client, user_id: int, data: dict, trx_id: str, is_auto: bool = False):
    try:
        links_text = ""
        u_cache = get_cached_user(str(user_id))
        prem_channels = u_cache.get('premium_channels', {})
        
        for ch_key in data['selected']:
            chat_id = CHANNELS[ch_key]
            ch_name = CHANNEL_NAMES.get(ch_key, f"চ্যানেল {BN_NUMS.get(ch_key, ch_key)}")
            
            prem_channels[ch_key] = {
                'status': 'ACTIVE',
                'type': 'LIFETIME',
                'start_date': datetime.now().isoformat(),
                'expiry_date': None,
                'channel_name': ch_name
            }
            
            invite_link = await client.create_chat_invite_link(
                chat_id=chat_id, 
                creates_join_request=True, 
                name=f"VIP_{user_id}"
            )
            links_text += f"🔹 **{ch_name}:** {invite_link.invite_link}\n\n"

        update_cached_user(str(user_id), {'premium_channels': prem_channels})

        user_success_msg = (
            "🎉 **অভিনন্দন! আপনার পেমেন্ট সফল হয়েছে!** 🎉\n\n"
            f"💰 পরিশোধিত টাকা: **{data['amount']} ৳**\n"
            f"🧾 ট্রানজেকশন আইডি: `{trx_id if trx_id else 'Approved'}`\n\n"
            "নিচের লিংকে ক্লিক করে প্রিমিয়াম চ্যানেলে **Join Request** দিন, বট আপনাকে সাথে সাথে অটোমেটিক Approve করে নিবে:\n\n"
            f"{links_text}"
            "⚠️ এই লিংক শুধু আপনার জন্য তৈরি করা হয়েছে।"
        )
        await client.send_message(user_id, user_success_msg)

        user_name = data.get('user_name')
        if not user_name or user_name == 'VIP User':
            u_cache = get_cached_user(str(user_id))
            if u_cache.get('name'):
                user_name = u_cache.get('name')
            else:
                try:
                    tg_u = await client.get_users(user_id)
                    fn = tg_u.first_name or ""
                    ln = tg_u.last_name or ""
                    user_name = f"{fn} {ln}".strip() or fn or "VIP User"
                    update_cached_user(str(user_id), {'name': user_name, 'username': tg_u.username})
                except:
                    user_name = "VIP Member"

        username_val = data.get('username')
        if not username_val:
            u_cache = get_cached_user(str(user_id))
            username_val = u_cache.get('username')
        username_str = f"@{username_val}" if username_val else "নেই (No Username)"

        ch_names = ", ".join([CHANNEL_NAMES.get(x, f"Ch {x}") for x in data['selected']])
        if data.get('limit') == 4: ch_names = "সবগুলো (৪টি চ্যানেল)"
        uid_str = str(user_id)
        masked_uid = f"{uid_str[:3]}***{uid_str[-2:]}" if len(uid_str) >= 6 else uid_str
        masked_trx = f"{trx_id[:4]}****{trx_id[-2:]}" if len(trx_id) >= 6 else (trx_id if trx_id else "Verified")
        method_used = data.get('chosen_method', 'বিকাশ (bKash)')
        bd_time = get_bd_time_str()

        if PROOF_CHANNEL_ID != 0:
            try:
                proof_caption = (
                    "🎉 **NEW VIP MEMBER PURCHASED!** 🌟\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    f"👤 **ক্রেতার নাম:** {user_name}\n"
                    f"🆔 **ইউজার আইডি:** `{masked_uid}`\n"
                    f"📦 **প্যাকেজ:** {data.get('pkg_name')}\n"
                    f"📺 **চ্যানেলসমূহ:** {ch_names}\n"
                    f"💳 **পেমেন্ট মাধ্যম:** {method_used}\n"
                    f"💵 **পরিশোধিত টাকা:** {data['amount']} ৳\n"
                    f"🧾 **TrxID:** `{masked_trx}`\n"
                    f"⏰ **সময় ও তারিখ:** {bd_time}\n"
                    f"💎 **মেয়াদ:** আজীবন (Lifetime VIP Access)\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    "✨ আপনিও এখনই ভিআইপি মেম্বার হয়ে আনলিমিটেড এক্সেস উপভোগ করুন!"
                )
                proof_btn = InlineKeyboardMarkup([[InlineKeyboardButton("💎 এখুনি প্রিমিয়াম কিনুন", url="https://t.me/PREMIUM_GROUP_BUY_BOT?start=start")]])

                media_id = data.get('media_id')
                media_type = data.get('media_type')

                if media_id and media_type == "photo":
                    await client.send_photo(PROOF_CHANNEL_ID, photo=media_id, caption=proof_caption, reply_markup=proof_btn)
                elif media_id and media_type == "video":
                    await client.send_video(PROOF_CHANNEL_ID, video=media_id, caption=proof_caption, reply_markup=proof_btn)
                else:
                    await client.send_message(PROOF_CHANNEL_ID, proof_caption, reply_markup=proof_btn)
            except Exception as e:
                print(f"Proof Channel Error: {e}")

        # বট ব্যবহারকারী সবার কাছে নোটিফিকেশন মেসেজ পাঠানো
        asyncio.create_task(broadcast_vip_purchase(client, user_name, data.get('pkg_name', 'VIP Package'), ch_names))

        if is_auto:
            try:
                admin_auto_msg = (
                    "⚡️ **অটো পেমেন্ট সফল হয়েছে!** 💰\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    f"👤 **নাম:** {user_name}\n"
                    f"🏷 **ইউজার নাম:** {username_str}\n"
                    f"🆔 **ইউজার আইডি:** `{user_id}`\n"
                    f"📦 **প্যাকেজ:** {data.get('pkg_name')}\n"
                    f"📺 **চ্যানেলসমূহ:** {ch_names}\n"
                    f"🧾 **TrxID:** `{trx_id}`\n"
                    f"💳 **সিলেক্ট মেথড:** {method_used}\n"
                    f"💵 **টাকা:** {data.get('amount')} ৳\n"
                    f"⏰ **সময় ও তারিখ:** {bd_time}\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    "✅ সিস্টেম স্বয়ংক্রিয়ভাবে ট্রানজেকশন যাচাই করে জয়েন লিংক প্রদান করেছে!"
                )
                await client.send_message(ADMIN_ID, admin_auto_msg)
            except Exception as e:
                print(f"Admin auto msg error: {e}")

        waiting_for_payment.pop(user_id, None)
        pending_approvals.pop(user_id, None)

    except Exception as e:
        traceback.print_exc()

# ================= ১০. অ্যাডমিন ভেরিফিকেশন কলব্যাক =================
@app.on_callback_query(filters.regex("^(approve|reject)_"))
async def admin_verification_callback(client: Client, callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("অনুমতি নেই!", show_alert=True)
        
    data_parts = callback.data.split("_")
    action = data_parts[0]
    user_id = int(data_parts[1])
    
    if user_id not in pending_approvals:
        return await callback.answer("ডাটা পাওয়া যায়নি বা আগেই সম্পন্ন হয়েছে!", show_alert=True)
        
    pkg_data = pending_approvals[user_id]
    trx_id = pkg_data.get('trx_id', '')

    if action == "approve":
        await process_success_approval(client, user_id, pkg_data, trx_id, is_auto=False)
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.reply_text("✅ **সফলভাবে Approve করা হয়েছে এবং ইউজারকে লিংক পাঠানো হয়েছে!**")
    elif action == "reject":
        try:
            reject_msg = (
                "❌ **আপনার পেমেন্ট রিকোয়েস্ট বাতিল করা হয়েছে!**\n\n"
                "সঠিক ট্রানজেকশন আইডি বা পেমেন্টের প্রমাণ দিন। কোনো সমস্যা হলে আমাদের লাইভ সাপোর্টে যোগাযোগ করুন।"
            )
            await client.send_message(user_id, reject_msg, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("👨‍💻 লাইভ সাপোর্ট", url="https://t.me/ItsSaddam9")]]))
        except: pass
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.reply_text("❌ **Request Rejected.**")
        pending_approvals.pop(user_id, None)
        waiting_for_payment.pop(user_id, None)

    await callback.answer()

# ================= ১১. ৫ মিনিট ট্রায়াল এক্সিকিউশন ও টাইমার ইঞ্জিন =================

async def execute_kick_user(user_id: int, chat_id: int, ch_name: str, reason: str = "TRIAL_EXPIRED"):
    """
    টেলিগ্রাম চ্যানেল থেকে ইউজারকে কিক করে এবং নোটিফিকেশন পাঠায়।
    কিক করতে ব্যর্থ হলে এডমিনকে তাৎক্ষণিক এলার্ট দেয়।
    """
    u_id = int(user_id)
    c_id = int(chat_id)
    trial_key = f"{u_id}_{c_id}"
    
    print(f"🚀 [Kick Process] User {u_id} from {ch_name} ({c_id}). Reason: {reason}")
    kicked_ok = False
    err_str = ""
    
    try:
        await app.ban_chat_member(c_id, u_id)
        await asyncio.sleep(1)
        await app.unban_chat_member(c_id, u_id)
        kicked_ok = True
        print(f"✅ [Kick Success] User {u_id} kicked from {ch_name} ({c_id})")
    except Exception as e:
        err_str = str(e)
        print(f"❌ [Kick Failed] User {u_id} in {c_id}: {err_str}")
        try:
            alert_text = (
                "⚠️ **[জরুরি সতর্কতা] ট্রায়াল ইউজারকে চ্যানেল থেকে রিমুভ করা যায়নি!**\n\n"
                f"👤 ইউজার: `{u_id}`\n"
                f"📺 চ্যানেল: **{ch_name}** (`{c_id}`)\n"
                f"❌ এরর বিবরণ: `{err_str}`\n\n"
                "💡 **সমাধান:**\n"
                "১. বটে ওই চ্যানেলে Admin হিসেবে **'Ban Users'** বা **'Restrict Members'** পারমিশন দেওয়া আছে কিনা চেক করুন।\n"
                "২. চ্যানেল সেটিংসে যান -> Administrators -> বটের উপর ক্লিক করে 'Ban Users' পারমিশন অন করে দিন।"
            )
            await app.send_message(ADMIN_ID, alert_text)
        except Exception:
            pass

    if reason == "TRIAL_EXPIRED":
        try:
            kick_notice = (
                f"⏳ **'{ch_name}' -এ আপনার {TRIAL_MINUTES} মিনিটের ফ্রি ট্রায়াল সময় শেষ হয়ে গেছে!** ⏳\n\n"
                "আপনাকে চ্যানেল থেকে রিমুভ করা হয়েছে। আশা করি আমাদের চ্যানেলের কন্টেন্ট আপনার পছন্দ হয়েছে! 🔥\n\n"
                "সারাজীবনের জন্য (Lifetime) প্রিমিয়াম অ্যাক্সেস পেতে নিচের বাটন থেকে পছন্দের প্যাকেজটি কিনে নিন:"
            )
            await app.send_message(u_id, kick_notice, reply_markup=get_main_keyboard())
        except Exception as e:
            print(f"Kick notice error for {u_id}: {e}")
    elif reason == "FORCE_KICK":
        try:
            await app.send_message(
                u_id,
                f"⚠️ আপনাকে অ্যাডমিন কর্তৃক **{ch_name}** চ্যানেল থেকে রিমুভ করা হয়েছে।\nসারাজীবনের জন্য যুক্ত হতে প্যাকেজ কিনুন:",
                reply_markup=get_main_keyboard()
            )
        except Exception:
            pass
    elif reason == "TEST_TRIAL":
        try:
            await app.send_message(
                u_id,
                f"🎉 **[টেস্ট সফল] ১ মিনিটের টেস্ট ট্রায়াল সফলভাবে সম্পন্ন হয়েছে!**\n\nবট সফলভাবে আপনাকে **{ch_name}** থেকে রিমুভ করেছে। অটো কিক সিস্টেম ১০০% কার্যকর রয়েছে!"
            )
        except Exception:
            pass

    trial_entry = ACTIVE_TRIALS.pop(trial_key, None)
    if trial_entry and trial_entry.get('task') and not trial_entry['task'].done():
        try: trial_entry['task'].cancel()
        except: pass
        
    if db:
        try:
            db.collection('active_trials').document(trial_key).delete()
        except Exception as e:
            print(f"Db trial delete error: {e}")

    return kicked_ok, err_str

async def schedule_trial_kick(user_id: int, chat_id: int, ch_name: str, delay_seconds: int, reason: str = "TRIAL_EXPIRED"):
    u_id = int(user_id)
    c_id = int(chat_id)
    trial_key = f"{u_id}_{c_id}"
    try:
        print(f"⏱️ [Trial Timer Active] {delay_seconds}s countdown for user {u_id} in {ch_name}")
        await asyncio.sleep(delay_seconds)
        if trial_key in ACTIVE_TRIALS:
            await execute_kick_user(u_id, c_id, ch_name, reason=reason)
    except asyncio.CancelledError:
        print(f"Timer cancelled for {trial_key}")
    except Exception as e:
        print(f"Timer error for {trial_key}: {e}")

async def load_and_resume_active_trials():
    """বট স্টার্টআপে ফায়ারস্টোর থেকে একবার রানিং ট্রায়ালগুলো পড়ে এনে টাইমার চালু করে বা কিক করে।"""
    if not db:
        return
    try:
        now_ts = int(time.time())
        docs = list(db.collection('active_trials').stream())
        print(f"🔄 Syncing {len(docs)} active trials from Firestore at startup...")
        
        for doc in docs:
            d = doc.to_dict()
            u_id = d.get('user_id')
            c_id = d.get('chat_id')
            c_name = d.get('ch_name', 'চ্যানেল')
            expire_at = d.get('expire_at', 0)
            u_name = d.get('user_name', 'User')
            
            if not u_id or not c_id:
                continue
                
            u_id = int(u_id)
            c_id = int(c_id)
            remaining = expire_at - now_ts
            trial_key = f"{u_id}_{c_id}"
            
            if remaining <= 0:
                print(f"⚡ Offline expired trial for user {u_id}. Kicking now...")
                asyncio.create_task(execute_kick_user(u_id, c_id, c_name, reason="TRIAL_EXPIRED"))
            else:
                print(f"⏱️ Resuming trial for user {u_id} in {c_name} with {remaining}s remaining...")
                task = asyncio.create_task(schedule_trial_kick(u_id, c_id, c_name, remaining, reason="TRIAL_EXPIRED"))
                ACTIVE_TRIALS[trial_key] = {
                    'user_id': u_id,
                    'chat_id': c_id,
                    'ch_name': c_name,
                    'user_name': u_name,
                    'expire_at': expire_at,
                    'task': task
                }
    except Exception as e:
        print(f"Error loading active trials at startup: {e}")

async def in_memory_trial_sweeper():
    """মেমোরি সেফটি লুপ - প্রতি ৩০ সেকেন্ডে মেমোরি চেক করে। ZERO Firestore Reads!"""
    while True:
        try:
            now_ts = int(time.time())
            expired = []
            for key, data in list(ACTIVE_TRIALS.items()):
                if now_ts >= data.get('expire_at', 0):
                    expired.append((key, data))
            
            for key, data in expired:
                u_id = data.get('user_id')
                c_id = data.get('chat_id')
                c_name = data.get('ch_name', 'চ্যানেল')
                print(f"🧹 Sweeper found expired trial in memory for {u_id}")
                await execute_kick_user(u_id, c_id, c_name, reason="TRIAL_EXPIRED")
        except Exception as e:
            print(f"Error in in_memory_trial_sweeper: {e}")
        await asyncio.sleep(30)

@app.on_chat_join_request() 
async def handle_join_request(client: Client, request: ChatJoinRequest):
    user_id = request.from_user.id
    chat_id = request.chat.id
    
    if chat_id not in TRIAL_CHANNELS:
        return 
        
    ch_key = next((k for k, v in CHANNELS.items() if v == chat_id), "0")
    ch_name = CHANNEL_NAMES.get(ch_key, f"চ্যানেল {BN_NUMS.get(ch_key, ch_key)}")
    
    user_data = get_cached_user(str(user_id))
    prem_channels = user_data.get('premium_channels', {})
    
    # ১. রিমুভড প্রিমিয়াম চেক
    if ch_key in prem_channels and prem_channels[ch_key].get('status') == 'REMOVED':
        await request.decline()
        try:
            await client.send_message(user_id, f"🚫 আপনাকে **{ch_name}** থেকে রিমুভ করা হয়েছে।")
        except: pass
        return
        
    # ২. একটিভ প্রিমিয়াম চেক
    if ch_key in prem_channels and prem_channels[ch_key].get('status') == 'ACTIVE':
        await request.approve()
        welcome_text = (
            f"🎉 **অভিনন্দন {request.from_user.first_name}!** 🎉\n\n"
            f"আপনার **{ch_name}** এর Lifetime VIP Access সফলভাবে Verify করা হয়েছে।"
        )
        try: await client.send_message(user_id, welcome_text)
        except: pass
        return

    # ৩. ট্রায়াল হিস্ট্রি চেক
    trial_channels = user_data.get('trial_channels', [])

    if str(chat_id) in trial_channels:
        await request.decline()
        try:
            msg = (
                f"❌ **আপনি ইতিমধ্যে '{ch_name}' -এ ৫ মিনিট ফ্রি ট্রায়াল নিয়েছেন!**\n\n"
                "সারাজীবনের জন্য আনলিমিটেড এক্সেস পেতে দয়া করে প্যাকেজ কিনে নিন।"
            )
            await client.send_message(user_id, msg, reply_markup=get_main_keyboard())
        except: pass
    else:
        # ১ম বার ট্রায়াল: জয়েন রিকোয়েস্ট অটো এপ্রুভ!
        await request.approve()
        
        trial_channels.append(str(chat_id))
        update_cached_user(str(user_id), {
            'trial_channels': trial_channels,
            'name': request.from_user.first_name,
            'username': request.from_user.username
        })
        
        duration_secs = TRIAL_MINUTES * 60
        expire_time = int(time.time()) + duration_secs
        trial_key = f"{user_id}_{chat_id}"
        
        if db:
            try:
                db.collection('active_trials').document(trial_key).set({
                    'user_id': user_id,
                    'chat_id': chat_id,
                    'ch_name': ch_name,
                    'expire_at': expire_time,
                    'user_name': request.from_user.first_name,
                    'started_at': int(time.time())
                })
            except Exception as e:
                print(f"Db save trial error: {e}")

        # মেমোরিতে সরাসরি ৫ মিনিটের কাউন্টডাউন টাস্ক চালু
        task = asyncio.create_task(schedule_trial_kick(user_id, chat_id, ch_name, duration_secs, reason="TRIAL_EXPIRED"))
        ACTIVE_TRIALS[trial_key] = {
            'user_id': user_id,
            'chat_id': chat_id,
            'ch_name': ch_name,
            'user_name': request.from_user.first_name,
            'expire_at': expire_time,
            'task': task
        }

        trial_welcome = (
            f"🎉 **অভিনন্দন {request.from_user.first_name}!** 🎉\n\n"
            f"আপনাকে **{ch_name}** চ্যানেলে **{TRIAL_MINUTES} মিনিটের ফ্রি ট্রায়াল** এপ্রুভ করা হয়েছে! 🔓\n\n"
            f"⏳ **ট্রায়াল সময়সীমা:** ঠিক {TRIAL_MINUTES} মিনিট\n"
            f"⚠️ **সতর্কতা:** ৫ মিনিট শেষ হওয়া মাত্রই বট স্বয়ংক্রিয়ভাবে আপনাকে চ্যানেল থেকে রিমুভ করে দিবে।\n\n"
            f"📺 **চ্যানেল:** {ch_name}\n\n"
            "💎 সারাজীবনের জন্য (Lifetime) ফুল অ্যাক্সেস পেতে চাইলে নিচে বাটন থেকে প্যাকেজ কিনে নিন!"
        )
        try:
            await client.send_message(user_id, trial_welcome, reply_markup=get_main_keyboard())
        except: pass

# ================= ১২. অ্যাডমিন প্যানেল, টেস্ট ও ট্রায়াল রিসেট =================
@app.on_message(filters.command("admin") & filters.user(ADMIN_ID))
async def admin_panel(client: Client, message: Message):
    await message.reply_text("🛠 **অ্যাডমিন কন্ট্রোল প্যানেল**", reply_markup=get_admin_keyboard())

@app.on_callback_query(filters.regex("^(admin_|reply_|manrej_|changeprice_|remprem_|rempremtoggle_|confirmrem_|mpstoggle_|mpsconfirm_|splinktoggle_|splinkconfirm_|forcekick_|test_|rstoggle_|rsconfirm|autopost_|quick_|welcome_|howtobuy_)"))
async def admin_callbacks(client: Client, callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    data = callback.data
    
    if data == "admin_back":
        admin_state.pop(ADMIN_ID, None)
        await callback.message.edit_text("🛠 **অ্যাডমিন কন্ট্রোল প্যানেল**", reply_markup=get_admin_keyboard())

    # ১. লাইভ রানিং ট্রায়াল লিস্ট ও ইনস্ট্যান্ট ফোর্স কিক টেস্ট
    elif data == "admin_active_trials":
        if not ACTIVE_TRIALS:
            text = (
                "⏱️ **বর্তমানে কোনো রানিং ট্রায়াল নেই!**\n\n"
                "কোনো ইউজার চ্যানেলে জয়েন রিকোয়েস্ট দিলে সাথে সাথে এখানে লাইভ কাউন্টডাউন শুরু হবে।"
            )
            buttons = [
                [InlineKeyboardButton("⚡️ ১ মিনিটের টেস্ট ট্রায়াল শুরু করুন (নিজের একাউন্টে)", callback_data="test_quick_trial")],
                [InlineKeyboardButton("🔙 ব্যাক", callback_data="admin_back")]
            ]
            await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
        else:
            now_ts = int(time.time())
            text = f"⏱️ **বর্তমানে রানিং ট্রায়ালসমূহ ({len(ACTIVE_TRIALS)} জন):**\n\n"
            buttons = []
            for k, v in list(ACTIVE_TRIALS.items()):
                rem = max(0, v.get('expire_at', 0) - now_ts)
                mins = rem // 60
                secs = rem % 60
                u_name = v.get('user_name', 'User')
                u_id = v.get('user_id')
                c_id = v.get('chat_id')
                c_name = v.get('ch_name', 'চ্যানেল')
                
                text += f"👤 **{u_name}** (`{u_id}`)\n📺 {c_name}\n⏳ বাকি সময়: **{mins:02d} মি. {secs:02d} সে.**\n━━━━━━━━━━━━━━━━━━━━\n"
                buttons.append([InlineKeyboardButton(f"⚡️ কিক করুন: {u_name} ({mins}m {secs}s)", callback_data=f"forcekick_{u_id}_{c_id}")])
            
            buttons.append([InlineKeyboardButton("🔄 রিফ্রেশ (Refresh)", callback_data="admin_active_trials")])
            buttons.append([InlineKeyboardButton("🔙 ব্যাক", callback_data="admin_back")])
            await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("forcekick_"):
        parts = data.split("_")
        u_id = int(parts[1])
        c_id = int(parts[2])
        trial_key = f"{u_id}_{c_id}"
        ch_name = ACTIVE_TRIALS.get(trial_key, {}).get('ch_name', 'চ্যানেল')
        
        await callback.message.edit_text(f"⏳ User `{u_id}` কে {ch_name} থেকে কিক করা হচ্ছে...")
        ok, err = await execute_kick_user(u_id, c_id, ch_name, reason="FORCE_KICK")
        if ok:
            await callback.message.edit_text(
                f"✅ **User `{u_id}` কে {ch_name} থেকে সফলভাবে কিক করা হয়েছে!**\n\nইউজারের কাছে রিমুভ নোটিফিকেশন পৌঁছে গেছে।",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⏱️ রানিং ট্রায়াল লিস্ট", callback_data="admin_active_trials")], [InlineKeyboardButton("🔙 অ্যাডমিন প্যানেল", callback_data="admin_back")]])
            )
        else:
            await callback.message.edit_text(
                f"❌ **কিক করতে ব্যর্থ হয়েছে!**\n\nটেলিগ্রাম এরর: `{err}`\n\nবটের ওই চ্যানেলে 'Ban Users' পারমিশন অন আছে কিনা নিশ্চিত করুন।",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ব্যাক", callback_data="admin_active_trials")]])
            )

    # ২. কিক ও চ্যানেল টেস্ট মেনু
    elif data == "admin_test_kick_menu":
        text = (
            "🧪 **কিক ও চ্যানেল টেস্ট কন্ট্রোল:**\n\n"
            "বট ৫ মিনিট পর মেম্বারদের সঠিকভাবে বের করে দিতে পারছে কিনা তা পরীক্ষা করার টুলসমূহ:\n\n"
            "১. **চ্যানেল পারমিশন টেস্ট:** প্রতিটি চ্যানেলে বটের 'Ban Users' পারমিশন ঠিক আছে কিনা অটো-চেক করবে।\n"
            "২. **১ মিনিটের টেস্ট ট্রায়াল:** আপনার নিজের একাউন্টে ১ মিনিটের ট্রায়াল শুরু হবে এবং ঘড়ি ধরে ১ মিনিট পর বের করে দিয়ে নোটিফিকেশন পাঠাবে।\n"
            "৩. **ইউজার আইডি দিয়ে কিক টেস্ট:** যেকোনো ইউজার আইডি দিয়ে চ্যানেল থেকে বের করার টেস্ট করুন।"
        )
        buttons = [
            [InlineKeyboardButton("🔍 চ্যানেল পারমিশন টেস্ট (সব চ্যানেল)", callback_data="test_perm_all")],
            [InlineKeyboardButton("⚡️ ১ মিনিটের টেস্ট ট্রায়াল শুরু করুন", callback_data="test_quick_trial")],
            [InlineKeyboardButton("👤 ইউজার আইডি দিয়ে কিক টেস্ট", callback_data="test_kick_uid_input")],
            [InlineKeyboardButton("🔙 অ্যাডমিন প্যানেল", callback_data="admin_back")]
        ]
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

    elif data == "test_perm_all":
        await callback.message.edit_text("⏳ সব চ্যানেলের পারমিশন চেক করা হচ্ছে...")
        bot_self = await client.get_me()
        report = "🔍 **চ্যানেল পারমিশন রিপোর্ট:**\n\n"
        
        for k, c_id in CHANNELS.items():
            c_name = CHANNEL_NAMES.get(k, f"চ্যানেল {k}")
            if not c_id or c_id == 0:
                report += f"⚠️ **{c_name}:** Channel ID সেট করা নেই!\n\n"
                continue
            try:
                member = await client.get_chat_member(c_id, bot_self.id)
                if member.status.value in ["administrator", "owner"]:
                    privs = member.privileges
                    can_ban = privs.can_restrict_members if privs else False
                    if can_ban or member.status.value == "owner":
                        report += f"✅ **{c_name}:** পারমিশন ১০০% সঠিক আছে! (ইউজার কিক করতে পারবে)\n\n"
                    else:
                        report += f"❌ **{c_name}:** বট Admin কিন্তু **'Ban Users' (Restrict Members)** পারমিশন বন্ধ আছে! দয়া করে চ্যানেলে গিয়ে পারমিশন অন করুন।\n\n"
                else:
                    report += f"❌ **{c_name}:** বট অ্যাডমিন নয়! বটকে অ্যাডমিন বানান।\n\n"
            except Exception as e:
                report += f"❌ **{c_name}:** চেক করতে ব্যর্থ (`{str(e)}`)\n\n"
                
        buttons = [
            [InlineKeyboardButton("🔄 আবার চেক করুন", callback_data="test_perm_all")],
            [InlineKeyboardButton("🔙 টেস্ট মেনু", callback_data="admin_test_kick_menu")]
        ]
        await callback.message.edit_text(report, reply_markup=InlineKeyboardMarkup(buttons))

    elif data == "test_quick_trial":
        admin_uid = callback.from_user.id
        c_id = CHANNELS.get("1", 0)
        c_name = CHANNEL_NAMES.get("1", "চ্যানেল ১")
        if not c_id or c_id == 0:
            return await callback.answer("চ্যানেল ১ কনফিগার করা নেই!", show_alert=True)
            
        duration_secs = 60 # ১ মিনিট
        expire_time = int(time.time()) + duration_secs
        trial_key = f"{admin_uid}_{c_id}"
        
        task = asyncio.create_task(schedule_trial_kick(admin_uid, c_id, c_name, duration_secs, reason="TEST_TRIAL"))
        ACTIVE_TRIALS[trial_key] = {
            'user_id': admin_uid,
            'chat_id': c_id,
            'ch_name': c_name,
            'user_name': callback.from_user.first_name,
            'expire_at': expire_time,
            'task': task
        }
        
        try:
            ch_link = await client.create_chat_invite_link(chat_id=c_id, creates_join_request=False)
            link_str = ch_link.invite_link
        except:
            link_str = "চ্যানেল লিংক"
            
        text = (
            f"🧪 **১ মিনিটের টেস্ট ট্রায়াল শুরু হয়েছে!**\n\n"
            f"📺 চ্যানেল: **{c_name}**\n"
            f"⏳ সময়: **ঠিক ৬০ সেকেন্ড (১ মিনিট)**\n\n"
            f"🔗 জয়েন লিংক: {link_str}\n\n"
            "👉 ঠিক ৬০ সেকেন্ড পর বট স্বয়ংক্রিয়ভাবে আপনাকে চ্যানেল থেকে রিমুভ করে দিয়ে নোটিফিকেশন পাঠাবে। ঘড়ি ধরে লাইভ দেখুন!"
        )
        buttons = [
            [InlineKeyboardButton("⏱️ রানিং ট্রায়াল স্ট্যাটাস দেখুন", callback_data="admin_active_trials")],
            [InlineKeyboardButton("⚡️ এখনি ফোর্স কিক টেস্ট", callback_data=f"forcekick_{admin_uid}_{c_id}")],
            [InlineKeyboardButton("🔙 টেস্ট মেনু", callback_data="admin_test_kick_menu")]
        ]
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

    elif data == "test_kick_uid_input":
        admin_state[ADMIN_ID] = {"action": "test_kick_uid"}
        await callback.message.edit_text(
            "👤 **কিক টেস্ট করতে ইউজার আইডি দিন:**\n\nযে ইউজারকে চ্যানেল থেকে কিক করে টেস্ট করতে চান তার Telegram User ID লিখে পাঠান: (/cancel)",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ব্যাক", callback_data="admin_test_kick_menu")]])
        )

    # ৩. বট স্ট্যাটিস্টিকস
    elif data == "admin_stats":
        now = time.time()
        if STATS_CACHE['data'] and (now - STATS_CACHE['time'] < 60):
            stats = STATS_CACHE['data']
        else:
            total = 0
            prem = 0
            trial_history = 0
            if db:
                try:
                    users = list(db.collection('users').stream())
                    total = len(users)
                    for u in users:
                        d = u.to_dict()
                        if d.get('trial_channels'): trial_history += 1
                        p_chans = d.get('premium_channels', {})
                        if p_chans and any(v.get('status') == 'ACTIVE' for v in p_chans.values()):
                            prem += 1
                except Exception as e:
                    print(f"Stats db error: {e}")
            stats = {
                'total': total,
                'active_now': len(ACTIVE_TRIALS),
                'trial_history': trial_history,
                'prem': prem,
                'sms_count': len(received_sms_cache)
            }
            STATS_CACHE['data'] = stats
            STATS_CACHE['time'] = now
            
        text = (
            "📊 **বট স্ট্যাটিস্টিকস (Bot Statistics):**\n\n"
            f"👥 মোট ইউজার (Total Users): **{stats['total']}**\n"
            f"🟢 বর্তমানে রানিং ট্রায়াল (Live Active): **{stats['active_now']}** জন\n"
            f"⏱️ ট্রায়াল গ্রহণকারী (History): **{stats['trial_history']}** জন\n"
            f"👑 প্রিমিয়াম মেম্বার (Premium Users): **{stats['prem']}** জন\n"
            f"📥 সিঙ্কড পেমেন্ট SMS: **{stats['sms_count']}** টি\n\n"
            "💡 *Firebase Quota বাঁচাতে প্রতি ১ মিনিটে স্ট্যাটাস ক্যাশ আপডেট হয়।*"
        )
        buttons = [
            [InlineKeyboardButton("⏱️ রানিং ট্রায়াল লিস্ট", callback_data="admin_active_trials")],
            [InlineKeyboardButton("🔙 অ্যাডমিন প্যানেল", callback_data="admin_back")]
        ]
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

    # ৪. প্রিমিয়াম লিস্ট
    elif data.startswith("admin_premium_list"):
        parts = data.split("_")
        page = int(parts[4]) if (len(parts) >= 5 and parts[4].isdigit()) else 1
        
        prem_users = []
        if db:
            try:
                users = list(db.collection('users').stream())
                for u in users:
                    udata = u.to_dict()
                    p_chans = udata.get('premium_channels', {})
                    active_ch = [v.get('channel_name', CHANNEL_NAMES.get(k, f"Ch {k}")) for k, v in p_chans.items() if v.get('status') == 'ACTIVE']
                    if active_ch:
                        prem_users.append({
                            'id': u.id,
                            'name': udata.get('name', 'VIP User'),
                            'username': udata.get('username'),
                            'channels': active_ch
                        })
            except Exception as e:
                print(f"Db read error in prem list: {e}")
                
        total_prem = len(prem_users)
        if total_prem == 0:
            text = (
                "👑 **প্রিমিয়াম মেম্বারদের তালিকা:**\n\n"
                "বর্তমানে কোনো সক্রিয় প্রিমিয়াম মেম্বার নেই।"
            )
            buttons = [
                [InlineKeyboardButton("➕ ম্যানুয়াল প্রিমিয়াম দিন", callback_data="admin_manual_prem")],
                [InlineKeyboardButton("🔙 অ্যাডমিন প্যানেল", callback_data="admin_back")]
            ]
            await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
        else:
            page_size = 5
            total_pages = (total_prem + page_size - 1) // page_size
            page = max(1, min(page, total_pages))
            start_idx = (page - 1) * page_size
            page_items = prem_users[start_idx:start_idx + page_size]
            
            text = f"👑 **প্রিমিয়াম মেম্বারদের তালিকা (মোট {total_prem} জন) [পৃষ্ঠা {page}/{total_pages}]:**\n\n"
            for idx, pu in enumerate(page_items, start=start_idx + 1):
                u_id = pu['id']
                uname = f"(@{pu['username']})" if pu.get('username') else ""
                ch_str = ", ".join(pu['channels'])
                text += f"{idx}. 👤 **{pu['name']}** {uname}\n   🆔 ID: `{u_id}`\n   📺 চ্যানেল: {ch_str}\n   💎 মেয়াদ: Lifetime VIP\n━━━━━━━━━━━━━━━━━━━━\n"
            
            buttons = []
            nav_row = []
            if page > 1:
                nav_row.append(InlineKeyboardButton("◀️ পূর্ববর্তী", callback_data=f"admin_premium_list_page_{page-1}"))
            if page < total_pages:
                nav_row.append(InlineKeyboardButton("পরবর্তী ▶️", callback_data=f"admin_premium_list_page_{page+1}"))
            if nav_row:
                buttons.append(nav_row)
                
            buttons.append([
                InlineKeyboardButton("➕ ম্যানুয়াল প্রিমিয়াম", callback_data="admin_manual_prem"),
                InlineKeyboardButton("🚫 প্রিমিয়াম রিমুভ", callback_data="admin_remove_prem")
            ])
            buttons.append([InlineKeyboardButton("🔙 অ্যাডমিন প্যানেল", callback_data="admin_back")])
            await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

    # ৫. ম্যানুয়াল প্রিমিয়াম
    elif data == "admin_manual_prem":
        admin_state[ADMIN_ID] = {"action": "manual_prem_uid"}
        await callback.message.edit_text(
            "➕ **ম্যানুয়াল প্রিমিয়াম যোগ করুন:**\n\n"
            "যাকে প্রিমিয়াম দিতে চান তার **Telegram User ID** লিখে পাঠান:\n\n"
            "(বাতিল করতে /cancel লিখুন)",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 অ্যাডমিন প্যানেল", callback_data="admin_back")]])
        )

    elif data.startswith("mpstoggle_"):
        parts = data.split("_")
        uid = parts[1]
        ch_key = parts[2]
        state = admin_state.get(ADMIN_ID, {})
        selected = state.get("selected", [])
        
        if ch_key == "all":
            if len(selected) == 4:
                selected = []
            else:
                selected = ["1", "2", "3", "4"]
        else:
            if ch_key in selected:
                selected.remove(ch_key)
            else:
                selected.append(ch_key)
                
        state["selected"] = selected
        admin_state[ADMIN_ID] = state
        await render_manual_prem_selection(callback.message, uid, edit=True)

    elif data.startswith("mpsconfirm_"):
        uid = data.split("_")[1]
        state = admin_state.get(ADMIN_ID, {})
        selected = state.get("selected", [])
        if not selected:
            return await callback.answer("দয়া করে অন্তত একটি চ্যানেল নির্বাচন করুন!", show_alert=True)
            
        await callback.message.edit_text("⏳ ম্যানুয়াল প্রিমিয়াম প্রসেস করা হচ্ছে...")
        user_data = get_cached_user(str(uid))
        prem_dict = user_data.get('premium_channels', {})
        links_text = ""
        selected_ch_names = []
        
        for k in selected:
            c_id = CHANNELS[k]
            c_name = CHANNEL_NAMES[k]
            selected_ch_names.append(c_name)
            prem_dict[k] = {
                'status': 'ACTIVE',
                'type': 'LIFETIME',
                'start_date': datetime.now().isoformat(),
                'expiry_date': None,
                'channel_name': c_name
            }
            try:
                invite_link = await client.create_chat_invite_link(chat_id=c_id, creates_join_request=True, name=f"VIP_{uid}")
                links_text += f"🔹 **{c_name}:** {invite_link.invite_link}\n\n"
            except Exception as e:
                print(f"Error creating link for {c_name}: {e}")
                
        update_cached_user(str(uid), {'premium_channels': prem_dict})
        
        # ১. ইউজারের কাছে লিংক পাঠানো
        user_msg = (
            "🎉 **অভিনন্দন! আপনাকে Lifetime VIP Access দেওয়া হয়েছে!** 🎉\n\n"
            "অ্যাডমিন আপনার জন্য নিচের চ্যানেলগুলোর প্রিমিয়াম অ্যাক্সেস অনুমোদন করেছেন।\n\n"
            "নিচের লিংকে ক্লিক করে চ্যানেলে **Join Request** দিন, বট আপনাকে সাথে সাথে অটোমেটিক Approve করে নিবে:\n\n"
            f"{links_text}"
            "💎 সারাজীবনের জন্য আনলিমিটেড ভিডিও উপভোগ করুন!"
        )
        try:
            await client.send_message(int(uid), user_msg)
        except Exception as e:
            print(f"Send user link error: {e}")
            
        # ২. পেমেন্ট প্রুফ চ্যানেলে পোস্ট
        user_name = user_data.get('name')
        if not user_name or user_name == 'VIP User':
            try:
                tg_u = await client.get_users(int(uid))
                fn = tg_u.first_name or ""
                ln = tg_u.last_name or ""
                user_name = f"{fn} {ln}".strip() or fn or "VIP Member"
                update_cached_user(str(uid), {'name': user_name, 'username': tg_u.username})
            except:
                user_name = "VIP Member"
        ch_names_str = ", ".join(selected_ch_names)
        pkg_name = f"{len(selected)}টি চ্যানেল" if len(selected) < 4 else "৪টি চ্যানেল (ফুল বান্ডেল)"
        
        if PROOF_CHANNEL_ID != 0:
            try:
                masked_uid = f"{uid[:3]}***{uid[-2:]}" if len(uid) >= 6 else uid
                bd_time = get_bd_time_str()
                proof_caption = (
                    "🎉 **NEW VIP MEMBER PURCHASED!** 🌟\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    f"👤 **ক্রেতার নাম:** {user_name}\n"
                    f"🆔 **ইউজার আইডি:** `{masked_uid}`\n"
                    f"📦 **প্যাকেজ:** {pkg_name}\n"
                    f"📺 **চ্যানেলসমূহ:** {ch_names_str}\n"
                    f"💳 **পেমেন্ট মাধ্যম:** অ্যাডমিন ম্যানুয়াল ভেরিফিকেশন\n"
                    f"⏰ **সময় ও তারিখ:** {bd_time}\n"
                    f"💎 **মেয়াদ:** আজীবন (Lifetime VIP Access)\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    "✨ আপনিও এখনই ভিআইপি মেম্বার হয়ে আনলিমিটেড এক্সেস উপভোগ করুন!"
                )
                proof_btn = InlineKeyboardMarkup([[InlineKeyboardButton("💎 এখুনি প্রিমিয়াম কিনুন", url="https://t.me/PREMIUM_GROUP_BUY_BOT?start=start")]])
                await client.send_message(PROOF_CHANNEL_ID, proof_caption, reply_markup=proof_btn)
            except Exception as e:
                print(f"Proof Channel Error in manual prem: {e}")

        # ৩. সব বট ইউজারদের কাছে অ্যানাউন্সমেন্ট পাঠানো
        asyncio.create_task(broadcast_vip_purchase(client, user_name, pkg_name, ch_names_str))
        
        # ৪. অ্যাডমিনকে নিশ্চিতকরণ পাঠানো
        admin_state.pop(ADMIN_ID, None)
        await callback.message.edit_text(
            f"✅ **User `{uid}` এর ম্যানুয়াল প্রিমিয়াম সফলভাবে এক্টিভ করা হয়েছে!**\n\n"
            f"📺 অনুমোদিত চ্যানেল: {ch_names_str}\n\n"
            f"🔗 তৈরি হওয়া জয়েন লিংক ইউজারের ইনবক্সে পৌঁছে দেওয়া হয়েছে:\n\n{links_text}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 অ্যাডমিন প্যানেল", callback_data="admin_back")]])
        )

    # ৬. প্রিমিয়াম রিমুভ
    elif data == "admin_remove_prem":
        admin_state[ADMIN_ID] = {"action": "remprem_uid"}
        await callback.message.edit_text(
            "🚫 **প্রিমিয়াম রিমুভ কন্ট্রোল:**\n\n"
            "যাকে প্রিমিয়াম থেকে রিমুভ করতে চান তার **Telegram User ID** লিখে পাঠান:\n\n"
            "(বাতিল করতে /cancel লিখুন)",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 অ্যাডমিন প্যানেল", callback_data="admin_back")]])
        )

    elif data.startswith("rempremtoggle_"):
        parts = data.split("_")
        uid = parts[1]
        ch_key = parts[2]
        state = admin_state.get(ADMIN_ID, {})
        selected = state.get("selected", [])
        
        if ch_key == "all":
            if len(selected) == 4:
                selected = []
            else:
                selected = ["1", "2", "3", "4"]
        else:
            if ch_key in selected:
                selected.remove(ch_key)
            else:
                selected.append(ch_key)
                
        state["selected"] = selected
        admin_state[ADMIN_ID] = state
        await render_remprem_selection(callback.message, uid, edit=True)

    elif data.startswith("confirmrem_"):
        uid = data.split("_")[1]
        state = admin_state.get(ADMIN_ID, {})
        selected = state.get("selected", [])
        if not selected:
            return await callback.answer("দয়া করে অন্তত একটি চ্যানেল নির্বাচন করুন!", show_alert=True)
            
        await callback.message.edit_text("⏳ ইউজারকে প্রিমিয়াম চ্যানেল থেকে রিমুভ ও কিক করা হচ্ছে...")
        user_data = get_cached_user(str(uid))
        prem_dict = user_data.get('premium_channels', {})
        removed_names = []
        
        for k in selected:
            c_id = CHANNELS[k]
            c_name = CHANNEL_NAMES[k]
            removed_names.append(c_name)
            if k in prem_dict:
                prem_dict[k]['status'] = 'REMOVED'
                prem_dict[k]['removed_at'] = datetime.now().isoformat()
            try:
                await client.ban_chat_member(c_id, int(uid))
                await asyncio.sleep(0.5)
                await client.unban_chat_member(c_id, int(uid))
            except Exception as e:
                print(f"Kick error for {uid} from {c_name}: {e}")
                
        update_cached_user(str(uid), {'premium_channels': prem_dict})
        
        # ইউজারের কাছে রিমুভ মেসেজ পাঠানো
        try:
            await client.send_message(
                int(uid),
                f"🚫 **আপনার প্রিমিয়াম অ্যাক্সেস বাতিল করা হয়েছে!**\n\n"
                f"আপনাকে নিম্নলিখিত চ্যানেল(গুলো) থেকে রিমুভ করা হয়েছে:\n"
                + "\n".join([f"❌ {name}" for name in removed_names]) + "\n\n"
                "পুনরায় অ্যাক্সেস পেতে চাইলে প্যাকেজ কিনে নিন।"
            )
        except Exception as e:
            print(f"Send user removal error: {e}")
            
        admin_state.pop(ADMIN_ID, None)
        await callback.message.edit_text(
            f"✅ **User `{uid}` কে সফলভাবে রিমুভ করা হয়েছে!**\n\n"
            f"রিমুভকৃত চ্যানেলসমূহ:\n" + "\n".join([f"• {name}" for name in removed_names]) + "\n\n"
            "ইউজারের কাছে রিমুভ নোটিফিকেশন পৌঁছে গেছে এবং চ্যানেল থেকে কিক করা হয়েছে।",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 অ্যাডমিন প্যানেল", callback_data="admin_back")]])
        )

    # ৭. সব ট্রায়াল রিসেট (চ্যানেল ওয়াইজ সিলেক্ট ও ফাস্ট রিসেট)
    elif data == "admin_reset_trials_menu":
        counts = {"1": 0, "2": 0, "3": 0, "4": 0}
        if db:
            try:
                users = list(db.collection('users').stream())
                for u in users:
                    t_chans = u.to_dict().get('trial_channels', [])
                    for k in ["1", "2", "3", "4"]:
                        c_id_str = str(CHANNELS.get(k, 0))
                        if c_id_str in t_chans or k in t_chans:
                            counts[k] += 1
            except Exception as e:
                print(f"Count trial error: {e}")
        admin_state[ADMIN_ID] = {"action": "reset_trials", "selected": [], "counts": counts}
        await render_trial_reset_menu(callback.message, edit=True)

    elif data.startswith("rstoggle_"):
        k = data.split("_")[1]
        state = admin_state.get(ADMIN_ID, {})
        selected = state.get("selected", [])
        
        if k == "all":
            if len(selected) == 4:
                selected = []
            else:
                selected = ["1", "2", "3", "4"]
        else:
            if k in selected:
                selected.remove(k)
            else:
                selected.append(k)
                
        state["selected"] = selected
        admin_state[ADMIN_ID] = state
        await render_trial_reset_menu(callback.message, edit=True)

    elif data == "rsconfirm":
        state = admin_state.get(ADMIN_ID, {})
        selected = state.get("selected", [])
        if not selected:
            return await callback.answer("দয়া করে অন্তত একটি চ্যানেল নির্বাচন করুন!", show_alert=True)
            
        await callback.message.edit_text("⏳ অতি দ্রুত ট্রায়াল রিসেট করা হচ্ছে...")
        
        target_ch_ids = set()
        for k in selected:
            target_ch_ids.add(str(CHANNELS.get(k, 0)))
            target_ch_ids.add(str(k))
            
        # ১. ইন-মেমোরি রানিং ট্রায়াল ক্লিয়ার
        to_del = []
        for tk, tv in list(ACTIVE_TRIALS.items()):
            if str(tv.get('chat_id')) in target_ch_ids:
                if tv.get('task'):
                    tv['task'].cancel()
                to_del.append(tk)
        for tk in to_del:
            ACTIVE_TRIALS.pop(tk, None)
            
        # ২. ফায়ারবেস ব্যাচ রিসেট (Ultra Fast Batch)
        reset_user_count = 0
        if db:
            try:
                users = list(db.collection('users').stream())
                batch = db.batch()
                b_ops = 0
                for u in users:
                    udata = u.to_dict()
                    t_chans = udata.get('trial_channels', [])
                    new_t = [ch for ch in t_chans if ch not in target_ch_ids]
                    if len(new_t) != len(t_chans):
                        doc_ref = db.collection('users').document(u.id)
                        batch.update(doc_ref, {'trial_channels': new_t})
                        b_ops += 1
                        reset_user_count += 1
                        if u.id in USER_CACHE:
                            USER_CACHE[u.id]['data']['trial_channels'] = new_t
                        if b_ops >= 400:
                            batch.commit()
                            batch = db.batch()
                            b_ops = 0
                if b_ops > 0:
                    batch.commit()
                    
                at_docs = list(db.collection('active_trials').stream())
                at_batch = db.batch()
                at_ops = 0
                for ad in at_docs:
                    ad_data = ad.to_dict()
                    if str(ad_data.get('chat_id')) in target_ch_ids:
                        at_batch.delete(ad.reference)
                        at_ops += 1
                        if at_ops >= 400:
                            at_batch.commit()
                            at_batch = db.batch()
                            at_ops = 0
                if at_ops > 0:
                    at_batch.commit()
            except Exception as e:
                print(f"Batch reset error: {e}")
                
        ch_names_str = ", ".join([CHANNEL_NAMES.get(k, f"Ch {k}") for k in selected])
        admin_state.pop(ADMIN_ID, None)
        await callback.message.edit_text(
            f"✅ **ট্রায়াল রিসেট সফল হয়েছে!**\n\n"
            f"📺 রিসেটকৃত চ্যানেলসমূহ: **{ch_names_str}**\n"
            f"👥 মোট প্রভাব পড়েছে: **{reset_user_count}** জন ইউজারের ট্রায়ালে।\n\n"
            "এখন সবাই আবার নতুন করে এই চ্যানেলগুলোতে ৫ মিনিট ফ্রি ট্রায়াল নিতে পারবে।",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 অ্যাডমিন প্যানেল", callback_data="admin_back")]])
        )

    # ৮. প্রাইস পরিবর্তন
    elif data == "admin_change_price":
        text = "💰 **Change Price:**\n\nকোনটির প্রাইস পরিবর্তন করবেন?"
        buttons = []
        for k, v in CHANNEL_NAMES.items():
            buttons.append([InlineKeyboardButton(f"📺 {v} (বর্তমান: {PRICES[k]} ৳)", callback_data=f"changeprice_{k}")])
        buttons.append([InlineKeyboardButton(f"📦 Full Bundle (বর্তমান: {PRICES['all']} ৳)", callback_data="changeprice_all")])
        buttons.append([InlineKeyboardButton("🔙 ব্যাক", callback_data="admin_back")])
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("changeprice_"):
        ch_key = data.split("_")[1]
        admin_state[ADMIN_ID] = {"action": "set_price", "channel": ch_key}
        await callback.message.reply_text(f"💰 নতুন Price কত হবে তা লিখে পাঠান: (/cancel)")

    elif data.startswith("reply_"):
        target_uid = data.split("_")[1]
        admin_state[ADMIN_ID] = {"action": "reply_user", "target": target_uid}
        await callback.message.reply_text(f"💬 User `{target_uid}` কে কী মেসেজ দিতে চান তা টাইপ করুন: (/cancel)")

    # ৯. ফুল ব্রডকাস্ট
    elif data == "admin_broadcast":
        admin_state[ADMIN_ID] = {"action": "broadcast", "filter": "ALL"}
        await callback.message.edit_text(
            "📢 **ফুল ব্রডকাস্ট (All Users):**\n\n"
            "সকল ইউজারকে পাঠানোর জন্য যেকোনো টেক্সট মেসেজ, অথবা ছবি/ভিডিও সহ ক্যাপশন পাঠান:\n\n"
            "(/cancel লিখলে বাতিল হবে)",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ব্যাক", callback_data="admin_back")]])
        )

    # ১০. নির্দিষ্ট ব্রডকাস্ট
    elif data == "admin_specific_cast":
        admin_state[ADMIN_ID] = {"action": "specific_cast_uid"}
        await callback.message.edit_text(
            "👤 **নির্দিষ্ট ইউজার ব্রডকাস্ট (Specific User Broadcast):**\n\n"
            "যাকে মেসেজ পাঠাতে চান তার **Telegram User ID** লিখে পাঠান:\n\n"
            "(বাতিল করতে /cancel)",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ব্যাক", callback_data="admin_back")]])
        )

    # ১১. স্পেশাল লিংক
    elif data == "admin_special_link":
        admin_state[ADMIN_ID] = {"action": "special_link_uid"}
        await callback.message.edit_text(
            "🔗 **স্পেশাল লিংক জেনারেটর:**\n\n"
            "যে ইউজারের জন্য স্পেশাল লিংক তৈরি করবেন তার **Telegram User ID** লিখে পাঠান:\n\n"
            "(বাতিল করতে /cancel)",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ব্যাক", callback_data="admin_back")]])
        )

    elif data.startswith("splinktoggle_"):
        parts = data.split("_")
        uid = parts[1]
        ch_key = parts[2]
        state = admin_state.get(ADMIN_ID, {})
        selected = state.get("selected", [])
        if isinstance(selected, str): selected = [selected] if selected else []
        
        if ch_key == "all":
            if len(selected) == 4:
                selected = []
            else:
                selected = ["1", "2", "3", "4"]
        else:
            if ch_key in selected:
                selected.remove(ch_key)
            else:
                selected.append(ch_key)
                
        state["selected"] = selected
        admin_state[ADMIN_ID] = state
        await render_special_link_selection(callback.message, uid, edit=True)

    elif data.startswith("splinkconfirm_"):
        uid = data.split("_")[1]
        state = admin_state.get(ADMIN_ID, {})
        selected = state.get("selected", [])
        if isinstance(selected, str): selected = [selected] if selected else []
        
        if not selected:
            return await callback.answer("দয়া করে অন্তত একটি চ্যানেল নির্বাচন করুন!", show_alert=True)

        try:
            user_data = get_cached_user(str(uid))
            prem_dict = user_data.get('premium_channels', {})
            links_list = []
            
            for ch_key in selected:
                chat_id = CHANNELS[ch_key]
                ch_name = CHANNEL_NAMES[ch_key]
                prem_dict[ch_key] = {
                    'status': 'ACTIVE',
                    'type': 'SPECIAL_LIFETIME',
                    'start_date': datetime.now().isoformat(),
                    'expiry_date': None,
                    'channel_name': ch_name
                }
                invite_link = await client.create_chat_invite_link(chat_id=chat_id, creates_join_request=True, name=f"SPL_{uid}")
                links_list.append(f"🔹 **{ch_name}:**\n`{invite_link.invite_link}`")
                
            update_cached_user(str(uid), {'premium_channels': prem_dict})

            admin_msg = (
                f"✅ **User `{uid}` এর জন্য স্পেশাল লিংক সফলভাবে তৈরি হয়েছে!**\n\n"
                + "\n\n".join(links_list) + "\n\n"
                "👉 **কীভাবে ব্যবহার করবেন?**\n"
                "১. উপরের লিংক(গুলো) কপি করে ইউজারকে দিন।\n"
                "২. ইউজার এই লিংকে ক্লিক করে Join Request দেওয়া মাত্রই বট সাথে সাথে তাকে **অটো এপ্রুভ** করবে এবং অভিনন্দন মেসেজ পাঠাবে!"
            )
            await callback.message.edit_text(admin_msg, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 অ্যাডমিন প্যানেল", callback_data="admin_back")]]))
            admin_state.pop(ADMIN_ID, None)
        except Exception as e:
            await callback.answer(f"Error: {e}", show_alert=True)

    # ১২. অটো পোস্ট কন্ট্রোল
    elif data == "admin_autopost":
        await render_autopost_dashboard(callback.message, edit=True)

    elif data == "autopost_setup":
        admin_state[ADMIN_ID] = {"action": "autopost_step1"}
        await callback.message.edit_text(
            "⏰ **অটো পোস্ট সেটআপ (ধাপ ১/২):**\n\n"
            "যে পোস্টটি সবার কাছে নির্দিষ্ট সময় পর পর অটো পাঠাতে চান তা লিখে পাঠান (বা ছবি/ভিডিও সহ ক্যাপশন পাঠান):\n\n"
            "(বাতিল করতে /cancel লিখুন)",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ব্যাক", callback_data="admin_autopost")]])
        )

    elif data == "autopost_toggle":
        curr = AUTO_POST_CONFIG.get('running', False)
        AUTO_POST_CONFIG['running'] = not curr
        if db:
            try:
                db.collection('config').document('autopost').set({'running': AUTO_POST_CONFIG['running']}, merge=True)
            except: pass
        restart_autopost_worker(client)
        await render_autopost_dashboard(callback.message, edit=True)

    elif data == "autopost_test_broadcast":
        file_id = AUTO_POST_CONFIG.get('file_id')
        caption = AUTO_POST_CONFIG.get('caption', '')
        media_type = AUTO_POST_CONFIG.get('media_type', 'text')
        
        if not file_id and not caption:
            return await callback.answer("আগে 'নতুন অটো পোস্ট সেট করুন' বাটনে ক্লিক করে পোস্ট সেট করুন!", show_alert=True)
            
        await callback.answer("এডমিন ইনবক্সে টেস্ট পোস্ট পাঠানো হচ্ছে...")
        btn = InlineKeyboardMarkup([[InlineKeyboardButton("💎 এখুনি প্রিমিয়াম কিনুন", callback_data="back_to_pkg")]])
        try:
            if media_type == 'photo':
                await client.send_photo(ADMIN_ID, photo=file_id, caption=caption, reply_markup=btn)
            elif media_type == 'video':
                await client.send_video(ADMIN_ID, video=file_id, caption=caption, reply_markup=btn)
            elif media_type == 'document':
                await client.send_document(ADMIN_ID, document=file_id, caption=caption, reply_markup=btn)
            elif media_type == 'animation':
                await client.send_animation(ADMIN_ID, animation=file_id, caption=caption, reply_markup=btn)
            else:
                await client.send_message(ADMIN_ID, caption, reply_markup=btn)
            await callback.message.reply_text("✅ আপনার কাছে টেস্ট পোস্টটি পাঠানো হয়েছে। চেক করুন!")
        except Exception as e:
            await callback.message.reply_text(f"❌ টেস্ট পাঠাতে ব্যর্থ: {e}")

    elif data == "autopost_delete":
        AUTO_POST_CONFIG['running'] = False
        AUTO_POST_CONFIG['file_id'] = None
        AUTO_POST_CONFIG['caption'] = ''
        AUTO_POST_CONFIG['media_type'] = 'text'
        AUTO_POST_CONFIG['total_sent'] = 0
        AUTO_POST_CONFIG['last_sent'] = None
        restart_autopost_worker(client)
        if db:
            try:
                db.collection('config').document('autopost').delete()
            except: pass
        await callback.answer("অটো পোস্ট মুছে ফেলা হয়েছে!", show_alert=True)
        await render_autopost_dashboard(callback.message, edit=True)

    # ১৩. ফরোয়ার্ড মেসেজ দিয়ে ইউজার আইডি এক্সট্র্যাক্ট
    elif data == "admin_extract_id":
        admin_state[ADMIN_ID] = {"action": "waiting_forward_id"}
        text = (
            "🔎 **ইউজার আইডি ও প্রোফাইল এক্সট্র্যাক্টর:**\n\n"
            "📩 আপনি যে ইউজারের আইডি বা তথ্য বের করতে চান, তার যেকোনো একটি মেসেজ এখানে **ফরওয়ার্ড (Forward)** করুন।\n\n"
            "💡 **সুবিধা:**\n"
            "অনেকেই বটে ঢুকতে বা বটের কমান্ড বুঝতে পারে না। তাদের পাঠানো যেকোনো মেসেজ এখানে ফরওয়ার্ড করলেই বট তার **নাম, ইউজারনেম ও ইউজার আইডি** বের করে দিবে।\n\n"
            "এরপর আপনি এক ক্লিকেই তাকে **ম্যানুয়াল প্রিমিয়াম** দিতে পারবেন অথবা ইউজার আইডি কপি করে নিতে পারবেন!\n\n"
            "(বাতিল করতে /cancel লিখুন)"
        )
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 অ্যাডমিন প্যানেল", callback_data="admin_back")]]))

    # ১৪. কুইক অ্যাকশন হ্যান্ডলার (আইডি বের করার পর এক ক্লিকে এক্সেস)
    elif data.startswith("quick_mp_"):
        uid = data.split("_")[2]
        admin_state[ADMIN_ID] = {"action": "manual_prem_select", "target_uid": uid, "selected": []}
        await render_manual_prem_selection(callback.message, uid, edit=True)

    elif data.startswith("quick_rp_"):
        uid = data.split("_")[2]
        admin_state[ADMIN_ID] = {"action": "remprem_select", "target_uid": uid, "selected": []}
        await render_remprem_selection(callback.message, uid, edit=True)

    elif data.startswith("quick_spl_"):
        uid = data.split("_")[2]
        admin_state[ADMIN_ID] = {"action": "special_link_select", "target_uid": uid, "selected": []}
        await render_special_link_selection(callback.message, uid, edit=True)

    elif data.startswith("quick_msg_"):
        uid = data.split("_")[2]
        admin_state[ADMIN_ID] = {"action": "specific_cast_msg", "target_uid": int(uid)}
        await callback.message.edit_text(
            f"📝 **User `{uid}` এর জন্য ব্রডকাস্ট মেসেজ পাঠান:**\n\n"
            "আপনি সাধারণ টেক্সট অথবা ছবি/ভিডিও সহ ক্যাপশন পাঠাতে পারেন।\n\n"
            "(বাতিল করতে /cancel)",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ব্যাক", callback_data="admin_back")]])
        )

    # ১৫. ফায়ারবেস কোটা শিল্ড ড্যাশবোর্ড ও ব্যাকআপ
    elif data == "admin_quota_shield":
        total_cached = len(REGISTERED_USERS_SET)
        now_str = datetime.now().strftime('%d %b %Y, %I:%M %p')
        text = (
            "🛡️ **ফায়ারবেস ৫০,০০০ কোটা শিল্ড ড্যাশবোর্ড:**\n\n"
            f"👥 **রেজিস্টার্ড ইউজার মেমোরি:** `{total_cached}` জন\n"
            "⚡ **ব্রডকাস্ট ও অটো-পোস্ট মোড:** Zero-Read In-Memory সক্রিয় ✅\n"
            "💾 **লোকাল ফাইল ক্যাশ:** `cached_users.json` সংরক্ষিত ✅\n"
            f"🚀 **সেভ হওয়া Firestore রীড:** `{FIRESTORE_READS_SAVED}` টি\n"
            f"🕒 **লাস্ট স্ট্যাটাস চেক:** {now_str}\n\n"
            "💡 এই সিস্টেমের কারণে ব্রডকাস্ট বা অটো পোস্ট পাঠালেও ফায়ারবেসের ৫০,০০০ ফ্রি কোটা থেকে ১টিও অতিরিক্ত রীড খরচ হয় না।"
        )
        buttons = [
            [InlineKeyboardButton("🔄 ফায়ারবেস থেকে ইউজার ডাটা রি-সিঙ্ক", callback_data="admin_sync_users")],
            [InlineKeyboardButton("📥 ইউজার আইডি ব্যাকআপ ডাউনলোড", callback_data="admin_export_users")],
            [InlineKeyboardButton("🔙 অ্যাডমিন প্যানেল", callback_data="admin_back")]
        ]
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

    elif data == "admin_sync_users":
        await callback.answer("ফায়ারবেস থেকে সিঙ্ক করা হচ্ছে...", show_alert=False)
        count = 0
        if db:
            try:
                docs = list(db.collection('users').stream())
                for d in docs:
                    register_user_id(d.id)
                    count += 1
            except Exception as e:
                print(f"Sync error: {e}")
        await callback.message.edit_text(
            f"✅ **ফায়ারবেস ডাটা সিঙ্ক সম্পন্ন!**\n\nমোট `{len(REGISTERED_USERS_SET)}` জন ইউজারের আইডি মেমোরি ও ক্যাশ ফাইলে সংরক্ষিত হয়েছে।",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 কোটা শিল্ড", callback_data="admin_quota_shield")]])
        )

    elif data == "admin_export_users":
        await callback.answer("ইউজার ব্যাকআপ ফাইল তৈরি করা হচ্ছে...")
        user_list = sorted(list(REGISTERED_USERS_SET))
        export_file = "users_backup.txt"
        with open(export_file, "w", encoding="utf-8") as f:
            f.write(f"--- BOT REGISTERED USERS BACKUP ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ---\n")
            f.write(f"Total Users: {len(user_list)}\n\n")
            for u in user_list:
                f.write(f"{u}\n")
        try:
            await client.send_document(
                ADMIN_ID,
                document=export_file,
                caption=f"📁 **ইউজার ব্যাকআপ ফাইল**\n\nমোট ইউজার: `{len(user_list)}` জন\nতারিখ: `{datetime.now().strftime('%d %b %Y')}`"
            )
            await callback.message.reply_text("✅ ব্যাকআপ ফাইল আপনার ইনবক্সে সফলভাবে পাঠানো হয়েছে!")
        except Exception as e:
            await callback.message.reply_text(f"❌ ব্যাকআপ ফাইল পাঠাতে ব্যর্থ: {e}")

    elif data == "admin_full_backup":
        await callback.answer("সম্পূর্ণ সিস্টেম ডাটা ব্যাকআপ তৈরি হচ্ছে...")
        backup_content = {
            "timestamp": datetime.now().isoformat(),
            "prices": PRICES,
            "registered_users_count": len(REGISTERED_USERS_SET),
            "users": sorted(list(REGISTERED_USERS_SET)),
            "autopost": {
                "running": AUTO_POST_CONFIG.get("running"),
                "interval": AUTO_POST_CONFIG.get("interval"),
                "total_sent": AUTO_POST_CONFIG.get("total_sent")
            }
        }
        fname = f"system_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(fname, "w", encoding="utf-8") as f:
            json.dump(backup_content, f, indent=2, ensure_ascii=False)
        try:
            await client.send_document(
                ADMIN_ID,
                document=fname,
                caption=f"📦 **সম্পূর্ণ সিস্টেম ডাটা ব্যাকআপ**\n\n🕒 সময়: `{datetime.now().strftime('%d %b %Y, %I:%M %p')}`\n👥 মোট ইউজার: `{len(REGISTERED_USERS_SET)}`"
            )
            await callback.message.reply_text("✅ সম্পূর্ণ সিস্টেম ব্যাকআপ ফাইল আপনার ইনবক্সে সফলভাবে পাঠানো হয়েছে!")
        except Exception as e:
            await callback.message.reply_text(f"❌ ব্যাকআপ পাঠাতে ব্যর্থ: {e}")

    # ১৬. বাটন কালার স্টাইল টগল
    elif data == "admin_toggle_colors":
        global COLORFUL_BUTTONS
        COLORFUL_BUTTONS = not COLORFUL_BUTTONS
        save_bot_settings()
        status_txt = "🟢 চালু (Multi-color Premium)" if COLORFUL_BUTTONS else "⚪ বন্ধ (Standard)"
        await callback.answer(f"বাটন কালার স্টাইল: {status_txt}", show_alert=True)
        await callback.message.edit_reply_markup(reply_markup=get_admin_keyboard())

    # ১৭. ওয়েলকাম মেসেজ ও মিডিয়া সেটিংস
    elif data == "admin_welcome_menu":
        media_status = "নেই (Text Only)"
        if WELCOME_CONFIG.get('media_type') == 'photo':
            media_status = "🖼️ ফটো (Photo)"
        elif WELCOME_CONFIG.get('media_type') == 'video':
            media_status = "🎥 ভিডিও (Video)"

        curr_text = WELCOME_CONFIG.get('text') or DEFAULT_WELCOME_TEXT
        prev_text = (curr_text[:120] + "...") if len(curr_text) > 120 else curr_text

        text = (
            "👋 **ওয়েলকাম মেসেজ ও মিডিয়া কাস্টমাইজেশন:**\n\n"
            f"📁 **বর্তমান মিডিয়া:** {media_status}\n"
            f"📝 **মেসেজ প্রিভিউ:**\n_{prev_text}_\n\n"
            "💡 ইউজার বটে `/start` দিলে বা প্রথমবার আসলে এই মেসেজ ও ছবি/ভিডিও দেখতে পাবে।"
        )
        buttons = [
            [InlineKeyboardButton("✏️ ওয়েলকাম টেক্সট পরিবর্তন", callback_data="welcome_edit_text")],
            [InlineKeyboardButton("🖼️ ফটো/ভিডিও সেট করুন", callback_data="welcome_set_media"),
             InlineKeyboardButton("🗑️ মিডিয়া রিমুভ", callback_data="welcome_remove_media")],
            [InlineKeyboardButton("👁️ প্রিভিউ দেখুন", callback_data="welcome_preview")],
            [InlineKeyboardButton("🔙 অ্যাডমিন প্যানেল", callback_data="admin_back")]
        ]
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

    elif data == "welcome_edit_text":
        admin_state[ADMIN_ID] = {"action": "welcome_edit_text"}
        await callback.message.edit_text(
            "✏️ **নতুন ওয়েলকাম মেসেজ লিখে পাঠান:**\n\n"
            "ইউজারের নামের জায়গায় `{name}` ব্যবহার করতে পারেন।\n\n"
            "উদাহরণ:\n`হ্যালো {name}! আমাদের VIP বটে আপনাকে স্বাগতম...`\n\n"
            "(বাতিল করতে /cancel লিখুন)",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ব্যাক", callback_data="admin_welcome_menu")]])
        )

    elif data == "welcome_set_media":
        admin_state[ADMIN_ID] = {"action": "welcome_set_media"}
        await callback.message.edit_text(
            "🖼️ **ওয়েলকাম ফটো অথবা ভিডিও পাঠান:**\n\n"
            "যেকোনো আকর্ষণীয় ব্যানার ছবি বা ইন্ট্রো ভিডিও পাঠিয়ে দিন (ক্যাপশন দিতে চাইলে দিতে পারেন)।\n\n"
            "(বাতিল করতে /cancel লিখুন)",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ব্যাক", callback_data="admin_welcome_menu")]])
        )

    elif data == "welcome_remove_media":
        WELCOME_CONFIG['media_type'] = None
        WELCOME_CONFIG['file_id'] = None
        save_bot_settings()
        await callback.answer("✅ ওয়েলকাম মিডিয়া রিমুভ করা হয়েছে!", show_alert=True)
        await callback.message.edit_text(
            "👋 **ওয়েলকাম মেসেজ ও মিডিয়া কাস্টমাইজেশন:**\n\n"
            "📁 **বর্তমান মিডিয়া:** নেই (Text Only)\n"
            f"📝 **মেসেজ প্রিভিউ:**\n_{(WELCOME_CONFIG.get('text') or DEFAULT_WELCOME_TEXT)[:120]}...\n\n"
            "✅ মিডিয়া সফলভাবে রিমুভ করা হয়েছে। এখন শুধু টেক্সট পাঠানো হবে।",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✏️ ওয়েলকাম টেক্সট পরিবর্তন", callback_data="welcome_edit_text")],
                [InlineKeyboardButton("🖼️ ফটো/ভিডিও সেট করুন", callback_data="welcome_set_media")],
                [InlineKeyboardButton("👁️ প্রিভিউ দেখুন", callback_data="welcome_preview")],
                [InlineKeyboardButton("🔙 অ্যাডমিন প্যানেল", callback_data="admin_back")]
            ])
        )

    elif data == "welcome_preview":
        curr_text = (WELCOME_CONFIG.get('text') or DEFAULT_WELCOME_TEXT).replace("{name}", callback.from_user.first_name)
        m_id = WELCOME_CONFIG.get('file_id')
        m_type = WELCOME_CONFIG.get('media_type')
        try:
            if m_id and m_type == 'photo':
                await client.send_photo(ADMIN_ID, photo=m_id, caption=f"👁️ **ওয়েলকাম প্রিভিউ:**\n\n{curr_text}")
            elif m_id and m_type == 'video':
                await client.send_video(ADMIN_ID, video=m_id, caption=f"👁️ **ওয়েলকাম প্রিভিউ:**\n\n{curr_text}")
            else:
                await client.send_message(ADMIN_ID, f"👁️ **ওয়েলকাম প্রিভিউ:**\n\n{curr_text}")
            await callback.answer("প্রিভিউ পাঠানো হয়েছে!", show_alert=False)
        except Exception as e:
            await callback.answer(f"প্রিভিউ এরর: {e}", show_alert=True)

    # ১৮. 'কিভাবে কিনবেন' টিউটোরিয়াল সেটিংস
    elif data == "admin_howtobuy_menu":
        media_status = "নেই (Text Only)"
        if HOW_TO_BUY_CONFIG.get('media_type') == 'photo':
            media_status = "🖼️ ফটো (Photo/Screenshot)"
        elif HOW_TO_BUY_CONFIG.get('media_type') == 'video':
            media_status = "🎥 ভিডিও (Video Tutorial)"

        curr_text = HOW_TO_BUY_CONFIG.get('text') or DEFAULT_HOW_TO_BUY_TEXT
        prev_text = (curr_text[:120] + "...") if len(curr_text) > 120 else curr_text

        text = (
            "📖 **'কিভাবে প্রিমিয়াম কিনবেন' টিউটোরিয়াল সেটিংস:**\n\n"
            f"📁 **বর্তমান মিডিয়া:** {media_status}\n"
            f"📝 **গাইডলাইন প্রিভিউ:**\n_{prev_text}_\n\n"
            "💡 ইউজাররা '💡 কিভাবে কিনবেন?' বাটনে ক্লিক করলে এই তথ্য দেখতে পাবে।"
        )
        buttons = [
            [InlineKeyboardButton("✏️ নির্দেশিকা টেক্সট এডিট", callback_data="howtobuy_edit_text")],
            [InlineKeyboardButton("🖼️ ফটো/ভিডিও সেট করুন", callback_data="howtobuy_set_media"),
             InlineKeyboardButton("🗑️ মিডিয়া রিমুভ", callback_data="howtobuy_remove_media")],
            [InlineKeyboardButton("👁️ প্রিভিউ দেখুন", callback_data="howtobuy_preview")],
            [InlineKeyboardButton("🔙 অ্যাডমিন প্যানেল", callback_data="admin_back")]
        ]
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

    elif data == "howtobuy_edit_text":
        admin_state[ADMIN_ID] = {"action": "howtobuy_edit_text"}
        await callback.message.edit_text(
            "✏️ **'কিভাবে কিনবেন' টিউটোরিয়াল মেসেজ লিখে পাঠান:**\n\n"
            "এখানে বিস্তারিত লিখে দিন কিভাবে বিকাশ/নগদে টাকা পাঠিয়ে TrxID দিতে হবে।\n\n"
            "(বাতিল করতে /cancel লিখুন)",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ব্যাক", callback_data="admin_howtobuy_menu")]])
        )

    elif data == "howtobuy_set_media":
        admin_state[ADMIN_ID] = {"action": "howtobuy_set_media"}
        await callback.message.edit_text(
            "🖼️ **টিউটোরিয়াল ফটো অথবা ভিডিও পাঠান:**\n\n"
            "পেমেন্ট করার স্ক্রিনশট বা ভিডিও গাইড পাঠিয়ে দিন।\n\n"
            "(বাতিল করতে /cancel লিখুন)",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ব্যাক", callback_data="admin_howtobuy_menu")]])
        )

    elif data == "howtobuy_remove_media":
        HOW_TO_BUY_CONFIG['media_type'] = None
        HOW_TO_BUY_CONFIG['file_id'] = None
        save_bot_settings()
        await callback.answer("✅ টিউটোরিয়াল মিডিয়া রিমুভ করা হয়েছে!", show_alert=True)
        await callback.message.edit_text(
            "📖 **'কিভাবে প্রিমিয়াম কিনবেন' টিউটোরিয়াল সেটিংস:**\n\n"
            "📁 **বর্তমান মিডিয়া:** নেই (Text Only)\n"
            f"📝 **গাইডলাইন প্রিভিউ:**\n_{(HOW_TO_BUY_CONFIG.get('text') or DEFAULT_HOW_TO_BUY_TEXT)[:120]}...\n\n"
            "✅ মিডিয়া সফলভাবে মুছে ফেলা হয়েছে।",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✏️ নির্দেশিকা টেক্সট এডিট", callback_data="howtobuy_edit_text")],
                [InlineKeyboardButton("🖼️ ফটো/ভিডিও সেট করুন", callback_data="howtobuy_set_media")],
                [InlineKeyboardButton("👁️ প্রিভিউ দেখুন", callback_data="howtobuy_preview")],
                [InlineKeyboardButton("🔙 অ্যাডমিন প্যানেল", callback_data="admin_back")]
            ])
        )

    elif data == "howtobuy_preview":
        curr_text = HOW_TO_BUY_CONFIG.get('text') or DEFAULT_HOW_TO_BUY_TEXT
        m_id = HOW_TO_BUY_CONFIG.get('file_id')
        m_type = HOW_TO_BUY_CONFIG.get('media_type')
        try:
            if m_id and m_type == 'photo':
                await client.send_photo(ADMIN_ID, photo=m_id, caption=f"👁️ **টিউটোরিয়াল প্রিভিউ:**\n\n{curr_text}")
            elif m_id and m_type == 'video':
                await client.send_video(ADMIN_ID, video=m_id, caption=f"👁️ **টিউটোরিয়াল প্রিভিউ:**\n\n{curr_text}")
            else:
                await client.send_message(ADMIN_ID, f"👁️ **টিউটোরিয়াল প্রিভিউ:**\n\n{curr_text}")
            await callback.answer("প্রিভিউ পাঠানো হয়েছে!", show_alert=False)
        except Exception as e:
            await callback.answer(f"প্রিভিউ এরর: {e}", show_alert=True)

# ================= ১৩. অ্যাডমিন ইনপুট হ্যান্ডলার (টেক্সট, ছবি ও ভিডিও) =================
@app.on_message(filters.private & filters.user(ADMIN_ID) & ~filters.command(["admin", "start"]))
async def handle_admin_text_inputs(client: Client, message: Message):
    state = admin_state.get(ADMIN_ID, {})
    action = state.get("action")
    text = (message.text or message.caption or "").strip()

    # ০. ইউজার মেসেজ ফরোয়ার্ড অথবা আইডি এক্সট্র্যাক্ট হ্যান্ডলার
    if action == "waiting_forward_id" or message.forward_date is not None or message.forward_from is not None or message.forward_sender_name is not None:
        if message.forward_from:
            target_user = message.forward_from
            target_id = target_user.id
            first_name = target_user.first_name or ""
            last_name = target_user.last_name or ""
            full_name = f"{first_name} {last_name}".strip() or "নাম নেই"
            username = f"@{target_user.username}" if target_user.username else "নেই (No Username)"
            register_user_id(target_id)

            user_data = get_cached_user(str(target_id))
            prem_dict = user_data.get('premium_channels', {})
            active_channels = [CHANNEL_NAMES.get(k, f"চ্যানেল {k}") for k, v in prem_dict.items() if v.get('status') == 'ACTIVE']
            status_desc = f"🌟 ভিআইপি ({', '.join(active_channels)})" if active_channels else "সাধারণ ইউজার"

            admin_state.pop(ADMIN_ID, None)
            res_text = (
                "✅ **ইউজার ইনফরমেশন সফলভাবে উদ্ধার করা হয়েছে!**\n\n"
                f"👤 **নাম:** {full_name}\n"
                f"🌐 **ইউজারনেম:** {username}\n"
                f"🆔 **ইউজার আইডি:** `{target_id}`\n"
                f"📊 **বর্তমান স্ট্যাটাস:** {status_desc}\n\n"
                f"📋 *কপি করতে ইউজার আইডি `{target_id}` এর উপর চাপ দিন!*\n\n"
                "👇 আপনি সরাসরি নিচের বাটনে এক ক্লিকেই কাজ করতে পারবেন:"
            )
            buttons = [
                [InlineKeyboardButton("👑 এই ইউজারকে ম্যানুয়াল প্রিমিয়াম দিন", callback_data=f"quick_mp_{target_id}")],
                [InlineKeyboardButton("🚫 প্রিমিয়াম থেকে রিমুভ করুন", callback_data=f"quick_rp_{target_id}")],
                [InlineKeyboardButton("🔗 স্পেশাল লিংক তৈরি করুন", callback_data=f"quick_spl_{target_id}")],
                [InlineKeyboardButton("✉️ এই ইউজারকে মেসেজ পাঠান", callback_data=f"quick_msg_{target_id}")],
                [InlineKeyboardButton("🔎 অন্য ইউজারের মেসেজ ফরওয়ার্ড করুন", callback_data="admin_extract_id")],
                [InlineKeyboardButton("🔙 অ্যাডমিন প্যানেল", callback_data="admin_back")]
            ]
            return await message.reply_text(res_text, reply_markup=InlineKeyboardMarkup(buttons))

        elif message.forward_sender_name:
            sender_name = message.forward_sender_name
            admin_state.pop(ADMIN_ID, None)
            res_text = (
                "⚠️ **ইউজার ফরোয়ার্ড প্রাইভেসি সক্রিয় রয়েছে:**\n\n"
                f"👤 **নাম:** {sender_name}\n\n"
                "🔒 টেলিগ্রামের প্রাইভেসি সেটিংসে এই ব্যবহারকারী 'Forwarded Messages -> Nobody' দিয়ে রেখেছেন। ফলে টেলিগ্রাম সরাসরি তার ইউজার আইডি প্রদান করেনি।\n\n"
                "💡 **সহজ সমাধান:**\n"
                "১. ইউজারকে বলুন বটের ইনবক্সে যেকোনো একটি মেসেজ দিতে বা `/start` চাপতে। সাথে সাথে বটের ডাটাবেজে তার আইডি চলে আসবে।\n"
                "২. অথবা তার টেলিগ্রাম `@username` সংগ্রহ করুন।\n"
                "৩. অথবা ইউজারের আইডি জানা থাকলে সরাসরি নিচের বাটনে চাপুন।"
            )
            buttons = [
                [InlineKeyboardButton("➕ ম্যানুয়াল প্রিমিয়াম", callback_data="admin_manual_prem")],
                [InlineKeyboardButton("🔎 আবার চেষ্টা করুন", callback_data="admin_extract_id")],
                [InlineKeyboardButton("🔙 অ্যাডমিন প্যানেল", callback_data="admin_back")]
            ]
            return await message.reply_text(res_text, reply_markup=InlineKeyboardMarkup(buttons))

        elif text.isdigit():
            target_id = int(text)
            register_user_id(target_id)
            user_data = get_cached_user(str(target_id))
            prem_dict = user_data.get('premium_channels', {})
            active_channels = [CHANNEL_NAMES.get(k, f"চ্যানেল {k}") for k, v in prem_dict.items() if v.get('status') == 'ACTIVE']
            status_desc = f"🌟 ভিআইপি ({', '.join(active_channels)})" if active_channels else "সাধারণ ইউজার"
            first_name = user_data.get('first_name', 'ইউজার')
            uname = f"@{user_data.get('username')}" if user_data.get('username') else "অজ্ঞাত"

            admin_state.pop(ADMIN_ID, None)
            res_text = (
                "✅ **ইউজার আইডি সফলভাবে পাওয়া গেছে!**\n\n"
                f"👤 **নাম:** {first_name}\n"
                f"🌐 **ইউজারনেম:** {uname}\n"
                f"🆔 **ইউজার আইডি:** `{target_id}`\n"
                f"📊 **বর্তমান স্ট্যাটাস:** {status_desc}\n\n"
                "👇 আপনি সরাসরি নিচের বাটনে এক ক্লিকেই কাজ করতে পারবেন:"
            )
            buttons = [
                [InlineKeyboardButton("👑 এই ইউজারকে ম্যানুয়াল প্রিমিয়াম দিন", callback_data=f"quick_mp_{target_id}")],
                [InlineKeyboardButton("🚫 প্রিমিয়াম থেকে রিমুভ করুন", callback_data=f"quick_rp_{target_id}")],
                [InlineKeyboardButton("🔗 স্পেশাল লিংক তৈরি করুন", callback_data=f"quick_spl_{target_id}")],
                [InlineKeyboardButton("✉️ এই ইউজারকে মেসেজ পাঠান", callback_data=f"quick_msg_{target_id}")],
                [InlineKeyboardButton("🔙 অ্যাডমিন প্যানেল", callback_data="admin_back")]
            ]
            return await message.reply_text(res_text, reply_markup=InlineKeyboardMarkup(buttons))

    if not state:
        return
        
    if text == "/cancel":
        admin_state.pop(ADMIN_ID, None)
        return await message.reply_text("❌ অপারেশন বাতিল করা হয়েছে।", reply_markup=get_admin_keyboard())
    
    # ১. প্রাইস পরিবর্তন
    if action == "set_price":
        try:
            new_price = int(text)
            ch = state.get("channel")
            PRICES[ch] = new_price
            if db:
                db.collection('config').document('prices').set(PRICES, merge=True)
            admin_state.pop(ADMIN_ID, None)
            await message.reply_text(f"✅ নতুন মূল্য সেট করা হয়েছে: {new_price} ৳", reply_markup=get_admin_keyboard())
        except ValueError:
            await message.reply_text("⚠️ সঠিক সংখ্যা লিখুন! (/cancel)")

    # ২. ইউজারকে রিপ্লাই পাঠানো
    elif action == "reply_user":
        target = state.get("target")
        try:
            if message.photo:
                await client.send_photo(int(target), photo=message.photo.file_id, caption=f"👨‍💻 **অ্যাডমিন সাপোর্ট:**\n\n{text}")
            elif message.video:
                await client.send_video(int(target), video=message.video.file_id, caption=f"👨‍💻 **অ্যাডমিন সাপোর্ট:**\n\n{text}")
            else:
                await client.send_message(int(target), f"👨‍💻 **অ্যাডমিন সাপোর্ট মেসেজ:**\n\n{text}")
            admin_state.pop(ADMIN_ID, None)
            await message.reply_text(f"✅ User `{target}` এর কাছে মেসেজ সফলভাবে পাঠানো হয়েছে।", reply_markup=get_admin_keyboard())
        except Exception as e:
            await message.reply_text(f"❌ মেসেজ পাঠাতে ব্যর্থ: {e}")

    # ৩. ফুল ব্রডকাস্ট (টেক্সট, ছবি বা ভিডিও) - Zero Firestore Reads
    elif action == "broadcast":
        admin_state.pop(ADMIN_ID, None)
        await message.reply_text("📢 ফুল ব্রডকাস্ট পাঠানো শুরু হচ্ছে...")
        sent, fail = 0, 0
        
        caption = message.caption or message.text or ""
        media_type = 'photo' if message.photo else ('video' if message.video else ('document' if message.document else ('animation' if message.animation else 'text')))
        file_id = message.photo.file_id if message.photo else (message.video.file_id if message.video else (message.document.file_id if message.document else (message.animation.file_id if message.animation else None)))
        
        btn = InlineKeyboardMarkup([[InlineKeyboardButton("💎 এখুনি প্রিমিয়াম কিনুন", callback_data="back_to_pkg")]])
        
        target_users = list(REGISTERED_USERS_SET)
        if not target_users and db:
            try:
                users = list(db.collection('users').stream())
                for u in users:
                    register_user_id(u.id)
                target_users = list(REGISTERED_USERS_SET)
            except: pass

        for uid_str in target_users:
            try:
                uid = int(uid_str)
                if media_type == 'photo':
                    await client.send_photo(uid, photo=file_id, caption=caption, reply_markup=btn)
                elif media_type == 'video':
                    await client.send_video(uid, video=file_id, caption=caption, reply_markup=btn)
                elif media_type == 'document':
                    await client.send_document(uid, document=file_id, caption=caption, reply_markup=btn)
                elif media_type == 'animation':
                    await client.send_animation(uid, animation=file_id, caption=caption, reply_markup=btn)
                else:
                    await client.send_message(uid, caption, reply_markup=btn)
                sent += 1
                await asyncio.sleep(0.04)
            except:
                fail += 1
        await message.reply_text(f"✅ ব্রডকাস্ট সমাপ্ত!\nসফল: {sent}\nব্যর্থ: {fail}", reply_markup=get_admin_keyboard())

    # ৪. নির্দিষ্ট ব্রডকাস্ট (ধাপ ১: User ID গ্রহণ)
    elif action in ["specific_cast_id", "specific_cast_uid"]:
        clean_uid = text.replace("`", "").strip()
        if not clean_uid.isdigit():
            return await message.reply_text("⚠️ সঠিক টেলিগ্রাম User ID (সংখ্যা) লিখে পাঠান! (/cancel)")
            
        target_uid = int(clean_uid)
        admin_state[ADMIN_ID] = {"action": "specific_cast_msg", "target_uid": target_uid}
        await message.reply_text(
            f"📝 **User `{target_uid}` এর জন্য ব্রডকাস্ট মেসেজ পাঠান:**\n\n"
            "আপনি যেকোনো সাধারণ টেক্সট মেসেজ, অথবা ছবি/ভিডিও সহ ক্যাপশন পাঠাতে পারেন। যা পাঠাবেন তা হুবহু ইউজারের কাছে চলে যাবে।\n\n"
            "(বাতিল করতে /cancel)"
        )

    # ৪. নির্দিষ্ট ব্রডকাস্ট (ধাপ ২: মেসেজ/মিডিয়া পাঠানো)
    elif action == "specific_cast_msg":
        target_uid = state.get("target_uid")
        admin_state.pop(ADMIN_ID, None)
        try:
            caption = message.caption or message.text or ""
            btn = InlineKeyboardMarkup([[InlineKeyboardButton("💎 এখুনি প্রিমিয়াম কিনুন", callback_data="back_to_pkg")]])
            
            if message.photo:
                await client.send_photo(target_uid, photo=message.photo.file_id, caption=caption, reply_markup=btn)
            elif message.video:
                await client.send_video(target_uid, video=message.video.file_id, caption=caption, reply_markup=btn)
            elif message.document:
                await client.send_document(target_uid, document=message.document.file_id, caption=caption, reply_markup=btn)
            elif message.animation:
                await client.send_animation(target_uid, animation=message.animation.file_id, caption=caption, reply_markup=btn)
            else:
                await client.send_message(target_uid, caption, reply_markup=btn)
                
            await message.reply_text(f"✅ **User `{target_uid}` এর কাছে নির্দিষ্ট ব্রডকাস্ট সফলভাবে পাঠানো হয়েছে!**", reply_markup=get_admin_keyboard())
        except Exception as e:
            await message.reply_text(f"❌ ব্রডকাস্ট পাঠাতে ব্যর্থ: {e}", reply_markup=get_admin_keyboard())

    # ৫. ম্যানুয়াল প্রিমিয়াম User ID ইনপুট
    elif action in ["manual_prem_id", "manual_prem_uid"]:
        clean_uid = text.replace("`", "").strip()
        if not clean_uid.isdigit():
            return await message.reply_text("⚠️ সঠিক টেলিগ্রাম User ID (সংখ্যা) লিখে পাঠান! (/cancel)")
            
        admin_state[ADMIN_ID] = {"action": "manual_prem_select", "target_uid": clean_uid, "selected": []}
        await render_manual_prem_selection(message, clean_uid, edit=False)

    # ৬. প্রিমিয়াম রিমুভ User ID ইনপুট
    elif action in ["remprem_uid", "remove_prem_id"]:
        clean_uid = text.replace("`", "").strip()
        if not clean_uid.isdigit():
            return await message.reply_text("⚠️ সঠিক টেলিগ্রাম User ID (সংখ্যা) লিখে পাঠান! (/cancel)")
            
        admin_state[ADMIN_ID] = {"action": "remprem_select", "target_uid": clean_uid, "selected": []}
        await render_remprem_selection(message, clean_uid, edit=False)

    # ৭. স্পেশাল লিংক User ID ইনপুট
    elif action == "special_link_uid":
        clean_uid = text.replace("`", "").strip()
        if not clean_uid.isdigit():
            return await message.reply_text("⚠️ সঠিক টেলিগ্রাম User ID (সংখ্যা) লিখে পাঠান! (/cancel)")
            
        admin_state[ADMIN_ID] = {"action": "special_link_select", "target_uid": clean_uid, "selected": []}
        await render_special_link_selection(message, clean_uid, edit=False)

    # ৮. অটো পোস্ট সেটআপ (ধাপ ১: পোস্ট কনটেন্ট)
    elif action == "autopost_step1":
        caption = message.caption or message.text or ""
        media_type = 'photo' if message.photo else ('video' if message.video else ('document' if message.document else ('animation' if message.animation else 'text')))
        file_id = message.photo.file_id if message.photo else (message.video.file_id if message.video else (message.document.file_id if message.document else (message.animation.file_id if message.animation else None)))
        
        post_data = {
            'media_type': media_type,
            'file_id': file_id,
            'caption': caption
        }
        admin_state[ADMIN_ID] = {"action": "autopost_step2", "post_data": post_data}
        await message.reply_text(
            "⏰ **অটো পোস্ট সেটআপ (ধাপ ২/২):**\n\n"
            "পোস্টটি কত মিনিট পর পর পাঠানো হবে? (মিনিটের সংখ্যা লিখুন)\n\n"
            "উদাহরণ:\n"
            "• ৩০ মিনিট পর পর = `30`\n"
            "• ১ ঘণ্টা পর পর = `60`\n"
            "• ২ ঘণ্টা পর পর = `120`\n"
            "• ৬ ঘণ্টা পর পর = `360`\n"
            "• ১২ ঘণ্টা পর পর = `720`\n"
            "• ২৪ ঘণ্টা পর পর = `1440`\n\n"
            "মিনিটের সংখ্যা লিখে পাঠান: (/cancel)"
        )

    # ৮. অটো পোস্ট সেটআপ (ধাপ ২: বিরতির সময়)
    elif action == "autopost_step2":
        try:
            interval = int(text)
            if interval < 1:
                return await message.reply_text("⚠️ বিরতির সময় কমপক্ষে ১ মিনিট হতে হবে! সঠিক সংখ্যা লিখুন:")
                
            post_data = state.get("post_data", {})
            AUTO_POST_CONFIG.update({
                'running': True,
                'interval': interval,
                'media_type': post_data.get('media_type', 'text'),
                'file_id': post_data.get('file_id'),
                'caption': post_data.get('caption', ''),
                'total_sent': 0,
                'last_sent': None
            })
            
            if db:
                try:
                    db.collection('config').document('autopost').set({
                        'running': True,
                        'interval': interval,
                        'media_type': post_data.get('media_type', 'text'),
                        'file_id': post_data.get('file_id'),
                        'caption': post_data.get('caption', ''),
                        'total_sent': 0,
                        'last_sent': None
                    }, merge=True)
                except Exception as e:
                    print(f"Db save autopost error: {e}")
                    
            restart_autopost_worker(client)
            admin_state.pop(ADMIN_ID, None)
            
            await message.reply_text(
                f"✅ **অটো পোস্ট সফলভাবে সেট ও চালু করা হয়েছে!**\n\n"
                f"⏳ প্রতি **{interval} মিনিট** পর পর বট স্বয়ংক্রিয়ভাবে সবার কাছে এই পোস্টটি ব্রডকাস্ট করবে।",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⏰ অটো পোস্ট ড্যাশবোর্ড দেখুন", callback_data="admin_autopost")],
                    [InlineKeyboardButton("🔙 অ্যাডমিন প্যানেল", callback_data="admin_back")]
                ])
            )
        except ValueError:
            await message.reply_text("⚠️ সঠিক সংখ্যা লিখুন! যেমন: 60 (/cancel)")

    # ৯. ইউজার আইডি দিয়ে কিক টেস্ট
    elif action == "test_kick_uid":
        try:
            target_uid = int(text)
            admin_state.pop(ADMIN_ID, None)
            c_id = CHANNELS.get("1", 0)
            c_name = CHANNEL_NAMES.get("1", "চ্যানেল ১")
            await message.reply_text(f"⏳ User `{target_uid}` কে {c_name} থেকে কিক করার টেস্ট চলছে...")
            ok, err = await execute_kick_user(target_uid, c_id, c_name, reason="FORCE_KICK")
            if ok:
                await message.reply_text(f"✅ **টেস্ট সফল!** User `{target_uid}` কে {c_name} থেকে সফলভাবে কিক করা হয়েছে!", reply_markup=get_admin_keyboard())
            else:
                await message.reply_text(f"❌ **কিক টেস্ট ব্যর্থ!**\n\nএরর: `{err}`\n\nবটের ওই চ্যানেলে 'Ban Users' পারমিশন অন আছে কিনা চেক করুন।", reply_markup=get_admin_keyboard())
        except ValueError:
            await message.reply_text("⚠️ সঠিক টেলিগ্রাম User ID লিখুন! (/cancel)")

    # ১০. ওয়েলকাম টেক্সট পরিবর্তন
    elif action == "welcome_edit_text":
        if not text:
            return await message.reply_text("⚠️ দয়া করে টেক্সট মেসেজ লিখুন! (/cancel)")
        WELCOME_CONFIG['text'] = text
        save_bot_settings()
        admin_state.pop(ADMIN_ID, None)
        await message.reply_text("✅ **ওয়েলকাম মেসেজ সফলভাবে আপডেট করা হয়েছে!**", reply_markup=get_admin_keyboard())

    # ১১. ওয়েলকাম ফটো/ভিডিও সেট করা
    elif action == "welcome_set_media":
        if message.photo:
            WELCOME_CONFIG['media_type'] = 'photo'
            WELCOME_CONFIG['file_id'] = message.photo.file_id
        elif message.video:
            WELCOME_CONFIG['media_type'] = 'video'
            WELCOME_CONFIG['file_id'] = message.video.file_id
        else:
            return await message.reply_text("⚠️ দয়া করে একটি ফটো অথবা ভিডিও পাঠান! (/cancel)")

        if message.caption:
            WELCOME_CONFIG['text'] = message.caption

        save_bot_settings()
        admin_state.pop(ADMIN_ID, None)
        await message.reply_text("✅ **ওয়েলকাম ফটো/ভিডিও সফলভাবে সেট করা হয়েছে!**", reply_markup=get_admin_keyboard())

    # ১২. 'কিভাবে কিনবেন' টেক্সট পরিবর্তন
    elif action == "howtobuy_edit_text":
        if not text:
            return await message.reply_text("⚠️ দয়া করে টেক্সট মেসেজ লিখুন! (/cancel)")
        HOW_TO_BUY_CONFIG['text'] = text
        save_bot_settings()
        admin_state.pop(ADMIN_ID, None)
        await message.reply_text("✅ **'কিভাবে কিনবেন' মেসেজ সফলভাবে আপডেট করা হয়েছে!**", reply_markup=get_admin_keyboard())

    # ১৩. 'কিভাবে কিনবেন' ফটো/ভিডিও সেট করা
    elif action == "howtobuy_set_media":
        if message.photo:
            HOW_TO_BUY_CONFIG['media_type'] = 'photo'
            HOW_TO_BUY_CONFIG['file_id'] = message.photo.file_id
        elif message.video:
            HOW_TO_BUY_CONFIG['media_type'] = 'video'
            HOW_TO_BUY_CONFIG['file_id'] = message.video.file_id
        else:
            return await message.reply_text("⚠️ দয়া করে একটি ফটো অথবা ভিডিও পাঠান! (/cancel)")

        if message.caption:
            HOW_TO_BUY_CONFIG['text'] = message.caption

        save_bot_settings()
        admin_state.pop(ADMIN_ID, None)
        await message.reply_text("✅ **'কিভাবে কিনবেন' ফটো/ভিডিও সফলভাবে সেট করা হয়েছে!**", reply_markup=get_admin_keyboard())

# ================= ১৪. ওয়েব সার্ভার ও Webhook রিসিভার =================
async def handle_ping(request):
    return web.Response(text="✅ AutoPay VIP Bot Server is UP and Running!")

async def handle_webapp(request):
    html_content = f"""<!DOCTYPE html>
<html lang="bn">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>PREMIUM GROUP BUY - VIP Store</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        :root {{
            --bg-color: #0f172a;
            --card-bg: #1e293b;
            --text-color: #f8fafc;
            --text-muted: #94a3b8;
        }}
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            -webkit-tap-highlight-color: transparent;
        }}
        body {{
            background: var(--bg-color);
            color: var(--text-color);
            padding: 16px;
            padding-bottom: 40px;
        }}
        .header {{
            text-align: center;
            margin-bottom: 20px;
        }}
        .header h1 {{
            font-size: 20px;
            font-weight: 800;
            background: linear-gradient(135deg, #38bdf8, #818cf8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 6px;
        }}
        .header p {{
            font-size: 13px;
            color: var(--text-muted);
        }}
        .section-title {{
            font-size: 14px;
            font-weight: 700;
            margin: 16px 0 10px 0;
            display: flex;
            align-items: center;
            gap: 6px;
            color: #e2e8f0;
        }}
        .grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            margin-bottom: 16px;
        }}
        .btn-full {{
            grid-column: span 2;
        }}
        .color-btn {{
            border: none;
            outline: none;
            border-radius: 14px;
            padding: 16px 14px;
            cursor: pointer;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            gap: 6px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        }}
        .color-btn:active {{
            transform: scale(0.97);
            filter: brightness(1.1);
        }}
        /* ফুল কালার বাটন গ্রেডিয়েন্ট */
        .btn-red {{
            background: linear-gradient(135deg, #ef4444 0%, #b91c1c 100%);
            color: #ffffff;
            box-shadow: 0 6px 16px rgba(239, 68, 68, 0.35);
        }}
        .btn-orange {{
            background: linear-gradient(135deg, #f97316 0%, #c2410c 100%);
            color: #ffffff;
            box-shadow: 0 6px 16px rgba(249, 115, 22, 0.35);
        }}
        .btn-purple {{
            background: linear-gradient(135deg, #a855f7 0%, #6b21a8 100%);
            color: #ffffff;
            box-shadow: 0 6px 16px rgba(168, 85, 247, 0.35);
        }}
        .btn-gold {{
            background: linear-gradient(135deg, #eab308 0%, #ca8a04 100%);
            color: #111827;
            font-weight: 800;
            border: 2px solid #fef08a;
            box-shadow: 0 8px 22px rgba(234, 179, 8, 0.45);
        }}
        .btn-bkash {{
            background: linear-gradient(135deg, #e2136e 0%, #9f0d4d 100%);
            color: #ffffff;
            box-shadow: 0 6px 16px rgba(226, 19, 110, 0.35);
        }}
        .btn-nagad {{
            background: linear-gradient(135deg, #f97316 0%, #ea580c 100%);
            color: #ffffff;
            box-shadow: 0 6px 16px rgba(249, 115, 22, 0.35);
        }}
        .btn-rocket {{
            background: linear-gradient(135deg, #8b5cf6 0%, #5b21b6 100%);
            color: #ffffff;
            box-shadow: 0 6px 16px rgba(139, 92, 246, 0.35);
        }}
        .btn-upay {{
            background: linear-gradient(135deg, #f59e0b 0%, #b45309 100%);
            color: #ffffff;
            box-shadow: 0 6px 16px rgba(245, 158, 11, 0.35);
        }}
        .color-btn .icon {{
            font-size: 26px;
        }}
        .color-btn .title {{
            font-size: 15px;
            font-weight: 700;
        }}
        .color-btn .price {{
            font-size: 14px;
            font-weight: 800;
            background: rgba(0,0,0,0.25);
            padding: 3px 10px;
            border-radius: 20px;
        }}
        .btn-gold .price {{
            background: rgba(0,0,0,0.7);
            color: #fef08a;
        }}
        .selected {{
            outline: 3px solid #38bdf8;
            outline-offset: 2px;
            transform: scale(1.02);
        }}
        .card {{
            background: var(--card-bg);
            border-radius: 16px;
            padding: 16px;
            margin-top: 14px;
            border: 1px solid rgba(255,255,255,0.06);
        }}
        .copy-box {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: #0f172a;
            border-radius: 10px;
            padding: 10px 14px;
            margin: 10px 0;
            border: 1px dashed #38bdf8;
        }}
        .copy-num {{
            font-size: 16px;
            font-weight: 800;
            color: #38bdf8;
            letter-spacing: 1px;
        }}
        .copy-btn {{
            background: #38bdf8;
            color: #0f172a;
            border: none;
            padding: 6px 12px;
            border-radius: 8px;
            font-weight: 700;
            font-size: 12px;
            cursor: pointer;
        }}
        .input-group {{
            margin-top: 14px;
        }}
        .input-group label {{
            display: block;
            font-size: 13px;
            font-weight: 600;
            margin-bottom: 6px;
            color: #cbd5e1;
        }}
        .input-group input {{
            width: 100%;
            padding: 12px 14px;
            border-radius: 10px;
            border: 1px solid #475569;
            background: #0f172a;
            color: #ffffff;
            font-size: 15px;
            text-transform: uppercase;
        }}
        .input-group input:focus {{
            outline: none;
            border-color: #38bdf8;
        }}
        .submit-btn {{
            width: 100%;
            padding: 15px;
            margin-top: 16px;
            border: none;
            border-radius: 12px;
            background: linear-gradient(135deg, #10b981 0%, #047857 100%);
            color: #ffffff;
            font-size: 16px;
            font-weight: 800;
            cursor: pointer;
            box-shadow: 0 6px 18px rgba(16, 185, 129, 0.4);
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }}
        .submit-btn:active {{
            transform: scale(0.98);
        }}
        .footer-links {{
            margin-top: 24px;
            display: flex;
            gap: 10px;
        }}
        .secondary-btn {{
            flex: 1;
            padding: 12px;
            border-radius: 10px;
            background: #334155;
            color: #f8fafc;
            border: none;
            font-size: 13px;
            font-weight: 600;
            text-align: center;
            text-decoration: none;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>✨ PREMIUM VIP STORE ✨</h1>
        <p>নিচে আপনার প্যাকেজ ও পেমেন্ট মাধ্যম বেছে নিন</p>
    </div>

    <div class="section-title">📦 ১. প্যাকেজ নির্বাচন করুন:</div>
    <div class="grid">
        <button class="color-btn btn-red selected" onclick="selectPkg(1, {PRICES['1']}, this)">
            <span class="icon">📺</span>
            <span class="title">১টি চ্যানেল</span>
            <span class="price">{PRICES['1']} ৳</span>
        </button>
        <button class="color-btn btn-orange" onclick="selectPkg(2, {PRICES['2']*2}, this)">
            <span class="icon">🎬</span>
            <span class="title">২টি চ্যানেল</span>
            <span class="price">{PRICES['2']*2} ৳</span>
        </button>
        <button class="color-btn btn-purple" onclick="selectPkg(3, {PRICES['3']*3}, this)">
            <span class="icon">🔥</span>
            <span class="title">৩টি চ্যানেল</span>
            <span class="price">{PRICES['3']*3} ৳</span>
        </button>
        <button class="color-btn btn-gold btn-full" onclick="selectPkg(4, {PRICES['all']}, this)">
            <span class="icon">👑</span>
            <span class="title">৪টি চ্যানেল (ফুল বান্ডেল অফার)</span>
            <span class="price">{PRICES['all']} ৳ (Lifetime)</span>
        </button>
    </div>

    <div class="section-title">💳 ২. পেমেন্ট মাধ্যম নির্বাচন করুন:</div>
    <div class="grid">
        <button class="color-btn btn-bkash selected" onclick="selectMethod('বিকাশ (bKash)', this)">
            <span class="icon">🔴</span>
            <span class="title">বিকাশ</span>
        </button>
        <button class="color-btn btn-nagad" onclick="selectMethod('নগদ (Nagad)', this)">
            <span class="icon">🟠</span>
            <span class="title">নগদ</span>
        </button>
        <button class="color-btn btn-rocket" onclick="selectMethod('রকেট (Rocket)', this)">
            <span class="icon">🟣</span>
            <span class="title">রকেট</span>
        </button>
        <button class="color-btn btn-upay" onclick="selectMethod('উপায় (Upay)', this)">
            <span class="icon">🟡</span>
            <span class="title">উপায়</span>
        </button>
    </div>

    <div class="card">
        <div style="font-size: 13px; color: #94a3b8; line-height: 1.5;">
            নিচের পার্সোনাল নাম্বারে <strong id="lbl-method" style="color:#f8fafc">বিকাশ</strong> অ্যাপ দিয়ে ঠিক <strong id="lbl-price" style="color:#38bdf8">{PRICES['1']} ৳</strong> Send Money করুন:
        </div>
        <div class="copy-box">
            <span class="copy-num" id="payNumber">{PAYMENT_NUMBER}</span>
            <button class="copy-btn" onclick="copyNumber()">📋 কপি করুন</button>
        </div>
        <div class="input-group">
            <label for="trxInput">টাকা পাঠানোর পর TrxID লিখুন:</label>
            <input type="text" id="trxInput" placeholder="যেমন: DIR584YB78" maxlength="15">
        </div>
        <button class="submit-btn" onclick="submitTrx()">
            ⚡️ সাবমিট করুন ও জয়েন লিংক পান
        </button>
    </div>

    <div class="footer-links">
        <a class="secondary-btn" href="https://t.me/ItsSaddam9" target="_blank">👨‍💻 লাইভ সাপোর্ট</a>
        <a class="secondary-btn" href="https://t.me/Premium_payment_pruf" target="_blank">✅ পেমেন্ট প্রুফ</a>
    </div>

    <script>
        const tg = window.Telegram?.WebApp;
        if (tg) {{
            tg.ready();
            tg.expand();
        }}

        let selectedPkg = 1;
        let selectedAmount = {PRICES['1']};
        let selectedMethod = 'বিকাশ (bKash)';

        function selectPkg(num, price, btn) {{
            selectedPkg = num;
            selectedAmount = price;
            document.querySelectorAll('.grid:first-of-type .color-btn').forEach(b => b.classList.remove('selected'));
            btn.classList.add('selected');
            document.getElementById('lbl-price').innerText = price + ' ৳';
        }}

        function selectMethod(method, btn) {{
            selectedMethod = method;
            document.querySelectorAll('.grid:last-of-type .color-btn').forEach(b => b.classList.remove('selected'));
            btn.classList.add('selected');
            document.getElementById('lbl-method').innerText = method;
        }}

        function copyNumber() {{
            const num = document.getElementById('payNumber').innerText;
            navigator.clipboard.writeText(num).then(() => {{
                if (tg && tg.showAlert) tg.showAlert('পার্সোনাল নাম্বার কপি করা হয়েছে: ' + num);
                else alert('নাম্বার কপি হয়েছে: ' + num);
            }});
        }}

        function submitTrx() {{
            const trx = document.getElementById('trxInput').value.trim();
            if (!trx || trx.length < 6) {{
                if (tg && tg.showAlert) tg.showAlert('সঠিক Transaction ID (TrxID) লিখুন!');
                else alert('সঠিক Transaction ID লিখুন!');
                return;
            }}
            if (tg) {{
                tg.sendData(JSON.stringify({{
                    action: 'web_payment',
                    pkg: selectedPkg,
                    amount: selectedAmount,
                    method: selectedMethod,
                    trx_id: trx
                }}));
                tg.close();
            }} else {{
                alert('পেমেন্ট TrxID (' + trx + ') বটে পাঠানো হয়েছে। অনুগ্রহ করে বটের চ্যাটে দেখুন!');
                window.location.href = "https://t.me/PREMIUM_GROUP_BUY_BOT";
            }}
        }}
    </script>
</body>
</html>"""
    return web.Response(text=html_content, content_type='text/html')

async def handle_sms_webhook(request):
    try:
        data = await request.json()
        print(f"📥 Received Webhook Data: {data}")

        trx_id = str(data.get("trx_id") or data.get("trxId") or "").strip().upper()
        amount = float(data.get("amount", 0))
        provider = data.get("provider", "UNKNOWN")
        raw_sms = data.get("raw_sms", "")
        sender_phone = data.get("sender_phone", "")

        if trx_id:
            payment_obj = {
                "trx_id": trx_id,
                "amount": amount,
                "provider": provider,
                "sender_phone": sender_phone,
                "raw_sms": raw_sms,
                "used": False,
                "timestamp": datetime.now().isoformat()
            }
            received_sms_cache[trx_id] = payment_obj

            if db:
                try:
                    db.collection("sms_payments").document(trx_id).set(payment_obj, merge=True)
                except Exception as e:
                    print(f"Firestore save error: {e}")

            for uid, wait_data in list(waiting_for_payment.items()):
                user_pending_trx = wait_data.get("trx_id", "")
                if user_pending_trx == trx_id:
                    expected_amount = float(wait_data["amount"])
                    if amount == expected_amount:
                        payment_obj["used"] = True
                        if db:
                            db.collection("sms_payments").document(trx_id).update({"used": True, "used_by": uid})
                        asyncio.create_task(process_success_approval(app, uid, wait_data, trx_id, is_auto=True))
                    elif amount < expected_amount:
                        asyncio.create_task(app.send_message(
                            uid, 
                            f"❌ **ভেরিফিকেশন ব্যর্থ (টাকা কম দেওয়া হয়েছে)!**\n\n📦 প্যাকেজের মূল্য: {expected_amount} ৳\n💸 আপনি পাঠিয়েছেন: {amount} ৳\n\nসিস্টেম কম টাকা গ্রহণ করে না।"
                        ))
                    elif amount > expected_amount:
                        asyncio.create_task(app.send_message(
                            uid, 
                            f"❌ **ভেরিফিকেশন ব্যর্থ (টাকা বেশি দেওয়া হয়েছে)!**\n\n📦 প্যাকেজের মূল্য: {expected_amount} ৳\n💸 আপনি পাঠিয়েছেন: {amount} ৳\n\nনির্ধারিত মূল্যের চেয়ে বেশি টাকা দেওয়ায় অটো সিস্টেম গ্রহণ করেনি।"
                        ))

            return web.json_response({
                "status": "success",
                "message": f"Payment SMS received for TrxID {trx_id}",
                "amount": amount
            })

        return web.json_response({"status": "ignored", "message": "No TrxID provided"}, status=200)

    except Exception as e:
        traceback.print_exc()
        return web.json_response({"status": "error", "message": str(e)}, status=400)

async def start_web_server():
    app_web = web.Application()
    app_web.router.add_get('/', handle_webapp)
    app_web.router.add_get('/shop', handle_webapp)
    app_web.router.add_get('/ping', handle_ping)
    app_web.router.add_post('/webhook', handle_sms_webhook)
    app_web.router.add_post('/api/payment-webhook', handle_sms_webhook)
    
    runner = web.AppRunner(app_web)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    print(f"✅ Webhook & Full-Color WebApp Server started on port {PORT}")

# ================= ১৫. মেইন ফাংশন =================
background_tasks = set()

async def main():
    global db, PRICES
    try:
        try:
            cred = credentials.Certificate("firebase_cred.json") 
            if not firebase_admin._apps:
                firebase_admin.initialize_app(cred)
            db = firestore.client()
            print("✅ Firebase Firestore connected successfully!")
        except Exception as e:
            print(f"⚠️ Firebase initialization skipped or cred missing: {e}")
        
        if db:
            try:
                price_doc = db.collection('config').document('prices').get()
                if price_doc.exists:
                    PRICES.update(price_doc.to_dict())
                    print(f"✅ Loaded prices from Firebase: {PRICES}")
            except Exception as e:
                print(f"Price load error: {e}")

            try:
                ap_doc = db.collection('config').document('autopost').get()
                if ap_doc.exists:
                    ap_data = ap_doc.to_dict()
                    AUTO_POST_CONFIG.update(ap_data)
                    print(f"✅ Loaded AutoPost config from Firebase: running={AUTO_POST_CONFIG.get('running')}")
            except Exception as e:
                print(f"Autopost config load error: {e}")

            try:
                bs_doc = db.collection('config').document('bot_settings').get()
                if bs_doc.exists:
                    bs_data = bs_doc.to_dict()
                    if 'colorful_buttons' in bs_data:
                        COLORFUL_BUTTONS = bs_data['colorful_buttons']
                    if 'welcome' in bs_data:
                        WELCOME_CONFIG.update(bs_data['welcome'])
                    if 'how_to_buy' in bs_data:
                        HOW_TO_BUY_CONFIG.update(bs_data['how_to_buy'])
                    save_bot_settings()
                    print(f"✅ Loaded bot settings from Firebase!")
            except Exception as e:
                print(f"Bot settings load error: {e}")
        
        load_local_registered_users()
        if len(REGISTERED_USERS_SET) == 0 and db:
            try:
                user_docs = list(db.collection('users').stream())
                for d in user_docs:
                    register_user_id(d.id)
                print(f"✅ Initialized {len(REGISTERED_USERS_SET)} users into local cache from Firebase!")
            except Exception as e:
                print(f"User sync error: {e}")
        
        await start_web_server()
        await app.start()
        print("✅ Telegram VIP Bot is running successfully!")
        
        # স্টার্টআপে পূর্বে রানিং ট্রায়ালগুলো লোড ও রিজ্যুম করা
        await load_and_resume_active_trials()

        # পূর্বে সক্রিয় থাকলে অটো পোস্ট কর্মী চালু করা
        if AUTO_POST_CONFIG.get('running'):
            restart_autopost_worker(app)

        # মেমোরি সেফটি সুইপার টাস্ক (Firebase Quota 0 খরচ করে)
        sweeper_task = asyncio.create_task(in_memory_trial_sweeper())
        background_tasks.add(sweeper_task)

        await idle()
        await app.stop()
    except Exception as e:
        traceback.print_exc()

if __name__ == "__main__":
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        traceback.print_exc()
