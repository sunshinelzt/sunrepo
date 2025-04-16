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
    """Автоматически отправляет зеркальное сообщение в ответ на ключевые слова"""
    
    strings = {
        "name": "MirrorResponder",
        "mirror_enabled": "<emoji document_id=5909201569898827582>🔔</emoji> <b>Автоответчик зеркала включен</b>",
        "mirror_disabled": "<emoji document_id=5909123362839335003>🔕</emoji> <b>Автоответчик зеркала выключен</b>",
    }
    
    def __init__(self):
        # Список распространенных ключевых слов для активации
        default_keywords = [
            "ссылка", "ссылку", "бота", "бот", "удалили", "снесли", "зеркало", 
            "блокнули", "заблокировали", "заблокали", "рабочий", "фанстат", 
            "робот", "ботик", "телелог", "bot", "robot", "фс", "ботом", 
            "скинь", "фанстатом", "фан стат"
        ]
        
        self.config = loader.ModuleConfig(
            "keywords", default_keywords, "Ключевые слова для активации зеркала",
            "mirror_text", "<b>[Авто отправка зеркала]</b>\n <emoji document_id=5931415565955503486>🤖</emoji> <b>Hoвый бoт:</b> @telelogrbot, @telellogbot\n\n<code>+{}</code> 💠", 
            "Текст зеркала (используйте {} для вставки случайного числа)",
            "cooldown", 30, "Кулдаун между ответами в одном чате (в секундах)",
            "chats", [], "Список ID чатов для работы (пустой список = все чаты)"
        )
        self.last_response = {}  # Словарь для отслеживания кулдауна по чатам
    
    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        self.is_enabled = self.db.get(self.__class__.__name__, "enabled", True)
    
    @loader.command(ru_doc="Включить/выключить модуль зеркала")
    async def mirr(self, message):
        """Включить/выключить модуль зеркала"""
        self.is_enabled = not self.is_enabled
        self.db.set(self.__class__.__name__, "enabled", self.is_enabled)
        
        await utils.answer(
            message, 
            self.strings["mirror_enabled"] if self.is_enabled else self.strings["mirror_disabled"]
        )
    
    def _check_for_keywords(self, text):
        """Проверяет наличие ключевых слов в тексте"""
        if not text:
            return False
            
        text_lower = text.lower()
        
        # Проверяем каждое ключевое слово
        for keyword in self.config["keywords"]:
            # Ищем слово целиком (с границами слов)
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, text_lower):
                return True
                
        return False
    
    @loader.watcher()
    async def watcher(self, message):
        """Наблюдает за сообщениями и отвечает при обнаружении ключевых слов"""
        if not self.is_enabled:
            return
            
        # Проверяем, является ли сообщение текстовым
        if not message.text:
            return
            
        # Получаем ID чата
        chat_id = utils.get_chat_id(message)
        
        # Проверяем список разрешенных чатов (если список не пустой)
        if self.config["chats"] and chat_id not in self.config["chats"]:
            return
            
        # Игнорируем собственные сообщения
        if message.sender_id == (await message.client.get_me()).id:
            return
        
        # Игнорируем сообщения от ботов
        if getattr(message.sender, "bot", False):
            return
            
        # Проверяем на кулдаун
        current_time = time.time()
        if chat_id in self.last_response:
            time_passed = current_time - self.last_response[chat_id]
            if time_passed < self.config["cooldown"]:
                return
        
        # Проверяем наличие ключевых слов
        if self._check_for_keywords(message.text):
            try:
                # Генерируем случайное 9-значное число
                random_number = random.randint(100000000, 999999999)
                
                # Форматируем текст зеркала
                mirror_text = self.config["mirror_text"].format(random_number)
                
                # Записываем время ответа для кулдауна
                self.last_response[chat_id] = current_time
                
                # Отправляем зеркальное сообщение в ответ
                await message.reply(mirror_text)
            except Exception as e:
                # Логирование ошибок для отладки при необходимости
                self.log(f"Ошибка отправки сообщения: {e}")
