from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


class Keyboards:
    @staticmethod
    def get_main_menu_inline() -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.button(text="📝 Добавить дедлайн", callback_data="add_deadline")
        builder.button(text="📅 Мои дедлайны", callback_data="list_deadlines")
        builder.button(text="✏️ Редактировать дедлайн", callback_data="edit_deadline")
        builder.button(text="📌 Заметки", callback_data="notes_menu")
        builder.button(text="✅ Завершить дедлайн", callback_data="complete_deadline")
        builder.button(text="🗑 Удалить дедлайн", callback_data="delete_deadline")
        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def get_categories_inline() -> InlineKeyboardMarkup:
        categories = [
            ("📚 Домашняя работа", "category_Домашняя работа"),
            ("🔬 Лабораторная", "category_Лабораторная"),
            ("📝 Курсовая", "category_Курсовая"),
            ("📊 Отчет", "category_Отчет"),
            ("📖 Экзамен", "category_Экзамен"),
            ("❓ Другое", "category_Другое")
        ]
        builder = InlineKeyboardBuilder()
        for text, callback in categories:
            builder.button(text=text, callback_data=callback)
        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def deadline_list(deadlines: list, action_prefix: str) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        for dl in deadlines:
            builder.button(
                text=f"{dl['title']} ({dl['deadline_date']})",
                callback_data=f"{action_prefix}{dl['id']}"
            )
        builder.button(text="⬅️ Назад", callback_data="back_to_menu")
        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def notes_actions(deadline_id: int) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.button(text="➕ Добавить заметку", callback_data=f"add_note_{deadline_id}")
        builder.button(text="⬅️ Назад", callback_data="back_to_menu")
        builder.adjust(1)
        return builder.as_markup()