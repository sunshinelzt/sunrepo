# meta developer: @sunshinelzt

from telethon import events
from .. import loader, utils
import re

class StableWaifuPromoMod(loader.Module):
    """Автоматически активирует промокоды из @StableWaifu"""

    strings = {"name": "StableWaifuPromo"}

    async def client_ready(self, client, db):
        self.client = client
        self.db = db

    async def promowatchcmd(self, message):
        """Включает/выключает автоактивацию промокодов"""
        watching = not self.db.get("StableWaifuPromo", "watching", False)
        self.db.set("StableWaifuPromo", "watching", watching)
        await utils.answer(message, f"✅ Автоактивация {'включена' if watching else 'выключена'}")

    @events.register(events.NewMessage(chats="StableWaifu"))
    async def check_promo(self, message):
        """Проверяет сообщения на наличие промокодов и активирует их"""
        if not self.db.get("StableWaifuPromo", "watching", False):
            return

        # Ищем все ссылки в сообщении
        links = re.findall(r"https://t\.me/StableWaifuBot\?start=(promo_[\w\d]+)", message.raw_text)

        for link in links:
            await self.client.send_message("StableWaifuBot", f"/start {link}")
