# -*- coding: utf-8 -*- 
# Улучшенный экспорт чатов для Hikka Userbot
# Поддержка фото, видео, стикеров, голосовых, реакций, JSON и красивый HTML-дизайн
# meta developer: @sunshinelzt

from telethon.tl.functions.messages import GetHistoryRequest
from telethon.utils import get_display_name
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument, MessageMediaWebPage, MessageMediaVoice, MessageMediaContact, MessageMediaGeo, MessageMediaPoll, MessageMediaDice, MessageReaction
import os
import json
import shutil
from datetime import datetime
from .. import loader, utils

class ExportChatMod(loader.Module):
    """Экспорт чата в HTML с медиа, архивом и JSON"""
    strings = {"name": "ExportChat"}

    async def exportcmd(self, message):
        """Использование: .export <ссылка/ID чата>"""
        args = utils.get_args_raw(message)
        if not args:
            return await message.delete()

        chat = await self.client.get_entity(args)
        chat_name = get_display_name(chat)
        chat_id = chat.id
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        base_folder = f"export_{chat_id}_{timestamp}"
        os.makedirs(f"{base_folder}/photos", exist_ok=True)
        os.makedirs(f"{base_folder}/videos", exist_ok=True)
        os.makedirs(f"{base_folder}/documents", exist_ok=True)
        os.makedirs(f"{base_folder}/voices", exist_ok=True)
        os.makedirs(f"{base_folder}/stickers", exist_ok=True)

        messages_list = []
        offset_id = 0
        limit = 100  

        while True:
            history = await self.client(GetHistoryRequest(
                peer=chat, offset_id=offset_id, limit=limit, max_id=0, min_id=0, hash=0
            ))

            if not history.messages:
                break

            for msg in history.messages:
                reactions = ""
                if isinstance(msg.reactions, MessageReaction):
                    reactions = " ".join([f"{r.reaction} ({r.count})" for r in msg.reactions.results])

                msg_data = {
                    "id": msg.id,
                    "date": msg.date.strftime("%Y-%m-%d %H:%M:%S"),
                    "sender_id": msg.sender_id,
                    "text": msg.message or "",
                    "media": None,
                    "reactions": reactions
                }

                if msg.media:
                    media_path = None
                    if isinstance(msg.media, MessageMediaPhoto):
                        media_path = await self.client.download_media(msg, file=f"{base_folder}/photos/{msg.id}.jpg")
                    elif isinstance(msg.media, MessageMediaDocument):
                        media_path = await self.client.download_media(msg, file=f"{base_folder}/documents/{msg.id}")
                    elif isinstance(msg.media, MessageMediaVoice):
                        media_path = await self.client.download_media(msg, file=f"{base_folder}/voices/{msg.id}.ogg")

                    if media_path:
                        msg_data["media"] = os.path.basename(media_path)

                messages_list.append(msg_data)
            offset_id = history.messages[-1].id

        json_path = f"{base_folder}/chat.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(messages_list, f, ensure_ascii=False, indent=4)

        html_path = f"{base_folder}/chat.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(f"""<html><head><meta charset='utf-8'><title>{chat_name}</title>
            <style>
                body {{ font-family: Arial, sans-serif; background: #181818; color: #e0e0e0; padding: 20px; }}
                .msg {{ padding: 10px; border-bottom: 1px solid #444; }}
                img {{ max-width: 300px; border-radius: 5px; transition: 0.3s; }}
                img:hover {{ transform: scale(1.05); }}
                .reaction {{ color: #f1c40f; }}
                .media img, video, audio {{ max-width: 100%; margin-top: 5px; }}
                h1 {{ color: #f39c12; }}
            </style></head><body>""")
            f.write(f"<h1>Чат: {chat_name}</h1>")
            for msg in messages_list:
                f.write(f"<div class='msg'><b>{msg['date']} - {msg['sender_id']}</b>: {msg['text']}")
                if msg["reactions"]:
                    f.write(f" <span class='reaction'>({msg['reactions']})</span>")
                f.write("</div>")
                if msg["media"]:
                    f.write(f'<div class="media"><img src="photos/{msg["media"]}"></div>')
            f.write("</body></html>")

        archive_path = f"{base_folder}.zip"
        shutil.make_archive(base_folder, "zip", base_folder)

        await self.client.send_file("me", archive_path, caption=f"📂 Архив чата **{chat_name}**")

        shutil.rmtree(base_folder)
        os.remove(archive_path)

        await message.delete()
