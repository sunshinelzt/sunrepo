# meta developer: @sunshinelzt

from telethon import events
from hikkatl.types import Message
from .. import loader, utils

class StableWaifuPromo(loader.Module):
    """Автоматическая активация промокодов из @StableWaifu"""

    strings = {"name": "StableWaifuPromo"}

    async def client_ready(self, client, db):
        """Инициализация"""
        self.client = client
        self.db = db
        self.channel = "@StableWaifu"

        if self.db.get("StableWaifuPromo", "enabled", False):
            self.client.add_event_handler(self.check_new_messages, events.NewMessage(chats=self.channel))

    async def wcmd(self, message: Message):
        """Включает / Выключает автоактивацию"""
        args = utils.get_args_raw(message)

        if args == "on":
            self.db.set("StableWaifuPromo", "enabled", True)
            self.client.add_event_handler(self.check_new_messages, events.NewMessage(chats=self.channel))
            return await utils.answer(message, "**✅ Автоактивация ВКЛЮЧЕНА!**")
        elif args == "off":
            self.db.set("StableWaifuPromo", "enabled", False)
            self.client.remove_event_handler(self.check_new_messages)
            return await utils.answer(message, "**⛔ Автоактивация ВЫКЛЮЧЕНА.**")

        status = "**🟢 ВКЛЮЧЕНА**" if self.db.get("StableWaifuPromo", "enabled", False) else "**🔴 ВЫКЛЮЧЕНА**"
        await utils.answer(message, f"**📡 Статус автоактивации: {status}**")

    async def check_new_messages(self, event: Message):
        """Отслеживает новые промокоды и активирует их"""
        promo_links = [e.url for e in event.message.entities or [] if hasattr(e, "url") and "start=promo_" in e.url]

        for link in promo_links:
            promo_code = link.split("start=")[1]
            await self.client.send_message("StableWaifuBot", f"/start {promo_code}")
