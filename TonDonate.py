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
            "<code>.dton [текст] | сумма | [комментарий]</code>\n\n"
            "<b>Примеры:</b>\n"
            "<code>.dton 10</code> - простая оплата\n"
            "<code>.dton Поддержка проекта | 5.5 | Спасибо!</code>\n"
        ),
        "invalid_wallet": "❌ <b>Некорректный кошелек!</b>\n\n<i>Проверьте правильность адреса TON кошелька в настройках.</i>",
        "negative_amount": "❌ <b>Некорректная сумма!</b>\n\n<i>Сумма перевода должна быть больше нуля.</i>",
        "provide_amount": "⚠️ <b>Недостаточно данных!</b>\n\n<i>Пожалуйста, укажите сумму перевода.</i>",
        "payment_created": "💎 <b>Toncoin | Платёжная ссылка</b>\n\n✅ <i>Успешно создана ссылка для оплаты</i> <b>{} TON</b>",
        "payment_button": "💳 Оплатить {} TON",
        "banner_loading_error": "⚠️ <i>Не удалось загрузить баннер, используется текстовый формат</i>",
        "payment_info": "💎 <b>TON Платёж</b>\n\n{}\n\n💰 <b>Сумма:</b> {} TON",
        "with_comment": "\n💬 <b>Комментарий:</b> {}",
        "processing": "⏳ <i>Создание платежной ссылки...</i>",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "wallet_address", 
                "", 
                "Введите адрес вашего TON кошелька (формат: UQ... или EQ...)"
            ),
            loader.ConfigValue(
                "default_banner_url", 
                "", 
                "Ссылка на баннер по умолчанию (опционально)"
            )
        )
        
    def _validate_ton_address(self, address: str) -> bool:
        """Валидация TON адреса"""
        if not address or not isinstance(address, str):
            return False
            
        address = address.strip()
        
        # Базовая проверка формата TON адреса
        ton_address_pattern = r'^[UE][Qf][A-Za-z0-9_-]{46}$'
        if not re.match(ton_address_pattern, address):
            return False
            
        # Проверка на валидные символы base64url
        valid_chars = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-')
        b64_part = address[2:]
        
        return all(char in valid_chars for char in b64_part)

    def _parse_arguments(self, args_raw: str) -> Dict[str, Any]:
        """Парсинг аргументов команды"""
        result = {
            "text": None,
            "amount": None,
            "comment": None
        }
        
        if not args_raw.strip():
            return result
            
        if "|" in args_raw:
            parts = [part.strip() for part in args_raw.split("|", 2)]
            
            for i, part in enumerate(parts):
                if not part:
                    continue
                    
                if i == 0:
                    result["text"] = part
                elif i == 1:
                    result["amount"] = part
                elif i == 2:
                    result["comment"] = part
        else:
            # Если нет разделителей, считаем что это сумма
            result["amount"] = args_raw.strip()
            
        return result

    def _validate_amount(self, amount_str: str) -> Optional[float]:
        """Валидация суммы"""
        if not amount_str:
            return None
            
        try:
            # Заменяем запятые на точки и убираем лишние пробелы
            cleaned = amount_str.replace(",", ".").strip()
            amount = float(cleaned)
            
            if amount <= 0:
                return None
                
            # Округляем до 9 знаков после запятой (максимальная точность TON)
            return round(amount, 9)
        except (ValueError, TypeError):
            return None

    def _validate_url(self, url: str) -> bool:
        """Валидация URL для баннера"""
        if not url or not isinstance(url, str):
            return False
            
        url = url.strip()
        
        # Простая проверка URL
        url_pattern = re.compile(
            r'^https?://'
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
            r'localhost|'
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
            r'(?::\d+)?'
            r'(?:/?|[/?]\S+)$', re.IGNORECASE
        )
        return bool(url_pattern.match(url))

    def _detect_media_type(self, url: str) -> str:
        """Определение типа медиа по URL"""
        if not url:
            return "photo"
            
        url_lower = url.lower()
        
        # Видео форматы
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.m4v', '.flv', '.wmv']
        if any(url_lower.endswith(ext) for ext in video_extensions):
            return "video"
            
        # GIF анимации
        if url_lower.endswith('.gif'):
            return "animation"
            
        # По умолчанию фото
        return "photo"

    def _create_payment_url(self, wallet: str, amount: float, comment: Optional[str] = None) -> str:
        """Создание URL для платежа"""
        # Конвертируем TON в nanoton (1 TON = 1,000,000,000 nanoton)
        nano_amount = int(amount * 1_000_000_000)
        
        # Создаем web URL для Tonkeeper
        web_url = f"https://app.tonkeeper.com/transfer/{wallet}?amount={nano_amount}"
        
        if comment:
            encoded_comment = urllib.parse.quote(comment, safe='')
            web_url += f"&text={encoded_comment}"
            
        return web_url

    def _format_message(self, text: Optional[str], amount: float, comment: Optional[str] = None) -> str:
        """Форматирование сообщения"""
        if text:
            message = self.strings["payment_info"].format(text, amount)
        else:
            message = self.strings["payment_created"].format(amount)
            
        if comment:
            message += self.strings["with_comment"].format(comment)
            
        return message

    async def _send_payment_form(self, message, text: str, payment_url: str, banner_url: Optional[str] = None, amount: float = 0):
        """Отправка формы с платежной ссылкой"""
        markup = [
            [{"text": self.strings["payment_button"].format(amount), "url": payment_url}]
        ]
        
        form_params = {
            "message": message,
            "text": text,
            "reply_markup": markup
        }
        
        # Обработка баннера
        if banner_url and banner_url.strip():
            try:
                if self._validate_url(banner_url):
                    media_type = self._detect_media_type(banner_url)
                    form_params[media_type] = banner_url
                    
                    # Пытаемся отправить с баннером
                    await self.inline.form(**form_params)
                    return
                else:
                    logger.warning(f"Невалидный URL баннера: {banner_url}")
                    
            except Exception as e:
                logger.error(f"Ошибка при загрузке баннера {banner_url}: {e}")
                
                # Показываем предупреждение о проблеме с баннером
                try:
                    await utils.answer(message, self.strings["banner_loading_error"])
                    await asyncio.sleep(1)
                except Exception:
                    pass
        
        # Отправляем без баннера
        await self.inline.form(**form_params)

    @loader.command()
    async def dton(self, message):
        """Создать платежную ссылку TON - [текст] | сумма | [комментарий]"""
        args_raw = utils.get_args_raw(message)
        wallet = self.config["wallet_address"]
        
        # Проверяем наличие кошелька
        if not wallet:
            return await utils.answer(message, self.strings["no_wallet"])
            
        # Валидируем адрес кошелька
        if not self._validate_ton_address(wallet):
            return await utils.answer(message, self.strings["invalid_wallet"])
            
        # Проверяем наличие аргументов
        if not args_raw:
            return await utils.answer(message, self.strings["provide_amount"])
        
        # Показываем индикатор обработки
        processing_msg = await utils.answer(message, self.strings["processing"])
        
        try:
            # Парсим аргументы
            parsed_args = self._parse_arguments(args_raw)
            
            # Проверяем наличие суммы
            if not parsed_args["amount"]:
                return await utils.answer(message, self.strings["provide_amount"])
                
            # Валидируем сумму
            amount = self._validate_amount(parsed_args["amount"])
            if amount is None:
                return await utils.answer(message, self.strings["negative_amount"])
                
            # Создаем платежную ссылку
            payment_url = self._create_payment_url(wallet, amount, parsed_args["comment"])
            
            # Получаем URL баннера
            banner_url = self.config["default_banner_url"]
            
            # Форматируем сообщение
            message_text = self._format_message(parsed_args["text"], amount, parsed_args["comment"])
            
            # Удаляем сообщение о процессе
            try:
                await processing_msg.delete()
            except Exception:
                pass
            
            # Отправляем форму с платежной ссылкой
            await self._send_payment_form(message, message_text, payment_url, banner_url, amount)
            
        except Exception as e:
            logger.error(f"Ошибка при создании платежной ссылки: {e}")
            try:
                await processing_msg.delete()
            except Exception:
                pass
            await utils.answer(message, "❌ <b>Произошла ошибка при создании платежной ссылки</b>")
