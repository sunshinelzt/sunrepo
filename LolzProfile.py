# meta developer: @sunshinelzt

import sys
from hikka import loader, utils
from telethon.tl.functions.users import GetFullUserRequest

try:
    import LOLZTEAM
except ImportError:
    sys.exit("❌ Ошибка: отсутствует библиотека 'LOLZTEAM'. Установи её:\n\npip install LOLZTEAM")

class LolzInfo(loader.Module):
    """Получает информацию о пользователе с форума lolz.live по API"""

    strings = {"name": "LolzInfo"}

    def __init__(self):
        self.config = loader.ModuleConfig(
            "LOLZ_API_KEY", "", "API-ключ форума lolz.live"
        )
        self.client = None

    async def client_ready(self, client, db):
        api_key = self.config["LOLZ_API_KEY"]
        if api_key:
            self.client = LOLZTEAM.Forum(api_key)
        self.tg_client = client

    async def lolzcmd(self, message):
        """Использование: .lolz <реплай/@юзернейм/ник>"""
        args = utils.get_args_raw(message)
        tg_username = None
        forum_nickname = None

        if message.is_reply:
            reply = await message.get_reply_message()
            tg_username = await self.get_tg_username(reply.sender_id)
        elif args.startswith("@"):
            tg_username = args.lstrip("@")
        else:
            forum_nickname = args

        if tg_username:
            user_info = await self.get_user_info_by_tg(tg_username)
        elif forum_nickname:
            user_info = await self.get_user_info_by_nickname(forum_nickname)
        else:
            return await message.edit("<b>🚫 Укажите ник или ответьте на сообщение.</b>")

        if not user_info:
            return await message.edit("<b>🚫 Пользователь не найден!</b>")

        await message.edit(self.format_profile(user_info), parse_mode="HTML")

    async def get_tg_username(self, user_id):
        """Получает Telegram-юзернейм по ID пользователя."""
        try:
            user = await self.tg_client(GetFullUserRequest(user_id))
            return user.user.username if user.user.username else None
        except Exception:
            return None

    async def get_user_info_by_tg(self, tg_username):
        """Получает информацию о пользователе на форуме по Telegram-юзернейму."""
        if not self.client:
            return None
        try:
            response = self.client.users.search(username=tg_username)
            return response[0] if response else None
        except Exception:
            return None

    async def get_user_info_by_nickname(self, nickname):
        """Получает информацию о пользователе на форуме по нику."""
        if not self.client:
            return None
        try:
            return self.client.users.get(nickname)
        except Exception:
            return None

    def format_profile(self, user):
        """Форматирует информацию о пользователе для вывода."""
        return (
            f"👤 <b>Пользователь:</b> <a href='https://lolz.live/members/{user.id}/'>{user.username}</a>\n"
            f"🔗 <b>Профиль LZT:</b> {user.nickname}\n"
            f"ℹ️ <b>Группа:</b> {user.group_title}\n"
            f"📝 <b>Статус:</b> {user.status}\n"
            f"💬 <b>Сообщений:</b> {user.messages}\n"
            f"💚 <b>Симпатий:</b> {user.likes}\n"
            f"👍 <b>Лайков:</b> {user.likes_count}\n"
            f"🎁 <b>Розыгрышей:</b> {user.giveaways}\n"
            f"🏆 <b>Трофеев:</b> {user.trophies}\n"
            f"👥 <b>Подписчиков:</b> {user.followers}\n"
            f"👤 <b>Подписок:</b> {user.subscriptions}\n"
            f"⏳ <b>Дата регистрации:</b> {user.registration_date}\n"
            f"✅ <b>Заблокирован:</b> {'Да' if user.banned else 'Нет'}"
        )
