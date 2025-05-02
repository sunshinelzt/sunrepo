# meta developer: @sunshinelzt
# охуенно улучшено: 2025-05-03
# переписано нахуй так, чтобы работало как должно

import os
import asyncio
import contextlib
import logging
import json
import time
import random
from typing import Union, List, Dict, Optional, Tuple, Any
import re
from langdetect import detect

import aiohttp
from pydub import AudioSegment
from .. import loader, utils


logger = logging.getLogger(__name__)


@loader.tds
class TTSMod(loader.Module):
    """Ахуенный модуль для превращения текста в голосовое сообщение с ебейшей кастомизацией"""
    
    strings = {
        "name": "TTS",
        "error_processing": "Хуйня какая-то при обработке текста",
        "no_text": "Бля, текст введи для озвучки",
        "busy": "Погодь, я ещё прошлый запрос обрабатываю",
        "api_error": "API наебнулся: {}",
        "connection_error": "Соединение накрылось пиздой: {}",
        "unknown_error": "Хз что за хуйня: {}"
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            # Основные настройки
            "api_key", "", "API ключ от ElevenLabs (получи на elevenlabs.io)",
            "model_id", "eleven_multilingual_v2", "ID модели (eleven_multilingual_v2, eleven_monolingual_v1, eleven_turbo_v2)",
            
            # Настройки голоса
            "voice_type", "male", "Тип голоса по умолчанию (male/female)",
            "stability", 0.5, "Стабильность голоса (0.0-1.0, где 0.0 - хаотичный пиздец, 1.0 - ровно как робот)",
            "similarity_boost", 0.75, "Схожесть голоса с оригиналом (0.0-1.0, где 0.0 - пьяный в хлам, 1.0 - будто клон)",
            
            # Настройки стиля речи
            "style", 0.7, "Степень экспрессии (0.0-1.0, где 0.0 - уныло, 1.0 - пиздец эмоционально)",
            "use_speaker_boost", True, "Улучшение чёткости голоса (True/False)",
            
            # Настройки звука
            "volume_adjustment_db", 0, "Корректировка громкости (+/- дБ)",
            
            # Кастомные голоса для языков (мужские)
            "male_voices", {
                "ru": "jsCqWAovK2LkecY7zXl4", # Баста (русский)
                "en": "pNInz6obpgDQGcFmaJgB", # Adam (английский)
                "uk": "mTSvIrm2hmcxR9Mew3mV", # Олег (украинский)
                "de": "IKne3meq5aSn9XLyUdCD", # Hans (немецкий)
                "fr": "ODnIvQq3BiMoMQCE5PUa", # Pierre (французский)
                "es": "ErXwobaYiN019PkySvjV", # Antoni (испанский)
                "it": "Yko7PKHZNXotIFUBG7I9", # Lorenzo (итальянский)
                "ja": "zbkzjolmHyMVm0yBNMDt", # Hiroshi (японский)
                "zh": "TxGEqnHWrfWFTfGW9XjX", # Lee (китайский)
                "ar": "t0jbNlBVZ17f02VDIeMI", # Ahmed (арабский)
                "hi": "XB0fDUnXU5powFXDhCwa", # Ajay (хинди)
                "ko": "ZCYOGA6EZ7RMuiMwDQ3d", # Jin (корейский)
                "pt": "FLvDGyVHxPJXnWmYSV98", # Mateus (португальский)
                "default": "pNInz6obpgDQGcFmaJgB", # Adam (если не нашлось подходящего языка)
            },
            
            # Кастомные голоса для языков (женские)
            "female_voices", {
                "ru": "0G2aDhfNxRTGnEUYb3xd", # Ксения (русский)
                "en": "EXAVITQu4vr4xnSDxMaL", # Rachel (английский)
                "uk": "mVEDpXKqJZ4Q9YN36YDw", # Оксана (украинский)
                "de": "JBFqnCBsd6RMkjVDRZzb", # Anna (немецкий)
                "fr": "MF3mGyEYCl7XYWbV9V6O", # Nicole (французский)
                "es": "H8ZpFUgUHLRQzw1pX2WT", # Sofia (испанский)
                "it": "piTKgcLEGmPE4e6mEKli", # Valentina (итальянский)
                "ja": "zcAOhNBS3c14rBihAFp1", # Yuki (японский)
                "zh": "zhTTFinSZ1tgH9SZyuD4", # Lin (китайский)
                "ar": "iP95p4xoKVk53GoZ742B", # Leila (арабский)
                "hi": "pMsXgVXv3BLzUgSXRplE", # Priya (хинди)
                "ko": "DGBnDqJNcGn0InVTbnKN", # Ji-Min (корейский)
                "pt": "CYw3kZ02Hs0563khs1Fj", # Isabella (португальский)
                "default": "EXAVITQu4vr4xnSDxMaL", # Rachel (если не нашлось подходящего языка)
            },
            
            # Настройки функционала
            "delete_original", True, "Удалять ли исходное сообщение после отправки голосового",
            "max_length", 500, "Максимальная длина текста (ограничение API, не больше 2000)",
            "response_timeout", 30, "Таймаут ожидания ответа от API (в секундах)",
            "chunk_size", 1024, "Размер чанка при скачивании (не трогай, если не шаришь)",
            "use_proxy", False, "Использовать прокси для запросов к API",
            "proxy_url", "", "URL прокси в формате http://user:pass@host:port"
        )
        
        # Инициализация базовых переменных
        self._temp_file = os.path.join("/tmp", f"tts_output_{random.randint(1000, 9999)}.mp3")
        self._processing = False
        self._language_mapping = {
            "zh-cn": "zh", "zh-tw": "zh", "en-us": "en", "en-gb": "en",
            "pt-br": "pt", "pt-pt": "pt", "es-es": "es", "es-mx": "es",
            "fr-fr": "fr", "fr-ca": "fr", "de-de": "de", "de-at": "de",
            "it-it": "it", "ja-jp": "ja", "ko-kr": "ko", "ru-ru": "ru",
            "ar-sa": "ar", "hi-in": "hi"
        }
        
    async def _get_voice_id(self, text: str) -> str:
        """Умная определялка какой нахуй голос подойдёт для текста"""
        try:
            # Сначала определяем язык текста
            detected_lang = detect(text.lower())
            
            # Берем только основной код языка
            if "-" in detected_lang:
                detected_lang = detected_lang.split("-")[0]
                
            # Если язык есть в маппинге, используем его
            if detected_lang in self._language_mapping:
                lang_code = self._language_mapping[detected_lang]
            else:
                lang_code = detected_lang
                
            # Выбираем мужской или женский голос в зависимости от конфига
            voice_type = self.config["voice_type"].lower()
            if voice_type == "male":
                voices_dict = self.config["male_voices"]
            else: # female по умолчанию, если что-то не так
                voices_dict = self.config["female_voices"]
                
            # Возвращаем ID голоса для определённого языка, 
            # а если такого нет - берём дефолтный
            return voices_dict.get(lang_code, voices_dict["default"])
            
        except Exception as e:
            logger.error(f"Пиздец при определении голоса: {e}")
            # Если всё пошло по пизде, возвращаем дефолтный голос
            voice_type = self.config["voice_type"].lower()
            if voice_type == "male":
                return self.config["male_voices"]["default"]
            else:
                return self.config["female_voices"]["default"]
                
    async def _process_tts(self, text: str, voice_id: str) -> Tuple[bool, str]:
        """Основная логика превращения текста в охуенное голосовое"""
        try:
            # Проверяем если текст пустой
            text = text.strip()
            if not text:
                return False, "Текст пустой, хули озвучивать?"
                
            # Если текст слишком длинный - обрезаем его
            if len(text) > self.config["max_length"]:
                text = text[:self.config["max_length"]] + "..."
                
            # Готовим JSON для запроса
            payload = {
                "text": text,
                "model_id": self.config["model_id"],
                "voice_settings": {
                    "stability": self.config["stability"],
                    "similarity_boost": self.config["similarity_boost"],
                    "style": self.config["style"],
                    "use_speaker_boost": self.config["use_speaker_boost"]
                }
            }
            
            # Формируем заголовки запроса
            headers = {
                "xi-api-key": self.config["api_key"],
                "Content-Type": "application/json",
                "Accept": "audio/mpeg"
            }
            
            # Подготавливаем сессию
            session_kwargs = {}
            if self.config["use_proxy"] and self.config["proxy_url"]:
                session_kwargs["proxy"] = self.config["proxy_url"]
                
            # Делаем запрос к API
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
            
            async with aiohttp.ClientSession(**session_kwargs) as session:
                try:
                    async with session.post(
                        url, 
                        json=payload, 
                        headers=headers,
                        timeout=self.config["response_timeout"]
                    ) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            return False, f"Ошибка API: {response.status} - {error_text}"
                            
                        # Сохраняем аудио в файл
                        with open(self._temp_file, "wb") as f:
                            async for chunk in response.content.iter_chunked(self.config["chunk_size"]):
                                f.write(chunk)
                                
                        # Если нужно поменять громкость
                        if self.config["volume_adjustment_db"] != 0:
                            audio = AudioSegment.from_file(self._temp_file, format="mp3")
                            audio = audio.apply_gain(self.config["volume_adjustment_db"])
                            audio.export(self._temp_file, format="mp3")
                            
                        return True, ""
                        
                except asyncio.TimeoutError:
                    return False, "API долго думает, таймаут нахуй"
                except aiohttp.ClientError as e:
                    return False, f"Ошибка соединения: {str(e)}"
                    
        except Exception as e:
            logger.exception(f"Пиздец в процессе TTS: {e}")
            return False, str(e)
            
    async def _cleanup(self) -> None:
        """Убираем за собой говно"""
        with contextlib.suppress(Exception):
            if os.path.exists(self._temp_file):
                os.remove(self._temp_file)
                
    @loader.owner
    async def speakcmd(self, message):
        """Превращает текст в голосовое сообщение. Использование: .speak <текст> или ответ на сообщение"""
        if self._processing:
            await utils.answer(message, self.strings["busy"])
            return
            
        # Ставим флаг что уже обрабатываем
        self._processing = True
        
        try:
            # Удаляем сообщение сразу
            if self.config["delete_original"]:
                await message.delete()
                
            # Получаем текст для озвучки
            args = utils.get_args_raw(message)
            if not args:
                reply = await message.get_reply_message()
                if reply and reply.text:
                    text = reply.text
                else:
                    if not self.config["delete_original"]:
                        await utils.answer(message, self.strings["no_text"])
                    self._processing = False
                    return
            else:
                text = args
                
            # Определяем ID голоса на основе текста
            voice_id = await self._get_voice_id(text)
            
            # Превращаем текст в голосовое
            success, error = await self._process_tts(text, voice_id)
            
            # Отправляем результат
            if success and os.path.exists(self._temp_file):
                await message.client.send_file(
                    message.chat_id,
                    self._temp_file,
                    voice_note=True,
                    reply_to=message.reply_to_msg_id if message.reply_to_msg_id else None
                )
            else:
                if not self.config["delete_original"]:
                    await utils.answer(message, f"{self.strings['error_processing']}: {error}")
                else:
                    # Отправляем ошибку в личку себе
                    me = await message.client.get_me()
                    await message.client.send_message(
                        me.id, 
                        f"<b>Ошибка в TTS:</b>\n{error}"
                    )
                    
        except Exception as e:
            logger.exception(f"Ошибка в команде speak: {e}")
            if not self.config["delete_original"]:
                await utils.answer(message, f"{self.strings['unknown_error']}: {str(e)}")
            
        finally:
            # Удаляем файл и снимаем флаг обработки
            await self._cleanup()
            self._processing = False
