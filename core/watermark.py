import logging
from io import BytesIO

from aiogram.types import BufferedInputFile
from PIL import Image

from db.settings import get_setting


# ============================================================
# НАСТРОЙКИ
# ============================================================

WATERMARK_OPACITY = 0.55

# Доля ширины фотографии,
# которую максимум может занимать watermark.
WATERMARK_WIDTH_RATIO = 0.80


# ============================================================
# ФОТО + WATERMARK
# ============================================================

async def process_photo_with_watermark(
    bot,
    file_id: str,
):
    """
    Старый интерфейс проекта:

        process_photo_with_watermark(bot, file_id)

    Возвращает:
        - BufferedInputFile с обработанным фото
        - либо исходный file_id, если watermark
          не установлен или обработка не удалась.

    Watermark ставится по центру фотографии.
    """

    watermark_id = await get_setting(
        "watermark_file_id",
        "",
    )

    # --------------------------------------------------------
    # Если watermark не установлен
    # --------------------------------------------------------

    if not watermark_id:
        return file_id

    try:
        # ====================================================
        # СКАЧИВАЕМ ОРИГИНАЛЬНОЕ ФОТО
        # ====================================================

        original_info = await bot.get_file(
            file_id
        )

        original_data = BytesIO()

        await bot.download_file(
            original_info.file_path,
            destination=original_data,
        )

        # ====================================================
        # СКАЧИВАЕМ WATERMARK
        # ====================================================

        watermark_info = await bot.get_file(
            watermark_id
        )

        watermark_data = BytesIO()

        await bot.download_file(
            watermark_info.file_path,
            destination=watermark_data,
        )

        # ====================================================
        # ОТКРЫВАЕМ ИЗОБРАЖЕНИЯ
        # ====================================================

        base = Image.open(
            BytesIO(
                original_data.getvalue()
            )
        ).convert("RGBA")

        mark = Image.open(
            BytesIO(
                watermark_data.getvalue()
            )
        ).convert("RGBA")

        # ====================================================
        # РАЗМЕР WATERMARK
        # ====================================================

        target_width = max(
            1,
            int(
                base.width
                * WATERMARK_WIDTH_RATIO
            ),
        )

        target_height = max(
            1,
            int(
                mark.height
                * target_width
                / max(
                    1,
                    mark.width,
                )
            ),
        )

        mark.thumbnail(
            (
                target_width,
                target_height,
            ),
            Image.Resampling.LANCZOS,
        )

        # ====================================================
        # ПРОЗРАЧНОСТЬ
        # ====================================================

        alpha = mark.getchannel(
            "A"
        )

        alpha = alpha.point(
            lambda value: int(
                value
                * WATERMARK_OPACITY
            )
        )

        mark.putalpha(
            alpha
        )

        # ====================================================
        # ЦЕНТР ФОТО
        # ====================================================

        x = (
            base.width
            - mark.width
        ) // 2

        y = (
            base.height
            - mark.height
        ) // 2

        # ====================================================
        # НАКЛАДЫВАЕМ WATERMARK
        # ====================================================

        base.alpha_composite(
            mark,
            (
                x,
                y,
            ),
        )

        # ====================================================
        # СОХРАНЯЕМ
        # ====================================================

        output = BytesIO()

        base.convert(
            "RGB"
        ).save(
            output,
            format="JPEG",
            quality=92,
            optimize=True,
        )

        return BufferedInputFile(
            output.getvalue(),
            filename="watermarked.jpg",
        )

    except Exception:
        logging.exception(
            "Ошибка обработки водяного знака"
        )

        # Очень важно:
        # если watermark не обработался,
        # публикация не должна ломаться.
        return file_id


# ============================================================
# ОБРАБОТКА BYTES
# ============================================================

def add_watermark_to_image(
    image_data: bytes,
    watermark_data: bytes,
) -> bytes:
    """
    Низкоуровневая функция.
    Принимает готовые bytes изображения
    и watermark.

    Возвращает JPEG bytes.
    """

    base = Image.open(
        BytesIO(image_data)
    ).convert("RGBA")

    mark = Image.open(
        BytesIO(watermark_data)
    ).convert("RGBA")

    # --------------------------------------------------------
    # Размер watermark
    # --------------------------------------------------------

    target_width = max(
        1,
        int(
            base.width
            * WATERMARK_WIDTH_RATIO
        ),
    )

    target_height = max(
        1,
        int(
            mark.height
            * target_width
            / max(
                1,
                mark.width,
            )
        ),
    )

    mark.thumbnail(
        (
            target_width,
            target_height,
        ),
        Image.Resampling.LANCZOS,
    )

    # --------------------------------------------------------
    # Прозрачность
    # --------------------------------------------------------

    alpha = mark.getchannel(
        "A"
    )

    alpha = alpha.point(
        lambda value: int(
            value
            * WATERMARK_OPACITY
        )
    )

    mark.putalpha(
        alpha
    )

    # --------------------------------------------------------
    # Центр
    # --------------------------------------------------------

    x = (
        base.width
        - mark.width
    ) // 2

    y = (
        base.height
        - mark.height
    ) // 2

    base.alpha_composite(
        mark,
        (
            x,
            y,
        ),
    )

    # --------------------------------------------------------
    # JPEG
    # --------------------------------------------------------

    output = BytesIO()

    base.convert(
        "RGB"
    ).save(
        output,
        format="JPEG",
        quality=92,
        optimize=True,
    )

    return output.getvalue()


