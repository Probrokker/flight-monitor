# storage.py — работа с SQLite-базой цен

import sqlite3
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

DB_PATH = os.getenv("DB_PATH", "prices.db")


def _get_connection() -> sqlite3.Connection:
    """Создаёт подключение к базе с поддержкой типов."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Создаёт таблицы, если они не существуют."""
    conn = _get_connection()
    cursor = conn.cursor()

    # История всех найденных цен
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            destination TEXT NOT NULL,
            destination_type TEXT NOT NULL,
            airport TEXT,
            price INTEGER NOT NULL,
            airline TEXT,
            departure_date TEXT,
            return_date TEXT,
            search_date TEXT NOT NULL,
            source TEXT NOT NULL
        )
        """
    )

    # Актуальные минимумы (upsert по направлению)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            destination TEXT NOT NULL UNIQUE,
            destination_type TEXT NOT NULL,
            airport TEXT,
            price INTEGER NOT NULL,
            airline TEXT,
            departure_date TEXT,
            return_date TEXT,
            updated_at TEXT NOT NULL,
            source TEXT NOT NULL
        )
        """
    )

    conn.commit()
    conn.close()


def append_price(
    destination: str,
    destination_type: str,
    airport: Optional[str],
    price: int,
    airline: Optional[str],
    departure_date: Optional[str],
    return_date: Optional[str],
    source: str,
) -> None:
    """Добавляет запись в историю и обновляет актуальный минимум."""
    conn = _get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()

    # В историю
    cursor.execute(
        """
        INSERT INTO history (destination, destination_type, airport, price, airline, departure_date, return_date, search_date, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (destination, destination_type, airport, price, airline, departure_date, return_date, now, source),
    )

    # Upsert в актуальные цены
    cursor.execute(
        """
        INSERT INTO prices (destination, destination_type, airport, price, airline, departure_date, return_date, updated_at, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(destination) DO UPDATE SET
            destination_type = excluded.destination_type,
            airport = excluded.airport,
            price = excluded.price,
            airline = excluded.airline,
            departure_date = excluded.departure_date,
            return_date = excluded.return_date,
            updated_at = excluded.updated_at,
            source = excluded.source
        """,
        (destination, destination_type, airport, price, airline, departure_date, return_date, now, source),
    )

    conn.commit()
    conn.close()


def get_history(
    destination: str, days: int = 30
) -> List[Dict]:
    """Возвращает историю цен для направления за последние N дней."""
    conn = _get_connection()
    cursor = conn.cursor()
    since = (datetime.now() - timedelta(days=days)).isoformat()

    cursor.execute(
        """
        SELECT * FROM history
        WHERE destination = ? AND search_date > ?
        ORDER BY search_date DESC
        """,
        (destination, since),
    )

    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_rolling_average(destination: str, days: int = 7) -> Optional[float]:
    """Считает скользящее среднее цен для направления."""
    conn = _get_connection()
    cursor = conn.cursor()
    since = (datetime.now() - timedelta(days=days)).isoformat()

    cursor.execute(
        """
        SELECT AVG(price) as avg_price FROM history
        WHERE destination = ? AND search_date > ?
        """,
        (destination, since),
    )

    result = cursor.fetchone()
    conn.close()
    return result["avg_price"] if result and result["avg_price"] else None


def get_historical_minimum(destination: str) -> Optional[Tuple[int, str]]:
    """Возвращает исторический минимум цены и дату его появления."""
    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT price, search_date FROM history
        WHERE destination = ?
        ORDER BY price ASC, search_date DESC
        LIMIT 1
        """,
        (destination,),
    )

    result = cursor.fetchone()
    conn.close()
    if result:
        return (result["price"], result["search_date"])
    return None


def get_all_current_prices() -> List[Dict]:
    """Возвращает все актуальные минимальные цены."""
    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM prices ORDER BY destination")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_current_price(destination: str) -> Optional[Dict]:
    """Возвращает актуальную цену для конкретного направления."""
    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM prices WHERE destination = ?", (destination,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None
