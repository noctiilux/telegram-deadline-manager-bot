from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime

from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dateparser import parse
from dotenv import load_dotenv

from database import db
from keyboards import Keyboards


load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- Bot Initialization ---

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler()


class DeadlineForm(StatesGroup):
    title = State()
    date = State()
    category = State()


class EditDeadlineForm(StatesGroup):
    deadline_id = State()
    field = State()
    new_value = State()


class NoteForm(StatesGroup):
    deadline_id = State()
    content = State()



def validate_date(date_str: str) -> str | None:
    parsed = parse(date_str, languages=['ru'])
    if parsed and parsed >= datetime.now():
        return parsed.strftime("%d.%m.%Y")
    return None


async def on_startup():
    if not db.check_database():
        logger.error("База данных повреждена!")
        return False
    if not db.check_database_structure():
        logger.error("Ошибка структуры базы данных!")
        return False
    logger.info("База данных проверена и готова к работе")
    return True


async def main():
    try:
        logger.info("Запуск бота...")
        if not await on_startup():
            raise RuntimeError("Ошибка инициализации базы данных")

        scheduler.add_job(check_upcoming_deadlines, 'interval', minutes=15, id="deadline_checker")
        scheduler.start()

        await dp.start_polling(bot)
    except Exception as e:
        logger.critical(f"Критическая ошибка: {e}", exc_info=True)
    finally:
        if scheduler.running:
            scheduler.shutdown(wait=False)
        await bot.session.close()
        logger.info("Бот остановлен")


async def send_deadline_notification(user_id: int, deadline: dict):
    try:
        deadline_date = datetime.strptime(deadline['date'], "%d.%m.%Y")
        days_left = (deadline_date - datetime.now()).days

        message = {
            0: f"⏰ Сегодня последний день для '{deadline['title']}'!",
            1: f"⏰ Завтра истекает дедлайн '{deadline['title']}'!"
        }.get(days_left, f"⏰ До дедлайна '{deadline['title']}' осталось {days_left} дней")

        await bot.send_message(
            user_id,
            f"{message}\nДата: {deadline['date']}\nКатегория: {deadline['category']}",
            reply_markup=Keyboards.get_main_menu_inline()
        )
    except Exception as e:
        logger.error(f"Ошибка отправки уведомления: {e}")


async def check_upcoming_deadlines():
    logger.info("Проверка предстоящих дедлайнов...")
    deadlines = db.get_upcoming_deadlines(days=3)
    for dl in deadlines:
        await send_deadline_notification(dl['user_id'], dl)


# --- Command Handlers ---
@dp.message(lambda m: m.text == "/start")
async def start(message: Message):
    await message.answer(
        "📚 Добро пожаловать в бот для управления дедлайнами!",
        reply_markup=Keyboards.get_main_menu_inline()
    )

@dp.callback_query(F.data == "add_deadline")
async def handle_add_deadline_callback(callback: CallbackQuery, state: FSMContext):
    await state.set_state(DeadlineForm.title)
    await callback.message.edit_text("📝 Введите название дедлайна (макс. 100 символов):")
    await callback.answer()


@dp.message(DeadlineForm.title)
async def process_deadline_title(message: Message, state: FSMContext):
    if len(message.text) > 100:
        await message.answer("❌ Слишком длинное название!")
        return

    await state.update_data(title=message.text)
    await state.set_state(DeadlineForm.date)
    await message.answer("📅 Введите дату дедлайна:")


@dp.message(DeadlineForm.date)
async def process_deadline_date(message: Message, state: FSMContext):
    validated_date = validate_date(message.text)
    if not validated_date:
        await message.answer("❌ Неверная дата! Попробуйте ещё раз.")
        return

    await state.update_data(date=validated_date)
    await state.set_state(DeadlineForm.category)
    await message.answer("📂 Выберите категорию:", reply_markup=Keyboards.get_categories_inline())


@dp.callback_query(F.data.startswith("category_"), DeadlineForm.category)
async def process_deadline_category(callback: CallbackQuery, state: FSMContext):
    try:
        data = await state.get_data()
        category = callback.data.split('_')[1]

        deadline_id = db.add_deadline(
            user_id=callback.from_user.id,
            title=data['title'],
            date=data['date'],
            category=category
        )

        logger.info(f"Добавлен дедлайн ID {deadline_id} для пользователя {callback.from_user.id}")

        await callback.message.edit_text(
            f"✅ Дедлайн сохранен!\n\n"
            f"Название: {data['title']}\n"
            f"Дата: {data['date']}\n"
            f"Категория: {category}",
            reply_markup=Keyboards.get_main_menu_inline()
        )
    except Exception as e:
        logger.error(f"Ошибка сохранения дедлайна: {e}")
        await callback.answer("❌ Ошибка при сохранении", show_alert=True)
    finally:
        await state.clear()


