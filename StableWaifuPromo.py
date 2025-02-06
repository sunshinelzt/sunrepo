# meta developer: @sunshinelzt
# meta name: PromoClaimer
# meta desc: Автоматически активирует промокоды для @StableWaifuBot

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
        "claimed_promo": "[PromoClaimer] 👌 Я успешно активировал промокод {promo} на {amount} токен(-ов)!",
        "error_watcher": "[PromoClaimer] ⛔️ Во время отслеживания сообщений произошла ошибка:\n{e}",
        "invalid_promo": "[PromoClaimer] 😢 Промокод {promo} недействителен, либо уже истек!",
        "already_claimed": "[PromoClaimer] 😢 Промокод {promo} уже активирован!",
        "config_changed": "[PromoClaimer] ✅ Настройки изменены: {key} = {value}",
        "logging_disabled": "[PromoClaimer] 🛑 Логирование отключено.",
        "logging_enabled": "[PromoClaimer] ✅ Логирование включено.",
        "_cls_doc": "Автоматически забирать промокоды для https://t.me/StableWaifuBot",
    }

    strings_ru = {
        "claimed_promo": "[PromoClaimer] 👌 Я успешно активировал промокод {promo} на {amount} токен(-ов)!",
        "error_watcher": "[PromoClaimer] ⛔️ Во время отслеживания сообщений произошла ошибка:\n{e}",
        "invalid_promo": "[PromoClaimer] 😢 Промокод {promo} недействителен, либо уже истек!",
        "already_claimed": "[PromoClaimer] 😢 Промокод {promo} уже активирован!",
        "config_changed": "[PromoClaimer] ✅ Настройки изменены: {key} = {value}",
        "logging_disabled": "[PromoClaimer] 🛑 Логирование отключено.",
        "logging_enabled": "[PromoClaimer] ✅ Логирование включено.",
        "_cls_doc": "Автоматически забирать промокоды для https://t.me/StableWaifuBot",
    }

    def __init__(self):
        self.config = {
            "enabled": True,  # Включение/выключение автоактивации промокодов
            "processed": [],  # Обработанные промокоды
            "max_claims_per_hour": 10,  # Максимальное количество активированных промокодов в час
            "logging": True,  # Включение/выключение логирования
        }

    def _update_logging(self):
        """Обновляет настройки логирования в зависимости от конфигурации."""
        if self.config["logging"]:
            logger.setLevel(logging.INFO)
        else:
            logger.setLevel(logging.CRITICAL)

    @loader.command(ru_doc='| Включить или выключить автоактивацию промокодов')
    async def wpromo(self, message: Message):
        """| Включить или выключить автоактивацию промокодов"""
        if self.config["enabled"]:
            self.config["enabled"] = False
            await utils.answer(message, "[PromoClaimer] ⛔️ Автоактивация промокодов выключена!")
        else:
            self.config["enabled"] = True
            await utils.answer(message, "[PromoClaimer] ✅ Автоактивация промокодов включена!")

    @loader.command(ru_doc='| Настроить максимальное количество активаций в час')
    async def setmaxclaims(self, message: Message):
        """| Настроить максимальное количество активаций промокодов в час"""
        try:
            value = int(message.text.split()[1])
            self.config["max_claims_per_hour"] = value
            await utils.answer(message, self.strings["config_changed"].format(key="max_claims_per_hour", value=value))
        except (IndexError, ValueError):
            await utils.answer(message, "❌ Пожалуйста, укажите корректное значение для максимального количества активаций.")

    @loader.command(ru_doc='| Показать текущие настройки')
    async def showconfig(self, message: Message):
        """| Показать текущие настройки"""
        config_info = "\n".join([f"{key}: {value}" for key, value in self.config.items()])
        await utils.answer(message, f"Текущие настройки:\n{config_info}")

    @loader.command(ru_doc='| Включить или выключить логирование')
    async def togglelogging(self, message: Message):
        """| Включить или выключить логирование"""
        if self.config["logging"]:
            self.config["logging"] = False
            self._update_logging()
            await utils.answer(message, self.strings["logging_disabled"])
        else:
            self.config["logging"] = True
            self._update_logging()
            await utils.answer(message, self.strings["logging_enabled"])

    @loader.watcher()
    async def watcher(self, message: Message):
        try:
            if not self.config["enabled"]:
                return

            # Ищем промокоды в сообщениях
            pattern = r'https://t\.me/StableWaifuBot\?start=promo_(\w+)'
            matches = re.findall(pattern, message.text)

            for match in matches:
                promo = 'promo_' + match
                if promo in self.config["processed"]:
                    continue  # Пропускаем, если промокод уже был обработан

                if len(self.config["processed"]) >= self.config["max_claims_per_hour"]:
                    logger.info(f"❌ Достигнут предел активаций в час ({self.config['max_claims_per_hour']})")
                    return

                async with self.client.conversation('@StableWaifuBot') as conv:
                    msg = await conv.send_message(f'/start {promo}')
                    response = await conv.get_response()

                    await conv.mark_read()
                    await msg.delete()
                    await response.delete()

                # Если промокод недействителен
                if response.text == '🥲 Промокод недействителен или уже истёк!':
                    logger.info(self.strings("invalid_promo").format(promo=promo))
                # Если промокод уже активирован
                elif response.text == '❌ Этот промокод уже активирован, проверь выше!':
                    logger.info(self.strings('already_claimed').format(promo=promo))
                else:
                    # Если промокод успешно активирован
                    amount = response.text.split('(+')[1]
                    logger.info(self.strings('claimed_promo').format(promo=promo, amount=amount))

                # Добавляем промокод в список обработанных
                self.config["processed"].append(promo)

        except Exception as e:
            if self.config["logging"]:
                logger.error(self.strings['error_watcher'].format(e=str(e)))
