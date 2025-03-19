# meta developer: @sunshinelzt

import random
from telethon import types
from .. import loader, utils

@loader.tds
class iibotMod(loader.Module):
    """Модуль для включения режима дурачка в чате"""
    
    strings = {
        "name": "iibot",
        "pref": "<b>ii</b> ",
        "need_arg": "{}Нужен аргумент",
        "status": "{}{}",
        "on": "{}Включён",
        "off": "{}Выключен",
        "no_track_users_desc": "Список пользователей, которых бот будет игнорировать",
    }
    _db_name = "iibot"

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "no_track_users",
                [],
                doc=lambda: self.strings("no_track_users_desc"),
                validator=loader.validators.Series(
                    loader.validators.Union(loader.validators.String(), loader.validators.Integer())
                ),
            ),
            loader.ConfigValue(
                "chance",
                0,
                "Шанс ответа (0 - всегда отвечает, N - 1 к N)"
            ),
        )

    @property
    def blacklist(self) -> set:
        """Возвращает черный список пользователей в виде множества для быстрой проверки"""
        return set(map(str, self.config["no_track_users"]))

    @property
    def chance(self) -> int:
        """Возвращает шанс ответа"""
        return self.config["chance"]

    async def client_ready(self, _, db):
        self.db = db

    async def iicmd(self, m: types.Message):
        """Переключить режим дурачка в чате"""
        args = utils.get_args_raw(m)
        if not m.chat:
            return

        chat = m.chat.id
        chats = set(self.db.get(self._db_name, "chats", []))

        if args.lower() in ("on", "включить", "yes", "да", "1"):
            chats.add(chat)
            self.db.set(self._db_name, "chats", list(chats))
            return await utils.answer(m, self.strings["on"].format(self.strings["pref"]))

        chats.discard(chat)
        self.db.set(self._db_name, "chats", list(chats))
        return await utils.answer(m, self.strings["off"].format(self.strings["pref"]))

    async def randomicmd(self, m: types.Message):
        """Установить шанс 1 к N. 0 - всегда отвечает"""
        args = utils.get_args_raw(m)
        if args.isdigit():
            self.config["chance"] = int(args)
            return await utils.answer(m, self.strings["status"].format(self.strings["pref"], args))
        return await utils.answer(m, self.strings["need_arg"].format(self.strings["pref"]))

    async def watcher(self, m: types.Message):
        if not isinstance(m, types.Message) or not m.chat:
            return

        user_id = str(m.sender_id)
        chat_id = m.chat.id

        if user_id in self.blacklist:
            return

        if chat_id not in self.db.get(self._db_name, "chats", []):
            return

        if self.chance and random.randint(0, self.chance) != 0:
            return

        text = m.raw_text
        if not text:
            return

        words = [w for w in text.split() if len(w) >= 3]
        if not words:
            return

        keyword = random.choice(words)
        messages = [msg async for msg in m.client.iter_messages(chat_id, search=keyword) if msg.replies and msg.replies.max_id]

        if not messages:
            return

        replier = random.choice(messages)
        sid, eid = replier.id, replier.replies.max_id

        replies = [
            msg async for msg in m.client.iter_messages(chat_id, ids=list(range(sid + 1, eid + 1)))
            if msg and msg.reply_to and msg.reply_to.reply_to_msg_id == sid
        ]

        if replies:
            await m.reply(random.choice(replies))
