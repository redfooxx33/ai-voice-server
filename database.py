import sqlite3

def init_db():
    conn = sqlite3.connect("hotel.db")
    cursor = conn.cursor()

    # 1. ENVANTER TABLOSU
    cursor.execute('''CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT, room_type TEXT UNIQUE, price_per_night REAL, available_rooms INTEGER)''')

    # 2. EKSTRA SERVİSLER TABLOSU
    cursor.execute('''CREATE TABLE IF NOT EXISTS extra_services (
        id INTEGER PRIMARY KEY AUTOINCREMENT, service_name TEXT UNIQUE, price REAL)''')

    # 3. YENİ: MÜŞTERİ REZERVASYON TABLOSU (LEAD CAPTURE)
    cursor.execute('''CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT, customer_name TEXT, phone_number TEXT, 
        room_type TEXT, nights INTEGER, total_price REAL, status TEXT)''')

    cursor.execute('DELETE FROM inventory')
    cursor.execute('DELETE FROM extra_services')

    rooms = [("standard", 100.0, 5), ("deluxe", 200.0, 2), ("suite", 500.0, 0)]
    extras = [("breakfast", 25.0), ("vip_transfer", 100.0)]

    cursor.executemany('INSERT INTO inventory (room_type, price_per_night, available_rooms) VALUES (?, ?, ?)', rooms)
    cursor.executemany('INSERT INTO extra_services (service_name, price) VALUES (?, ?)', extras)

    conn.commit()
    conn.close()
    print("✅ Tam fonksiyonlu Veri Tabanı (hotel.db) oluşturuldu. Bookings tablosu hazır!")

if __name__ == "__main__":
    init_db()