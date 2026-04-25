# sources.py — парсинг цен с авиасайтов через Playwright

import asyncio
import random
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from playwright.async_api import async_playwright, Page

from airports import ORIGIN, SEARCH_HORIZON_DAYS, TRIP_MIN_DAYS, TRIP_MAX_DAYS, CURRENCY

# Задержки между запросами (секунды)
REQUEST_DELAY_MIN = 1.5
REQUEST_DELAY_MAX = 3.0
DELAY_BETWEEN_DESTINATIONS = 5.0


async def _random_delay(min_sec: float = REQUEST_DELAY_MIN, max_sec: float = REQUEST_DELAY_MAX):
    """Случайная задержка для снижения риска бана."""
    await asyncio.sleep(random.uniform(min_sec, max_sec))


async def _create_browser_context(playwright):
    """Создаёт браузер с реалистичным user-agent."""
    browser = await playwright.chromium.launch(headless=True)
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        viewport={"width": 1920, "height": 1080},
        locale="ru-RU",
        timezone_id="Europe/Moscow",
    )
    return browser, context


async def _close_popups(page: Page):
    """Пытается закрыть модальные окна и попапы."""
    popup_selectors = [
        "[data-test-id='popup-close']",
        "button[aria-label='Закрыть']",
        ".close-button",
        "[class*='popup'] button",
        "[class*='modal'] button[class*='close']",
    ]
    for selector in popup_selectors:
        try:
            close_btn = await page.query_selector(selector)
            if close_btn:
                await close_btn.click()
                await asyncio.sleep(0.3)
        except Exception:
            pass


# ───────────────────────────────────────────────
# Яндекс Путешествия
# ───────────────────────────────────────────────

async def search_yandex_travel(
    destination_airports: List[str],
    search_date: datetime,
) -> Optional[Dict]:
    """
    Парсит цены с travel.yandex.ru.
    Возвращает минимальную цену или None.
    """
    result = None
    async with async_playwright() as playwright:
        browser, context = await _create_browser_context(playwright)
        page = await context.new_page()

        try:
            # Формируем URL для поиска
            dest = destination_airports[0] if len(destination_airports) == 1 else destination_airports[0]
            dep_date = search_date.strftime("%Y-%m-%d")
            ret_date = (search_date + timedelta(days=7)).strftime("%Y-%m-%d")

            url = (
                f"https://travel.yandex.ru/avia/search/result/?"
                f"fromId=c{ORIGIN}&toId=c{dest}&"
                f"when={dep_date}&returnDate={ret_date}&"
                f"adults=1&children=0&infants=0&class=econom"
            )

            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await _random_delay(3, 5)
            await _close_popups(page)

            # Ждём загрузки результатов
            await page.wait_for_selector("[data-test-id='ticket']", timeout=15000)

            # Ищем цены
            price_elements = await page.query_selector_all("[data-test-id='price']")
            prices = []
            for el in price_elements[:5]:  # Топ-5 предложений
                text = await el.text_content()
                if text:
                    # Извлекаем число из текста вида "12 456 ₽"
                    digits = "".join(c for c in text if c.isdigit())
                    if digits:
                        prices.append(int(digits))

            if prices:
                result = {
                    "price": min(prices),
                    "airline": None,  # Яндекс не всегда показывает авиакомпанию в списке
                    "departure_date": dep_date,
                    "return_date": ret_date,
                    "source": "yandex",
                }

        except Exception as e:
            print(f"[Yandex] Ошибка для {destination_airports}: {e}")
            result = None

        finally:
            await context.close()
            await browser.close()

    return result


# ───────────────────────────────────────────────
# Туту
# ───────────────────────────────────────────────

async def search_tutu(
    destination_airports: List[str],
    search_date: datetime,
) -> Optional[Dict]:
    """
    Парсит цены с avia.tutu.ru.
    Возвращает минимальную цену или None.
    """
    result = None
    async with async_playwright() as playwright:
        browser, context = await _create_browser_context(playwright)
        page = await context.new_page()

        try:
            dest = destination_airports[0] if len(destination_airports) == 1 else destination_airports[0]
            dep_date = search_date.strftime("%Y-%m-%d")
            ret_date = (search_date + timedelta(days=7)).strftime("%Y-%m-%d")

            url = (
                f"https://avia.tutu.ru/s/?"
                f"class_econom=1&passengers_adults=1&"
                f"route[0]=LED-{dest}-{dep_date}&"
                f"route[1]={dest}-LED-{ret_date}"
            )

            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await _random_delay(3, 5)
            await _close_popups(page)

            # Ждём появления результатов
            await page.wait_for_selector("[class*='price']", timeout=15000)

            # Ищем элементы с ценами
            price_selectors = [
                "[class*='Price']",
                ".price",
                "[data-ti*='price']",
            ]
            prices = []
            for selector in price_selectors:
                elements = await page.query_selector_all(selector)
                for el in elements[:5]:
                    text = await el.text_content()
                    if text:
                        digits = "".join(c for c in text if c.isdigit())
                        if digits and int(digits) > 1000:  # Фильтруем мусор
                            prices.append(int(digits))
                if prices:
                    break

            if prices:
                result = {
                    "price": min(prices),
                    "airline": None,
                    "departure_date": dep_date,
                    "return_date": ret_date,
                    "source": "tutu",
                }

        except Exception as e:
            print(f"[Tutu] Ошибка для {destination_airports}: {e}")
            result = None

        finally:
            await context.close()
            await browser.close()

    return result


