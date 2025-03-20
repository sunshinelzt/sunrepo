# meta developer

from telethon import loader, utils
import logging
from LOLZTEAM.Client import Forum, Market
from telethon import Button
import asyncio
import re
from datetime import datetime

logger = logging.getLogger(__name__)

@loader.tds
class LolzTransferMod(loader.Module):
    """Модуль перевода денег на lolz.live с расширенными возможностями"""
    strings = {
        "name": "LolzTransfer",
        "invalid_args": "❌ <b>Использование:</b> <code>.lolzm ник сумма валюта [комментарий]</code>",
        "user_not_found": "❌ <b>Пользователь</b> <code>{}</code> <b>не найден на lolz.live.</b>",
        "transfer_error": "❌ Произошла ошибка при переводе: {}",
        "insufficient_funds": "❌ <b>Недостаточно средств для перевода.</b>",
        "invalid_amount": "❌ <b>Сумма перевода должна быть положительным числом.</b>",
        "invalid_currency": "❌ <b>Поддерживаемые валюты:</b> USD, EUR, RUB.",
        "auth_error": "❌ <b>Ошибка авторизации API. Проверьте API ключ.</b>",
        "cancel_transfer": "❌ Перевод отменён.",
        "successful_transfer": "✅ Перевод успешно выполнен! ID транзакции: {}",
        "processing": "⏳ <b>Обработка запроса...</b>",
        "config_updated": "✅ <b>Настройки успешно обновлены!</b>",
        "balance_info": "💰 <b>Ваш баланс на Lolz:</b>\n{}"
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            "API_KEY", "", "API ключ от lolz.live",
            "SECRET_PHRASE", "", "Секретная фраза для переводов",
            "HOLD_TIME", 0, "Длительность холда (0 - без холда)",
            "HOLD_OPTION", "hour", "Единица времени холда (hour/day)",
            "DEFAULT_CURRENCY", "rub", "Валюта по умолчанию (usd/eur/rub)",
            "AUTO_CONFIRM", False, "Автоматическое подтверждение переводов без запроса (True/False)",
            "TRANSFER_LIMIT", 1000, "Лимит суммы перевода (0 - без лимита)"
        )
        self.market = None
        self.forum = None

    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        # Инициализация при запуске
        self._initialize_api()
        
    def _initialize_api(self):
        """Инициализация API клиентов"""
        if self.config["API_KEY"]:
            try:
                self.market = Market(token=self.config["API_KEY"])
                self.forum = Forum(token=self.config["API_KEY"])
            except Exception as e:
                logger.error(f"Ошибка инициализации API: {e}")
                self.market = None
                self.forum = None

    async def lolzconfigcmd(self, message):
        """Настройка параметров модуля: .lolzconfig параметр значение"""
        args = utils.get_args(message)
        
        if len(args) < 2:
            config_info = "\n".join([
                f"🔹 <b>{key}</b>: <code>{self.config[key] if key != 'SECRET_PHRASE' and key != 'API_KEY' else '***'}</code>"
                for key in self.config
            ])
            await message.edit(f"⚙️ <b>Текущие настройки:</b>\n\n{config_info}\n\n"
                               f"<b>Использование:</b> <code>.lolzconfig параметр значение</code>")
            return
            
        param, value = args[0].upper(), " ".join(args[1:])
        
        # Конвертация значений
        if param in ["HOLD_TIME", "TRANSFER_LIMIT"]:
            try:
                value = int(value)
            except ValueError:
                await message.edit(f"❌ <b>Параметр {param} должен быть числом</b>")
                return
        elif param == "AUTO_CONFIRM":
            value = value.lower() in ["true", "1", "yes", "да"]
        
        if param in self.config:
            self.config[param] = value
            # Переинициализация API при изменении ключа
            if param == "API_KEY":
                self._initialize_api()
            await message.edit(self.strings["config_updated"])
        else:
            await message.edit(f"❌ <b>Параметр {param} не существует</b>")

    async def lolzmcmd(self, message):
        """Перевод: .lolzm ник сумма [валюта] [комментарий]"""
        if not self.market or not self.forum:
            self._initialize_api()
            if not self.market or not self.forum:
                await message.edit(self.strings["auth_error"])
                return
                
        await message.edit(self.strings["processing"])
        
        args = utils.get_args_raw(message).split()
        
        if len(args) < 2:
            await message.edit(self.strings["invalid_args"])
            return

        nickname = args[0]
        
        # Проверка и парсинг суммы
        try:
            amount = float(args[1])
        except ValueError:
            await message.edit(self.strings["invalid_amount"])
            return
            
        if amount <= 0:
            await message.edit(self.strings["invalid_amount"])
            return
            
        # Проверка лимита перевода
        if self.config["TRANSFER_LIMIT"] > 0 and amount > self.config["TRANSFER_LIMIT"]:
            await message.edit(f"❌ <b>Превышен лимит перевода ({self.config['TRANSFER_LIMIT']}).</b>")
            return
            
        # Определение валюты
        if len(args) >= 3 and args[2].lower() in ["usd", "eur", "rub"]:
            currency = args[2].lower()
            comment_start = 3
        else:
            currency = self.config["DEFAULT_CURRENCY"]
            comment_start = 2
            
        comment = " ".join(args[comment_start:]) if len(args) > comment_start else f"Перевод от {datetime.now().strftime('%d.%m.%Y %H:%M')}"

        # Получение информации о пользователе
        user = await self.get_user_by_nickname(nickname)
        if not user:
            await message.edit(self.strings["user_not_found"].format(nickname))
            return

        # Получение своего баланса
        balance = await self.get_balance()
        if not balance:
            await message.edit("❌ <b>Не удалось получить информацию о балансе.</b>")
            return
            
        if currency in balance and float(balance[currency]) < amount:
            await message.edit(self.strings["insufficient_funds"])
            return

        # Автоподтверждение или запрос на подтверждение
        if self.config["AUTO_CONFIRM"]:
            response = await self.transfer_funds(user["id"], amount, currency, comment)
            if response.get("success"):
                transaction_id = response.get("transfer_id", "N/A")
                await message.edit(f"✅ <b>Перевод выполнен успешно!</b>\n"
                                 f"👤 <b>Получатель:</b> <a href='https://lolz.live/members/{user['id']}'>{user['name']}</a>\n"
                                 f"💸 <b>Сумма:</b> {amount} {currency.upper()}\n"
                                 f"🔢 <b>ID транзакции:</b> {transaction_id}\n"
                                 f"💬 <b>Комментарий:</b> {comment}")
            else:
                error = response.get("error", "Неизвестная ошибка")
                await message.edit(self.strings["transfer_error"].format(error))
        else:
            profile_url = f"https://lolz.live/members/{user['id']}/"
            
            # Формирование информации о балансе
            balance_info = f"<b>Доступно:</b> {balance.get(currency, 0)} {currency.upper()}"
            
            text = (
                f"💸 <b>Вы собираетесь перевести</b>: <code>{amount} {currency.upper()}</code>\n"
                f"👤 <b>Получатель</b>: <a href='{profile_url}'>{user['name']}</a>\n"
                f"💰 {balance_info}\n"
                f"💬 <b>Комментарий</b>: <i>{comment}</i>\n"
                f"⏳ <b>Холд</b>: {self.config['HOLD_TIME']} {self.config['HOLD_OPTION']}"
            )

            buttons = [
                [Button.inline("✅ Подтвердить", data=f"confirm_{user['id']}_{amount}_{currency}_{comment}"),
                 Button.inline("❌ Отмена", data="cancel")]
            ]

            try:
                await message.delete()
                await self.client.send_message(message.chat_id, text, buttons=buttons, parse_mode='html')
            except Exception as e:
                logger.error(f"Ошибка при отправке сообщения: {e}")
                await message.edit("❌ Произошла ошибка при отправке сообщения.")

    async def lolzbalancecmd(self, message):
        """Показать баланс на Lolz"""
        if not self.market:
            self._initialize_api()
            if not self.market:
                await message.edit(self.strings["auth_error"])
                return
        
        await message.edit("⏳ <b>Получение информации о балансе...</b>")
        
        balance = await self.get_balance()
        if not balance:
            await message.edit("❌ <b>Не удалось получить информацию о балансе.</b>")
            return
            
        balance_text = "\n".join([f"🔹 <b>{currency.upper()}</b>: <code>{amount}</code>" for currency, amount in balance.items()])
        await message.edit(self.strings["balance_info"].format(balance_text))

    async def lolzhistorycmd(self, message):
        """Показать историю переводов: .lolzhistory [количество]"""
        if not self.market:
            self._initialize_api()
            if not self.market:
                await message.edit(self.strings["auth_error"])
                return
                
        args = utils.get_args(message)
        limit = 5
        
        if args and args[0].isdigit():
            limit = int(args[0])
            if limit > 20:
                limit = 20  # Ограничение на количество записей
                
        await message.edit("⏳ <b>Получение истории переводов...</b>")
        
        try:
            response = await self.market.payments.history(limit=limit)
            history = response.json()
            
            if not history.get("success"):
                await message.edit("❌ <b>Не удалось получить историю переводов.</b>")
                return
                
            transfers = history.get("transfers", [])
            
            if not transfers:
                await message.edit("ℹ️ <b>История переводов пуста.</b>")
                return
                
            result = "📜 <b>История переводов:</b>\n\n"
            
            for transfer in transfers:
                transfer_type = "➡️ Отправлено" if transfer.get("is_outgoing") else "⬅️ Получено"
                date = datetime.fromtimestamp(transfer.get("date", 0)).strftime("%d.%m.%Y %H:%M")
                amount = transfer.get("amount", 0)
                currency = transfer.get("currency", "").upper()
                comment = transfer.get("comment", "Без комментария")
                user = transfer.get("user", {})
                user_link = f"<a href='https://lolz.live/members/{user.get('user_id')}'>{user.get('username', 'Unknown')}</a>"
                
                result += (f"<b>{transfer_type}</b> {date}\n"
                          f"💰 <b>{amount} {currency}</b> {'к' if transfer.get('is_outgoing') else 'от'} {user_link}\n"
                          f"💬 <i>{comment}</i>\n\n")
                
            await message.edit(result)
        except Exception as e:
            logger.error(f"Ошибка при получении истории: {e}")
            await message.edit(f"❌ <b>Ошибка при получении истории: {str(e)}</b>")

    async def get_user_by_nickname(self, nickname):
        """Поиск пользователя по нику на форуме"""
        try:
            response = await self.forum.users.get(nickname=nickname)
            if response.get("success"):
                return {"id": response["user"]["user_id"], "name": response["user"]["username"]}
            return None
        except Exception as e:
            logger.error(f"Ошибка при поиске пользователя {nickname}: {e}")
            return None
            
    async def get_balance(self):
        """Получение баланса пользователя"""
        try:
            response = await self.market.user.me()
            data = response.json()
            
            if not data.get("success"):
                return None
                
            balance = {}
            balance_data = data.get("user", {}).get("balance", {})
            
            for currency in ["usd", "eur", "rub"]:
                balance[currency] = balance_data.get(currency, 0)
                
            return balance
        except Exception as e:
            logger.error(f"Ошибка при получении баланса: {e}")
            return None

    async def on_callback_query(self, call):
        """Обработка inline кнопок для подтверждения или отмены перевода"""
        data = call.data.decode("utf-8")
        
        if data.startswith("confirm_"):
            # Разбиваем данные с учетом возможных пробелов в комментарии
            parts = data.split("_", 4)
            if len(parts) < 5:
                await call.answer("❌ Некорректные данные для перевода.", alert=True)
                return
                
            _, user_id, amount, currency, comment = parts
            
            # Обновляем сообщение во время обработки
            await self.client.edit_message(
                call.message,
                f"⏳ <b>Выполнение перевода {amount} {currency.upper()}...</b>",
                buttons=None,
                parse_mode='html'
            )
            
            response = await self.transfer_funds(user_id, amount, currency, comment)
            
            if response.get("success"):
                transaction_id = response.get("transfer_id", "N/A")
                await self.client.edit_message(
                    call.message,
                    f"✅ <b>Перевод выполнен успешно!</b>\n"
                    f"💸 <b>Сумма:</b> {amount} {currency.upper()}\n"
                    f"🔢 <b>ID транзакции:</b> {transaction_id}\n"
                    f"💬 <b>Комментарий:</b> {comment}",
                    parse_mode='html'
                )
                await call.answer(self.strings["successful_transfer"].format(transaction_id), alert=True)
            else:
                error = response.get("error", "Неизвестная ошибка")
                await self.client.edit_message(
                    call.message,
                    f"❌ <b>Ошибка при переводе:</b> {error}",
                    parse_mode='html'
                )
                await call.answer(self.strings["transfer_error"].format(error), alert=True)
        elif data == "cancel":
            await self.client.edit_message(
                call.message,
                "❌ <b>Перевод отменён.</b>",
                buttons=None,
                parse_mode='html'
            )
            await call.answer(self.strings["cancel_transfer"], alert=True)

    async def transfer_funds(self, user_id, amount, currency, comment):
        """Функция для выполнения перевода средств"""
        try:
            # Преобразуем количество в float и валюту в нижний регистр
            amount = float(amount)
            currency = currency.lower()

            # Валидация суммы и валюты
            if amount <= 0:
                return {"error": "Сумма перевода должна быть положительным числом."}
            if currency not in ["usd", "eur", "rub"]:
                return {"error": "Неверная валюта."}

            response = await self.market.payments.transfer(
                amount=amount,
                currency=currency,
                secret_answer=self.config["SECRET_PHRASE"],
                user_id=int(user_id),
                comment=comment,
                hold=self.config["HOLD_TIME"],
                hold_option=self.config["HOLD_OPTION"]
            )
            return response.json()
        except Exception as e:
            logger.error(f"Ошибка при выполнении перевода: {e}")
            return {"error": str(e)}
