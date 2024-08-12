import asyncio
import json
import websockets
import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Optional

app = FastAPI()

# Глобальный словарь для хранения данных
live_data = {
    "kraken": {},
    "binance": {}
}

# Маппинг валют для нормализации
CURRENCY_MAPPING = {
    "USD": "USDT",
    "XBT": "BTC",
    "BCHABC": "BCH",
    "BCHSV": "BSV",
    "DOG": "DOGE",
}

# Функция для нормализации валюты
def normalize_currency(currency):
    return CURRENCY_MAPPING.get(currency, currency)

# Функция для нормализации пар
def normalize_pair(pair):
    if "/" in pair:
        base, quote = pair.split("/")
        normalized_base = normalize_currency(base)
        normalized_quote = normalize_currency(quote)
        return f"{normalized_base}{normalized_quote}"
    return pair

# Асинхронная функция для получения доступных пар с Kraken
async def get_kraken_tradable_pairs():
    async with httpx.AsyncClient() as client:
        response = await client.get('https://api.kraken.com/0/public/AssetPairs')
        data = response.json()
        pairs = []
        for pair, info in data['result'].items():
            if info.get('status') == 'online':
                base = info['base'][1:] if len(info['base']) == 4 else info['base']
                quote = info['quote'][1:] if len(info['quote']) == 4 else info['quote']
                normalized_pair = f"{base}/{quote}"
                pairs.append(normalized_pair)
        return pairs

# Асинхронная функция для работы с WebSocket Kraken
async def kraken_ws():
    uri = "wss://ws.kraken.com/"
    pairs = await get_kraken_tradable_pairs()
    subscribe_message = {
        "event": "subscribe",
        "pair": pairs,
        "subscription": {"name": "ticker"}
    }

    while True:
        try:
            async with websockets.connect(uri) as websocket:
                await websocket.send(json.dumps(subscribe_message))
                while True:
                    try:
                        data = await websocket.recv()
                        data = json.loads(data)
                        if isinstance(data, list) and len(data) > 1:
                            pair = data[-1]
                            bid = float(data[1]['b'][0])
                            ask = float(data[1]['a'][0])
                            live_data['kraken'][normalize_pair(pair)] = {
                                'bid': bid,
                                'ask': ask,
                                'avg': (bid + ask) / 2
                            }
                    except websockets.ConnectionClosedError as e:
                        print(f"Connection closed: {e}")
                        break
                    except json.JSONDecodeError as e:
                        print(f"JSON decode error: {e}")
                    except Exception as e:
                        print(f"Unexpected error: {e}")
        except websockets.ConnectionClosedError as e:
            print(f"Failed to connect to Kraken WebSocket: {e}")
        await asyncio.sleep(5)

# Асинхронная функция для работы с WebSocket Binance
async def binance_ws():
    uri = "wss://stream.binance.com:9443/ws/!ticker@arr"
    async with websockets.connect(uri) as websocket:
        while True:
            data = await websocket.recv()
            data = json.loads(data)
            for item in data:
                pair = item['s']
                live_data['binance'][pair] = {
                    'bid': float(item['b']),
                    'ask': float(item['a']),
                    'avg': (float(item['b']) + float(item['a'])) / 2
                }

# WebSocket эндпоинт для стриминга данных
@app.websocket("/ws/{exchange}/{pair}")
async def websocket_endpoint(websocket: WebSocket, exchange: str, pair: str):
    await websocket.accept()
    try:
        while True:
            if exchange in live_data:
                normalized_pair = normalize_pair(pair)
                if normalized_pair in live_data[exchange]:
                    await websocket.send_json(live_data[exchange][normalized_pair])
                else:
                    await websocket.send_json({"error": "Pair not found"})
            else:
                await websocket.send_json({"error": "Exchange not found"})
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        print("Client disconnected")

# GET эндпоинт для получения цен
@app.get("/prices/")
async def get_prices(pair: Optional[str] = None, exchange: Optional[str] = None):
    result = {}
    if exchange:
        data = live_data.get(exchange, {})
        for original_pair, price_data in data.items():
            normalized_pair = normalize_pair(original_pair)
            if pair is None or normalized_pair == pair:
                result[normalized_pair] = price_data
        return result if result else {"error": "Pair not found"}
    else:
        for exch, prices in live_data.items():
            for original_pair, price_data in prices.items():
                normalized_pair = normalize_pair(original_pair)
                if pair is None or normalized_pair == pair:
                    result[f"{normalized_pair}"] = price_data
        return result

# Запуск WebSocket соединений при старте приложения
@app.on_event("startup")
async def start_ws_connections():
    asyncio.create_task(kraken_ws())  # Kraken connection
    asyncio.create_task(binance_ws())  # Binance connection
