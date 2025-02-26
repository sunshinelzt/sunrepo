# meta developer: @sunshinelzt

import requests
from hikka import loader, utils

class LolzProfileMod(loader.Module):
    strings = {"name": "LZTProfile"}
    
    def __init__(self):
        self.config = loader.ModuleConfig("LOLZ_API_KEY", "", "API-ключ форума lolz.live")

    async def lolzcmd(self, message):
        args = utils.get_args_raw(message)
        username = args if args else (await message.get_reply_message()).sender.username if message.is_reply else None

        if not username:
            return await message.edit("<b>⚠️ Укажи ник или сделай реплай!</b>")

        user_info = await self.get_lolz_user(username)
        if not user_info:
            return await message.edit("<b>🚫 Пользователь не найден или API-ключ недействителен!</b>")

        await message.edit(self.format_user_info(user_info), parse_mode="HTML")

    async def get_lolz_user(self, query):
        api_key = self.config["LOLZ_API_KEY"]
        url = f"https://api.lolz.live/v1/users/{query}"
        headers = {"Authorization": f"Bearer {api_key}"}

        try:
            response = requests.get(url, headers=headers, timeout=10)
            data = response.json()
            return None if "error" in data else data
        except requests.RequestException:
            return None

    def format_user_info(self, user):
        status = "🔴 Заблокирован" if user.get('banned', False) else "🟢 Не заблокирован"

        return (
            f"╭━━━📌 <b>ЛОЛЗТИМ ПРОФИЛЬ</b>\n"
            f"┣ 🆔 <b>ID:</b> {user.get('id', 'Неизвестно')}\n"
            f"┣ 👤 <b>Ник:</b> <a href='https://lolz.live/members/{user.get('id', '')}/'>{user.get('nickname', 'Неизвестно')}</a>\n"
            f"┣ 🏷 <b>Юзернейм:</b> @{user.get('username', 'Неизвестно')}\n"
            f"┣ 🔗 <b>Группа:</b> {user.get('group', 'Неизвестно')}\n"
            f"┣ 🎖 <b>Ранг:</b> {user.get('custom_title', '—')}\n"
            f"┣ 🛡 <b>Статус:</b> {status}\n"
            f"┣ 🗓 <b>Регистрация:</b> {user.get('registration_date', '—')}\n"
            f"╰━━━━━━━━━━━━━━━━━━\n"
            f"╭━━━📊 <b>СТАТИСТИКА</b>\n"
            f"┣ 💬 <b>Сообщений:</b> {user.get('messages', 0)}\n"
            f"┣ ❤️ <b>Лайков:</b> {user.get('likes', 0)}\n"
            f"┣ 🔥 <b>Реакций:</b> {user.get('reactions', 0)}\n"
            f"┣ 🎁 <b>Розыгрышей:</b> {user.get('raffles', 0)}\n"
            f"┣ 🏆 <b>Трофеев:</b> {user.get('trophies', 0)}\n"
            f"╰━━━━━━━━━━━━━━━━━━\n"
            f"╭━━━👥 <b>СОЦИАЛЬНОЕ</b>\n"
            f"┣ 👤 <b>Подписчики:</b> {user.get('followers', 0)}\n"
            f"┣ 🤝 <b>Подписок:</b> {user.get('following', 0)}\n"
            f"╰━━━━━━━━━━━━━━━━━━"
        )
