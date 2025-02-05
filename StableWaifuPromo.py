# meta developer: @sunshinelzt
# meta name: StableWaifuPromo
# meta desc: Автоматически активирует промокоды в группе @StableWaifu
# meta author: @sunshinelzt

import re
import asyncio
from hikka import loader
from hikkatl.types import Message

class StableWaifuPromoMod(loader.Module):
    """Автоматически активирует промокоды в группе @StableWaifu"""

    strings = {"name": "StableWaifuPromo"}
    waifu_bot = "@StableWaifuBot"
    waifu_chat = -1001771182827  # ID группы @StableWaifu
    delay = 1.5  # Задержка для защиты от спама

    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        self.active = self.db.get("StableWaifuPromo", "active", True)
        self.processed = set()  # Храним обработанные промокоды в сессии

    async def watcher(self, message: Message):
        """Мониторинг сообщений в группе @StableWaifu"""
        if not self.active or message.chat_id != self.waifu_chat or not message.raw_text:
            return

        promo_codes = set(re.findall(r"https://t\.me/StableWaifuBot\?start=promo_([\w\d]+)", message.raw_text))
        promo_codes.update(
            entity_text.split("promo_")[-1]
            for _, entity_text in message.get_entities_text()
            if "t.me/StableWaifuBot?start=promo_" in entity_text
        )

        new_codes = promo_codes - self.processed  # Убираем уже активированные в этой сессии

        for promo_code in new_codes:
            await self.client.send_message(self.waifu_bot, f"/start promo_{promo_code}")
            self.processed.add(promo_code)  # Добавляем в список обработанных
            await asyncio.sleep(self.delay)  # Защита от спама

    async def wpromo_cmd(self, message: Message):
        """Включить / отключить автоактивацию промокодов"""
        self.active = not self.active
        self.db.set("StableWaifuPromo", "active", self.active)
        await message.edit(f"✅ Автоактивация: {'ВКЛЮЧЕНА' if self.active else 'ВЫКЛЮЧЕНА'}")
