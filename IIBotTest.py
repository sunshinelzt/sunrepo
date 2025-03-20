# meta developer: @sunshinelzt

import random
from telethon import types
from .. import loader, utils

@loader.tds
class iibotMod(loader.Module):
    strings = {
        "name": "iibot",
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
        """Переключить режим дурачка в чате"""
        if not m.chat:
            return

        args = utils.get_args_raw(m)
        chat_id = m.chat.id
        chats = set(self.db.get(self._db_name, "chats", []))

        if self.str2bool(args):
            chats.add(chat_id)
            await utils.answer(m, self.strings("on").format(self.strings("pref")))
        else:
            chats.discard(chat_id)
            await utils.answer(m, self.strings("off").format(self.strings("pref")))

        self.db.set(self._db_name, "chats", list(chats))

    async def randomicmd(self, m: types.Message):
        """Установить шанс 1 к N.\n0 - всегда обрабатывать."""
        args = utils.get_args_raw(m)
        if args.isdigit():
            self.db.set(self._db_name, "chance", int(args))
            return await utils.answer(m, self.strings("status").format(self.strings("pref"), args))

        return await utils.answer(m, self.strings("need_arg").format(self.strings("pref")))

    async def watcher(self, m: types.Message):
        if not isinstance(m, types.Message) or not m.chat:
            return

        chat_id = m.chat.id
        if chat_id not in self.db.get(self._db_name, "chats", []):
            return
        if m.sender_id == (await m.client.get_me()).id:
            return

        ch = self.db.get(self._db_name, "chance", 0)
        if ch != 0 and random.randint(0, ch) != 0:
            return

        words = [
            word for word in m.raw_text.split() if len(word) >= 3
        ]
        if not words:
            return

        search_word = random.choice(words)
        msgs = [
            x async for x in m.client.iter_messages(chat_id, search=search_word) if x.replies and x.replies.max_id
        ]
        if not msgs:
            return

        replier = random.choice(msgs)
        sid, eid = replier.id, replier.replies.max_id
        reply_msgs = [
            x async for x in m.client.iter_messages(chat_id, ids=list(range(sid + 1, eid + 1)))
            if x and x.reply_to and x.reply_to.reply_to_msg_id == sid
        ]
        if not reply_msgs:
            return
        
        # Бот обрабатывает сообщение, но не отвечает
        _ = random.choice(reply_msgs)  # Просто используем, чтобы не отвечать
