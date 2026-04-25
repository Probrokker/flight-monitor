# demo.py — демонстрация работы парсера (тестовый запуск)

"""
Быстрый тест: ищет цены на 1-2 направления для проверки работоспособности.
"""

import asyncio
from airports import DOMESTIC_AIRPORTS, INTERNATIONAL_DESTINATIONS
from storage import init_db, append_price
from sources import search_destination


async def demo():
    init_db()

    # Тестовые направления
    test_destinations = [
        ("domestic", "Москва", DOMESTIC_AIRPORTS["Москва"]),
        ("international", "Турция", INTERNATIONAL_DESTINATIONS["Турция"]),
    ]

    print("🧪 Демо-запуск поиска\n")

    for dest_type, name, airports in test_destinations:
        print(f"🔍 {name} ({', '.join(airports)})")
        result = await search_destination(name, dest_type, airports)

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
            print(f"  ✅ {result['price']:,} ₽ ({result['source']})")
        else:
            print(f"  ❌ Не найдено")

    print("\n✅ Демо завершено. Проверьте prices.db.")


if __name__ == "__main__":
    asyncio.run(demo())
