import io
from telethon.tl.types import Message
from hikka import loader


@loader.tds
class SDPicsMod(loader.Module):
    """Модуль для сохранения самоуничтожающихся и одноразовых медиа."""

    strings = {
        "name": "SDPics",
        "description": "Модуль для сохранения самоуничтожающихся и одноразовых медиа.",
        "usage": "🚫 Пожалуйста, ответьте на самоуничтожающиеся медиа или одноразовое фото/видео.",
    }

    async def scmd(self, message: Message):
        """Команда для сохранения самоуничтожающихся или одноразовых медиа."""

        # Получаем сообщение, на которое был сделан ответ
        reply = await message.get_reply_message()

        # Проверяем, что медиа существует
        if not reply or not reply.media:
            return  # Если медиа нет, выходим

        # Проверка на самоуничтожающееся медиа с ttl_seconds
        if hasattr(reply.media, 'ttl_seconds') and reply.media.ttl_seconds > 0:
            try:
                # Скачиваем медиа в память
                file = io.BytesIO(await reply.download_media(bytes))
                file.name = reply.file.name  # Имя файла сохраняется

                # Отправляем файл себе в личные сообщения без уведомлений
                await self._client.send_file("me", file, silent=True)

            except Exception:
                pass  # Игнорируем ошибки

        # Проверка на одноразовое медиа (если оно только для просмотра один раз)
        elif hasattr(reply.media, 'flags') and reply.media.flags & 8:
            try:
                # Скачиваем медиа в память
                file = io.BytesIO(await reply.download_media(bytes))
                file.name = reply.file.name  # Имя файла сохраняется

                # Отправляем файл себе в личные сообщения без уведомлений
                await self._client.send_file("me", file, silent=True)

            except Exception:
                pass  # Игнорируем ошибки

        # Если медиа не самоуничтожающееся, но всё ещё поддерживает скачивание
        elif hasattr(reply.media, 'file') and hasattr(reply.media, 'mime_type'):
            try:
                # Скачиваем медиа в память
                file = io.BytesIO(await reply.download_media(bytes))
                file.name = reply.file.name  # Имя файла сохраняется
                await self._client.send_file("me", file, silent=True)
            except Exception:
                pass  # Игнорируем ошибки

        # Удаляем команду после выполнения, чтобы избежать следов
        await message.delete()
