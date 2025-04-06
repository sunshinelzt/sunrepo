# meta developer: @sunshinelzt

import os
import asyncio
import contextlib
from typing import Union, List, Dict, Optional
from langdetect import detect
import edge_tts
from .. import loader, utils


@loader.tds
class TextToSpeechMod(loader.Module):
    """Модуль преобразования текста в голосовое сообщение"""
    strings = {
        "name": "TextToSpeech",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            "voice_type", "male", "Тип голоса (male/female)",
            "speech_rate", "+0%", "Скорость речи (например, '+10%', '-5%')",
            "delete_original", True, "Удаление исходного сообщения после обработки"
        )
        self._voices = {
            "male": {
                "ru": "ru-RU-DmitryNeural",
                "en": "en-US-GuyNeural",
                "uk": "uk-UA-OstapNeural",
                "de": "de-DE-ConradNeural",
                "fr": "fr-FR-HenriNeural",
                "es": "es-ES-AlvaroNeural",
                "it": "it-IT-DiegoNeural",
                "zh": "zh-CN-YunxiNeural",
                "ja": "ja-JP-KeitaNeural",
                "default": "ru-RU-DmitryNeural"
            },
            "female": {
                "ru": "ru-RU-SvetlanaNeural",
                "en": "en-US-JennyNeural",
                "uk": "uk-UA-PolinaNeural",
                "de": "de-DE-KatjaNeural",
                "fr": "fr-FR-DeniseNeural",
                "es": "es-ES-ElviraNeural",
                "it": "it-IT-ElsaNeural",
                "zh": "zh-CN-XiaoxiaoNeural",
                "ja": "ja-JP-NanamiNeural",
                "default": "ru-RU-SvetlanaNeural"
            }
        }
        self._temp_file = "tts_output.mp3"
        self._processing = False

    def _get_voice(self, text: str) -> str:
        try:
            detected_lang = detect(text)
            if detected_lang == 'uk':
                lang_code = 'uk'
            else:
                lang_code = detected_lang.split('-')[0]
            
            voice_type = self.config["voice_type"].lower()
            if voice_type not in ["male", "female"]:
                voice_type = "male"
                
            return self._voices[voice_type].get(lang_code, self._voices[voice_type]["default"])
        except Exception:
            voice_type = self.config["voice_type"].lower()
            if voice_type not in ["male", "female"]:
                voice_type = "male"
            return self._voices[voice_type]["default"]

    async def _process_tts(self, text: str, voice: str) -> bool:
        """Обработка текста в голос с оптимизированной логикой"""
        try:
            communicate = edge_tts.Communicate(
                text, 
                voice=voice,
                rate=self.config["speech_rate"],
                volume="+0%",
                pitch="+0Hz"
            )
            
            await communicate.save(self._temp_file)
            return True
        except Exception:
            return False

    @loader.owner
    async def speakcmd(self, message):
        """Преобразование текста в речь. Использование: .speak <текст>"""
        if self._processing:
            return
            
        self._processing = True
        
        try:
            if len(message.text.split(" ", maxsplit=1)) > 1:
                text = message.text.split(" ", maxsplit=1)[1]
            else:
                self._processing = False
                return
            
            reply = await message.get_reply_message()
            reply_to_id = reply.id if reply else None
            
            voice = self._get_voice(text)
            success = await self._process_tts(text, voice)
            
            if success and os.path.exists(self._temp_file):
                await message.client.send_file(
                    message.chat_id,
                    self._temp_file,
                    voice_note=True,
                    reply_to=reply_to_id
                )
            
            if self.config["delete_original"]:
                await message.delete()
                
        except Exception:
            pass
        finally:
            with contextlib.suppress(Exception):
                if os.path.exists(self._temp_file):
                    os.remove(self._temp_file)
            self._processing = False

    @loader.owner
    async def speakvcmd(self, message):
        """Выбор типа голоса. Использование: .speakv <мужской/женский>"""
        args = utils.get_args_raw(message).lower()
        
        if args in ["мужской", "male", "м", "m"]:
            self.config["voice_type"] = "male"
        elif args in ["женский", "female", "ж", "f"]:
            self.config["voice_type"] = "female"
            
        await message.delete()

    @loader.owner
    async def speakscmd(self, message):
        """Установка скорости речи. Использование: .speaks <+10%/-5%/0%>"""
        args = utils.get_args_raw(message).lower()
        
        if args and (args.endswith("%") and (args.startswith("+") or args.startswith("-") or args == "0%")):
            self.config["speech_rate"] = args
            
        await message.delete()
