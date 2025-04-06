# meta developer: @sunshinelzt

import os
import asyncio
import contextlib
from typing import Union, List, Dict, Optional, Tuple
from langdetect import detect
import edge_tts
from .. import loader, utils


@loader.tds
class TextToSpeechMod(loader.Module):
    """Модуль преобразования текста в голосовое сообщение"""
    strings = {
        "name": "TextToSpeech",
        "processing": "<emoji document_id=5386367538735104399>⌛</emoji> Обработка...",
        "error_processing": "<emoji document_id=5210952531676504517>❌</emoji> Ошибка при обработке текста",
        "voice_changed": "<emoji document_id=5427009714745517609>✅</emoji> Голос изменен на {}",
        "speed_changed": "<emoji document_id=5427009714745517609>✅</emoji> Скорость речи изменена на {}",
        "pitch_changed": "<emoji document_id=5427009714745517609>✅</emoji> Высота голоса изменена на {}",
        "volume_changed": "<emoji document_id=5427009714745517609>✅</emoji> Громкость изменена на {}"
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            "voice_type", "male", "Тип голоса (male/female)",
            "speech_rate", "+0%", "Скорость речи (например, '+10%', '-5%')",
            "speech_pitch", "+0Hz", "Высота голоса (например, '+10Hz', '-5Hz')",
            "speech_volume", "+0%", "Громкость голоса (например, '+10%', '-5%')",
            "delete_original", True, "Удаление исходного сообщения после обработки",
            "show_processing", True, "Показывать сообщение о процессе обработки"
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
                "ar": "ar-SA-HamedNeural",
                "bg": "bg-BG-BorislavNeural",
                "ca": "ca-ES-EnricNeural",
                "cs": "cs-CZ-AntoninNeural",
                "da": "da-DK-JeppeNeural",
                "el": "el-GR-NestorasNeural",
                "fi": "fi-FI-HarriNeural",
                "he": "he-IL-AvriNeural",
                "hi": "hi-IN-MadhurNeural",
                "hr": "hr-HR-SreckoNeural",
                "hu": "hu-HU-TamasNeural",
                "id": "id-ID-ArdiNeural",
                "ko": "ko-KR-InJoonNeural",
                "ms": "ms-MY-OsmanNeural",
                "nl": "nl-NL-MaartenNeural",
                "no": "nb-NO-FinnNeural",
                "pl": "pl-PL-MarekNeural",
                "pt": "pt-PT-DuarteNeural",
                "ro": "ro-RO-EmilNeural",
                "sk": "sk-SK-LukasNeural",
                "sl": "sl-SI-RokNeural",
                "sv": "sv-SE-MattiasNeural",
                "th": "th-TH-PremwadeeNeural",
                "tr": "tr-TR-AhmetNeural",
                "vi": "vi-VN-NamMinhNeural",
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
                "ar": "ar-SA-ZariyahNeural",
                "bg": "bg-BG-KalinaNeural",
                "ca": "ca-ES-JoanaNeural",
                "cs": "cs-CZ-VlastaNeural",
                "da": "da-DK-ChristelNeural",
                "el": "el-GR-AthinaNeural",
                "fi": "fi-FI-NooraNeural",
                "he": "he-IL-HilaNeural",
                "hi": "hi-IN-SwaraNeural",
                "hr": "hr-HR-GabrijelaNeural",
                "hu": "hu-HU-NoemiNeural",
                "id": "id-ID-GadisNeural",
                "ko": "ko-KR-SoonBokNeural",
                "ms": "ms-MY-YasminNeural",
                "nl": "nl-NL-ColetteNeural",
                "no": "nb-NO-IselinNeural",
                "pl": "pl-PL-ZofiaNeural",
                "pt": "pt-PT-RaquelNeural",
                "ro": "ro-RO-AlinaNeural",
                "sk": "sk-SK-ViktoriaNeural",
                "sl": "sl-SI-PetraNeural",
                "sv": "sv-SE-SofieNeural",
                "th": "th-TH-AcharaNeural",
                "tr": "tr-TR-EmelNeural",
                "vi": "vi-VN-HoaiMyNeural",
                "default": "ru-RU-SvetlanaNeural"
            }
        }
        self._temp_file = "tts_output.mp3"
        self._processing = False
        self._language_mapping = {
            "zh-cn": "zh", "zh-tw": "zh", "en-us": "en", "en-gb": "en",
            "pt-br": "pt", "pt-pt": "pt", "es-es": "es", "es-mx": "es"
        }

    def _get_voice(self, text: str) -> str:
        """Определение подходящего голоса на основе языка текста"""
        try:
            detected_lang = detect(text.lower())
            if detected_lang in self._language_mapping:
                lang_code = self._language_mapping[detected_lang]
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

    async def _process_tts(self, text: str, voice: str) -> Tuple[bool, str]:
        """Обработка текста в голос с расширенными параметрами"""
        try:
            communicate = edge_tts.Communicate(
                text, 
                voice=voice,
                rate=self.config["speech_rate"],
                volume=self.config["speech_volume"],
                pitch=self.config["speech_pitch"]
            )
            
            await communicate.save(self._temp_file)
            return True, ""
        except Exception as e:
            return False, str(e)

    async def _get_available_voices(self) -> List[Dict]:
        """Получение списка всех доступных голосов"""
        try:
            voices = await edge_tts.list_voices()
            return voices
        except Exception:
            return []

    @loader.owner
    async def speakcmd(self, message):
        """Преобразование текста в речь. Использование: .speak <текст>"""
        if self._processing:
            await message.edit("<emoji document_id=5447644880824181073>⚠️</emoji> Уже обрабатывается другой запрос")
            return

        processing_msg = None
        if self.config["show_processing"] and not self.config["delete_original"]:
            processing_msg = await message.edit(self.strings["processing"])
        elif self.config["show_processing"]:
            processing_msg = await message.client.send_message(
                message.chat_id, 
                self.strings["processing"]
            )

        if self.config["delete_original"]:
            await message.delete()
            
        self._processing = True
        
        try:
            if len(message.text.split(" ", maxsplit=1)) > 1:
                text = message.text.split(" ", maxsplit=1)[1]
            else:
                self._processing = False
                if processing_msg:
                    await processing_msg.delete()
                return
            
            reply = await message.get_reply_message()
            reply_to_id = reply.id if reply else None
            
            voice = self._get_voice(text)
            success, error = await self._process_tts(text, voice)
            
            if success and os.path.exists(self._temp_file):
                await message.client.send_file(
                    message.chat_id,
                    self._temp_file,
                    voice_note=True,
                    reply_to=reply_to_id,
                    #caption=f"🗣 Голос: {voice}"
                )
            else:
                if not self.config["delete_original"]:
                    await message.edit(f"{self.strings['error_processing']}: {error}")
                else:
                    await message.client.send_message(
                        message.chat_id,
                        f"{self.strings['error_processing']}: {error}"
                    )
                
        except Exception as e:
            if not self.config["delete_original"]:
                await message.edit(f"{self.strings['error_processing']}: {str(e)}")
            else:
                await message.client.send_message(
                    message.chat_id,
                    f"{self.strings['error_processing']}: {str(e)}"
                )
        finally:
            with contextlib.suppress(Exception):
                if os.path.exists(self._temp_file):
                    os.remove(self._temp_file)
            if processing_msg:
                with contextlib.suppress(Exception):
                    await processing_msg.delete()
            self._processing = False

    @loader.owner
    async def speakvcmd(self, message):
        """Выбор типа голоса. Использование: .speakv <мужской/женский>"""
        args = utils.get_args_raw(message).lower()
        
        if args in ["мужской", "male", "м", "m"]:
            self.config["voice_type"] = "male"
            await utils.answer(message, self.strings["voice_changed"].format("мужской"))
        elif args in ["женский", "female", "ж", "f"]:
            self.config["voice_type"] = "female"
            await utils.answer(message, self.strings["voice_changed"].format("женский"))
        else:
            await utils.answer(message, "Укажите тип голоса: мужской/женский")
            await asyncio.sleep(3)
            
        await message.delete()

    @loader.owner
    async def speakscmd(self, message):
        """Установка скорости речи. Использование: .speaks <+10%/-5%/0%>"""
        args = utils.get_args_raw(message).lower()
        
        if args and (args.endswith("%") and (args.startswith("+") or args.startswith("-") or args == "0%")):
            self.config["speech_rate"] = args
            await utils.answer(message, self.strings["speed_changed"].format(args))
            await asyncio.sleep(3)
        else:
            await utils.answer(message, "Укажите скорость в формате: +10%, -5%, 0%")
            await asyncio.sleep(3)
            
        await message.delete()

    @loader.owner
    async def speakpcmd(self, message):
        """Установка высоты голоса. Использование: .speakp <+10Hz/-5Hz/0Hz>"""
        args = utils.get_args_raw(message).lower()
        
        if args and (args.endswith("hz") and (args.startswith("+") or args.startswith("-") or args == "0hz")):
            self.config["speech_pitch"] = args
            await utils.answer(message, self.strings["pitch_changed"].format(args))
            await asyncio.sleep(3)
        else:
            await utils.answer(message, "Укажите высоту в формате: +10Hz, -5Hz, 0Hz")
            await asyncio.sleep(3)
            
        await message.delete()
        
    @loader.owner
    async def speaklcmd(self, message):
        """Показать список доступных языков"""
        voice_type = self.config["voice_type"].lower()
        if voice_type not in ["male", "female"]:
            voice_type = "male"
            
        languages = sorted(list(self._voices[voice_type].keys()))
        languages.remove("default")
        
        langs_text = "<emoji document_id=5399898266265475100>🌍</emoji> Доступные языки:\n\n" + ", ".join(languages)
        
        await utils.answer(message, langs_text)
        
    @loader.owner
    async def speakvlcmd(self, message):
        """Показать все доступные голоса с API Edge TTS"""
        reply = await message.edit("<emoji document_id=5386367538735104399>⌛</emoji> Загрузка списка голосов...")
        
        try:
            voices = await self._get_available_voices()
            if not voices:
                await utils.answer(message, "<emoji document_id=5210952531676504517>❌</emoji> Не удалось получить список голосов")
                return
                
            total = len(voices)
            voices_by_lang = {}
            
            for voice in voices:
                lang = voice.get("Locale", "unknown")
                name = voice.get("ShortName", "unknown")
                gender = "👨" if "Male" in voice.get("Gender", "") else "👩"
                
                if lang not in voices_by_lang:
                    voices_by_lang[lang] = []
                    
                voices_by_lang[lang].append(f"{gender} {name}")
            
            result = f"<emoji document_id=5382013970905309819>🎙</emoji> Всего доступно голосов: {total}\n\n"
            
            for lang, voice_list in sorted(voices_by_lang.items()):
                result += f"<emoji document_id=5447410659077661506>🌐</emoji> {lang}:\n"
                result += "  " + "\n  ".join(voice_list) + "\n\n"
                
            if len(result) > 4096:
                parts = [result[i:i+4096] for i in range(0, len(result), 4096)]
                for i, part in enumerate(parts):
                    if i == 0:
                        await utils.answer(message, part)
                    else:
                        await message.client.send_message(message.chat_id, part)
            else:
                await utils.answer(message, result)
                
        except Exception as e:
            await utils.answer(message, f"<emoji document_id=5210952531676504517>❌</emoji> Ошибка: {str(e)}")
            
    @loader.owner
    async def speakvmcmd(self, message):
        """Установка индивидуального голоса вручную. Использование: .speakvm <ShortName>"""
        args = utils.get_args_raw(message)
        
        if not args:
            await utils.answer(message, "<emoji document_id=5210952531676504517>❌</emoji> Укажите короткое имя голоса (используйте .speakvl для просмотра)")
            await asyncio.sleep(3)
            await message.delete()
            return
            
        try:
            voices = await self._get_available_voices()
            voice_exists = False
            
            for voice in voices:
                if voice.get("ShortName") == args:
                    voice_exists = True
                    break
                    
            if voice_exists:
                for voice in voices:
                    if voice.get("ShortName") == args:
                        gender = "male" if "Male" in voice.get("Gender", "") else "female"
                        locale = voice.get("Locale", "").lower().split("-")[0]
                        
                        self._voices[gender][locale] = args
                        
                        await utils.answer(message, f"<emoji document_id=5427009714745517609>✅</emoji> Голос {args} установлен как основной для языка {locale}")
                        await asyncio.sleep(3)
            else:
                await utils.answer(message, f"<emoji document_id=5210952531676504517>❌</emoji> Голос {args} не найден")
                await asyncio.sleep(3)
                
        except Exception as e:
            await utils.answer(message, f"<emoji document_id=5210952531676504517>❌</emoji> Ошибка: {str(e)}")
            await asyncio.sleep(3)
            
        await message.delete()
        
    @loader.owner
    async def speakvocmd(self, message):
        """Установка громкости голоса. Использование: .speakvo <+10%/-5%/0%>"""
        args = utils.get_args_raw(message).lower()
        
        if args and (args.endswith("%") and (args.startswith("+") or args.startswith("-") or args == "0%")):
            self.config["speech_volume"] = args
            await utils.answer(message, self.strings["volume_changed"].format(args))
            await asyncio.sleep(3)
        else:
            await utils.answer(message, "Укажите громкость в формате: +10%, -5%, 0%")
            await asyncio.sleep(3)
            
        await message.delete()
        
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
