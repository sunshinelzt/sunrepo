# членикииипенис

import asyncio
import aiohttp
import logging
from typing import Optional, Dict, Any, Tuple
from telethon.tl.types import Message

from .. import loader, utils


@loader.tds
class LolzTransferMod(loader.Module):
    """💰 Продвинутый модуль безопасных переводов Lolz.live"""

    strings = {
        "name": "LolzTransfer",
        "transfer_header": "💸 <b>Безопасный перевод средств</b>",
        "config_api_token": "🔑 API токен Lolz.live",
        "config_secret_phrase": "🔐 Секретная фраза для переводов",
        "transfer_confirm": (
            "🔔 <b>Подтверждение перевода:</b>\n\n"
            "• Сумма: <code>{amount}</code> руб.\n"
            "• Получатель: {user_link}\n"
            "• Комментарий: <code>{comment}</code>\n\n"
            "⚠️ Тщательно проверьте данные!"
        ),
        "transfer_success": (
            "✅ <b>Перевод выполнен!</b>\n\n"
            "• Сумма: <code>{amount}</code> руб.\n"
            "• Получатель: {user_link}\n"
            "• Комментарий: <code>{comment}</code>"
        ),
        "transfer_failed": "❌ <b>Ошибка перевода:</b> {error}",
        "user_not_found": "🔍 Пользователь <code>{username}</code> не найден",
        "invalid_amount": "❗ Некорректная сумма. Введите положительное число.",
        "missing_arguments": "❓ Формат: <code>.transfer &lt;ник&gt; &lt;сумма&gt; [комментарий]</code>",
        "no_config": "❌ Настройте API токен и секретную фразу в конфиге!",
        "operation_cancelled": "🚫 Операция отменена пользователем"
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "api_token", 
                None, 
                doc=lambda: self.strings["config_api_token"],
                validator=loader.validators.String()
            ),
            loader.ConfigValue(
                "secret_phrase", 
                None, 
                doc=lambda: self.strings["config_secret_phrase"],
                validator=loader.validators.String()
            ),
            loader.ConfigValue(
                "hold", 
                0, 
                doc="Время холда в днях",
                validator=loader.validators.Integer(minimum=0)
            ),
            loader.ConfigValue(
                "banner_url",
                None,
                doc="URL баннера для формы перевода",
                validator=loader.validators.String()
            )
        )
        self._cache = {}
        self._pending_transfers = {}
        self._logger = logging.getLogger(__name__)

    async def client_ready(self, client, db):
        self._client = client
        self._db = db
        
        # Правильный способ получения inline менеджера в Hikka
        self.inline = self.allmodules.get_module("InlineManager")

    async def _validate_config(self) -> bool:
        """Проверка конфигурации"""
        return bool(self.config['api_token'] and self.config['secret_phrase'])

    async def _get_user_info(self, username: str) -> Optional[Dict[str, Any]]:
        """Получение информации о пользователе по никнейму через API Lolz"""
        if not await self._validate_config():
            return None

        # Используем кэш, если есть
        cache_key = f"username_{username.lower()}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            headers = {"Authorization": f"Bearer {self.config['api_token']}"}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"https://api.lolz.live/users/find?username={username}", 
                    headers=headers,
                    timeout=10
                ) as response:
                    if response.status != 200:
                        self._logger.error(f"API error: {response.status}")
                        return None
                        
                    data = await response.json()
                    users = data.get("users", [])
                    
                    matching_users = [
                        user for user in users 
                        if user["username"].lower() == username.lower()
                    ]
                    
                    user = matching_users[0] if matching_users else None
                    
                    if user:
                        # Сохраняем в кэш
                        self._cache[cache_key] = user
                        self._cache[f"user_id_{user['user_id']}"] = user
                        
                    return user
        except Exception as e:
            self._logger.error(f"Error fetching user info: {e}")
            return None

    async def _send_transfer(
        self, 
        user_id: str, 
        amount: float, 
        comment: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """Выполнение перевода через API Lolz.live согласно документации"""
        if not await self._validate_config():
            return False, {"error": "Не настроены API токен и секретная фраза"}

        try:
            headers = {"Authorization": f"Bearer {self.config['api_token']}"}
            payload = {
                "user_id": user_id,
                "amount": amount,
                "secret_phrase": self.config["secret_phrase"],
                "hold": self.config.get("hold", 0),
                "comment": comment
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.lolz.live/market/pay", 
                    json=payload, 
                    headers=headers,
                    timeout=15
                ) as response:
                    result = await response.json()
                    return result.get("success", False), result
        except Exception as e:
            self._logger.error(f"Error sending transfer: {e}")
            return False, {"error": f"Ошибка при выполнении запроса: {str(e)}"}

    @loader.command(ru_doc="Перевести средства пользователю")
    async def transfercmd(self, message: Message):
        """Инициировать безопасный перевод: .transfer <ник> <сумма> [комментарий]"""
        if not await self._validate_config():
            await utils.answer(message, self.strings["no_config"])
            return

        args = utils.get_args_raw(message).split(maxsplit=2)
        if len(args) < 2:
            await utils.answer(message, self.strings["missing_arguments"])
            return

        username, amount_str, *comment_parts = args
        comment = comment_parts[0] if comment_parts else "Без комментария"

        try:
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError
        except ValueError:
            await utils.answer(message, self.strings["invalid_amount"])
            return

        user_info = await self._get_user_info(username)
        if not user_info:
            await utils.answer(
                message, 
                self.strings["user_not_found"].format(username=username)
            )
            return

        user_id = user_info["user_id"]
        username = user_info["username"]  # Используем точный никнейм
        user_link = f"<a href='https://lolz.live/members/{user_id}/'>{username}</a>"

        # Генерируем уникальный ID для перевода
        transfer_id = utils.rand(16)
        
        # Сохраняем данные о переводе
        self._pending_transfers[transfer_id] = {
            "user_id": user_id,
            "amount": amount,
            "comment": comment,
            "username": username
        }

        # Формируем текст для подтверждения
        confirm_text = self.strings["transfer_confirm"].format(
            amount=f"{amount:.2f}",
            user_link=user_link,
            comment=comment
        )

        # Создаем инлайн-форму с кнопками в соответствии с вашим примером
        if self.config["banner_url"] is None:
            await self.inline.form(
                message=message,
                text=confirm_text,
                reply_markup=[
                    [
                        {"text": "✅ Подтвердить", "callback": self._confirm_transfer, "args": (transfer_id,)},
                        {"text": "❌ Отмена", "callback": self._cancel_transfer, "args": (transfer_id,)},
                    ],
                    [
                        {"text": "🔻 Закрыть", "callback": self._delete_form}  
                    ],
                ],
            )
        else:
            await self.inline.form(
                message=message,
                text=confirm_text,
                photo=self.config["banner_url"],
                reply_markup=[
                    [
                        {"text": "✅ Подтвердить", "callback": self._confirm_transfer, "args": (transfer_id,)},
                        {"text": "❌ Отмена", "callback": self._cancel_transfer, "args": (transfer_id,)},
                    ],
                    [
                        {"text": "🔻 Закрыть", "callback": self._delete_form}  
                    ],
                ],
            )

    async def _confirm_transfer(self, call, transfer_id):
        """Обработчик подтверждения перевода"""
        if transfer_id not in self._pending_transfers:
            await call.edit(
                text=self.strings["transfer_failed"].format(error="Перевод не найден или устарел")
            )
            return

        transfer_data = self._pending_transfers[transfer_id]
        user_id = transfer_data["user_id"]
        amount = transfer_data["amount"]
        comment = transfer_data["comment"]
        username = transfer_data["username"]
        
        user_link = f"<a href='https://lolz.live/members/{user_id}/'>{username}</a>"

        # Выполняем перевод
        success, result = await self._send_transfer(user_id, amount, comment)

        if success:
            await call.edit(
                text=self.strings["transfer_success"].format(
                    amount=f"{amount:.2f}",
                    user_link=user_link,
                    comment=comment
                )
            )
        else:
            error_msg = result.get("error", "Неизвестная ошибка")
            self._logger.error(f"Transfer failed: {error_msg}")
            await call.edit(
                text=self.strings["transfer_failed"].format(error=error_msg)
            )

        # Удаляем данные о переводе
        del self._pending_transfers[transfer_id]

    async def _cancel_transfer(self, call, transfer_id):
        """Обработчик отмены перевода"""
        if transfer_id in self._pending_transfers:
            del self._pending_transfers[transfer_id]
        
        await call.edit(text=self.strings["operation_cancelled"])
        
    async def _delete_form(self, call):
        """Обработчик закрытия формы"""
        await call.delete()

    @loader.inline_handler(pattern="lolz_transfer")
    async def inline_handler(self, query):
        """Обработчик инлайн-запросов для переводов"""
        if not await self._validate_config():
            return await query.answer(
                [
                    {
                        "title": "❌ Модуль не настроен",
                        "description": "Нужно настроить API токен и секретную фразу",
                        "message": self.strings["no_config"],
                    }
                ],
                cache_time=0
            )

        # Парсим запрос: lolz_transfer username amount [comment]
        args = query.text.split()[1:] if len(query.text.split()) > 1 else []
        
        if len(args) < 2:
            return await query.answer(
                [
                    {
                        "title": "ℹ️ Помощь по использованию",
                        "description": "Формат: lolz_transfer <ник> <сумма> [комментарий]",
                        "message": self.strings["missing_arguments"],
                    }
                ],
                cache_time=0
            )

        username, amount_str, *comment_parts = args
        comment = " ".join(comment_parts) if comment_parts else "Без комментария"

        try:
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError
        except ValueError:
            return await query.answer(
                [
                    {
                        "title": "❗ Некорректная сумма",
                        "description": "Введите положительное число",
                        "message": self.strings["invalid_amount"],
                    }
                ],
                cache_time=0
            )

        # Получаем информацию о пользователе
        user_info = await self._get_user_info(username)
        
        if not user_info:
            return await query.answer(
                [
                    {
                        "title": "🔍 Пользователь не найден",
                        "description": f"Пользователь {username} не найден на Lolz.live",
                        "message": self.strings["user_not_found"].format(username=username),
                    }
                ],
                cache_time=0
            )

        user_id = user_info["user_id"]
        precise_username = user_info["username"]
        
        # Генерируем уникальный ID для перевода
        transfer_id = utils.rand(16)
        
        # Сохраняем данные о переводе
        self._pending_transfers[transfer_id] = {
            "user_id": user_id,
            "amount": amount,
            "comment": comment,
            "username": precise_username
        }

        # Создаем инлайн-результат с кнопками подтверждения/отмены
        user_link = f"<a href='https://lolz.live/members/{user_id}/'>{precise_username}</a>"
        
        text = self.strings["transfer_confirm"].format(
            amount=f"{amount:.2f}",
            user_link=user_link,
            comment=comment
        )

        # Правильное создание инлайн-кнопок для ответа
        return await query.answer(
            [
                {
                    "title": f"💸 Перевод {amount} руб. для {precise_username}",
                    "description": f"Комментарий: {comment}",
                    "message": text,
                    "reply_markup": [
                        [
                            {"text": "✅ Подтвердить", "callback": self._confirm_transfer, "args": (transfer_id,)},
                            {"text": "❌ Отмена", "callback": self._cancel_transfer, "args": (transfer_id,)},
                        ],
                        [
                            {"text": "🔻 Закрыть", "callback": self._delete_form}  
                        ],
                    ],
                }
            ],
            cache_time=0
        )
