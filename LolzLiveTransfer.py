# meta developer: @sunshinelzt

from hikka import loader, utils
import lolzteam
import os
from hikka.types import InlineKeyboardButton, InlineKeyboardMarkup

class LolzLiveTransfer(loader.Module):
    """Модуль для перевода денег на Lolz.live с инлайн-подтверждением и комментариями"""

    strings = {
        "name": "LolzLiveTransfer",
        "help": "Использование: .transfer <сумма> <пользователь> [комментарий]\nПример: .transfer 100 @username Оплата за товар"
    }

    def __init__(self):
        # Конфигурация
        self.config = loader.ModuleConfig(
            "LOLZ_API_KEY", os.getenv("LOLZ_API_KEY") or "ВСТАВЬ_СВОЙ_API_КЛЮЧ",
            "API-ключ для работы с Lolz.live"
        )
        self.secret_answer = loader.ModuleConfig(
            "SECRET_ANSWER", "your_secret_answer", 
            "Ответ на секретный вопрос для перевода средств"
        )
        self.currency = loader.ModuleConfig(
            "CURRENCY", "rub", 
            "Валюта для перевода"
        )

    async def client_ready(self, client: hikka.Client):
        """Инициализация клиента API LolzTeam"""
        self.market = lolzteam.Market(api_key=self.config["LOLZ_API_KEY"])

    @loader.command()
    async def transfer(self, message: hikka.Message):
        """
        Перевод денег пользователю на Lolz.live с возможностью указания комментария.
        Пример: .transfer 100 @username Оплата за товар
        """
        # Получаем аргументы из сообщения
        args = utils.get_args_raw(message).split()
        if len(args) < 2:
            await message.reply("Использование: .transfer <сумма> <пользователь> [комментарий]")
            return

        # Извлекаем сумму и получателя
        try:
            amount = float(args[0])
        except ValueError:
            await message.reply("Сумма должна быть числом!")
            return

        recipient = args[1]
        comment = None
        
        # Если комментарий есть, добавляем его
        if len(args) > 2:
            comment = " ".join(args[2:])

        # Проверка на правильность суммы
        if amount <= 0:
            await message.reply("Сумма перевода должна быть больше нуля!")
            return

        # Получаем информацию о пользователе по логину или ID
        try:
            user = None
            if recipient.isdigit():  # если передан ID
                user = self.market.users.get(id=int(recipient))
            else:  # если передан логин
                user = self.market.users.get(username=recipient)

            if not user:
                await message.reply("Пользователь не найден!")
                return

            user_id = user["id"]
            username = user["username"]
        except Exception as e:
            await message.reply(f"Ошибка при поиске пользователя: {str(e)}")
            return

        # Создаем инлайн-кнопки для подтверждения
        confirm_button = InlineKeyboardButton("Подтвердить", callback_data=f"confirm_{amount}_{username}_{comment}")
        cancel_button = InlineKeyboardButton("Отменить", callback_data="cancel_transfer")
        inline_markup = InlineKeyboardMarkup([[confirm_button, cancel_button]])

        # Отправляем сообщение с инлайн-кнопками
        await message.reply(f"Вы собираетесь перевести {amount} {self.currency} пользователю {username}. Подтвердите действие:", reply_markup=inline_markup)

    @loader.inline_handler()
    async def inline_handler(self, query: hikka.InlineQuery):
        """Обрабатываем инлайн запросы"""
        if query.data.startswith("confirm_"):
            # Получаем данные из callback
            _, amount, username, comment = query.data.split("_")
            amount = float(amount)
            comment = comment if comment != "None" else None

            # Выполнение перевода
            try:
                response = self.market.payments.transfer(
                    amount=amount,
                    currency=self.currency,
                    secret_answer=self.secret_answer,
                    user_id=int(username),  # Используем username как ID
                    username=username,
                    comment=comment if comment else ""
                )
                await query.answer(f"Перевод на {username} на сумму {amount} {self.currency} завершен успешно!")
            except Exception as e:
                await query.answer(f"Ошибка при выполнении перевода: {str(e)}")
        
        elif query.data == "cancel_transfer":
            await query.answer("Перевод отменен.")
