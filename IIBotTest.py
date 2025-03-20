# meta developer: @sunshinelzt

import random
from telethon import types
from .. import loader, utils

@loader.tds
class iibotMod(loader.Module):
    strings = {
        "name": "IIBot",
        "pref": "<b>ii</b> ",
        "need_arg": "{}Нужен аргумент",
        "status": "{}{}",
        "on": "{}Включён",
        "off": "{}Выключен",
    }
    _db_name = "iibot"

    async def client_ready(self, _, db):
        self.db = db

    @staticmethod
    def str2bool(v: str) -> bool:
        return v.lower() in {"yes", "y", "true", "1", "on", "enable", "start", "да"}

    async def iicmd(self, m: types.Message):
        """Переключить режим работы в чате"""
        if not m.chat:
            return

        args = utils.get_args_raw(m)
        chat_id = m.chat.id
        active_chats = set(self.db.get(self._db_name, "chats", []))

        if self.str2bool(args):
            active_chats.add(chat_id)
            await utils.answer(m, self.strings("on").format(self.strings("pref")))
        else:
            active_chats.discard(chat_id)
            await utils.answer(m, self.strings("off").format(self.strings("pref")))

        self.db.set(self._db_name, "chats", list(active_chats))

    async def randomicmd(self, m: types.Message):
        """Установить шанс 1 к N. 0 - всегда обрабатывать."""
        args = utils.get_args_raw(m)
        if args.isdigit():
            self.db.set(self._db_name, "chance", int(args))
            return await utils.answer(m, self.strings("status").format(self.strings("pref"), args))

        return await utils.answer(m, self.strings("need_arg").format(self.strings("pref")))

    async def watcher(self, m: types.Message):
        if not isinstance(m, types.Message) or not m.chat or not m.raw_text.strip():
            return

        chat_id = m.chat.id
        if chat_id not in self.db.get(self._db_name, "chats", []):
            return
        if m.sender_id == (await m.client.get_me()).id:
            return

        # Проверяем вероятность ответа
        chance = self.db.get(self._db_name, "chance", 0)
        if chance != 0 and random.randint(0, chance) != 0:
            return

        # Разбиваем текст на слова и фильтруем короткие и незначимые
        words = [word for word in m.raw_text.split() if len(word) > 1]
        if not words:
            return

        search_word = random.choice(words)

        # Ищем сообщения по слову
        msgs = [
            msg async for msg in m.client.iter_messages(chat_id, search=search_word) if msg.replies and msg.replies.max_id
        ]
        if not msgs:
            return

        base_msg = random.choice(msgs)
        sid, eid = base_msg.id, base_msg.replies.max_id

        # Ищем ответы на это сообщение
        reply_msgs = [
            msg async for msg in m.client.iter_messages(chat_id, ids=list(range(sid + 1, eid + 1)))
            if msg and msg.reply_to and msg.reply_to.reply_to_msg_id == sid
        ]
        if not reply_msgs:
            return

        # Отправляем случайное найденное сообщение без reply
        await m.client.send_message(chat_id, random.choice(reply_msgs).raw_text)
