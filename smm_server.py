#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SMM Platform Server & Telegram Bot Engine
Features:
- Telegram Mini App (Web App) served on Cloud Run Port 8080
- Telegram Bot polling engine using pure Python Standard Library (0 external dependencies)
- SQLite database for users, services, orders, deposits, and transactions
- JustAnotherPanel (JAP) API V2 integration
- Instant notifications to User, Admin, and Proof Channel
"""

import os
import sys
import json
import time
import sqlite3
import threading
import urllib.request
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

# ================= CONFIGURATION =================
PORT = 3000
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8893514341:AAFIH0yATe_m28lTETkEu36GSmmoz4NkrsU")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 8701368956))
ADMIN_USERNAME = "ItsSaddam9"
PAYMENT_NUMBER = "01985664862"
PROOF_CHANNEL_LINK = "https://t.me/+LFH-8mX0MJljYWU9"
PROOF_CHANNEL_CHAT_ID = os.environ.get("PROOF_CHANNEL_CHAT_ID", "") # Can be set if bot is added as admin

JAP_API_URL = "https://justanotherpanel.com/api/v2"
JAP_API_KEY = "58ad025b6b241ff6b5ba0aff5368bf42"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEBAPP_URL = "https://ais-dev-vksa5zmsuo3umrd73oedyl-475005245439.asia-southeast1.run.app"
DB_FILE = os.path.join(BASE_DIR, "smm_store.db")
HTML_FILE = os.path.join(BASE_DIR, "webapp.html")

# ================= DATABASE INITIALIZATION =================
def get_db():
    conn = sqlite3.connect(DB_FILE, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Users Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            username TEXT,
            balance REAL DEFAULT 0.0,
            total_deposit REAL DEFAULT 0.0,
            total_spent REAL DEFAULT 0.0,
            total_orders INTEGER DEFAULT 0,
            ref_by INTEGER DEFAULT 0,
            ref_earnings REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Services Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service_id INTEGER,
            platform TEXT,
            category TEXT,
            name TEXT,
            price_bdt REAL,
            cost_bdt REAL,
            min_order INTEGER,
            max_order INTEGER
        )
        """)
        
        # Orders Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            service_id INTEGER,
            service_name TEXT,
            platform TEXT,
            category TEXT,
            link TEXT,
            quantity INTEGER,
            charge REAL,
            status TEXT DEFAULT 'pending',
            jap_order_id TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Deposits Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS deposits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            method TEXT,
            amount REAL,
            trxid TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        conn.commit()
    seed_services()

