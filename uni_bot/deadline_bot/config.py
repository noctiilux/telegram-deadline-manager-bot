from dotenv import load_dotenv
import os

# Явно указываем путь к .env (если файл в той же папке)
load_dotenv(dotenv_path=".env")  # или просто load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
