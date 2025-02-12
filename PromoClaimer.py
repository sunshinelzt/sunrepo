# meta developer: @sunshinelzt

import logging
import re
from telethon.errors import AlreadyInConversationError
from telethon.tl.types import Message
from .. import loader, utils

logger = logging.getLogger('PromoClaimer')

@loader.tds
class PromoClaimerMod(loader.Module):
    strings = {
        "name": "PromoClaimer",
        "claimed_promo": "[PromoClaimer] 👌 Успешно активирован промокод {promo} на {amount} токенов!",
        "error_watcher": "[PromoClaimer] ⛔ Ошибка при отслеживании сообщений:\n{e}",
        "invalid_promo": "[PromoClaimer] 😢 Промокод {promo} недействителен или истёк!",
        "already_claimed": "[PromoClaimer] 😢 Промокод {promo} уже активирован!",
        "enabled": "[PromoClaimer] ✅ Автозабор промокодов ВКЛЮЧЕН!",
        "disabled": "[PromoClaimer] ❌ Автозабор промокодов ВЫКЛЮЧЕН!",
    }

    GROUP_USERNAME = "StableWaifu"

    async def get_group_id(self):
        if not hasattr(self, "group_id"):
            entity = await self.client.get_entity(f"t.me/{self.GROUP_USERNAME}")
            self.group_id = entity.id
        return self.group_id

    async def client_ready(self, client, db):
        self.db = db
        self.enabled = self.db.get("PromoClaimer", "enabled", True)

    @loader.command(ru_doc="| Включить/выключить автозабор промокодов")
    async def wpromo(self, message: Message):
        self.enabled = not self.enabled
        self.db.set("PromoClaimer", "enabled", self.enabled)
        await utils.answer(message, self.strings["enabled"] if self.enabled else self.strings["disabled"])

    @loader.command(ru_doc="| Посмотреть баланс токенов")
    async def wcheck(self, message: Message):
        try:
            async with self.client.conversation('@StableWaifuBot') as conv:
                await conv.send_message('/tokens')
                response = await conv.get_response()

                match = re.search(r"💵 Доступные токены:\s*(\d+)", response.text)

                if match:
                    tokens = match.group(1)
                    await conv.mark_read()
                    await response.delete()
                    await utils.answer(message, f"Доступные токены: {tokens}")
                else:
                    await utils.answer(message, "Не удалось найти количество токенов.")
        except AlreadyInConversationError:
            pass

    @loader.watcher(incoming=True, edited_messages=True)
    async def watcher(self, message: Message):
        if not self.enabled or message.chat_id != await self.get_group_id():
            return

        try:
            pattern = r'https://t\.me/StableWaifuBot\?start=promo_(\w+)'
            for match in re.findall(pattern, message.text):
                promo = f'promo_{match}'

                async with self.client.conversation('StableWaifuBot') as conv:
                    msg = await conv.send_message(f'/start {promo}')
                    response = await conv.get_response()
                    await conv.mark_read()
                    await msg.delete()
                    await response.delete()

                text = response.text

                if "🥲 Промокод недействителен" in text:
                    logger.info(self.strings["invalid_promo"].format(promo=promo))
                elif "❌ Этот промокод уже активирован" in text:
                    logger.info(self.strings["already_claimed"].format(promo=promo))
                else:
                    amount = re.search(r"\(\+(\d+)", text)
                    amount = amount.group(1) if amount else "?"
                    logger.info(self.strings["claimed_promo"].format(promo=promo, amount=amount))

        except Exception as e:
            logger.exception(f"[PromoClaimer] Ошибка: {e}")
