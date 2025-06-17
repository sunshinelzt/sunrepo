# meta developer: @sunshinelzt
import random
import asyncio
import time
from telethon.tl.types import InputPeerChannel, MessageMediaDocument
from telethon.tl.functions.messages import GetHistoryRequest
from .. import loader, utils

@loader.tds
class RandomCircleMod(loader.Module):
    """Модуль для отправки случайных кружочков из ВСЕХ сообщений каналов"""
    
    strings = {"name": "RandomCircle"}
    
    def __init__(self):
        self.channels_ids = [
            -1001678673876, -1001829766952, -1001641159794, -1001719785599,
            -1001549768481, -1001345824533, -1001869062957
        ]
        self.full_cache = {}  # Полный кэш всех кружочков
        self.cache_status = {}  # Статус кэширования каналов
        self.quick_pool = []  # Пул для быстрого доступа
        self.indexing_in_progress = set()
        self.last_global_update = 0
        self.global_update_interval = 86400  # 24 часа
    
    async def _index_all_circles_in_channel(self, client, channel_id):
        """Индексирует АБСОЛЮТНО ВСЕ кружочки в канале"""
        if channel_id in self.indexing_in_progress:
            return self.full_cache.get(channel_id, [])
        
        self.indexing_in_progress.add(channel_id)
        
        try:
            entity = await client.get_entity(channel_id)
            peer = InputPeerChannel(entity.id, entity.access_hash)
            
            all_circles = []
            offset_id = 0
            empty_batches = 0
            
            # Сканируем ВСЕ сообщения канала
            while empty_batches < 3:  # Останавливаемся только после 3 пустых батчей
                try:
                    history = await client(GetHistoryRequest(
                        peer=peer, limit=100, offset_id=offset_id,
                        offset_date=None, max_id=0, min_id=0, add_offset=0, hash=0
                    ))
                    
                    if not history.messages:
                        empty_batches += 1
                        continue
                    
                    # Фильтруем кружочки из батча
                    batch_circles = []
                    for msg in history.messages:
                        if self._is_circle_message(msg):
                            batch_circles.append(msg)
                    
                    if batch_circles:
                        all_circles.extend(batch_circles)
                        empty_batches = 0  # Сбрасываем счетчик если нашли кружочки
                    else:
                        empty_batches += 1
                    
                    # Обновляем offset для следующего батча
                    offset_id = history.messages[-1].id
                    
                    # Микро-пауза для избежания лимитов
                    await asyncio.sleep(0.05)
                    
                except Exception:
                    empty_batches += 1
                    await asyncio.sleep(0.1)
            
            # Сохраняем результат
            self.full_cache[channel_id] = all_circles
            self.cache_status[channel_id] = {
                'total_circles': len(all_circles),
                'last_indexed': time.time(),
                'fully_indexed': True
            }
            
            return all_circles
            
        except Exception:
            return []
        finally:
            self.indexing_in_progress.discard(channel_id)
    
    def _is_circle_message(self, msg):
        """Проверка на кружочек"""
        return (isinstance(msg.media, MessageMediaDocument) and
                msg.media.document and
                msg.media.document.attributes and
                any(getattr(attr, 'round_message', False) 
                    for attr in msg.media.document.attributes
                    if hasattr(attr, 'round_message')))
    
    async def _ensure_circles_available(self, client):
        """Гарантирует наличие кружочков для отправки"""
        available_circles = []
        
        # Собираем из уже проиндексированных каналов
        for channel_id, circles in self.full_cache.items():
            if circles:
                available_circles.extend(circles)
        
        # Если кружочков мало, быстро индексируем несколько каналов
        if len(available_circles) < 100:
            quick_channels = random.sample(self.channels_ids, min(3, len(self.channels_ids)))
            
            for channel_id in quick_channels:
                if channel_id not in self.full_cache:
                    # Быстрая индексация первых 200 сообщений
                    circles = await self._quick_index_channel(client, channel_id)
                    if circles:
                        available_circles.extend(circles)
        
        return available_circles
    
    async def _quick_index_channel(self, client, channel_id, limit_batches=2):
        """Быстрая индексация канала (первые N батчей)"""
        try:
            entity = await client.get_entity(channel_id)
            peer = InputPeerChannel(entity.id, entity.access_hash)
            
            circles = []
            offset_id = 0
            
            for _ in range(limit_batches):
                history = await client(GetHistoryRequest(
                    peer=peer, limit=100, offset_id=offset_id,
                    offset_date=None, max_id=0, min_id=0, add_offset=0, hash=0
                ))
                
                if not history.messages:
                    break
                
                for msg in history.messages:
                    if self._is_circle_message(msg):
                        circles.append(msg)
                
                offset_id = history.messages[-1].id
            
            # Сохраняем в кэш
            self.full_cache[channel_id] = circles
            return circles
            
        except Exception:
            return []
    
    async def _background_full_indexing(self, client):
        """Фоновая полная индексация всех каналов"""
        for channel_id in self.channels_ids:
            if channel_id not in self.indexing_in_progress:
                # Запускаем индексацию канала в фоне
                asyncio.create_task(self._index_all_circles_in_channel(client, channel_id))
                # Пауза между запусками индексации
                await asyncio.sleep(1)
    
    async def rccmd(self, message):
        """Отправляет случайный кружочек из ВСЕХ доступных"""
        await message.delete()
        
        try:
            # Получаем доступные кружочки
            available_circles = await self._ensure_circles_available(message.client)
            
            if available_circles:
                # Отправляем случайный кружочек
                random_circle = random.choice(available_circles)
                await message.client.send_file(
                    message.chat_id,
                    file=random_circle.media.document,
                    reply_to=message.reply_to_msg_id if message.is_reply else None
                )
            
            # Запускаем фоновую полную индексацию если нужно
            current_time = time.time()
            if current_time - self.last_global_update > self.global_update_interval:
                self.last_global_update = current_time
                asyncio.create_task(self._background_full_indexing(message.client))
            
            # Периодически запускаем полную индексацию случайного канала
            elif random.random() < 0.1:  # 10% вероятность
                random_channel = random.choice([
                    ch for ch in self.channels_ids 
                    if ch not in self.indexing_in_progress
                ])
                if random_channel:
                    asyncio.create_task(
                        self._index_all_circles_in_channel(message.client, random_channel)
                    )
            
        except Exception:
            # Экстренная стратегия
            try:
                emergency_channel = random.choice(self.channels_ids)
                emergency_circles = await self._quick_index_channel(
                    message.client, emergency_channel, limit_batches=1
                )
                if emergency_circles:
                    await message.client.send_file(
                        message.chat_id,
                        file=random.choice(emergency_circles).media.document,
                        reply_to=message.reply_to_msg_id if message.is_reply else None
                    )
            except Exception:
                pass
