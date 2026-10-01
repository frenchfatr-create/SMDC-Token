import logging
from io import BytesIO

from aiogram.types import BufferedInputFile
from PIL import Image

from db.settings import get_setting


async def process_photo_with_watermark(bot, file_id: str):
    watermark_id = await get_setting("watermark_file_id", "")

    if not watermark_id:
        return file_id

    try:
        # Загружаем исходную фотографию
        original_info = await bot.get_file(file_id)

        original_data = BytesIO()

        await bot.download_file(
            original_info.file_path,
            destination=original_data,
        )

        # Загружаем водяной знак.
        # Это может быть:
        # - PNG
        # - JPG
        # - WEBP
        # - обычный статический Telegram-стикер
        watermark_info = await bot.get_file(watermark_id)

        watermark_data = BytesIO()

        await bot.download_file(
            watermark_info.file_path,
            destination=watermark_data,
        )

        # Открываем изображения через Pillow.
        # Telegram-статические стикеры обычно приходят как WEBP.
        base = Image.open(
            BytesIO(original_data.getvalue())
        ).convert("RGBA")

        mark = Image.open(
            BytesIO(watermark_data.getvalue())
        ).convert("RGBA")

        if mark.width <= 0 or mark.height <= 0:
            return file_id

        # Размер водяного знака —
        # примерно 28% ширины исходной фотографии.
        target_width = max(
            1,
            int(base.width * 0.28),
        )

        target_height = max(
            1,
            int(
                mark.height
                * target_width
                / mark.width
            ),
        )

        mark.thumbnail(
            (target_width, target_height),
            Image.Resampling.LANCZOS,
        )

        # Делаем водяной знак полупрозрачным.
        alpha = mark.getchannel("A").point(
            lambda value: int(value * 0.55)
        )

        mark.putalpha(alpha)

        # Отступ от краёв.
        margin = max(
            10,
            int(base.width * 0.025),
        )

        position = (
            base.width
            - mark.width
            - margin,

            base.height
            - mark.height
            - margin,
        )

        base.alpha_composite(
            mark,
            position,
        )

        # Telegram дальше получает обычный JPEG.
        output = BytesIO()

        base.convert("RGB").save(
            output,
            format="JPEG",
            quality=92,
        )

        return BufferedInputFile(
            output.getvalue(),
            filename="watermarked.jpg",
        )

    except Exception:
        logging.exception(
            "Ошибка обработки водяного знака"
        )

        # Если обработка не удалась,
        # возвращаем исходный file_id.
        return file_id