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
    """🔁 Отвечает зеркалами на ключевые слова"""

    strings = {
        "name": "MirrorResponder",
        "mirror_enabled": "<emoji document_id=5909201569898827582>🔔</emoji> <b>Автоответчик зеркала включен</b>",
        "mirror_disabled": "<emoji document_id=5909123362839335003>🔕</emoji> <b>Автоответчик зеркала выключен</b>",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "keywords",
                [
                    "ссылка", "ссылку", "бота", "бот", "удалили", "снесли", "зеркало",
                    "блокнули", "заблокировали", "заблокали", "рабочий", "фанстат",
                    "робот", "ботик", "телелог", "bot", "robot", "фс", "ботом",
                    "скинь", "фанстатом", "фан стат"
                ],
                "Ключевые слова для активации зеркала"
            ),
            loader.ConfigValue(
                "mirror_text",
                "<b>🤖 Актуальные зеркала:</b>\n\n"
                "@telelogrbot\n"
                "@telellogbot\n\n"
                "<i>[Автоматическая отправка].</i>",
                "Текст зеркала, который будет отправляться в ответ"
            ),
            loader.ConfigValue(
                "cooldown", 30, "Задержка между ответами в одном чате (в секундах)"
            ),
            loader.ConfigValue(
                "chats", [], "Список ID чатов, где модуль активен (пусто = везде)"
            ),
        )
        self.last_response = {}

    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        self.is_enabled = self.db.get(self.__class__.__name__, "enabled", True)

    @loader.command(ru_doc="Включить/выключить автоответчик зеркала")
    async def mirr(self, message):
        self.is_enabled = not self.is_enabled
        self.db.set(self.__class__.__name__, "enabled", self.is_enabled)
        await utils.answer(message, self.strings["mirror_enabled"] if self.is_enabled else self.strings["mirror_disabled"])

    def _check_for_keywords(self, text: str) -> bool:
        if not text:
            return False

        text_lower = text.lower()
        keywords = self.config.get("keywords", [])
        if not isinstance(keywords, list):
            return False

        for keyword in keywords:
            pattern = r'(?<!\w)' + re.escape(keyword) + r'(?!\w)'
            if re.search(pattern, text_lower):
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
            chats = self.config.get("chats", [])
            if chats and chat_id not in chats:
                return

            sender = getattr(message, "sender", None)
            if not sender or sender.bot or sender.id == (await message.client.get_me()).id:
                return

            cooldown = self.config.get("cooldown", 30)
            current_time = time.time()
            if chat_id in self.last_response:
                if current_time - self.last_response[chat_id] < cooldown:
                    return

            if self._check_for_keywords(message.text):
                self.last_response[chat_id] = current_time
                mirror_text = self.config.get("mirror_text", "")
                await message.reply(mirror_text)
                self.log(f"[MirrorResponder] Ответ отправлен в чат {chat_id}")
        except Exception as e:
            self.log(f"[MirrorResponder] Ошибка в watcher: {repr(e)}")
