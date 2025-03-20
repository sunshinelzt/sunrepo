# meta developer

from telethon import loader, utils
import logging
from LOLZTEAM.Client import Forum, Market
from telethon import Button
import asyncio

logger = logging.getLogger(__name__)

@loader.tds
class LolzTransferMod(loader.Module):
    """Модуль перевода денег на lolz.live с улучшениями"""
    strings = {"name": "LolzTransfer"}

    def __init__(self):
        self.config = loader.ModuleConfig(
            "API_KEY", "", "API ключ от lolz.live",
            "SECRET_PHRASE", "", "Секретная фраза для переводов",
            "HOLD_TIME", 0, "Длительность холда (0 - без холда)",
            "HOLD_OPTION", "hour", "Единица времени холда (hour/day)"
        )

    async def client_ready(self, client, db):
        self.client = client
        # Initialize API clients after config is loaded
        self.market = Market(token=self.config["API_KEY"])
        self.forum = Forum(token=self.config["API_KEY"])

    async def lolzmcmd(self, message):
        """Перевод: .lolzm ник сумма валюта [комментарий]"""
        args = utils.get_args_raw(message).split()

        if len(args) < 3:
            await message.edit("❌ <b>Использование:</b> <code>.lolzm ник сумма валюта [комментарий]</code>")
            return

        nickname, amount_str, currency = args[:3]
        comment = " ".join(args[3:]) if len(args) > 3 else "Без комментария"

        # Validate amount
        try:
            amount = float(amount_str)
            if amount <= 0:
                await message.edit("❌ <b>Сумма перевода должна быть положительным числом.</b>")
                return
        except ValueError:
            await message.edit("❌ <b>Сумма должна быть числом.</b>")
            return

        # Validate currency
        currency = currency.lower()
        if currency not in ["usd", "eur", "rub"]:
            await message.edit("❌ <b>Поддерживаемые валюты: USD, EUR, RUB.</b>")
            return

        user = await self.get_user_by_nickname(nickname)
        if not user:
            await message.edit(f"❌ <b>Пользователь</b> <code>{nickname}</code> <b>не найден на lolz.live.</b>")
            return

        profile_url = f"https://lolz.live/members/{user['id']}/"
        text = (
            f"💸 <b>Вы собираетесь перевести</b>: <code>{amount} {currency.upper()}</code>\n"
            f"👤 <b>Получатель</b>: <a href='{profile_url}'>{user['name']}</a>\n"
            f"💬 <b>Комментарий</b>: <i>{comment}</i>\n"
            f"⏳ <b>Холд</b>: {self.config['HOLD_TIME']} {self.config['HOLD_OPTION']}"
        )

        # Encode comment for button data to avoid parsing issues
        encoded_comment = comment.replace("_", "꘎")  # Using rare Unicode character as separator

        buttons = [
            [Button.inline("✅ Подтвердить", data=f"confirm_{user['id']}_{amount}_{currency}_{encoded_comment}"),
             Button.inline("❌ Отмена", data="cancel")]
        ]

        try:
            await message.delete()
            await self.client.send_message(message.chat_id, text, buttons=buttons, parse_mode='html')
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения: {e}")
            await message.edit("❌ <b>Произошла ошибка при отправке сообщения.</b>")

    async def get_user_by_nickname(self, nickname):
        """Поиск пользователя по нику на форуме"""
        try:
            response = await self.forum.users.get(nickname=nickname)
            return {"id": response["user_id"], "name": response["username"]}
        except Exception as e:
            logger.error(f"Ошибка при поиске пользователя {nickname}: {e}")
            return None

    async def callback_handler(self, call):
        """Обработка inline кнопок для подтверждения или отмены перевода"""
        data = call.data.decode("utf-8")
        
        if data.startswith("confirm_"):
            parts = data.split("_", 4)
            if len(parts) != 5:
                await call.answer("❌ Неверный формат данных.", alert=True)
                return
                
            _, user_id, amount, currency, encoded_comment = parts
            comment = encoded_comment.replace("꘎", "_")  # Decode comment
            
            try:
                response = await self.transfer_funds(user_id, amount, currency, comment)
                if response and response.get("success"):
                    await call.edit(
                        f"✅ <b>Перевод выполнен успешно!</b>\n"
                        f"💸 <b>Сумма</b>: <code>{amount} {currency.upper()}</code>\n"
                        f"🆔 <b>Получатель ID</b>: <code>{user_id}</code>",
                        buttons=None
                    )
                else:
                    error = response.get("error", "Неизвестная ошибка.")
                    await call.edit(f"❌ <b>Ошибка при переводе:</b> {error}", buttons=None)
            except Exception as e:
                logger.error(f"Ошибка при обработке подтверждения: {e}")
                await call.edit("❌ <b>Произошла ошибка при обработке запроса.</b>", buttons=None)
        
        elif data == "cancel":
            await call.edit("❌ <b>Перевод отменён.</b>", buttons=None)

    async def transfer_funds(self, user_id, amount, currency, comment):
        """Функция для выполнения перевода средств"""
        try:
            # Преобразуем количество в float
            amount = float(amount)
            
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
            return {"success": False, "error": f"Произошла ошибка при переводе: {str(e)}"}
