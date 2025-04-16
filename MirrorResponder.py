# ---------------------------------------------------------------------------------
# | Название: MirrorResponder                                                     |
# | Функция: Автоматическая отправка зеркального сообщения при ключевых словах    |
# | Префикс: .mirr                                                                |
# ---------------------------------------------------------------------------------
# | Создан для Heroku userbot                                                      |
# | Категория: funstat                                                            |
# ---------------------------------------------------------------------------------

# meta developer: @sunshinelzt

import random
import re
import time
from .. import loader, utils

@loader.tds
class MirrorResponderMod(loader.Module):
    """Зеркальный автоответчик под фанстат"""

    strings = {
        "name": "MirrorResponder",
        "mirror_enabled": "<emoji document_id=5909201569898827582>🔔</emoji> <b>Автоответчик включен</b>",
        "mirror_disabled": "<emoji document_id=5909123362839335003>🔕</emoji> <b>Автоответчик выключен</b>",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "keywords",
                [
                    "ссылка", "ссылку", "бота", "бот", "удалили", "снесли",
                    "зеркало", "блокнули", "заблокировали", "заблокали",
                    "рабочий", "фанстат", "робот", "ботик", "телелог",
                    "bot", "robot", "фс", "ботом", "скинь", "фанстатом", "фан стат"
                ],
                "Ключевые слова для активации зеркала",
            ),
            loader.ConfigValue(
                "mirror_text",
                "<i>🤖 Авто отправка зеркала | Auto Mirror Dispatch</i>\n\n"
                "@telelogrbot\n@telellogbot\n\n"
                "Фaнcтaт всегда жив!"
                "Ответ на сообщение (можно использовать HTML)",
            ),
            loader.ConfigValue(
                "cooldown", 30, "Кулдаун между ответами в одном чате (в секундах)"
            ),
            loader.ConfigValue(
                "chats", [], "Список chat_id, в которых работает (пусто — везде)"
            ),
        )
        self.last_response = {}

    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        self.is_enabled = self.db.get(self.__class__.__name__, "enabled", True)

    @loader.command(ru_doc="Включить/выключить автоответчик зеркала")
    async def mirr(self, message):
        """Включить/выключить автоответчик"""
        self.is_enabled = not self.is_enabled
        self.db.set(self.__class__.__name__, "enabled", self.is_enabled)

        await utils.answer(
            message,
            self.strings["mirror_enabled"] if self.is_enabled else self.strings["mirror_disabled"]
        )

    def _has_keywords(self, text: str) -> bool:
        if not text:
            return False

        text = text.lower()
        for kw in self.config["keywords"]:
            if re.search(rf"\b{re.escape(kw)}\b", text):
                return True
        return False

    @loader.watcher()
    async def watcher(self, message):
        if not self.is_enabled:
            return

        if not message or not getattr(message, "text", None):
            return

        try:
            chat_id = utils.get_chat_id(message)
            allowed_chats = self.config["chats"]
            if allowed_chats and chat_id not in allowed_chats:
                return

            sender = getattr(message, "sender", None)
            if not sender or sender.bot:
                return

            if sender.id == (await message.client.get_me()).id:
                return

            now = time.time()
            if chat_id in self.last_response:
                if now - self.last_response[chat_id] < self.config["cooldown"]:
                    return

            if self._has_keywords(message.text):
                self.last_response[chat_id] = now
                await message.reply(self.config["mirror_text"])
                self.logger.debug(f"[MirrorResponder] Ответ отправлен в чат {chat_id}")

        except Exception as e:
            self.logger.error(f"[MirrorResponder] Ошибка в watcher: {repr(e)}")
