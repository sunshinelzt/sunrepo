# meta developer: @sunshinelzt
# meta pic: https://img.icons8.com/color/48/000000/youtube-music.png
# scope: hikka_only
# scope: hikka_min 1.0.0

import os
import re
import sys
import asyncio
import logging
import tempfile
import platform
from typing import Union, Optional

from telethon import events
from telethon.tl.types import DocumentAttributeAudio
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from .. import loader, utils

logger = logging.getLogger(__name__)

@loader.tds
class YTMusicDLMod(loader.Module):
    """Модуль для скачивания музыки с YouTube и YouTube Music с поддержкой cookies"""
    
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
        "config_cookies": "Используемый браузер для cookies (chrome, firefox, opera, edge, safari, brave)",
        "config_quality": "Качество скачиваемой музыки (от 128 до 320)",
        "config_max_duration": "Максимальная продолжительность аудио (в минутах, 0 - без ограничений)",
    }
    
    def __init__(self):
        self.config = loader.ModuleConfig(
            "browser", "chrome", lambda: self.strings["config_cookies"],
            "quality", "320", lambda: self.strings["config_quality"],
            "max_duration", 0, lambda: self.strings["config_max_duration"],
        )
    
    async def client_ready(self, client, db):
        """Вызывается при готовности клиента"""
        self.client = client
        self.db = db
    
    def get_browser_cookies_path(self) -> Optional[str]:
        """Получает путь к cookies для указанного браузера"""
        browser = self.config["browser"].lower()
        
        if browser not in ["chrome", "firefox", "opera", "edge", "safari", "brave"]:
            return None
            
        return browser
    
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
            
            ydl_opts = self.get_ydl_opts(download=False)
            
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
        
        # Проверка предварительной информации о треке
        try:
            with YoutubeDL(self.get_ydl_opts(download=False)) as ydl:
                info = ydl.extract_info(video_url, download=False)
                
                # Проверка максимальной продолжительности
                max_duration = self.config["max_duration"]
                if max_duration > 0 and info.get("duration", 0) > max_duration * 60:
                    await utils.answer(status_message, f"<b><emoji document_id=5210952531676504517>❌</emoji> <i>Трек слишком длинный! Максимальная продолжительность: {max_duration} минут</i></b>")
                    return
        except Exception as e:
            logger.error(f"Ошибка получения информации: {e}")
            # Продолжаем выполнение, так как это необязательная проверка
        
        # Создаем временную директорию для скачивания
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = os.path.join(temp_dir, "%(title)s.%(ext)s")
            
            ydl_opts = self.get_ydl_opts(output_file=output_file)
            
            try:
                with YoutubeDL(ydl_opts) as ydl:
                    await utils.answer(status_message, self.strings["downloading"])
                    info = ydl.extract_info(video_url, download=True)
                    filepath = ydl.prepare_filename(info).replace(f".{info['ext']}", ".mp3")
                    
                    title = info.get("title", "Unknown")
                    artist = info.get("artist", info.get("uploader", "Unknown"))
                    duration = self.format_duration(info.get("duration", 0))
                    
                    await utils.answer(status_message, self.strings["uploading"])
                    
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
            except DownloadError as e:
                await utils.answer(status_message, self.strings["error"].format(str(e)))
                return
            except Exception as e:
                logger.error(f"Ошибка загрузки: {e}")
                await utils.answer(status_message, self.strings["error"].format(str(e)))
                return
    
    def get_ydl_opts(self, output_file=None, download=True):
        """Получает настройки для yt-dlp с учетом cookies"""
        cookies_browser = self.get_browser_cookies_path()
        quality = self.config["quality"]
        
        # Проверка качества
        try:
            quality_int = int(quality)
            if quality_int < 128:
                quality = "128"
            elif quality_int > 320:
                quality = "320"
        except:
            quality = "320"
        
        ydl_opts = {
            "format": "bestaudio/best",
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "nocheckcertificate": True,
            "ignoreerrors": False,
            "logtostderr": False,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "geo_bypass": True,
            "geo_bypass_country": "US",
            "no_color": True,
            "socket_timeout": 15,
        }
        
        # Добавляем cookies из браузера, если указан
        if cookies_browser:
            ydl_opts["cookiesfrombrowser"] = (cookies_browser,)
        
        # Если это запрос на скачивание
        if download and output_file:
            ydl_opts.update({
                "outtmpl": output_file,
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": quality,
                }],
            })
        else:
            # Если это только запрос на информацию
            ydl_opts["extract_flat"] = True
        
        return ydl_opts
    
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
