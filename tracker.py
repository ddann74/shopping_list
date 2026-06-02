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
    
    # Enhanced browser identity footprint to bypass basic corporate cloud firewalls
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": "https://www.woolworths.com.au",
        "Referer": f"https://www.woolworths.com.au/shop/search/products?searchTerm={term.replace(' ', '%20')}"
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
        print(f"-> Endpoint response status for '{term}': {res.status_code}")
        
        if res.status_code == 200:
            data = res.json()
            products = data.get("Products", [])
            
            # If the search endpoint returned an outer envelope wrap instead
            if not products and "SearchResults" in data:
                products = data.get("SearchResults", [])
                
            results = []
            for p in products:
                # Target the primary item payload securely
                inner_list = p.get("Products", [])
                if not inner_list:
                    continue
                inner = inner_list[0]
                
                if inner:
                    stock_code = inner.get("Stockcode")
                    name = inner.get("Name", "")
                    price = inner.get("Price")
                    
                    if price is None:
                        continue
                        
                    # Calculate standard retail price thresholds
                    was_price = inner.get("WasPrice", price)
                    is_special = 1 if inner.get("IsOnSpecial") else 0
                    
                    results.append({
                        "store": "Woolworths",
                        "id": str(stock_code),
                        "name": name,
                        "price": float(price),
                        "is_special": is_special,
                        "retail_base": float(was_price if was_price and was_price > 0 else price)
                    })
            print(f"   Successfully parsed {len(results)} items matching '{term}'")
            return results
        else:
            print(f"   Warning: Cloud block or request structure anomaly. Server returned: {res.text[:200]}")
    except Exception as e:
        print(f"   Extraction exception for keyword '{term}': {e}")
    return []

def log_pricing_run():
    # Connects to the local SQLite storage engine mapping
    conn = sqlite3.connect("history.db")
    cursor = conn.cursor()
    
    print("Beginning synchronized live scraping extraction matrix...")
    total_inserted = 0
    
    for term in WATCHLIST_TERMS:
        print(f"Scanning target: {term}")
        woolies_matches = fetch_woolworths_keyword(term)
        
        for item in woolies_matches:
            cursor.execute("""
                INSERT INTO price_history (store, product_id, product_name, current_price, is_special, normal_retail_price)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (item["store"], item["id"], item["name"], item["price"], item["is_special"], item["retail_base"]))
            total_inserted += 1
            
        time.sleep(2.0)  # Safe protection delay buffer to prevent rapid sequence bans
        
    conn.commit()
    conn.close()
    print(f"Pricing log transaction matrix committed. Inserted {total_inserted} total matching rows.")

if __name__ == "__main__":
    log_pricing_run()
