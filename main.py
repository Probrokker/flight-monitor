# main.py — оркестратор поиска и отправки отчётов

"""
Основной скрипт мониторинга.
Запускает поиск цен по всем направлениям, сохраняет в SQLite,
формирует и отправляет отчёт в Telegram.

Можно запускать:
- Локально: python main.py
- GitHub Actions: по cron (см. .github/workflows/monitor.yml)
"""

import os
import asyncio
import logging
from datetime import datetime

from dotenv import load_dotenv

from airports import get_all_destinations, format_destination_name
from storage import init_db, append_price, get_all_current_prices
from sources import search_all_destinations
from alerts import get_all_alerts, format_alert_line
from bot import send_report

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_IDS = os.getenv("TELEGRAM_CHAT_ID", "")


def get_chat_ids():
    """Возвращает список chat_id из переменной окружения."""
    if not TELEGRAM_CHAT_IDS:
        return []
    return [int(cid.strip()) for cid in TELEGRAM_CHAT_IDS.split(",") if cid.strip().isdigit()]


async def run_search() -> None:
    """Выполняет полный цикл поиска и сохранения цен."""
    init_db()

    destinations = get_all_destinations()
    logger.info(f"Начинаем поиск по {len(destinations)} направлениям")

    results = await search_all_destinations(destinations)

    # Сохраняем результаты
    saved = 0
    for result in results:
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
        saved += 1

    logger.info(f"Сохранено {saved} результатов")
    return results


def build_report(results: list) -> str:
    """Формирует текст отчёта для Telegram."""
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    lines = [f"📊 *Мониторинг LED → мир | {now}*\n"]
    lines.append("💡 *Цены на ближайшие даты (следующие 2 недели)*\n")

    # Разделяем по типам
    domestic = [r for r in results if r.get("destination_type") == "domestic"]
    international = [r for r in results if r.get("destination_type") == "international"]

    if domestic:
        lines.append("🇷🇺 *РОССИЯ:*")
        for r in domestic:
            dep = r.get('departure_date', '?')
            ret = r.get('return_date', '?')
            airline = r.get('airline', '')
            transfers = r.get('transfers', 0)
            transfer_str = "прямой" if transfers == 0 else f"{transfers} пересадка"
            airline_str = f" ({airline})" if airline else ""
            lines.append(
                f"• {r['destination']}: {r['price']:,} ₽{airline_str} | {dep} → {ret} | {transfer_str}"
            )
        lines.append("")

    if international:
        lines.append("🌍 *ЗАРУБЕЖ:*")
        for r in international:
            dep = r.get('departure_date', '?')
            ret = r.get('return_date', '?')
            airline = r.get('airline', '')
            transfers = r.get('transfers', 0)
            transfer_str = "прямой" if transfers == 0 else f"{transfers} пересадка"
            airline_str = f" ({airline})" if airline else ""
            lines.append(
                f"• {r['destination']}: {r['price']:,} ₽{airline_str} | {dep} → {ret} | {transfer_str}"
            )
        lines.append("")

    # Добавляем аномалии
    alerts = get_all_alerts()
    if alerts:
        lines.append("🚨 *АНОМАЛИИ:*")
        for alert in alerts:
            lines.append(
                format_alert_line(
                    alert["destination"],
                    alert["current_price"],
                    alert,
                    alert.get("destination_type", "domestic"),
                )
            )
        lines.append("")

    lines.append("💡 Команды бота: /today, /history, /alerts, /help")

    return "\n".join(lines)


async def main() -> None:
    """Главная точка входа."""
    logger.info("=== Запуск мониторинга ===")

    results = await run_search()

    if not results:
        logger.warning("Нет результатов — отчёт не сформирован")
        return

    report = build_report(results)
    logger.info(f"Отчёт сформирован ({len(report)} символов)")

    # Отправляем в Telegram если настроен
    chat_ids = get_chat_ids()
    if TELEGRAM_BOT_TOKEN and chat_ids:
        for chat_id in chat_ids:
            try:
                await send_report(chat_id, report)
                logger.info(f"Отчёт отправлен в чат {chat_id}")
            except Exception as e:
                logger.error(f"Ошибка отправки в чат {chat_id}: {e}")
    else:
        logger.info("Telegram не настроен — вывод в консоль")
        print("\n" + "=" * 50)
        print(report)
        print("=" * 50 + "\n")

    logger.info("=== Мониторинг завершён ===")


if __name__ == "__main__":
    asyncio.run(main())
