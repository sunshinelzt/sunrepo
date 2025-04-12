# meta developer: @sunshinelzt
# О боже, какой же саншайн ахуенний, он такой крутой и красивый, я не магу... Умний, стильний, харизьматичный — в нём всьо иделяльно. Он всегда делает шота крутое, и за ним невозможна не восхишаться.

"""
 _____             ____                    _       
|_   _|_ _  _ _   |  _ \  ___ _ _   __ _| |_ ___ 
  | |/ _ \| '_ \  | | | |/ _ \| '_ \ / _` | __/ _ \
  | | (_) | | | | | |_| | (_) | | | | (_| | ||  __/
  |_|\___/|_| |_| |____/ \___/|_| |_|\__,_|\__\___|
"""

from .. import loader, utils
import logging
from urllib.parse import quote

logger = logging.getLogger(__name__)

# Группа эмодзи для легкой замены
class Emoji:
    QUESTION = "<emoji document_id=5436113877181941026>❓</emoji>"
    WARNING = "<emoji document_id=5447644880824181073>⚠️</emoji>"
    ERROR = "<emoji document_id=5210952531676504517>❌</emoji>"
    INFO = "<emoji document_id=5334544901428229844>ℹ️</emoji>"
    MONEY = "<emoji document_id=5409048419211682843>💵</emoji>"
    CRYSTAL = "💎"
    WALLET = "👛"
    CHECK = "<emoji document_id=5427009714745517609>✅</emoji>"
    SETTINGS = "<emoji document_id=5341715473882955310>⚙️</emoji>"

@loader.tds
class TonDonate(loader.Module):
    """Создает красивую ссылку на оплату TON с баннером. by @sunshinelzt"""
    
    strings = {
        "name": "TonDonate",
        "no_wallet": f"{Emoji.WARNING} <b>Ошибка</b> {Emoji.WARNING}\n\n{Emoji.QUESTION} <b>Вы не указали адрес кошелька в конфигурации модуля.</b>\n\n<i>Используйте команду .dtoncfg для настройки</i>",
        "no_amount": f"{Emoji.WARNING} <b>Ошибка</b> {Emoji.WARNING}\n\n{Emoji.QUESTION} <b>Необходимо указать сумму для создания платежа</b>\n\n<i>Пример: .dton 10</i>",
        "invalid_format": f"{Emoji.ERROR} <b>Ошибка формата</b> {Emoji.ERROR}\n\n{Emoji.INFO} <b>Правильный формат:</b>\n<code>.dton текст / сумма / комментарий</code>\n\n<i>Текст и комментарий необязательны, сумма обязательна</i>",
        "negative_amount": f"{Emoji.ERROR} <b>Ошибка</b> {Emoji.ERROR}\n\n<b>Сумма должна быть больше нуля</b>",
        "default_text": f"Запрос на оплату {{}} TON",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            "WALLET_ADDRESS", 
            None, 
            "Введите адрес своего TON кошелька",
            
            "BANNER_URL",
            "https://i.imgur.com/example.jpg",
            "Ссылка на изображение баннера (jpg, png, gif)",
            
            #"USE_CRYPTOBOT",
            #True,
            #"Добавлять кнопку для CryptoBot (True/False)",
            
            "USE_BANNER",
            True,
            "Использовать баннер-картинку (True/False)"
        )

    def _format_payment_message(self, title, amount, comment=None):
        """Формирует сообщение для запроса оплаты"""
        message = f"<b>{Emoji.CRYSTAL} Запрос на оплату TON</b>\n\n"
        
        if title:
            message += f"<b>{title}</b>\n\n"
        
        message += f"<b>{Emoji.MONEY} Сумма:</b> {amount} TON\n"
        
        if comment:
            message += f"<b>{Emoji.INFO} Комментарий:</b> {comment}\n"
        
        message += f"\n<i>Нажмите кнопку ниже для оплаты</i>"
        
        return message

    @loader.command()
    async def dton(self, message):
        """— текст / сумма / комментарий"""
        args = utils.get_args_raw(message)
        wallet = self.config["WALLET_ADDRESS"]
        
        if not wallet:
            return await utils.answer(message, self.strings["no_wallet"])
        
        if not args:
            return await utils.answer(message, self.strings["no_amount"])
        
        text, amount, comment = None, None, None
        
        if "/" in args:
            parts = list(map(str.strip, args.split("/", 2)))
            if len(parts) < 2:
                return await utils.answer(message, self.strings["invalid_format"])
            
            text = parts[0] or None
            amount = parts[1]
            comment = parts[2] if len(parts) == 3 else None
        else:
            text = None
            amount = args.strip()
            comment = None
            
        try:
            amount_float = float(amount)
        except ValueError:
            return await utils.answer(message, self.strings["invalid_format"])
        
        if amount_float <= 0:
            return await utils.answer(message, self.strings["negative_amount"])
        
        # Convert to nano TON (1 TON = 10^9 nano TON)
        nano_amount = int(amount_float * 1_000_000_000)
        
        # Create payment URL for Tonkeeper
        tonkeeper_url = f"https://app.tonkeeper.com/transfer/{wallet}?amount={nano_amount}"
        if comment:
            tonkeeper_url += f"&text={quote(comment)}"
        
        # Create payment URL for CryptoBot if enabled
        #cryptobot_url = None
        #if self.config["USE_CRYPTOBOT"]:
            #cryptobot_url = f"https://t.me/CryptoBot?start=ton_{amount}-{wallet}"
            #if comment:
                #cryptobot_url += f"-{quote(comment)}"
        
        # Default text if none provided
        if not text:
            text = self.strings["default_text"].format(amount)
        
        # Форматируем сообщение для запроса оплаты
        payment_message = self._format_payment_message(text, amount, comment)
        
        # Создаем кнопки оплаты
        buttons = [
            [{"text": f"{Emoji.CRYSTAL} Оплатить через Tonkeeper", "url": tonkeeper_url}]
        ]
        
        # Добавляем кнопку для CryptoBot, если включено
        #if cryptobot_url:
            #buttons.append([{"text": f"{Emoji.WALLET} Оплатить через CryptoBot", "url": cryptobot_url}])
        
        # Если баннер включен - отправляем с картинкой
        if self.config["USE_BANNER"]:
            banner_url = self.config["BANNER_URL"]
            
            await message.client.send_file(
                message.chat_id,
                banner_url,
                caption=payment_message,
                reply_to=message.reply_to_msg_id,
                buttons=buttons
            )
            
            # Удаляем исходное сообщение с командой
            if message.out:
                await message.delete()
        else:
            # Если баннер отключен - отправляем обычное сообщение
            await self.inline.form(
                message=message,
                text=payment_message,
                reply_markup=buttons
            )

    @loader.command()
    async def dtoncfg(self, message):
        """— настроить модуль TonDonate"""
        await self.allmodules.commands["config"](
            await utils.answer(message, f"{self.get_prefix()}config {self.strings['name']}")
        )
