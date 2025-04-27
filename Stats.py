# meta developer: @sunshinelzt

from .. import loader, utils
from telethon.tl.functions.contacts import GetBlockedRequest
from telethon.tl.functions.messages import GetDialogFiltersRequest
from datetime import datetime, timedelta
import time

@loader.tds
class EnhancedStats(loader.Module):
    """Расширенная статистика аккаунта с детальным анализом"""

    strings = {
        "name": "EnhancedStats",
        
        "stats": """
<emoji document_id=5774022692642492953>✅</emoji><b> Account Statistics</b>

</b><emoji document_id=5208454037531280484>💜</emoji><b> Total chats: </b><code>{all_chats}</code><b>

</b><emoji document_id=6035084557378654059>👤</emoji><b> Private chats: </b><code>{users}</code><b>
  <b>Ͱ</b> Active today: <code>{active_users_today}</code>
  <b>Ͱ</b> Active this week: <code>{active_users_week}</code>
</b><emoji document_id=6030400221232501136>🤖</emoji><b> Bots: </b><code>{bots}</code><b>
</b><emoji document_id=6032609071373226027>👥</emoji><b> Groups: </b><code>{groups}</code><b>
  <b>Ͱ</b> Small groups (≤100): <code>{small_groups}</code>
  <b>Ͱ</b> Large groups (>100): <code>{large_groups}</code>
</b><emoji document_id=5870886806601338791>👥</emoji><b> Channels: </b><code>{channels}</code><b>
</b><emoji document_id=5870563425628721113>📨</emoji><b> Archived chats: </b><code>{archived}</code><b>
</b><emoji document_id=5870948572526022116>✋</emoji><b> Total blocked: </b><code>{blocked}</code>
  <b>Ͱ</b><emoji document_id=6035084557378654059>👤</emoji><b> Users: </b><code>{blocked_users}</code>
  <b>Ͱ</b><emoji document_id=6030400221232501136>🤖</emoji><b> Bots: </b><code>{blocked_bots}</code>

</b><emoji document_id=5431456208487471643>🗂</emoji><b> Folders: </b><code>{folders}</code><b>

</b><emoji document_id=5210953444764963840>💬</emoji><b> Messages statistics:</b><b>
  <b>Ͱ</b> Unread messages: <code>{unread_messages}</code>
  <b>Ͱ</b> Unread mentions: <code>{unread_mentions}</code>

</b><emoji document_id=5787237370709413702>⏱</emoji><b> Account activity:</b><b>
  <b>Ͱ</b> Online time today: <code>{online_time}</code>
  <b>Ͱ</b> Most active chat: <code>{most_active_chat}</code>
  <b>Ͱ</b> Messages sent today: <code>{sent_today}</code>

</b><emoji document_id=5409183589017854327>🔄</emoji><b> Last update: </b><code>{last_update}</code>""",

        "chat_stats": """
<emoji document_id=5774022692642492953>✅</emoji><b> Chat Statistics for {chat_name}</b>

<emoji document_id=6035084557378654059>👤</emoji><b> Members: </b><code>{members}</code>
<emoji document_id=5210953444764963840>💬</emoji><b> Total messages: </b><code>{total_messages}</code>
<emoji document_id=5787237370709413702>⏱</emoji><b> Created: </b><code>{created_date}</code>
<emoji document_id=5431456208487471643>🗂</emoji><b> Your messages: </b><code>{user_messages}</code>
<emoji document_id=5215361797921465842>📊</emoji><b> Your contribution: </b><code>{contribution}%</code>
<emoji document_id=5188406776288981282>🔤</emoji><b> Media count: </b><code>{media_count}</code>""",

        "loading_stats": "<b><emoji document_id=5309893756244206277>🫥</emoji> Loading statistics...</b>",
        "loading_chat_stats": "<b><emoji document_id=5309893756244206277>🫥</emoji> Loading chat statistics...</b>",
        "no_chat": "<b><emoji document_id=5854929766146118183>❌</emoji> Please specify a chat or reply to a message from the chat.</b>",
        "no_such_chat": "<b><emoji document_id=5854929766146118183>❌</emoji> Chat not found.</b>",
    }

    strings_ru = {
        "name": "EnhancedStats",
        
        "stats": """
<emoji document_id=5774022692642492953>✅</emoji><b> Статистика аккаунта</b>

</b><emoji document_id=5208454037531280484>💜</emoji><b> Всего чатов: </b><code>{all_chats}</code><b>

</b><emoji document_id=6035084557378654059>👤</emoji><b> Личных чатов: </b><code>{users}</code><b>
  <b>Ͱ</b> Активных сегодня: <code>{active_users_today}</code>
  <b>Ͱ</b> Активных за неделю: <code>{active_users_week}</code>
</b><emoji document_id=6030400221232501136>🤖</emoji><b> Ботов: </b><code>{bots}</code><b>
</b><emoji document_id=6032609071373226027>👥</emoji><b> Групп: </b><code>{groups}</code><b>
  <b>Ͱ</b> Малых групп (≤100): <code>{small_groups}</code>
  <b>Ͱ</b> Больших групп (>100): <code>{large_groups}</code>
</b><emoji document_id=5870886806601338791>👥</emoji><b> Каналов: </b><code>{channels}</code><b>
</b><emoji document_id=5870563425628721113>📨</emoji><b> Архивированных чатов: </b><code>{archived}</code><b>
</b><emoji document_id=5870948572526022116>✋</emoji><b> Всего заблокированных: </b><code>{blocked}</code>
  <b>Ͱ</b><emoji document_id=6035084557378654059>👤</emoji><b> Пользователи: </b><code>{blocked_users}</code>
  <b>Ͱ</b><emoji document_id=6030400221232501136>🤖</emoji><b> Боты: </b><code>{blocked_bots}</code>

</b><emoji document_id=5431456208487471643>🗂</emoji><b> Папки: </b><code>{folders}</code><b>

</b><emoji document_id=5210953444764963840>💬</emoji><b> Статистика сообщений:</b><b>
  <b>Ͱ</b> Непрочитанных сообщений: <code>{unread_messages}</code>
  <b>Ͱ</b> Непрочитанных упоминаний: <code>{unread_mentions}</code>

</b><emoji document_id=5787237370709413702>⏱</emoji><b> Активность аккаунта:</b><b>
  <b>Ͱ</b> Время онлайн сегодня: <code>{online_time}</code>
  <b>Ͱ</b> Самый активный чат: <code>{most_active_chat}</code>
  <b>Ͱ</b> Отправлено сообщений сегодня: <code>{sent_today}</code>

</b><emoji document_id=5409183589017854327>🔄</emoji><b> Последнее обновление: </b><code>{last_update}</code>""",

        "chat_stats": """
<emoji document_id=5774022692642492953>✅</emoji><b> Статистика чата {chat_name}</b>

<emoji document_id=6035084557378654059>👤</emoji><b> Участников: </b><code>{members}</code>
<emoji document_id=5210953444764963840>💬</emoji><b> Всего сообщений: </b><code>{total_messages}</code>
<emoji document_id=5787237370709413702>⏱</emoji><b> Создан: </b><code>{created_date}</code>
<emoji document_id=5431456208487471643>🗂</emoji><b> Ваших сообщений: </b><code>{user_messages}</code>
<emoji document_id=5215361797921465842>📊</emoji><b> Ваш вклад: </b><code>{contribution}%</code>
<emoji document_id=5188406776288981282>🔤</emoji><b> Количество медиа: </b><code>{media_count}</code>""",

        "loading_stats": "<b><emoji document_id=5309893756244206277>🫥</emoji> Загрузка статистики...</b>",
        "loading_chat_stats": "<b><emoji document_id=5309893756244206277>🫥</emoji> Загрузка статистики чата...</b>",
        "no_chat": "<b><emoji document_id=5854929766146118183>❌</emoji> Пожалуйста, укажите чат или ответьте на сообщение из чата.</b>",
        "no_such_chat": "<b><emoji document_id=5854929766146118183>❌</emoji> Чат не найден.</b>",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            "online_time_tracking", False, "Отслеживать время онлайн",
            "track_sent_messages", False, "Отслеживать отправленные сообщения",
        )
        self.online_start = time.time()
        self.sent_messages_today = 0
        self.active_chats = {}

    async def client_ready(self, client, db):
        self.db = db
        self._client = client
        
        # Initialize stats tracking
        if self.get("last_day") != datetime.now().day:
            self.set("last_day", datetime.now().day)
            self.set("sent_today", 0)
            self.set("online_time", 0)
        
        # Message tracking
        if self.config["track_sent_messages"]:
            client.add_event_handler(self._message_handler, events=events.NewMessage(outgoing=True))
        
        # Online tracking
        if self.config["online_time_tracking"]:
            self._update_online_time()
    
    async def _message_handler(self, event):
        # Track sent messages
        sent_today = self.get("sent_today", 0)
        self.set("sent_today", sent_today + 1)
        
        # Track active chats
        chat_id = utils.get_chat_id(event)
        active_chats = self.get("active_chats", {})
        active_chats[str(chat_id)] = active_chats.get(str(chat_id), 0) + 1
        self.set("active_chats", active_chats)
    
    def _update_online_time(self):
        # Update online time
        current_time = time.time()
        online_time = self.get("online_time", 0)
        online_time += current_time - self.online_start
        self.set("online_time", online_time)
        self.online_start = current_time
    
    def _format_time(self, seconds):
        hours, remainder = divmod(int(seconds), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    @loader.command()
    async def stats(self, message):
        """Получить расширенную статистику аккаунта"""
        await utils.answer(message, self.strings['loading_stats'])
        
        users = 0
        bots = 0
        groups = 0
        small_groups = 0
        large_groups = 0
        channels = 0
        all_chats = 0
        archived = 0
        blocked_bots = 0
        blocked_users = 0
        unread_messages = 0
        unread_mentions = 0
        active_users_today = 0
        active_users_week = 0
        
        # Update online time before getting stats
        if self.config["online_time_tracking"]:
            self._update_online_time()
        
        # Get blocked users
        limit = 100
        offset = 0
        total_blocked = 0
        while True:
            blocked_chats = await self._client(GetBlockedRequest(offset=offset, limit=limit))
            for user in blocked_chats.users:
                if user.bot:
                    blocked_bots += 1
                else:
                    blocked_users += 1
            blocked = len(blocked_chats.users)
            total_blocked += blocked

            if blocked < limit:
                break

            offset += limit
        
        # Get folders
        try:
            folders = await self._client(GetDialogFiltersRequest())
            folders_count = len(folders)
        except:
            folders_count = 0
        
        # Initialize most active chat
        most_active_chat = "None"
        max_activity = 0
        active_chats = self.get("active_chats", {})
        
        # Process all dialogs
        now = datetime.now()
        today = now - timedelta(days=1)
        week_ago = now - timedelta(days=7)
        
        async for dialog in self._client.iter_dialogs():
            if getattr(dialog, "archived", False):
                archived += 1
                
            unread_messages += dialog.unread_count
            unread_mentions += dialog.unread_mentions_count
            
            # Update most active chat
            chat_id = str(utils.get_chat_id(dialog))
            if chat_id in active_chats and active_chats[chat_id] > max_activity:
                max_activity = active_chats[chat_id]
                if hasattr(dialog.entity, "title"):
                    most_active_chat = dialog.entity.title
                elif hasattr(dialog.entity, "first_name"):
                    name_parts = []
                    if dialog.entity.first_name:
                        name_parts.append(dialog.entity.first_name)
                    if hasattr(dialog.entity, "last_name") and dialog.entity.last_name:
                        name_parts.append(dialog.entity.last_name)
                    most_active_chat = " ".join(name_parts)
            
            # Process by chat type
            if dialog.is_user:
                if getattr(dialog.entity, "bot", False):
                    bots += 1
                    all_chats += 1
                else:
                    users += 1
                    all_chats += 1
                    
                    # Check activity (for users only)
                    if hasattr(dialog.entity, "status"):
                        if hasattr(dialog.entity.status, "was_online"):
                            last_online = dialog.entity.status.was_online
                            if last_online and last_online > today:
                                active_users_today += 1
                            if last_online and last_online > week_ago:
                                active_users_week += 1
                                
            elif getattr(dialog, "is_group", False):
                groups += 1
                all_chats += 1
                
                # Differentiate between small and large groups
                if hasattr(dialog, "entity") and hasattr(dialog.entity, "participants_count"):
                    if dialog.entity.participants_count <= 100:
                        small_groups += 1
                    else:
                        large_groups += 1
                else:
                    small_groups += 1  # Default to small if can't determine
                    
            elif dialog.is_channel:
                if getattr(dialog.entity, "megagroup", False) or getattr(dialog.entity, "gigagroup", False):
                    groups += 1
                    all_chats += 1
                    
                    # Differentiate between small and large groups for megagroups
                    if hasattr(dialog.entity, "participants_count"):
                        if dialog.entity.participants_count <= 100:
                            small_groups += 1
                        else:
                            large_groups += 1
                    else:
                        small_groups += 1  # Default to small if can't determine
                        
                elif getattr(dialog.entity, "broadcast", False):
                    channels += 1
                    all_chats += 1
        
        # Format online time
        online_time = self._format_time(self.get("online_time", 0))
        sent_today = self.get("sent_today", 0)
        last_update = now.strftime("%d.%m.%Y %H:%M:%S")
        
        await utils.answer(
            message, 
            self.strings("stats", message).format(
                users=users, 
                bots=bots, 
                channels=channels,
                groups=groups, 
                small_groups=small_groups,
                large_groups=large_groups,
                all_chats=all_chats,
                blocked=total_blocked, 
                archived=archived, 
                blocked_users=blocked_users,
                blocked_bots=blocked_bots,
                folders=folders_count,
                unread_messages=unread_messages,
                unread_mentions=unread_mentions,
                active_users_today=active_users_today,
                active_users_week=active_users_week,
                online_time=online_time,
                most_active_chat=most_active_chat,
                sent_today=sent_today,
                last_update=last_update
            )
        )

    @loader.command()
    async def chatstats(self, message):
        """[chat_id]* - Получить статистику указанного чата"""
        args = utils.get_args_raw(message)
        
        await utils.answer(message, self.strings['loading_chat_stats'])
        
        if args:
            try:
                chat = await self._client.get_entity(args)
            except ValueError:
                return await utils.answer(message, self.strings['no_such_chat'])
        else:
            if message.is_reply:
                reply = await message.get_reply_message()
                chat = await reply.get_chat()
            else:
                chat = await message.get_chat()
                if chat.id == message.sender_id:
                    return await utils.answer(message, self.strings['no_chat'])
        
        # Get chat name
        if hasattr(chat, "title"):
            chat_name = chat.title
        elif hasattr(chat, "first_name"):
            name_parts = []
            if chat.first_name:
                name_parts.append(chat.first_name)
            if hasattr(chat, "last_name") and chat.last_name:
                name_parts.append(chat.last_name)
            chat_name = " ".join(name_parts)
        else:
            chat_name = str(chat.id)
        
        # Get basic chat info
        members = 0
        if hasattr(chat, "participants_count"):
            members = chat.participants_count
        
        # Get creation date if available
        created_date = "Unknown"
        if hasattr(chat, "date"):
            created_date = chat.date.strftime("%d.%m.%Y")
        
        # Count total messages (approximation for large chats)
        total_messages = 0
        user_messages = 0
        media_count = 0
        
        try:
            # Try to get full stats with a reasonable limit
            async for msg in self._client.iter_messages(chat, limit=1000):
                total_messages += 1
                if msg.sender_id == self._client.uid:
                    user_messages += 1
                if msg.media:
                    media_count += 1
                    
        except Exception:
            # Fallback if we can't get messages
            total_messages = "N/A"
            user_messages = "N/A"
            media_count = "N/A"
            
        # Calculate contribution
        if isinstance(total_messages, int) and isinstance(user_messages, int) and total_messages > 0:
            contribution = round((user_messages / total_messages) * 100, 2)
        else:
            contribution = "N/A"
            
        await utils.answer(
            message,
            self.strings("chat_stats").format(
                chat_name=chat_name,
                members=members,
                total_messages=total_messages,
                created_date=created_date,
                user_messages=user_messages,
                contribution=contribution,
                media_count=media_count
            )
        )
    
    @loader.command()
    async def resetstats(self, message):
        """Сбросить счетчики статистики"""
        self.set("sent_today", 0)
        self.set("online_time", 0)
        self.set("active_chats", {})
        self.online_start = time.time()
        await utils.answer(message, "<emoji document_id=5774022692642492953>✅</emoji> <b>Счетчики статистики сброшены</b>")
