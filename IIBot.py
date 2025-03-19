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
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            "blacklist", [], "ID пользователей, которым бот не отвечает",
            "generate_text", True, "Генерировать ответ, если ничего не найдено"
        )
        self.active_chats = set()
        self.reply_chance = 0

    async def iicmd(self, m: types.Message):
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
        args = utils.get_args_raw(m)

        if args.isdigit():
            self.reply_chance = int(args)
            return await utils.answer(m, self.strings["chance_set"].format(args))

        return await utils.answer(m, self.strings["need_arg"])

    async def watcher(self, m: types.Message):
        if not isinstance(m, types.Message) or not m.chat:
            return

        chat_id, user_id = m.chat.id, m.sender_id

        if chat_id not in self.active_chats or user_id == (await m.client.get_me()).id or user_id in self.config["blacklist"]:
            return

        if self.reply_chance and random.randint(0, self.reply_chance) != 0:
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
                return await m.reply(random.choice(reply_msgs))

        if self.config["generate_text"]:
            return await m.reply(self.generate_random_response())

    def generate_random_response(self):
        phrases = [
            "Хм... даже не знаю 🤔",
            "А что ты хотел услышать?",
            "Интересный вопрос! А ты как думаешь?",
            "Может быть... а может и нет 😏",
            "Это слишком сложно для меня...",
            "Пожалуй, промолчу 🤐",
            "Я хез, не спрашивай меня такое 😂",
            "Ммм... на это у меня нет ответа...",
            "Я не уверен, но скорее всего... нет 😅",
            "Это слишком философский вопрос для меня 😶"
        ]
        return random.choice(phrases)

    def get_blacklist(self):
        return self.config["blacklist"]

    def add_to_blacklist(self, user_id):
        if user_id not in self.config["blacklist"]:
            self.config["blacklist"].append(user_id)
            return f"Пользователь с ID {user_id} добавлен в чёрный список."
        return "Этот пользователь уже в чёрном списке."

    def remove_from_blacklist(self, user_id):
        if user_id in self.config["blacklist"]:
            self.config["blacklist"].remove(user_id)
            return f"Пользователь с ID {user_id} удалён из чёрного списка."
        return "Этот пользователь не в чёрном списке."
