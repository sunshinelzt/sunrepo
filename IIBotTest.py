# meta developer: @sunshinelzt

import random
from telethon import types
from .. import loader, utils
import asyncio

@loader.tds
class IiBotMod(loader.Module):
    """Модуль для имитации дурачка в чате, отвечающий случайными сообщениями из истории"""
    
    strings = {
        'name': 'iiBot',
        'pref': '<b>iiBot:</b> ',
        'need_arg': '{}Нужен аргумент',
        'status': '{}Шанс ответа установлен: 1/{} ({}%)',
        'on': '{}Модуль включён в этом чате',
        'off': '{}Модуль выключен в этом чате',
        'min_len_set': '{}Минимальная длина слова: {}',
        'word_count_set': '{}Количество слов для поиска: {}',
        'status_info': '{}Статус в этом чате: {}\nШанс ответа: 1/{} ({}%)\nМинимальная длина слова: {}\nКоличество слов для поиска: {}'
    }
    
    db_name = 'iibot'
    
    async def client_ready(self, client, db):
        """Инициализация модуля при запуске"""
        self.db = db
        self.client = client
        
        # Инициализация настроек по умолчанию
        if self.db.get(self.db_name, 'min_length', None) is None:
            self.db.set(self.db_name, 'min_length', 3)
        
        if self.db.get(self.db_name, 'word_count', None) is None:
            self.db.set(self.db_name, 'word_count', 2)
    
    @staticmethod
    def str2bool(v):
        """Преобразует строку в логическое значение"""
        if not v:
            return False
        return v.lower() in ("yes", "y", "ye", "yea", "true", "t", "1", "on", "enable", "start", "run", "go", "да")
    
    async def iicmd(self, message: types.Message):
        """Переключить режим дурачка в чате
        Использование: .ii [on/off]"""
        args = utils.get_args_raw(message)
        
        if not message.chat:
            return await utils.answer(message, f"{self.strings['pref']}Команда работает только в чатах")
            
        chat_id = message.chat.id
        chats = self.db.get(self.db_name, 'chats', [])
        
        # Обработка случая без аргументов (переключение)
        if not args:
            if chat_id in chats:
                chats.remove(chat_id)
                self.db.set(self.db_name, 'chats', chats)
                return await utils.answer(message, self.strings['off'].format(self.strings['pref']))
            else:
                chats.append(chat_id)
                chats = list(set(chats))  # Удаление дубликатов
                self.db.set(self.db_name, 'chats', chats)
                return await utils.answer(message, self.strings['on'].format(self.strings['pref']))
        
        # Обработка явного включения/выключения
        if self.str2bool(args):
            if chat_id not in chats:
                chats.append(chat_id)
                chats = list(set(chats))  # Удаление дубликатов
                self.db.set(self.db_name, 'chats', chats)
            return await utils.answer(message, self.strings['on'].format(self.strings['pref']))
        else:
            if chat_id in chats:
                chats.remove(chat_id)
                self.db.set(self.db_name, 'chats', chats)
            return await utils.answer(message, self.strings['off'].format(self.strings['pref']))
    
    async def randomicmd(self, message: types.Message):
        """Установить шанс ответа 1 к N.
        0 - всегда отвечать.
        Использование: .randomi <число>"""
        args = utils.get_args_raw(message)
        
        if not args:
            chance = self.db.get(self.db_name, 'chance', 0)
            percent = "100%" if chance == 0 else f"{100 / chance:.1f}%"
            return await utils.answer(
                message, 
                self.strings['need_arg'].format(self.strings['pref']) + 
                f"\nТекущее значение: 1/{chance} ({percent})"
            )
        
        if not args.isdigit():
            return await utils.answer(message, self.strings['need_arg'].format(self.strings['pref']))
            
        chance = int(args)
        self.db.set(self.db_name, 'chance', chance)
        
        percent = "100%" if chance == 0 else f"{100 / chance:.1f}%"
        return await utils.answer(
            message, 
            self.strings['status'].format(self.strings['pref'], chance, percent)
        )
    
    async def minlencmd(self, message: types.Message):
        """Установить минимальную длину слова для поиска
        Использование: .minlen <число>"""
        args = utils.get_args_raw(message)
        
        if not args:
            min_length = self.db.get(self.db_name, 'min_length', 3)
            return await utils.answer(
                message, 
                f"{self.strings['pref']}Текущая минимальная длина слова: {min_length}"
            )
        
        if not args.isdigit():
            return await utils.answer(message, self.strings['need_arg'].format(self.strings['pref']))
            
        min_length = max(1, int(args))  # Минимум 1 символ
        self.db.set(self.db_name, 'min_length', min_length)
        
        return await utils.answer(
            message, 
            self.strings['min_len_set'].format(self.strings['pref'], min_length)
        )
        
    async def wordcountcmd(self, message: types.Message):
        """Установить количество слов для поиска
        Использование: .wordcount <число>"""
        args = utils.get_args_raw(message)
        
        if not args:
            word_count = self.db.get(self.db_name, 'word_count', 2)
            return await utils.answer(
                message, 
                f"{self.strings['pref']}Текущее количество слов для поиска: {word_count}"
            )
        
        if not args.isdigit():
            return await utils.answer(message, self.strings['need_arg'].format(self.strings['pref']))
            
        word_count = max(1, min(5, int(args)))  # От 1 до 5 слов
        self.db.set(self.db_name, 'word_count', word_count)
        
        return await utils.answer(
            message, 
            self.strings['word_count_set'].format(self.strings['pref'], word_count)
        )
    
    async def iistatuscmd(self, message: types.Message):
        """Показать текущий статус модуля в чате"""
        if not message.chat:
            return await utils.answer(message, f"{self.strings['pref']}Команда работает только в чатах")
        
        chat_id = message.chat.id
        chats = self.db.get(self.db_name, 'chats', [])
        status = "Включен" if chat_id in chats else "Выключен"
        
        chance = self.db.get(self.db_name, 'chance', 0)
        percent = "100%" if chance == 0 else f"{100 / chance:.1f}%"
        
        min_length = self.db.get(self.db_name, 'min_length', 3)
        word_count = self.db.get(self.db_name, 'word_count', 2)
        
        return await utils.answer(
            message,
            self.strings['status_info'].format(
                self.strings['pref'], status, chance, percent, min_length, word_count
            )
        )
    
    async def watcher(self, message: types.Message):
        """Обработчик входящих сообщений"""
        # Проверяем, что это сообщение в чате и не от нас
        if not isinstance(message, types.Message):
            return
        if not message.chat or message.sender_id == (await message.client.get_me()).id:
            return
        
        # Проверяем, что модуль включен в этом чате
        chat_id = message.chat.id
        if chat_id not in self.db.get(self.db_name, 'chats', []):
            return
        
        # Проверяем шанс ответа
        chance = self.db.get(self.db_name, 'chance', 0)
        if chance != 0 and random.randint(0, chance) != 0:
            return
        
        # Получаем текст сообщения
        text = message.raw_text
        if not text:
            return
        
        # Фильтруем слова по минимальной длине
        min_length = self.db.get(self.db_name, 'min_length', 3)
        filtered_words = list(filter(lambda x: len(x) >= min_length, text.split()))
        
        if not filtered_words:
            return
            
        # Выбираем случайные слова для поиска
        word_count = min(self.db.get(self.db_name, 'word_count', 2), len(filtered_words))
        words = {random.choice(filtered_words) for _ in range(word_count)}
        
        # Ищем сообщения по словам
        msgs = []
        for word in words:
            try:
                async for msg in message.client.iter_messages(message.chat.id, search=word, limit=10000):
                    if msg and msg.replies and msg.replies.max_id:
                        msgs.append(msg)
            except Exception:
                continue
        
        if not msgs:
            return
            
        # Выбираем случайное сообщение
        try:
            replier = random.choice(msgs)
            sid = replier.id
            eid = replier.replies.max_id
            
            # Получаем все ответы на это сообщение
            reply_msgs = []
            async for msg in message.client.iter_messages(
                message.chat.id, 
                ids=list(range(sid + 1, eid + 1))
            ):
                if msg and msg.reply_to and msg.reply_to.reply_to_msg_id == sid:
                    reply_msgs.append(msg)
                    
            if not reply_msgs:
                return
                
            # Выбираем случайный ответ
            reply_msg = random.choice(reply_msgs)
            
            # Небольшая задержка для естественности
            await asyncio.sleep(random.uniform(0.5, 2.0))
            
            # Проверяем, что модуль все еще активен
            if message.chat.id not in self.db.get(self.db_name, 'chats', []):
                return
                
            # Отправляем ответ
            await message.reply(reply_msg)
            
        except Exception:
            return
