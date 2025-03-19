# meta developer: @sunshinelzt

import random
import asyncio
from typing import List, Set, Dict, Any, Optional
from telethon import types, events
from .. import loader, utils


@loader.tds
class EnhancedIIBotMod(loader.Module):
    """
    Умный чат-бот, который отвечает на сообщения с учетом контекста
    Возможности:
    - Настраиваемый шанс ответа
    - Черный список пользователей
    - Настраиваемые шаблоны ответов
    - Память чата и обучение
    - Фильтрация сообщений
    """

    strings = {
        "name": "IIBot",
        "enabled": "✅ Режим дурака включен в этом чате!",
        "disabled": "❌ Режим дурака отключен в этом чате.",
        "chance_set": "🎲 Шанс ответа установлен на 1 к {}",
        "need_arg": "⚠ Необходимо указать значение!",
        "blacklist_added": "🚫 Пользователь {} добавлен в черный список",
        "blacklist_removed": "✅ Пользователь {} удален из черного списка",
        "blacklist_list": "📋 Пользователи в черном списке:\n{}",
        "templates_updated": "📝 Шаблоны ответов обновлены",
        "templates_list": "📋 Текущие шаблоны ответов:\n{}",
        "invalid_number": "⚠ Пожалуйста, укажите корректное число",
        "memory_cleared": "🧹 Память чата очищена для этого чата",
        "status": "📊 Статус:\n• Активен: {}\n• Шанс ответа: 1 к {}\n• Размер памяти: {}\n• Пользователей в ЧС: {}\n• Генерировать текст: {}",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            "blacklist", [], "ID пользователей, которым бот не отвечает",
            "generate_text", True, "Генерировать ответ, если подходящий ответ не найден",
            "max_memory_per_chat", 500, "Максимальное количество сообщений для запоминания на чат",
            "min_word_length", 3, "Минимальная длина слова для поиска",
            "max_search_results", 50, "Максимальное количество сообщений для поиска",
            "response_templates", [
                "Хм... даже не знаю 🤔",
                "А что ты хотел услышать?",
                "Интересный вопрос! А ты как думаешь?",
                "Может быть... а может и нет 😏",
                "Это слишком сложно для меня...",
                "Пожалуй, промолчу 🤐",
                "Я хз, не спрашивай меня такое 😂",
                "Ммм... на это у меня нет ответа...",
                "Я не уверен, но скорее всего... нет 😅",
                "Это слишком философский вопрос для меня 😶"
            ], "Шаблоны случайных ответов, когда подходящий ответ не найден"
        )
        self.active_chats: Set[int] = set()
        self.reply_chance: int = 5  # По умолчанию шанс 1 к 5
        self.chat_memory: Dict[int, List[Dict[str, Any]]] = {}
        self._me = None
        self._db = None

    async def client_ready(self, client, db):
        """Вызывается, когда клиент готов к использованию"""
        self._db = db
        self._me = await client.get_me()
        
        # Загрузка сохраненных данных
        self._load_data()

    def _load_data(self):
        """Загрузка сохраненных данных из базы данных"""
        data = self._db.get(self.strings["name"], "data", {})
        self.active_chats = set(data.get("active_chats", []))
        self.reply_chance = data.get("reply_chance", 5)
    
    def _save_data(self):
        """Сохранение данных в базу данных"""
        self._db.set(self.strings["name"], "data", {
            "active_chats": list(self.active_chats),
            "reply_chance": self.reply_chance
        })

    async def iicmd(self, message: types.Message):
        """
        Управление активацией бота в текущем чате
        Использование: .ii [on|off]
        """
        if not message.chat:
            return await utils.answer(message, "⚠ Эта команда работает только в чатах")

        chat_id = message.chat.id
        args = utils.get_args_raw(message).lower()

        if args in {"on", "вкл", "enable"}:
            self.active_chats.add(chat_id)
            self._save_data()
            return await utils.answer(message, self.strings["enabled"])

        if args in {"off", "выкл", "disable"}:
            self.active_chats.discard(chat_id)
            self._save_data()
            return await utils.answer(message, self.strings["disabled"])

        # Показать статус, если аргументы не указаны
        is_active = chat_id in self.active_chats
        status = self.strings["status"].format(
            "Да" if is_active else "Нет",
            self.reply_chance,
            len(self.chat_memory.get(chat_id, [])),
            len(self.config["blacklist"]),
            "Да" if self.config["generate_text"] else "Нет"
        )
        return await utils.answer(message, status)

    async def chancecmd(self, message: types.Message):
        """
        Установка шанса ответа
        Использование: .chance <число>
        """
        args = utils.get_args_raw(message)

        if not args:
            return await utils.answer(message, f"Текущий шанс ответа: 1 к {self.reply_chance}")

        if not args.isdigit() or int(args) < 1:
            return await utils.answer(message, self.strings["invalid_number"])

        self.reply_chance = int(args)
        self._save_data()
        return await utils.answer(message, self.strings["chance_set"].format(args))

    async def blacklistcmd(self, message: types.Message):
        """
        Управление черным списком пользователей
        Использование: .blacklist [add|remove|list] [user_id]
        """
        args = utils.get_args(message)
        
        if not args or args[0].lower() == "list":
            blacklist = self.config["blacklist"]
            if not blacklist:
                return await utils.answer(message, "📋 Черный список пуст")
            
            return await utils.answer(message, self.strings["blacklist_list"].format(
                "\n".join([f"• {user_id}" for user_id in blacklist])
            ))
        
        if len(args) < 2:
            return await utils.answer(message, self.strings["need_arg"])
        
        action, user_id = args[0].lower(), args[1]
        
        if not user_id.isdigit():
            return await utils.answer(message, "⚠ ID пользователя должен быть числом")
        
        user_id = int(user_id)
        
        if action == "add":
            if user_id not in self.config["blacklist"]:
                self.config["blacklist"].append(user_id)
                return await utils.answer(message, self.strings["blacklist_added"].format(user_id))
            return await utils.answer(message, f"Пользователь {user_id} уже в черном списке")
        
        if action == "remove":
            if user_id in self.config["blacklist"]:
                self.config["blacklist"].remove(user_id)
                return await utils.answer(message, self.strings["blacklist_removed"].format(user_id))
            return await utils.answer(message, f"Пользователь {user_id} не в черном списке")
        
        return await utils.answer(message, "⚠ Неизвестное действие. Используйте add, remove или list")

    async def templatescmd(self, message: types.Message):
        """
        Управление шаблонами ответов
        Использование: .templates [list|set "шаблон1" "шаблон2" ...]
        """
        args = utils.get_args(message)
        
        if not args or args[0].lower() == "list":
            templates = self.config["response_templates"]
            return await utils.answer(message, self.strings["templates_list"].format(
                "\n".join([f"• {template}" for template in templates])
            ))
        
        if args[0].lower() == "set" and len(args) > 1:
            self.config["response_templates"] = args[1:]
            return await utils.answer(message, self.strings["templates_updated"])
        
        return await utils.answer(message, "⚠ Неизвестное действие. Используйте list или set")

    async def clearmemorycmd(self, message: types.Message):
        """Очистка памяти бота для текущего чата"""
        if not message.chat:
            return await utils.answer(message, "⚠ Эта команда работает только в чатах")
        
        chat_id = message.chat.id
        if chat_id in self.chat_memory:
            self.chat_memory[chat_id] = []
            return await utils.answer(message, self.strings["memory_cleared"])
        
        return await utils.answer(message, "Нет памяти для очистки в этом чате")

    async def watcher(self, message: types.Message):
        """Отслеживание всех сообщений для возможных ответов"""
        if not isinstance(message, types.Message) or not message.chat:
            return

        chat_id, user_id = message.chat.id, message.sender_id

        # Обновляем память независимо от активного статуса (для накопления знаний)
        self._update_memory(chat_id, message)

        # Проверяем, должны ли мы обрабатывать это сообщение
        if (chat_id not in self.active_chats or 
            user_id == self._me.id or 
            user_id in self.config["blacklist"] or
            not message.text):  # Игнорируем медиа-сообщения без текста
            return

        # Проверка случайного шанса
        if random.randint(1, self.reply_chance) != 1:
            return

        # Обрабатываем сообщение и генерируем ответ
        await self._process_and_reply(message)

    def _update_memory(self, chat_id: int, message: types.Message):
        """Обновление памяти чата новыми сообщениями"""
        if chat_id not in self.chat_memory:
            self.chat_memory[chat_id] = []
        
        # Не сохраняем пустые или очень короткие сообщения
        if not message.text or len(message.text) < 3:
            return
        
        # Сохраняем сообщение в памяти
        self.chat_memory[chat_id].append({
            "id": message.id,
            "text": message.text,
            "sender": message.sender_id,
            "timestamp": message.date.timestamp(),
            "reply_to": message.reply_to.reply_to_msg_id if message.reply_to else None
        })
        
        # Ограничиваем размер памяти для каждого чата
        if len(self.chat_memory[chat_id]) > self.config["max_memory_per_chat"]:
            self.chat_memory[chat_id] = self.chat_memory[chat_id][-self.config["max_memory_per_chat"]:]

    async def _process_and_reply(self, message: types.Message):
        """Обработка сообщения и генерация подходящего ответа"""
        chat_id = message.chat.id
        text = message.text
        
        # Извлекаем значимые слова для поиска
        words = [
            word for word in text.split() 
            if len(word) >= self.config["min_word_length"] and not word.startswith(('http', '@', '#'))
        ]
        
        if not words:
            return
        
        # Пытаемся найти контекстуально релевантные ответы
        response = await self._find_contextual_reply(chat_id, message, words)
        
        # Если контекстуальный ответ не найден, пробуем ответ на основе памяти
        if not response and self.chat_memory.get(chat_id):
            response = await self._find_memory_based_reply(chat_id, words)
        
        # Если все еще нет ответа и generate_text включен, используем шаблоны
        if not response and self.config["generate_text"]:
            response = self._generate_random_response()
        
        # Отправляем ответ, если он у нас есть
        if response:
            await asyncio.sleep(random.uniform(1, 3))  # Естественная задержка перед ответом
            await message.reply(response)

    async def _find_contextual_reply(self, chat_id: int, message: types.Message, words: List[str]) -> Optional[str]:
        """Поиск контекстуально релевантного ответа на основе содержания сообщения"""
        # Пробуем несколько случайных ключевых слов
        search_words = random.sample(words, min(3, len(words)))
        
        for search_word in search_words:
            try:
                # Ищем сообщения, содержащие это слово
                messages = []
                async for msg in message.client.iter_messages(
                    chat_id, 
                    search=search_word,
                    limit=self.config["max_search_results"]
                ):
                    if msg.replies and msg.replies.max_id and msg.id != message.id:
                        messages.append(msg)
                
                if not messages:
                    continue
                
                # Выбираем случайное сообщение с ответами
                base_message = random.choice(messages)
                
                # Получаем ответы на это сообщение
                reply_msgs = []
                async for msg in message.client.iter_messages(
                    chat_id,
                    ids=list(range(base_message.id + 1, base_message.replies.max_id + 1))
                ):
                    if (msg.reply_to and 
                        msg.reply_to.reply_to_msg_id == base_message.id and
                        msg.sender_id != self._me.id):  # Не используем наши собственные ответы
                        reply_msgs.append(msg)
                
                if reply_msgs:
                    # Выбираем ответ, который наиболее контекстуально подходит
                    return random.choice(reply_msgs).text
            
            except Exception:
                continue
        
        return None

    async def _find_memory_based_reply(self, chat_id: int, words: List[str]) -> Optional[str]:
        """Поиск ответа на основе памяти чата"""
        memory = self.chat_memory.get(chat_id, [])
        if not memory:
            return None
        
        # Находим сообщения в памяти, которые содержат наши поисковые слова
        matching_messages = []
        for msg in memory:
            if any(word.lower() in msg["text"].lower() for word in words):
                matching_messages.append(msg)
        
        if not matching_messages:
            return None
        
        # Находим сообщение, на которое есть ответы
        for base_msg in matching_messages:
            # Находим ответы на это сообщение
            replies = [
                msg for msg in memory 
                if msg["reply_to"] == base_msg["id"] and msg["sender"] != self._me.id
            ]
            
            if replies:
                # Сортируем ответы по релевантности
                return random.choice(replies)["text"]
        
        return None

    def _generate_random_response(self) -> str:
        """Генерация случайного ответа из шаблонов"""
        templates = self.config["response_templates"]
        return random.choice(templates)
