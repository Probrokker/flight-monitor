# airports.py — справочник аэропортов и направлений для поиска

"""
Справочник аэропортов для мониторинга цен из LED (Санкт-Петербург).
Россия: поиск по каждому аэропорту отдельно.
Зарубеж: поиск по стране (минимум по всем аэропортам).
"""

# Российские направления (по аэропортам)
DOMESTIC_AIRPORTS = {
    "Москва": ["SVO", "DME", "VKO"],
    "Калининград": ["KGD"],
    "Пермь": ["PEE"],
    "Новосибирск": ["OVB"],
    "Сочи": ["AER"],
    "Котлас": ["KSZ"],
}

# Зарубежные направления (по странам — минимум по всем аэропортам страны)
# Ключ: страна, Значение: список основных аэропортов для поиска
INTERNATIONAL_DESTINATIONS = {
    "Турция": ["IST", "SAW", "AYT", "ADB"],
    "Египет": ["CAI", "HRG", "SSH"],
    "ОАЭ": ["DXB", "AUH", "SHJ"],
    "Саудовская Аравия": ["JED", "RUH"],
    "Катар": ["DOH"],
    "Бахрейн": ["BAH"],
    "Оман": ["MCT"],
    "Кувейт": ["KWI"],
    "Иордания": ["AMM"],
    "Китай": ["PEK", "PVG", "CAN", "SZX"],
    "Таиланд": ["BKK", "DMK", "HKT"],
    "Вьетнам": ["HAN", "SGN"],
    "Индия": ["DEL", "BOM", "MAA", "BLR"],
    "Индонезия": ["CGK", "DPS"],
    "Малайзия": ["KUL"],
    "Шри-Ланка": ["CMB"],
    "Мальдивы": ["MLE"],
}

# IATA-код Санкт-Петербурга
ORIGIN = "LED"

# Горизонт поиска (дней вперёд)
SEARCH_HORIZON_DAYS = 30

# Диапазон длительности поездки (дней)
TRIP_MIN_DAYS = 3
TRIP_MAX_DAYS = 14

# Валюта
CURRENCY = "RUB"


def get_all_destinations():
    """
    Возвращает полный список направлений для поиска.
    Формат: [(тип, название, [аэропорты])]
    """
    destinations = []
    for city, airports in DOMESTIC_AIRPORTS.items():
        destinations.append(("domestic", city, airports))
    for country, airports in INTERNATIONAL_DESTINATIONS.items():
        destinations.append(("international", country, airports))
    return destinations


def format_destination_name(dest_type, name):
    """Форматирует название направления для вывода."""
    if dest_type == "domestic":
        return f"🇷🇺 {name}"
    return f"🌍 {name}"
