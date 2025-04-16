# meta developer: @sunshinelzt
# scope: hikka_only

from telethon import events
from telethon.tl.types import Message
from .. import loader, utils

@loader.tds
class AutoRespMod(loader.Module):
    """Авто-ответ на сообщения с ключевыми словами в выбранных чатах"""
    
    strings = {"name": "AutoResp"}
    
    def __init__(self):
        self.config = loader.ModuleConfig(
            "msg", "[Авто отправка зеркала]\n<emoji document_id=5931415565955503486>🤖</emoji><b>Hoвый бoт:</b> @telelogrbot\n@telellogbot\n\n<b>Мяу</b><emoji document_id=6046410905829251121>💥</emoji>", "Текст ответа",
            "kw", [
                "ссылка", "ссылку", "бота", "бот", "удалили", "снесли", "зеркало", 
                "блокнули", "заблокировали", "заблокали", "рабочий", "фанстат", 
                "робот", "ботик", "телелог", "bot", "robot", "фс", "ботом",
                "скинь", "фанстатом", "фан стат"
            ], "Ключевые слова"
        )
        self.chats = {}
    
    def __save_chats(self):
        self._db.set(self.strings["name"], "chats", self.chats)
        
    def __load_chats(self):
        return self._db.get(self.strings["name"], "chats", {})
    
    @loader.watcher(only_messages=True)
    async def watcher(self, message: Message):
        """Наблюдатель за сообщениями"""
        if not isinstance(message, Message):
            return
            
        chat_id = str(utils.get_chat_id(message))
        if chat_id not in self.chats or not self.chats[chat_id]:
            return
            
        if message.sender_id == self._tg_id:
            return
            
        if message.text:
            lower_text = message.text.lower()
            for keyword in self.config["kw"]:
                if keyword.lower() in lower_text:
                    await message.reply(self.config["msg"])
                    return
    
    async def client_ready(self, client, db):
        """Инициализация модуля"""
        self._tg_id = client.tg_id
        self._client = client
        self._db = db
        self.chats = self.__load_chats()
    
    async def arcmd(self, message: Message):
        """Включить/выключить автоответчик в текущем чате"""
        chat_id = str(utils.get_chat_id(message))
        
        if chat_id not in self.chats:
            self.chats[chat_id] = True
            status = "<emoji document_id=5776375003280838798>✅</emoji> Включен"
        else:
            self.chats[chat_id] = not self.chats[chat_id]
            status = "<emoji document_id=5776375003280838798>✅</emoji> Включен" if self.chats[chat_id] else "<emoji document_id=5778527486270770928>❌</emoji> Выключен"
            
        self.__save_chats()
        await utils.answer(message, f"<b>Автоответчик в этом чате: {status}</b>")
    
    async def arsetcmd(self, message: Message):
        """Установить текст ответа. Синтаксис: .arset [текст]"""
        args = utils.get_args_raw(message)
        if not args:
            return await utils.answer(message, f"<b>Текущий ответ:</b>\n{self.config['msg']}")
        
        self.config["msg"] = args
        await utils.answer(message, f"<b>Новый ответ установлен</b>")
    
    async def kwcmd(self, message: Message):
        """Управление ключевыми словами. Синтаксис: .kw [слова через запятую]"""
        args = utils.get_args_raw(message)
        if not args:
            keywords = ", ".join(self.config["kw"])
            return await utils.answer(message, f"<b>Ключевые слова:</b>\n{keywords}")
        
        keywords = [kw.strip() for kw in args.split(",")]
        self.config["kw"] = keywords
        await utils.answer(message, f"<b>Новые ключевые слова установлены</b>")
        
    async def archats(self, message: Message):
        """Показать список чатов с активным автоответчиком"""
        active_chats = []
        
        for chat_id, is_active in self.chats.items():
            if is_active:
                try:
                    chat = await self._client.get_entity(int(chat_id))
                    chat_name = chat.title if hasattr(chat, "title") else chat.first_name
                    active_chats.append(f"• {chat_name}")
                except:
                    active_chats.append(f"• ID: {chat_id}")
        
        if not active_chats:
            return await utils.answer(message, "<b>Нет активных чатов</b>")
            
        await utils.answer(message, "<b>Активные чаты:</b>\n" + "\n".join(active_chats))
