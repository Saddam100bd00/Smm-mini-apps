import json

with open('/tmp/jap_services.json') as f:
    services = json.load(f)

def find_services(keywords, must_have=[], exclude=[]):
    matched = []
    for s in services:
        txt = (s.get('category', '') + ' ' + s.get('name', '')).lower()
        if all(k in txt for k in keywords) and all(m in txt for m in must_have) and not any(e in txt for e in exclude):
            try:
                rate = float(s['rate'])
                matched.append((rate, s))
            except:
                pass
    matched.sort(key=lambda x: x[0])
    return matched

with open('selected_services.txt', 'w') as out:
    out.write("--- TIKTOK ---\n")
    for rate, s in find_services(['tiktok', 'view'], must_have=['refill'], exclude=['comment', 'live'])[:2]:
        out.write(f"ID: {s['service']} | ${rate:.4f} (~{rate*122:.2f} BDT) | {s['name'][:65]}\n")
    for rate, s in find_services(['tiktok', 'like'], must_have=['refill'], exclude=['comment', 'live'])[:2]:
        out.write(f"ID: {s['service']} | ${rate:.4f} (~{rate*122:.2f} BDT) | {s['name'][:65]}\n")
    for rate, s in find_services(['tiktok', 'follower'], must_have=['refill'], exclude=['comment', 'live'])[:2]:
        out.write(f"ID: {s['service']} | ${rate:.4f} (~{rate*122:.2f} BDT) | {s['name'][:65]}\n")

    out.write("\n--- FACEBOOK ---\n")
    for rate, s in find_services(['facebook', 'view'], must_have=['reel'], exclude=['live'])[:2]:
        out.write(f"ID: {s['service']} | ${rate:.4f} (~{rate*122:.2f} BDT) | {s['name'][:65]}\n")
    for rate, s in find_services(['facebook', 'reaction'], must_have=[], exclude=['comment', 'live'])[:2]:
        out.write(f"ID: {s['service']} | ${rate:.4f} (~{rate*122:.2f} BDT) | {s['name'][:65]}\n")
    for rate, s in find_services(['facebook', 'page'], must_have=['like'], exclude=['comment', 'post'])[:2]:
        out.write(f"ID: {s['service']} | ${rate:.4f} (~{rate*122:.2f} BDT) | {s['name'][:65]}\n")

    out.write("\n--- INSTAGRAM ---\n")
    for rate, s in find_services(['instagram', 'view'], must_have=['reel'], exclude=['live', 'story', 'impression'])[:2]:
        out.write(f"ID: {s['service']} | ${rate:.4f} (~{rate*122:.2f} BDT) | {s['name'][:65]}\n")
    for rate, s in find_services(['instagram', 'like'], must_have=['refill'], exclude=['live', 'comment'])[:2]:
        out.write(f"ID: {s['service']} | ${rate:.4f} (~{rate*122:.2f} BDT) | {s['name'][:65]}\n")
    for rate, s in find_services(['instagram', 'follower'], must_have=['refill'], exclude=['live', 'story'])[:2]:
        out.write(f"ID: {s['service']} | ${rate:.4f} (~{rate*122:.2f} BDT) | {s['name'][:65]}\n")

    out.write("\n--- YOUTUBE ---\n")
    for rate, s in find_services(['youtube', 'view'], must_have=['refill'], exclude=['live', 'short', 'stream'])[:2]:
        out.write(f"ID: {s['service']} | ${rate:.4f} (~{rate*122:.2f} BDT) | {s['name'][:65]}\n")
    for rate, s in find_services(['youtube', 'like'], must_have=[], exclude=['dislike', 'comment', 'live'])[:2]:
        out.write(f"ID: {s['service']} | ${rate:.4f} (~{rate*122:.2f} BDT) | {s['name'][:65]}\n")
    for rate, s in find_services(['youtube', 'subscriber'], must_have=['refill'], exclude=['live'])[:2]:
        out.write(f"ID: {s['service']} | ${rate:.4f} (~{rate*122:.2f} BDT) | {s['name'][:65]}\n")

    out.write("\n--- TELEGRAM ---\n")
    for rate, s in find_services(['telegram', 'view'], must_have=[], exclude=['auto'])[:2]:
        out.write(f"ID: {s['service']} | ${rate:.4f} (~{rate*122:.2f} BDT) | {s['name'][:65]}\n")
    for rate, s in find_services(['telegram', 'member'], must_have=[], exclude=['bot', 'auto'])[:2]:
        out.write(f"ID: {s['service']} | ${rate:.4f} (~{rate*122:.2f} BDT) | {s['name'][:65]}\n")

print("Finished filtering")
