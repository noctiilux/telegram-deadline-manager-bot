from database import db
from datetime import datetime


def migrate():
    with db._get_connection() as conn:
        cursor = conn.cursor()

        # 1. Создаем временную таблицу
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS deadlines_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                deadline_date TEXT,
                category TEXT NOT NULL,
                completed BOOLEAN DEFAULT FALSE,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 2. Копируем данные с преобразованием дат
        cursor.execute("""
            INSERT INTO deadlines_new 
            SELECT 
                id, user_id, title, 
                CASE 
                    WHEN deadline_date IS NULL THEN NULL
                    ELSE strftime('%d.%m.%Y', deadline_date)
                END as deadline_date,
                category, completed, created_at
            FROM deadlines
        """)

        # 3. Заменяем старую таблицу новой
        cursor.execute("DROP TABLE deadlines")
        cursor.execute("ALTER TABLE deadlines_new RENAME TO deadlines")

        conn.commit()


if __name__ == "__main__":
    migrate()
    print("Миграция базы данных успешно завершена")