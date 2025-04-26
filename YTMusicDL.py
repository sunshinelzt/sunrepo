# meta developer: @sunshinelzt
# meta pic: https://img.icons8.com/color/48/000000/youtube-music.png
# scope: hikka_only
# scope: hikka_min 1.0.0

import os
import re
import asyncio
import logging
from typing import Union

from telethon import events
from telethon.tl.types import DocumentAttributeAudio
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from .. import loader, utils

logger = logging.getLogger(__name__)

@loader.tds
class YTMusicDLMod(loader.Module):
    """Модуль для скачивания музыки с YouTube и YouTube Music"""
    
    strings = {
        "name": "YTMusicDL",
        "downloading": "<b><emoji document_id=5463107823946717464>🎵</emoji> <i>Скачиваю трек...</i></b>",
        "searching": "<b><emoji document_id=5231012545799666522>🔍</emoji> <i>Ищу</i> <code>{}</code> <i>на YouTube...</i></b>",
        "uploading": "<b><emoji document_id=5445355530111437729>📤</emoji> <i>Загружаю трек...</i></b>",
        "success": "<b><emoji document_id=5776375003280838798>✅</emoji> <i>Трек успешно загружен!</i></b>\n\n<b><emoji document_id=5891249688933305846>🎵</emoji> Название:</b> <code>{}</code>\n<b><emoji document_id=5879770735999717115>👤</emoji> Исполнитель:</b> <code>{}</code>\n<b><emoji document_id=5936170807716745162>🎛</emoji> Длительность:</b> <code>{}</code>",
        "error": "<b><emoji document_id=5210952531676504517>❌</emoji> <i>Произошла ошибка при скачивании:</i></b>\n\n<code>{}</code>",
        "no_results": "<b><emoji document_id=5210952531676504517>❌</emoji> <i>По запросу</i> <code>{}</code> <i>ничего не найдено</i></b>",
        "processing": "<b><emoji document_id=5341715473882955310>⚙️</emoji> <i>Обработка...</i></b>",
        "starting": "<b><emoji document_id=5188481279963715781>🚀</emoji> <i>Начинаю загрузку...</i></b>",
    }
    
    async def client_ready(self, client, db):
        """Вызывается при готовности клиента"""
        self.client = client
        self.db = db
    
    @loader.owner
    @loader.command(ru_doc="[ссылка или название] - Скачать музыку с YouTube")
    async def yt(self, message):
        """[ссылка или название] - Скачать музыку с YouTube"""
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, "Укажите ссылку на видео или название трека")
            return
        
        status_message = await utils.answer(message, self.strings["starting"])
        
        youtube_regex = r"(?:https?:\/\/)?(?:www\.)?(?:youtube\.com|youtu\.be)\/(?:watch\?v=)?([^\s&]+)"
        youtube_music_regex = r"(?:https?:\/\/)?(?:www\.)?music\.youtube\.com\/watch\?v=([^\s&]+)"
        
        youtube_match = re.match(youtube_regex, args)
        youtube_music_match = re.match(youtube_music_regex, args)
        
        if youtube_match or youtube_music_match:
            video_url = args
            await utils.answer(status_message, self.strings["downloading"])
        else:
            await utils.answer(status_message, self.strings["searching"].format(args))
            search_query = f"ytsearch1:{args}"
            
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "format": "bestaudio/best",
                "extract_flat": True,
            }
            
            try:
                with YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(search_query, download=False)
                    if not info or "entries" not in info or not info["entries"]:
                        await utils.answer(status_message, self.strings["no_results"].format(args))
                        return
                    
                    video_url = f"https://www.youtube.com/watch?v={info['entries'][0]['id']}"
            except Exception as e:
                logger.error(f"Ошибка поиска: {e}")
                await utils.answer(status_message, self.strings["error"].format(str(e)))
                return
        
        await utils.answer(status_message, self.strings["processing"])
        
        output_dir = os.path.join("downloads", "ytmusic")
        os.makedirs(output_dir, exist_ok=True)
        
        output_file = os.path.join(output_dir, "%(title)s.%(ext)s")
        
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": output_file,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "320",
            }],
            "quiet": True,
            "no_warnings": True,
        }
        
        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=True)
                filepath = ydl.prepare_filename(info).replace(f".{info['ext']}", ".mp3")
                
                title = info.get("title", "Unknown")
                artist = info.get("artist", info.get("uploader", "Unknown"))
                duration = self.format_duration(info.get("duration", 0))
        except DownloadError as e:
            await utils.answer(status_message, self.strings["error"].format(str(e)))
            return
        except Exception as e:
            logger.error(f"Ошибка загрузки: {e}")
            await utils.answer(status_message, self.strings["error"].format(str(e)))
            return
        
        await utils.answer(status_message, self.strings["uploading"])
        
        try:
            await self.client.send_file(
                message.chat_id,
                filepath,
                caption=self.strings["success"].format(title, artist, duration),
                reply_to=message.reply_to_msg_id if message.reply_to_msg_id else None,
                attributes=[
                    DocumentAttributeAudio(
                        duration=info.get("duration", 0),
                        title=title,
                        performer=artist,
                    )
                ],
            )
            
            await status_message.delete()
            os.remove(filepath)
        except Exception as e:
            logger.error(f"Ошибка отправки файла: {e}")
            await utils.answer(status_message, self.strings["error"].format(str(e)))
            
            if os.path.exists(filepath):
                os.remove(filepath)
            
            return
    
    def format_duration(self, seconds: int) -> str:
        """Форматирует длительность в удобочитаемый формат"""
        if not seconds:
            return "Неизвестно"
        
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        
        if hours:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"