# ============================================================
# СОВМЕСТИМОСТЬ СО СТАРЫМ КОДОМ
# ============================================================

def process_photo_bytes_with_watermark(
    image_data: bytes,
    watermark_data: bytes,
) -> bytes:
    """
    Обработка уже скачанных bytes.
    """

    return add_watermark_to_image(
        image_data,
        watermark_data,
    )


# ============================================================
# ВИДЕО
# ============================================================

async def process_video_with_watermark(
    bot,
    file_id: str,
):
    """
    Обработка видео с watermark.

    Используется отдельно от старого
    process_photo_with_watermark().

    Если ffmpeg недоступен или обработка не удалась,
    возвращается исходный file_id.
    """

    import os
    import shutil
    import tempfile
    import asyncio

    watermark_id = await get_setting(
        "watermark_file_id",
        "",
    )

    if not watermark_id:
        return file_id

    video_path = None
    watermark_path = None
    output_path = None

    try:
        # ----------------------------------------------------
        # Проверяем ffmpeg
        # ----------------------------------------------------

        ffmpeg = shutil.which(
            "ffmpeg"
        )

        if not ffmpeg:
            logging.warning(
                "ffmpeg не найден, видео публикуется без watermark"
            )
            return file_id

        # ----------------------------------------------------
        # Скачиваем видео
        # ----------------------------------------------------

        video_info = await bot.get_file(
            file_id
        )

        video_tmp = tempfile.NamedTemporaryFile(
            suffix=".mp4",
            delete=False,
        )

        video_path = video_tmp.name

        video_tmp.close()

        with open(
            video_path,
            "wb",
        ) as f:

            await bot.download_file(
                video_info.file_path,
                destination=f,
            )

        # ----------------------------------------------------
        # Скачиваем watermark
        # ----------------------------------------------------

        watermark_info = await bot.get_file(
            watermark_id
        )

        watermark_tmp = tempfile.NamedTemporaryFile(
            suffix=".png",
            delete=False,
        )

        watermark_path = watermark_tmp.name

        watermark_tmp.close()

        watermark_buffer = BytesIO()

        await bot.download_file(
            watermark_info.file_path,
            destination=watermark_buffer,
        )

        watermark_image = Image.open(
            BytesIO(
                watermark_buffer.getvalue()
            )
        ).convert("RGBA")

        watermark_image.save(
            watermark_path,
            format="PNG",
        )

        # ----------------------------------------------------
        # Выходной файл
        # ----------------------------------------------------

        output_path = tempfile.mktemp(
            suffix=".mp4"
        )

        # ----------------------------------------------------
        # FFmpeg
        # ----------------------------------------------------

        process = await asyncio.create_subprocess_exec(
            ffmpeg,

            "-y",

            "-i",
            video_path,

            "-i",
            watermark_path,

            "-filter_complex",
            (
                "[1:v]"
                "format=rgba,"
                "colorchannelmixer=aa=0.55"
                "[wm];"

                "[0:v][wm]"
                "overlay="
                "(main_w-overlay_w)/2:"
                "(main_h-overlay_h)/2"
            ),

            "-map",
            "0:v:0",

            "-map",
            "0:a?",

            "-c:v",
            "libx264",

            "-preset",
            "veryfast",

            "-crf",
            "23",

            "-c:a",
            "copy",

            "-movflags",
            "+faststart",

            output_path,

            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = (
            await process.communicate()
        )

        if process.returncode != 0:
            logging.error(
                "FFmpeg error: %s",
                stderr.decode(
                    "utf-8",
                    errors="ignore",
                )[-3000:],
            )

            return file_id

        # ----------------------------------------------------
        # Читаем результат
        # ----------------------------------------------------

        with open(
            output_path,
            "rb",
        ) as f:

            result = f.read()

        if not result:
            return file_id

        return BufferedInputFile(
            result,
            filename="watermarked.mp4",
        )

    except Exception:

        logging.exception(
            "Ошибка обработки видео с watermark"
        )

        return file_id

    finally:

        # ----------------------------------------------------
        # Удаляем временные файлы
        # ----------------------------------------------------

        for path in (
            video_path,
            watermark_path,
            output_path,
        ):

            if (
                path
                and os.path.exists(path)
            ):

                try:
                    os.remove(
                        path
                    )
                except Exception:
                    pass