from .. import loader, utils
import qrcode
from io import BytesIO
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageEnhance, ImageOps
import math
import random
import os
import glob
import asyncio
import time
import logging

logger = logging.getLogger(__name__)

@loader.tds
class UltimateYueQRCodeMod(loader.Module):
    """Создает идеально красивые аниме QR-коды с Юэ и очищает хранилище"""
    
    strings = {"name": "UltimateYueQR"}
    
    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
    
    async def _periodic_cleanup(self):
        """Периодическая очистка временных файлов"""
        while True:
            try:
                self._cleanup_temp_files()
                await asyncio.sleep(3600)  # Проверка каждый час
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
                await asyncio.sleep(3600)
    
    def _cleanup_temp_files(self):
        """Удаляет временные файлы с диска"""
        try:
            # Типичные пути временных файлов
            temp_paths = [
                "/tmp/*.png", "/tmp/*.jpg", "/tmp/*.jpeg",
                os.path.join(os.environ.get("TEMP", ""), "*.png"),
                os.path.join(os.environ.get("TMP", ""), "*.png"),
                "*.tmp", "*.temp", "*.cache"
            ]
            
            deleted_count = 0
            for path_pattern in temp_paths:
                try:
                    for file_path in glob.glob(path_pattern):
                        # Проверяем, что файл старше 1 часа
                        if os.path.exists(file_path) and time.time() - os.path.getmtime(file_path) > 3600:
                            os.remove(file_path)
                            deleted_count += 1
                except Exception:
                    pass
            
            logger.info(f"Cleaned up {deleted_count} temporary files")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    async def qrcmd(self, message):
        """Создать ультимативный аниме QR-код с Юэ. Используй: .qr <текст/ссылка>"""
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, "❌")
            return
        
        await utils.answer(message, "🔄")
        
        try:
            # Создаем улучшенный QR-код с максимальным качеством
            qr = qrcode.QRCode(
                version=3,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=15,
                border=4,
            )
            qr.add_data(args)
            qr.make(fit=True)
            
            # Расширенная цветовая палитра в розовых тонах
            pink_gradients = [
                (255, 182, 193),  # Light pink
                (255, 105, 180),  # Hot pink
                (255, 20, 147),   # Deep pink
                (219, 112, 147),  # Pale violet red
                (255, 0, 255),    # Magenta
                (238, 130, 238),  # Violet
                (218, 112, 214),  # Orchid
                (186, 85, 211),   # Medium orchid
                (221, 160, 221),  # Plum
                (255, 0, 127)     # Rose
            ]
            
            # Базовые цвета
            main_color = pink_gradients[1]
            accent_color = pink_gradients[3]
            bg_color = (252, 246, 255)  # Почти белый с розовым оттенком
            
            # Создаем базовое изображение с расширенным размером для эффектов
            qr_matrix = qr.modules
            matrix_size = len(qr_matrix)
            cell_size = 15
            padding = 80  # Дополнительное пространство вокруг QR-кода для декоративных элементов
            
            qr_width = matrix_size * cell_size
            qr_height = matrix_size * cell_size
            img_width = qr_width + 2 * padding
            img_height = qr_height + 2 * padding
            
            # Создаем базовое изображение с градиентным фоном
            base_img = Image.new("RGBA", (img_width, img_height), (0, 0, 0, 0))
            
            # Создаем градиентный фон
            for y in range(img_height):
                for x in range(img_width):
                    # Создаем радиальный градиент от центра
                    center_x, center_y = img_width // 2, img_height // 2
                    distance = math.sqrt((x - center_x) ** 2 + (y - center_y) ** 2)
                    max_distance = math.sqrt((img_width // 2) ** 2 + (img_height // 2) ** 2)
                    ratio = min(1.0, distance / max_distance)
                    
                    # Интерполируем между светлым центром и более темным краем
                    r = int(bg_color[0] - (20 * ratio))
                    g = int(bg_color[1] - (30 * ratio))
                    b = int(bg_color[2] - (10 * ratio))
                    
                    # Создаем легкий узор для фона
                    if (x + y) % 20 == 0:
                        r = min(255, r + 5)
                        g = min(255, g + 5)
                        b = min(255, b + 5)
                    
                    if x < img_width and y < img_height:  # Проверка границ
                        base_img.putpixel((x, y), (r, g, b, 255))
            
            # Слой для QR-кода
            qr_layer = Image.new("RGBA", (img_width, img_height), (0, 0, 0, 0))
            draw_qr = ImageDraw.Draw(qr_layer)
            
            # Функция для получения случайного цвета из градиента
            def get_gradient_color(base_index=None, alpha=255):
                if base_index is None:
                    base = random.choice(pink_gradients)
                else:
                    base = pink_gradients[base_index % len(pink_gradients)]
                
                variation = random.randint(-15, 15)
                return (
                    max(0, min(255, base[0] + variation)),
                    max(0, min(255, base[1] + variation)),
                    max(0, min(255, base[2] + variation)),
                    alpha
                )
            
            # Определяем области позиционных шаблонов
            def is_position_pattern(i, j):
                # Верхний левый, верхний правый и нижний левый углы
                return (
                    (i < 7 and j < 7) or
                    (i < 7 and j >= matrix_size - 7) or
                    (i >= matrix_size - 7 and j < 7)
                )
            
            # Определяем центральную область для Юэ
            def is_center_area(i, j):
                center_i, center_j = matrix_size // 2, matrix_size // 2
                radius = matrix_size // 5
                return math.sqrt((i - center_i) ** 2 + (j - center_j) ** 2) < radius
            
            # Добавляем декоративные элементы на фон
            for _ in range(50):
                x = random.randint(0, img_width - 1)
                y = random.randint(0, img_height - 1)
                size = random.randint(2, 6)
                
                # Случайный выбор между сакурой, звездой и кружком
                shape_type = random.choice(["sakura", "star", "circle"])
                
                if shape_type == "sakura":
                    # Рисуем цветок сакуры
                    petals = 5
                    for p in range(petals):
                        angle = p * (360 / petals)
                        rad = math.radians(angle)
                        petal_x = x + size * 2 * math.cos(rad)
                        petal_y = y + size * 2 * math.sin(rad)
                        
                        draw_qr.ellipse([
                            petal_x - size, petal_y - size,
                            petal_x + size, petal_y + size
                        ], fill=get_gradient_color(0, 100))
                    
                    # Центр цветка
                    draw_qr.ellipse([
                        x - size // 2, y - size // 2,
                        x + size // 2, y + size // 2
                    ], fill=get_gradient_color(3, 150))
                    
                elif shape_type == "star":
                    # Рисуем звезду
                    points = []
                    for i in range(5):
                        # Внешние точки
                        angle_out = i * 72
                        rad_out = math.radians(angle_out)
                        point_x = x + size * 2 * math.cos(rad_out)
                        point_y = y + size * 2 * math.sin(rad_out)
                        points.append((point_x, point_y))
                        
                        # Внутренние точки
                        angle_in = angle_out + 36
                        rad_in = math.radians(angle_in)
                        point_x = x + size * math.cos(rad_in)
                        point_y = y + size * math.sin(rad_in)
                        points.append((point_x, point_y))
                    
                    draw_qr.polygon(points, fill=get_gradient_color(8, 120))
                
                else:  # circle
                    draw_qr.ellipse([
                        x - size, y - size,
                        x + size, y + size
                    ], fill=get_gradient_color(4, 100))
            
            # Рисуем QR-код с эффектами
            for i in range(matrix_size):
                for j in range(matrix_size):
                    if qr_matrix[i][j]:
                        # Преобразуем координаты матрицы в координаты изображения
                        x = padding + j * cell_size + cell_size // 2
                        y = padding + i * cell_size + cell_size // 2
                        
                        if is_position_pattern(i, j):
                            # Стилизованный позиционный шаблон
                            if (i == 0 or i == 6 or i == matrix_size - 7 or i == matrix_size - 1 or
                                j == 0 or j == 6 or j == matrix_size - 7 or j == matrix_size - 1 or
                                (1 <= i <= 5 and 1 <= j <= 5) or
                                (1 <= i <= 5 and matrix_size - 6 <= j <= matrix_size - 2) or
                                (matrix_size - 6 <= i <= matrix_size - 2 and 1 <= j <= 5)):
                                
                                # Внешний квадрат для позиционных маркеров
                                size = cell_size * 0.9
                                draw_qr.rectangle([
                                    x - size, y - size, 
                                    x + size, y + size
                                ], fill=get_gradient_color(2), outline=get_gradient_color(1), width=2)
                            else:
                                # Внутренние части позиционных маркеров
                                size = cell_size * 0.7
                                draw_qr.ellipse([
                                    x - size, y - size,
                                    x + size, y + size
                                ], fill=get_gradient_color(0))
                        
                        elif is_center_area(i, j):
                            # Пропускаем центральную область для Юэ
                            pass
                        
                        elif (i + j) % 4 == 0:
                            # Каждый четвертый элемент - сердечко
                            size = cell_size * 0.6
                            
                            # Простое сердце из двух кругов и треугольника
                            circle_y = y - size * 0.2
                            
                            # Левый круг
                            draw_qr.ellipse([
                                x - size, circle_y - size/2,
                                x, circle_y + size/2
                            ], fill=get_gradient_color())
                            
                            # Правый круг
                            draw_qr.ellipse([
                                x, circle_y - size/2,
                                x + size, circle_y + size/2
                            ], fill=get_gradient_color())
                            
                            # Треугольник снизу
                            draw_qr.polygon([
                                (x - size, circle_y),
                                (x + size, circle_y),
                                (x, y + size)
                            ], fill=get_gradient_color())
                            
                        elif (i * j) % 5 == 0:
                            # Каждый пятый элемент - звездочка
                            size = cell_size * 0.7
                            points = []
                            for angle in range(0, 360, 45):
                                rad = math.radians(angle)
                                px = x + size * 0.5 * math.cos(rad)
                                py = y + size * 0.5 * math.sin(rad)
                                points.append((px, py))
                            draw_qr.polygon(points, fill=get_gradient_color())
                            
                        else:
                            # Обычные точки - круги разных размеров
                            size_variation = random.uniform(0.5, 0.8)
                            size = cell_size * size_variation
                            
                            # Легкий эффект свечения
                            glow_size = size * 1.2
                            draw_qr.ellipse([
                                x - glow_size, y - glow_size,
                                x + glow_size, y + glow_size
                            ], fill=(*get_gradient_color()[:3], 30))  # Полупрозрачный
                            
                            draw_qr.ellipse([
                                x - size, y - size,
                                x + size, y + size
                            ], fill=get_gradient_color())
            
            # Создаем центральный элемент Юэ
            center_x = img_width // 2
            center_y = img_height // 2
            center_size = min(qr_width, qr_height) // 4
            
            # Создаем детализированную Юэ
            yue_layer = Image.new("RGBA", (img_width, img_height), (0, 0, 0, 0))
            draw_yue = ImageDraw.Draw(yue_layer)
            
            # Функция рисования блика
            def draw_shine(x, y, size, draw, angle=None):
                # Рисуем блик на заданном месте
                if angle is None:
                    angle = random.randint(0, 360)
                rad = math.radians(angle)
                dx = math.cos(rad) * size * 0.3
                dy = math.sin(rad) * size * 0.3
                
                for i in range(3):
                    alpha = 150 - i * 40
                    s = size * (1 - i * 0.2)
                    draw.ellipse([
                        x + dx - s/2, y + dy - s/2,
                        x + dx + s/2, y + dy + s/2
                    ], fill=(255, 255, 255, alpha))
            
            # Очищаем центральную область QR-кода
            center_clear_size = center_size * 1.5
            mask = Image.new("L", (img_width, img_height), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse([
                center_x - center_clear_size,
                center_y - center_clear_size,
                center_x + center_clear_size,
                center_y + center_clear_size
            ], fill=255)
            
            # Слой Юэ
            
            # 1. Голова/лицо
            face_color = (255, 230, 240, 255)  # Светлый оттенок для кожи
            draw_yue.ellipse([
                center_x - center_size * 0.8,
                center_y - center_size * 0.8,
                center_x + center_size * 0.8,
                center_y + center_size * 0.8
            ], fill=face_color, outline=(180, 90, 120, 200), width=2)
            
            # 2. Волосы (серебристо-пурпурные, как у Юэ)
            hair_color = (220, 190, 230, 255)  # Серебристо-пурпурный
            hair_shade = (160, 120, 180, 255)  # Более темный оттенок для теней
            
            # Основная масса волос
            for i in range(16):
                angle = i * 22.5
                length = center_size * random.uniform(0.9, 1.3)
                
                if 45 <= angle <= 135:  # Верхняя часть головы - меньше волос
                    length *= 0.7
                
                rad = math.radians(angle)
                end_x = center_x + length * math.cos(rad)
                end_y = center_y + length * math.sin(rad)
                
                # Варьируем ширину прядей
                width = random.randint(5, 12)
                
                # Рисуем основную прядь
                draw_yue.line([(center_x, center_y), (end_x, end_y)], 
                             fill=hair_color, width=width)
                
                # Для некоторых прядей добавляем детали
                if random.random() > 0.6:
                    detail_length = length * 0.7
                    detail_angle = angle + random.uniform(-20, 20)
                    detail_rad = math.radians(detail_angle)
                    
                    mid_x = center_x + length * 0.6 * math.cos(rad)
                    mid_y = center_y + length * 0.6 * math.sin(rad)
                    
                    detail_end_x = mid_x + detail_length * 0.4 * math.cos(detail_rad)
                    detail_end_y = mid_y + detail_length * 0.4 * math.sin(detail_rad)
                    
                    draw_yue.line([(mid_x, mid_y), (detail_end_x, detail_end_y)], 
                                 fill=hair_shade, width=width-2)
            
            # 3. Глаза (красные, характерные для Юэ)
            eye_size = center_size * 0.2
            eye_color = (200, 10, 40, 255)  # Красные глаза
            
            # Левый глаз
            left_eye_x = center_x - center_size * 0.3
            left_eye_y = center_y - center_size * 0.1
            
            # Добавляем тень вокруг глаз
            draw_yue.ellipse([
                left_eye_x - eye_size * 1.2, 
                left_eye_y - eye_size * 1.2,
                left_eye_x + eye_size * 1.2, 
                left_eye_y + eye_size * 1.2
            ], fill=(0, 0, 0, 50))
            
            # Основной цвет глаза
            draw_yue.ellipse([
                left_eye_x - eye_size, 
                left_eye_y - eye_size,
                left_eye_x + eye_size, 
                left_eye_y + eye_size
            ], fill=eye_color)
            
            # Блик в глазу
            draw_shine(left_eye_x, left_eye_y, eye_size * 0.6, draw_yue, 45)
            
            # Правый глаз
            right_eye_x = center_x + center_size * 0.3
            right_eye_y = center_y - center_size * 0.1
            
            # Тень
            draw_yue.ellipse([
                right_eye_x - eye_size * 1.2, 
                right_eye_y - eye_size * 1.2,
                right_eye_x + eye_size * 1.2, 
                right_eye_y + eye_size * 1.2
            ], fill=(0, 0, 0, 50))
            
            # Основной цвет
            draw_yue.ellipse([
                right_eye_x - eye_size, 
                right_eye_y - eye_size,
                right_eye_x + eye_size, 
                right_eye_y + eye_size
            ], fill=eye_color)
            
            # Блик
            draw_shine(right_eye_x, right_eye_y, eye_size * 0.6, draw_yue, 45)
            
            # 4. Рот (маленький и милый)
            mouth_y = center_y + center_size * 0.3
            
            # Используем кривую Безье для более естественной улыбки
            points = [
                (center_x - center_size * 0.2, mouth_y),
                (center_x, mouth_y + center_size * 0.1),
                (center_x + center_size * 0.2, mouth_y)
            ]
            
            # Рисуем улыбку
            draw_yue.line(points, fill=(255, 20, 90, 220), width=2, joint="curve")
            
            # 5. Добавляем румянец на щеках
            blush_size = center_size * 0.15
            blush_color = (255, 150, 150, 100)  # Полупрозрачный розовый
            
            # Левая щека
            draw_yue.ellipse([
                center_x - center_size * 0.5 - blush_size,
                center_y + center_size * 0.1 - blush_size,
                center_x - center_size * 0.5 + blush_size,
                center_y + center_size * 0.1 + blush_size
            ], fill=blush_color)
            
            # Правая щека
            draw_yue.ellipse([
                center_x + center_size * 0.5 - blush_size,
                center_y + center_size * 0.1 - blush_size,
                center_x + center_size * 0.5 + blush_size,
                center_y + center_size * 0.1 + blush_size
            ], fill=blush_color)
            
            # 6. Добавляем элементы, характерные для Юэ (украшения, аксессуары)
            
            # Ободок или корона (Юэ - вампир и дворянка)
            crown_color = (180, 30, 100, 255)
            crown_points = []
            
            for i in range(7):
                angle = -90 + i * 30  # Распределение по верхней части головы
                rad = math.radians(angle)
                
                # Внешние точки (пики)
                if i % 2 == 0:
                    r = center_size * 0.85  # Пики выше
                else:
                    r = center_size * 0.75  # Впадины ниже
                
                x = center_x + r * math.cos(rad)
                y = center_y + r * math.sin(rad)
                crown_points.append((x, y))
            
            # Рисуем корону
            draw_yue.polygon(crown_points, fill=crown_color, outline=(220, 120, 180, 255), width=2)
            
            # Добавляем блестки для короны
            for i in range(4):
                shine_x = center_x + center_size * 0.8 * math.cos(math.radians(-90 + i * 60))
                shine_y = center_y + center_size * 0.8 * math.sin(math.radians(-90 + i * 60))
                draw_shine(shine_x, shine_y, center_size * 0.1, draw_yue)
            
            # 7. Добавляем эффект аниме-свечения вокруг Юэ
            glow_layer = Image.new("RGBA", (img_width, img_height), (0, 0, 0, 0))
            draw_glow = ImageDraw.Draw(glow_layer)
            
            # Создаем мягкое свечение вокруг персонажа
            for i in range(5):
                alpha = 40 - i * 8
                size = center_size * (1.1 + i * 0.1)
                
                draw_glow.ellipse([
                    center_x - size, center_y - size,
                    center_x + size, center_y + size
                ], fill=(255, 180, 220, alpha))
            
            # Собираем все слои вместе
            final_img = Image.alpha_composite(base_img, glow_layer)
            final_img = Image.alpha_composite(final_img, qr_layer)
            
            # Применяем маску, чтобы очистить центр для Юэ
            qr_mask = Image.new("RGBA", (img_width, img_height), (0, 0, 0, 0))
            qr_mask_draw = ImageDraw.Draw(qr_mask)
            
            # Создаем маску для области Юэ
            yue_area_size = center_size * 1.2
            qr_mask_draw.ellipse([
                center_x - yue_area_size, center_y - yue_area_size,
                center_x + yue_area_size, center_y + yue_area_size
            ], fill=(0, 0, 0, 255))
            
            # Инвертируем маску
            qr_mask_array = ImageOps.invert(qr_mask.convert("L"))
            
            # Применяем маску к QR-слою
            qr_masked = Image.new("RGBA", (img_width, img_height), (0, 0, 0, 0))
            qr_masked.paste(final_img, (0, 0), qr_mask_array)
            
            # Добавляем Юэ поверх всего
            final_img = Image.alpha_composite(qr_masked, yue_layer)
            
            # Добавляем финальные эффекты
            final_img = final_img.filter(ImageFilter.GaussianBlur(radius=0.5))
            final_img = ImageEnhance.Brightness(final_img).enhance(1.05)
            final_img = ImageEnhance.Contrast(final_img).enhance(1.1)
            
            # Оптимизируем размер файла
            buffer = BytesIO()
            final_img.save(buffer, format="PNG", optimize=True, quality=95)
            buffer.seek(0)
            
            # Отправляем без текста
            await message.client.send_file(
                message.chat_id,
                buffer,
                reply_to=message.id,
                silent=True
            )
            
            # Удаляем сообщение-индикатор
            await message.delete()
            
            # Очищаем временные файлы
            self._cleanup_temp_files()
            
        except Exception as e:
            logger.error(f"QR generation error: {e}")
            await utils.answer(message, "❌")
