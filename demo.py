# demo.py — демонстрация работы парсера (тестовый запуск)

"""
Быстрый тест: ищет цены на 1-2 направления для проверки работоспособности.
"""

import asyncio
import aiohttp
from airports import DOMESTIC_AIRPORTS, INTERNATIONAL_DESTINATIONS
from storage import init_db, append_price
from sources import search_destination_api


async def demo():
    init_db()

    # Тестовые направления
    test_destinations = [
        ("domestic", "Москва", DOMESTIC_AIRPORTS["Москва"]),
        ("domestic", "Котлас", DOMESTIC_AIRPORTS["Котлас"]),
        ("domestic", "Новосибирск", DOMESTIC_AIRPORTS["Новосибирск"]),
        ("international", "Турция", INTERNATIONAL_DESTINATIONS["Турция"]),
    ]

    print("🧪 Демо-запуск поиска\n")

    async with aiohttp.ClientSession() as session:
        for dest_type, name, airports in test_destinations:
            print(f"🔍 {name} ({', '.join(airports)})")
            result = await search_destination_api(session, name, dest_type, airports)

            if result:
                append_price(
                    destination=result["destination"],
                    destination_type=result["destination_type"],
                    airport=result.get("airport"),
                    price=result["price"],
                    airline=result.get("airline"),
                    departure_date=result.get("departure_date"),
                    return_date=result.get("return_date"),
                    source=result["source"],
                )
                dep = result.get('departure_date', '?')
                ret = result.get('return_date', '?')
                transfers = result.get('transfers', 0)
                transfer_str = "прямой" if transfers == 0 else f"{transfers} пересадка"
                print(f"  ✅ {result['price']:,} ₽ ({dep} → {ret}, {transfer_str})")
            else:
                print(f"  ❌ Не найдено")

    print("\n✅ Демо завершено. Проверьте prices.db.")


if __name__ == "__main__":
    asyncio.run(demo())
