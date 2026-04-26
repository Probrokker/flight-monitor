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
                print(f"[API] HTTP {resp.status} для {params.get('destination', 'unknown')}")
                return None
            data = await resp.json()
            if not data.get("success"):
                print(f"[API] Ошибка: {data.get('error')}")
                return None
            return data.get("data")
    except Exception as e:
        print(f"[API] Исключение: {e}")
        return None


async def search_cheap_for_dates(
    session: aiohttp.ClientSession,
    dest_iata: str,
    destination_name: str,
    destination_type: str,
    days_ahead: int = 14,
) -> Optional[Dict]:
    """
    Ищет дешёвые билеты на ближайшие N дней через prices/cheap.
    Перебирает даты вылета, возвращает самый дешёвый найденный вариант.
    """
    today = datetime.now()
    best_price = None
    best_result = None
    
    # Ищем на ближайшие 14 дней с интервалом 2 дня (чтобы не превысить лимит API)
    for day_offset in range(0, days_ahead, 2):
        depart_date = (today + timedelta(days=day_offset)).strftime("%Y-%m-%d")
        return_date = (today + timedelta(days=day_offset + 7)).strftime("%Y-%m-%d")
        
        params = {
            "origin": ORIGIN,
            "destination": dest_iata,
            "depart_date": depart_date,
            "return_date": return_date,
            "limit": 5,
        }
        
        data = await _api_request(session, "prices/cheap", params)
        if data:
            for key, flight in data.items():
                if not isinstance(flight, dict):
                    continue
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
                        "flight_number": flight.get("flight_number"),
                        "transfers": flight.get("transfers", 0),
                    }
        
        await asyncio.sleep(0.5)  # Короткая задержка между датами
    
    return best_result


async def search_monthly_minimum(
    session: aiohttp.ClientSession,
    dest_iata: str,
    destination_name: str,
    destination_type: str,
) -> Optional[Dict]:
    """
    Ищет абсолютный минимум за текущий и следующий месяц через prices/monthly.
    """
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
            for month_key, flight in data.items():
                if not isinstance(flight, dict):
                    continue
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


async def search_destination_api(
    session: aiohttp.ClientSession,
    destination_name: str,
    destination_type: str,
    destination_airports: List[str],
) -> Optional[Dict]:
    """
    Ищет минимальную цену: сначала на ближайшие даты (cheap),
    потом абсолютный минимум за месяц (monthly) как fallback.
    """
    dest_iata = destination_airports[0]
    
    # Сначала ищем на ближайшие даты (актуальные цены)
    result = await search_cheap_for_dates(
        session, dest_iata, destination_name, destination_type, days_ahead=14
    )
    
    # Если не нашли — пробуем monthly
    if not result:
        result = await search_monthly_minimum(
            session, dest_iata, destination_name, destination_type
        )
    
    return result


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
                # Формируем человекочитаемую строку с датой
                dep = result.get('departure_date', 'неизвестно')
                ret = result.get('return_date', 'неизвестно')
                transfers = result.get('transfers', 0)
                transfer_str = "прямой" if transfers == 0 else f"{transfers} пересадка"
                
                print(f"  ✅ {result['price']:,} ₽ ({dep} → {ret}, {transfer_str})")
                results.append(result)
            else:
                print(f"  ❌ Цены не найдены")
            
            # Задержка между направлениями для соблюдения лимитов API
            await asyncio.sleep(REQUEST_DELAY)
    
    return results
