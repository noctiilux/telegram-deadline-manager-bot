import logging
from aiogram import Bot
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from database import db

logger = logging.getLogger(__name__)


class NotificationManager:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.notification_intervals = [
            (timedelta(days=7), "7 дней"),
            (timedelta(days=3), "3 дня"),
            (timedelta(days=1), "24 часа"),
            (timedelta(hours=6), "6 часов"),
            (timedelta(hours=1), "1 час")
        ]

    async def check_upcoming_deadlines(self):
        """Проверяет приближающиеся дедлайны и отправляет уведомления"""
        logger.info("⏰ Запуск проверки дедлайнов")

        try:
            deadlines = db.get_active_deadlines()
            if not deadlines:
                logger.info("Нет активных дедлайнов для проверки")
                return

            now = datetime.now()
            notified_deadlines = set()

            for deadline in deadlines:
                try:
                    await self._process_deadline(deadline, now, notified_deadlines)
                except Exception as e:
                    logger.error(f"Ошибка обработки дедлайна ID {deadline.get('id')}: {e}")

            logger.info(f"Проверка завершена. Обработано {len(deadlines)} дедлайнов")

        except Exception as e:
            logger.critical(f"Критическая ошибка при проверке дедлайнов: {e}")

    async def _process_deadline(self, deadline: Dict, now: datetime, notified_deadlines: set):
        """Обрабатывает отдельный дедлайн"""
        deadline_id = deadline['id']
        if deadline_id in notified_deadlines:
            return

        try:
            deadline_date = datetime.strptime(deadline['deadline_date'], "%d.%m.%Y")
            time_left = deadline_date - now

            if time_left < timedelta(0):
                await self._handle_expired_deadline(deadline)
                return

            for interval, message in self.notification_intervals:
                if time_left <= interval:
                    if deadline_id not in notified_deadlines:
                        await self._send_notification(deadline, message)
                        notified_deadlines.add(deadline_id)
                        break

        except ValueError as e:
            logger.error(f"Некорректная дата в дедлайне ID {deadline_id}: {deadline['deadline_date']}")
            await self._handle_invalid_deadline(deadline)

    async def _send_notification(self, deadline: Dict, time_left: str):
        """Отправляет уведомление о дедлайне"""
        try:
            user_id = deadline['user_id']
            message = self._format_notification(deadline, time_left)

            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode="HTML"
            )
            logger.info(f"Уведомление отправлено пользователю {user_id} о дедлайне {deadline['id']}")

        except Exception as e:
            logger.error(f"Ошибка отправки уведомления для дедлайна {deadline['id']}: {e}")

    def _format_notification(self, deadline: Dict, time_left: str) -> str:
        """Форматирует текст уведомления"""
        return (
            f"⏰ <b>Напоминание о дедлайне!</b>\n\n"
            f"📌 <b>{deadline['title']}</b>\n"
            f"📅 Дата: <code>{deadline['deadline_date']}</code>\n"
            f"⏳ Осталось: <b>{time_left}</b>\n"
            f"🏷 Категория: {deadline['category']}\n\n"
            f"ID: <code>{deadline['id']}</code>"
        )

    async def _handle_expired_deadline(self, deadline: Dict):
        """Обрабатывает просроченный дедлайн"""
        try:
            if not deadline['completed']:
                await self._send_expired_notification(deadline)
                db.mark_deadline_expired(deadline['id'])
        except Exception as e:
            logger.error(f"Ошибка обработки просроченного дедлайна {deadline['id']}: {e}")

    async def _send_expired_notification(self, deadline: Dict):
        """Отправляет уведомление о просроченном дедлайне"""
        try:
            await self.bot.send_message(
                chat_id=deadline['user_id'],
                text=f"⌛️ <b>Дедлайн просрочен!</b>\n\n"
                     f"«{deadline['title']}» должен был быть выполнен {deadline['deadline_date']}",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления о просрочке: {e}")

    async def _handle_invalid_deadline(self, deadline: Dict):
        """Обрабатывает дедлайн с некорректной датой"""
        try:
            await self.bot.send_message(
                chat_id=deadline['user_id'],
                text=f"⚠️ <b>Обнаружена проблема с дедлайном!</b>\n\n"
                     f"Дедлайн «{deadline['title']}» имеет некорректную дату.\n"
                     f"Пожалуйста, обновите дату дедлайна.",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления о проблеме: {e}")


async def setup_notifications(bot: Bot, scheduler):
    """Настраивает периодическую проверку дедлайнов"""
    manager = NotificationManager(bot)

    # Добавляем задачу в планировщик
    scheduler.add_job(
        manager.check_upcoming_deadlines,
        'interval',
        minutes=30,
        id='deadline_checker'
    )

    # Немедленный запуск первой проверки
    await manager.check_upcoming_deadlines()