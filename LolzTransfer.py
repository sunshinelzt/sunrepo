# meta developer

from .. import loader, utils
import logging
import lolzteam
from telethon import Button

logger = logging.getLogger(__name__)

@loader.tds
class LolzTransferMod(loader.Module):
    """Идеальный модуль перевода денег на lolz.live"""
    strings = {"name": "LolzTransfer"}

    def __init__(self):
        self.config = loader.ModuleConfig(
            "API_KEY", "", "API ключ от lolz.live",
            "SECRET_PHRASE", "", "Секретная фраза для переводов",
            "HOLD_TIME", 0, "Длительность холда (0 - без холда)",
            "HOLD_OPTION", "hour", "Единица времени холда (hour/day)"
        )
        self.market = None

    async def client_ready(self, client, db):
        self.client = client
        self.market = lolzteam.Market(self.config["API_KEY"])

    async def lolzmcmd(self, message):
        """Перевод: .lolzm ник сумма валюта [комментарий]"""
        args = utils.get_args_raw(message).split()

        if len(args) < 3:
            await message.edit("❌ <b>Использование:</b> <code>.lolzm ник 100 rub [комментарий]</code>")
            return

        nickname, amount, currency = args[:3]
        comment = " ".join(args[3:]) if len(args) > 3 else "Без комментария"

        user = self.get_user(nickname)
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

    def get_user(self, nickname):
        """Поиск пользователя по нику"""
        try:
            user = self.market.user.get(nickname)
            return {"id": user.user_id, "name": user.username}
        except Exception as e:
            logger.error(f"Ошибка поиска пользователя: {e}")
            return None

    async def on_callback_query(self, call):
        """Обработка кнопок"""
        data = call.data.decode("utf-8")
        if data.startswith("confirm_"):
            _, user_id, amount, currency, comment = data.split("_", 4)
            response = self.transfer_funds(user_id, amount, currency, comment)
            if response.get("success"):
                await call.answer("✅ Перевод успешно выполнен!", alert=True)
            else:
                error = response.get("error", "Ошибка при переводе.")
                await call.answer(f"❌ {error}", alert=True)
        elif data == "cancel":
            await call.answer("❌ Перевод отменён.", alert=True)

    def transfer_funds(self, user_id, amount, currency, comment):
        """Отправка перевода"""
        try:
            response = self.market.payments.transfer(
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
            logger.error(f"Ошибка при переводе: {e}")
            return {"error": "Произошла ошибка при переводе."}
