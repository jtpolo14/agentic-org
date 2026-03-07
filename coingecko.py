import requests

BASE = "https://api.coingecko.com/api/v3"

def get_price(*coin_ids, vs="usd"):
    r = requests.get(f"{BASE}/simple/price", params={
        "ids": ",".join(coin_ids),
        "vs_currencies": vs,
        "include_24hr_change": True,
        "include_market_cap": True
    })
    return r.json()

def get_coin_info(coin_id):
    r = requests.get(f"{BASE}/coins/{coin_id}", params={
        "localization": False,
        "tickers": False,
        "community_data": False,
        "developer_data": False
    })
    data = r.json()
    return {
        "name":       data["name"],
        "symbol":     data["symbol"].upper(),
        "rank":       data["market_cap_rank"],
        "price_usd":  data["market_data"]["current_price"]["usd"],
        "24h_change": data["market_data"]["price_change_percentage_24h"],
        "7d_change":  data["market_data"]["price_change_percentage_7d"],
        "market_cap": data["market_data"]["market_cap"]["usd"],
    }

def search_coin(query):
    r = requests.get(f"{BASE}/search", params={"query": query})
    coins = r.json().get("coins", [])[:5]
    return [{"id": c["id"], "name": c["name"], "symbol": c["symbol"]} for c in coins]

def trending():
    r = requests.get(f"{BASE}/search/trending")
    coins = r.json().get("coins", [])
    return [{"id": c["item"]["id"], "name": c["item"]["name"], "symbol": c["item"]["symbol"]} for c in coins]
