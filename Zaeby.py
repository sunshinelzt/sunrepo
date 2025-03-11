# meta developer: @sunshinelzt

import asyncio
import random
from .. import loader, utils

def register(cb):
    cb(ZaebyMod())

class ZaebyMod(loader.Module):
    """Заебет любого"""
    strings = {'name': 'Заёбушка'}
    
    def __init__(self):
        self.config = loader.ModuleConfig(
            "DEFAULT_COUNT", 50, "Количество сообщений по умолчанию",
            "MIN_DELAY", 0.2, "Минимальная задержка между сообщениями (в секундах)",
            "MAX_DELAY", 0.5, "Максимальная задержка между сообщениями (в секундах)",
            "MESSAGE_TEXT", "Заёбушка :3", "Текст сообщения (поддерживает HTML и любые символы)",
            "AUTO_DELETE", True, "Удалять сообщения после отправки (True/False)"
        )
        self.running = {}

    async def zaebcmd(self, message):
        """.zaeb <количество> <реплай> — Начать заёбывание"""
        reply = await message.get_reply_message()
        if not reply:
            await message.edit("<b>А кого заёбывать-то?</b>")
            return

        user_id = reply.sender_id
        args = utils.get_args(message)
        count = int(args[0]) if args and args[0].isdigit() and int(args[0]) > 0 else self.config["DEFAULT_COUNT"]
        chat_id = message.chat_id

        if chat_id in self.running:
            await message.edit("<b>Уже заёбываю!</b>")
            return

        self.running[chat_id] = True
        await message.delete()

        text = f'<a href="tg://user?id={user_id}">{self.config["MESSAGE_TEXT"]}</a>'

        for _ in range(count):
            if not self.running.get(chat_id):
                break
            try:
                msg = await message.client.send_message(chat_id, text)
                await asyncio.sleep(random.uniform(self.config["MIN_DELAY"], self.config["MAX_DELAY"]))
                if self.config["AUTO_DELETE"]:
                    await msg.delete()
            except Exception:
                break

        self.running.pop(chat_id, None)

    async def szaebcmd(self, message):
        """.szaeb — Остановить заёбывание"""
        chat_id = message.chat_id
        if chat_id in self.running:
            self.running[chat_id] = False
            await message.edit("<b>Заёбывание остановлено.</b>")
        else:
            await message.edit("<b>Никого не заёбываю.</b>")
