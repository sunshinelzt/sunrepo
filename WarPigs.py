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

    async def auto_action(self, message, key, command):
        """Переключает авто-режим"""
        running = self.get(key, False)
        self.set(key, not running)

        if running:
            return await utils.answer(message, self.strings[f"{key}_off"])

        await utils.answer(message, self.strings[f"{key}_on"])
        while self.get(key):
            await message.respond(f"/{command}")
            await asyncio.sleep(86410)

    async def agrow(self, message):
        """Включает/отключает авто-рост"""
        await self.auto_action(message, "pig_growth", "grow")

    async def afight(self, message):
        """Включает/отключает авто-бой"""
        await self.auto_action(message, "pig_fights", "fight")
