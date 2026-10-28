import sqlite3

from database import db
from datetime import datetime


def migrate_database():
    with db._get_connection() as conn:
        cursor = conn.cursor()

        # 1. Добавляем недостающие столбцы
        try:
            cursor.execute("ALTER TABLE deadlines ADD COLUMN date TEXT")
        except sqlite3.OperationalError:
            pass

        # 2. Копируем данные из deadline_date в date
        cursor.execute("""
            UPDATE deadlines 
            SET date = deadline_date
            WHERE date IS NULL AND deadline_date IS NOT NULL
        """)

        # 3. Устанавливаем значения по умолчанию
        cursor.execute("""
            UPDATE deadlines
            SET date = 'Дата не указана'
            WHERE date IS NULL
        """)

        conn.commit()


if __name__ == "__main__":
    migrate_database()
    print("Миграция базы данных завершена")