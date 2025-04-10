# meta developer: @sunshinelzt

import json
import logging
import random
from asyncio import sleep
from typing import Union, List, Dict, Any, Optional

import requests
from telethon.tl.types import Message

from .. import loader, utils
from ..inline.types import InlineCall

logger = logging.getLogger(__name__)


@loader.tds
class LoveMagicMod(loader.Module):
    """Анимация сердечек в стиле TikTok, реализованная в Hikka без спама в логи"""

    strings = {
        "name": "LoveMagic",
        "message": "<b>❤️‍🔥 I want to tell you something...</b>\n<i>{}</i>",
        "loading": "<b>Загрузка анимаций...</b>",
        "error_loading": "<b>❌ Ошибка загрузки анимаций!</b>\n<i>Проверьте подключение к интернету</i>",
        "classic_button": "💖 Классика",
        "gay_button": "🏳️‍🌈 Радуга",
        "custom_button": "✨ Своё сообщение",
        "back_button": "« Назад",
        "select_type": "<b>🎭 Выберите тип анимации:</b>",
        "enter_text": "<b>✏️ Введите своё сообщение:</b>",
        "default_classic": "Я ❤️ тебя!",
        "default_gay": "Я люблю тебя всеми цветами радуги! 💙",
        "promote": "💝 Хочу также!",
    }

    strings_ru = {
        "name": "СердечныеЧары",
        "message": "<b>❤️‍🔥 Я хочу тебе сказать кое-что...</b>\n<i>{}</i>",
        "loading": "<b>Загрузка анимаций...</b>",
        "error_loading": "<b>❌ Ошибка загрузки анимаций!</b>\n<i>Проверьте подключение к интернету</i>",
        "classic_button": "💖 Классика",
        "gay_button": "🏳️‍🌈 Радуга",
        "custom_button": "✨ Своё сообщение",
        "back_button": "« Назад",
        "select_type": "<b>🎭 Выберите тип анимации:</b>",
        "enter_text": "<b>✏️ Введите своё сообщение:</b>",
        "default_classic": "Я ❤️ тебя!",
        "default_gay": "Я люблю тебя всеми цветами радуги! 💙",
        "promote": "💝 Хочу также!",
        "_cls_doc": "Анимация сердечек в стиле TikTok, реализованная в Hikka без спама в логи",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            "CLASSIC_URL",
            "https://gist.github.com/hikariatama/89d0246c72e5882e12af43be63f5bca5/raw/08a5df7255d5e925ab2ede1efc892d9dc93af8e1/ily_classic.json",
            lambda: "URL для классической анимации сердечек",
            "GAY_URL",
            "https://gist.github.com/hikariatama/3596a7c4f273a41e5289586ccff53a71/raw/f680c04f5855dcb02645b603d84d2496a8ea3350/ily_gay.json",
            lambda: "URL для радужной анимации сердечек",
            "INTERVAL",
            0.5,
            lambda: "Интервал между кадрами анимации (в секундах)",
            "TIMEOUT",
            10,
            lambda: "Время отображения анимации перед переходом к финальному сообщению (в секундах)",
            "PROMOTE_URL",
            "https://t.me/hikka_talks",
            lambda: "URL для кнопки \"Хочу также!\"",
        )
        self.classic_frames: List[str] = []
        self.gay_frames: List[str] = []
        self.is_loaded = False

    async def client_ready(self, client, db):
        """Загрузка анимаций при запуске модуля"""
        try:
            self.classic_frames = (
                await utils.run_sync(
                    requests.get,
                    self.config["CLASSIC_URL"],
                    timeout=10,
                )
            ).json()

            self.gay_frames = (
                await utils.run_sync(
                    requests.get,
                    self.config["GAY_URL"],
                    timeout=10,
                )
            ).json()
            
            self.is_loaded = True
            logger.info("LoveMagic: Анимации успешно загружены")
        except Exception as e:
            logger.error(f"LoveMagic: Ошибка загрузки анимаций: {e}")
            self.is_loaded = False

    async def _check_animations(self, message: Message) -> bool:
        """Проверяет загружены ли анимации и пытается загрузить их при необходимости"""
        if self.is_loaded:
            return True
            
        status_msg = await utils.answer(message, self.strings("loading"))
        
        try:
            self.classic_frames = (
                await utils.run_sync(
                    requests.get,
                    self.config["CLASSIC_URL"],
                    timeout=10,
                )
            ).json()

            self.gay_frames = (
                await utils.run_sync(
                    requests.get,
                    self.config["GAY_URL"],
                    timeout=10,
                )
            ).json()
            
            self.is_loaded = True
            await utils.answer(status_msg, self.strings("select_type"))
            return True
        except Exception as e:
            logger.error(f"LoveMagic: Ошибка загрузки анимаций: {e}")
            await utils.answer(status_msg, self.strings("error_loading"))
            return False

    async def animate(
        self,
        obj: Union[InlineCall, Message],
        frames: List[str],
        interval: float = None,
        inline: bool = False,
    ) -> Union[InlineCall, Message]:
        """Анимирует сообщение, последовательно обновляя его фреймы"""
        interval = interval or self.config["INTERVAL"]
        
        if isinstance(obj, Message):
            message = await utils.answer(obj, frames[0])
            for frame in frames[1:]:
                await sleep(interval)
                message = await utils.answer(message, frame)
            return message
        else:
            for frame in frames:
                await obj.edit(frame)
                await sleep(interval)
            return obj

    async def love_handler(
        self,
        obj: Union[InlineCall, Message],
        text: str,
        animation_type: str = "classic",
        inline: bool = False,
    ):
        """Основной обработчик анимации с текстом"""
        # Выбираем анимацию в зависимости от типа
        if animation_type == "gay":
            frames = self.gay_frames
        else:
            frames = self.classic_frames
            
        # Добавляем постепенное появление текста в конце анимации
        final_frames = frames + [
            f'<b>{" ".join(text.split()[: i + 1])}</b>'
            for i in range(len(text.split()))
        ]

        # Запускаем анимацию
        obj = await self.animate(
            obj, 
            final_frames, 
            interval=self.config["INTERVAL"], 
            inline=inline
        )

        # После анимации ждем некоторое время перед финальным сообщением
        await sleep(self.config["TIMEOUT"])
        
        # Если это инлайн, обновляем на финальное сообщение с кнопкой
        if not isinstance(obj, Message):
            await obj.edit(
                f"<b>{text}</b>",
                reply_markup={
                    "text": self.strings("promote"),
                    "url": self.config["PROMOTE_URL"],
                },
            )
            await obj.unload()

    @loader.command(ru_doc="Показать меню анимаций сердечек")
    async def lovemagic(self, message: Message):
        """Показывает интерактивное меню для выбора анимации сердечек"""
        if not await self._check_animations(message):
            return
            
        await self.inline.form(
            self.strings("select_type"),
            reply_markup=[
                [
                    {
                        "text": self.strings("classic_button"),
                        "callback": self._inline_classic,
                    },
                    {
                        "text": self.strings("gay_button"),
                        "callback": self._inline_gay,
                    },
                ],
                [
                    {
                        "text": self.strings("custom_button"),
                        "callback": self._inline_custom,
                    }
                ]
            ],
            message=message,
            disable_security=True,
        )
    
    async def _inline_classic(self, call: InlineCall):
        """Обработчик для классической анимации"""
        await call.edit(
            self.strings("message").format("*" * len(self.strings("default_classic"))),
            reply_markup={
                "text": "🧸 Открыть",
                "callback": self.love_handler,
                "args": (self.strings("default_classic"),),
                "kwargs": {"animation_type": "classic", "inline": True},
            },
        )
    
    async def _inline_gay(self, call: InlineCall):
        """Обработчик для радужной анимации"""
        await call.edit(
            self.strings("message").format("*" * len(self.strings("default_gay"))),
            reply_markup={
                "text": "🌈 Открыть",
                "callback": self.love_handler,
                "args": (self.strings("default_gay"),),
                "kwargs": {"animation_type": "gay", "inline": True},
            },
        )
    
    async def _inline_custom(self, call: InlineCall):
        """Обработчик для ввода пользовательского текста"""
        await call.edit(
            self.strings("enter_text"),
            reply_markup=[
                [
                    {
                        "text": self.strings("back_button"),
                        "callback": self._back_to_menu,
                    }
                ]
            ],
        )
        await call.set_state("waiting_love_text")
    
    async def _back_to_menu(self, call: InlineCall):
        """Возвращает в основное меню"""
        await call.edit(
            self.strings("select_type"),
            reply_markup=[
                [
                    {
                        "text": self.strings("classic_button"),
                        "callback": self._inline_classic,
                    },
                    {
                        "text": self.strings("gay_button"),
                        "callback": self._inline_gay,
                    },
                ],
                [
                    {
                        "text": self.strings("custom_button"),
                        "callback": self._inline_custom,
                    }
                ]
            ],
        )
    
    async def watcher(self, message: Message):
        """Отслеживает сообщения для обработки пользовательского ввода"""
        if not isinstance(message, Message):
            return
            
        # Проверяем, есть ли активная форма и ожидаем ли мы текст
        form = self.inline._forms.get(utils.get_chat_id(message))
        if not form or not form.get("state") == "waiting_love_text":
            return
            
        # Если сообщение от текущего пользователя и есть текст
        if message.sender_id != self._tg_id or not message.text:
            return
            
        # Получаем текст и удаляем введенное сообщение
        text = message.text
        await message.delete()
        
        # Обновляем форму и вызываем анимацию
        form_message = form.get("message")
        if not form_message:
            return
            
        # Выбираем случайный тип анимации
        animation_type = random.choice(["classic", "gay"])
        
        # Обновляем инлайн сообщение
        await self.inline._bot.edit_message_text(
            self.strings("message").format("*" * len(text)),
            inline_message_id=form_message,
            reply_markup=self.inline.generate_markup(
                {
                    "text": "💖 Открыть",
                    "callback": self.love_handler,
                    "args": (text,),
                    "kwargs": {"animation_type": animation_type, "inline": True},
                }
            ),
        )
        
        # Сбрасываем состояние
        form["state"] = None
    
    @loader.command(ru_doc="Отправить классическую анимацию сердец")
    async def loveclassic(self, message: Message):
        """Отправить сообщение с классической анимацией сердец"""
        if not await self._check_animations(message):
            return
            
        text = utils.get_args_raw(message) or self.strings("default_classic")
        await self.love_handler(message, text, animation_type="classic", inline=False)

    @loader.command(ru_doc="Отправить радужную анимацию сердец")
    async def lovegay(self, message: Message):
        """Отправить сообщение с радужной анимацией сердец"""
        if not await self._check_animations(message):
            return
            
        text = utils.get_args_raw(message) or self.strings("default_gay")
        await self.love_handler(message, text, animation_type="gay", inline=False)
    
    # Поддержка старых команд для обратной совместимости
    async def ilycmd(self, message: Message):
        """Обратная совместимость со старой командой"""
        return await self.loveclassic(message)
        
    async def ilyicmd(self, message: Message):
        """Обратная совместимость со старой командой"""
        if not await self._check_animations(message):
            return
            
        args = utils.get_args_raw(message) or self.strings("default_classic")
        await self.inline.form(
            self.strings("message").format("*" * len(args)),
            reply_markup={
                "text": "🧸 Открыть",
                "callback": self.love_handler,
                "args": (args,),
                "kwargs": {"animation_type": "classic", "inline": True},
            },
            message=message,
            disable_security=True,
        )
        
    async def ilygay(self, message: Message):
        """Обратная совместимость со старой командой"""
        return await self.lovegay(message)
        
    async def ilygayicmd(self, message: Message):
        """Обратная совместимость со старой командой"""
        if not await self._check_animations(message):
            return
            
        args = utils.get_args_raw(message) or self.strings("default_gay")
        await self.inline.form(
            self.strings("message").format("*" * len(args)),
            reply_markup={
                "text": "🌈 Открыть",
                "callback": self.love_handler,
                "args": (args,),
                "kwargs": {"animation_type": "gay", "inline": True},
            },
            message=message,
            disable_security=True,
        )
