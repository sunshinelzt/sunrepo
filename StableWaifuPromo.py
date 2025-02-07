# meta developer: @sunshinelzt

import logging
import re

from telethon.errors import AlreadyInConversationError
from telethon.tl.types import Message
from .. import loader, utils

logger = logging.getLogger('PromoClaimer')

@loader.tds
class PromoClaimerMod(loader.Module):
    """Automatically claim https://t.me/StableWaifuBot promo from any chat"""
    
    strings = {
        "name": "PromoClaimer",
        "claimed_promo": "[PromoClaimer] 👌 Successfully claimed promo {promo} for {amount} tokens!",
        "error_watcher": "[PromoClaimer] ⛔️ Error while watching messages:\n{e}",
        "invalid_promo": "[PromoClaimer] 😢 Promo {promo} is invalid or expired!",
        "already_claimed": "[PromoClaimer] 😢 Promo {promo} has already been claimed!",
        "checktokens_failed": "[PromoClaimer] 🚫 Failed to check token balance!\n{e}",
        "enabled": "[PromoClaimer] ✅ Auto-claiming is now **ENABLED**",
        "disabled": "[PromoClaimer] ❌ Auto-claiming is now **DISABLED**",
        "status": "[PromoClaimer] ⚙️ Auto-claiming is **{status}**",
    }

    strings_ru = {
        "claimed_promo": "[PromoClaimer] 👌 Успешно активирован промокод {promo} на {amount} токен(-ов)!",
        "error_watcher": "[PromoClaimer] ⛔️ Ошибка при отслеживании сообщений:\n{e}",
        "invalid_promo": "[PromoClaimer] 😢 Промокод {promo} недействителен или истёк!",
        "already_claimed": "[PromoClaimer] 😢 Промокод {promo} уже активирован!",
        "checktokens_failed": "[PromoClaimer] 🚫 Ошибка при проверке баланса токенов!\n{e}",
        "enabled": "[PromoClaimer] ✅ Авто-приём промокодов **ВКЛЮЧЕН**",
        "disabled": "[PromoClaimer] ❌ Авто-приём промокодов **ВЫКЛЮЧЕН**",
        "status": "[PromoClaimer] ⚙️ Авто-приём промокодов **{status}**",
        "_cls_doc": "Автоматически забирает промокоды для https://t.me/StableWaifuBot",
    }

    async def get_codes(self, text):
        """Ищет промокоды в тексте"""
        promo_pattern = r'https?://t\.me/StableWaifuBot\?start=promo_([\w-]+)'
        text_promo_pattern = r'promo_([\w-]+)'

        codes = set(re.findall(promo_pattern, text))
        text_codes = set(re.findall(text_promo_pattern, text)) 

        return codes.union(text_codes)

    async def claim_promo(self, promo_code):
        """Отправляет промокод в StableWaifuBot"""
        async with self.client.conversation('StableWaifuBot') as conv:
            msg = await conv.send_message(f'/start {promo_code}')
            response = await conv.get_response()
            await conv.mark_read()
            await msg.delete()
            await response.delete()

        if 'Промокод недействителен' in response.text:
            logger.info(self.strings("invalid_promo").format(promo=promo_code))
        elif 'Этот промокод уже активирован' in response.text:
            logger.info(self.strings("already_claimed").format(promo=promo_code))
        else:
            amount_match = re.search(r'\(\+(\d+) токен', response.text)
            amount = amount_match.group(1) if amount_match else "?"
            logger.info(self.strings("claimed_promo").format(promo=promo_code, amount=amount))

    async def check_tokens(self, message: Message):
        """Проверяет баланс токенов"""
        try:
            async with self.client.conversation('@StableWaifuBot') as conv:
                msg = await conv.send_message('/tokens')
                response = await conv.get_response()
                await conv.mark_read()
                await msg.delete()
                await response.delete()

            match = re.search(r'💵 Доступные токены: (\d+)', response.text)
            tokens = match.group(1) if match else "❌ Не удалось получить баланс"

            await utils.answer(message, f"💵 Токены: {tokens}")

        except Exception as e:
            logger.error(self.strings("checktokens_failed").format(e=str(e)))
            await utils.answer(message, self.strings("checktokens_failed").format(e=str(e)))

    async def watcher(self, message: Message):
        """Отслеживает новые сообщения и автоматически забирает промокоды"""
        if not self.get("enabled", True):
            return

        try:
            codes = await self.get_codes(message.text)
            for code in codes:
                await self.claim_promo(f'promo_{code}')
        except Exception as e:
            logger.error(self.strings("error_watcher").format(e=str(e)))

    @loader.command(ru_doc="| Включить / выключить авто-приём промокодов")
    async def wcheck(self, message: Message):
        """| Toggle auto-claiming promo codes"""
        new_state = not self.get("enabled", True)
        self.set("enabled", new_state)

        status = self.strings("enabled") if new_state else self.strings("disabled")
        await utils.answer(message, status)
