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
        self.running = {}

    async def zaebcmd(self, message):
        """.zaeb <количество> <реплай> — Заёбывает пользователя"""
        reply = await message.get_reply_message()
        if not reply:
            await message.edit("<b>А кого заёбывать-то?</b>")
            return

        user_id = reply.sender_id
        args = utils.get_args(message)
        count = int(args[0]) if args and args[0].isdigit() and int(args[0]) > 0 else 50
        chat_id = message.chat_id

        if chat_id in self.running:
            await message.edit("<b>Уже заёбываю!</b>")
            return

        self.running[chat_id] = True
        await message.delete()
        
        text = f'<a href="tg://user?id={user_id}">Заёбушка :3</a>'

        for i in range(count):
            if not self.running.get(chat_id):
                break
            try:
                msg = await message.client.send_message(chat_id, text)
                await asyncio.sleep(random.uniform(0.2, 0.5))  # Рандомная задержка
                await msg.delete()
            except Exception:
                break  # Останавливаемся, если телега ругается

        self.running.pop(chat_id, None)

    async def stopzaebcmd(self, message):
        """.stopzaeb — Остановить заёбывание"""
        chat_id = message.chat_id
        if chat_id in self.running:
            self.running[chat_id] = False
            await message.edit("<b>Заёбывание остановлено.</b>")
        else:
            await message.edit("<b>Никого не заёбываю.</b>")
