# 🤖 AT SMM PANEL - Telegram Bot & API Server (Render Deployment)

এই ফোল্ডারের ফাইলগুলো দিয়ে আপনি খুব সহজেই **Render.com**-এ সম্পূর্ণ ফ্রিতে ২৪/৭ টেলিগ্রাম বট ও REST API ব্যাকএন্ড ডিপলয় করতে পারবেন।

---

## 📁 প্রয়োজনীয় ফাইলসমূহ:
1. `smm_server.py` - মূল পাইথন স্ক্রিপ্ট (বট হ্যান্ডলার + API সার্ভার)
2. `seed_database.py` - অটো-সিডার স্ক্রিপ্ট (প্রথমবার রান হলেই ৭৪টি ক্যাটাগরি ও ৭৪০টি প্রিমিয়াম সার্ভিস ডাটাবেজে যুক্ত করে)
3. `requirements.txt` - পাইথন ডিপেনডেন্সি তালিকা
4. `Procfile` - রেনডার প্রসেস ফাইল (`web: python3 smm_server.py`)
5. `render.yaml` - রেনডার ১-ক্লিক ব্লুপ্রিন্ট কনফিগারেশন
6. `.env.example` - প্রয়োজনীয় এনভায়রনমেন্ট ভেরিয়েবল টেমপ্লেট
7. `.gitignore` - গিট ইগনোর ফাইল

---

## 🚀 ধাপে ধাপে গিটহাব এবং Render-এ ডিপলয় করার নিয়ম:

### ধাপ ১: GitHub-এ নতুন রিপোজিটরি তৈরি করুন
1. [github.com](https://github.com)-এ যান এবং লগইন করুন।
2. **"New repository"** বাটনে ক্লিক করুন।
3. রিপোজিটরির নাম দিন, যেমন: `smm-telegram-bot`
4. **Public** বা **Private** সিলেক্ট করে **"Create repository"** বাটনে ক্লিক করুন।
5. এই ফোল্ডারের (`telegram_bot_render`) ভেতরের সব ফাইলগুলো (`smm_server.py`, `seed_database.py`, `requirements.txt`, `Procfile`, ইত্যাদি) আপনার ওই গিটহাব রিপোজিটরিতে আপলোড/পুশ করুন।

---

### ধাপ ২: Render.com-এ Web Service তৈরি করুন
1. [render.com](https://render.com)-এ যান এবং GitHub একাউন্ট দিয়ে Sign In করুন।
2. ড্যাশবোর্ডে গিয়ে **"New +"** বাটনে ক্লিক করে **"Web Service"** সিলেক্ট করুন।
3. আপনার গিটহাবের `smm-telegram-bot` রিপোজিটরিটি সিলেক্ট করে **"Connect"** করুন।
4. সেটিংস ফিল্ডগুলো নিচের মতো পূরণ করুন:
   - **Name:** `at-smm-panel-bot` (বা যেকোনো নাম)
   - **Region:** Singapore / Frankfurt (বা আপনার পছন্দের রিজিয়ন)
   - **Branch:** `main`
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python3 smm_server.py`
   - **Instance Type:** `Free` (বিনামূল্যে)

---

### ধাপ ৩: Environment Variables (এনভায়রনমেন্ট ভেরিয়েবল) সেট করুন
একটু নিচে স্ক্রল করে **"Environment Variables"** সেকশনে যান এবং নিচের কী-ভ্যালুগুলো এড করুন:

| Key | Value | বিবরণ |
|---|---|---|
| `BOT_TOKEN` | `8893514341:AAFIH0yATe_m28lTETkEu36GSmmoz4NkrsU` | আপনার টেলিগ্রাম বটের টোকেন |
| `ADMIN_ID` | `8701368956` | আপনার টেলিগ্রাম ইউজার আইডি |
| `ADMIN_USERNAME` | `ItsSaddam9` | আপনার টেলিগ্রাম ইউজারনেম |
| `JAP_API_KEY` | `58ad025b6b241ff6b5ba0aff5368bf42` | JustAnotherPanel API কী |
| `PAYMENT_NUMBER` | `01985664862` | বিকাশ/নগদ পেমেন্ট নম্বর |
| `PROOF_CHANNEL_LINK` | `https://t.me/+LFH-8mX0MJljYWU9` | প্রুফ চ্যানেলের ইনভাইট লিংক |
| `WEBAPP_URL` | `https://smm-mini-app.vercel.app` | Vercel-এ পাওয়া আপনার মিনি অ্যাপের লাইভ লিংক |

---

### ধাপ ৪: ডিপলয় সম্পন্ন করুন
1. নিচে থাকা **"Deploy Web Service"** বাটনে ক্লিক করুন।
2. রেনডার অটোমেটিক বিল্ড শুরু করবে এবং প্রথমবারেই সমস্ত ক্যাটাগরি ও সার্ভিস ডাটাবেজে সিড করে নিবে।
3. বিল্ড শেষ হলে আপনার সার্ভিসের উপরে একটি লাইভ লিঙ্ক দেখতে পাবেন (যেমন: `https://at-smm-panel-bot.onrender.com`)।

🎉 **অভিনন্দন!** এখন আপনার টেলিগ্রাম বট ২৪/৭ চালু থাকবে এবং মিনি অ্যাপের সমস্ত API রিকোয়েস্ট রেনডার হ্যান্ডেল করবে!
