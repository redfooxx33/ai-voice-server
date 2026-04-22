import sqlite3

def veritabani_kur():
    # 1. Deftere bağlan (Dosya yoksa oluşturur)
    conn = sqlite3.connect('dumpster_business.db')
    cursor = conn.cursor()

    print("Tablolar oluşturuluyor...")
    
    # 2. Bölge (Service Areas) tablosunu oluştur
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS service_areas (
        city TEXT PRIMARY KEY,
        tier TEXT,
        surcharge INTEGER
    )
    ''')

    # 3. Stok (Inventory) tablosunu oluştur
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS inventory (
        size INTEGER PRIMARY KEY,
        available_count INTEGER
    )
    ''')

    # 4. YENİ: Müşteri (Leads) tablosunu oluştur
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        phone TEXT,
        size TEXT,
        address TEXT
    )
    ''')

    print("Veriler ekleniyor...")
    
    # Eski verileri temizle (Üst üste binmemesi için)
    cursor.execute("DELETE FROM service_areas")
    cursor.execute("DELETE FROM inventory")

    # Bölge verileri
    areas = [
        ('Lakeland', 'Tier 2', 25),
        ('Tampa', 'Tier 1', 0),
        ('Orlando', 'Tier 3', 50)
    ]
    cursor.executemany("INSERT INTO service_areas (city, tier, surcharge) VALUES (?, ?, ?)", areas)

    # Stok verileri
    inv = [
        (10, 5),
        (20, 2),
        (30, 0)
    ]
    cursor.executemany("INSERT INTO inventory (size, available_count) VALUES (?, ?)", inv)

    # 5. Değişiklikleri kaydet ve dükkanı kapat
    conn.commit()
    conn.close()
    
    print("İşlem Başarılı! Tüm tablolar (Leads dahil) hazır.")

# Kodu çalıştır
if __name__ == '__main__':
    veritabani_kur()