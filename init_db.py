import sqlite3

def initialize_database():
    conn = sqlite3.connect("history.db")
    cursor = conn.cursor()
    
    # Core price execution log table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS price_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        store TEXT,
        product_id TEXT,
        product_name TEXT,
        current_price REAL,
        is_special INTEGER,
        normal_retail_price REAL
    )
    """)
    
    conn.commit()
    conn.close()
    print("SQLite analytical architecture initialized successfully.")

if __name__ == "__main__":
    initialize_database()
