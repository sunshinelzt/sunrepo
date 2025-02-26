# meta developer: @sunshinelzt
# requires: requests

import requests
from hikka import loader, utils

class LolzProfile(loader.Module):
    strings = {"name": "LolzProfile"}
    
    def __init__(self):
        self.config = loader.ModuleConfig("LOLZ_API_KEY", "", "API-ключ форума lolz.live")

    async def lolzcmd(self, message):
        args = utils.get_args_raw(message)
        if message.is_reply:
            reply = await message.get_reply_message()
            args = reply.sender.username if reply.sender else None
        
        if not args:
            return await message.edit("<b>⚠️ Укажи ник или сделай реплай!</b>")

        user_info = await self.get_user_info(args)
        if not user_info:
            return await message.edit("<b>🚫 Пользователь не найден или API-ключ неверный!</b>")

        await message.edit(self.format_profile(user_info), parse_mode="HTML")

    async def get_user_info(self, username):
        api_key = self.config["LOLZ_API_KEY"]
        if not api_key:
            return None

        url = f"https://api.lolz.live/v1/users/{username}"
        headers = {"Authorization": f"Bearer {api_key}"}

        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                return None
            return response.json()
        except requests.RequestException:
            return None

    def format_profile(self, user):
        return (
            f"👤 <b>Профиль:</b> <a href='https://lolz.live/members/{user['id']}/'>{user['nickname']}</a>\n"
            f"🆔 <b>ID:</b> {user['id']}\n"
            f"🏷 <b>Юзернейм:</b> @{user['username']}\n"
            f"🔗 <b>Группа:</b> {user['group']}\n"
            f"📝 <b>Статус:</b> {user.get('custom_title', '—')}\n"
            f"🛡 <b>Аккаунт:</b> {'🔴 Заблокирован' if user.get('banned', False) else '🟢 Активен'}\n"
            f"📅 <b>Регистрация:</b> {user['registration_date']}\n"
            f"💬 <b>Сообщений:</b> {user['messages']}\n"
            f"❤️ <b>Лайков:</b> {user['likes']}\n"
            f"🔥 <b>Реакций:</b> {user['reactions']}\n"
            f"🎁 <b>Розыгрышей:</b> {user['raffles']}\n"
            f"🏆 <b>Трофеев:</b> {user['trophies']}\n"
            f"👥 <b>Подписчики:</b> {user['followers']}\n"
            f"📌 <b>Подписки:</b> {user['following']}\n"
        )
