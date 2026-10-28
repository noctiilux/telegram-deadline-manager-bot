import sqlite3
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

# Настройка логгирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_path: str = "deadlines.db"):
        self.db_path = Path(db_path)
        self._init_db()
        self._create_indexes()
        self._fix_database_issues()  # Исправляем возможные проблемы при старте
        logger.info(f"Database initialized at {self.db_path}")

    def _init_db(self):
        """Инициализирует таблицы в базе данных"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Таблица дедлайнов
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS deadlines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    deadline_date TEXT NOT NULL,  -- Основное поле для даты
                    category TEXT NOT NULL,
                    completed BOOLEAN DEFAULT FALSE,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Таблица заметок

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    deadline_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(deadline_id) REFERENCES deadlines(id) ON DELETE CASCADE
                )
            """)
            conn.commit()


    def _create_indexes(self):
        """Создает индексы для ускорения запросов"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_deadlines_user ON deadlines(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_deadlines_date ON deadlines(deadline_date)",
                "CREATE INDEX IF NOT EXISTS idx_deadlines_completed ON deadlines(completed)",
                "CREATE INDEX IF NOT EXISTS idx_notes_deadline ON notes(deadline_id)",
                "CREATE INDEX IF NOT EXISTS idx_notes_user ON notes(user_id)"
            ]
            for index_sql in indexes:
                try:
                    cursor.execute(index_sql)
                except sqlite3.Error as e:
                    logger.error(f"Error creating index: {e}")
            conn.commit()

    def _fix_database_issues(self):
        """Исправляет возможные проблемы в структуре базы данных"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                # 1. Проверяем наличие всех необходимых столбцов
                cursor.execute("PRAGMA table_info(deadlines)")
                columns = [col[1] for col in cursor.fetchall()]
                # 2. Если есть старое поле 'date', переносим данные в 'deadline_date'
                if 'date' in columns and 'deadline_date' in columns:
                    cursor.execute("""
                        UPDATE deadlines 
                        SET deadline_date = date
                        WHERE deadline_date IS NULL OR deadline_date = ''
                    """)
                # 3. Удаляем лишние столбцы если они есть
                for col in ['old_date', 'temp_column']:  # Добавьте здесь другие ненужные столбцы
                    if col in columns:
                        self._safe_drop_column(conn, 'deadlines', col)
                conn.commit()
            except sqlite3.Error as e:
                logger.error(f"Database fixing error: {e}")
                conn.rollback()

    def _safe_drop_column(self, conn, table: str, column: str):
        """Безопасное удаление столбца через создание новой таблицы"""
        cursor = conn.cursor()
        # Получаем информацию о текущей таблице
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [col[1] for col in cursor.fetchall() if col[1] != column]
        if column not in columns:
            return
        # Создаем новую таблицу без этого столбца
        columns_str = ', '.join(columns)
        cursor.execute(f"""
            CREATE TABLE new_{table} AS 
            SELECT {columns_str} FROM {table}
        """)
        # Удаляем старую и переименовываем новую
        cursor.execute(f"DROP TABLE {table}")
        cursor.execute(f"ALTER TABLE new_{table} RENAME TO {table}")

    def _get_connection(self) -> sqlite3.Connection:
        """Возвращает соединение с базой данных"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Для доступа к полям по имени
        conn.execute("PRAGMA foreign_keys = ON")  # Включаем внешние ключи
        return conn

    def _validate_date(self, date_str: str) -> str:
        """Проверяет и форматирует дату"""
        try:
            date_obj = datetime.strptime(date_str, "%d.%m.%Y")
            return date_obj.strftime("%d.%m.%Y")
        except ValueError:
            logger.warning(f"Invalid date format: {date_str}, using current date")
            return datetime.now().strftime("%d.%m.%Y")

    # --- Основные методы для работы с дедлайнами ---
    def add_deadline(self, user_id: int, title: str, date: str, category: str) -> int:
        """Добавляет новый дедлайн"""
        formatted_date = self._validate_date(date)
        with self._get_connection() as conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO deadlines (user_id, title, deadline_date, category)
                    VALUES (?, ?, ?, ?)
                """, (user_id, title, formatted_date, category))
                conn.commit()
                return cursor.lastrowid
            except sqlite3.Error as e:
                logger.error(f"Error adding deadline: {e}")
                conn.rollback()
                return -1

    def get_deadlines(self, user_id: int, include_completed: bool = False) -> List[Dict]:
        """Получает все дедлайны пользователя"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if include_completed:
                cursor.execute("""
                    SELECT * FROM deadlines 
                    WHERE user_id = ?
                    ORDER BY date(deadline_date) ASC
                """, (user_id,))
            else:
                cursor.execute("""
                    SELECT * FROM deadlines 
                    WHERE user_id = ? AND completed = FALSE
                    ORDER BY date(deadline_date) ASC
                """, (user_id,))
            return [dict(row) for row in cursor.fetchall()]

    def get_active_deadlines(self, user_id: int) -> List[Dict]:
        """Получает активные дедлайны пользователя"""
        return self.get_deadlines(user_id, include_completed=False)

    def complete_deadline(self, deadline_id: int, user_id: int) -> bool:
        with self._get_connection() as conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE deadlines 
                    SET completed = TRUE, 
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND user_id = ?
                """, (deadline_id, user_id))
                conn.commit()
                return cursor.rowcount > 0
            except sqlite3.Error as e:
                logger.error(f"Error completing deadline: {e}")
                conn.rollback()
                return False

    def delete_deadline(self, deadline_id: int, user_id: int) -> bool:
        with self._get_connection() as conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM deadlines 
                    WHERE id = ? AND user_id = ?
                """, (deadline_id, user_id))
                conn.commit()
                return cursor.rowcount > 0
            except sqlite3.Error as e:
                logger.error(f"Error deleting deadline: {e}")
                conn.rollback()
                return False

    def update_deadline_date(self, deadline_id: int, new_date: str, user_id: int) -> bool:
        """Обновляет дату дедлайна"""
        formatted_date = self._validate_date(new_date)
        with self._get_connection() as conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE deadlines 
                    SET deadline_date = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND user_id = ?
                """, (formatted_date, deadline_id, user_id))
                conn.commit()
                return cursor.rowcount > 0
            except sqlite3.Error as e:
                logger.error(f"Error updating deadline: {e}")
                conn.rollback()
                return False

    def get_upcoming_deadlines(self, days: int = 3) -> List[Dict]:
        """Получает предстоящие дедлайны"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    id,
                    user_id,
                    title,
                    deadline_date as date,
                    category
                FROM deadlines
                WHERE completed = FALSE
                  AND date(deadline_date) BETWEEN date('now') AND date('now', ?, 'days')
                ORDER BY date(deadline_date)
            """, (days,))
            return [dict(row) for row in cursor.fetchall()]

    # --- Методы для работы с заметками ---
    def add_note(self, deadline_id: int, user_id: int, content: str) -> int:
        """Добавляет заметку к дедлайну"""
        with self._get_connection() as conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO notes (deadline_id, user_id, content)
                    VALUES (?, ?, ?)
                """, (deadline_id, user_id, content))
                conn.commit()
                return cursor.lastrowid
            except sqlite3.Error as e:
                logger.error(f"Error adding note: {e}")
                conn.rollback()
                return -1

    def check_database_structure(self) -> bool:
        """Проверяет наличие всех необходимых таблиц и столбцов"""
        required_tables = {
            'deadlines': ['id', 'user_id', 'title', 'deadline_date', 'category', 'completed'],
            'notes': ['id', 'deadline_id', 'user_id', 'content']
        }
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Проверяем наличие таблиц
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = {row[0] for row in cursor.fetchall()}
            if not required_tables.keys() <= existing_tables:
                return False
            # Проверяем столбцы в каждой таблице
            for table, columns in required_tables.items():
                cursor.execute(f"PRAGMA table_info({table})")
                existing_columns = {row[1] for row in cursor.fetchall()}
                if not set(columns) <= existing_columns:
                    return False
        return True

    def get_deadline_by_id(self, deadline_id: int, user_id: int) -> Optional[Dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM deadlines WHERE id = ? AND user_id = ?", (deadline_id, user_id))
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_deadline_title(self, deadline_id: int, user_id: int, new_title: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE deadlines SET title = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND user_id = ?
            """, (new_title, deadline_id, user_id))
            conn.commit()
            return cursor.rowcount > 0

    def update_deadline_category(self, deadline_id: int, user_id: int, new_category: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE deadlines SET category = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND user_id = ?
            """, (new_category, deadline_id, user_id))
            conn.commit()
            return cursor.rowcount > 0

    def get_notes(self, deadline_id: int, user_id: int) -> List[Dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    id,
                    content,
                    strftime('%d.%m.%Y %H:%M', created_at) as created_at
                FROM notes
                WHERE deadline_id = ? AND user_id = ?
                ORDER BY created_at DESC
            """, (deadline_id, user_id))
            return [dict(row) for row in cursor.fetchall()]

    def check_database(self) -> bool:
        """Проверяет целостность базы данных"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            return result[0] == "ok" if result else False


# Глобальный экземпляр для использования
db = Database()
