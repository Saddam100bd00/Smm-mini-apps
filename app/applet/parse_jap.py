import urllib.request
import urllib.parse
import json

url = 'https://justanotherpanel.com/api/v2'
data = urllib.parse.urlencode({'key': '58ad025b6b241ff6b5ba0aff5368bf42', 'action': 'services'}).encode('utf-8')
req = urllib.request.Request(url, data=data, headers={'User-Agent': 'Mozilla/5.0'})

with urllib.request.urlopen(req) as resp:
    services = json.loads(resp.read().decode('utf-8'))

USD_TO_BDT = 122.0

def find_best(keywords, exclude=[]):
    matches = []
    for s in services:
        name = s.get('name', '').lower()
        cat = s.get('category', '').lower()
        combined = f'{cat} {name}'
        
        if all(k.lower() in combined for k in keywords):
            if not any(e.lower() in combined for e in exclude):
                try:
                    rate = float(s['rate'])
                    matches.append((rate, s))
                except:
                    pass
    matches.sort(key=lambda x: x[0])
    return matches[:4]

queries = [
    ('TikTok Views', ['tiktok', 'view'], ['live', 'story', 'comment']),
    ('TikTok Likes', ['tiktok', 'like'], ['live', 'comment', 'dislike']),
    ('TikTok Followers', ['tiktok', 'follower'], ['live']),
    
    ('Facebook Video Views', ['facebook', 'view'], ['live', 'story', 'monetiz', 'custom']),
    ('Facebook Page Likes / Followers', ['facebook', 'page', 'like'], ['post', 'comment']),
    ('Facebook Post Reactions/Likes', ['facebook', 'post', 'like'], ['page', 'comment']),
    
    ('Instagram Views / Reels', ['instagram', 'view'], ['live', 'story', 'tv', 'impression']),
    ('Instagram Likes', ['instagram', 'like'], ['live', 'comment', 'story']),
    ('Instagram Followers', ['instagram', 'follower'], ['live']),
    
    ('YouTube Views', ['youtube', 'view'], ['live', 'adwords', 'stream', 'premiere']),
    ('YouTube Subscribers', ['youtube', 'subscriber'], ['live']),
    ('YouTube Likes', ['youtube', 'like'], ['dislike', 'comment', 'live']),
    
    ('Telegram Post Views', ['telegram', 'view'], ['auto', 'target']),
    ('Telegram Channel Members', ['telegram', 'member'], ['auto', 'bot', 'reaction'])
]

with open('/app/applet/price_report.txt', 'w') as out:
    out.write('=== JAP LIVE PRICES & RECOMMENDATIONS ===\n')
    for label, incl, excl in queries:
        bests = find_best(incl, excl)
        out.write(f'\n--- {label} ---\n')
        for rate, s in bests:
            bdt = rate * USD_TO_BDT
            srv_id = s.get('service')
            min_q = s.get('min')
            max_q = s.get('max')
            name = s.get('name')
            out.write(f'ID: {srv_id} | USD: ${rate:.4f} (~{bdt:.2f} BDT / 1k) | Min: {min_q} Max: {max_q} | {name}\n')

print('Done writing report')
