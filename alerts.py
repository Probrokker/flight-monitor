# alerts.py — детекция аномалий и трендов цен

from typing import Optional, Dict, List
from storage import get_rolling_average, get_historical_minimum, get_current_price

# Порог падения цены для алерта (процент)
PRICE_DROP_THRESHOLD = 0.20


def detect_anomaly(destination: str, current_price: int) -> Optional[Dict]:
    """
    Проверяет, является ли текущая цена аномалией.
    Возвращает словарь с типом алерта или None.
    """
    rolling_avg = get_rolling_average(destination, days=7)
    hist_min = get_historical_minimum(destination)

    # Нет истории — нечего сравнивать
    if rolling_avg is None:
        return None

    result = None

    # Падение на ≥20% к скользящему среднему
    if rolling_avg > 0 and current_price <= rolling_avg * (1 - PRICE_DROP_THRESHOLD):
        drop_pct = round((rolling_avg - current_price) / rolling_avg * 100)
        result = {
            "type": "drop",
            "emoji": "🔥",
            "message": f"↓ {drop_pct}% к среднему за 7 дней",
            "current_price": current_price,
            "reference_price": round(rolling_avg),
        }

    # Достижение или приближение к историческому минимуму
    if hist_min:
        hist_price, hist_date = hist_min
        if current_price <= hist_price:
            if result is None:
                result = {
                    "type": "historical_low",
                    "emoji": "🏆",
                    "message": f"Исторический минимум! (предыдущий: {hist_price} ₽)",
                    "current_price": current_price,
                    "reference_price": hist_price,
                }
            else:
                # Дополняем существующий алерт
                result["type"] = "drop+record"
                result["emoji"] = "🔥🏆"
                result["message"] += f" | Исторический минимум! (предыдущий: {hist_price} ₽)"

    return result


def get_all_alerts() -> List[Dict]:
    """
    Возвращает список всех текущих аномалий по всем направлениям.
    """
    from storage import get_all_current_prices

    alerts = []
    current_prices = get_all_current_prices()

    for record in current_prices:
        destination = record["destination"]
        price = record["price"]
        alert = detect_anomaly(destination, price)
        if alert:
            alert["destination"] = destination
            alert["destination_type"] = record.get("destination_type", "unknown")
            alerts.append(alert)

    return alerts


def format_alert_line(destination: str, price: int, alert: Dict, dest_type: str = "domestic") -> str:
    """Форматирует строку алерта для Telegram."""
    prefix = "🇷🇺" if dest_type == "domestic" else "🌍"
    return f"{prefix} {destination}: {price:,} ₽ {alert['emoji']} ({alert['message']})"


def get_price_trend_symbol(destination: str, current_price: int) -> str:
    """
    Возвращает символ тренда на основе скользящего среднего.
    ▲ — выше среднего, ▼ — ниже, → — около среднего.
    """
    rolling_avg = get_rolling_average(destination, days=7)
    if rolling_avg is None:
        return "→"

    diff_pct = (current_price - rolling_avg) / rolling_avg

    if diff_pct > 0.10:
        return "▲"
    elif diff_pct < -0.10:
        return "▼"
    return "→"
