from fastapi import FastAPI, Request
import json
import uvicorn
import sqlite3
import requests
import re

app = FastAPI()

# 🔥 Senin n8n Webhook Linkin
N8N_WEBHOOK_URL = "https://expecto2027312.app.n8n.cloud/webhook-test/34185adf-c5f1-499f-92e6-1ec03acece3d"

# ENVANTER VE KURALLAR
ROOM_RULES = {
    "standard": {"capacity": 2, "description": "comfortable for 2 people"},
    "deluxe": {"capacity": 3, "description": "spacious for up to 3 people"},
    "suite": {"capacity": 5, "description": "luxury space for up to 5 people"}
}

def query_db(query, args=(), one=False, commit=False):
    conn = sqlite3.connect("hotel.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(query, args)
    if commit:
        conn.commit()
        rv = cursor.lastrowid
    else:
        rv = cursor.fetchall()
    conn.close()
    return (rv[0] if rv else None) if one and not commit else rv

@app.post("/api/v1/voice-tools")
async def handle_voice_tools(request: Request):
    data = await request.json()
    message = data.get("message", {})
    responses = []

    if message.get("type") == "tool-calls":
        for tool_call in message.get("toolCallList", []):
            tool_call_id = tool_call.get("id")
            func_data = tool_call.get("function", {})
            tool_name = func_data.get("name")
            
            # 🔥 500 Hatası Zırhı
            raw_args = func_data.get("arguments", {})
            args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            
            # --- ARAÇ 1: GENEL BİLGİ VE FİYAT ---
            if tool_name == "get_general_info":
                room_type = args.get("roomType", "standard").lower()
                room_data = query_db("SELECT price_per_night FROM inventory WHERE room_type = ?", (room_type,), one=True)
                capacity = ROOM_RULES.get(room_type, {}).get("capacity", 2)
                description = ROOM_RULES.get(room_type, {}).get("description", "comfortable stay")
                
                summary = f"Our {room_type} rooms start at ${room_data['price_per_night']} per night and can accommodate up to {capacity} people. It's a great choice if you're looking for {description}."
                result_obj = {"info": summary, "userSafeSummary": summary}

            # --- ARAÇ 2: MÜSAİTLİK VE KAPASİTE KONTROLÜ ---
            elif tool_name == "check_room_availability":
                room_type = args.get("roomType", "standard").lower()
                guests = args.get("guestCount", 2)
                capacity = ROOM_RULES.get(room_type, {}).get("capacity", 2)
                
                if guests > capacity:
                    summary = f"Actually, the {room_type} room is only for {capacity} people. For {guests} guests, I recommend our larger rooms. Shall we check those instead?"
                    result_obj = {"isAvailable": False, "userSafeSummary": summary}
                else:
                    room_data = query_db("SELECT available_rooms FROM inventory WHERE room_type = ?", (room_type,), one=True)
                    if not room_data or room_data["available_rooms"] <= 0:
                        summary = f"I'm sorry, we're currently fully booked for {room_type} rooms on those dates. May I suggest a different room type?"
                        result_obj = {"isAvailable": False, "userSafeSummary": summary}
                    else:
                        summary = f"Yes, we have that available! It fits your group perfectly. Would you like the pricing details now?"
                        result_obj = {"isAvailable": True, "userSafeSummary": summary}

            # --- ARAÇ 3: FİYAT HESAPLAMA ---
            elif tool_name == "get_room_quote":
                room_type = args.get("roomType", "standard").lower()
                
                # Güvenli Sayı Çevrimi
                try:
                    nights = max(1, int(args.get("nights", 1)))
                except (ValueError, TypeError):
                    nights = 1

                room_data = query_db("SELECT price_per_night FROM inventory WHERE room_type = ?", (room_type,), one=True)
                total = room_data["price_per_night"] * nights
                summary = f"For a {nights}-night stay, the total would be ${total}. This includes all standard amenities. Does that work for your budget?"
                result_obj = {"totalPrice": total, "userSafeSummary": summary}

            # --- ARAÇ 4: REZERVASYON & N8N TETİKLEME (Kurumsal Versiyon) ---
            elif tool_name == "book_room":
                # 1. Input Sanitization (Veri Temizleme ve Güvenlik)
                try:
                    customer_name = str(args.get("customerName", "Guest"))[:100].strip()
                    # Sadece rakam ve + işaretini bırak (Güvenlik zırhı)
                    phone = re.sub(r"[^\d\+]", "", str(args.get("phone", "")))[:20]
                    room_type = args.get("roomType", "standard").lower()
                    nights = max(1, int(args.get("nights", 1)))
                    total_price = max(0.0, float(args.get("totalPrice", 0)))
                except (ValueError, TypeError):
                    result_obj = {"status": "error", "userSafeSummary": "I couldn't process the reservation details. Please let me know your name and phone number again."}
                    responses.append({"toolCallId": tool_call_id, "result": json.dumps(result_obj)})
                    continue

                # 2. Race Condition Önlemi (Satıştan hemen önce stok kontrolü)
                stock = query_db("SELECT available_rooms FROM inventory WHERE room_type = ?", (room_type,), one=True)
                if not stock or stock["available_rooms"] < 1:
                    result_obj = {
                        "status": "unavailable",
                        "userSafeSummary": f"I'm so sorry, but it seems our {room_type} rooms just sold out. Shall I check another room type for you?"
                    }
                    responses.append({"toolCallId": tool_call_id, "result": json.dumps(result_obj)})
                    continue

                # 3. Veritabanı İşlemleri (Mevcut şemana uygun, çökmeyecek yapı)
                try:
                    query_db("INSERT INTO bookings (customer_name, phone_number, room_type, nights, total_price, status) VALUES (?, ?, ?, ?, ?, ?)", 
                             (customer_name, phone, room_type, nights, total_price, "confirmed"), commit=True)
                    
                    query_db("UPDATE inventory SET available_rooms = available_rooms - 1 WHERE room_type = ? AND available_rooms > 0", 
                             (room_type,), commit=True)
                except Exception as e:
                    print(f"❌ DB Hatası: {e}")
                    result_obj = {"status": "error", "userSafeSummary": "I'm experiencing a quick system issue right now. Give me a moment to try again."}
                    responses.append({"toolCallId": tool_call_id, "result": json.dumps(result_obj)})
                    continue

                # 4. Webhook Tetikleme (Hata toleranslı)
                webhook_payload = {
                    "customer": customer_name,
                    "phone": phone,
                    "room": room_type,
                    "nights": nights,
                    "revenue": total_price
                }
                try:
                    resp = requests.post(N8N_WEBHOOK_URL, json=webhook_payload, timeout=5)
                    resp.raise_for_status()
                    print("🚀 Webhook n8n'e başarıyla gönderildi!")
                except Exception as e:
                    print(f"⚠️ Webhook hatası: {e} - Veri veritabanında güvende.")

                # 5. Geveze Olmayan Satış Kapama Cümlesi
                summary = f"Wonderful, {customer_name}! Your {room_type} room is confirmed for {nights} nights. We'll send the details to {phone}. We look forward to hosting you."
                result_obj = {"status": "success", "userSafeSummary": summary}

            responses.append({"toolCallId": tool_call_id, "result": json.dumps(result_obj)})

    return {"results": responses}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)