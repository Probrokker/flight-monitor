# bot.py — Telegram-бот для мониторинга цен

import os
import logging
from typing import Optional

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from storage import get_all_current_prices, get_history, get_current_price, init_db
from alerts import get_all_alerts, format_alert_line, get_price_trend_symbol

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Токен из переменных окружения
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик /start — приветствие и инструкции."""
    chat_id = update.effective_chat.id
    text = (
        "✈️ *Мониторинг авиабилетов LED*\n\n"
        "Привет! Я бот для отслеживания цен на авиабилеты из Санкт-Петербурга.\n\n"
        "*Команды:*\n"
        "`/today` — актуальные цены\n"
        "`/history <направление> [дней]` — график цен\n"
        "`/alerts` — аномалии и скидки\n"
        "`/help` — справка\n\n"
        f"📍 Ваш `chat_id`: `{chat_id}`\n"
        "Добавьте его в `.env` для автоматических отчётов."
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик /help."""
    text = (
        "*Команды бота:*\n\n"
        "`/today` — текущие минимальные цены по всем направлениям\n"
        "`/history Москва` — история цен на Москву за 30 дней\n"
        "`/history Москва 7` — история за 7 дней\n"
        "`/alerts` — текущие аномалии (падение ≥20% или рекордный минимум)\n"
        "`/start` — приветствие и получение chat_id\n\n"
        "Отчёты приходят автоматически в 07:00 и 13:00 МСК."
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def today_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик /today — актуальные цены."""
    records = get_all_current_prices()
    if not records:
        await update.message.reply_text("📭 База пуста. Запустите поиск или дождитесь автоматического отчёта.")
        return

    lines = ["📊 *Актуальные цены LED → мир*\n"]

    domestic = [r for r in records if r["destination_type"] == "domestic"]
    international = [r for r in records if r["destination_type"] == "international"]

    if domestic:
        lines.append("\n🇷🇺 *Россия:*")
        for r in domestic:
            trend = get_price_trend_symbol(r["destination"], r["price"])
            lines.append(f"• {r['destination']}: {r['price']:,} ₽ {trend}")

    if international:
        lines.append("\n🌍 *Зарубеж:*")
        for r in international:
            trend = get_price_trend_symbol(r["destination"], r["price"])
            lines.append(f"• {r['destination']}: {r['price']:,} ₽ {trend}")

    text = "\n".join(lines)
    # Разбиваем на части если сообщение слишком длинное
    if len(text) > 4000:
        text = text[:4000] + "\n... (обрезано)"

    await update.message.reply_text(text, parse_mode="Markdown")


async def history_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик /history <направление> [дней]."""
    args = context.args
    if not args:
        await update.message.reply_text(
            "Использование: `/history <направление> [дней]`\n"
            "Пример: `/history Москва 7`",
            parse_mode="Markdown",
        )
        return

    destination = args[0]
    days = int(args[1]) if len(args) > 1 and args[1].isdigit() else 30

    records = get_history(destination, days)
    if not records:
        await update.message.reply_text(f"📭 Нет истории для *{destination}* за {days} дней.")
        return

    # Формируем текстовый график
    lines = [f"📈 *История цен: {destination}* (за {days} дней)\n"]

    # Группируем по дате, берём минимум за день
    daily_min = {}
    for r in records:
        date = r["search_date"][:10]  # YYYY-MM-DD
        price = r["price"]
        if date not in daily_min or price < daily_min[date]:
            daily_min[date] = price

    # Сортируем по дате
    sorted_dates = sorted(daily_min.keys())

    if len(sorted_dates) >= 2:
        # Рисуем тренд
        for i, date in enumerate(sorted_dates):
            price = daily_min[date]
            if i == 0:
                symbol = "→"
            else:
                prev = daily_min[sorted_dates[i - 1]]
                if price < prev * 0.95:
                    symbol = "▼"
                elif price > prev * 1.05:
                    symbol = "▲"
                else:
                    symbol = "→"
            lines.append(f"{date}: {price:,} ₽ {symbol}")
    else:
        for date in sorted_dates:
            lines.append(f"{date}: {daily_min[date]:,} ₽")

    # Статистика
    prices = list(daily_min.values())
    lines.append(f"\n📊 Мин: {min(prices):,} ₽ | Макс: {max(prices):,} ₽ | Сред: {sum(prices)//len(prices):,} ₽")

    text = "\n".join(lines)
    if len(text) > 4000:
        text = text[:4000] + "\n... (обрезано)"

    await update.message.reply_text(text, parse_mode="Markdown")


async def alerts_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик /alerts — текущие аномалии."""
    alerts = get_all_alerts()
    if not alerts:
        await update.message.reply_text("🟢 Аномалий не обнаружено. Всё спокойно.")
        return

    lines = ["🚨 *Текущие аномалии:*\n"]
    for alert in alerts:
        lines.append(
            format_alert_line(
                alert["destination"],
                alert["current_price"],
                alert,
                alert.get("destination_type", "domestic"),
            )
        )

    text = "\n".join(lines)
    if len(text) > 4000:
        text = text[:4000] + "\n... (обрезано)"

    await update.message.reply_text(text, parse_mode="Markdown")


async def unknown_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ответ на неизвестные сообщения."""
    await update.message.reply_text(
        "Не понял команду 🤔\n"
        "Напишите `/help` для списка команд."
    )


async def send_report(chat_id: int, report_text: str) -> None:
    """Отправляет отчёт в указанный чат."""
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN не задан")
        return

    application = Application.builder().token(token).build()
    await application.bot.send_message(chat_id=chat_id, text=report_text, parse_mode="Markdown")
    await application.shutdown()


def run_bot() -> None:
    """Запускает бота в режиме polling."""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN не задан в окружении!")
        return

    init_db()

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("help", help_handler))
    application.add_handler(CommandHandler("today", today_handler))
    application.add_handler(CommandHandler("history", history_handler))
    application.add_handler(CommandHandler("alerts", alerts_handler))
    application.add_handler(MessageHandler(filters.COMMAND, unknown_handler))

    logger.info("Бот запущен в режиме polling")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    run_bot()
