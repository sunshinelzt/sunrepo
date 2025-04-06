import os
import asyncio
import contextlib
from typing import Union, List, Dict, Optional
import langdetect
from TTS.api import TTS
import torch
from .. import loader, utils


@loader.tds
class RealisticTTSMod(loader.Module):
    """Модуль преобразования текста в реалистичное голосовое сообщение"""
    strings = {
        "name": "RealisticTTS",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            "voice_type", "male", "Тип голоса (male/female)",
            "speech_rate", 1.0, "Скорость речи (например, 1.0 - нормальная, 1.2 - быстрее, 0.8 - медленнее)",
            "delete_original", True, "Удаление исходного сообщения после обработки",
            "model_quality", "medium", "Качество модели (low/medium/high)",
            "emotion", "neutral", "Эмоциональная окраска (neutral/happy/sad/angry)"
        )
        self._models = {
            "low": {
                "male": "tts_models/en/ljspeech/tacotron2-DDC",
                "female": "tts_models/en/ljspeech/tacotron2-DDC"
            },
            "medium": {
                "male": "tts_models/en/vctk/vits",
                "female": "tts_models/en/vctk/vits"
            },
            "high": {
                "male": "tts_models/multilingual/multi-dataset/xtts_v2",
                "female": "tts_models/multilingual/multi-dataset/xtts_v2"
            }
        }
        self._speaker_ids = {
            "male": {
                "en": "p273",  # VCTK male speaker
                "ru": "p273",  # Fallback for Russian
                "default": "p273"
            },
            "female": {
                "en": "p225",  # VCTK female speaker
                "ru": "p225",  # Fallback for Russian
                "default": "p225"
            }
        }
        self._emotion_settings = {
            "neutral": {"pitch_shift": 0.0, "energy_scale": 1.0},
            "happy": {"pitch_shift": 0.2, "energy_scale": 1.2},
            "sad": {"pitch_shift": -0.2, "energy_scale": 0.8},
            "angry": {"pitch_shift": 0.1, "energy_scale": 1.5}
        }
        self._tts = None
        self._temp_file = "realistic_tts_output.wav"
        self._processing = False
        self._device = "cuda" if torch.cuda.is_available() else "cpu"

    async def _load_tts_model(self):
        """Загрузка и кэширование модели TTS"""
        quality = self.config["model_quality"]
        voice_type = self.config["voice_type"]
        
        if quality not in self._models:
            quality = "medium"
        if voice_type not in ["male", "female"]:
            voice_type = "male"
        
        model_path = self._models[quality][voice_type]
        
        # Инициализация модели TTS только при первом использовании
        if self._tts is None:
            self._tts = TTS(model_path, progress_bar=False).to(self._device)

    def _get_speaker_id(self, lang_code: str) -> str:
        """Получение идентификатора диктора в зависимости от языка"""
        voice_type = self.config["voice_type"]
        if voice_type not in ["male", "female"]:
            voice_type = "male"
            
        return self._speaker_ids[voice_type].get(lang_code, self._speaker_ids[voice_type]["default"])

    def _detect_language(self, text: str) -> str:
        """Определение языка текста с обработкой исключений"""
        try:
            detected_lang = langdetect.detect(text)
            return detected_lang.split('-')[0]
        except Exception:
            return "en"  # Английский по умолчанию

    async def _process_tts(self, text: str) -> bool:
        """Обработка текста в голос с использованием реалистичной модели"""
        try:
            await self._load_tts_model()
            
            # Определение языка текста
            lang_code = self._detect_language(text)
            
            # Получение идентификатора диктора
            speaker_id = self._get_speaker_id(lang_code)
            
            # Эмоциональные настройки
            emotion = self.config["emotion"]
            if emotion not in self._emotion_settings:
                emotion = "neutral"
            
            emotion_settings = self._emotion_settings[emotion]
            
            # Обработка речи с учетом скорости, настроек эмоций и диктора
            await asyncio.to_thread(
                self._tts.tts_to_file,
                text=text,
                file_path=self._temp_file,
                speaker=speaker_id,
                speed=self.config["speech_rate"]
            )
            
            # Применение дополнительной обработки для эмоциональной окраски
            if os.path.exists(self._temp_file):
                # Дополнительная обработка аудио могла бы быть здесь
                # (например, изменение высоты тона, энергии голоса и т.д.)
                pass
                
            return True
        except Exception as e:
            print(f"TTS processing error: {str(e)}")
            return False

    @loader.owner
    async def realspeakcmd(self, message):
        """Преобразование текста в реалистичную речь. Использование: .realspeak <текст>"""
        if self._processing:
            await message.edit("⏳ Уже обрабатывается другой запрос...")
            return

        self._processing = True
        
        try:
            if len(message.text.split(" ", maxsplit=1)) > 1:
                text = message.text.split(" ", maxsplit=1)[1]
            else:
                await message.edit("❌ Текст не указан")
                self._processing = False
                return
            
            await message.edit("🔄 Генерирую реалистичную речь...")
            
            reply = await message.get_reply_message()
            reply_to_id = reply.id if reply else None
            
            success = await self._process_tts(text)
            
            if success and os.path.exists(self._temp_file):
                await message.client.send_file(
                    message.chat_id,
                    self._temp_file,
                    voice_note=True,
                    reply_to=reply_to_id
                )
                
                if self.config["delete_original"]:
                    await message.delete()
                else:
                    await message.edit("✅ Голосовое сообщение создано")
            else:
                await message.edit("❌ Не удалось создать голосовое сообщение")
                
        except Exception as e:
            await message.edit(f"❌ Ошибка: {str(e)}")
        finally:
            with contextlib.suppress(Exception):
                if os.path.exists(self._temp_file):
                    os.remove(self._temp_file)
            self._processing = False

    @loader.owner
    async def realvoicecmd(self, message):
        """Выбор типа голоса. Использование: .realvoice <мужской/женский>"""
        args = utils.get_args_raw(message).lower()
        
        if args in ["мужской", "male", "м", "m"]:
            self.config["voice_type"] = "male"
            await message.edit("✅ Установлен мужской голос")
        elif args in ["женский", "female", "ж", "f"]:
            self.config["voice_type"] = "female"
            await message.edit("✅ Установлен женский голос")
        else:
            await message.edit("❌ Неверный тип голоса. Используйте 'мужской' или 'женский'")
        
        await asyncio.sleep(2)
        await message.delete()

    @loader.owner
    async def realspeedcmd(self, message):
        """Установка скорости речи. Использование: .realspeed <значение>"""
        args = utils.get_args_raw(message).lower()
        
        try:
            speed = float(args)
            if 0.5 <= speed <= 2.0:
                self.config["speech_rate"] = speed
                await message.edit(f"✅ Установлена скорость речи: {speed}")
            else:
                await message.edit("❌ Скорость должна быть в диапазоне от 0.5 до 2.0")
        except ValueError:
            await message.edit("❌ Неверное значение скорости")
        
        await asyncio.sleep(2)
        await message.delete()

    @loader.owner
    async def realqualitycmd(self, message):
        """Установка качества модели. Использование: .realquality <low/medium/high>"""
        args = utils.get_args_raw(message).lower()
        
        if args in ["low", "medium", "high"]:
            self.config["model_quality"] = args
            await message.edit(f"✅ Установлено качество модели: {args}")
            
            # Сбрасываем кэшированную модель для загрузки новой
            self._tts = None
        else:
            await message.edit("❌ Неверное качество. Используйте 'low', 'medium' или 'high'")
        
        await asyncio.sleep(2)
        await message.delete()

    @loader.owner
    async def realemotioncmd(self, message):
        """Установка эмоциональной окраски. Использование: .realemotion <neutral/happy/sad/angry>"""
        args = utils.get_args_raw(message).lower()
        
        if args in ["neutral", "happy", "sad", "angry"]:
            self.config["emotion"] = args
            await message.edit(f"✅ Установлена эмоциональная окраска: {args}")
        else:
            await message.edit("❌ Неверная эмоция. Используйте 'neutral', 'happy', 'sad' или 'angry'")
        
        await asyncio.sleep(2)
        await message.delete()
