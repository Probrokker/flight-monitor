# 📊 Мониторинг авиабилетов LED → Telegram

Сервис для мониторинга минимальных цен на авиабилеты из Санкт-Петербурга (LED) с отправкой отчётов в Telegram.

## Возможности

- Автоматический поиск 2 раза в день (07:00 и 13:00 МСК)
- Парсинг цен с Яндекс Путешествий, Туту, OneTwoTrip
- SQLite-база с историей цен и детекцией аномалий
- Telegram-бот с командами: `/today`, `/history`, `/alerts`, `/help`
- Алерты при падении цены ≥20% или достижении исторического минимума

## Стек

Python 3.11, Playwright, python-telegram-bot v20+, SQLite

## Структура

- `main.py` — оркестратор, запускает поиск и отправляет отчёты
- `sources.py` — парсинг цен с сайтов
- `storage.py` — работа с SQLite
- `alerts.py` — детекция аномалий и трендов
- `bot.py` — Telegram-бот (команды и ответы)
- `airports.py` — справочник аэропортов и направлений
- `get_chat_id.py` — получение `chat_id` для бота
- `.github/workflows/monitor.yml` — GitHub Actions cron

## Запуск

### Локально

```bash
pip install -r requirements.txt
playwright install chromium
python main.py
```

### Получение chat_id

```bash
python get_chat_id.py
```

Напишите боту `@Airdrey_bot` → `/start`, скопируйте `chat_id` в `.env`.

### GitHub Actions

1. Загрузите код в репозиторий
2. В Settings → Secrets and variables → Actions добавьте:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
3. Workflow запускается автоматически по cron

## Переменные окружения (.env)

```env
TELEGRAM_BOT_TOKEN=8537390248:AAGsxHWWdV3siXrk9-xgAwGu5g6VNzmFp0k
TELEGRAM_CHAT_ID=your_chat_id_here
```

## Команды бота

- `/today` — актуальные цены из SQLite
- `/history <направление> [дней]` — график цен с трендами
- `/alerts` — текущие аномалии
- `/help` — справка

## Лицензия

Проект создан для личного использования.
