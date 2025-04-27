import io
import asyncio
import logging
from telethon import types
from .. import loader, utils

logger = logging.getLogger(__name__)

@loader.tds
class KeeperMod(loader.Module):
    """Пиздец как удобный модуль для моментального спасения всякой хуйни, которая самоуничтожается нахуй"""
    strings = {"name": "Keeper"}

    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        self._me = await client.get_me()
        self._silent_mode = True  # Всегда в тихом режиме

    def is_self_destruct(self, media):
        """Проверка на самоуничтожающееся говно"""
        if not media:
            return False
        return getattr(media, 'ttl_seconds', None) is not None or getattr(media, 'has_view_once', False)

    def get_extension(self, message):
        """Определяет тип этой парши по расширению"""
        if not message or not message.media:
            return ".хз"
            
        # Получаем MIME тип
        mime_type = getattr(message.media, 'mime_type', '')
        if not mime_type and hasattr(message.media, 'document'):
            mime_type = getattr(message.media.document, 'mime_type', '')
            
        # Определяем расширение на основе MIME типа
        extensions = {
            'image/jpeg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif',
            'video/mp4': '.mp4',
            'video/quicktime': '.mov',
            'audio/mpeg': '.mp3',
            'audio/ogg': '.ogg'
        }
        
        if mime_type in extensions:
            return extensions[mime_type]
        elif mime_type:
            main_type, sub_type = mime_type.split('/', 1)
            return f".{sub_type}"
        
        # Если не удалось определить по MIME, пробуем получить из атрибутов
        if hasattr(message.media, 'document') and hasattr(message.media.document, 'attributes'):
            for attr in message.media.document.attributes:
                if isinstance(attr, types.DocumentAttributeFilename) and attr.file_name:
                    return f".{attr.file_name.split('.')[-1]}"
        
        # Значение по умолчанию, если не удалось определить
        return ".jpg" if "image" in mime_type else ".mp4" if "video" in mime_type else ".файл"

    async def save_media(self, message):
        """Сохраняем эту хрень"""
        try:
            media_bytes = await message.download_media(bytes)
            if not media_bytes:
                return False
                
            file = io.BytesIO(media_bytes)
            ext = self.get_extension(message)
            timestamp = utils.get_chat_id(message)
            file.name = getattr(message.file, "name", f"stolen_{timestamp}{ext}")
            
            sender = message.sender
            caption = f"<b>🔒 Спиздили файл</b>\n"
            if sender:
                caption += f"<b>От:</b> {getattr(sender, 'first_name', 'хз кто')} {getattr(sender, 'last_name', '')}\n"
                caption += f"<b>Юзернейм:</b> @{getattr(sender, 'username', 'неизвестен')}"
                caption += f"<b>ID:</b> <code>{sender.id}</code>"
            
            await self.client.send_file("me", file, caption=caption)
            return True
        except Exception as e:
            logger.error(f"Блять, ошибка при сохранении: {e}")
            return False

    @loader.owner
    async def kpcmd(self, m):
        """Забрать медиа по реплаю"""
        reply = await m.get_reply_message()
        if not reply or not reply.media or not self.is_self_destruct(reply.media):
            return await m.delete()
        
        await m.delete()
        await self.save_media(reply)

    @loader.owner
    async def akpcmd(self, m):
        """Включить/выключить автосохранение"""
        state = self.db.get("Keeper", "state", False)
        
        # Переключаем состояние автосохранения
        self.db.set("Keeper", "state", not state)
        
        # Отправляем информацию в чат о текущем состоянии и сразу удаляем
        if state:
            temp_msg = await m.reply("Автосохранение **выключено**.")
        else:
            temp_msg = await m.reply("Автосохранение **включено**.")
            
        await m.delete()
        await asyncio.sleep(2)  # Ждём 2 секунды
        await temp_msg.delete()  # Удаляем уведомление

    async def watcher(self, m):
        """Смотрим за всеми сообщениями как ебаные шпионы"""
        if not m or not self.db.get("Keeper", "state", False):
            return
            
        if not m.media or not self.is_self_destruct(m.media):
            return
            
        if m.sender_id == self._me.id:
            return
            
        # Тихо воруем и сохраняем
        await self.save_media(m)
