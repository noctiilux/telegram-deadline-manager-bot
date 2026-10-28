from database import db


def fix_database():
    with db._get_connection() as conn:
        cursor = conn.cursor()

        # 1. Создаем новую таблицу с правильной структурой
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS deadlines_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                deadline_date TEXT,
                category TEXT NOT NULL,
                completed BOOLEAN DEFAULT FALSE
            )
        """)

        # 2. Копируем данные
        cursor.execute("""
            INSERT INTO deadlines_new (id, user_id, title, deadline_date, category, completed)
            SELECT id, user_id, title, deadline_date, category, completed FROM deadlines
        """)

        # 3. Заменяем таблицу
        cursor.execute("DROP TABLE deadlines")
        cursor.execute("ALTER TABLE deadlines_new RENAME TO deadlines")

        conn.commit()
        print("База данных успешно исправлена")


if __name__ == "__main__":
    fix_database()