# get_chat_id.py — получение chat_id для Telegram-бота

"""
Запустите этот скрипт, напишите боту @Airdrey_bot /start,
и скрипт покажет ваш chat_id.
"""

import os
import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, filters

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8537390248:AAGsxHWWdV3siXrk9-xgAwGu5g6VNzmFp0k")


async def get_chat_id(update: Update, context) -> None:
    """Выводит chat_id при любом входящем сообщении."""
    chat_id = update.effective_chat.id
    user = update.effective_user.first_name or "Unknown"
    
    print(f"\n{'='*50}")
    print(f"👤 Пользователь: {user}")
    print(f"🆔 CHAT_ID: {chat_id}")
    print(f"{'='*50}")
    print(f"\nДобавьте в .env:")
    print(f"TELEGRAM_CHAT_ID={chat_id}")
    print(f"\nИли в GitHub Secrets:")
    print(f"TELEGRAM_CHAT_ID = {chat_id}")
    print(f"{'='*50}\n")

    await update.message.reply_text(
        f"✅ Ваш chat_id: `{chat_id}`\n\n"
        f"Добавьте его в `.env` или GitHub Secrets:")


def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN не задан!")
        print("Установите переменную окружения или пропишите в .env")
        return

    print("🤖 Бот запущен. Напишите ему /start в Telegram...")
    print(f"   Бот: @Airdrey_bot")
    print(f"   Ожидание сообщения...\n")

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(MessageHandler(filters.ALL, get_chat_id))
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
