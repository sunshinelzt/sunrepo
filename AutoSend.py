# meta developer: @sunshinelzt
# scope: hikka_only

import asyncio
import random
from datetime import datetime
from telethon.tl.types import Message
from .. import loader, utils

@loader.tds
class AutoSenderMod(loader.Module):
    """Автоматически отправляет сообщение в чат через заданный интервал"""
    
    strings = {"name": "AutoSender"}
    
    def __init__(self):
        self.config = loader.ModuleConfig(
            "text", """[Авто отправка зеркала]
<emoji document_id=5931415565955503486>🤖</emoji><b> Hoвый бoт:</b>
@telelogrbot
@telellogbot
<b>Мяу</b><emoji document_id=6046410905829251121>💥</emoji>""", "Текст сообщения для отправки",
            
            "min_time", 30, "Минимальное время в минутах",
            "max_time", 60, "Максимальное время в минутах",
            "random", True, "Использовать случайное время"
        )
        self.tasks = {}
    
    async def client_ready(self, client, db):
        self._client = client
        self._db = db
        self.chats = self._db.get(self.strings["name"], "chats", {})
        
        # Восстанавливаем задачи
        for chat_id in self.chats:
            if self.chats[chat_id]["active"]:
                self._start_task(chat_id)
    
    def _get_interval(self):
        if self.config["random"]:
            minutes = random.randint(self.config["min_time"], self.config["max_time"])
        else:
            minutes = self.config["min_time"]
        return minutes * 60  # в секундах
    
    def _save_chats(self):
        self._db.set(self.strings["name"], "chats", self.chats)
    
    async def _sender_task(self, chat_id):
        try:
            while chat_id in self.chats and self.chats[chat_id]["active"]:
                # Отправляем сообщение
                await self._client.send_message(int(chat_id), self.config["text"])
                
                # Ждем следующего интервала
                await asyncio.sleep(self._get_interval())
        except Exception as e:
            self.chats[chat_id]["active"] = False
            self._save_chats()
    
    def _start_task(self, chat_id):
        if chat_id in self.tasks and not self.tasks[chat_id].done():
            self.tasks[chat_id].cancel()
        self.tasks[chat_id] = asyncio.create_task(self._sender_task(chat_id))
    
    async def autosendcmd(self, message: Message):
        """Включить/выключить автоотправку в текущем чате"""
        chat_id = str(utils.get_chat_id(message))
        
        if chat_id not in self.chats:
            self.chats[chat_id] = {
                "active": True,
                "added": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            self._start_task(chat_id)
            status = "<emoji document_id=5776375003280838798>✅</emoji> Включен"
        else:
            self.chats[chat_id]["active"] = not self.chats[chat_id]["active"]
            
            if self.chats[chat_id]["active"]:
                self._start_task(chat_id)
                status = "<emoji document_id=5776375003280838798>✅</emoji> Включен"
            else:
                if chat_id in self.tasks:
                    self.tasks[chat_id].cancel()
                status = "<emoji document_id=5778527486270770928>❌</emoji> Выключен"
        
        self._save_chats()
        
        if self.config["random"]:
            interval = f"от {self.config['min_time']} <b>до</b> {self.config['max_time']} <b>мин</b>"
        else:
            interval = f"{self.config['min_time']} мин"
            
        await utils.answer(message, f"<b>Автоотправщик: {status}</b>\n\n<b>Интервал: {interval}</b>")
    
    async def autochats(self, message: Message):
        """Показать список чатов с активной автоотправкой"""
        active_chats = []
        
        for chat_id in self.chats:
            if self.chats[chat_id]["active"]:
                try:
                    chat = await self._client.get_entity(int(chat_id))
                    chat_name = chat.title if hasattr(chat, "title") else chat.first_name
                except:
                    chat_name = f"Чат {chat_id}"
                
                active_chats.append(f"• {chat_name}")
        
        if not active_chats:
            text = "<b>Нет активных чатов</b>"
        else:
            text = "<b>Активные чаты:</b>\n" + "\n".join(active_chats)
        
        await utils.answer(message, text)
