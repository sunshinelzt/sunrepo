import io
import re
import requests
from ShazamAPI import Shazam
from .. import loader, utils

@loader.tds
class ShazamMod(loader.Module):
    """Recognize songs from audio/video files or voice messages using Shazam API"""
    
    strings = {
        "name": "Shazam",
        "downloading": "<emoji document_id=5443127283898405358>🔥</emoji> <b>Downloading media...</b>",
        "searching": "<emoji document_id=5447410659077661506>🔍</emoji> <b>Searching for song...</b>",
        "no_reply": "<emoji document_id=5294339927318739359>❌</emoji> <b>Please reply to an audio/video message.</b>",
        "not_found": "<emoji document_id=5210952531676504517>🫣</emoji> <b>Song not found.</b>",
        "error_processing": "<emoji document_id=5312526098750252863>⚠️</emoji> <b>Error processing file: {}</b>",
        "track_info": (
            "<emoji document_id=5325547803936572038>✨</emoji> <b>Song found!</b>\n\n"
            '<emoji document_id=5460795800101594035>🎵</emoji> <b>Title:</b> "<code>{title}</code>"\n'
            '<emoji document_id=5373141891321699086>👤</emoji> <b>Artist:</b> "<code>{artist}</code>"\n'
            '<emoji document_id=5431376038628171216>💽</emoji> <b>Album:</b> "<code>{album}</code>"\n\n'
            '<emoji document_id=5188705588925702510>🔗</emoji> <b>Listen on:</b>\n'
            '{links}'
        ),
        "processing_time": "<emoji document_id=5420689925493313072>⏱</emoji> <b>Processing time:</b> {time}s"
    }
    
    strings_ru = {
        "downloading": "<emoji document_id=5443127283898405358>🔥</emoji> <b>Загрузка файла...</b>",
        "searching": "<emoji document_id=5447410659077661506>🔍</emoji> <b>Поиск песни...</b>",
        "no_reply": "<emoji document_id=5294339927318739359>❌</emoji> <b>Ответьте на аудио/видео сообщение</b>",
        "not_found": "<emoji document_id=5210952531676504517>🫣</emoji> <b>Не удалось найти песню</b>",
        "error_processing": "<emoji document_id=5312526098750252863>⚠️</emoji> <b>Ошибка обработки файла: {}</b>",
        "track_info": (
            "<emoji document_id=5325547803936572038>✨</emoji> <b>Песня найдена!</b>\n\n"
            '<emoji document_id=5460795800101594035>🎵</emoji> <b>Название:</b> "<code>{title}</code>"\n'
            '<emoji document_id=5373141891321699086>👤</emoji> <b>Исполнитель:</b> "<code>{artist}</code>"\n'
            '<emoji document_id=5431376038628171216>💽</emoji> <b>Альбом:</b> "<code>{album}</code>"\n\n'
            '<emoji document_id=5188705588925702510>🔗</emoji> <b>Слушать на:</b>\n'
            '{links}'
        ),
        "processing_time": "<emoji document_id=5420689925493313072>⏱</emoji> <b>Время обработки:</b> {time}с",
        "released": "<emoji document_id=5469741319330996757>📅</emoji> <b>Дата выхода:</b> <code>{date}</code>",
        "genre": "<emoji document_id=5470094069289984325>🎸</emoji> <b>Жанр:</b> <code>{genre}</code>",
        "lyrics_preview": "<emoji document_id=5469998152712266576>📝</emoji> <b>Текст песни (отрывок):</b>\n<i>{lyrics}</i>"
    }

    async def fetch_media(self, message):
        """Extract audio from various media types"""
        reply = await message.get_reply_message()
        
        if not reply:
            await utils.answer(message, self.strings['no_reply'])
            return None, None
            
        # Check if the message contains audio or video
        is_voice = reply.document and getattr(reply.document, 'attributes', None) and any(
            getattr(attr, 'CONSTRUCTOR_ID', None) == 0x6B8D29C1 
            for attr in reply.document.attributes
        )
        
        is_audio = (
            reply.audio or 
            (reply.document and reply.document.mime_type and 
             reply.document.mime_type.startswith(("audio/", "video/", "application/ogg"))) or
            is_voice
        )
        
        is_video = reply.video or (reply.document and reply.document.mime_type and 
                                   reply.document.mime_type.startswith("video/"))
        
        if not (is_audio or is_video):
            await utils.answer(message, self.strings['no_reply'])
            return None, None
        
        try:
            await utils.answer(message, self.strings['downloading'])
            audio_data = io.BytesIO(await reply.download_media(bytes))
            await utils.answer(message, self.strings['searching'])
            return audio_data, reply
        except Exception as e:
            await utils.answer(message, self.strings['error_processing'].format(str(e)))
            return None, None

    def get_streaming_links(self, track_data):
        """Generate formatted streaming links from track data"""
        links = []
        
        # Prepare link data with improved emojis and more services
        link_data = {
            "Spotify": {
                "emoji": "<emoji document_id=5256345140059577605>🟢</emoji>",
                "url": track_data.get("hub", {}).get("providers", []),
                "find": lambda x: x.get("type") == "SPOTIFY"
            },
            "Apple Music": {
                "emoji": "<emoji document_id=5256214589488898012>🍎</emoji>",
                "url": track_data.get("hub", {}).get("options", []),
                "find": lambda x: x.get("provider") == "applemusic"
            },
            "YouTube Music": {
                "emoji": "<emoji document_id=5256155149022744064>🎧</emoji>",
                "url": f"https://music.youtube.com/search?q={requests.utils.quote(track_data.get('subtitle', '') + ' - ' + track_data.get('title', ''))}",
                "direct": True
            },
            "YouTube": {
                "emoji": "<emoji document_id=5436008692022571647>📺</emoji>",
                "url": f"https://www.youtube.com/results?search_query={requests.utils.quote(track_data.get('subtitle', '') + ' - ' + track_data.get('title', ''))}",
                "direct": True
            },
            "SoundCloud": {
                "emoji": "<emoji document_id=5258065195566747816>🔶</emoji>",
                "url": f"https://soundcloud.com/search?q={requests.utils.quote(track_data.get('subtitle', '') + ' - ' + track_data.get('title', ''))}",
                "direct": True
            },
            "Deezer": {
                "emoji": "<emoji document_id=5258754555879023860>🎵</emoji>",
                "url": f"https://www.deezer.com/search/{requests.utils.quote(track_data.get('subtitle', '') + ' ' + track_data.get('title', ''))}",
                "direct": True
            },
            "VK Music": {
                "emoji": "<emoji document_id=5257504728540402357>🎼</emoji>",
                "url": f"https://vk.com/audio?q={requests.utils.quote(track_data.get('subtitle', '') + ' - ' + track_data.get('title', ''))}",
                "direct": True
            }
        }
        
        # Build formatted links with shadows for better visual appearance
        for platform, data in link_data.items():
            if data.get("direct"):
                links.append(f"{data['emoji']} <a href=\"{data['url']}\">{platform}</a>")
            else:
                item = next(filter(data["find"], data["url"]), None)
                if item and "actions" in item:
                    url = next((a.get("uri") for a in item["actions"] if "uri" in a), None)
                    if url:
                        links.append(f"{data['emoji']} <a href=\"{url}\">{platform}</a>")
        
        return "\n".join(links)

    def get_extra_track_info(self, track_data):
        """Extract additional track information for enhanced display"""
        extra_info = {}
        
        # Get release date if available
        sections = track_data.get("sections", [])
        metadata = next((section.get("metadata", []) for section in sections if "metadata" in section), [])
        
        # Find release date
        release_date = next((item.get("text") for item in metadata if item.get("title") == "Released"), None)
        if release_date:
            extra_info["release_date"] = release_date
            
        # Find genre
        genre = next((item.get("text") for item in metadata if item.get("title") == "Genre"), None)
        if genre:
            extra_info["genre"] = genre
            
        # Find lyrics snippet if available
        lyrics_section = next((section for section in sections if section.get("type") == "LYRICS"), None)
        if lyrics_section and "text" in lyrics_section:
            # Get first few lines of lyrics (limit to prevent large messages)
            lyrics_preview = "\n".join(lyrics_section["text"][:5])
            if lyrics_preview:
                extra_info["lyrics_preview"] = lyrics_preview
                
        return extra_info

    @loader.command(ru_doc='<ответ на аудио/видео> - распознать трек')
    async def sh(self, message):
        """<reply to audio/video> - recognize track"""
        import time
        start_time = time.time()
        
        audio_data, reply = await self.fetch_media(message)
        if not audio_data:
            return
            
        try:
            shazam = Shazam(audio_data.read())
            recognition_result = next(shazam.recognizeSong(), (None, None))
            
            if not recognition_result or not recognition_result[1].get("track"):
                await utils.answer(message, self.strings['not_found'])
                return
                
            track = recognition_result[1]["track"]
            
            # Get track info
            title = track.get("title", "Unknown")
            artist = track.get("subtitle", "Unknown Artist")
            album = track.get("sections", [{}])[0].get("metadata", [{}])[0].get("text", "Unknown Album")
            
            # Get extra track info
            extra_info = self.get_extra_track_info(track)
            
            # Get image if available, or use default
            image = None
            if "images" in track and "coverarthq" in track["images"]:
                image = track["images"]["coverarthq"]
            elif "images" in track and "background" in track["images"]:
                image = track["images"]["background"]
                
            # Format links to streaming platforms
            links = self.get_streaming_links(track)
            
            # Calculate processing time
            processing_time = round(time.time() - start_time, 2)
            
            # Format response with track info and links
            caption = self.strings['track_info'].format(
                title=title,
                artist=artist,
                album=album,
                links=links
            )
            
            # Add extra information if available
            if "release_date" in extra_info:
                caption += f"\n\n{self.strings['released'].format(date=extra_info['release_date'])}"
                
            if "genre" in extra_info:
                caption += f"\n{self.strings['genre'].format(genre=extra_info['genre'])}"
                
            # Add processing time
            caption += f"\n\n{self.strings['processing_time'].format(time=processing_time)}"
                
            # Add lyrics preview if available (at the end)
            if "lyrics_preview" in extra_info:
                caption += f"\n\n{self.strings['lyrics_preview'].format(lyrics=extra_info['lyrics_preview'])}"
            
            # Send result
            if image:
                try:
                    image_data = requests.get(image).content
                    await self.client.send_file(
                        message.peer_id,
                        file=image_data,
                        caption=caption,
                        reply_to=reply.id,
                        parse_mode="HTML"
                    )
                    await message.delete()
                except Exception:
                    await utils.answer(message, caption, parse_mode="HTML")
            else:
                await utils.answer(message, caption, parse_mode="HTML")
                
        except Exception as e:
            await utils.answer(message, self.strings['not_found'])
