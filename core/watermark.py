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
        original_info = await bot.get_file(file_id)
        original_data = BytesIO()
        await bot.download_file(original_info.file_path, destination=original_data)

        watermark_info = await bot.get_file(watermark_id)
        watermark_data = BytesIO()
        await bot.download_file(watermark_info.file_path, destination=watermark_data)

        base = Image.open(BytesIO(original_data.getvalue())).convert("RGBA")
        mark = Image.open(BytesIO(watermark_data.getvalue())).convert("RGBA")

        target_width = max(1, int(base.width * 0.28))
        target_height = max(1, int(mark.height * target_width / mark.width))
        mark.thumbnail((target_width, target_height), Image.Resampling.LANCZOS)

        alpha = mark.getchannel("A").point(lambda v: int(v * 0.55))
        mark.putalpha(alpha)

        margin = max(10, int(base.width * 0.025))
        position = (
            base.width - mark.width - margin,
            base.height - mark.height - margin,
        )
        base.alpha_composite(mark, position)

        output = BytesIO()
        base.convert("RGB").save(output, format="JPEG", quality=92)

        return BufferedInputFile(output.getvalue(), filename="watermarked.jpg")

    except Exception:
        logging.exception("Ошибка обработки водяного знака")
        return file_id
