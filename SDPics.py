import io
from telethon.tl.types import Message
from hikka import loader, utils

@loader.tds
class SDPicsMod(loader.Module):
    """Module to save self-destructing media (photos, videos, audios, documents, etc.)"""

    strings = {
        "name": "SDPics",
        "usage": "🚫 <b>Please, reply to self-destructing media (photo, video, audio, document, etc.)</b>",
    }

    strings_ru = {
        "usage": "🚫 <b>Пожалуйста, ответь на самоуничтожающееся фото, видео, аудио, документ и другие типы медиа</b>",
        "_cls_doc": "Модуль для сохранения самоуничтожающихся медиа (фото, видео, аудио, документы и другие типы)",
        "_cmd_doc_s": "<Реплай на самоуничтожающееся медиа>",
    }

    async def scmd(self, message: Message):
        """<reply to self-destructing media>"""
        reply = await message.get_reply_message()

        # Проверяем, что медиа существует и оно самоуничтожающееся
        if not reply or not reply.media:
            await utils.answer(message, self.strings("usage"))
            return

        # Проверяем на самоуничтожение по времени (TTL) или одноразовое (флаг)
        if reply.media.ttl_seconds or reply.media.flags & 8:
            # Загружаем медиа
            file = io.BytesIO(await reply.download_media(bytes))
            file.name = reply.file.name
            
            # Отправляем файл себе
            await self._client.send_file("me", file)
