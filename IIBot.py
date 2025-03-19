# meta developer: @sunshinelzt

import random
from telethon import types
from .. import loader, utils


@loader.tds
class iibotMod(loader.Module):
    """Бот-дурачок, который отвечает на сообщения в чате"""

    strings = {
        "name": "IIBot",
        "enabled": "✅ Режим дурака включён!",
        "disabled": "❌ Режим дурака отключён.",
        "chance_set": "🎲 Шанс ответа установлен на 1 к {}",
        "need_arg": "⚠ Нужно указать значение!",
        "blacklist_added": "🚫 Пользователь с ID {user_id} добавлен в черный список.",
        "blacklist_removed": "✅ Пользователь с ID {user_id} удалён из черного списка.",
        "blacklist_exists": "⚠ Этот пользователь уже в черном списке.",
        "blacklist_not_exists": "⚠ Этот пользователь не в черном списке.",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            "blacklist", [], "ID пользователей, которым бот не отвечает",
            "reply_chance", 1, "Шанс ответа (1 к N, где N — число)"
        )
        self.active_chats = set()

    async def iicmd(self, m: types.Message):
        """Включить/выключить бота в чате: /ii on или /ii off"""
        if not m.chat:
            return

        chat_id = m.chat.id
        args = utils.get_args_raw(m).lower()

        if args in {"on", "вкл", "enable"}:
            self.active_chats.add(chat_id)
            return await utils.answer(m, self.strings["enabled"])

        if args in {"off", "выкл", "disable"}:
            self.active_chats.discard(chat_id)
            return await utils.answer(m, self.strings["disabled"])

        return await utils.answer(m, self.strings["need_arg"])

    async def randomicmd(self, m: types.Message):
        """Установить шанс ответа: /randomi N (0 - всегда, N - 1 к N)"""
        args = utils.get_args_raw(m)

        if args.isdigit():
            self.config["reply_chance"] = int(args)
            return await utils.answer(m, self.strings["chance_set"].format(args))

        return await utils.answer(m, self.strings["need_arg"])

    async def watcher(self, m: types.Message):
        """Основной обработчик сообщений"""
        if not isinstance(m, types.Message) or not m.chat:
            return

        chat_id, user_id = m.chat.id, m.sender_id

        if chat_id not in self.active_chats or user_id == (await m.client.get_me()).id or user_id in self.config["blacklist"]:
            return

        if self.config["reply_chance"] and random.randint(1, self.config["reply_chance"]) != 1:
            return

        words = [word for word in m.raw_text.split() if len(word) >= 3]
        if not words:
            return

        search_word = random.choice(words)
        messages = [
            msg async for msg in m.client.iter_messages(chat_id, search=search_word)
            if msg.replies and msg.replies.max_id
        ]

        if messages:
            base_message = random.choice(messages)
            reply_msgs = [
                msg async for msg in m.client.iter_messages(
                    chat_id,
                    ids=list(range(base_message.id + 1, base_message.replies.max_id + 1))
                )
                if msg.reply_to and msg.reply_to.reply_to_msg_id == base_message.id
            ]
            if reply_msgs:
                return await m.reply(random.choice(reply_msgs).text)

    def get_blacklist(self):
        """Получить черный список"""
        return self.config["blacklist"]

    def add_to_blacklist(self, user_id):
        """Добавить пользователя в черный список"""
        if user_id not in self.config["blacklist"]:
            self.config["blacklist"].append(user_id)
            return self.strings["blacklist_added"].format(user_id=user_id)
        return self.strings["blacklist_exists"]

    def remove_from_blacklist(self, user_id):
        """Удалить пользователя из черного списка"""
        if user_id in self.config["blacklist"]:
            self.config["blacklist"].remove(user_id)
            return self.strings["blacklist_removed"].format(user_id=user_id)
        return self.strings["blacklist_not_exists"]
