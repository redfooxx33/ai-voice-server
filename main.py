import http
import sqlite3
import json
from fastapi import FastAPI, Request

app = FastAPI()

@app.post("/api/v1/voice-tools")
async def handle_vapi_request(request: Request):
    data = await request.json()
    message = data.get("message", {})

    if message.get("type") == "tool-calls":
        tool_calls = message.get("toolCalls", [])
        responses = []

        for tool_call in tool_calls:
            tool_call_id = tool_call.get("id")
            function_name = tool_call.get("function", {}).get("name")
    
            # Varsayılan hata yanıtı (Artık JSON formatında)
            response_data = {"userSafeSummary": "I encountered an error processing your request."}

            try:
                arguments = json.loads(tool_call.get("function", {}).get("arguments", "{}"))
            except:
                arguments = tool_call.get("function", {}).get("arguments", {})

            print(f"\n--- [YENİ İSTEK GELDİ] ---")
            print(f"[*] Araç: {function_name} | Veri: {arguments}")

            # ---------------------------------------------------------
            # FAZ 1: BÖLGE VE FİYAT KONTROLÜ
            # ---------------------------------------------------------
            if function_name == "get_service_area_tier":
                city_name = arguments.get("city", "").strip()
                
                conn = sqlite3.connect('dumpster_business.db')
                cursor = conn.cursor()
                cursor.execute("SELECT surcharge FROM service_areas WHERE city = ?", (city_name,))
                result = cursor.fetchone()
                conn.close()

                if result:
                    surcharge = result[0]
                    tier_code = f"surcharge_{surcharge}" 
                    response_data = {
                        "serviceTier": tier_code,
                        "userSafeSummary": f"Yes, we serve {city_name}. Delivery surcharge is ${surcharge}."
                    }
                else:
                    response_data = {
                        "serviceTier": "out_of_area",
                        "userSafeSummary": f"I'm sorry, we do not provide service in {city_name}. May I have your contact info to transfer you to our VIP team?"
                    }

            # ---------------------------------------------------------
            # FAZ 2: STOK KONTROLÜ
            # ---------------------------------------------------------
            elif function_name == "check_availability":
                car_class = arguments.get("carClass")
                
                if not car_class:
                    response_data = {"userSafeSummary": "I need to know the car class to check availability."}
                else:
                    conn = sqlite3.connect('dumpster_business.db')
                    cursor = conn.cursor()
                    cursor.execute("SELECT available_count, model_example FROM inventory WHERE car_class = ?", (car_class,))
                    result = cursor.fetchone()
                    conn.close()

                    if result and result[0] > 0:
                        model_name = result[1]
                        response_data = {
                            "availability": True,
                            "userSafeSummary": f"Great! A {car_class} (like a {model_name}) is available for your dates."
                        }
                    else:
                        response_data = {
                            "availability": False,
                            "userSafeSummary": f"I am sorry, but all our {car_class} vehicles are currently booked. Would you like me to check a Premium Sedan or Luxury SUV instead?"
                        }

            # ---------------------------------------------------------
            # FAZ 3: MÜŞTERİ KAYDI
            # ---------------------------------------------------------
            elif function_name == "create_lead":
                name = arguments.get("name", "Unknown")
                phone = arguments.get("phone", "Unknown")
                address = arguments.get("address", "No Address")
                car_class = arguments.get("carClass", "Unknown")

                conn = sqlite3.connect('dumpster_business.db')
                cursor = conn.cursor()
                cursor.execute("INSERT INTO leads (name, phone, size, address) VALUES (?, ?, ?, ?)", 
                               (name, phone, car_class, address))
                conn.commit()
                conn.close()

                response_data = {"userSafeSummary": f"Perfect {name}, I've recorded your booking. Our VIP team will call you shortly."}
                print(f"[✅ VIP KAYIT ATILDI]: {name} - {phone} - {car_class}")

            # ---------------------------------------------------------
            # FAZ 4: FİYAT TEKLİFİ HESAPLAMA (GET QUOTE)
            # ---------------------------------------------------------
            elif function_name == "get_quote":
                car_class = arguments.get("carClass", "Premium Sedan")
                tier = arguments.get("serviceTier", "standard")
                insurance = arguments.get("insuranceType", "standard")
                
                # Matematik çökmesini engellemek için string koruması
                try: days = int(arguments.get("rentalDaysRequested", 3))
                except: days = 3

                daily_rates = {"Premium Sedan": 150, "Luxury SUV": 250, "Sports Coupe": 400, "Executive Van": 200}
                base_rate = daily_rates.get(car_class, 150)
                
                travel_surcharge = 0
                if "surcharge_" in tier:
                    try: travel_surcharge = int(tier.split("_")[1])
                    except: travel_surcharge = 0
                
                insurance_surcharge = (50 * days) if insurance.lower() == "premium" else 0
                total_price = (base_rate * days) + travel_surcharge + insurance_surcharge

                response_data = {"userSafeSummary": f"For a {car_class}, {days} days: ${total_price} total. This includes delivery and {insurance} insurance."}
                print(f"[💰 FİYAT HESAPLANDI]: Toplam {total_price} Dolar")

            # MİMARIN DOKUNUŞU: Yanıtı tam Vapi'nin istediği gibi JSON String'e çeviriyoruz
            responses.append({
                "toolCallId": tool_call_id,
                "result": json.dumps(response_data)
            })

        return {"results": responses}

    return {"status": "ok"}