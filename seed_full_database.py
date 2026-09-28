#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Seeder for AT SMM PANEL:
- Creates app_settings, categories, services, users, orders, deposits
- Populates platform-specific categories exactly as shown in the video
- Populates at least 10 high-quality services per category with realistic BDT prices
- Stores default app name, bot username, and platform logo URLs
"""

import sqlite3
import json
import os

DB_FILE = "/app/applet/smm_store.db"

def seed_complete_database():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # 1. App Settings Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS app_settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)

    default_platform_logos = {
        "instagram": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a5/Instagram_icon.png/1200px-Instagram_icon.png",
        "twitter": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6f/Logo_of_Twitter.svg/1200px-Logo_of_Twitter.svg.png",
        "telegram": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/82/Telegram_logo.svg/1200px-Telegram_logo.svg.png",
        "tiktok": "https://cdn-icons-png.flaticon.com/512/3046/3046121.png",
        "facebook": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/05/Facebook_Logo_%282019%29.png/1200px-Facebook_Logo_%282019%29.png",
        "youtube": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/09/YouTube_full-color_icon_%282017%29.svg/1200px-YouTube_full-color_icon_%282017%29.svg.png",
        "website": "https://cdn-icons-png.flaticon.com/512/1006/1006771.png",
        "other": "https://cdn-icons-png.flaticon.com/512/1055/1055666.png"
    }

    settings = [
        ("app_name", "AT SMM PANEL"),
        ("bot_username", "@ATSMM PANEL1_BOT"),
        ("app_logo", "https://api.dicebear.com/7.x/bottts/svg?seed=smmbot"),
        ("platform_logos", json.dumps(default_platform_logos))
    ]
    for k, v in settings:
        cursor.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)", (k, v))

    # 2. Categories Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        platform TEXT,
        name TEXT,
        icon TEXT
    )
    """)

    # 3. Services Table
    cursor.execute("DROP TABLE IF EXISTS services")
    cursor.execute("""
    CREATE TABLE services (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        service_id INTEGER,
        platform TEXT,
        category_id INTEGER,
        category_name TEXT,
        name TEXT,
        price_bdt REAL,
        cost_bdt REAL,
        min_order INTEGER,
        max_order INTEGER,
        description TEXT DEFAULT ''
    )
    """)

    # Clear categories to avoid duplicates
    cursor.execute("DELETE FROM categories")

    # Categories list per platform (matching the video)
    categories_data = {
        "tiktok": [
            "TikTok - Likes [ HQ Profiles - Ultrafast ]",
            "TikTok - Video Views [ Real Monetizable ] [ Non Drop ] ⁿᵉʷ",
            "TikTok - Video View [ Cheapest ] ⁿᵉʷ",
            "TikTok - Likes [ HQ Profiles - Cheapest ] ⁿᵉʷ",
            "TikTok - View [ No Drop Since 30 Days ] ⁿᵉʷ",
            "TikTok - Video Views [ Auto Refill ] ⁿᵉʷ",
            "TikTok - Likes [ Refill Button Working ] ⁿᵉʷ",
            "TikTok - Views [ Real Monetizable ] [ Drop 0% ] ⁿᵉʷ",
            "TikTok - Share [ Best Speed ] ⁿᵉʷ",
            "TikTok - Live Stream Likes & Share [ Cheapest ] ⁿᵉʷ",
            "TikTok - Save [ ULTRA FAST SPEED ] [ Best Price ] ⁿᵉʷ",
            "TikTok - Followers [ Real & Non Drop ]"
        ],
        "facebook": [
            "Facebook - Followers [ Real Account - Fast Speed ] [ Maximum Recourse 100k ] ⁿᵉʷ",
            "Facebook - Followers [ Real Account - Slow Speed ] ⁿᵉʷ",
            "Facebook - Followers [ Bot Data - Fast Speed ] [ Non Drop - Provider ] S1 ⁿᵉʷ",
            "Facebook - Followers [ Non Drop - Cheapest ] ⁿᵉʷ",
            "Facebook - Followers [ Real Account - Fast Speed ] [ Cheapest ] ⁿᵉʷ",
            "Facebook - Video Views [ Instant 100M ]",
            "Facebook - Page Likes + Followers [ 90D Refill ]",
            "Facebook - Post Reactions [ Love ❤️ Care 🥰 Haha 😂 ]",
            "Facebook - 60k Minutes Watch Time Pack [ Monetizable ]",
            "Facebook - Custom Comments [ Bangladesh/Mix ]"
        ],
        "instagram": [
            "Instagram - AUTO Views",
            "Instagram - Best Services ⭐",
            "Instagram - Story | Save | Shares | Impression",
            "Instagram - Save/Repost/Comment/Followers/Views ⁿᵉʷ",
            "Instagram - Likes [ NEW ] [ HQ Accounts - Best Price ] [ S1 ] ⁿᵉʷ",
            "Instagram - Shares",
            "Instagram - Likes [ Real Mixed - Cheapest ] ⁿᵉʷ",
            "Instagram - Likes [ Updated: 26.09. | Stable ] ⁿᵉʷ",
            "Instagram - Video Views [ Cheapest ] ⁿᵉʷ",
            "Instagram - Views [ Video/Reels/TV ]"
        ],
        "youtube": [
            "YouTube - Subscribers [ High Dropped ] ⁿᵉʷ",
            "YouTube - Video Views [ High Retention ] [ Refill ]",
            "YouTube - Likes [ Fast & Non-Drop ]",
            "YouTube - 4000 Hours WatchTime [ Monetization Pack ]",
            "YouTube - Comments [ English / Bengali ]",
            "YouTube - Live Stream Concurrent Views",
            "YouTube - Shorts Views [ Instant & Viral ]",
            "YouTube - Channel Monetization Package Complete"
        ],
        "telegram": [
            "Telegram - Post View [ Cheapest ] ⁿᵉʷ",
            "Smmgen - Cheapest Services",
            "Telegram - Post View [ Recommended ] ⁿᵉʷ",
            "Telegram - Auto Post View [ Recommended ] ⁿᵉʷ",
            "Telegram - Members - Channel/Group",
            "Telegram views - [ Premium Accounts ]",
            "Telegram - Bot Start [ Subscription With Activity - Subscribers From Search ] ⁿᵉʷ",
            "Telegram - Members [ Low Quality - Cheapest ] ⁿᵉʷ",
            "Telegram Auto Reactions 🔥🔥🔥 ⁿᵉʷ",
            "Telegram - Post Reactions [ Premium Accounts ]",
            "Telegram - Members [ USA ] 🇺🇸 ⁿᵉʷ",
            "Telegram - Reaction [ AI Based on Content ] ⁿᵉʷ"
        ],
        "twitter": [
            "Smmgen - Cheapest Services",
            "X ( Twitter ) - Tweet Views [ Best Prices ] ⁿᵉʷ",
            "X ( Twitter ) - Tweet Views [ Target ]",
            "X ( Twitter ) - Tweet Views [ Cheapest ] ⁿᵉʷ",
            "X ( Twitter ) - Tweet Likes / Hearts",
            "X ( Twitter ) - Followers [ Real Looking ]",
            "X ( Twitter ) - Retweets [ Instant ]"
        ],
        "website": [
            "Website Traffic from UK [ INSTANT ]",
            "Website Traffic from Brazil [ INSTANT ]",
            "Website Traffic from Indonesia [ INSTANT ]",
            "Website Traffic from Italy [ INSTANT ]",
            "Website Traffic from Poland [ INSTANT ]",
            "Website Traffic from Netherlands [ INSTANT ]",
            "Website Traffic from Germany [ INSTANT ]",
            "Website Traffic from Turkey [ INSTANT ]",
            "Website Traffic from France [ INSTANT ]",
            "Website Traffic from Spain [ INSTANT ]",
            "Website Traffic from Czech [ INSTANT ]",
            "Website Traffic - Google Organic Traffic [ High Duration ]"
        ],
        "other": [
            "All-in-One Social Media Starter Pack",
            "VIP Influencer Growth Bundle",
            "Custom Enterprise Promotion"
        ]
    }

    # Insert Categories and populate 10+ services for each category!
    for platform, cat_list in categories_data.items():
        for cat_name in cat_list:
            cursor.execute("INSERT INTO categories (platform, name, icon) VALUES (?, ?, ?)", (platform, cat_name, ""))
            cat_id = cursor.lastrowid

            # Generate 10+ high-converting services for this category
            # Custom naming depending on category keywords
            services_to_insert = []
            
            if "like" in cat_name.lower():
                base_names = [
                    (10331, f"{platform.capitalize()} Likes ~ HQ Accounts - Max 1M - 200k/Days - Instant - NO REFILL", 11.3585, 6.2, 50, 1000000),
                    (10332, f"{platform.capitalize()} Likes ~ HQ Accounts - Max 1M - 200k/Days - Instant - REFILL 30D", 11.8410, 6.5, 50, 1000000),
                    (10333, f"{platform.capitalize()} Likes ~ HQ Accounts - Max 1M - 200k/Days - Instant - REFILL 60D", 12.1000, 6.8, 50, 1000000),
                    (10334, f"{platform.capitalize()} Likes ~ HQ Accounts - Max 1M - 200k/Days - Instant - REFILL 90D", 12.3010, 7.0, 50, 1000000),
                    (10335, f"{platform.capitalize()} Likes ~ HQ Accounts - Max 1M - 200k/Days - Instant - REFILL 365D", 13.5000, 7.5, 50, 1000000),
                    (10336, f"{platform.capitalize()} Likes ~ Real Active Users - Super Fast - Drop 0%", 14.2000, 8.0, 50, 500000),
                    (10337, f"{platform.capitalize()} Likes ~ High Speed 500k/Day - Lifetime Refill Guarantee", 15.0000, 8.5, 100, 2000000),
                    (10338, f"{platform.capitalize()} Likes ~ Ultra Fast Delivery - Start 0-5 Minutes", 16.5000, 9.0, 50, 1000000),
                    (10339, f"{platform.capitalize()} Likes ~ Mixed Global Profiles - High Quality ⚡", 18.0000, 10.0, 50, 500000),
                    (10340, f"{platform.capitalize()} Likes ~ VIP Non-Drop Premium Server [ Ultra Stable ]", 22.0000, 12.0, 100, 500000)
                ]
            elif "view" in cat_name.lower():
                base_names = [
                    (8526, f"{platform.capitalize()} Views ~ Ultra Fast Server - 50M/Day - Instant Start", 1.8500, 0.9, 100, 50000000),
                    (8527, f"{platform.capitalize()} Views ~ Real Monetizable - High Retention [ 30D Refill ]", 2.2000, 1.1, 100, 20000000),
                    (8528, f"{platform.capitalize()} Views ~ Non-Drop 100% Guaranteed - Super Fast", 2.6500, 1.3, 100, 10000000),
                    (8529, f"{platform.capitalize()} Views ~ Viral Algorithm Booster [ Speed 10M/Day ]", 3.1000, 1.5, 100, 5000000),
                    (8530, f"{platform.capitalize()} Views ~ Real Video Impressions + Reach Boost", 3.8000, 1.8, 100, 5000000),
                    (8531, f"{platform.capitalize()} Views ~ Auto Refill Button Enabled [ Lifetime ]", 4.5000, 2.2, 100, 10000000),
                    (8532, f"{platform.capitalize()} Views ~ Targeted High Quality Audience - Zero Drop", 5.2000, 2.5, 100, 2000000),
                    (8533, f"{platform.capitalize()} Views ~ Reels / Shorts Viral Explosion Server", 5.9000, 2.9, 100, 5000000),
                    (8534, f"{platform.capitalize()} Views ~ Premium HQ Profiles [ Safe & Monetizable ]", 6.8000, 3.4, 100, 10000000),
                    (8535, f"{platform.capitalize()} Views ~ Instant Delivery [ Start Under 60 Seconds ]", 7.5000, 3.8, 100, 10000000)
                ]
            elif "follower" in cat_name.lower() or "member" in cat_name.lower() or "subscriber" in cat_name.lower():
                base_names = [
                    (10136, f"{platform.capitalize()} Growth ~ HQ Profiles - Fast Speed 50k/Day [ S1 ]", 28.5000, 15.0, 50, 500000),
                    (10137, f"{platform.capitalize()} Growth ~ Real Looking Accounts - Non Drop 30D Refill", 34.0000, 18.0, 50, 300000),
                    (10138, f"{platform.capitalize()} Growth ~ Stable Organic Speed - Safe for Account", 42.0000, 22.0, 100, 250000),
                    (10139, f"{platform.capitalize()} Growth ~ Instant Delivery - 90 Days Auto Refill Guarantee", 49.5000, 26.0, 50, 200000),
                    (10140, f"{platform.capitalize()} Growth ~ Active User Profiles with Posts & Bio", 58.0000, 30.0, 50, 100000),
                    (10141, f"{platform.capitalize()} Growth ~ Lifetime Refill Guarantee - Ultra Stable", 68.0000, 36.0, 50, 100000),
                    (10142, f"{platform.capitalize()} Growth ~ Bangladesh / Asian Region Targeted Accounts", 78.0000, 42.0, 50, 50000),
                    (10143, f"{platform.capitalize()} Growth ~ USA & European High Quality Accounts", 89.0000, 48.0, 50, 50000),
                    (10144, f"{platform.capitalize()} Growth ~ VIP Celebrity Quality - 100% Zero Drop", 110.0000, 60.0, 50, 50000),
                    (10145, f"{platform.capitalize()} Growth ~ Premium Exclusive Fast Server [ Provider Direct ]", 135.0000, 75.0, 50, 25000)
                ]
            elif "traffic" in cat_name.lower() or "website" in cat_name.lower():
                base_names = [
                    (5110, f"{cat_name} ~ High Duration (1-3 Min) - Google Analytics 4 Supported", 18.5000, 10.0, 1000, 10000000),
                    (5111, f"{cat_name} ~ Organic Search Traffic [ Keyword Targeted ]", 22.0000, 12.0, 1000, 5000000),
                    (5112, f"{cat_name} ~ Social Media Referral Traffic [ Facebook / Twitter ]", 24.5000, 13.0, 1000, 5000000),
                    (5113, f"{cat_name} ~ Low Bounce Rate Visitors (Under 25%)", 28.0000, 15.0, 1000, 5000000),
                    (5114, f"{cat_name} ~ Direct Browser Visitors - Instant Speed 100k/Day", 31.0000, 16.5, 1000, 10000000),
                    (5115, f"{cat_name} ~ Desktop + Mobile Mixed Real Visitors", 35.0000, 19.0, 1000, 5000000),
                    (5116, f"{cat_name} ~ E-Commerce AdSense Safe Visitors", 39.0000, 21.0, 1000, 2000000),
                    (5117, f"{cat_name} ~ 100% Human Traffic - GA4 Real Time Confirmed", 44.0000, 24.0, 1000, 2000000),
                    (5118, f"{cat_name} ~ High Retention (5+ Minutes Read Time)", 49.0000, 27.0, 1000, 1000000),
                    (5119, f"{cat_name} ~ VIP Tier 1 Direct Visitors [ Premium IP Pool ]", 55.0000, 30.0, 1000, 1000000)
                ]
            else:
                base_names = [
                    (9001, f"{cat_name} ~ Instant Server - Fast Processing [ S1 ]", 8.5000, 4.5, 50, 500000),
                    (9002, f"{cat_name} ~ High Quality Delivery - 30D Refill Protection", 11.2000, 6.0, 50, 500000),
                    (9003, f"{cat_name} ~ Super Fast Speed 200k/Day - Non Drop", 14.5000, 7.8, 50, 300000),
                    (9004, f"{cat_name} ~ Lifetime Guarantee - 100% Stable Performance", 18.0000, 9.5, 50, 200000),
                    (9005, f"{cat_name} ~ Real User Activity - Safe for All Accounts", 22.5000, 12.0, 50, 100000),
                    (9006, f"{cat_name} ~ VIP Exclusive Provider Server [ Direct API ]", 27.0000, 14.5, 50, 100000),
                    (9007, f"{cat_name} ~ Ultra Fast Start (0-2 Minutes) - Drop 0%", 32.0000, 17.0, 50, 50000),
                    (9008, f"{cat_name} ~ Verified Account Quality - Maximum Engagement", 38.5000, 21.0, 50, 50000),
                    (9009, f"{cat_name} ~ Viral Reach & Organic Impression Booster", 45.0000, 24.5, 50, 25000),
                    (9010, f"{cat_name} ~ Diamond Tier Premium Package [ Top Quality ]", 55.0000, 30.0, 50, 10000)
                ]

            for s_id, s_name, s_price, s_cost, s_min, s_max in base_names:
                cursor.execute("""
                INSERT INTO services (service_id, platform, category_id, category_name, name, price_bdt, cost_bdt, min_order, max_order)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (s_id, platform, cat_id, cat_name, s_name, s_price, s_cost, s_min, s_max))

    conn.commit()
    cursor.execute("SELECT count(*) FROM categories")
    cat_count = cursor.fetchone()[0]
    cursor.execute("SELECT count(*) FROM services")
    srv_count = cursor.fetchone()[0]
    conn.close()
    print(f"🎉 Complete Seeding Done! Seeded {cat_count} categories and {srv_count} services!")

if __name__ == "__main__":
    seed_complete_database()
