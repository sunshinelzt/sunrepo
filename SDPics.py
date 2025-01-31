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

    async def s_cmd(self, message: Message):
        """Скрытная команда для сохранения самоуничтожающихся или одноразовых медиа."""

        # Получаем сообщение, на которое был сделан ответ
        reply = await message.get_reply_message()

        # Проверяем, что медиа существует
        if not reply or not reply.media:
            await message.delete()  # Удаляем команду, если медиа нет
            return

        try:
            # Скачиваем медиа в память
            file = io.BytesIO(await reply.download_media(bytes))
            file.name = reply.file.name or "saved_media"  # Имя файла сохраняется или задаётся по умолчанию

            # Отправляем файл себе в личные сообщения без уведомлений
            await self._client.send_file("me", file, silent=True)

        except Exception:
            pass  # Игнорируем ошибки, чтобы не оставлять следов

        # Удаляем команду после выполнения, чтобы избежать следов
        await message.delete()
