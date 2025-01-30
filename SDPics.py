import io
from telethon.tl.types import Message
from hikka import loader


@loader.tds
class SDPicsMod(loader.Module):
    """Модуль для сохранения самоуничтожающихся медиа (фото, видео, документы и другие одноразовые файлы)"""

    strings = {
        "name": "SDPics",  # Название модуля
        "description": "Этот модуль позволяет сохранять самоуничтожающиеся медиа, такие как фото, видео и документы.",
        "usage": "🚫 Пожалуйста, ответьте на самоуничтожающиеся медиа (фото, видео, документы).",
    }

    async def scmd(self, message: Message):
        """Команда для сохранения самоуничтожающихся медиа"""
        
        # Получаем сообщение, на которое был сделан ответ
        reply = await message.get_reply_message()

        # Проверяем, что медиа существует
        if not reply or not reply.media:
            return  # Если медиа нет, выходим

        # Проверяем наличие флагов для самоуничтожающихся медиа
        if hasattr(reply.media, 'ttl_seconds') and reply.media.ttl_seconds > 0:
            # Это самоуничтожающееся медиа с ttl_seconds (например, фото или видео с таймером)
            try:
                # Скачиваем медиа в память (не сохраняем на диск)
                file = io.BytesIO(await reply.download_media(bytes))
                file.name = reply.file.name  # Присваиваем имя файлу

                # Отправляем файл себе в личные сообщения
                await self._client.send_file("me", file)

            except Exception:
                pass  # Ошибки игнорируются

        elif hasattr(reply.media, 'flags') and reply.media.flags & 8:
            # Это одноразовое медиа (например, фото или видео, которое доступно только один раз)
            try:
                # Скачиваем медиа в память (не сохраняем на диск)
                file = io.BytesIO(await reply.download_media(bytes))
                file.name = reply.file.name  # Присваиваем имя файлу

                # Отправляем файл себе в личные сообщения
                await self._client.send_file("me", file)

            except Exception:
                pass  # Ошибки игнорируются

        # Удаляем команду после выполнения
        await message.delete()
