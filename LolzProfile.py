# meta developer: @sunshinelzt

import LOLZTEAM
from telethon.tl.functions.users import GetFullUserRequest
from hikka import loader, utils

class LolzProfile(loader.Module):
    """Модуль для получения информации о профиле пользователя на форуме lolz.live"""
    strings = {"name": "LolzProfile"}

    def __init__(self):
        self.config = loader.ModuleConfig(
            "LOLZ_API_KEY", "", "API-ключ форума lolz.live"
        )
        self.client = None

    async def client_ready(self, client, db):
        api_key = self.config["LOLZ_API_KEY"]
        if api_key:
            self.client = LOLZTEAM.Client(api_key)
        self.tg_client = client

    async def lolzcmd(self, message):
        """Использование: .lolz <реплай/@юзернейм/ник>
        Получает информацию о профиле пользователя на lolz.live.
        """
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
            return await message.edit("<b>🚫 Укажите никнейм или ответьте на сообщение.</b>")

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
            response = self.client.user.search(username=tg_username)
            return response[0] if response else None
        except Exception:
            return None

    async def get_user_info_by_nickname(self, nickname):
        """Получает информацию о пользователе на форуме по нику."""
        if not self.client:
            return None
        try:
            return self.client.user.get(nickname)
        except Exception:
            return None

    def format_profile(self, user):
        """Форматирует информацию о пользователе для отображения."""
        return (
            f"👤 <b>Профиль:</b> <a href='https://lolz.live/members/{user.id}/'>{user.username}</a>\n"
            f"🆔 <b>ID:</b> {user.id}\n"
            f"🏷 <b>Группа:</b> {user.group_title}\n"
            f"📝 <b>Статус:</b> {user.custom_title or '—'}\n"
            f"📅 <b>Регистрация:</b> {user.register_date}\n"
            f"📊 <b>Статистика:</b>\n"
            f"   💬 Сообщений: {user.message_count}\n"
            f"   ❤️ Лайков: {user.like_count}\n"
            f"   🔥 Реакций: {user.reaction_score}\n"
            f"   🎁 Розыгрышей: {user.raffle_count}\n"
            f"   🏆 Трофеев: {user.trophy_points}\n"
            f"   👥 Подписчики: {user.followers_count}\n"
            f"   📌 Подписки: {user.following_count}\n"
            f"🛡 <b>Аккаунт:</b> {'🔴 Заблокирован' if user.is_banned else '🟢 Активен'}"
        )
