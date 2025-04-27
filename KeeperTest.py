import io
import asyncio
import logging
from telethon import types
from .. import loader, utils

logger = logging.getLogger(__name__)

@loader.tds
class KeeperMod(loader.Module):
    """Пиздец какой удобный модуль для моментального сохранения всякой хуйни, которая самоуничтожается нахуй"""
    strings = {"name": "Keeper"}

    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        self._me = await client.get_me()
        self._silent_mode = True

    def is_self_destruct(self, media):
        """Проверка на самоуничтожающееся говно"""
        if not media:
            return False
            
        # Проверка на TTL (таймер самоуничтожения)
        if getattr(media, 'ttl_seconds', None) is not None:
            return True
            
        # Флаг "просмотреть один раз"
        if getattr(media, 'has_view_once', False):
            return True
            
        # Видеосообщения (кружочки) только с флагом "просмотреть 1 раз"
        if hasattr(media, 'round_message') and media.round_message and getattr(media, 'has_view_once', False):
            return True
            
        # Проверка самоуничтожающихся голосовых и кружков
        if hasattr(media, 'document'):
            for attr in getattr(media.document, 'attributes', []):
                if isinstance(attr, types.DocumentAttributeAudio) and attr.voice:
                    if getattr(media, 'has_view_once', False):
                        return True
                # Проверка круглых видеосообщений через атрибуты (только самоуничтожающиеся)
                elif isinstance(attr, types.DocumentAttributeVideo):
                    if getattr(attr, 'round_message', False) and getattr(media, 'has_view_once', False):
                        return True
                        
        return False

    def get_extension(self, message):
        """Определяет тип этой параши по расширению"""
        if not message or not message.media:
            return ".хз"
            
        mime_type = getattr(message.media, 'mime_type', '')
        if not mime_type and hasattr(message.media, 'document'):
            mime_type = getattr(message.media.document, 'mime_type', '')
            
        extensions = {
            'image/jpeg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif',
            'image/webp': '.webp',
            'video/mp4': '.mp4',
            'video/quicktime': '.mov',
            'audio/mpeg': '.mp3',
            'audio/ogg': '.ogg',
            'application/pdf': '.pdf'
        }
        
        # Улучшенное определение видеокружков
        if hasattr(message.media, 'document'):
            for attr in getattr(message.media.document, 'attributes', []):
                # Голосовые сообщения
                if isinstance(attr, types.DocumentAttributeAudio) and attr.voice:
                    return '.ogg'
                # Видеокружки
                elif isinstance(attr, types.DocumentAttributeVideo) and getattr(attr, 'round_message', False):
                    return '.mp4'
        
        # Прямая проверка на кружки (запасной вариант)
        if hasattr(message.media, 'round_message') and message.media.round_message:
            return '.mp4'
        
        # Стандартная проверка MIME-типа
        if mime_type in extensions:
            return extensions[mime_type]
        elif mime_type:
            main_type, sub_type = mime_type.split('/', 1)
            return f".{sub_type}"
        
        # Проверка атрибута имени файла
        if hasattr(message.media, 'document') and hasattr(message.media.document, 'attributes'):
            for attr in message.media.document.attributes:
                if isinstance(attr, types.DocumentAttributeFilename) and attr.file_name:
                    return f".{attr.file_name.split('.')[-1]}"
        
        # Запасной вариант по типу MIME
        return ".jpg" if "image" in mime_type else ".mp4" if "video" in mime_type else ".файл"

    def get_media_type_info(self, message):
        """Пиздатая функция определения типа медиа с доп. информацией"""
        media_info = {
            "type": "хз что",
            "duration": None,
            "is_voice": False,
            "is_video_note": False,
            "has_view_once": False
        }
        
        if not message or not message.media:
            return media_info
        
        # Проверка флага "просмотреть один раз"
        media_info["has_view_once"] = getattr(message.media, 'has_view_once', False)
        
        # Проверка таймера самоуничтожения
        if getattr(message.media, 'ttl_seconds', None) is not None:
            media_info["ttl_seconds"] = getattr(message.media, 'ttl_seconds')
        
        # Прямая проверка на кружки
        if hasattr(message.media, 'round_message') and message.media.round_message:
            media_info["type"] = "кружок"
            media_info["is_video_note"] = True
            return media_info
        
        # Проверка атрибутов медиа
        if hasattr(message.media, 'document'):
            for attr in getattr(message.media.document, 'attributes', []):
                # Голосовые сообщения
                if isinstance(attr, types.DocumentAttributeAudio):
                    if attr.voice:
                        media_info["type"] = "голосовое"
                        media_info["is_voice"] = True
                        media_info["duration"] = attr.duration
                    else:
                        media_info["type"] = "аудио"
                        media_info["duration"] = attr.duration
                    return media_info
                
                # Видеокружки
                elif isinstance(attr, types.DocumentAttributeVideo):
                    if getattr(attr, 'round_message', False):
                        media_info["type"] = "кружок"
                        media_info["is_video_note"] = True
                        media_info["duration"] = attr.duration
                        return media_info
                    else:
                        media_info["type"] = "видео"
                        media_info["duration"] = attr.duration
        
        # Определение по MIME-типу
        mime_type = getattr(message.media, 'mime_type', '')
        if not mime_type and hasattr(message.media, 'document'):
            mime_type = getattr(message.media.document, 'mime_type', '')
        
        if mime_type.startswith('image/'):
            media_info["type"] = "фото"
        elif mime_type.startswith('video/'):
            media_info["type"] = "видео"
        elif mime_type.startswith('audio/'):
            media_info["type"] = "аудио"
        
        return media_info

    async def save_media(self, message):
        """Сохраняем эту хуйню с улучшенной обработкой"""
        try:
            media_bytes = await message.download_media(bytes)
            if not media_bytes:
                logger.error("Не удалось скачать медиа, хуй знает почему")
                return False
                
            file = io.BytesIO(media_bytes)
            ext = self.get_extension(message)
            timestamp = utils.get_chat_id(message)
            file.name = getattr(message.file, "name", f"спизжено_{timestamp}{ext}")
            
            media_info = self.get_media_type_info(message)
            
            sender = message.sender
            caption = f"<emoji document_id=6046410905829251121>💥</emoji> <b>Спиздил медиа</b>\n"
            
            if sender:
                first_name = getattr(sender, 'first_name', 'хз кто')
                last_name = getattr(sender, 'last_name', '')
                username = getattr(sender, 'username', 'хз какой')
                
                caption += f"<b>От:</b> {first_name}"
                if last_name:
                    caption += f" {last_name}"
                caption += "\n"
                
                caption += f"<b>Юзернейм:</b> @{username}\n"
                caption += f"<b>ID:</b> <code>{sender.id}</code>"
            
            # Добавляем инфу о типе медиа в подпись
            if media_info["is_video_note"]:
                caption += "\n<b>Тип:</b> Кружок"
                if media_info["duration"]:
                    caption += f" ({media_info['duration']}с)"
            elif media_info["is_voice"]:
                caption += "\n<b>Тип:</b> Голосовое сообщение"
                if media_info["duration"]:
                    caption += f" ({media_info['duration']}с)"
            else:
                caption += f"\n<b>Тип:</b> {media_info['type'].capitalize()}"
            
            if media_info["has_view_once"]:
                caption += "\n<b>Просмотр один раз:</b> Да, нахуй"
            
            if "ttl_seconds" in media_info:
                caption += f"\n<b>Таймер самоуничтожения:</b> {media_info['ttl_seconds']}с"
            
            await self.client.send_file("me", file, caption=caption)
            logger.info(f"Заебись, успешно сохранил самоуничтожающееся медиа типа: {media_info['type']}")
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
        success = await self.save_media(reply)
        
        if not self._silent_mode and success:
            temp_msg = await m.respond("✅ Заебись, медиа сохранено!")
            await asyncio.sleep(2)
            await temp_msg.delete()

    @loader.owner
    async def smcmd(self, m):
        """Вкл/выкл уведомления о сохранении"""
        self._silent_mode = not self._silent_mode
        
        state = "выключены" if self._silent_mode else "включены"
        temp_msg = await m.reply(f"<emoji document_id=6044327262575141199>🌟</emoji> Уведомления {state}, нахуй.")
        
        await m.delete()
        await asyncio.sleep(2)
        await temp_msg.delete()

    @loader.owner
    async def akpcmd(self, m):
        """Включить/выключить автосохранение"""
        state = self.db.get("Keeper", "state", False)
        
        self.db.set("Keeper", "state", not state)
        
        if state:
            temp_msg = await m.reply("<emoji document_id=6044327262575141199>🌟</emoji> Автосохранение <b>выключено</b>.")
        else:
            temp_msg = await m.reply("<emoji document_id=6044327262575141199>🌟</emoji> Автосохранение <b>включено</b>.")
            
        await m.delete()
        await asyncio.sleep(2)
        await temp_msg.delete()

    async def watcher(self, m):
        """Смотрим за всеми сообщениями как ебаные шпионы"""
        if not m or not self.db.get("Keeper", "state", False):
            return
            
        if not m.media or not self.is_self_destruct(m.media):
            return
            
        if m.sender_id == self._me.id:
            return
            
        await self.save_media(m)
