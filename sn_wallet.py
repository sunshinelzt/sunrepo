#meta developer @sunshinelzt

from .. import loader

@loader.tds
class GreetingModule(loader.Module):
    """Модуль для отправки сообщения о пополнении кошельков, настраиваемое через конфиг."""
    strings = {
        "name": "sn_wallet",
        "config_wallet": "Твой TON-адрес",
        "config_crypto_link": "Ссылка на счет для пополнения через @CryptoBot",
        "config_xrocket_link": "Ссылка на счет для пополнения через @tonRocketBot",
        "error_missing_config": "Ошибка: Все настройки должны быть заполнены. Используй команду `.cfg yg_wallet` для конфигурации.",
        "error_sending_message": "Ошибка: Не удалось отправить сообщение. Попробуй снова позже.",
        "welcome_message": (
            "<emoji document_id=5472055112702629499>👋</emoji> <b>Привет!</b>\n\n"
            "<emoji document_id=5471952986970267163>💎</emoji> <i>Мой баланс легко пополнить с помощью TON-адреса ниже:</i>\n\n"
            "<code>{wallet}</code>\n\n"
            "<b><emoji document_id=5217705010539812022>☺️</emoji> <a href='{crypto_link}'>Пополнить мой CryptoBot</a></b>\n\n"
            "<b><emoji document_id=5235575317191474172>🚀</emoji> <a href='{xrocket_link}'>Пополнить мой xRocket</a></b>"
        )
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "wallet",
                "укажи свой TON-адрес в конфиге (команда - .cfg sn_wallet)",
                lambda: self.strings("config_wallet")
            ),
            loader.ConfigValue(
                "crypto_link",
                "https://example.com",
                lambda: self.strings("config_crypto_link")
            ),
            loader.ConfigValue(
                "xrocket_link",
                "https://example.com",
                lambda: self.strings("config_xrocket_link")
            )
        )

    def _validate_config(self):
        """Проверка на наличие всех обязательных настроек."""
        wallet = self.config["wallet"]
        crypto_link = self.config["crypto_link"]
        xrocket_link = self.config["xrocket_link"]
        return all([wallet, crypto_link, xrocket_link])

    async def wcmd(self, message):
        """Показать всю информацию для пополнения кошельков."""
        
        # Проверка конфигурации
        if not self._validate_config():
            await message.edit(self.strings("error_missing_config"))
            return

        wallet = self.config["wallet"]
        crypto_link = self.config["crypto_link"]
        xrocket_link = self.config["xrocket_link"]

        # Формируем сообщение с улучшенным форматом
        welcome_message = self.strings("welcome_message").format(
            wallet=wallet,
            crypto_link=crypto_link,
            xrocket_link=xrocket_link
        )

        # Принудительное использование UTF-8 для всех операций с текстом
        welcome_message_utf8 = welcome_message.encode('utf-8').decode('utf-8')

        # Отправка подготовленного сообщения
        try:
            await message.edit(welcome_message_utf8)
        except Exception:
            await message.edit(self.strings("error_sending_message"))
