# sources.py — парсинг цен через Travelpayouts API (Aviasales)

import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

from airports import ORIGIN

# API конфигурация
TP_API_TOKEN = "4eb9e4a5e7f268e966a0f43b0864f977"
TP_BASE_URL = "https://api.travelpayouts.com/v1"

# Ограничение: 200 запросов в час с одного IP
REQUEST_DELAY = 1.5  # секунд между запросами


async def _api_request(session: aiohttp.ClientSession, endpoint: str, params: dict) -> Optional[Dict]:
    """Выполняет запрос к Travelpayouts API."""
    params["token"] = TP_API_TOKEN
    url = f"{TP_BASE_URL}/{endpoint}"
    
    try:
        async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status != 200:
                print(f"[API] HTTP {resp.status} для {params}")
                return None
            data = await resp.json()
            if not data.get("success"):
                print(f"[API] Ошибка: {data.get('error')}")
                return None
            return data.get("data")
    except Exception as e:
        print(f"[API] Исключение: {e}")
        return None


async def search_destination_api(
    session: aiohttp.ClientSession,
    destination_name: str,
    destination_type: str,
    destination_airports: List[str],
) -> Optional[Dict]:
    """
    Ищет минимальную цену через Travelpayouts API.
    Для зарубежных направлений ищет по первому аэропорту списка.
    """
    dest_iata = destination_airports[0]
    
    # Получаем цены за текущий и следующий месяц
    current_month = datetime.now().strftime("%Y-%m")
    next_month = (datetime.now() + timedelta(days=30)).strftime("%Y-%m")
    
    best_price = None
    best_result = None
    
    for month in [current_month, next_month]:
        params = {
            "origin": ORIGIN,
            "destination": dest_iata,
            "month": month,
        }
        
        data = await _api_request(session, "prices/monthly", params)
        if data:
            # data содержит ключи вида "2026-04" с минимальными ценами
            for month_key, flight in data.items():
                price = flight.get("price")
                if price and (best_price is None or price < best_price):
                    best_price = price
                    best_result = {
                        "price": price,
                        "airline": flight.get("airline"),
                        "departure_date": flight.get("departure_at", "")[:10],
                        "return_date": flight.get("return_at", "")[:10],
                        "source": "aviasales_api",
                        "destination": destination_name,
                        "destination_type": destination_type,
                        "airport": dest_iata,
                    }
        
        await asyncio.sleep(REQUEST_DELAY)
    
    return best_result


async def search_all_destinations(destinations: List[Tuple[str, str, List[str]]]) -> List[Dict]:
    """
    Ищет цены для всех направлений через API.
    """
    results = []
    
    async with aiohttp.ClientSession() as session:
        for dest_type, name, airports in destinations:
            print(f"🔍 Поиск: {name} ({', '.join(airports)})")
            
            result = await search_destination_api(session, name, dest_type, airports)
            if result:
                results.append(result)
                print(f"  ✅ {result['price']:,} ₽ ({result['source']})")
            else:
                print(f"  ❌ Цены не найдены")
            
            # Задержка между направлениями для соблюдения лимитов API
            await asyncio.sleep(REQUEST_DELAY)
    
    return results
