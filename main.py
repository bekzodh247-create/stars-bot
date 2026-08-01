import json, sqlite3, time, random, requests

# --- TO'G'RI SOZLAMALAR ---
BOT_TOKEN = "7933162271:AAHsjTrm_lzZhrtOGlowH7nAp42P9wXf0r4"
ADMINS = [6857135696]

API_URL = f"https://telegram.org{BOT_TOKEN}/"

# --- MA'LUMOTLAR BAZASI ---
conn = sqlite3.connect("stars_konkurs.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, points INTEGER DEFAULT 0, username TEXT, name TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS channels (channel_id TEXT PRIMARY KEY, channel_name TEXT, channel_url TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS contests (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, text TEXT, status TEXT DEFAULT 'active')")
cursor.execute("CREATE TABLE IF NOT EXISTS participants (contest_id INTEGER, user_id INTEGER, PRIMARY KEY(contest_id, user_id))")
conn.commit()

def req(method, data=None):
    url = API_URL + method
    try:
        if data:
            response = requests.post(url, json=data, timeout=15)
        else:
            response = requests.get(url, timeout=15)
        return response.json()
    except Exception as e:
        print(f"Ulanish xatosi ({method}): {e}")
        return {"ok": False}

def sm(c, t, rm=None): 
    return req("sendMessage", {"chat_id": c, "text": t, "parse_mode": "Markdown", "reply_markup": rm})

def check_sub(u):
    cursor.execute("SELECT channel_id FROM channels")
    ch = cursor.fetchall()
    for (c_id,) in ch:
        res = req("getChatMember", {"chat_id": c_id, "user_id": u})
        if not res.get("ok") or res["result"]["status"] in ['left', 'kicked']: return False
    return True

def main_menu(): 
    return {"keyboard": [[{"text": "🎉 Faol Konkurslar"}, {"text": "📊 Mening Ishtirokim"}], [{"text": "🏆 Oxirgi G'oliblar"}]], "resize_keyboard": True}

def admin_menu(): 
    return {"inline_keyboard": [[{"text": "➕ Yangi Konkurs Yaratish", "callback_data": "adm_create"}],[{"text": "📣 Kanallarni Sozlash", "callback_data": "adm_ch"}],[{"text": "🎁 G'olibni Aniqlash", "callback_data": "adm_winner"}],[{"text": "✉️ Ommaviy Reklama Yuborish", "callback_data": "adm_bc"}]]}

def msg_handler(msg):
    c = msg["chat"]["id"]
    t = msg.get("text", "")
    u = msg["from"].get("username", "Foydalanuvchi")
    fn = msg["from"].get("first_name", "Ishtirokchi")
    
    if t.startswith("/start"):
        cursor.execute("INSERT OR REPLACE INTO users VALUES (?, 0, ?, ?)", (c, u, fn))
        conn.commit()
        if not check_sub(c):
            cursor.execute("SELECT channel_name, channel_url FROM channels")
            kb = [[{"text": n, "url": l}] for n, l in cursor.fetchall()]
            kb.append([{"text": "✅ Obunani Tekshirish", "callback_data": "sub_check"}])
            return sm(c, "🚨 *Botdan foydalanish uchun quyidagi kanallarga a'zo bo'ling:*", {"inline_keyboard": kb})
        sm(c, f"👋 *Salom {fn}!* Rasmiy Konkurs Botiga xush kelibsiz. Quyidagi menyudan foydalaning:", main_menu())
    elif t == "🎉 Faol Konkurslar":
        if not check_sub(c): return sm(c, "❌ Avval kanallarga a'zo bo'ling! /start")
        cursor.execute("SELECT id, title, text FROM contests WHERE status='active'")
        contests = cursor.fetchall()
        if not contests: return sm(c, "😔 Hozircha faol konkurslar yo'q.")
        for cid, title, text in contests:
            kb = {"inline_keyboard": [[{"text": "✅ Konkursda Qatnashish", "callback_data": f"join_{cid}"}]]}
            sm(c, f"📌 *Konkurs:* {title}\n\n{text}", kb)
    elif t == "📊 Mening Ishtirokim":
        cursor.execute("SELECT COUNT(*) FROM participants WHERE user_id=?", (c,))
        res = cursor.fetchone()
        count = res if res else 0
        sm(c, f"📊 Siz jami *{count} ta* konkursda ishtirok etyapsiz.")
    elif t == "🏆 Oxirgi G'oliblar":
        sm(c, "🏆 Yaqinda yakunlangan konkurslar g'oliblari kanalda e'lon qilingan yoki bu bo'lim ayni damda bo'sh.")
    elif t == "/admin" and c in ADMINS: 
        sm(c, "⚙️ *Xush kelibsiz Admin!* Quyidagi funksiyalardan foydalaning:", admin_menu())

