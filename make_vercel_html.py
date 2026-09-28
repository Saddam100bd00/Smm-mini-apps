#!/usr/bin/env python3
import os
import re

html_path = "webapp.html" if os.path.exists("webapp.html") else "/webapp.html"
with open(html_path, "r", encoding="utf-8") as f:
    content = f.read()

# Add script config.js after telegram-web-app.js
script_tag = '  <script src="https://telegram.org/js/telegram-web-app.js"></script>\n  <script src="config.js"></script>'
content = content.replace('  <script src="https://telegram.org/js/telegram-web-app.js"></script>', script_tag, 1)

# Add apiUrl helper inside <script>
api_helper = """
    // API URL Helper (supports Render URL configured in config.js or relative URL)
    function apiUrl(path) {
      const base = (window.BACKEND_API_URL || '').replace(/\\/+$/, '');
      return `${base}${path}`;
    }
"""

content = content.replace('let selectedCategory = null;', api_helper + '\n    let selectedCategory = null;', 1)

# Replace all fetch('/api or fetch(`/api
content = re.sub(r"fetch\((['\"]/api[^'\"]*['\"])", r"fetch(apiUrl(\1))", content)
content = re.sub(r"fetch\((`/api[^`]*`)", r"fetch(apiUrl(\1))", content)

os.makedirs("mini_app_vercel", exist_ok=True)
with open("mini_app_vercel/index.html", "w", encoding="utf-8") as f:
    f.write(content)

print("Vercel index.html created successfully! Size:", len(content))

