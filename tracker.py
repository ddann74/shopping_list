import os
import sqlite3
import time
import requests

# Your master fuzzy query lookup items
WATCHLIST_TERMS = [
    "Cadbury Dairy Milk 180g",
    "Finish Ultimate Pro Dishwasher Tablets",
    "Cobram Estate Extra Virgin Olive Oil 750ml"
]

def fetch_woolworths(term):
    url = "https://www.woolworths.com.au/apis/ui/Search/products"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*"
    }
    payload = {"SearchTerm": term, "PageSize": 20, "PageNumber": 1, "SortType": "TraderRelevance", "IsSnapshot": False}
    
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=15)
        if res.status_code == 200:
            bundles = res.json().get("Bundles", []) or res.json().get("Products", [])
            results = []
            for b in bundles:
                p_list = b.get("Products", []) or ([b] if "Stockcode" in b else [])
                if not p_list: continue
                inner = p_list[0]
                price = inner.get("Price")
                if price is None: continue
                results.append({
                    "store": "Woolworths",
                    "id": str(inner.get("Stockcode")),
                    "name": inner.get("Name", ""),
                    "price": float(price),
                    "is_special": 1 if inner.get("IsOnSpecial") else 0,
                    "retail_base": float(inner.get("WasPrice", price) or price)
                })
            return results
    except Exception as e:
        print(f"Woolworths search fault for '{term}': {e}")
    return []

def fetch_coles(term):
    # Coles modern public search endpoint gateway
    url = "https://www.coles.com.au/api/v1/search/products"
    
    # Highly specific headers required to prevent Akamai WAF block responses
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Content-Type": "application/json",
        "Origin": "https://www.coles.com.au",
        "Referer": f"https://www.coles.com.au/search?q={term.replace(' ', '%20')}"
    }
    
    payload = {
        "searchTerm": term,
        "page": 1,
        "pageSize": 24,
        "sortType": "RELEVANCE"
    }
    
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=15)
        print(f"-> Coles API connection response status for '{term}': {res.status_code}")
        
        if res.status_code == 200:
            data = res.json()
            results = []
            results_list = data.get("results", [])
            
            for item in results_list:
                # Bypass non-product placeholders
                if item.get("_type") != "PRODUCT":
                    continue
                    
                stock_id = item.get("id")
                name = f"{item.get('brand', '')} {item.get('name', '')}".strip()
                
                # Check for available pricing array tiers
                pricing = item.get("pricing", {})
                if not pricing:
                    continue
                    
                current_price = pricing.get("now")
                if current_price is None:
                    continue
                    
                # Determine promotional special rules
                was_price = pricing.get("was", current_price)
                is_special = 1 if pricing.get("promotionType") or was_price > current_price else 0
                
                results.append({
                    "store": "Coles",
                    "id": str(stock_id),
                    "name": name,
                    "price": float(current_price),
                    "is_special": is_special,
                    "retail_base": float(was_price if was_price > 0 else current_price)
                })
            return results
    except Exception as e:
        print(f"Coles execution processing anomaly for '{term}': {e}")
    return []

def log_pricing_run():
    conn = sqlite3.connect("history.db")
    cursor = conn.cursor()
    
    print("Initiating cross-retailer matrix crawl...")
    total_inserted = 0
    
    for term in WATCHLIST_TERMS:
        # 1. Fetch Woolworths
        print(f"Scouting Woolworths: '{term}'")
        w_items = fetch_woolworths(term)
        for item in w_items:
            cursor.execute("""
                INSERT INTO price_history (store, product_id, product_name, current_price, is_special, normal_retail_price)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (item["store"], item["id"], item["name"], item["price"], item["is_special"], item["retail_base"]))
            total_inserted += 1
            
        time.sleep(1.5)
        
        # 2. Fetch Coles
        print(f"Scouting Coles: '{term}'")
        c_items = fetch_coles(term)
        for item in c_items:
            cursor.execute("""
                INSERT INTO price_history (store, product_id, product_name, current_price, is_special, normal_retail_price)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (item["store"], item["id"], item["name"], item["price"], item["is_special"], item["retail_base"]))
            total_inserted += 1
            
        time.sleep(2.0) # Extended rate limit delay buffer
        
    conn.commit()
    conn.close()
    print(f"Multi-store database transaction sync finalized. Logged {total_inserted} records.")

if __name__ == "__main__":
    log_pricing_run()
