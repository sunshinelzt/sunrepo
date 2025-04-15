# -*- coding: utf-8 -*-
# Module by @sunshinelzt
# Licensed under GNU GPL-3.0

# meta developer: @sunshinelzt

__version__ = (1, 0, 0)

import asyncio
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Union

import aiohttp
import requests
from telethon.tl.custom import Message
from telethon.tl.types import Message as TLMessage

from .. import loader, utils
from ..inline.types import InlineCall, InlineQuery
from ..inline.utils import answer

logger = logging.getLogger(__name__)

CURRENCIES = ["rub", "uah", "kzt", "byn", "usd", "eur", "gbp", "cny", "try", "jpy", "brl"]


@loader.tds
class LolzMarketMod(loader.Module):
    """Модуль для интеграции с API Lolz.live Market"""

    strings = {
        "name": "LolzMarket",
        "cfg_api_key": "Ваш API ключ от Lolz.live",
        "cfg_merchant_id": "ID вашего мерчанта на Lolz.live",
        "cfg_success_url": "URL для перенаправления после успешной оплаты",
        "cfg_callback_url": "URL для получения уведомлений о платежах (опционально)",
        "no_api_key": "<emoji document_id=5312526098750252863>❌</emoji> <b>Не указан API ключ!</b>\nУкажите его в конфиге командой <code>.config LolzMarket</code>",
        "no_merchant_id": "<emoji document_id=5312526098750252863>❌</emoji> <b>Не указан ID мерчанта!</b>\nУкажите его в конфиге",
        "invoice_created": "<emoji document_id=5472111548572900003>✅</emoji> <b>Инвойс успешно создан!</b>\n\n<b>Сумма:</b> {amount} {currency}\n<b>ID платежа:</b> {payment_id}\n<b>Время действия:</b> {lifetime} сек.\n\n<b>URL для оплаты:</b> {url}",
        "create_invoice": "🧾 Создать инвойс",
        "select_currency": "💰 Выберите валюту",
        "enter_amount": "<emoji document_id=5431376038628171216>💸</emoji> <b>Введите сумму платежа:</b>",
        "enter_payment_id": "<emoji document_id=5467666648263564704>🔢</emoji> <b>Введите ID платежа (уникальный идентификатор):</b>",
        "enter_comment": "<emoji document_id=5467690926894759285>✏️</emoji> <b>Введите комментарий к платежу:</b>",
        "enter_lifetime": "<emoji document_id=5467939548632599747>⏲</emoji> <b>Введите время жизни инвойса (в секундах, от 300 до 43200):</b>",
        "default_lifetime": "3600",
        "enter_additional_data": "<emoji document_id=5467829766610921936>📝</emoji> <b>Введите дополнительную информацию (опционально):</b>\n<i>Нажмите 'Пропустить', если не требуется</i>",
        "skip": "Пропустить",
        "invalid_amount": "<emoji document_id=5312526098750252863>❌</emoji> <b>Неверная сумма! Введите положительное число.</b>",
        "invalid_lifetime": "<emoji document_id=5312526098750252863>❌</emoji> <b>Неверное время жизни! Введите число от 300 до 43200.</b>",
        "api_error": "<emoji document_id=5312526098750252863>❌</emoji> <b>Ошибка API Lolz.live:</b>\n{error}",
        "processing": "<emoji document_id=5213452215527677338>⏳</emoji> <b>Обработка запроса...</b>",
        "confirm_invoice": "<emoji document_id=5467829766610921936>📝</emoji> <b>Подтвердите создание инвойса:</b>\n\n<b>Валюта:</b> {currency}\n<b>Сумма:</b> {amount}\n<b>ID платежа:</b> {payment_id}\n<b>Комментарий:</b> {comment}\n<b>Время жизни:</b> {lifetime} сек.\n<b>Доп. информация:</b> {additional_data}",
        "confirm": "✅ Подтвердить",
        "cancel": "❌ Отмена",
        "operation_cancelled": "<emoji document_id=5312526098750252863>❌</emoji> <b>Операция отменена!</b>",
        "help_text": """
<emoji document_id=5467666648263564704>ℹ️</emoji> <b>Помощь по модулю LolzMarket</b>

<emoji document_id=5431376038628171216>💸</emoji> <b>Команды:</b>
<code>.lolz</code> - Показать меню модуля
<code>.lolzcreate</code> - Быстрое создание инвойса

<emoji document_id=5472111548572900003>✅</emoji> <b>Настройка:</b>
<code>.config LolzMarket</code> - Настроить API ключ и другие параметры
""",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "api_key",
                None,
                lambda: self.strings["cfg_api_key"],
                validator=loader.validators.Hidden(),
            ),
            loader.ConfigValue(
                "merchant_id",
                None,
                lambda: self.strings["cfg_merchant_id"],
                validator=loader.validators.Integer(),
            ),
            loader.ConfigValue(
                "success_url",
                "https://t.me/your_username",
                lambda: self.strings["cfg_success_url"],
            ),
            loader.ConfigValue(
                "callback_url",
                None,
                lambda: self.strings["cfg_callback_url"],
            ),
        )
        self.name = self.strings["name"]

    async def client_ready(self, client, db):
        self._db = db
        self._client = client
        self._api_url = "https://api.lzt.market"

    @loader.command(alias="lolz")
    async def lolzmarket(self, message: Message):
        """Показать меню модуля LolzMarket"""
        await self.inline.form(
            message=message,
            text=self.strings["help_text"],
            reply_markup=[
                [
                    {
                        "text": self.strings["create_invoice"],
                        "callback": self.create_invoice_callback,
                    }
                ],
            ],
        )

    @loader.command(alias="lolzcreate")
    async def lolzmarket_create(self, message: Message):
        """Быстрое создание инвойса"""
        await self.create_invoice_callback(InlineCall(None, None, message))

    async def create_invoice_callback(self, call: InlineCall):
        if not self.config["api_key"]:
            await call.edit(self.strings["no_api_key"])
            return

        if not self.config["merchant_id"]:
            await call.edit(self.strings["no_merchant_id"])
            return

        # Показываем выбор валюты
        await call.edit(
            text=self.strings["select_currency"],
            reply_markup=self._generate_currency_keyboard(),
        )

    def _generate_currency_keyboard(self):
        """Создает клавиатуру с валютами"""
        buttons = []
        row = []
        
        for i, currency in enumerate(CURRENCIES):
            row.append({"text": currency.upper(), "callback": self._currency_selected, "args": (currency,)})
            
            if (i + 1) % 3 == 0 or i == len(CURRENCIES) - 1:
                buttons.append(row)
                row = []
                
        buttons.append([{"text": self.strings["cancel"], "callback": self._cancel_operation}])
        return buttons

    async def _currency_selected(self, call: InlineCall, currency: str):
        # Сохраняем выбранную валюту
        self._db.set("lolzmarket", "current_invoice", {"currency": currency})
        
        # Запрашиваем сумму
        await call.edit(
            text=self.strings["enter_amount"],
            reply_markup=[
                [{"text": self.strings["cancel"], "callback": self._cancel_operation}],
            ],
        )
        
        # Ожидаем ответ пользователя с суммой
        amount_msg = await self._client.wait_event(
            lambda e: isinstance(e, TLMessage) and e.chat_id == call.form["chat"] and e.out is False,
            timeout=300,
        )
        
        try:
            amount = float(amount_msg.text)
            if amount <= 0:
                await self._client.send_message(
                    call.form["chat"], self.strings["invalid_amount"]
                )
                await self._cancel_operation(call)
                return
        except (ValueError, TypeError):
            await self._client.send_message(
                call.form["chat"], self.strings["invalid_amount"]
            )
            await self._cancel_operation(call)
            return
        
        # Удаляем сообщение пользователя с суммой
        await amount_msg.delete()
        
        # Обновляем текущий инвойс
        current_invoice = self._db.get("lolzmarket", "current_invoice", {})
        current_invoice["amount"] = amount
        self._db.set("lolzmarket", "current_invoice", current_invoice)
        
        # Запрашиваем ID платежа
        await call.edit(
            text=self.strings["enter_payment_id"],
            reply_markup=[
                [{"text": self.strings["cancel"], "callback": self._cancel_operation}],
            ],
        )
        
        # Ожидаем ответ пользователя с ID платежа
        payment_id_msg = await self._client.wait_event(
            lambda e: isinstance(e, TLMessage) and e.chat_id == call.form["chat"] and e.out is False,
            timeout=300,
        )
        
        payment_id = payment_id_msg.text
        await payment_id_msg.delete()
        
        # Обновляем текущий инвойс
        current_invoice = self._db.get("lolzmarket", "current_invoice", {})
        current_invoice["payment_id"] = payment_id
        self._db.set("lolzmarket", "current_invoice", current_invoice)
        
        # Запрашиваем комментарий
        await call.edit(
            text=self.strings["enter_comment"],
            reply_markup=[
                [{"text": self.strings["cancel"], "callback": self._cancel_operation}],
            ],
        )
        
        # Ожидаем ответ пользователя с комментарием
        comment_msg = await self._client.wait_event(
            lambda e: isinstance(e, TLMessage) and e.chat_id == call.form["chat"] and e.out is False,
            timeout=300,
        )
        
        comment = comment_msg.text
        await comment_msg.delete()
        
        # Обновляем текущий инвойс
        current_invoice = self._db.get("lolzmarket", "current_invoice", {})
        current_invoice["comment"] = comment
        self._db.set("lolzmarket", "current_invoice", current_invoice)
        
        # Запрашиваем время жизни инвойса
        await call.edit(
            text=self.strings["enter_lifetime"],
            reply_markup=[
                [
                    {
                        "text": self.strings["default_lifetime"],
                        "callback": self._lifetime_selected,
                        "args": (3600,),
                    }
                ],
                [{"text": self.strings["cancel"], "callback": self._cancel_operation}],
            ],
        )

    async def _lifetime_selected(self, call: InlineCall, lifetime: int):
        # Обновляем текущий инвойс с временем жизни
        current_invoice = self._db.get("lolzmarket", "current_invoice", {})
        current_invoice["lifetime"] = lifetime
        self._db.set("lolzmarket", "current_invoice", current_invoice)
        
        # Запрашиваем дополнительную информацию
        await call.edit(
            text=self.strings["enter_additional_data"],
            reply_markup=[
                [
                    {
                        "text": self.strings["skip"],
                        "callback": self._additional_data_selected,
                        "args": (None,),
                    }
                ],
                [{"text": self.strings["cancel"], "callback": self._cancel_operation}],
            ],
        )

    async def _additional_data_selected(self, call: InlineCall, additional_data: Optional[str]):
        # Обновляем текущий инвойс с дополнительной информацией
        current_invoice = self._db.get("lolzmarket", "current_invoice", {})
        current_invoice["additional_data"] = additional_data or ""
        self._db.set("lolzmarket", "current_invoice", current_invoice)
        
        # Показываем подтверждение создания инвойса
        current_invoice = self._db.get("lolzmarket", "current_invoice", {})
        
        await call.edit(
            text=self.strings["confirm_invoice"].format(
                currency=current_invoice.get("currency", "").upper(),
                amount=current_invoice.get("amount", ""),
                payment_id=current_invoice.get("payment_id", ""),
                comment=current_invoice.get("comment", ""),
                lifetime=current_invoice.get("lifetime", 3600),
                additional_data=current_invoice.get("additional_data", "") or "Не указано",
            ),
            reply_markup=[
                [{"text": self.strings["confirm"], "callback": self._confirm_invoice}],
                [{"text": self.strings["cancel"], "callback": self._cancel_operation}],
            ],
        )

    async def _confirm_invoice(self, call: InlineCall):
        # Показываем статус обработки
        await call.edit(
            text=self.strings["processing"],
            reply_markup=[],
        )
        
        # Получаем данные инвойса
        current_invoice = self._db.get("lolzmarket", "current_invoice", {})
        
        # Формируем данные для запроса
        payload = {
            "currency": current_invoice.get("currency", ""),
            "amount": current_invoice.get("amount", 0),
            "payment_id": current_invoice.get("payment_id", ""),
            "comment": current_invoice.get("comment", ""),
            "url_success": self.config["success_url"],
            "merchant_id": self.config["merchant_id"],
            "lifetime": current_invoice.get("lifetime", 3600),
        }
        
        # Добавляем опциональные поля, если они заполнены
        if self.config["callback_url"]:
            payload["url_callback"] = self.config["callback_url"]
            
        if current_invoice.get("additional_data"):
            payload["additional_data"] = current_invoice.get("additional_data")
        
        # Выполняем запрос к API
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self._api_url}/invoice",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {self.config['api_key']}",
                        "Content-Type": "application/json",
                    },
                ) as response:
                    result = await response.json()
                    
                    if response.status != 200:
                        await call.edit(
                            text=self.strings["api_error"].format(
                                error=result.get("detail", "Неизвестная ошибка")
                            ),
                            reply_markup=[],
                        )
                        return
                    
                    # Отображаем информацию о созданном инвойсе
                    await call.edit(
                        text=self.strings["invoice_created"].format(
                            amount=current_invoice.get("amount", ""),
                            currency=current_invoice.get("currency", "").upper(),
                            payment_id=current_invoice.get("payment_id", ""),
                            lifetime=current_invoice.get("lifetime", 3600),
                            url=result.get("url", ""),
                        ),
                        reply_markup=[
                            [
                                {
                                    "text": "🔗 Перейти к оплате",
                                    "url": result.get("url", ""),
                                }
                            ],
                            [
                                {
                                    "text": "🧾 Создать новый",
                                    "callback": self.create_invoice_callback,
                                }
                            ],
                        ],
                    )
        except Exception as e:
            logger.exception(e)
            await call.edit(
                text=self.strings["api_error"].format(error=str(e)),
                reply_markup=[],
            )

    async def _cancel_operation(self, call: InlineCall):
        await call.edit(
            text=self.strings["operation_cancelled"],
            reply_markup=[],
        )

    async def _wait_for_response(self, call: InlineCall, timeout=300):
        """Ожидание ответа от пользователя"""
        try:
            return await self._client.wait_event(
                lambda e: isinstance(e, TLMessage) and e.chat_id == call.form["chat"] and e.out is False,
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            await call.edit(
                text=self.strings["operation_cancelled"],
                reply_markup=[],
            )
            return None

    @loader.inline_handler(ru_doc="Создать инвойс на Lolz.live")
    async def lolz_inline_handler(self, query: InlineQuery) -> List[dict]:
        """Инлайн хендлер для создания инвойса"""
        return [
            {
                "title": "LolzMarket",
                "description": "Создать инвойс на Lolz.live",
                "thumb": "https://img.icons8.com/fluency/96/000000/invoice.png",
                "message": self.strings["help_text"],
                "reply_markup": {
                    "text": self.strings["create_invoice"],
                    "callback": self.create_invoice_callback,
                },
            }
        ]