def cb_handler(call):
    c = call["message"]["chat"]["id"]
    d = call["data"]
    mid = call["message"]["message_id"]
    
    if d == "sub_check":
        if check_sub(c):
            req("deleteMessage", {"chat_id": c, "message_id": mid})
            sm(c, "🎉 Rahmat! Obuna tasdiqlandi.", main_menu())
        else:
            req("answerCallbackQuery", {"callback_query_id": call["id"], "text": "❌ Hali hamma kanalga a'zo bo'lmagansiz!", "show_alert": True})
    elif d.startswith("join_"):
        cid = int(d.split("_"))
        if not check_sub(c): return req("answerCallbackQuery", {"callback_query_id": call["id"], "text": "❌ Kanallardan chiqib ketgansiz!", "show_alert": True})
        try:
            cursor.execute("INSERT INTO participants VALUES (?, ?)", (cid, c))
            conn.commit()
            req("answerCallbackQuery", {"callback_query_id": call["id"], "text": "🎉 Tabriklaymiz! Siz konkurs ro'yxatiga qo'shildingiz.", "show_alert": True})
        except:
            req("answerCallbackQuery", {"callback_query_id": call["id"], "text": "⚠️ Siz allaqachon bu konkursda qatnashyapsiz!", "show_alert": True})
    elif c in ADMINS:
        if d == "adm_create": sm(c, "📝 *Yangi Konkurs yaratish uchun xabar yuboring:*\nFormat: `NEW_KONKURS:Sarlavha|Konkurs batafsil matni` Davomiga shartlarni yozishingiz mumkin.")
        elif d == "adm_ch": sm(c, "➕ *Majburiy obuna kanali qo'shish:*\nFormat: `ADD_KANAL:-1001234567,Kanal Nomi,https://t.me`")
        elif d == "adm_winner":
            cursor.execute("SELECT id, title FROM contests WHERE status='active'")
            contests = cursor.fetchall()
            if not contests: return sm(c, "❌ G'olibni aniqlash uchun faol konkurslar yo'q.")
            kb = {"inline_keyboard": [[{"text": title, "callback_data": f"pick_{cid}"}] for cid, title in contests]}
            sm(c, "🎁 Qaysi konkurs g'olibini aniqlamoqchisiz? (Random tanlanadi):", kb)
        elif d.startswith("pick_"):
            cid = int(d.split("_"))
            cursor.execute("SELECT user_id FROM participants WHERE contest_id=?", (cid,))
            parts = cursor.fetchall()
            if not parts: return sm(c, "❌ Bu konkursda hech kim qatnashmayapti.")
            winner_id = random.choice(parts)
            cursor.execute("SELECT username, name FROM users WHERE user_id=?", (winner_id,))
            w_info = cursor.fetchone()
            w_user = w_info if w_info and w_info else "Foydalanuvchi"
            cursor.execute("UPDATE contests SET status='ended' WHERE id=?", (cid,))
            conn.commit()
            w_txt = f"🎉 *Konkurs G'olibi Aniqlandi!* 🎉\n\n🏆 G'olib: @{w_user}\nID: `{winner_id}`"
            sm(c, w_txt)
            sm(winner_id, f"🥳 *Tabriklaymiz!* Siz botda o'tkazilgan konkursda g'olib bo'ldingiz! Admin tez orada siz bilan bog'lanadi.")
        elif d == "adm_bc": sm(c, "✉️ *Ommaviy xabar yuborish formatini yuboring:*\n`REKLAMA:Xabar matni`")

def text_admin_handler(msg):
    c, t = msg["chat"]["id"], msg.get("text", "")
    if t.startswith("NEW_KONKURS:"):
        try:
            data = t.replace("NEW_KONKURS:", "").split("|")
            cursor.execute("INSERT INTO contests (title, text) VALUES (?, ?)", (data.strip(), data.strip()))
            conn.commit()
            sm(c, "✅ Yangi konkurs muvaffaqiyatli yaratildi va foydalanuvchilarga ko'rinadigan bo'ldi!")
        except: sm(c, "❌ Xato! Formatni tekshiring (Sarlavha va matn orasiga | belgisini qo'ying).")
    elif t.startswith("ADD_KANAL:"):
        try:
            p = t.replace("ADD_KANAL:", "").split(",")
            cursor.execute("INSERT OR REPLACE INTO channels VALUES (?, ?, ?)", (p.strip(), p.strip(), p.strip()))
            conn.commit()
            sm(c, "✅ Majburiy obuna kanali ro'yxatga qo'shildi! Botni kanalga admin qilishni unutmang.")
        except: sm(c, "❌ Format xato! Vergullar bilan ajratib yozing.")
    elif t.startswith("REKLAMA:"):
        bc_txt = t.replace("REKLAMA:", "").strip()
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()
        sm(c, f"📣 {len(users)} ta foydalanuvchiga yuborilyapti...")
        for (u_id,) in users: 
            sm(u_id, bc_txt)
            time.sleep(0.05)
        sm(c, "✅ Ommaviy reklama tarqatildi!")

print("Bot muvaffaqiyatli ishga tushdi! Telegramdan xabar yuborishingiz mumkin...")
offset = 0
while True:
    try:
        up = req("getUpdates", {"offset": offset, "timeout": 10})
        if up.get("ok") and up.get("result"):
            for update in up["result"]:
                offset = update["update_id"] + 1
                if "message" in update:
                    m = update["message"]
                    mt = m.get("text", "")
                    if m["chat"]["id"] in ADMINS and (mt.startswith("NEW_KONKURS:") or mt.startswith("ADD_KANAL:") or mt.startswith("REKLAMA:")): 
                        text_admin_handler(m)
                    else: 
                        msg_handler(m)
                elif "callback_query" in update: 
                    cb_handler(update["callback_query"])
    except:
        pass
    time.sleep(1)