# ───────────────────────────────────────────────
# OneTwoTrip
# ───────────────────────────────────────────────

async def search_onetwotrip(
    destination_airports: List[str],
    search_date: datetime,
) -> Optional[Dict]:
    """
    Парсит цены с onetwotrip.com.
    Возвращает минимальную цену или None.
    """
    result = None
    async with async_playwright() as playwright:
        browser, context = await _create_browser_context(playwright)
        page = await context.new_page()

        try:
            dest = destination_airports[0] if len(destination_airports) == 1 else destination_airports[0]
            dep_date = search_date.strftime("%d.%m.%Y")
            ret_date = (search_date + timedelta(days=7)).strftime("%d.%m.%Y")

            url = (
                f"https://www.onetwotrip.com/ru/f/new/"
                f"?adult=1&child=0&infant=0&"
                f"class=Y&cs=Y&route={ORIGIN}{dest}{dep_date}{ret_date}"
            )

            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await _random_delay(3, 5)
            await _close_popups(page)

            # Ждём загрузки
            await page.wait_for_selector("[class*='price']", timeout=15000)

            price_selectors = [
                "[class*='Price']",
                ".price",
                "[data-price]",
            ]
            prices = []
            for selector in price_selectors:
                elements = await page.query_selector_all(selector)
                for el in elements[:5]:
                    text = await el.text_content()
                    if text:
                        digits = "".join(c for c in text if c.isdigit())
                        if digits and int(digits) > 1000:
                            prices.append(int(digits))
                if prices:
                    break

            if prices:
                result = {
                    "price": min(prices),
                    "airline": None,
                    "departure_date": dep_date,
                    "return_date": ret_date,
                    "source": "onetwotrip",
                }

        except Exception as e:
            print(f"[OneTwoTrip] Ошибка для {destination_airports}: {e}")
            result = None

        finally:
            await context.close()
            await browser.close()

    return result


# ───────────────────────────────────────────────
# Оркестратор поиска
# ───────────────────────────────────────────────

async def search_destination(
    destination_name: str,
    destination_type: str,
    destination_airports: List[str],
) -> Optional[Dict]:
    """
    Ищет минимальную цену для направления через доступные источники.
    Приоритет: Яндекс → Туту → OneTwoTrip.
    """
    # Выбираем даты для поиска: ближайшие доступные даты
    today = datetime.now()
    best_result = None

    # Перебираем разные длительности поездки
    for trip_days in range(TRIP_MIN_DAYS, TRIP_MAX_DAYS + 1, 3):
        search_date = today + timedelta(days=3)  # Начинаем поиск с завтрашнего дня + 2
        dep_date = search_date.strftime("%Y-%m-%d")
        ret_date = (search_date + timedelta(days=trip_days)).strftime("%Y-%m-%d")

        # Пробуем источники по очереди
        for source_func, source_name in [
            (search_yandex_travel, "yandex"),
            (search_tutu, "tutu"),
            (search_onetwotrip, "onetwotrip"),
        ]:
            try:
                result = await source_func(destination_airports, search_date)
                if result:
                    result["destination"] = destination_name
                    result["destination_type"] = destination_type
                    result["airport"] = destination_airports[0]
                    result["trip_days"] = trip_days

                    if best_result is None or result["price"] < best_result["price"]:
                        best_result = result

                    # Если нашли хорошую цену — не перебираем остальное
                    if best_result["price"] < 15000:
                        return best_result

                    break  # Переходим к следующей длительности

            except Exception as e:
                print(f"[{source_name}] Критическая ошибка: {e}")
                continue

        # Задержка между итерациями
        await asyncio.sleep(random.uniform(1, 2))

    return best_result


async def search_all_destinations(destinations: List[Tuple[str, str, List[str]]]) -> List[Dict]:
    """
    Ищет цены для всех направлений.
    Возвращает список результатов.
    """
    results = []

    for dest_type, name, airports in destinations:
        print(f"🔍 Поиск: {name} ({', '.join(airports)})")

        result = await search_destination(name, dest_type, airports)
        if result:
            results.append(result)
            print(f"  ✅ {result['price']:,} ₽ ({result['source']})")
        else:
            print(f"  ❌ Цены не найдены")

        # Задержка между направлениями чтобы не забанили IP
        await asyncio.sleep(DELAY_BETWEEN_DESTINATIONS)

    return results
