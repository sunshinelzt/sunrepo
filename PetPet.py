# meta developer: @sunshinelzt
# meta description: Создает анимированные GIF-изображения с эффектом поглаживания
# banner: https://img.icons8.com/color/452/petting.png
# requires: pet-pet-gif pillow
# scope: hikka_min 1.5.0

import asyncio
import logging
import tempfile
import contextlib
from typing import Union, Optional, Tuple
from io import BytesIO
import os

from telethon.tl.types import Message, DocumentAttributeFilename, DocumentAttributeImageSize
from telethon import events

from .. import loader, utils
from petpetgif import petpet
from PIL import Image, UnidentifiedImageError

logger = logging.getLogger(__name__)

@loader.tds
class EnhancedPetPetMod(loader.Module):
    """
    Создает анимированные GIF-изображения с эффектом поглаживания. 
    Поддерживает различные источники изображений и настройки анимации.
    """
    
    strings = {
        "name": "EnhancedPetPet",
        "no_media": "<emoji document_id=5465665476971471368>❌</emoji> <b>Ответьте на сообщение с изображением или отправьте изображение с командой</b>",
        "processing": "<emoji document_id=5213452215527677338>⏳</emoji> <b>Создаю анимацию...</b>",
        "error": "<emoji document_id=5465665476971471368>❌</emoji> <b>Ошибка:</b> <code>{}</code>",
        "success": "<emoji document_id=5206607081334906820>✅</emoji> <b>Готово!</b>",
        "config_saved": "<emoji document_id=5206607081334906820>✅</emoji> <b>Настройки сохранены</b>",
        "fps_set": "<emoji document_id=5206607081334906820>✅</emoji> <b>FPS установлен на {}</b>",
        "delay_set": "<emoji document_id=5206607081334906820>✅</emoji> <b>Задержка установлена на {} мс</b>"
    }
    
    def __init__(self):
        self.config = loader.ModuleConfig(
            "FPS", 15, "Количество кадров в секунду для анимации (от 10 до 30)",
            "FRAMES", 10, "Количество кадров в анимации (от 5 до 20)",
            "RESOLUTION", 256, "Разрешение выходного изображения (от 128 до 512)",
            "AUTO_DELETE", True, "Автоматически удалять сообщение с командой после обработки",
            "SQUISH", 0.8, "Степень сжатия при поглаживании (от 0.5 до 1)",
            "DELETE_ORIGINAL", False, "Удалять оригинальное сообщение с изображением"
        )

    async def client_ready(self, client, db):
        """Инициализация при запуске модуля"""
        self._client = client
        self._db = db
        self._temp_files = []  # Для отслеживания временных файлов

    @contextlib.asynccontextmanager
    async def temp_file(self, suffix=None):
        """Контекстный менеджер для создания и автоматической очистки временных файлов"""
        fd, path = tempfile.mkstemp(suffix=suffix)
        os.close(fd)
        self._temp_files.append(path)
        try:
            yield path
        finally:
            if os.path.exists(path):
                try:
                    os.remove(path)
                    if path in self._temp_files:
                        self._temp_files.remove(path)
                except Exception as e:
                    logger.warning(f"Не удалось удалить временный файл {path}: {e}")

    async def get_media_content(self, message: Message) -> Tuple[Optional[bytes], Optional[str]]:
        """Получает содержимое медиа из сообщения или ответа на сообщение
        
        Возвращает кортеж (содержимое в байтах, расширение файла)
        """
        reply = await message.get_reply_message() if message.is_reply else None
        source = reply or message
        
        if not source or not source.media:
            return None, None
            
        try:
            # Определяем тип медиа и расширение
            ext = None
            if hasattr(source.media, 'photo'):
                ext = '.jpg'
            elif hasattr(source.media, 'document'):
                mime = source.media.document.mime_type
                if mime and mime.startswith('image/'):
                    for attr in source.media.document.attributes:
                        if isinstance(attr, DocumentAttributeFilename):
                            ext = os.path.splitext(attr.file_name)[1].lower()
                            break
                    if not ext:
                        ext = '.' + mime.split('/')[1]
            
            if not ext:
                return None, None
                
            # Загружаем данные
            data = await self._client.download_media(source, bytes)
            return data, ext
            
        except Exception as e:
            logger.error(f"Ошибка при получении медиа: {e}")
            return None, None

    async def create_petpet_gif(self, image_data: bytes, output_path: str = None) -> Union[BytesIO, str]:
        """Создает анимацию pet-pet из изображения"""
        try:
            # Сначала проверяем, что это действительно изображение
            with BytesIO(image_data) as img_io:
                try:
                    img = Image.open(img_io)
                    img.verify()  # Проверка целостности
                except UnidentifiedImageError:
                    raise ValueError("Файл не является поддерживаемым изображением")
            
            # Создаем новый BytesIO с данными для обработки
            source = BytesIO(image_data)
            
            # Настройки для petpet
            config = {
                "fps": self.config["FPS"],
                "squish": self.config["SQUISH"],
                "resolution": self.config["RESOLUTION"],
                "frames": self.config["FRAMES"]
            }
            
            # Создаем анимацию
            if output_path:
                # Сохраняем во временный файл
                petpet.make(source, output_path, **config)
                return output_path
            else:
                # Сохраняем в память
                output = BytesIO()
                petpet.make(source, output, **config)
                output.name = "petpet.gif"
                output.seek(0)
                return output
                
        except Exception as e:
            logger.error(f"Ошибка при создании GIF: {e}")
            raise

    @loader.command(ru_doc="- Настройка параметров модуля")
    async def petcfg(self, message: Message):
        """- Настройка параметров модуля"""
        await self.allmodules.commands["config"](
            await utils.answer(message, f"{self.get_prefix()}config {self.strings['name']}")
        )

    @loader.command(ru_doc="[число] - Установить частоту кадров анимации")
    async def petfps(self, message: Message):
        """[число] - Установить частоту кадров анимации (от 10 до 30)"""
        args = utils.get_args_raw(message)
        if not args or not args.isdigit():
            await utils.answer(message, f"Текущий FPS: {self.config['FPS']}\nДля изменения: {self.get_prefix()}petfps [число от 10 до 30]")
            return
            
        fps = int(args)
        if 10 <= fps <= 30:
            self.config["FPS"] = fps
            await utils.answer(message, self.strings["fps_set"].format(fps))
        else:
            await utils.answer(message, "FPS должен быть в диапазоне от 10 до 30")

    @loader.command(ru_doc="- Создать анимацию с поглаживанием изображения")
    async def pet(self, message: Message):
        """- Создает анимированную GIF с эффектом поглаживания. Ответьте на фото/стикер или отправьте с командой"""
        try:
            # Получаем медиа
            image_data, ext = await self.get_media_content(message)
            if not image_data:
                await utils.answer(message, self.strings["no_media"])
                return
                
            # Показываем статус обработки
            status_message = await utils.answer(message, self.strings["processing"])
            
            # Создаем GIF
            async with self.temp_file(suffix='.gif') as output_path:
                # Функция создания GIF может занять время, выполняем в отдельной задаче
                gif_file = await asyncio.to_thread(
                    self.create_petpet_gif,
                    image_data,
                    output_path
                )
                
                # Определяем параметры для отправки
                reply_to_id = None
                if message.is_reply and not message.is_private:
                    reply = await message.get_reply_message()
                    if message.chat.forum:
                        reply_to_id = reply.id
                
                # Отправляем результат
                await self._client.send_file(
                    message.chat_id,
                    file=gif_file,
                    force_document=False,
                    reply_to=reply_to_id,
                    caption="<emoji document_id=5206607081334906820>✅</emoji> <b>PetPet</b>"
                )
                
                # Удаляем сообщения согласно настройкам
                if self.config["AUTO_DELETE"] and isinstance(status_message, Message):
                    await status_message.delete()
                    
                # Удаляем оригинальное сообщение если нужно
                if self.config["DELETE_ORIGINAL"] and message.is_reply:
                    reply = await message.get_reply_message()
                    await reply.delete()
            
        except Exception as e:
            logger.exception(f"Ошибка в команде pet: {e}")
            await utils.answer(
                status_message if locals().get('status_message') else message, 
                self.strings["error"].format(str(e))
            )

    def get_prefix(self):
        """Получает префикс команд"""
        return self._db.get("hikka.main", "command_prefix", ".")
        
    async def on_unload(self):
        """Очистка при выгрузке модуля"""
        # Удаляем все оставшиеся временные файлы
        for path in self._temp_files:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception as e:
                    logger.warning(f"Не удалось удалить временный файл при выгрузке: {e}")
