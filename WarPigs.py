# meta developer: @sunshinelzt

from .. import loader, utils
import asyncio


class WarpigsMod(loader.Module):
    """Автоматизирует работу с @warpigs_bot"""

    strings = {
        "name": "WarPigs",
        "pig_growth_on": "<emoji document_id=5316581501360420451>🐷</emoji> <b>Авто-рост свиньи: <i>Включен!</i></b>",
        "pig_growth_off": "<emoji document_id=5316581501360420451>🐷</emoji> <b>Авто-рост свиньи: <i>Отключен.</i></b>",
        "pig_fights_on": "<emoji document_id=5316581501360420451>⚔️</emoji> <b>Авто-бой свиньи: <i>Включен!</i></b>",
        "pig_fights_off": "<emoji document_id=5316581501360420451>⚔️</emoji> <b>Авто-бой свиньи: <i>Отключен.</i></b>",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            "pig_growth", False, "Статус авто-роста",
            "pig_fights", False, "Статус авто-боя"
        )

    async def auto_action(self, message, key, command):
        """Переключает авто-режим"""
        running = self.config[key]
        self.config[key] = not running

        await utils.answer(message, self.strings[f"{key}_on"] if not running else self.strings[f"{key}_off"])

        while self.config[key]:
            await message.respond(f"/{command}")
            await asyncio.sleep(86410)

    @loader.command(ru_doc="Включает/отключает авто-рост свиньи.")
    async def agrow(self, message):
        """Включает/отключает авто-рост"""
        await self.auto_action(message, "pig_growth", "grow")

    @loader.command(ru_doc="Включает/отключает авто-бой свиньи.")
    async def afight(self, message):
        """Включает/отключает авто-бой"""
        await self.auto_action(message, "pig_fights", "fight")
