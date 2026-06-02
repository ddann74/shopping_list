import os
import sqlite3
import time
import requests

# Your generic fuzzy search keys mapped to specific target criteria
WATCHLIST_TERMS = [
    "Cadbury Dairy Milk 180g",
    "Finish Ultimate Pro Dishwasher Tablets",
    "Cobram Estate Extra Virgin Olive Oil 750ml"
]

def fetch_woolworths_keyword(term):
    url = "https://www.woolworths.com.au/apis/ui/Search/products"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/json"
    }
    payload = {
        "SearchTerm": term,
        "PageSize": 20,
        "PageNumber": 1,
        "SortType": "TraderRelevance",
        "IsSnapshot": False
    }
    
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=15)
        if res.status_code == 200:
            products = res.json().get("Products", [])
            results = []
            for p in products:
                inner = p.get("Products", [{}])[0]
                if inner:
                    # Deduce normal retail price baseline
                    was_price = inner.get("WasPrice", inner.get("Price", 0))
                    is_special = 1 if inner.get("IsOnSpecial") else 0
                    results.append({
                        "store": "Woolworths",
                        "id": str(inner.get("Stockcode")),
                        "name": inner.get("Name"),
                        "price": float(inner.get("Price", 0)),
                        "is_special": is_special,
                        "retail_base": float(was_price if was_price > 0 else inner.get("Price", 0))
                    })
            return results
    except Exception as e:
        print(f"Extraction exception for keyword {term}: {e}")
    return []

def log_pricing_run():
    conn = sqlite3.connect("history.db")
    cursor = conn.cursor()
    
    print("Beginning synchronized live scraping extraction matrix...")
    for term in WATCHLIST_TERMS:
        print(f"Scanning target: {term}")
        woolies_matches = fetch_woolworths_keyword(term)
        
        for item in woolies_matches:
            cursor.execute("""
                INSERT INTO price_history (store, product_id, product_name, current_price, is_special, normal_retail_price)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (item["store"], item["id"], item["name"], item["price"], item["is_special"], item["retail_base"]))
            
        time.sleep(1.5)  # Safe protection delay buffer
        
    conn.commit()
    conn.close()
    print("Pricing log transaction matrix committed.")

if __name__ == "__main__":
    log_pricing_run()