def seed_services():
    services_data = [
        # --- TIKTOK ---
        (8526, 'tiktok', 'views', 'TikTok Video Views [10M] [30D Refill]', 7.00, 3.82, 100, 10000000),
        (10331, 'tiktok', 'likes', 'TikTok Video Likes [Fast] [HQ]', 30.00, 16.78, 50, 500000),
        (10136, 'tiktok', 'followers', 'TikTok Followers [HQ Non-Drop]', 200.00, 134.20, 100, 50000),
        (4134, 'tiktok', 'shares', 'TikTok Video Shares [Instant]', 4.00, 1.50, 100, 500000),
        (8532, 'tiktok', 'comments', 'TikTok Random Comments [Real Users]', 45.00, 25.00, 10, 5000),
        (8540, 'tiktok', 'live_stream', 'TikTok Live Stream Views [15 Min]', 70.00, 40.00, 50, 10000),

        # --- FACEBOOK ---
        (9572, 'facebook', 'views', 'Facebook Reels / Video Views [Instant]', 2.00, 0.77, 100, 5000000),
        (2936, 'facebook', 'reactions', 'Facebook Post Reactions [Love ❤️] [Fast]', 25.00, 13.71, 50, 10000),
        (2895, 'facebook', 'reactions', 'Facebook Post Reactions [Care 🥰]', 25.00, 13.71, 50, 10000),
        (2913, 'facebook', 'reactions', 'Facebook Post Reactions [Haha 😀]', 25.00, 13.71, 50, 10000),
        (5787, 'facebook', 'followers', 'Facebook Page Likes + Followers [90D Refill]', 60.00, 34.77, 50, 100000),
        (8891, 'facebook', 'watch_time', 'Facebook 60k Minutes Watch Time Pack', 130.00, 80.00, 100, 100000),
        (3110, 'facebook', 'comments', 'Facebook Custom Comments [Bangladesh/Mix]', 75.00, 45.00, 10, 5000),
        (4210, 'facebook', 'shares', 'Facebook Post Shares [HQ Public]', 28.00, 15.00, 50, 10000),

        # --- INSTAGRAM ---
        (3528, 'instagram', 'views', 'Instagram Reels / Video Views [Super Fast]', 2.00, 0.77, 100, 10000000),
        (8216, 'instagram', 'likes', 'Instagram Likes [Instant Delivery]', 3.00, 1.53, 50, 100000),
        (1806, 'instagram', 'followers', 'Instagram Followers [HQ Real Looking]', 48.00, 26.96, 100, 250000),
        (4510, 'instagram', 'comments', 'Instagram Random Positive Comments', 55.00, 30.00, 10, 5000),
        (5120, 'instagram', 'views', 'Instagram Story Views [All Active Stories]', 5.00, 2.50, 100, 50000),
        (9920, 'instagram', 'special', 'Instagram Verified / Blue Tick Impressions', 380.00, 250.00, 50, 1000),

        # --- YOUTUBE ---
        (5971, 'youtube', 'views', 'YouTube Video Views [High Retention] [Refill]', 75.00, 47.58, 100, 1000000),
        (7978, 'youtube', 'likes', 'YouTube Video / Shorts Likes [Non-Drop]', 150.00, 99.12, 50, 50000),
        (9186, 'youtube', 'followers', 'YouTube Channel Subscribers [30D Refill]', 115.00, 76.25, 50, 10000),
        (8910, 'youtube', 'watch_time', 'YouTube 4000 Hours Monetization Pack', 350.00, 220.00, 100, 10000),
        (6120, 'youtube', 'comments', 'YouTube Custom Comments [English/Bengali]', 85.00, 50.00, 10, 5000),
        (7210, 'youtube', 'live_stream', 'YouTube Live Stream Concurrent Viewers', 130.00, 80.00, 50, 5000),

        # --- TELEGRAM ---
        (10032, 'telegram', 'views', 'Telegram Post Views [Instant Fast]', 1.00, 0.39, 100, 500000),
        (7158, 'telegram', 'members', 'Telegram Channel Members [7D Refill]', 32.00, 17.54, 50, 50000),
        (9012, 'telegram', 'reactions', 'Telegram Post Emoji Reactions [👍 / ❤️ / 🔥]', 4.50, 2.00, 50, 20000),
        (6820, 'telegram', 'members', 'Telegram Group Members [Zero Drop]', 38.00, 22.00, 50, 30000),
        (9510, 'telegram', 'special', 'Telegram Premium Member Boosts', 230.00, 150.00, 1, 100),

        # --- TWITTER (X) ---
        (4910, 'twitter', 'views', 'Twitter (X) Video / Tweet Views', 5.00, 2.50, 100, 1000000),
        (4920, 'twitter', 'likes', 'Twitter (X) Tweet Likes / Hearts', 45.00, 25.00, 50, 50000),
        (4930, 'twitter', 'followers', 'Twitter (X) Followers [Real Looking]', 130.00, 80.00, 50, 10000),
        (4940, 'twitter', 'shares', 'Twitter (X) Retweets [Instant]', 55.00, 30.00, 50, 20000),

        # --- WEBSITE ---
        (5110, 'website', 'views', 'Website Organic Google Traffic [High Duration]', 28.00, 15.00, 1000, 10000000),
        (5120, 'website', 'views', 'Website Direct Worldwide Traffic', 35.00, 20.00, 1000, 5000000),

        # --- OTHER ---
        (9999, 'other', 'special', 'All-in-One Social Media Viral Starter Pack', 150.00, 90.00, 1, 100)
    ]

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT count(*) as cnt FROM services")
        if cursor.fetchone()['cnt'] == 0:
            cursor.executemany("""
            INSERT INTO services (service_id, platform, category, name, price_bdt, cost_bdt, min_order, max_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, services_data)
            conn.commit()
            print(f"✅ Seeded {len(services_data)} curated services into database!")

# ================= TELEGRAM BOT API CALLS =================
def tg_request(method, data=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    try:
        if data:
            req_data = json.dumps(data).encode('utf-8')
            req = urllib.request.Request(url, data=req_data, headers={'Content-Type': 'application/json'})
        else:
            req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        print(f"Telegram API Error ({method}): {e}")
        return None

def send_tg_message(chat_id, text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return tg_request("sendMessage", payload)

def broadcast_to_proof_channel(text):
    """Broadcasts to the proof channel if channel ID configured or admin"""
    if PROOF_CHANNEL_CHAT_ID:
        send_tg_message(PROOF_CHANNEL_CHAT_ID, text)
    # Also notify admin about the activity
    send_tg_message(ADMIN_ID, f"📢 <b>[প্রুফ চ্যানেল ব্রডকাস্ট]:</b>\n\n{text}")

# ================= JAP API CLIENT =================
def call_jap_order(service_id, link, quantity):
    try:
        data = urllib.parse.urlencode({
            'key': JAP_API_KEY,
            'action': 'add',
            'service': service_id,
            'link': link,
            'quantity': quantity
        }).encode('utf-8')
        req = urllib.request.Request(JAP_API_URL, data=data, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=12) as resp:
            res = json.loads(resp.read().decode('utf-8'))
            print(f"JAP Response: {res}")
            return res
    except Exception as e:
        print(f"JAP API Error: {e}")
        return {"error": str(e)}

def get_jap_balance():
    try:
        data = urllib.parse.urlencode({'key': JAP_API_KEY, 'action': 'balance'}).encode('utf-8')
        req = urllib.request.Request(JAP_API_URL, data=data, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=8) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        return {"error": str(e)}

# ================= HTTP SERVER & REST API =================
class SMMRequestHandler(BaseHTTPRequestHandler):
    def send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # Serve Mini App HTML at / or /webapp
        if path in ['/', '/webapp', '/index.html']:
            try:
                target_html = HTML_FILE if os.path.exists(HTML_FILE) else '/app/applet/webapp.html'
                if not os.path.exists(target_html):
                    target_html = 'webapp.html'
                with open(target_html, 'rb') as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(content)
                return
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f"Error reading webapp: {e}".encode())
                return

        # API: /api/settings
        if path == '/api/settings':
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT key, value FROM app_settings")
                settings = {row['key']: row['value'] for row in cursor.fetchall()}
                if 'platform_logos' in settings:
                    try:
                        settings['platform_logos'] = json.loads(settings['platform_logos'])
                    except:
                        pass
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({'ok': True, 'settings': settings}).encode('utf-8'))
            return

        # API: /api/categories?platform=...
        if path == '/api/categories':
            plat = query.get('platform', [''])[0].strip().lower()
            with get_db() as conn:
                cursor = conn.cursor()
                if plat:
                    cursor.execute("SELECT * FROM categories WHERE lower(platform) = ? ORDER BY id ASC", (plat,))
                else:
                    cursor.execute("SELECT * FROM categories ORDER BY id ASC")
                cats = [dict(row) for row in cursor.fetchall()]
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({'ok': True, 'categories': cats}).encode('utf-8'))
            return

        # API: /api/services?platform=...&category_id=...
        if path == '/api/services':
            plat = query.get('platform', [''])[0].strip().lower()
            cat_id = query.get('category_id', [''])[0].strip()
            with get_db() as conn:
                cursor = conn.cursor()
                if plat and cat_id:
                    cursor.execute("SELECT * FROM services WHERE lower(platform) = ? AND category_id = ? ORDER BY price_bdt ASC", (plat, cat_id))
                elif plat:
                    cursor.execute("SELECT * FROM services WHERE lower(platform) = ? ORDER BY price_bdt ASC", (plat,))
                elif cat_id:
                    cursor.execute("SELECT * FROM services WHERE category_id = ? ORDER BY price_bdt ASC", (cat_id,))
                else:
                    cursor.execute("SELECT * FROM services ORDER BY id ASC LIMIT 500")
                services = [dict(row) for row in cursor.fetchall()]
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({'ok': True, 'services': services}).encode('utf-8'))
            return

        # API: /api/user?user_id=...
        if path == '/api/user':
            user_id = query.get('user_id', ['8701368956'])[0]
            first_name = query.get('first_name', ['User'])[0]
            username = query.get('username', [''])[0]

            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
                user = cursor.fetchone()
                if not user:
                    cursor.execute("""
                    INSERT INTO users (user_id, first_name, username, balance)
                    VALUES (?, ?, ?, 0.0)
                    """, (user_id, first_name, username))
                    conn.commit()
                    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
                    user = cursor.fetchone()
                user_dict = dict(user)
                user_dict['is_admin'] = (str(user_id) == str(ADMIN_ID))

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({'ok': True, 'user': user_dict}).encode('utf-8'))
            return

        # API: /api/orders?user_id=...
        if path == '/api/orders':
            user_id = query.get('user_id', [0])[0]
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT 50", (user_id,))
                orders = [dict(r) for r in cursor.fetchall()]
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({'ok': True, 'orders': orders}).encode('utf-8'))
            return

        # API: /api/transactions?user_id=...
        if path == '/api/transactions':
            user_id = query.get('user_id', [0])[0]
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM deposits WHERE user_id = ? ORDER BY id DESC LIMIT 30", (user_id,))
                txs = [dict(r) for r in cursor.fetchall()]
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({'ok': True, 'transactions': txs}).encode('utf-8'))
            return

        # 404
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(length).decode('utf-8')
        
        try:
            body = json.loads(post_data) if post_data else {}
        except Exception:
            body = {}

        # API: /api/order
        if path == '/api/order':
            user_id = body.get('user_id')
            service_id = body.get('service_id')
            service_name = body.get('service_name', 'Service')
            platform = body.get('platform', 'other')
            category = body.get('category', 'views')
            link = body.get('link', '').strip()
            quantity = int(body.get('quantity', 0))
            charge = float(body.get('charge', 0.0))

            if not user_id or not service_id or not link or quantity <= 0:
                self.send_json({'ok': False, 'message': 'সব তথ্য সঠিকভাবে প্রদান করুন!'})
                return

            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT balance, first_name FROM users WHERE user_id = ?", (user_id,))
                user = cursor.fetchone()
                if not user or user['balance'] < charge:
                    self.send_json({'ok': False, 'message': 'অপর্যাপ্ত ব্যালেন্স! দয়া করে রিচার্জ করুন।'})
                    return

                # Deduct balance
                new_bal = user['balance'] - charge
                cursor.execute("""
                UPDATE users 
                SET balance = ?, total_spent = total_spent + ?, total_orders = total_orders + 1
                WHERE user_id = ?
                """, (new_bal, charge, user_id))

                # Place Order on JAP API
                jap_res = call_jap_order(service_id, link, quantity)
                jap_order_id = str(jap_res.get('order', ''))
                order_status = 'processing' if jap_order_id else 'pending'

                cursor.execute("""
                INSERT INTO orders (user_id, service_id, service_name, platform, category, link, quantity, charge, status, jap_order_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (user_id, service_id, service_name, platform, category, link, quantity, charge, order_status, jap_order_id))
                order_id = cursor.lastrowid
                conn.commit()

            # Send Telegram Confirmation to User
            user_msg = (
                f"🎉 <b>আপনার অর্ডার সফলভাবে সম্পন্ন হয়েছে!</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"📦 <b>অর্ডার আইডি:</b> #{order_id}\n"
                f"🚀 <b>সার্ভিস:</b> {service_name}\n"
                f"🔢 <b>পরিমাণ:</b> {quantity:,}\n"
                f"💵 <b>মোট খরচ:</b> ৳ {charge:.3f}\n"
                f"🔗 <b>টার্গেট লিঙ্ক:</b> {link}\n"
                f"📊 <b>বর্তমান স্ট্যাটাস:</b> ⚡ ইন প্রোগ্রেস\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"💡 কিছুক্ষণের মধ্যেই ফলাফল দেখতে পাবেন। ধন্যবাদ!"
            )
            send_tg_message(user_id, user_msg)

            # Broadcast to Proof Channel & Admin
            masked_id = str(user_id)[:3] + "***"
            proof_msg = (
                f"🚀 <b>[নতুন অর্ডার প্রসেসিং]</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 <b>কাস্টমার:</b> User#{masked_id}\n"
                f"📦 <b>সার্ভিস:</b> {service_name}\n"
                f"🔢 <b>পরিমাণ:</b> {quantity:,}\n"
                f"💵 <b>চার্জ:</b> ৳ {charge:.2f}\n"
                f"📊 <b>স্ট্যাটাস:</b> ⚡️ ডেলিভারি শুরু হয়েছে...\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"👉 আপনিও অর্ডার করতে বটের মিনি অ্যাপ ওপেন করুন: @Gmail_buy_sall_bot"
            )
            broadcast_to_proof_channel(proof_msg)

            self.send_json({'ok': True, 'order_id': order_id, 'jap_order_id': jap_order_id})
            return

        # API: /api/deposit
        if path == '/api/deposit':
            user_id = body.get('user_id')
            method = body.get('method', 'bkash')
            amount = float(body.get('amount', 0))
            trxid = body.get('trxid', '').strip()

            if not user_id or amount < 10 or not trxid:
                self.send_json({'ok': False, 'message': 'সঠিক পরিমাণ ও TrxID দিন!'})
                return

            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                INSERT INTO deposits (user_id, method, amount, trxid, status)
                VALUES (?, ?, ?, ?, 'pending')
                """, (user_id, method, amount, trxid))
                deposit_id = cursor.lastrowid
                conn.commit()

            # Notify Admin with Action Buttons
            admin_msg = (
                f"🔔 <b>[নতুন ডিপোজিট রিকোয়েস্ট]</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🆔 <b>ডিপোজিট আইডি:</b> #{deposit_id}\n"
                f"👤 <b>ইউজার আইডি:</b> <code>{user_id}</code>\n"
                f"💳 <b>মেথড:</b> {method.upper()}\n"
                f"💰 <b>টাকার পরিমাণ:</b> ৳ {amount:.2f}\n"
                f"📝 <b>TrxID:</b> <code>{trxid}</code>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"ভেরিফাই করে নিচের বাটনে ক্লিক করুন:"
            )
            reply_markup = {
                "inline_keyboard": [
                    [
                        {"text": "✅ Approve (ব্যালেন্স দিন)", "callback_data": f"appr_dep_{deposit_id}"},
                        {"text": "❌ Reject (বাতিল)", "callback_data": f"rej_dep_{deposit_id}"}
                    ]
                ]
            }
            send_tg_message(ADMIN_ID, admin_msg, reply_markup)

            self.send_json({'ok': True, 'deposit_id': deposit_id})
            return

        # API: /api/transfer
        if path == '/api/transfer':
            from_id = body.get('from_id')
            to_id = body.get('to_id')
            amount = float(body.get('amount', 0))

            if not from_id or not to_id or amount <= 0:
                self.send_json({'ok': False, 'message': 'সঠিক আইডি ও টাকার পরিমাণ দিন!'})
                return

            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT balance FROM users WHERE user_id = ?", (from_id,))
                sender = cursor.fetchone()
                if not sender or sender['balance'] < amount:
                    self.send_json({'ok': False, 'message': 'অপর্যাপ্ত ব্যালেন্স!'})
                    return

                cursor.execute("SELECT balance FROM users WHERE user_id = ?", (to_id,))
                receiver = cursor.fetchone()
                if not receiver:
                    self.send_json({'ok': False, 'message': 'প্রাপক ইউজার আইডি খুঁজে পাওয়া যায়নি!'})
                    return

                # Transfer
                cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, from_id))
                cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, to_id))
                conn.commit()

            send_tg_message(to_id, f"🎁 <b>অভিনন্দন!</b>\nইউজার #{from_id} আপনাকে <b>৳ {amount:.2f}</b> ব্যালেন্স ট্রান্সফার করেছেন!")
            send_tg_message(from_id, f"✅ ইউজার #{to_id} কে সফলভাবে <b>৳ {amount:.2f}</b> পাঠানো হয়েছে!")

            self.send_json({'ok': True})
            return

        # ADMIN API: /api/admin/settings
        if path == '/api/admin/settings':
            app_name = body.get('app_name', '').strip()
            bot_username = body.get('bot_username', '').strip()
            app_logo = body.get('app_logo', '').strip()
            platform_logos = body.get('platform_logos')

            with get_db() as conn:
                cursor = conn.cursor()
                if app_name:
                    cursor.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES ('app_name', ?)", (app_name,))
                if bot_username:
                    cursor.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES ('bot_username', ?)", (bot_username,))
                if app_logo:
                    cursor.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES ('app_logo', ?)", (app_logo,))
                if platform_logos is not None:
                    cursor.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES ('platform_logos', ?)", (json.dumps(platform_logos),))
                conn.commit()
            self.send_json({'ok': True, 'message': 'Settings saved successfully'})
            return

        # ADMIN API: /api/admin/category/add
        if path == '/api/admin/category/add':
            platform = body.get('platform', '').strip().lower()
            name = body.get('name', '').strip()
            icon = body.get('icon', '').strip()

            if not platform or not name:
                self.send_json({'ok': False, 'message': 'Platform and category name required'})
                return

            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO categories (platform, name, icon) VALUES (?, ?, ?)", (platform, name, icon))
                cat_id = cursor.lastrowid
                conn.commit()
            self.send_json({'ok': True, 'category_id': cat_id, 'message': 'Category added'})
            return

        # ADMIN API: /api/admin/category/delete
        if path == '/api/admin/category/delete':
            category_id = body.get('category_id')
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM categories WHERE id = ?", (category_id,))
                cursor.execute("DELETE FROM services WHERE category_id = ?", (category_id,))
                conn.commit()
            self.send_json({'ok': True, 'message': 'Category and its services deleted'})
            return

        # ADMIN API: /api/admin/service/add
        if path == '/api/admin/service/add':
            service_id = int(body.get('service_id', 9999))
            platform = body.get('platform', 'other').strip().lower()
            category_id = body.get('category_id')
            category_name = body.get('category_name', '')
            name = body.get('name', '').strip()
            price_bdt = float(body.get('price_bdt', 10.0))
            cost_bdt = float(body.get('cost_bdt', price_bdt * 0.5))
            min_order = int(body.get('min_order', 100))
            max_order = int(body.get('max_order', 1000000))

            if not name:
                self.send_json({'ok': False, 'message': 'Service name required'})
                return

            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                INSERT INTO services (service_id, platform, category_id, category_name, name, price_bdt, cost_bdt, min_order, max_order)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (service_id, platform, category_id, category_name, name, price_bdt, cost_bdt, min_order, max_order))
                new_id = cursor.lastrowid
                conn.commit()
            self.send_json({'ok': True, 'id': new_id, 'message': 'Service added successfully'})
            return

        # ADMIN API: /api/admin/service/edit
        if path == '/api/admin/service/edit':
            srv_id = body.get('id')
            name = body.get('name', '').strip()
            price_bdt = float(body.get('price_bdt', 0.0))
            min_order = int(body.get('min_order', 0))
            max_order = int(body.get('max_order', 0))

            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                UPDATE services 
                SET name = ?, price_bdt = ?, min_order = ?, max_order = ?
                WHERE id = ?
                """, (name, price_bdt, min_order, max_order, srv_id))
                conn.commit()
            self.send_json({'ok': True, 'message': 'Service updated'})
            return

        # ADMIN API: /api/admin/service/delete
        if path == '/api/admin/service/delete':
            srv_id = body.get('id')
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM services WHERE id = ?", (srv_id,))
                conn.commit()
            self.send_json({'ok': True, 'message': 'Service deleted'})
            return

        self.send_json({'ok': False, 'message': 'Endpoint not found'})

    def send_json(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

def run_web_server():
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, SMMRequestHandler)
    print(f"🚀 HTTP Server & Mini App running on port {PORT}")
    httpd.serve_forever()