@dp.message(DeadlineForm.title)
async def process_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(DeadlineForm.date)
    await message.answer("📅 Введите дату дедлайна:")


@dp.message(DeadlineForm.date)
async def process_date(message: Message, state: FSMContext):
    validated_date = validate_date(message.text)
    if not validated_date:
        await message.answer("❌ Неверная дата! Попробуйте ещё раз.")
        return
    await state.update_data(date=validated_date)
    await state.set_state(DeadlineForm.category)
    await message.answer("📂 Выберите категорию:", reply_markup=Keyboards.get_categories_inline())


@dp.callback_query(F.data.startswith("category_"), DeadlineForm.category)
async def process_category(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    category = callback.data.split('_')[1]
    db.add_deadline(callback.from_user.id, data['title'], data['date'], category)
    await callback.message.edit_text("✅ Дедлайн добавлен!", reply_markup=Keyboards.get_main_menu_inline())
    await state.clear()

@dp.callback_query(F.data == "list_deadlines")
async def handle_list_deadlines(callback: CallbackQuery):
    """Показывает список дедлайнов пользователя"""
    deadlines = db.get_active_deadlines(callback.from_user.id)

    if not deadlines:
        await callback.answer("🎉 У вас пока нет дедлайнов!")
        return

    response = ["📅 <b>Ваши дедлайны:</b>\n\n"]
    for dl in deadlines:
        status = "✅" if dl["completed"] else "🟡"
        date_str = dl.get("deadline_date", "❌ Дата не указана")

        response.append(
            f"{status} <b>{dl['title']}</b>\n"
            f"📅 {date_str}\n"
            f"theid>ID: <code>{dl['id']}</code>\n\n"
        )

    await callback.message.edit_text(''.join(response), parse_mode="HTML", reply_markup=Keyboards.get_main_menu_inline())
    await callback.answer()

# --- Edit Deadline ---
@dp.callback_query(F.data == "edit_deadline")
async def handle_edit_deadline(callback: CallbackQuery):
    deadlines = db.get_active_deadlines(callback.from_user.id)
    if not deadlines:
        await callback.answer("❌ Нет активных дедлайнов", show_alert=True)
        return
    await callback.message.edit_text("Выберите дедлайн для редактирования:",
                                    reply_markup=Keyboards.deadline_list(deadlines, "edit_"))


@dp.callback_query(F.data.startswith("edit_"))
async def select_field_to_edit(callback: CallbackQuery, state: FSMContext):
    deadline_id = int(callback.data.split("_")[1])
    deadline = db.get_deadline_by_id(deadline_id, callback.from_user.id)
    if not deadline:
        await callback.answer("❌ Дедлайн не найден", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    builder.button(text="📝 Название", callback_data=f"field_title_{deadline_id}")
    builder.button(text="📅 Дата", callback_data=f"field_date_{deadline_id}")
    builder.button(text="📂 Категория", callback_data=f"field_category_{deadline_id}")
    builder.button(text="⬅️ Назад", callback_data="back_to_menu")
    builder.adjust(1)

    await callback.message.edit_text(
        f"📌 Текущие данные:\n"
        f"Название: {deadline['title']}\n"
        f"Дата: {deadline['deadline_date']}\n"
        f"Категория: {deadline['category']}",
        reply_markup=builder.as_markup()
    )


@dp.callback_query(F.data.startswith("field_"))
async def ask_new_value(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    field_type, deadline_id = parts[1], int(parts[2])
    await state.set_state(EditDeadlineForm.new_value)
    await state.update_data(field=field_type, deadline_id=deadline_id)
    await callback.message.edit_text(f"Введите новое значение для '{field_type}':")


@dp.message(EditDeadlineForm.new_value)
async def update_deadline(message: Message, state: FSMContext):
    data = await state.get_data()
    field, deadline_id = data["field"], data["deadline_id"]
    value = message.text.strip()

    success = False
    if field == "title":
        success = db.update_deadline_title(deadline_id, message.from_user.id, value)
    elif field == "date":
        value = validate_date(value)
        if value:
            success = db.update_deadline_date(deadline_id, value, message.from_user.id)
        else:
            await message.answer("❌ Неверная дата")
            return
    elif field == "category":
        success = db.update_deadline_category(deadline_id, message.from_user.id, value)

    if success:
        await message.answer("✅ Поле обновлено!", reply_markup=Keyboards.get_main_menu_inline())
    else:
        await message.answer("❌ Ошибка обновления", reply_markup=Keyboards.get_main_menu_inline())

    await state.clear()


# --- Notes ---
@dp.callback_query(F.data == "notes_menu")
async def notes_menu(callback: CallbackQuery):
    deadlines = db.get_active_deadlines(callback.from_user.id)
    if not deadlines:
        await callback.answer("❌ Нет дедлайнов", show_alert=True)
        return
    await callback.message.edit_text("Выберите дедлайн для просмотра заметок:",
                                    reply_markup=Keyboards.deadline_list(deadlines, "notes_"))


@dp.callback_query(F.data.startswith("notes_"))
async def view_notes(callback: CallbackQuery):
    deadline_id = int(callback.data.split("_")[1])
    notes = db.get_notes(deadline_id, callback.from_user.id)
    text = "📌 <b>Заметки:</b>\n\n"
    if notes:
        for note in notes:
            text += f"{note['created_at']}:\n{note['content']}\n\n"
    else:
        text += "❌ Заметок пока нет."

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=Keyboards.notes_actions(deadline_id))


@dp.callback_query(F.data.startswith("add_note_"))
async def add_note_start(callback: CallbackQuery, state: FSMContext):
    deadline_id = int(callback.data.split("_")[2])
    await state.set_state(NoteForm.content)
    await state.update_data(deadline_id=deadline_id)
    await callback.message.edit_text("🖋 Введите текст заметки:")


@dp.message(NoteForm.content)
async def add_note_finish(message: Message, state: FSMContext):
    data = await state.get_data()
    db.add_note(data['deadline_id'], message.from_user.id, message.text)
    await message.answer("✅ Заметка добавлена!", reply_markup=Keyboards.get_main_menu_inline())
    await state.clear()


# --- Delete/Complete ---
@dp.callback_query(F.data == "delete_deadline")
async def handle_delete_deadline(callback: CallbackQuery):
    deadlines = db.get_active_deadlines(callback.from_user.id)
    if not deadlines:
        await callback.answer("🗑 Нет дедлайнов для удаления", show_alert=True)
        return
    await callback.message.edit_text("Выберите дедлайн для удаления:",
                                    reply_markup=Keyboards.deadline_list(deadlines, "delete_"))


@dp.callback_query(F.data.startswith("delete_"))
async def process_delete(callback: CallbackQuery):
    deadline_id = int(callback.data.split("_")[1])
    if db.delete_deadline(deadline_id, callback.from_user.id):
        await callback.answer("🗑 Удалено")
        await callback.message.edit_text("Дедлайн удален.", reply_markup=Keyboards.get_main_menu_inline())
    else:
        await callback.answer("❌ Не найден", show_alert=True)


@dp.callback_query(F.data == "complete_deadline")
async def handle_complete_deadline(callback: CallbackQuery):
    deadlines = db.get_active_deadlines(callback.from_user.id)
    if not deadlines:
        await callback.answer("✅ Нет дедлайнов", show_alert=True)
        return
    await callback.message.edit_text("Выберите дедлайн для завершения:",
                                    reply_markup=Keyboards.deadline_list(deadlines, "complete_"))


@dp.callback_query(F.data.startswith("complete_"))
async def process_complete(callback: CallbackQuery):
    deadline_id = int(callback.data.split("_")[1])
    if db.complete_deadline(deadline_id, callback.from_user.id):
        await callback.answer("✅ Завершено")
        await callback.message.edit_text("Дедлайн завершен.", reply_markup=Keyboards.get_main_menu_inline())
    else:
        await callback.answer("❌ Не найден", show_alert=True)


# --- Back to Menu ---
@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    await callback.message.edit_text("📚 Главное меню:",
                                    reply_markup=Keyboards.get_main_menu_inline())


@dp.message()
async def unknown_message(message: Message):
    await message.answer("❌ Неизвестная команда.", reply_markup=Keyboards.get_main_menu_inline())


@dp.callback_query()
async def unknown_callback(callback: CallbackQuery):
    logger.warning(f"Неизвестный callback: {callback.data}")
    await callback.answer("❌ Неизвестная команда", show_alert=True)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен вручную")