# meta developer: @sunshinelzt

import logging
import re
from telethon.errors import AlreadyInConversationError
from telethon.tl.types import Message
from .. import loader, utils

logger = logging.getLogger("PromoClaimer")

@loader.tds
class PromoClaimerMod(loader.Module):
    """Автозабор промокодов @StableWaifu"""

    strings = {
        "name": "PromoClaimer",
        "claimed_promo": "[PromoClaimer] 👌 Успешно активирован промокод {promo} на {amount} токенов!",
        "error_watcher": "[PromoClaimer] ⛔ Ошибка при отслеживании сообщений:\n{e}",
        "invalid_promo": "[PromoClaimer] 😢 Промокод {promo} недействителен или истёк!",
        "already_claimed": "[PromoClaimer] 😢 Промокод {promo} уже активирован!",
        "enabled": "[PromoClaimer] ✅ Автозабор промокодов ВКЛЮЧЕН!",
        "disabled": "[PromoClaimer] ❌ Автозабор промокодов ВЫКЛЮЧЕН!",
        "balance": "[PromoClaimer] 💵 Доступные токены: {tokens}"
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue("enabled", True, "Включить/выключить авто-забор промокодов"),
            loader.ConfigValue("groups", ["StableWaifu"], "Список групп для мониторинга"),
            loader.ConfigValue("bot_username", "StableWaifuBot", "Бот для активации промокодов"),
            loader.ConfigValue("notify_user", True, "Отправлять уведомления после активации"),
            loader.ConfigValue("check_balance_after_claim", True, "Проверять баланс после активации"),
            loader.ConfigValue("log_file", "promo_claimer.log", "Имя лог-файла")
        )
        self.group_ids = {}

    async def client_ready(self, client, db):
        self.client = client
        await self.cache_group_ids()

    async def cache_group_ids(self):
        self.group_ids = {
            group: (await self.client.get_entity(f"t.me/{group}")).id
            for group in self.config["groups"]
        }

    @loader.command(ru_doc="| Включить/выключить авто-забор промокодов")
    async def wpromo(self, message: Message):
        self.config["enabled"] = not self.config["enabled"]
        await utils.answer(message, self.strings["enabled"] if self.config["enabled"] else self.strings["disabled"])

    @loader.command(ru_doc="| Посмотреть баланс токенов")
    async def wcheck(self, message: Message):
        try:
            async with self.client.conversation(f"@{self.config['bot_username']}") as conv:
                await conv.send_message("/tokens")
                response = await conv.get_response()
                match = re.search(r"💵 Доступные токены:\s*(\d+)", response.text)
                if match:
                    tokens = match.group(1)
                    await conv.mark_read()
                    await response.delete()
                    await utils.answer(message, self.strings["balance"].format(tokens=tokens))
                else:
                    await utils.answer(message, "Не удалось найти количество токенов.")
        except AlreadyInConversationError:
            pass

    @loader.watcher(incoming=True, edited_messages=True)
    async def watcher(self, message: Message):
        if not self.config["enabled"] or message.chat_id not in self.group_ids.values():
            return

        try:
            pattern = r'https://t\.me/StableWaifuBot\?start=promo_(\w+)'
            for match in re.findall(pattern, message.text):
                promo = f'promo_{match}'

                async with self.client.conversation(self.config["bot_username"]) as conv:
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

                    if self.config["notify_user"]:
                        await self.client.send_message(message.sender_id, self.strings["claimed_promo"].format(promo=promo, amount=amount))

                    if self.config["check_balance_after_claim"]:
                        await self.wcheck(message)

        except Exception as e:
            logger.exception(f"[PromoClaimer] Ошибка: {e}")
            if self.config["notify_user"]:
                await utils.answer(message, f"Ошибка при активации промокода: {e}")
