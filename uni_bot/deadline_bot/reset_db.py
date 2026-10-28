from database import db
import os

def reset_database():
    if os.path.exists("deadlines.db"):
        os.remove("deadlines.db")
        print("База данных удалена")
    else:
        print("Файл базы данных не найден")

if __name__ == "__main__":
    reset_database()