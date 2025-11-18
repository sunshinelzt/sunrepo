# meta developer: @sunshinelzt

import io
import os
import asyncio
import logging
import tempfile
from hikkatl import types
from .. import loader, utils

logger = logging.getLogger(__name__)

@loader.tds
class KeeperMod(loader.Module):
    """Пиздец какой удобный модуль для моментального сохранения всякой хуйни, которая самоуничтожается нахуй"""
    
    strings = {
        "name": "Keeper",
        "saved": "<emoji document_id=6046410905829251121>💥</emoji> <b>Спиздил {media_type}</b>",
        "auto_on": "<emoji document_id=6044327262575141199>🌟</emoji> Автосохранение <b>включено</b>.",
        "auto_off": "<emoji document_id=6044327262575141199>🌟</emoji> Автосохранение <b>выключено</b>.",
        "from": "От", "username": "Юзернейм", "id": "ID",
        "no_media": "Нет медиа для сохранения",
        "sent_as_document": "<i>(отправлено как документ)</i>",
        "sender_unknown": "неизвестно", "name_unknown": "не указан",
        "media_types": {
            "photo": "фото", "video": "видео", "video_note": "кружочек",
            "voice": "голосовое", "audio": "аудио", "animation": "гифку",
            "document": "файл", "media": "медиа"
        }
    }
    
    strings_ru = strings.copy()

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue("auto_save", False, "Автосохранение скрытых медиа", validator=loader.validators.Boolean()),
            loader.ConfigValue("save_chat", "me", "Чат для сохранения медиа (ID чата/канала/группы или 'me' для избранного)", validator=loader.validators.String()),
            loader.ConfigValue("enable_logging", False, "Включить логирование работы модуля", validator=loader.validators.Boolean()),
        )
        self._me = None

    async def client_ready(self):
        self._me = await self._client.get_me()

    def _log(self, level, message):
        if self.config.get("enable_logging", False):
            getattr(logger, level)(message)

    def is_self_destruct(self, message):
        if not message or not message.media:
            return False
        
        media = message.media
        checks = [
            getattr(media, 'spoiler', False),
            getattr(media, 'ttl_seconds', None),
            getattr(media, 'once', False)
        ]
        
        if any(checks):
            return True
            
        if hasattr(media, 'document'):
            doc = media.document
            if getattr(doc, 'ttl_seconds', None) or getattr(doc, 'once', False):
                return True
                
            for attr in getattr(doc, 'attributes', []):
                if isinstance(attr, types.DocumentAttributeAudio) and attr.voice and getattr(media, 'once', False):
                    return True
                elif isinstance(attr, types.DocumentAttributeVideo) and attr.round_message and (getattr(media, 'once', False) or getattr(media, 'ttl_seconds', None)):
                    return True
        
        return False

    def get_extension_and_type(self, message):
        if not message or not message.media:
            return ".unknown", "document"
        
        mime_map = {
            'image/jpeg': ('.jpg', 'photo'), 'image/jpg': ('.jpg', 'photo'), 'image/png': ('.png', 'photo'),
            'image/gif': ('.gif', 'animation'), 'image/webp': ('.webp', 'photo'), 'video/mp4': ('.mp4', 'video'),
            'video/mpeg': ('.mpeg', 'video'), 'video/webm': ('.webm', 'video'), 'audio/mpeg': ('.mp3', 'audio'),
            'audio/ogg': ('.ogg', 'audio'), 'audio/wav': ('.wav', 'audio'), 'application/pdf': ('.pdf', 'document')
        }
        
        mime_type = getattr(message.media, 'mime_type', '') or getattr(getattr(message.media, 'document', None), 'mime_type', '')
        
        if hasattr(message.media, 'document') and hasattr(message.media.document, 'attributes'):
            for attr in message.media.document.attributes:
                if isinstance(attr, types.DocumentAttributeAudio):
                    return ('.ogg', 'voice') if attr.voice else ('.mp3', 'audio')
                elif isinstance(attr, types.DocumentAttributeVideo):
                    return ('.mp4', 'video_note') if attr.round_message else ('.mp4', 'video')
                elif isinstance(attr, types.DocumentAttributeFilename) and attr.file_name:
                    try:
                        ext = f".{attr.file_name.split('.')[-1].lower()}"
                        type_map = {
                            ('.jpg', '.jpeg', '.png', '.webp'): 'photo',
                            ('.gif',): 'animation',
                            ('.mp4', '.avi', '.mkv'): 'video',
                            ('.mp3', '.ogg', '.wav'): 'audio'
                        }
                        for exts, media_type in type_map.items():
                            if ext in exts:
                                return ext, media_type
                        return ext, 'document'
                    except:
                        pass
        
        if mime_type in mime_map:
            return mime_map[mime_type]
        
        if hasattr(message.media, 'photo'):
            return '.jpg', 'photo'
        
        main_type = mime_type.split('/')[0] if '/' in mime_type else ''
        type_map = {'image': ('photo', '.jpg'), 'video': ('video', '.mp4'), 'audio': ('audio', '.mp3')}
        
        if main_type in type_map:
            media_type, ext = type_map[main_type]
            return ext, 'animation' if main_type == 'image' and 'gif' in mime_type else media_type
        
        return ".file", 'document'

    def _make_caption(self, message):
        try:
            _, media_type = self.get_extension_and_type(message)
            media_name = self.strings["media_types"].get(media_type, self.strings["media_types"]["media"])
            caption = self.strings["saved"].format(media_type=media_name).rstrip('\n') + "\n"
            
            sender = message.sender
            if sender and hasattr(sender, 'id'):
                try:
                    first_name = getattr(sender, 'first_name', None) or self.strings["name_unknown"]
                    last_name = getattr(sender, 'last_name', None) or ''
                    username = getattr(sender, 'username', None) or ''
                    sender_id = sender.id
                    
                    display_name = str(first_name) + (f" {last_name}" if last_name else "")
                    display_name = (utils.escape_html(display_name) if hasattr(utils, 'escape_html') 
                                  else display_name.replace('<', '&lt;').replace('>', '&gt;'))
                    
                    caption += f"<b>{self.strings['from']}:</b> <a href='tg://user?id={sender_id}'>{display_name}</a>\n"
                    if username:
                        caption += f"<b>{self.strings['username']}:</b> @{username}\n"
                    caption += f"<b>{self.strings['id']}:</b> <code>{sender_id}</code>"
                except Exception as e:
                    self._log("warning", f"Ошибка при обработке отправителя: {e}")
                    caption += f"<b>{self.strings['id']}:</b> <code>{getattr(sender, 'id', self.strings['sender_unknown'])}</code>"
            else:
                caption += f"<b>Отправитель:</b> {self.strings['sender_unknown']}"
            
            return caption
        except Exception as e:
            self._log("warning", f"Ошибка при создании подписи: {e}")
            return self.strings["saved"].format(media_type=self.strings["media_types"]["media"]) + f"<b>Ошибка подписи</b>"

    def _get_save_chat(self):
        save_chat = self.config.get("save_chat", "me")
        if save_chat == "me":
            return "me"
        try:
            return int(save_chat)
        except (ValueError, TypeError):
            self._log("warning", f"Неверный формат ID чата: {save_chat}, использую 'me'")
            return "me"

    async def save_media(self, message):
        temp_file_path = None
        try:
            if not message or not message.media:
                return False
            
            save_chat = self._get_save_chat()
            ext, media_type = self.get_extension_and_type(message)
            timestamp = int(utils.time.time())
            temp_filename = f"keeper_{timestamp}_{message.sender_id if message.sender else 'unknown'}{ext}"
            temp_file_path = os.path.join(tempfile.gettempdir(), temp_filename)
            
            try:
                await asyncio.wait_for(message.download_media(temp_file_path), timeout=120.0)
            except asyncio.TimeoutError:
                self._log("error", "Таймаут при скачивании медиа")
                return False
            
            if not os.path.exists(temp_file_path) or os.path.getsize(temp_file_path) == 0:
                self._log("error", "Скачанный файл пустой или не создался")
                return False
            
            caption = self._make_caption(message)
            
            for attempt in range(3):
                try:
                    with open(temp_file_path, 'rb') as f:
                        file_io = io.BytesIO(f.read())
                    file_io.name = f"media{ext}"
                    
                    send_params = {
                        'entity': save_chat, 'file': file_io, 'caption': caption, 'parse_mode': 'html'
                    }
                    
                    if media_type == 'voice':
                        send_params['voice_note'] = True
                    elif media_type == 'video_note':
                        send_params['video_note'] = True
                    elif media_type in ['photo', 'animation', 'video', 'audio']:
                        send_params['force_document'] = False
                        if media_type == 'video':
                            send_params['supports_streaming'] = True
                    else:
                        send_params['force_document'] = True
                    
                    await self._client.send_file(**send_params)
                    self._log("info", f"Медиа успешно сохранено как {media_type} в {save_chat}")
                    return True
                    
                except Exception as send_error:
                    self._log("error", f"Попытка {attempt + 1} отправки не удалась: {send_error}")
                    if attempt == 2:
                        try:
                            with open(temp_file_path, 'rb') as f:
                                file_io = io.BytesIO(f.read())
                            file_io.name = f"backup_media{ext}"
                            
                            await self._client.send_file(
                                save_chat, file_io,
                                caption=caption + "\n" + self.strings["sent_as_document"],
                                parse_mode='html', force_document=True
                            )
                            self._log("warning", "Медиа отправлено как документ после неудачи")
                            return True
                        except Exception as backup_error:
                            self._log("error", f"Даже резервная отправка не удалась: {backup_error}")
                            return False
                    await asyncio.sleep(1)
            
            return False
            
        except Exception as e:
            self._log("error", f"Критическая ошибка при сохранении медиа: {e}")
            return False
        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                    self._log("debug", f"Временный файл удален: {temp_file_path}")
                except Exception as cleanup_error:
                    self._log("warning", f"Ошибка при удалении временного файла: {cleanup_error}")

    @loader.command(ru_doc="Забрать медиа по реплаю")
    async def kp(self, message):
        """Забрать медиа по реплаю"""
        try:
            await message.delete()
            reply = await message.get_reply_message()
            if not reply or not reply.media or not self.is_self_destruct(reply):
                return
            await self.save_media(reply)
        except Exception as e:
            self._log("error", f"Ошибка в команде kp: {e}")
            try:
                await message.delete()
            except:
                pass

    @loader.command(ru_doc="Включить/выключить автосохранение")
    async def akp(self, message):
        """Включить/выключить автосохранение"""
        self.config["auto_save"] = not self.config["auto_save"]
        status_msg = self.strings["auto_on"] if self.config["auto_save"] else self.strings["auto_off"]
        
        if utils.get_chat_id(message) == self._me.id or message.is_private:
            temp_msg = await utils.answer(message, status_msg)

    async def watcher(self, message):
        """Смотрим за всеми сообщениями как ебаные шпионы"""
        if (not self.config.get("auto_save", False) or not message or not message.media or 
            not self.is_self_destruct(message) or message.sender_id == self._me.id):
            return
        
        try:
            await self.save_media(message)
        except Exception as e:
            self._log("error", f"Ошибка в watcher при сохранении: {e}")
