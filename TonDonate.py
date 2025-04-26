# meta developer: @sunshinelzt

from .. import loader, utils
import urllib.parse
import logging

logger = logging.getLogger(__name__)

@loader.tds
class TonDonate(loader.Module):
    """Создает платежные ссылки для криптовалюты TON"""
    
    strings = {
        "name": "TonDonate",
        "no_wallet": "<b>⚠️ Ошибка!</b>\n\n<i>Вы не указали адрес кошелька в настройках модуля.</i>",
        "invalid_args": "<b>❌ Неверные аргументы!</b>\n\n<i>Используйте формат:</i>\n<code>.dton [текст] | сумма | [комментарий] | [баннер]</code>\n\n<i>Обязательным является только параметр суммы.</i>",
        "negative_amount": "<b>❌ Некорректная сумма!</b>\n\n<i>Сумма перевода должна быть больше нуля.</i>",
        "provide_amount": "<b>⚠️ Недостаточно данных!</b>\n\n<i>Пожалуйста, укажите хотя бы сумму перевода.</i>",
        "payment_created": "<b>💎 Toncoin | Платёжная ссылка</b>\n\n<i>✅ Успешно создана ссылка для оплаты <b>{} TON</b></i>",
        "payment_button": "💳 Оплатить через TON",
        "invalid_banner_url": "<b>⚠️ Предупреждение!</b>\n\n<i>Указанная ссылка на баннер некорректна. Будет использован стандартный формат без баннера.</i>"
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            "wallet_address", None, "Введите адрес вашего TON кошелька",
            "default_banner_url", None, "Ссылка на баннер (опционально)"
        )

    def _parse_arguments(self, args_raw):
        """Парсинг аргументов команды"""
        result = {
            "text": None,
            "amount": None,
            "comment": None,
            "banner_url": None
        }
        
        if not args_raw:
            return result
            
        if "|" in args_raw:
            parts = [part.strip() for part in args_raw.split("|", 3)]
            
            parts_count = len(parts)
            
            if parts_count >= 1:
                result["text"] = parts[0] if parts[0] else None
                
            if parts_count >= 2:
                result["amount"] = parts[1]
                
            if parts_count >= 3:
                result["comment"] = parts[2] if parts[2] else None
                
            if parts_count >= 4:
                result["banner_url"] = parts[3] if parts[3] else None
        else:
            result["amount"] = args_raw.strip()
            
        return result

    def _detect_banner_type(self, url):
        """Определение типа баннера по URL"""
        if not url:
            return None
            
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.gif']
        if any(url.lower().endswith(ext) for ext in video_extensions):
            return "video"
        return "photo"

    @loader.command()
    async def dton(self, message):
        """Создать платежную ссылку TON - [текст] | сумма | [комментарий] | [баннер]"""
        args = utils.get_args_raw(message)
        wallet = self.config["WALLET_ADDRESS"]
        
        if not wallet:
            return await utils.answer(message, self.strings["no_wallet"])
            
        if not args:
            return await utils.answer(message, self.strings["provide_amount"])
            
        parsed_args = self._parse_arguments(args)
        text = parsed_args["text"]
        amount = parsed_args["amount"]
        comment = parsed_args["comment"]
        banner_url = parsed_args["banner_url"] or self.config["DEFAULT_BANNER_URL"]
            
        try:
            amount_float = float(amount)
            if amount_float <= 0:
                return await utils.answer(message, self.strings["negative_amount"])
        except (ValueError, TypeError):
            return await utils.answer(message, self.strings["invalid_args"])
            
        nano_amount = int(amount_float * 1_000_000_000)
        
        url = f"https://app.tonkeeper.com/transfer/{wallet}?amount={nano_amount}"
        if comment:
            url += f"&text={urllib.parse.quote(comment)}"
        
        if not text:
            message_text = self.strings["payment_created"].format(amount_float)
        else:
            message_text = f"<b>💎 Toncoin | Оплата</b>\n\n{text}\n\n<i>Сумма: <b>{amount_float} TON</b></i>"
            if comment:
                message_text += f"\n<i>Комментарий: <b>{comment}</b></i>"
        
        await self._send_payment_form(message, message_text, url, banner_url)
    
    async def _send_payment_form(self, message, text, payment_url, banner_url=None):
        """Отправка формы с платежной ссылкой и баннером"""
        markup = [
            [{"text": self.strings["payment_button"], "url": payment_url}]
        ]
        
        if banner_url:
            try:
                if not banner_url.startswith(("http://", "https://")):
                    raise ValueError("Invalid URL format")
                
                banner_type = self._detect_banner_type(banner_url)
                
                await self.inline.form(
                    message=message,
                    text=text,
                    reply_markup=markup,
                    **{banner_type: banner_url}
                )
            except Exception as e:
                logger.error(f"Error with banner: {e}")
                await utils.answer(message, self.strings["invalid_banner_url"])
                await self.inline.form(
                    message=message,
                    text=text,
                    reply_markup=markup
                )
        else:
            await self.inline.form(
                message=message,
                text=text,
                reply_markup=markup
            )
