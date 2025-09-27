__version__ = (1, 1, 0)

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
    PeerChat,
    UpdateDeleteChannelMessages,
    UpdateDeleteMessages,
    UpdateEditChannelMessage,
    UpdateEditMessage,
)
from telethon.utils import get_display_name

from .. import loader, utils

logger = logging.getLogger(__name__)


@loader.tds
class NekoSpy(loader.Module):
    """Отправляет удаленные и/или отредактированные сообщения от выбранных пользователей"""

    rei = "<emoji document_id=5409143295039252230>👩‍🎤</emoji>"
    groups = "<emoji document_id=6037355667365300960>👥</emoji>"
    pm = "<emoji document_id=6048540195995782913>👤</emoji>"

    strings = {
        "name": "NekoSpy",
        "state": f"{rei} <b>Режим слежения теперь {{}}</b>",
        "spybl": f"{rei} <b>Текущий чат добавлен в черный список для слежения</b>",
        "spybl_removed": f"{rei} <b>Текущий чат удален из черного списка для слежения</b>",
        "spybl_clear": f"{rei} <b>Черный список для слежения очищен</b>",
        "spywl": f"{rei} <b>Текущий чат добавлен в белый список для слежения</b>",
        "spywl_removed": f"{rei} <b>Текущий чат удален из белого списка для слежения</b>",
        "spywl_clear": f"{rei} <b>Белый список для слежения очищен</b>",
        "whitelist": f"\n{rei} <b>Слежу только за сообщениями от пользователей / групп:</b>\n{{}}",
        "always_track": f"\n{rei} <b>Всегда слежу за сообщениями от пользователей / групп:</b>\n{{}}",
        "blacklist": f"\n{rei} <b>Игнорирую сообщения от пользователей / групп:</b>\n{{}}",
        "chat": f"{groups} <b>Слежу за сообщениями в группах</b>\n",
        "pm": f"{pm} <b>Слежу за сообщениями в личных сообщениях</b>\n",
        "mode_off": f"{pm} <b>Не отслеживаю сообщения </b><code>{{}}spymode</code>\n",
        "deleted_pm": (
            '🗑 <b><a href="{}">{}</a> удалил <a href="{message_url}">сообщение</a> в'
            " личке. Содержимое:</b>\n{}"
        ),
        "deleted_chat": (
            '🗑 <b><a href="{message_url}">Сообщение</a> в чате <a href="{}">{}</a> от'
            ' <a href="{}">{}</a> было удалено. Содержимое:</b>\n{}'
        ),
        "edited_pm": (
            '🔏 <b><a href="{}">{}</a> отредактировал <a'
            ' href="{message_url}">сообщение</a> в личке. Старое содержимое:</b>\n{}'
        ),
        "edited_chat": (
            '🔏 <b><a href="{message_url}">Сообщение</a> в чате <a href="{}">{}</a> от'
            ' <a href="{}">{}</a> было отредактировано. Старое содержимое:</b>\n{}'
        ),
        "on": "включен",
        "off": "выключен",
        "cfg_enable_pm": "Включить режим шпиона в личных сообщениях",
        "cfg_enable_groups": "Включить режим шпиона в группах",
        "cfg_whitelist": "Список чатов, от которых нужно сохранять сообщения",
        "cfg_blacklist": "Список чатов, от которых нужно игнорировать сообщения",
        "cfg_always_track": (
            "Список чатов, от которых всегда следует отслеживать сообщения, "
            "несмотря ни на что"
        ),
        "cfg_log_edits": "Сохранять отредактированные сообщения",
        "cfg_ignore_inline": "Игнорировать сообщения из инлайн-режима",
        "cfg_fw_protect": "Защита от флудвейтов при пересылке (секунды)",
        "no_channel_error": "❌ <b>Не удалось создать канал шпиона. Проверьте права бота.</b>",
    }

    def __init__(self):
        self._tl_channel = None
        self._me = None
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "enable_pm",
                True,
                lambda: self.strings("cfg_enable_pm"),
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "enable_groups",
                False,
                lambda: self.strings("cfg_enable_groups"),
                validator=loader.validators.Boolean(),
            ),
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
                3.0,
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
        system_ids = [777000, self._client.tg_id, self._tl_channel]
        if hasattr(self, 'inline') and hasattr(self.inline, 'bot_id'):
            system_ids.append(self.inline.bot_id)
        
        return list(map(self._int, self.config["blacklist"] + [x for x in system_ids if x]))

    @blacklist.setter
    def blacklist(self, value: list):
        """Устанавливает черный список, исключая системные ID"""
        system_ids = {777000, self._client.tg_id, self._tl_channel}
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
        self._me = await self._client.get_me()
        try:
            channel, _ = await utils.asset_channel(
                self._client,
                "heroku-nekospy",
                "Удаленные и отредактированные сообщения появляются здесь",
                silent=True,
                invite_bot=True,
                avatar="https://pm1.narvii.com/6733/0e0380ca5cd7595de53f48c0ce541d3e2f2effc4v2_hq.jpg",
                _folder="heroku",
            )
            
            self._channel = int(f"-100{channel.id}")
            self._tl_channel = channel.id
        except Exception as e:
            logger.error(f"Не удалось создать канал: {e}")

    @loader.command(ru_doc="Переключить режим слежения")
    async def spymode(self, message: Message):
        """Переключить режим слежения"""
        await utils.answer(
            message,
            self.strings("state").format(
                self.strings("off" if self.get("state", False) else "on")
            ),
        )
        self.set("state", not self.get("state", False))

    @loader.command(ru_doc="Добавить / удалить чат из черного списка")
    async def spybl(self, message: Message):
        """Добавить / удалить чат из черного списка"""
        chat = utils.get_chat_id(message)
        current_blacklist = self.config["blacklist"]
        
        if chat in current_blacklist:
            self.config["blacklist"] = [x for x in current_blacklist if x != chat]
            await utils.answer(message, self.strings("spybl_removed"))
        else:
            self.config["blacklist"] = current_blacklist + [chat]
            await utils.answer(message, self.strings("spybl"))

    @loader.command(ru_doc="Очистить черный список")
    async def spyblclear(self, message: Message):
        """Очистить черный список"""
        self.config["blacklist"] = []
        await utils.answer(message, self.strings("spybl_clear"))

    @loader.command(ru_doc="Добавить / удалить чат из белого списка")
    async def spywl(self, message: Message):
        """Добавить / удалить чат из белого списка"""
        chat = utils.get_chat_id(message)
        current_whitelist = self.config["whitelist"]
        
        if chat in current_whitelist:
            self.config["whitelist"] = [x for x in current_whitelist if x != chat]
            await utils.answer(message, self.strings("spywl_removed"))
        else:
            self.config["whitelist"] = current_whitelist + [chat]
            await utils.answer(message, self.strings("spywl"))

    @loader.command(ru_doc="Очистить белый список")
    async def spywlclear(self, message: Message):
        """Очистить белый список"""
        self.config["whitelist"] = []
        await utils.answer(message, self.strings("spywl_clear"))

    async def _get_entities_list(self, entities: list) -> str:
        """Получает отформатированный список сущностей"""
        result = []
        for entity_id in entities:
            try:
                entity = await self._client.get_entity(entity_id, exp=0)
                url = utils.get_entity_url(entity)
                name = get_display_name(entity)
                if hasattr(utils, 'escape_html'):
                    name = utils.escape_html(name)
                result.append(
                    f"\u0020\u2800\u0020\u2800<emoji document_id=4971987363145188045>▫️</emoji> "
                    f'<b><a href="{url}">{name}</a></b>'
                )
            except Exception as e:
                logger.warning(f"Не удалось получить информацию о сущности {entity_id}: {e}")
                result.append(
                    f"\u0020\u2800\u0020\u2800<emoji document_id=4971987363145188045>▫️</emoji> "
                    f"<b>ID: {entity_id}</b>"
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

        info = ""

        if self.config["enable_groups"]:
            info += self.strings("chat")

        if self.config["enable_pm"]:
            info += self.strings("pm")

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

    def _should_capture(self, user_id: int, chat_id: int) -> bool:
        """Проверяет, нужно ли захватывать сообщение"""
        return (
            chat_id not in self.blacklist
            and user_id not in self.blacklist
            and (
                not self.whitelist
                or chat_id in self.whitelist
                or user_id in self.whitelist
            )
        )

    async def _send_message_to_channel(self, content: str, media_message: Message = None):
        """Отправляет сообщение в канал слежения"""
        if not self._channel or not hasattr(self, 'inline'):
            return
            
        try:
            content = self.inline.sanitise_text(content)

            if not media_message or not any([
                media_message.photo, media_message.video, 
                media_message.voice, media_message.document
            ]):
                self._queue.append(
                    self.inline.bot.send_message(
                        self._channel,
                        content,
                        disable_web_page_preview=True,
                    )
                )
                return

            if media_message.sticker:
                self._queue.append(
                    self.inline.bot.send_message(
                        self._channel,
                        content + "\n\n&lt;стикер&gt;",
                        disable_web_page_preview=True,
                    )
                )
                return

            # Скачиваем и отправляем медиа
            file_data = await self._client.download_media(media_message, bytes)
            file = io.BytesIO(file_data)
            
            args = (self._channel, file)
            kwargs = {"caption": content}
            
            if media_message.photo:
                file.name = "photo.jpg"
                self._queue.append(self.inline.bot.send_photo(*args, **kwargs))
            elif media_message.video:
                file.name = "video.mp4"
                self._queue.append(self.inline.bot.send_video(*args, **kwargs))
            elif media_message.voice:
                file.name = "audio.ogg"
                self._queue.append(self.inline.bot.send_voice(*args, **kwargs))
            elif media_message.document:
                file.name = "document"
                # Получаем имя файла из атрибутов
                for attr in getattr(media_message.document, 'attributes', []):
                    if isinstance(attr, DocumentAttributeFilename):
                        file.name = attr.file_name
                        break
                self._queue.append(self.inline.bot.send_document(*args, **kwargs))
                
        except Exception as e:
            logger.error(f"Ошибка при отправке в канал: {e}")

    def _get_message_key(self, message: Message) -> str:
        """Получает ключ для кэширования сообщения"""
        if message.is_private or isinstance(message.peer_id, PeerChat):
            return str(message.id)
        return f"{utils.get_chat_id(message)}/{message.id}"

    def _get_message_url(self, message: Message) -> str:
        """Получает URL сообщения"""
        if hasattr(utils, 'get_message_link'):
            return utils.get_message_link(message)
        
        if hasattr(message, 'chat') and message.chat:
            return f"tg://c/{message.chat.id}/{message.id}"
        return f"tg://c/{getattr(message.peer_id, 'chat_id', message.id)}/{message.id}"

    def _format_user_name(self, user) -> str:
        """Форматирует имя пользователя с экранированием HTML"""
        name = get_display_name(user)
        if hasattr(utils, 'escape_html'):
            return utils.escape_html(name)
        return name.replace('<', '&lt;').replace('>', '&gt;')

    @loader.raw_handler(UpdateEditChannelMessage)
    async def channel_edit_handler(self, update: UpdateEditChannelMessage):
        """Обработчик редактирования сообщений в каналах"""
        if (
            not self.get("state", False)
            or update.message.out
            or (self.config["ignore_inline"] and update.message.via_bot_id)
        ):
            return

        try:
            key = f"{utils.get_chat_id(update.message)}/{update.message.id}"
            cached_message = self._cache.get(key)
            
            if not cached_message:
                self._cache[key] = update.message
                return

            # Проверяем условия для логирования
            should_log = (
                utils.get_chat_id(update.message) in self.always_track
                or cached_message.sender_id in self.always_track
                or (
                    self.config["log_edits"]
                    and self.config["enable_groups"]
                    and utils.get_chat_id(update.message) not in self.blacklist
                    and (
                        not self.whitelist
                        or utils.get_chat_id(update.message) in self.whitelist
                    )
                )
            )

            if (should_log and 
                not cached_message.sender.bot and 
                hasattr(update.message, 'raw_text') and 
                hasattr(cached_message, 'raw_text') and
                update.message.raw_text != cached_message.raw_text):
                
                message_url = self._get_message_url(cached_message)
                content = self.strings("edited_chat").format(
                    utils.get_entity_url(cached_message.chat),
                    self._format_user_name(cached_message.chat),
                    utils.get_entity_url(cached_message.sender),
                    self._format_user_name(cached_message.sender),
                    cached_message.text or "<без текста>",
                    message_url=message_url,
                )
                
                await self._send_message_to_channel(content, cached_message)

            self._cache[key] = update.message
        except Exception as e:
            logger.error(f"Ошибка в channel_edit_handler: {e}")

    @loader.raw_handler(UpdateEditMessage)
    async def pm_edit_handler(self, update: UpdateEditMessage):
        """Обработчик редактирования сообщений в ЛС"""
        if (
            not self.get("state", False)
            or update.message.out
            or (self.config["ignore_inline"] and update.message.via_bot_id)
        ):
            return

        try:
            key = str(update.message.id)
            cached_message = self._cache.get(key)
            
            if not cached_message:
                self._cache[key] = update.message
                return

            # Проверяем условия для логирования
            is_pm = not isinstance(cached_message.peer_id, PeerChat)
            is_group = isinstance(cached_message.peer_id, PeerChat)
            
            should_log = (
                cached_message.sender_id in self.always_track
                or utils.get_chat_id(cached_message) in self.always_track
                or (
                    self.config["log_edits"]
                    and self._should_capture(cached_message.sender_id, utils.get_chat_id(cached_message))
                    and ((self.config["enable_pm"] and is_pm) or (self.config["enable_groups"] and is_group))
                )
            )

            if (should_log and
                hasattr(update.message, 'raw_text') and 
                hasattr(cached_message, 'raw_text') and
                update.message.raw_text != cached_message.raw_text):
                
                sender = await self._client.get_entity(cached_message.sender_id, exp=0)
                if sender.bot:
                    return

                message_url = self._get_message_url(cached_message)
                
                if is_group:
                    chat = await self._client.get_entity(cached_message.peer_id.chat_id, exp=0)
                    content = self.strings("edited_chat").format(
                        utils.get_entity_url(chat),
                        self._format_user_name(chat),
                        utils.get_entity_url(sender),
                        self._format_user_name(sender),
                        cached_message.text or "<без текста>",
                        message_url=message_url,
                    )
                else:
                    content = self.strings("edited_pm").format(
                        utils.get_entity_url(sender),
                        self._format_user_name(sender),
                        cached_message.text or "<без текста>",
                        message_url=message_url,
                    )
                
                await self._send_message_to_channel(content, cached_message)

            self._cache[key] = update.message
        except Exception as e:
            logger.error(f"Ошибка в pm_edit_handler: {e}")

    @loader.raw_handler(UpdateDeleteMessages)
    async def pm_delete_handler(self, update: UpdateDeleteMessages):
        """Обработчик удаления сообщений в ЛС"""
        if not self.get("state", False):
            return

        try:
            for message_id in update.messages:
                cached_message = self._cache.pop(str(message_id), None)
                if not cached_message:
                    continue

                # Проверяем условия для логирования
                is_pm = not isinstance(cached_message.peer_id, PeerChat)
                is_group = isinstance(cached_message.peer_id, PeerChat)
                
                should_log = (
                    cached_message.sender_id in self.always_track
                    or utils.get_chat_id(cached_message) in self.always_track
                    or (
                        self._should_capture(cached_message.sender_id, utils.get_chat_id(cached_message))
                        and not (self.config["ignore_inline"] and cached_message.via_bot_id)
                        and ((self.config["enable_pm"] and is_pm) or (self.config["enable_groups"] and is_group))
                    )
                )

                if not should_log:
                    continue

                sender = await self._client.get_entity(cached_message.sender_id, exp=0)
                if sender.bot:
                    continue

                message_url = self._get_message_url(cached_message)
                
                if is_group:
                    chat = await self._client.get_entity(cached_message.peer_id.chat_id, exp=0)
                    content = self.strings("deleted_chat").format(
                        utils.get_entity_url(chat),
                        self._format_user_name(chat),
                        utils.get_entity_url(sender),
                        self._format_user_name(sender),
                        cached_message.text or "<без текста>",
                        message_url=message_url,
                    )
                else:
                    content = self.strings("deleted_pm").format(
                        utils.get_entity_url(sender),
                        self._format_user_name(sender),
                        cached_message.text or "<без текста>",
                        message_url=message_url,
                    )
                
                await self._send_message_to_channel(content, cached_message)
                
        except Exception as e:
            logger.error(f"Ошибка в pm_delete_handler: {e}")

    @loader.raw_handler(UpdateDeleteChannelMessages)
    async def channel_delete_handler(self, update: UpdateDeleteChannelMessages):
        """Обработчик удаления сообщений в каналах"""
        if not self.get("state", False):
            return

        try:
            for message_id in update.messages:
                key = f"{update.channel_id}/{message_id}"
                cached_message = self._cache.pop(key, None)
                if not cached_message:
                    continue

                should_log = (
                    cached_message.sender_id in self.always_track
                    or utils.get_chat_id(cached_message) in self.always_track
                    or (
                        self.config["enable_groups"]
                        and self._should_capture(cached_message.sender_id, utils.get_chat_id(cached_message))
                        and not (self.config["ignore_inline"] and cached_message.via_bot_id)
                        and not cached_message.sender.bot
                    )
                )

                if should_log:
                    message_url = self._get_message_url(cached_message)
                    content = self.strings("deleted_chat").format(
                        utils.get_entity_url(cached_message.chat),
                        self._format_user_name(cached_message.chat),
                        utils.get_entity_url(cached_message.sender),
                        self._format_user_name(cached_message.sender),
                        cached_message.text or "<без текста>",
                        message_url=message_url,
                    )
                    
                    await self._send_message_to_channel(content, cached_message)
                    
        except Exception as e:
            logger.error(f"Ошибка в channel_delete_handler: {e}")

    @loader.watcher("in")
    async def watcher(self, message: Message):
        """Кэширует входящие сообщения для отслеживания"""
        try:
            with contextlib.suppress(AttributeError):
                key = self._get_message_key(message)
                self._cache[key] = message
        except Exception as e:
            logger.error(f"Ошибка в watcher: {e}")
