# meta developer

from .. import loader, utils
import logging
import requests
from telethon import Button

logger = logging.getLogger(__name__)

@loader.tds
class LolzTransferMod(loader.Module):
    """Идеальный перевод денег на lolz.live по нику"""
    strings = {"name": "LolzTransfer"}

    def __init__(self):
        self.config = loader.ModuleConfig(
            "API_KEY", "", "API ключ от lolz.live",
            "SECRET_PHRASE", "", "Секретная фраза для переводов"
        )

    async def client_ready(self, client, db):
        self.client = client

    async def lolzmcmd(self, message):
        """Перевод денег: .lolzm ник сумма валюта [комментарий]"""
        args = utils.get_args_raw(message).split()

        if len(args) < 3:
            await message.edit("❌ Использование: `.lolzm ник 100 rub [комментарий]`")
            return

        nickname, amount, currency = args[:3]
        comment = " ".join(args[3:]) if len(args) > 3 else "Без комментария"

        user_id, username = await self.get_user_info(nickname)
        if not user_id:
            await message.edit(f"❌ Пользователь `{nickname}` не найден на lolz.live.")
            return

        profile_url = f"https://lolz.live/members/{user_id}/"
        text = (f"💸 <b>Вы собираетесь перевести</b>: <code>{amount} {currency.upper()}</code>\n"
                f"👤 <b>Получатель</b>: <a href='{profile_url}'>{username}</a>\n"
                f"💬 <b>Комментарий</b>: <i>{comment}</i>")

        buttons = [
            [Button.inline("✅ Подтвердить", data=f"confirm_{user_id}_{amount}_{currency}_{comment}"),
             Button.inline("❌ Отмена", data="cancel")]
        ]

        await self.client.send_message(message.chat_id, text, buttons=buttons, parse_mode='html')

    async def get_user_info(self, nickname):
        """Получение ID и ника пользователя с lolz.live"""
        url = f"https://api.lolz.live/v1/user/{nickname}"
        headers = {"Authorization": f"Bearer {self.config['API_KEY']}"}
        try:
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get("user_id"), data.get("username")
        except requests.exceptions.Timeout:
            logger.error("⏳ API Lolz.live не отвечает (таймаут)")
        except Exception as e:
            logger.error(f"Ошибка API Lolz: {e}")
        return None, None

    async def on_callback_query(self, call):
        """Обработка нажатий на инлайн-кнопки"""
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
        """Отправка перевода через API Lolz.live"""
        url = "https://api.lolz.live/v1/market/transfer"
        headers = {"Authorization": f"Bearer " + self.config["API_KEY"]}
        data = {
            "receiver": user_id,
            "amount": amount,
            "currency": currency,
            "comment": comment,
            "secret_answer": self.config["SECRET_PHRASE"],
            "transfer_hold": "no"
        }
        try:
            response = requests.post(url, headers=headers, json=data, timeout=5)
            return response.json()
        except requests.exceptions.Timeout:
            logger.error("⏳ API Lolz.live не отвечает (таймаут)")
            return {"error": "Сервер lolz.live не отвечает. Попробуйте позже."}
        except Exception as e:
            logger.error(f"Ошибка при переводе: {e}")
            return {"error": "Произошла ошибка при переводе."}
