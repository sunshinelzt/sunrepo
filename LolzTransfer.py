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
        self.market = None
        self.forum = Forum(token=self.config["API_KEY"])
        self.market = Market(token=self.config["API_KEY"])

    async def client_ready(self, client, db):
        self.client = client

    async def lolzmcmd(self, message):
        """Перевод: .lolzm ник сумма валюта [комментарий]"""
        args = utils.get_args_raw(message).split()

        if len(args) < 3:
            await message.edit("❌ <b>Использование:</b> <code>.lolzm ник сумма валюта [комментарий]</code>")
            return

        nickname, amount, currency = args[:3]
        comment = " ".join(args[3:]) if len(args) > 3 else "Без комментария"

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

        buttons = [
            [Button.inline("✅ Подтвердить", data=f"confirm_{user['id']}_{amount}_{currency}_{comment}"),
             Button.inline("❌ Отмена", data="cancel")]
        ]

        await self.client.send_message(message.chat_id, text, buttons=buttons, parse_mode='html')

    async def get_user_by_nickname(self, nickname):
        """Поиск пользователя по нику на форуме"""
        try:
            response = await self.forum.users.get(nickname=nickname)
            return {"id": response["user_id"], "name": response["username"]}
        except Exception as e:
            logger.error(f"Ошибка при поиске пользователя {nickname}: {e}")
            return None

    async def on_callback_query(self, call):
        """Обработка inline кнопок для подтверждения или отмены перевода"""
        data = call.data.decode("utf-8")
        if data.startswith("confirm_"):
            _, user_id, amount, currency, comment = data.split("_", 4)
            response = await self.transfer_funds(user_id, amount, currency, comment)
            if response.get("success"):
                await call.answer("✅ Перевод успешно выполнен!", alert=True)
            else:
                error = response.get("error", "Ошибка при переводе.")
                await call.answer(f"❌ {error}", alert=True)
        elif data == "cancel":
            await call.answer("❌ Перевод отменён.", alert=True)

    async def transfer_funds(self, user_id, amount, currency, comment):
        """Функция для выполнения перевода средств"""
        try:
            response = await self.market.payments.transfer(
                amount=float(amount),
                currency=currency.lower(),
                secret_answer=self.config["SECRET_PHRASE"],
                user_id=int(user_id),
                comment=comment,
                hold=self.config["HOLD_TIME"],
                hold_option=self.config["HOLD_OPTION"]
            )
            return response.json()
        except Exception as e:
            logger.error(f"Ошибка при выполнении перевода: {e}")
            return {"error": "Произошла ошибка при перевода."}
