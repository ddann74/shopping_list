import streamlit as st
import sqlite3
import pandas as pd

def ensure_database_is_healthy():
    """Ensures the database file and required tables exist before running queries."""
    conn = sqlite3.connect("history.db")
    cursor = conn.cursor()
    # Self-heal step: Create the table structure if it is missing on the server
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

def get_optimized_metrics(search_term):
    # Call our health-check guard before hitting the database
    ensure_database_is_healthy()
    
    conn = sqlite3.connect("history.db")
    
    # Query history logs to discover true baselines and matching line items
    query = """
        SELECT store, product_id, product_name, current_price, is_special, normal_retail_price,
               MIN(current_price) as historic_floor,
               AVG(current_price) as historic_average
        FROM price_history
        WHERE product_name LIKE ?
        GROUP BY store, product_id
    """
    df = pd.read_sql_query(query, conn, params=(f"%{search_term}%",))
    conn.close()
    return df

st.set_page_config(page_title="Grocery Optimizer")
st.title("🛒 Grocery List Rarity & Route Optimizer")
st.markdown("Enter your custom grocery list lines below to isolate optimized pricing routing alternatives.")

# User entry pipeline interface
user_input = st.text_area("Shopping List Items (One item per line)", 
                          "Olive Oil\nDishwasher Tablets\nCadbury")

list_items = [line.strip() for line in user_input.split("\n") if line.strip()]

if list_items:
    st.header("⚡ Live Price & Route Optimization Matrix")
    
    optimized_itinerary = []
    
    for item in list_items:
        metrics_df = get_optimized_metrics(item)
        
        if not metrics_df.empty:
            for idx, row in metrics_df.iterrows():
                current = row['current_price']
                floor = row['historic_floor']
                avg = row['historic_average']
                srp = row['normal_retail_price']
                
                savings_pct = ((srp - current) / srp * 100) if srp > 0 else 0
                
                # Assign dynamic custom rarity ratings similar to Szumark logic
                if current <= floor and row['is_special'] == 1:
                    rarity = "🔴 RRR (Historical Low)"
                elif current < avg and row['is_special'] == 1:
                    rarity = "🟡 RR (Rare Special)"
                elif row['is_special'] == 1:
                    rarity = "🟢 R (Standard Special)"
                else:
                    rarity = "⚪ Full Price"
                
                optimized_itinerary.append({
                    "Searched For": item,
                    "Exact Match Name": row['product_name'],
                    "Store": row['store'],
                    "Current Price": f"${current:.2f}",
                    "Normal Price (SRP)": f"${srp:.2f}",
                    "Est. Savings %": f"{savings_pct:.1f}%",
                    "Rarity Class": rarity,
                    "RawPrice": current
                })

    if optimized_itinerary:
        display_df = pd.DataFrame(optimized_itinerary)
        
        # Highlight best paths
        st.subheader("Optimized Sourcing Selections")
        st.dataframe(display_df.drop(columns=["RawPrice"]))
        
        # Render a simple checkout split strategy
        st.subheader("📍 Recommended Shopping Strategy Split")
        for search_key in list_items:
            sub = display_df[display_df["Searched For"] == search_key]
            if not sub.empty:
                best_option = sub.sort_values(by="RawPrice").iloc[0]
                st.info(f"For **{search_key}** -> Buy **{best_option['Exact Match Name']}** at **{best_option['Store']}** for **{best_option['Current Price']}** (Status: {best_option['Rarity Class']})")
    else:
        st.warning("Your database is initialized but currently empty. Run your GitHub Actions tracking script manually to pull this week's live catalogue prices!")
