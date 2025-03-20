# meta developer: @sunshinelzt

import random
from telethon import types
from .. import loader, utils

@loader.tds
class iibotMod(loader.Module):
    """Бот случайно выбирает сообщения из чата и отправляет их без reply."""
    
    strings = {
        "name": "IIBotTest",
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
    def str2bool(value: str) -> bool:
        return value.lower() in {"yes", "y", "true", "1", "on", "enable", "start", "да"}

    async def iicmd(self, message: types.Message):
        """Переключает режим работы в чате"""
        if not message.chat:
            return

        chat_id = message.chat.id
        args = utils.get_args_raw(message)
        active_chats = set(self.db.get(self._db_name, "chats", []))

        if self.str2bool(args):
            active_chats.add(chat_id)
            await utils.answer(message, self.strings("on").format(self.strings("pref")))
        else:
            active_chats.discard(chat_id)
            await utils.answer(message, self.strings("off").format(self.strings("pref")))

        self.db.set(self._db_name, "chats", list(active_chats))

    async def randomicmd(self, message: types.Message):
        """Устанавливает шанс 1 к N. 0 - всегда писать."""
        args = utils.get_args_raw(message)
        if args.isdigit():
            self.db.set(self._db_name, "chance", int(args))
            return await utils.answer(message, self.strings("status").format(self.strings("pref"), args))

        return await utils.answer(message, self.strings("need_arg").format(self.strings("pref")))

    async def watcher(self, message: types.Message):
        """Обрабатывает все сообщения в чате и пишет случайное сообщение, но без reply."""
        if not isinstance(message, types.Message) or not message.chat or not message.raw_text.strip():
            return

        chat_id = message.chat.id
        if chat_id not in self.db.get(self._db_name, "chats", []):
            return
        if message.sender_id == (await message.client.get_me()).id:
            return

        # Проверка шанса ответа
        chance = self.db.get(self._db_name, "chance", 0)
        if chance != 0 and random.randint(0, chance) != 0:
            return

        # Разбиваем текст на слова и убираем слишком короткие
        words = [word for word in message.raw_text.split() if len(word) > 1]
        if not words:
            return

        search_word = random.choice(words)

        # Ищем сообщения с этим словом
        messages = [
            msg async for msg in message.client.iter_messages(chat_id, search=search_word) if msg.replies and msg.replies.max_id
        ]
        if not messages:
            return

        base_message = random.choice(messages)
        start_id, end_id = base_message.id, base_message.replies.max_id

        # Ищем ответы на это сообщение
        reply_messages = [
            msg async for msg in message.client.iter_messages(chat_id, ids=list(range(start_id + 1, end_id + 1)))
            if msg and msg.reply_to and msg.reply_to.reply_to_msg_id == start_id
        ]
        if not reply_messages:
            return

        # Отправляем случайный текст из найденных сообщений (без reply)
        await message.client.send_message(chat_id, random.choice(reply_messages).raw_text)