# ================= TELEGRAM BOT ENGINE (LONG POLLING) =================
def handle_bot_update(update):
    # 1. Message Handling
    if 'message' in update:
        msg = update['message']
        chat_id = msg['chat']['id']
        text = msg.get('text', '').strip()
        from_user = msg.get('from', {})
        user_id = from_user.get('id', chat_id)
        first_name = from_user.get('first_name', 'User')
        username = from_user.get('username', '')

        # Auto register user
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, balance FROM users WHERE user_id = ?", (user_id,))
            u = cursor.fetchone()
            if not u:
                ref_by = 0
                if text.startswith("/start ref_"):
                    try:
                        ref_by = int(text.split("ref_")[-1])
                    except:
                        pass
                cursor.execute("INSERT INTO users (user_id, first_name, username, balance, ref_by) VALUES (?, ?, ?, 0.0, ?)",
                               (user_id, first_name, username, ref_by))
                conn.commit()
                u_bal = 0.0
            else:
                u_bal = u['balance']

        # Commands
        if text.startswith('/start'):
            welcome_text = (
                f"👋 <b>স্বাগতম {first_name}!</b>\n\n"
                f"🔥 <b>AT SMM PANEL - শীর্ষ সোশ্যাল মিডিয়া গ্রোথ প্ল্যাটফর্ম</b>\n"
                f"TikTok, Facebook, Instagram, YouTube, Telegram ও Twitter-এর জন্য "
                f"লাইক, ভিউ, ফলোয়ার ও মেম্বার নিন সবচেয়ে কম দামে ও দ্রুততম ডেলিভারিতে!\n\n"
                f"💰 <b>আপনার ব্যালেন্স:</b> ৳ {u_bal:.2f}\n"
                f"🆔 <b>আপনার ইউজার আইডি:</b> <code>{user_id}</code>\n\n"
                f"👇 নিচের <b>'📱 ওপেন স্টোর'</b> বাটনে ক্লিক করে সরাসরি আমাদের প্রিমিয়াম মিনি অ্যাপ ব্যবহার করুন:"
            )
            keyboard = {
                "inline_keyboard": [
                    [
                        {"text": "📱 ওপেন স্টোর (Mini App)", "web_app": {"url": WEBAPP_URL}}
                    ],
                    [
                        {"text": "💳 আমার ব্যালেন্স", "callback_data": "check_balance"},
                        {"text": "📥 টাকা এড করুন", "callback_data": "add_funds"}
                    ],
                    [
                        {"text": "📦 সার্ভিস ও প্রাইস", "callback_data": "show_services"},
                        {"text": "👥 রেফার ইনকাম", "callback_data": "referral_info"}
                    ],
                    [
                        {"text": "📢 প্রুফ চ্যানেল", "url": PROOF_CHANNEL_LINK},
                        {"text": "👨‍💻 এডমিন সাপোর্ট", "url": f"https://t.me/{ADMIN_USERNAME}"}
                    ]
                ]
            }
            send_tg_message(chat_id, welcome_text, keyboard)
            return

        # Admin Commands
        if user_id == ADMIN_ID:
            if text == '/admin':
                jap_bal = get_jap_balance()
                jap_usd = jap_bal.get('balance', '0.00')

                with get_db() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT count(*) as total_users FROM users")
                    total_u = cursor.fetchone()['total_users']
                    cursor.execute("SELECT count(*) as total_orders, sum(charge) as total_rev FROM orders")
                    ord_row = cursor.fetchone()
                    total_o = ord_row['total_orders'] or 0
                    total_r = ord_row['total_rev'] or 0.0
                    cursor.execute("SELECT count(*) as pending_dep FROM deposits WHERE status = 'pending'")
                    pending_d = cursor.fetchone()['pending_dep']

                admin_panel = (
                    f"👑 <b>এডমিন কন্ট্রোল প্যানেল</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"👥 <b>মোট ইউজার:</b> {total_u}\n"
                    f"📦 <b>মোট অর্ডার:</b> {total_o}\n"
                    f"💵 <b>মোট আয়:</b> ৳ {total_r:.2f}\n"
                    f"⏳ <b>পেন্ডিং ডিপোজিট:</b> {pending_d} টি\n"
                    f"🌐 <b>JAP প্যানেল ব্যালেন্স:</b> ${jap_usd} USD\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"💡 <b>কমান্ডসমূহ:</b>\n"
                    f"• <code>/addbal [user_id] [amount]</code> (ব্যালেন্স যোগ)\n"
                    f"• <code>/broadcast [message]</code> (সবার কাছে মেসেজ)"
                )
                send_tg_message(chat_id, admin_panel)
                return

            if text.startswith('/addbal'):
                parts = text.split()
                if len(parts) >= 3:
                    try:
                        target_id = int(parts[1])
                        amount = float(parts[2])
                        with get_db() as conn:
                            cursor = conn.cursor()
                            cursor.execute("UPDATE users SET balance = balance + ?, total_deposit = total_deposit + ? WHERE user_id = ?",
                                           (amount, amount, target_id))
                            conn.commit()
                        send_tg_message(chat_id, f"✅ ইউজার <code>{target_id}</code> এর অ্যাকাউন্টে <b>৳ {amount:.2f}</b> যোগ করা হয়েছে!")
                        send_tg_message(target_id, f"🎉 <b>আপনার অ্যাকাউন্টে ৳ {amount:.2f} যোগ করা হয়েছে!</b>\nএখন আপনি যেকোনো সার্ভিস অর্ডার করতে পারেন।")
                    except Exception as e:
                        send_tg_message(chat_id, f"Error: {e}")
                else:
                    send_tg_message(chat_id, "ব্যবহার: <code>/addbal [user_id] [amount]</code>")
                return

            if text.startswith('/broadcast'):
                msg_body = text.replace('/broadcast', '').strip()
                if msg_body:
                    with get_db() as conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT user_id FROM users")
                        all_users = cursor.fetchall()
                    count = 0
                    for u in all_users:
                        try:
                            send_tg_message(u['user_id'], f"📢 <b>[অফিসিয়াল নোটিশ]</b>\n\n{msg_body}")
                            count += 1
                            time.sleep(0.05)
                        except:
                            pass
                    send_tg_message(chat_id, f"✅ মোট {count} জন ইউজারের কাছে ব্রডকাস্ট সফল!")
                else:
                    send_tg_message(chat_id, "ব্যবহার: <code>/broadcast আপনার মেসেজ</code>")
                return

    # 2. Callback Query Handling
    if 'callback_query' in update:
        cq = update['callback_query']
        cq_id = cq['id']
        data = cq.get('data', '')
        from_user = cq['from']
        user_id = from_user['id']
        chat_id = cq.get('message', {}).get('chat', {}).get('id', user_id)

        tg_request("answerCallbackQuery", {"callback_query_id": cq_id})

        if data == "check_balance":
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT balance, total_spent, total_orders FROM users WHERE user_id = ?", (user_id,))
                u = cursor.fetchone()
                bal = u['balance'] if u else 0.0
                spent = u['total_spent'] if u else 0.0
                orders = u['total_orders'] if u else 0

            msg = (
                f"💳 <b>আপনার অ্যাকাউন্ট ব্যালেন্স</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"💰 <b>বর্তমান ব্যালেন্স:</b> ৳ {bal:.2f}\n"
                f"💸 <b>মোট খরচ:</b> ৳ {spent:.2f}\n"
                f"📦 <b>মোট সম্পন্ন অর্ডার:</b> {orders} টি\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"টাকা এড করতে নিচের বাটনে চাপ দিন:"
            )
            send_tg_message(chat_id, msg, {
                "inline_keyboard": [
                    [{"text": "📥 টাকা এড করুন (Deposit)", "callback_data": "add_funds"}],
                    [{"text": "📱 মিনি অ্যাপে যান", "web_app": {"url": WEBAPP_URL}}]
                ]
            })
            return

        if data == "add_funds":
            deposit_info = (
                f"📥 <b>টাকা এড করার নিয়ম (বিকাশ / নগদ / রকেট / উপায়)</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"📱 <b>পার্সোনাল নম্বর:</b> <code>{PAYMENT_NUMBER}</code>\n"
                f"📌 <b>পেমেন্ট টাইপ:</b> Send Money (সেন্ড মানি)\n"
                f"💵 <b>সর্বনিম্ন ডিপোজিট:</b> ১০ টাকা\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"টাকা পাঠিয়ে সরাসরি আমাদের <b>মিনি অ্যাপের 'FUNDS'</b> ট্যাবে গিয়ে TrxID ও পরিমাণ সাবমিট করুন। "
                f"কয়েক মিনিটের মধ্যেই ভেরিফাই হয়ে একাউন্টে ব্যালেন্স যোগ হবে।"
            )
            send_tg_message(chat_id, deposit_info, {
                "inline_keyboard": [
                    [{"text": "📱 মিনি অ্যাপে ডিপোজিট করুন", "web_app": {"url": WEBAPP_URL}}]
                ]
            })
            return

        if data == "referral_info":
            ref_link = f"https://t.me/Gmail_buy_sall_bot?start=ref_{user_id}"
            ref_msg = (
                f"👥 <b>রেফার করে প্যাসিভ ইনকাম!</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"আপনার বন্ধুদের আপনার রেফারেল লিংক শেয়ার করুন।\n"
                f"তারা যেকোনো অর্ডার করলে আপনি আজীবন পাবেন <b>২% কমিশন</b>!\n\n"
                f"🔗 <b>আপনার পার্সোনাল রেফার লিংক:</b>\n"
                f"<code>{ref_link}</code>"
            )
            send_tg_message(chat_id, ref_msg)
            return

        if data == "show_services":
            srv_msg = (
                f"📦 <b>জনপ্রিয় সার্ভিস ও পাইকারি প্রাইস লিস্ট</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🎵 <b>TikTok Views (Refill):</b> ৳ 7.00 / 1k\n"
                f"🎵 <b>TikTok Likes:</b> ৳ 30.00 / 1k\n"
                f"📘 <b>Facebook Video Views:</b> ৳ 2.00 / 1k\n"
                f"📘 <b>Facebook Page Likes:</b> ৳ 60.00 / 1k\n"
                f"📸 <b>Instagram Views:</b> ৳ 2.00 / 1k\n"
                f"📸 <b>Instagram Likes:</b> ৳ 3.00 / 1k\n"
                f"🔴 <b>YouTube Views:</b> ৳ 75.00 / 1k\n"
                f"✈️ <b>Telegram Post Views:</b> ৳ 1.00 / 1k\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"👉 অর্ডার করতে নিচের বাটনে চাপ দিন:"
            )
            send_tg_message(chat_id, srv_msg, {
                "inline_keyboard": [
                    [{"text": "🚀 অর্ডার করতে মিনি অ্যাপ খুলুন", "web_app": {"url": WEBAPP_URL}}]
                ]
            })
            return

        # Admin Approval for Deposit
        if user_id == ADMIN_ID:
            if data.startswith("appr_dep_"):
                dep_id = int(data.replace("appr_dep_", ""))
                with get_db() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT * FROM deposits WHERE id = ? AND status = 'pending'", (dep_id,))
                    dep = cursor.fetchone()
                    if dep:
                        u_id = dep['user_id']
                        amt = dep['amount']
                        cursor.execute("UPDATE deposits SET status = 'approved' WHERE id = ?", (dep_id,))
                        cursor.execute("UPDATE users SET balance = balance + ?, total_deposit = total_deposit + ? WHERE user_id = ?",
                                       (amt, amt, u_id))
                        conn.commit()

                        send_tg_message(chat_id, f"✅ ডিপোজিট #{dep_id} অনুমোদন করা হয়েছে এবং ৳ {amt:.2f} যোগ করা হয়েছে!")
                        send_tg_message(u_id, f"🎉 <b>আপনার ৳ {amt:.2f} ডিপোজিট সফল হয়েছে!</b>\nব্যালেন্স ওয়ালেটে যোগ হয়েছে। এখনই অর্ডার শুরু করুন!")

                        # Broadcast to Proof Channel
                        masked_id = str(u_id)[:3] + "***"
                        proof_msg = (
                            f"🔔 <b>[লাইভ ডিপোজিট সফল]</b>\n"
                            f"━━━━━━━━━━━━━━━━━━━━\n"
                            f"👤 <b>ইউজার:</b> User#{masked_id}\n"
                            f"💰 <b>পরিমাণ:</b> ৳ {amt:.2f} ({dep['method'].upper()})\n"
                            f"⚡ <b>স্ট্যাটাস:</b> APPROVED (অনুমোদিত)\n"
                            f"⏰ <b>সময়:</b> {datetime.now().strftime('%I:%M %p')}\n"
                            f"━━━━━━━━━━━━━━━━━━━━\n"
                            f"✅ স্বয়ংক্রিয়ভাবে ওয়ালেটে টাকা যোগ হয়েছে!"
                        )
                        broadcast_to_proof_channel(proof_msg)
                    else:
                        send_tg_message(chat_id, "⚠️ এই ডিপোজিটটি পূর্বে প্রসেস করা হয়েছে।")
                return

            if data.startswith("rej_dep_"):
                dep_id = int(data.replace("rej_dep_", ""))
                with get_db() as conn:
                    cursor = conn.cursor()
                    cursor.execute("UPDATE deposits SET status = 'rejected' WHERE id = ?", (dep_id,))
                    conn.commit()
                send_tg_message(chat_id, f"❌ ডিপোজিট #{dep_id} বাতিল করা হয়েছে।")
                return

def run_telegram_bot_poller():
    offset = 0
    print("🤖 Telegram Bot Poller started...")
    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={offset}&timeout=15"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=25) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                if data.get('ok') and data.get('result'):
                    for update in data['result']:
                        offset = update['update_id'] + 1
                        try:
                            handle_bot_update(update)
                        except Exception as e:
                            print(f"Error handling update: {e}")
        except Exception as e:
            time.sleep(2)

# ================= ENTRY POINT =================
if __name__ == "__main__":
    init_db()

    # Start Bot Poller in Background Thread
    bot_thread = threading.Thread(target=run_telegram_bot_poller, daemon=True)
    bot_thread.start()

    # Start Web Server on Main Thread (Cloud Run requirement)
    run_web_server()
