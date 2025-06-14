# meta developer: @sunshinelzt

from .. import loader, utils
import urllib.parse
import logging
from typing import Optional

logger = logging.getLogger(__name__)

@loader.tds
class TonDonate(loader.Module):
    """Создает платежные ссылки для криптовалюты TON"""
    
    strings = {
        "name": "TonDonate",
        "no_wallet": "<b>⚠️ Ошибка!</b>\n\n<i>Вы не указали адрес кошелька в настройках модуля.</i>",
        "invalid_args": (
            "<b>❌ Неверные аргументы!</b>\n\n"
            "<i>Используйте формат:</i>\n"
            "<code>.dton [текст] | сумма | [комментарий] | [баннер]</code>\n\n"
            "<i>Обязательным является только параметр суммы.</i>"
        ),
        "negative_amount": "<b>❌ Некорректная сумма!</b>\n\n<i>Сумма перевода должна быть больше нуля.</i>",
        "provide_amount": "<b>⚠️ Недостаточно данных!</b>\n\n<i>Пожалуйста, укажите хотя бы сумму перевода.</i>",
        "payment_created": "<b>💎 Toncoin | Платёжная ссылка</b>\n\n<i>✅ Успешно создана ссылка для оплаты <b>{} TON</b></i>",
        "payment_button": "💳 Оплатить через TON",
        "invalid_banner_url": (
            "<b>⚠️ Предупреждение!</b>\n\n"
            "<i>Указанная ссылка на баннер некорректна. Будет использован стандартный формат без баннера.</i>"
        )
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "wallet_address", 
                "", 
                "Введите адрес вашего TON кошелька"
            ),
            loader.ConfigValue(
                "default_banner_url", 
                "", 
                "Ссылка на баннер по умолчанию (опционально)"
            )
        )

    def _parse_arguments(self, args_raw: str) -> dict:
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
            
            if len(parts) >= 1 and parts[0]:
                result["text"] = parts[0]
                
            if len(parts) >= 2:
                result["amount"] = parts[1]
                
            if len(parts) >= 3 and parts[2]:
                result["comment"] = parts[2]
                
            if len(parts) >= 4 and parts[3]:
                result["banner_url"] = parts[3]
        else:
            result["amount"] = args_raw.strip()
            
        return result

    def _detect_banner_type(self, url: str) -> str:
        """Определение типа баннера по URL"""
        if not url:
            return "photo"
            
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.gif']
        if any(url.lower().endswith(ext) for ext in video_extensions):
            return "video"
        return "photo"

    def _validate_amount(self, amount_str: str) -> Optional[float]:
        """Валидация суммы"""
        try:
            amount = float(amount_str)
            return amount if amount > 0 else None
        except (ValueError, TypeError):
            return None

    def _create_payment_url(self, wallet: str, amount: float, comment: Optional[str] = None) -> str:
        """Создание URL для платежа"""
        nano_amount = int(amount * 1_000_000_000)
        url = f"https://app.tonkeeper.com/transfer/{wallet}?amount={nano_amount}"
        
        if comment:
            url += f"&text={urllib.parse.quote(comment)}"
            
        return url

    def _format_message(self, text: Optional[str], amount: float, comment: Optional[str]) -> str:
        """Форматирование сообщения"""
        if not text:
            return self.strings["payment_created"].format(amount)
        
        message = f"<b>💎 Toncoin | Оплата</b>\n\n{text}\n\n<i>Сумма: <b>{amount} TON</b></i>"
        
        if comment:
            message += f"\n<i>Комментарий: <b>{comment}</b></i>"
            
        return message

    @loader.command()
    async def dton(self, message):
        """Создать платежную ссылку TON - [текст] | сумма | [комментарий] | [баннер]"""
        args_raw = utils.get_args_raw(message)
        wallet = self.config["wallet_address"]
        
        # Проверка кошелька
        if not wallet:
            return await utils.answer(message, self.strings["no_wallet"])
            
        if not args_raw:
            return await utils.answer(message, self.strings["provide_amount"])
            
        # Парсинг аргументов
        parsed_args = self._parse_arguments(args_raw)
        
        if not parsed_args["amount"]:
            return await utils.answer(message, self.strings["provide_amount"])
            
        # Валидация суммы
        amount = self._validate_amount(parsed_args["amount"])
        if amount is None:
            return await utils.answer(message, self.strings["negative_amount"])
            
        # Создание URL платежа
        payment_url = self._create_payment_url(wallet, amount, parsed_args["comment"])
        
        # Определение баннера
        banner_url = parsed_args["banner_url"] or self.config["default_banner_url"]
        
        # Форматирование сообщения
        message_text = self._format_message(parsed_args["text"], amount, parsed_args["comment"])
        
        # Отправка формы
        await self._send_payment_form(message, message_text, payment_url, banner_url)

    async def _send_payment_form(self, message, text: str, payment_url: str, banner_url: Optional[str] = None):
        """Отправка формы с платежной ссылкой"""
        markup = [
            [{"text": self.strings["payment_button"], "url": payment_url}]
        ]
        
        form_params = {
            "message": message,
            "text": text,
            "reply_markup": markup
        }
        
        if banner_url and banner_url.strip():
            try:
                # Проверка URL
                if banner_url.startswith(("http://", "https://")):
                    banner_type = self._detect_banner_type(banner_url)
                    form_params[banner_type] = banner_url
                    
                    await self.inline.form(**form_params)
                else:
                    raise ValueError("Invalid URL format")
                    
            except Exception as e:
                logger.error(f"Error with banner: {e}")
                await utils.answer(message, self.strings["invalid_banner_url"])
                
                # Отправка без баннера
                form_params.pop("photo", None)
                form_params.pop("video", None)
                await self.inline.form(**form_params)
        else:
            await self.inline.form(**form_params)
