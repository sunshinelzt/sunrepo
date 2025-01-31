import io
from telethon.tl.types import Message
from hikka import loader

@loader.tds
class SDPicsMod(loader.Module):
    """Модуль для сохранения самоуничтожающихся медиа."""

    strings = {
        "name": "SDPics",
        "description": "Модуль для сохранения самоуничтожающихся медиа.",
        "usage": "🚫 Пожалуйста, ответьте на самоуничтожающееся медиа.",
    }

    async def scmd(self, message: Message):
        """Команда для сохранения самоуничтожающихся медиа."""

        # Получаем сообщение, на которое был сделан ответ
        reply = await message.get_reply_message()

        # Проверяем, что медиа существует и оно самоуничтожающееся (имеет ttl_seconds)
        if not self._is_valid_media(reply):
            return

        # Скачиваем и сохраняем медиа
        await self._save_media(reply)

        # Удаляем команду и сообщение, чтобы избежать следов
        await message.delete()

    def _is_valid_media(self, reply: Message) -> bool:
        """Проверяет, является ли медиа самоуничтожающимся."""
        if not reply or not reply.media:
            return False

        # Проверяем, что медиа имеет ttl_seconds и оно больше 0
        return hasattr(reply.media, 'ttl_seconds') and reply.media.ttl_seconds > 0

    async def _save_media(self, reply: Message):
        """Скачивает и отправляет медиа в личные сообщения."""
        try:
            # Скачиваем медиа в память
            file = io.BytesIO(await reply.download_media(bytes))
            file.name = reply.file.name  # Имя файла сохраняется

            # Отправляем файл себе в личные сообщения без уведомлений
            await self._client.send_file("me", file, silent=True)

            # Удаляем медиа после того как оно сохранено, чтобы не оставлять следов
            await reply.delete()

        except Exception:
            pass  # Игнорируем ошибки
