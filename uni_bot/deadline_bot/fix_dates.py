from database import db
from datetime import datetime, timedelta


def fix_existing_dates():
    with db._get_connection() as conn:
        cursor = conn.cursor()
        # Находим записи с NULL датой
        cursor.execute("SELECT id FROM deadlines WHERE deadline_date IS NULL")
        null_dates = cursor.fetchall()

        if not null_dates:
            print("Нет записей с NULL датой")
            return

        print(f"Найдено {len(null_dates)} записей с NULL датой")

        # Устанавливаем дату по умолчанию (сегодня + 7 дней)
        default_date = (datetime.now() + timedelta(days=7)).strftime("%d.%m.%Y")

        for (id,) in null_dates:
            cursor.execute("""
                UPDATE deadlines 
                SET deadline_date = ?
                WHERE id = ?
            """, (default_date, id))

        conn.commit()
        print(f"Обновлено {len(null_dates)} записей")


if __name__ == "__main__":
    fix_existing_dates()