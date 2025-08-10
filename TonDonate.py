# meta developer: @sunshinelzt

from .. import loader, utils
import urllib.parse
import logging
import re
import asyncio
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

@loader.tds
class TonDonate(loader.Module):
    """Создает платежные ссылки для криптовалюты TON"""
    
    strings = {
        "name": "TonDonate",
        "no_wallet": "⚠️ <b>Ошибка!</b>\n\n<i>Вы не указали адрес кошелька в настройках модуля.</i>",
        "invalid_args": (
            "❌ <b>Неверные аргументы!</b>\n\n"
            "<i>Используйте формат:</i>\n"
            "<code>.dton [текст] | сумма | [комментарий] | [баннер]</code>\n\n"
            "<b>Примеры:</b>\n"
            "<code>.dton 10</code> - простая оплата\n"
            "<code>.dton Поддержка проекта | 5.5 | Спасибо!</code>\n"
        ),
        "invalid_wallet": "❌ <b>Некорректный кошелек!</b>\n\n<i>Проверьте правильность адреса TON кошелька в настройках.</i>",
        "negative_amount": "❌ <b>Некорректная сумма!</b>\n\n<i>Сумма перевода должна быть больше нуля.</i>",
        "amount_too_large": "⚠️ <b>Слишком большая сумма!</b>\n\n<i>Максимальная сумма: 1,000,000 TON</i>",
        "provide_amount": "⚠️ <b>Недостаточно данных!</b>\n\n<i>Пожалуйста, укажите сумму перевода.</i>",
        "payment_created": "💎 <b>Toncoin | Платёжная ссылка</b>\n\n✅ <i>Успешно создана ссылка для оплаты</i> <b>{} TON</b>",
        "payment_button": "💳 Оплатить {} TON",

        "invalid_banner_url": (
            "⚠️ <b>Предупреждение!</b>\n\n"
            "<i>Указанная ссылка на баннер некорректна. Используется стандартный формат.</i>"
        ),
        "payment_info": "💎 <b>TON Платёж</b>\n\n{}\n\n💰 <b>Сумма:</b> {} TON\n👤 <b>Получатель:</b> <code>{}</code>",
        "with_comment": "\n💬 <b>Комментарий:</b> {}",
        "config_saved": "✅ <b>Настройки сохранены!</b>",

    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "wallet_address", 
                "", 
                "Введите адрес вашего TON кошелька (формат: UQ...)"
            ),
            loader.ConfigValue(
                "default_banner_url", 
                "", 
                "Ссылка на баннер по умолчанию (опционально)"
            ),

            loader.ConfigValue(
                "show_wallet_in_message",
                True,
                "Показывать адрес кошелька в сообщении",
                validator=loader.validators.Boolean()
            )
        )
        
    def _validate_ton_address(self, address: str) -> bool:
        """Валидация TON адреса"""
        if not address:
            return False
            
        ton_address_pattern = r'^[UE][Qf][A-Za-z0-9_-]{46}$'
        return bool(re.match(ton_address_pattern, address))

    def _parse_arguments(self, args_raw: str) -> Dict[str, Any]:
        """Улучшенный парсинг аргументов команды"""
        result = {
            "text": None,
            "amount": None,
            "comment": None,
            "banner_url": None
        }
        
        if not args_raw.strip():
            return result
            
        if "|" in args_raw:
            parts = [part.strip() for part in args_raw.split("|", 3)]
            
            for i, part in enumerate(parts):
                if not part:
                    continue
                    
                if i == 0:
                    result["text"] = part
                elif i == 1:
                    result["amount"] = part
                elif i == 2:
                    result["comment"] = part
                elif i == 3:
                    result["banner_url"] = part
        else:
            result["amount"] = args_raw.strip()
            
        return result

    def _detect_media_type(self, url: str) -> str:
        """Улучшенное определение типа медиа"""
        if not url:
            return "photo"
            
        url_lower = url.lower()
        
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.m4v', '.flv', '.wmv']
        if any(url_lower.endswith(ext) for ext in video_extensions):
            return "video"
            
        if url_lower.endswith('.gif'):
            return "animation"
            
        return "photo"

    def _validate_amount(self, amount_str: str) -> Optional[float]:
        """Валидация суммы"""
        if not amount_str:
            return None
            
        try:
            cleaned = amount_str.replace(",", ".").strip()
            amount = float(cleaned)
            
            if amount <= 0:
                return None
                
            return round(amount, 9)
        except (ValueError, TypeError):
            return None

    def _validate_url(self, url: str) -> bool:
        """Валидация URL"""
        if not url:
            return False
            
        url_pattern = re.compile(
            r'^https?://'
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
            r'localhost|'
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
            r'(?::\d+)?'
            r'(?:/?|[/?]\S+)$', re.IGNORECASE
        )
        return bool(url_pattern.match(url))

    def _create_payment_url(self, wallet: str, amount: float, comment: Optional[str] = None) -> str:
        """Создание URL для платежа с улучшенным форматированием"""
        nano_amount = int(amount * 1_000_000_000)
        
        base_url = f"ton://transfer/{wallet}"
        params = {"amount": str(nano_amount)}
        
        if comment:
            params["text"] = comment
            
        query_string = urllib.parse.urlencode(params)
        ton_url = f"{base_url}?{query_string}"
        
        web_url = f"https://app.tonkeeper.com/transfer/{wallet}?amount={nano_amount}"
        if comment:
            web_url += f"&text={urllib.parse.quote(comment)}"
            
        return web_url

    def _format_message(self, text: Optional[str], amount: float, wallet: str, comment: Optional[str] = None) -> str:
        """Улучшенное форматирование сообщения"""
        if text:
            message = self.strings["payment_info"].format(text, amount, wallet[:8] + "..." + wallet[-8:])
        else:
            message = self.strings["payment_created"].format(amount)
            
        if comment:
            message += self.strings["with_comment"].format(comment)
            
        if self.config["show_wallet_in_message"] and not text:
            message += f"\n\n👤 <b>Адрес:</b> <code>{wallet}</code>"
            
        return message



    @loader.command()
    async def dton(self, message):
        """Создать платежную ссылку TON - [текст] | сумма | [комментарий]"""
        args_raw = utils.get_args_raw(message)
        wallet = self.config["wallet_address"]
        
        if not wallet:
            return await utils.answer(message, self.strings["no_wallet"])
            
        if not self._validate_ton_address(wallet):
            return await utils.answer(message, self.strings["invalid_wallet"])
            
        if not args_raw:
            return await utils.answer(message, self.strings["provide_amount"])
            
        parsed_args = self._parse_arguments(args_raw)
        
        if not parsed_args["amount"]:
            return await utils.answer(message, self.strings["provide_amount"])
            
        amount = self._validate_amount(parsed_args["amount"])
        if amount is None:
            return await utils.answer(message, self.strings["negative_amount"])
            
        payment_url = self._create_payment_url(wallet, amount, parsed_args["comment"])
        
        banner_url = self.config["default_banner_url"]
        
        message_text = self._format_message(parsed_args["text"], amount, wallet, parsed_args["comment"])
        
        await self._send_payment_form(message, message_text, payment_url, banner_url, amount)

    async def _send_payment_form(self, message, text: str, payment_url: str, banner_url: Optional[str] = None, amount: float = 0):
        """Улучшенная отправка формы с платежной ссылкой"""
        markup = [
            [{"text": self.strings["payment_button"].format(amount), "url": payment_url}]
        ]
        
        form_params = {
            "message": message,
            "text": text,
            "reply_markup": markup
        }
        
        if banner_url and banner_url.strip():
            try:
                if self._validate_url(banner_url):
                    media_type = self._detect_media_type(banner_url)
                    form_params[media_type] = banner_url
                    await self.inline.form(**form_params)
                else:
                    raise ValueError("Invalid URL format")
                    
            except Exception as e:
                logger.warning(f"Ошибка с баннером: {e}")
                
                try:
                    await utils.answer(message, self.strings["invalid_banner_url"])
                    await asyncio.sleep(2)
                except:
                    pass
                    
                for media_key in ["photo", "video", "animation"]:
                    form_params.pop(media_key, None)
                await self.inline.form(**form_params)
        else:
            await self.inline.form(**form_params)
