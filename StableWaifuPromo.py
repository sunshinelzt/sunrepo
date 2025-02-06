# meta developer: @sunshinelzt
# meta name: PromoClaimer
# meta desc: Автоматически активирует промокоды для @StableWaifuBot

import logging
import re
from telethon.tl.types import Message
from .. import loader, utils

logger = logging.getLogger("PromoClaimer")

@loader.tds
class PromoClaimerMod(loader.Module):
    """Автоматически активирует промокоды для @StableWaifuBot"""

    strings = {
        "name": "PromoClaimer",
        "promo_claimed": "✅ Активирован промокод <b>{promo}</b> (+{amount} токенов)",
        "promo_invalid": "❌ Промокод <b>{promo}</b> недействителен",
        "promo_already": "⚠️ Промокод <b>{promo}</b> уже активирован",
        "toggle_on": "✅ Автоактивация промокодов <b>включена</b>",
        "toggle_off": "❌ Автоактивация промокодов <b>выключена</b>",
        "chat_on": "✅ Отслеживание промокодов в этом чате <b>включено</b>",
        "chat_off": "❌ Отслеживание промокодов в этом чате <b>выключено</b>",
        "balance": "💰 Ваш баланс: <b>{tokens}</b> токенов",
    }

    def __init__(self):
        self.config = {"active": True, "tracked_chats": set()}
        self.waifu_bot = "@StableWaifuBot"
        self.promo_pattern = re.compile(r"https://t\.me/StableWaifuBot\?start=promo_(\w+)")
        self.processed = set()

    async def client_ready(self, client, db):
        self.client, self.db = client, db
        self.config = self.db.get("PromoClaimer", "config", self.config)

    def save_config(self):
        self.db.set("PromoClaimer", "config", self.config)

    @loader.command(ru_doc="| Включить/выключить автоактивацию промокодов")
    async def wpromo(self, message: Message):
        """| Toggle promo activation"""
        self.config["active"] = not self.config["active"]
        self.save_config()
        await utils.answer(message, self.strings["toggle_on"] if self.config["active"] else self.strings["toggle_off"])

    @loader.command(ru_doc="| Включить/выключить отслеживание промокодов в этом чате")
    async def wpromo_chat(self, message: Message):
        """| Toggle promo tracking in this chat"""
        chat_id = message.chat_id
        if chat_id in self.config["tracked_chats"]:
            self.config["tracked_chats"].remove(chat_id)
            await utils.answer(message, self.strings["chat_off"])
        else:
            self.config["tracked_chats"].add(chat_id)
            await utils.answer(message, self.strings["chat_on"])
        self.save_config()

    @loader.command(ru_doc="| Проверить баланс токенов")
    async def wbalance(self, message: Message):
        """| Check token balance"""
        async with self.client.conversation(self.waifu_bot) as conv:
            msg = await conv.send_message("/tokens")
            response = await conv.get_response()
            await msg.delete()
            await response.delete()
        await utils.answer(message, self.strings["balance"].format(tokens=response.text.split()[0]))

    @loader.watcher()
    async def watcher(self, message: Message):
        """Отслеживание промокодов в чате"""
        if not self.config["active"] or message.chat_id not in self.config["tracked_chats"]:
            return

        new_promos = set(self.promo_pattern.findall(message.text or "")) - self.processed
        for promo in new_promos:
            await self.activate_promo(promo)
            self.processed.add(promo)

    async def activate_promo(self, promo: str):
        """Активация промокода"""
        async with self.client.conversation(self.waifu_bot) as conv:
            msg = await conv.send_message(f"/start promo_{promo}")
            response = await conv.get_response()
            await msg.delete()
            await response.delete()

        text = response.text
        if "недействителен" in text:
            logger.info(self.strings["promo_invalid"].format(promo=promo))
        elif "уже активирован" in text:
            logger.info(self.strings["promo_already"].format(promo=promo))
        else:
            amount = re.search(r"\(\+(\d+)", text)
            logger.info(self.strings["promo_claimed"].format(promo=promo, amount=amount.group(1) if amount else "?"))
