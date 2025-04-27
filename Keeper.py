# meta developer: @sunshinelzt

import io
from telethon import types
from .. import loader, utils

@loader.tds
class KeeperMod(loader.Module):
    """Модуль для моментального сохранения самоуничтожающихся медиа"""
    strings = {"name": "Keeper"}

    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        self._me = await client.get_me()

    def is_self_destruct(self, media):
        """Быстрая проверка: медиа с таймером или на один просмотр"""
        return getattr(media, 'ttl_seconds', None) or getattr(media, 'has_view_once', False)

    @loader.owner
    async def kpcmd(self, m):
        """Забрать медиа по реплаю"""
        reply = await m.get_reply_message()
        if not reply or not reply.media or not self.is_self_destruct(reply.media):
            return await m.delete()
        
        await m.delete()
        media_bytes = await reply.download_media(bytes)
        
        file = io.BytesIO(media_bytes)
        ext = utils.get_extension(reply) or ".jpg"
        file.name = getattr(reply.file, "name", f"media{ext}")
        
        await self.client.send_file("me", file)

    @loader.owner
    async def akpcmd(self, m):
        """Включить/выключить автосохранение"""
        state = self.db.get("Keeper", "state", False)
        
        # Печать текущего состояния автосохранения
        if state:
            print("Автосохранение включено.")
        else:
            print("Автосохранение выключено.")
        
        # Переключение состояния автосохранения
        self.db.set("Keeper", "state", not state)
        
        await m.delete()

    async def watcher(self, m):
        if not m or not self.db.get("Keeper", "state", False):
            return

        if not m.media or not self.is_self_destruct(m.media):
            return
            
        if m.sender_id == self._me.id:
            return

        media_bytes = await m.download_media(bytes)
        file = io.BytesIO(media_bytes)
        ext = utils.get_extension(m) or ".jpg"
        file.name = getattr(m.file, "name", f"media{ext}")
        
        sender = m.sender
        caption = f"<b>Keeper</b> | {getattr(sender, 'first_name', '')} | ID: {sender.id}" if sender else "<b>Keeper</b>"
        
        await self.client.send_file("me", file, caption=caption)
