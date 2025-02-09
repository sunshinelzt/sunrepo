# -*- coding: utf-8 -*-
#meta developer @sunshinelzt

from .. import loader

@loader.tds
class GreetingModule(loader.Module):
    """Модуль для отправки сообщения о пополнении кошельков, настраиваемое через конфиг."""
    strings = {
        "name": "yg_wallet",
        "config_wallet": "Твой TON-адрес",
        "config_crypto_link": "Ссылка на счет для пополнения через @CryptoBot",
        "config_xrocket_link": "Ссылка на счет для пополнения через @tonRocketBot"
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "wallet",
                "укажи свой TON-адрес в конфиге (команда - .cfg yg_wallet)",
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

    async def wcmd(self, message):
        """Показать всю информацию для пополнения кошельков."""
        wallet = self.config["wallet"]
        crypto_link = self.config["crypto_link"]
        xrocket_link = self.config["xrocket_link"]

        if not wallet or not crypto_link or not xrocket_link:
            await message.edit("<b>Ошибка:</b> Все настройки должны быть заполнены. Используй команду .cfg yg_wallet для конфигурации.")
            return

        # Создание сообщения с информацией о пополнении
        TON = (
            f"<emoji document_id=5472055112702629499>👋</emoji> <b>Привет!</b>\n\n"
            f"<emoji document_id=5471952986970267163>💎</emoji> <i>Мой баланс легко пополнить с помощью TON-адреса ниже:</i>\n\n"
            f"<code>{wallet}</code>\n\n"
            f"<b><emoji document_id=5217705010539812022>☺️</emoji> <a href='{crypto_link}'>Пополнить мой CryptoBot</a></b>\n\n"
            f"<b><emoji document_id=5235575317191474172>🚀</emoji> <a href='{xrocket_link}'>Пополнить мой xRocket</a></b>"
        )

        # Отправка подготовленного сообщения
        try:
            await message.edit(TON)
        except Exception as e:
            await message.edit(f"<b>Ошибка:</b> Не удалось отправить сообщение. {str(e)}")
