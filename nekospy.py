__version__ = (1, 1, 1)

# meta developer: @sunshinelzt
# scope: heroku_only

import asyncio
import contextlib
import io
import logging
import time
import typing

from telethon.tl.types import (
    DocumentAttributeFilename,
    Message,
    PeerUser,
    UpdateDeleteMessages,
    UpdateEditMessage,
)
from telethon.utils import get_display_name

from .. import loader, utils

logger = logging.getLogger(__name__)


@loader.tds
class NekoSpy(loader.Module):
    """Отправляет удаленные и/или отредактированные сообщения из личных сообщений"""

    rei = "<emoji document_id=5409143295039252230>👩‍🎤</emoji>"
    pm = "<emoji document_id=6048540195995782913>👤</emoji>"

    strings = {
        "name": "NekoSpy",
        "state": f"{rei} <b>Режим слежения в ЛС теперь {{}}</b>",
        "spybl": f"{rei} <b>Пользователь добавлен в черный список для слежения</b>",
        "spybl_removed": f"{rei} <b>Пользователь удален из черного списка для слежения</b>",
        "spybl_clear": f"{rei} <b>Черный список для слежения очищен</b>",
        "spywl": f"{rei} <b>Пользователь добавлен в белый список для слежения</b>",
        "spywl_removed": f"{rei} <b>Пользователь удален из белого списка для слежения</b>",
        "spywl_clear": f"{rei} <b>Белый список для слежения очищен</b>",
        "whitelist": f"\n{rei} <b>Слежу только за сообщениями от пользователей:</b>\n{{}}",
        "always_track": f"\n{rei} <b>Всегда слежу за сообщениями от пользователей:</b>\n{{}}",
        "blacklist": f"\n{rei} <b>Игнорирую сообщения от пользователей:</b>\n{{}}",
        "pm": f"{pm} <b>Слежу за сообщениями в личных сообщениях</b>\n",
        "mode_off": f"{pm} <b>Не отслеживаю сообщения </b><code>{{}}spymode</code>\n",
        "deleted_pm": (
            '🗑 <b><a href="{}">{}</a> удалил сообщение в личке.</b>\n'
            '<b>Содержимое:</b>\n{}'
        ),
        "edited_pm": (
            '🔏 <b><a href="{}">{}</a> отредактировал сообщение в личке.</b>\n'
            '<b>Старое содержимое:</b>\n{}'
        ),
        "on": "включен",
        "off": "выключен",
        "cfg_whitelist": "Список пользователей, от которых нужно сохранять сообщения",
        "cfg_blacklist": "Список пользователей, от которых нужно игнорировать сообщения",
        "cfg_always_track": (
            "Список пользователей, от которых всегда следует отслеживать сообщения"
        ),
        "cfg_log_edits": "Сохранять отредактированные сообщения",
        "cfg_ignore_inline": "Игнорировать сообщения из инлайн-режима",
        "cfg_fw_protect": "Защита от флудвейтов при пересылке (секунды)",
    }

    def __init__(self):
        self._tl_channel = None
        self._channel = None
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "whitelist",
                [],
                lambda: self.strings("cfg_whitelist"),
                validator=loader.validators.Series(),
            ),
            loader.ConfigValue(
                "blacklist",
                [],
                lambda: self.strings("cfg_blacklist"),
                validator=loader.validators.Series(),
            ),
            loader.ConfigValue(
                "always_track",
                [],
                lambda: self.strings("cfg_always_track"),
                validator=loader.validators.Series(),
            ),
            loader.ConfigValue(
                "log_edits",
                True,
                lambda: self.strings("cfg_log_edits"),
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "ignore_inline",
                True,
                lambda: self.strings("cfg_ignore_inline"),
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "fw_protect",
                2.0,
                lambda: self.strings("cfg_fw_protect"),
                validator=loader.validators.Float(minimum=0.0),
            ),
        )

        self._queue = []
        self._cache = {}
        self._next = 0

    @loader.loop(interval=0.1, autostart=True)
    async def sender(self):
        """Очередь для отправки сообщений с защитой от флудвейтов"""
        if not self._queue or self._next > time.time():
            return

        try:
            item = self._queue.pop(0)
            await item
            self._next = time.time() + self.config["fw_protect"]
        except Exception as e:
            logger.error(f"Ошибка в sender loop: {e}")

    @staticmethod
    def _int(value: typing.Union[str, int]) -> typing.Union[str, int]:
        """Конвертирует строку в int, если возможно"""
        return int(value) if str(value).isdigit() else value

    @property
    def blacklist(self):
        """Получает черный список с системными ID"""
        system_ids = [777000, self._client.tg_id]
        if hasattr(self, 'inline') and hasattr(self.inline, 'bot_id'):
            system_ids.append(self.inline.bot_id)
        
        return list(map(self._int, self.config["blacklist"] + [x for x in system_ids if x]))

    @blacklist.setter
    def blacklist(self, value: list):
        """Устанавливает черный список, исключая системные ID"""
        system_ids = {777000, self._client.tg_id}
        if hasattr(self, 'inline') and hasattr(self.inline, 'bot_id'):
            system_ids.add(self.inline.bot_id)
        
        self.config["blacklist"] = list(set(value) - system_ids)

    @property
    def whitelist(self):
        """Получает белый список"""
        return list(map(self._int, self.config["whitelist"]))

    @whitelist.setter
    def whitelist(self, value: list):
        """Устанавливает белый список"""
        self.config["whitelist"] = value

    @property
    def always_track(self):
        """Получает список для постоянного отслеживания"""
        return list(map(self._int, self.config["always_track"]))

    async def client_ready(self):
        """Инициализация клиента и создание канала"""
        try:
            channel, _ = await utils.asset_channel(
                self._client,
                "heroku-nekospy",
                "Удаленные и отредактированные сообщения из ЛС появляются здесь",
                silent=True,
                invite_bot=True,
                avatar="https://pm1.narvii.com/6733/0e0380ca5cd7595de53f48c0ce541d3e2f2effc4v2_hq.jpg",
                _folder="heroku",
            )
            
            self._channel = int(f"-100{channel.id}")
            self._tl_channel = channel.id
            logger.info(f"NekoSpy канал создан: {self._channel}")
        except Exception as e:
            logger.error(f"Не удалось создать канал NekoSpy: {e}")

    @loader.command(ru_doc="Переключить режим слежения в ЛС")
    async def spymode(self, message: Message):
        """Переключить режим слежения в ЛС"""
        new_state = not self.get("state", False)
        self.set("state", new_state)
        
        await utils.answer(
            message,
            self.strings("state").format(
                self.strings("on" if new_state else "off")
            ),
        )

    @loader.command(ru_doc="Добавить / удалить пользователя из черного списка")
    async def spybl(self, message: Message):
        """Добавить / удалить пользователя из черного списка"""
        if not message.is_private:
            await utils.answer(message, "❌ <b>Эта команда работает только в ЛС</b>")
            return
            
        user_id = utils.get_chat_id(message)
        current_blacklist = self.config["blacklist"]
        
        if user_id in current_blacklist:
            self.config["blacklist"] = [x for x in current_blacklist if x != user_id]
            await utils.answer(message, self.strings("spybl_removed"))
        else:
            self.config["blacklist"] = current_blacklist + [user_id]
            await utils.answer(message, self.strings("spybl"))

    @loader.command(ru_doc="Очистить черный список")
    async def spyblclear(self, message: Message):
        """Очистить черный список"""
        self.config["blacklist"] = []
        await utils.answer(message, self.strings("spybl_clear"))

    @loader.command(ru_doc="Добавить / удалить пользователя из белого списка")
    async def spywl(self, message: Message):
        """Добавить / удалить пользователя из белого списка"""
        if not message.is_private:
            await utils.answer(message, "❌ <b>Эта команда работает только в ЛС</b>")
            return
            
        user_id = utils.get_chat_id(message)
        current_whitelist = self.config["whitelist"]
        
        if user_id in current_whitelist:
            self.config["whitelist"] = [x for x in current_whitelist if x != user_id]
            await utils.answer(message, self.strings("spywl_removed"))
        else:
            self.config["whitelist"] = current_whitelist + [user_id]
            await utils.answer(message, self.strings("spywl"))

    @loader.command(ru_doc="Очистить белый список")
    async def spywlclear(self, message: Message):
        """Очистить белый список"""
        self.config["whitelist"] = []
        await utils.answer(message, self.strings("spywl_clear"))

    def _get_pm_link(self, user_id: int) -> str:
        """Создает ссылку для перехода в ЛС по ID пользователя"""
        return f"tg://user?id={user_id}"

    async def _get_entities_list(self, entities: list) -> str:
        """Получает отформатированный список пользователей"""
        result = []
        for user_id in entities:
            try:
                user = await self._client.get_entity(user_id, exp=0)
                url = self._get_pm_link(user_id)
                name = get_display_name(user)
                if hasattr(utils, 'escape_html'):
                    name = utils.escape_html(name)
                result.append(
                    f"\u0020\u2800\u0020\u2800<emoji document_id=4971987363145188045>▫️</emoji> "
                    f'<b><a href="{url}">{name}</a></b>'
                )
            except Exception as e:
                logger.warning(f"Не удалось получить информацию о пользователе {user_id}: {e}")
                result.append(
                    f"\u0020\u2800\u0020\u2800<emoji document_id=4971987363145188045>▫️</emoji> "
                    f"<b>ID: {user_id}</b>"
                )
        return "\n".join(result)

    @loader.command(ru_doc="Показать текущую конфигурацию режима слежения")
    async def spyinfo(self, message: Message):
        """Показать текущую конфигурацию режима слежения"""
        if not self.get("state"):
            await utils.answer(
                message, self.strings("mode_off").format(self.get_prefix())
            )
            return

        info = self.strings("pm")

        if self.whitelist:
            info += self.strings("whitelist").format(
                await self._get_entities_list(self.whitelist)
            )

        if self.config["blacklist"]:
            info += self.strings("blacklist").format(
                await self._get_entities_list(self.config["blacklist"])
            )

        if self.always_track:
            info += self.strings("always_track").format(
                await self._get_entities_list(self.always_track)
            )

        await utils.answer(message, info)

    def _should_capture(self, user_id: int) -> bool:
        """Проверяет, нужно ли захватывать сообщение от пользователя"""
        return (
            user_id not in self.blacklist
            and (
                not self.whitelist
                or user_id in self.whitelist
            )
        )

    def _format_user_name(self, user) -> str:
        """Форматирует имя пользователя с экранированием HTML"""
        name = get_display_name(user)
        if hasattr(utils, 'escape_html'):
            return utils.escape_html(name)
        return name.replace('<', '&lt;').replace('>', '&gt;')

    async def _send_to_channel(self, content: str, media_message: Message = None):
        """Отправляет сообщение в канал слежения"""
        if not self._channel or not hasattr(self, 'inline'):
            logger.warning("Канал или inline бот недоступен")
            return
            
        try:
            content = self.inline.sanitise_text(content)

            # Если нет медиа - отправляем текстом
            if not media_message or not media_message.media:
                
                if media_message and media_message.sticker:
                    content += "\n\n&lt;стикер&gt;"
                    
                self._queue.append(
                    self.inline.bot.send_message(
                        self._channel,
                        content,
                        parse_mode='HTML',
                        disable_web_page_preview=True,
                    )
                )
                return

            # Скачиваем и отправляем медиа
            try:
                file_data = await self._client.download_media(media_message, bytes)
                if not file_data:
                    # Если не удалось скачать медиа, отправляем только текст
                    content += "\n\n⚠️ <i>Медиа не удалось загрузить</i>"
                    self._queue.append(
                        self.inline.bot.send_message(
                            self._channel,
                            content,
                            parse_mode='HTML',
                            disable_web_page_preview=True,
                        )
                    )
                    return

                # Проверяем размер файла (Telegram bot API лимит ~50MB)
                if len(file_data) > 45 * 1024 * 1024:  # 45MB для безопасности
                    content += f"\n\n⚠️ <i>Файл слишком большой ({len(file_data)//1024//1024}MB)</i>"
                    self._queue.append(
                        self.inline.bot.send_message(
                            self._channel,
                            content,
                            parse_mode='HTML',
                            disable_web_page_preview=True,
                        )
                    )
                    return
                    
                file = io.BytesIO(file_data)
                file.seek(0)
                
                # Определяем тип медиа и отправляем
                if media_message.photo:
                    file.name = "photo.jpg"
                    self._queue.append(
                        self.inline.bot.send_photo(
                            self._channel, 
                            file, 
                            caption=content, 
                            parse_mode='HTML'
                        )
                    )
                elif media_message.video:
                    file.name = "video.mp4"
                    self._queue.append(
                        self.inline.bot.send_video(
                            self._channel, 
                            file, 
                            caption=content, 
                            parse_mode='HTML'
                        )
                    )
                elif media_message.voice:
                    file.name = "voice.ogg"
                    self._queue.append(
                        self.inline.bot.send_voice(
                            self._channel, 
                            file, 
                            caption=content, 
                            parse_mode='HTML'
                        )
                    )
                elif media_message.audio:
                    file.name = "audio.mp3"
                    self._queue.append(
                        self.inline.bot.send_audio(
                            self._channel, 
                            file, 
                            caption=content, 
                            parse_mode='HTML'
                        )
                    )
                elif getattr(media_message, 'gif', False) or (
                    media_message.document and 
                    getattr(media_message.document, 'mime_type', '').startswith('video/') and
                    'gif' in getattr(media_message.document, 'mime_type', '').lower()
                ):
                    file.name = "animation.gif"
                    self._queue.append(
                        self.inline.bot.send_animation(
                            self._channel, 
                            file, 
                            caption=content, 
                            parse_mode='HTML'
                        )
                    )
                elif media_message.document:
                    file.name = "document"
                    # Получаем оригинальное имя файла
                    for attr in getattr(media_message.document, 'attributes', []):
                        if isinstance(attr, DocumentAttributeFilename):
                            file.name = attr.file_name
                            break
                    
                    self._queue.append(
                        self.inline.bot.send_document(
                            self._channel, 
                            file, 
                            caption=content, 
                            parse_mode='HTML'
                        )
                    )
                else:
                    # Неопознанный тип медиа - отправляем как документ
                    file.name = "media"
                    self._queue.append(
                        self.inline.bot.send_document(
                            self._channel, 
                            file, 
                            caption=content, 
                            parse_mode='HTML'
                        )
                    )
                    
            except Exception as media_error:
                logger.error(f"Ошибка при работе с медиа: {media_error}")
                # Отправляем без медиа
                content += f"\n\n⚠️ <i>Ошибка загрузки медиа: {str(media_error)[:100]}...</i>"
                self._queue.append(
                    self.inline.bot.send_message(
                        self._channel,
                        content,
                        parse_mode='HTML',
                        disable_web_page_preview=True,
                    )
                )
                
        except Exception as e:
            logger.error(f"Ошибка при отправке в канал: {e}")

    @loader.raw_handler(UpdateEditMessage)
    async def edit_handler(self, update: UpdateEditMessage):
        """Обработчик редактирования сообщений в ЛС"""
        if (
            not self.get("state", False)
            or update.message.out
            or not isinstance(update.message.peer_id, PeerUser)  # Только ЛС
            or (self.config["ignore_inline"] and update.message.via_bot_id)
        ):
            return

        try:
            message_id = update.message.id
            cached_message = self._cache.get(message_id)
            
            if not cached_message:
                # Сохраняем новое сообщение в кэш
                self._cache[message_id] = update.message
                return

            sender_id = cached_message.sender_id

            # Проверяем условия для логирования
            should_log = (
                sender_id in self.always_track
                or (
                    self.config["log_edits"]
                    and self._should_capture(sender_id)
                )
            )

            if (should_log and
                hasattr(update.message, 'raw_text') and 
                hasattr(cached_message, 'raw_text') and
                update.message.raw_text != cached_message.raw_text):
                
                try:
                    sender = await self._client.get_entity(sender_id, exp=0)
                    if getattr(sender, 'bot', False):
                        return

                    content = self.strings("edited_pm").format(
                        self._get_pm_link(sender_id),
                        self._format_user_name(sender),
                        cached_message.text or "<без текста>",
                    )
                    
                    await self._send_to_channel(content, cached_message)
                    
                except Exception as entity_error:
                    logger.error(f"Ошибка при получении данных отправителя: {entity_error}")

            # Обновляем кэш
            self._cache[message_id] = update.message
            
        except Exception as e:
            logger.error(f"Ошибка в edit_handler: {e}")

    @loader.raw_handler(UpdateDeleteMessages)
    async def delete_handler(self, update: UpdateDeleteMessages):
        """Обработчик удаления сообщений в ЛС"""
        if not self.get("state", False):
            return

        try:
            for message_id in update.messages:
                cached_message = self._cache.pop(message_id, None)
                if not cached_message:
                    continue

                # Проверяем, что это ЛС
                if not isinstance(cached_message.peer_id, PeerUser):
                    continue

                sender_id = cached_message.sender_id

                # Проверяем условия для логирования
                should_log = (
                    sender_id in self.always_track
                    or (
                        self._should_capture(sender_id)
                        and not (self.config["ignore_inline"] and cached_message.via_bot_id)
                    )
                )

                if not should_log:
                    continue

                try:
                    sender = await self._client.get_entity(sender_id, exp=0)
                    if getattr(sender, 'bot', False):
                        continue

                    content = self.strings("deleted_pm").format(
                        self._get_pm_link(sender_id),
                        self._format_user_name(sender),
                        cached_message.text or "<без текста>",
                    )
                    
                    await self._send_to_channel(content, cached_message)
                    
                except Exception as entity_error:
                    logger.error(f"Ошибка при получении данных отправителя: {entity_error}")
                    
        except Exception as e:
            logger.error(f"Ошибка в delete_handler: {e}")

    @loader.watcher("in")
    async def watcher(self, message: Message):
        """Кэширует входящие сообщения из ЛС для отслеживания"""
        try:
            # Кэшируем только сообщения из ЛС
            if message.is_private and not message.out:
                self._cache[message.id] = message
                
                # Ограничиваем размер кэша
                if len(self._cache) > 10000:
                    # Удаляем старые записи (первые 1000)
                    old_keys = list(self._cache.keys())[:1000]
                    for key in old_keys:
                        self._cache.pop(key, None)
                        
        except Exception as e:
            logger.error(f"Ошибка в watcher: {e}")
