# meta developer: @sunshinelzt

from .. import loader, utils
import re
import urllib.parse

@loader.tds
class TonDonate(loader.Module):
    """Создает платежные ссылки для криптовалюты TON"""
    
    strings = {
        "name": "TonDonate",
        "no_wallet": "<b>⚠️ Ошибка!</b>\n\n<i>Вы не указали адрес кошелька в настройках модуля.</i>",
        "invalid_args": "<b>❌ Неверные аргументы!</b>\n\n<i>Используйте формат:</i>\n<code>.dton текст | сумма | комментарий | баннер</code>\n\n<i>Обязательным является только параметр суммы.</i>",
        "negative_amount": "<b>❌ Некорректная сумма!</b>\n\n<i>Сумма перевода должна быть больше нуля.</i>",
        "provide_amount": "<b>⚠️ Недостаточно данных!</b>\n\n<i>Пожалуйста, укажите хотя бы сумму перевода.</i>",
        "payment_created": "<b>💎 Toncoin | Платёжная ссылка</b>\n\n<i>✅ Успешно создана ссылка для оплаты <b>{} TON</b></i>",
        "payment_button": "💳 Оплатить через TON",
        "invalid_banner_url": "<b>⚠️ Предупреждение!</b>\n\n<i>Указанная ссылка на баннер некорректна. Будет использован стандартный формат без баннера.</i>"
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            "wallet_address", None, "Введите адрес вашего TON кошелька",
            "default_banner_url", None, "Ссылка на изображение или видео для баннера (опционально)"
        )

    @loader.command()
    async def dton(self, message):
        """Создать платежную ссылку TON - текст | сумма | комментарий"""
        args = utils.get_args_raw(message)
        wallet = self.config["wallet_address"]
        
        if not wallet:
            return await utils.answer(message, self.strings["no_wallet"])
            
        if not args:
            return await utils.answer(message, self.strings["provide_amount"])
            
        text, amount, comment, banner_url = None, None, None, None
        
        if "|" in args:
            parts = [part.strip() for part in args.split("|", 3)]
            
            if len(parts) >= 1:
                text = parts[0] or None
                
            if len(parts) >= 2:
                amount = parts[1]
                
            if len(parts) >= 3:
                comment = parts[2] or None
                
            if len(parts) == 4:
                banner_url = parts[3] or None
        else:
            amount = args.strip()
            
        if not banner_url:
            banner_url = self.config["default_banner_url"]
            
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
            text = self.strings["payment_created"].format(amount_float)
        else:
            payment_info = f"<b>💎 Toncoin | Оплата</b>\n\n{text}\n\n<i>Сумма: <b>{amount_float} TON</b></i>"
            if comment:
                payment_info += f"\n<i>Комментарий: <b>{comment}</b></i>"
            text = payment_info
        
        markup = [
            [{"text": self.strings["payment_button"], "url": url}]
        ]
        
        if banner_url:
            try:
                if not banner_url.startswith(("http://", "https://")):
                    raise ValueError("Invalid URL")
                
                banner_type = "photo"
                if any(banner_url.lower().endswith(ext) for ext in ['.mp4', '.avi', '.mov', '.mkv', '.webm']):
                    banner_type = "video"
                
                await self.inline.form(
                    message=message,
                    text=text,
                    reply_markup=markup,
                    **{banner_type: banner_url}
                )
            except Exception:
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
