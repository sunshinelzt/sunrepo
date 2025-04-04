# requires: ShazamAPI
import io
from ShazamAPI import Shazam
from .. import loader, utils

@loader.tds
class ShazamMod(loader.Module):
    """Use <reply to voice> to search for a song using audio."""
    strings = {
        "name": 'Shazam',
        "Downloading": "<emoji document_id=5443127283898405358>🔥</emoji> <b>Downloading...</b>",
        "Searching": "<emoji document_id=5447410659077661506>🔍</emoji> <b>Searching...</b>",
        "no_reply": "<emoji document_id=5294339927318739359>🚫</emoji> <b>Please reply to an audio message.</b>",
        "not_found": "<emoji document_id=5210952531676504517>🚫</emoji> <b>Song not found.</b>",
        "track_info": (
            "<emoji document_id=5325547803936572038>✨</emoji> <b>Song found</b>\n"
            '<emoji document_id=5460795800101594035>🎵</emoji> <b>Name:</b> "<code>{}</code>"\n'
            '<emoji document_id=5409770415070494968>👤</emoji> <b>Artist:</b> {}\n'
            '<emoji document_id=5373001317042101943>💿</emoji> <b>Album:</b> {}'
        ),
        "music_links": (
            "\n<b>Music Links:</b>\n{}"
        ),
        "youtube_link": '<emoji document_id=5210424995744481361>▶️</emoji> <a href="{}">YouTube</a>',
        "spotify_link": '<emoji document_id=5254973045619626382>🎧</emoji> <a href="{}">Spotify</a>',
        "soundcloud_link": '<emoji document_id=5214163411336709153>☁️</emoji> <a href="{}">SoundCloud</a>',
        "no_youtube": '<emoji document_id=5210424995744481361>▶️</emoji> YouTube: Not found',
        "no_spotify": '<emoji document_id=5254973045619626382>🎧</emoji> Spotify: Not found',
        "no_soundcloud": '<emoji document_id=5214163411336709153>☁️</emoji> SoundCloud: Not found'
    }
    
    strings_ru = {
        "Downloading": "<emoji document_id=5443127283898405358>🔥</emoji> <b>Загрузка..</b>",
        "Searching": "<emoji document_id=5447410659077661506>🔍</emoji> <b>Поиск..</b>",
        "no_reply": "<emoji document_id=5294339927318739359>🚫</emoji> <b>Oтветьте на аудио сообщение</b>",
        "not_found": "<emoji document_id=5210952531676504517>🚫</emoji> <b>Не удалось найти песню</b>",
        "track_info": (
            "<emoji document_id=5325547803936572038>✨</emoji> <b>Песня найдена</b>\n"
            '<emoji document_id=5460795800101594035>🎵</emoji> <b>Название:</b> "<code>{}</code>"\n'
            '<emoji document_id=5409770415070494968>👤</emoji> <b>Исполнитель:</b> {}\n'
            '<emoji document_id=5373001317042101943>💿</emoji> <b>Альбом:</b> {}'
        ),
        "music_links": (
            "\n<b>Ссылки на сервисы:</b>\n{}"
        ),
        "youtube_link": '<emoji document_id=5210424995744481361>▶️</emoji> <a href="{}">YouTube</a>',
        "spotify_link": '<emoji document_id=5254973045619626382>🎧</emoji> <a href="{}">Spotify</a>',
        "soundcloud_link": '<emoji document_id=5214163411336709153>☁️</emoji> <a href="{}">SoundCloud</a>',
        "no_youtube": '<emoji document_id=5210424995744481361>▶️</emoji> YouTube: Не найдено',
        "no_spotify": '<emoji document_id=5254973045619626382>🎧</emoji> Spotify: Не найдено',
        "no_soundcloud": '<emoji document_id=5214163411336709153>☁️</emoji> SoundCloud: Не найдено'
    }
    
    async def fetch_audio(self, message):
        reply = await message.get_reply_message()
        if reply and reply.file and reply.file.mime_type.startswith("audio"):
            await utils.answer(message, self.strings['Downloading'])
            audio_data = io.BytesIO(await reply.download_media(bytes))
            await utils.answer(message, self.strings['Searching'])
            return audio_data, reply
        await utils.answer(message, self.strings['no_reply'])
        return None, None
    
    def get_music_links(self, track_data):
        links = []
        
        # YouTube Link
        try:
            if "youtube" in track_data["hub"]["providers"][0]["actions"]:
                youtube_url = track_data["hub"]["providers"][0]["actions"][1]["uri"]
                links.append(self.strings["youtube_link"].format(youtube_url))
            else:
                links.append(self.strings["no_youtube"])
        except (KeyError, IndexError):
            links.append(self.strings["no_youtube"])
        
        # Spotify Link
        try:
            spotify_url = None
            for provider in track_data["hub"]["providers"]:
                if provider["type"] == "SPOTIFY":
                    spotify_url = provider["actions"][0]["uri"]
                    break
            
            if spotify_url:
                links.append(self.strings["spotify_link"].format(spotify_url))
            else:
                links.append(self.strings["no_spotify"])
        except (KeyError, IndexError):
            links.append(self.strings["no_spotify"])
        
        # SoundCloud Link
        try:
            soundcloud_url = None
            for option in track_data["hub"]["options"]:
                if "soundcloud" in option["caption"].lower():
                    soundcloud_url = option["actions"][0]["uri"]
                    break
            
            if soundcloud_url:
                links.append(self.strings["soundcloud_link"].format(soundcloud_url))
            else:
                links.append(self.strings["no_soundcloud"])
        except (KeyError, IndexError):
            links.append(self.strings["no_soundcloud"])
        
        return "\n".join(links)
    
    @loader.command(ru_doc='<reply to audio> - распознать трек')
    async def sh(self, message):
        """<reply to audio> - recognize track"""
        audio_data, reply = await self.fetch_audio(message)
        if not audio_data:
            return
        
        try:
            shazam = Shazam(audio_data.read())
            recognition_result = next(shazam.recognizeSong())
            track_data = recognition_result[1]["track"]
            
            # Extract artist name
            artist_name = track_data.get("subtitle", "Unknown Artist")
            
            # Extract album name
            album_name = track_data.get("sections", [{}])[0].get("metadata", [{}])[0].get("text", "Unknown Album")
            
            # Format music links
            music_links = self.get_music_links(track_data)
            
            # Build caption
            caption = self.strings['track_info'].format(
                track_data["share"]["subject"],
                artist_name,
                album_name
            )
            caption += self.strings['music_links'].format(music_links)
            
            # Send response with background image
            await self.client.send_file(
                message.peer_id,
                file=track_data["images"]["background"],
                caption=caption,
                reply_to=reply.id,
                parse_mode='HTML'
            )
            await message.delete()
        except StopIteration:
            await utils.answer(message, self.strings['not_found'])
        except Exception as e:
            self.logger.error(f"Error in Shazam module: {e}")
            await utils.answer(message, self.strings['not_found'])
