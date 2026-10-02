import io
import os
import tempfile
import logging

from PIL import Image


logger = logging.getLogger(__name__)


# =========================================================
# НАСТРОЙКИ
# =========================================================

WATERMARK_OPACITY = 150
WATERMARK_MARGIN = 20


# =========================================================
# ВСПОМОГАТЕЛЬНОЕ
# =========================================================

def _open_image(data: bytes):
    image = Image.open(io.BytesIO(data))

    # Нужен RGBA для нормальной прозрачности.
    return image.convert("RGBA")


def _prepare_watermark(
    watermark_data: bytes,
    max_width: int,
    max_height: int,
):
    """
    Загружает водяной знак и подгоняет его размер.
    Поддерживает PNG/WebP/JPEG и другие форматы,
    которые умеет Pillow.
    """

    watermark = _open_image(watermark_data)

    # Если водяной знак огромный — уменьшаем.
    watermark.thumbnail(
        (max_width, max_height),
        Image.Resampling.LANCZOS,
    )

    # Настраиваем прозрачность.
    alpha = watermark.getchannel("A")

    alpha = alpha.point(
        lambda value: int(
            value * WATERMARK_OPACITY / 255
        )
    )

    watermark.putalpha(alpha)

    return watermark


def _center_position(
    base: Image.Image,
    watermark: Image.Image,
):
    x = (
        base.width - watermark.width
    ) // 2

    y = (
        base.height - watermark.height
    ) // 2

    return x, y


# =========================================================
# ВОДЯНОЙ ЗНАК НА ФОТО
# =========================================================

def add_watermark_to_image(
    image_data: bytes,
    watermark_data: bytes,
) -> bytes:
    """
    Накладывает водяной знак строго по центру изображения.

    Возвращает готовое изображение в JPEG.
    """

    base = _open_image(
        image_data
    )

    # Водяной знак занимает максимум
    # примерно 45% ширины и 25% высоты.
    watermark = _prepare_watermark(
        watermark_data,
        max_width=max(
            1,
            int(base.width * 0.45),
        ),
        max_height=max(
            1,
            int(base.height * 0.25),
        ),
    )

    x, y = _center_position(
        base,
        watermark,
    )

    base.alpha_composite(
        watermark,
        (x, y),
    )

    output = io.BytesIO()

    # Telegram нормально работает с JPEG.
    base.convert("RGB").save(
        output,
        format="JPEG",
        quality=95,
        optimize=True,
    )

    output.seek(0)

    return output.getvalue()


# =========================================================
# ВОДЯНОЙ ЗНАК НА ВИДЕО
# =========================================================

async def add_watermark_to_video(
    video_data: bytes,
    watermark_data: bytes,
) -> bytes:
    """
    Накладывает водяной знак по центру видео.

    Требует ffmpeg, установленный на BotHost.
    """

    video_file = None
    watermark_file = None
    output_file = None

    try:
        # ---------------------------------------------
        # Временные файлы
        # ---------------------------------------------

        with tempfile.NamedTemporaryFile(
            suffix=".mp4",
            delete=False,
        ) as f:
            f.write(video_data)
            video_file = f.name

        with tempfile.NamedTemporaryFile(
            suffix=".png",
            delete=False,
        ) as f:
            f.write(watermark_data)
            watermark_file = f.name

        output_file = tempfile.mktemp(
            suffix=".mp4"
        )

        # ---------------------------------------------
        # Размер водяного знака
        # ---------------------------------------------

        watermark_image = _open_image(
            watermark_data
        )

        # Для видео делаем watermark
        # умеренного размера.
        watermark_image.thumbnail(
            (700, 400),
            Image.Resampling.LANCZOS,
        )

        # Сохраняем подготовленный PNG.
        prepared_watermark = tempfile.mktemp(
            suffix=".png"
        )

        watermark_image.save(
            prepared_watermark,
            "PNG",
        )

        watermark_file = prepared_watermark

        # ---------------------------------------------
        # FFmpeg
        # ---------------------------------------------

        import asyncio
        import shutil

        ffmpeg = shutil.which(
            "ffmpeg"
        )

        if not ffmpeg:
            raise RuntimeError(
                "ffmpeg не найден в системе"
            )

        process = await asyncio.create_subprocess_exec(
            ffmpeg,
            "-y",

            "-i",
            video_file,

            "-i",
            watermark_file,

            "-filter_complex",
            (
                "[1:v]format=rgba,"
                "colorchannelmixer=aa=0.59[wm];"
                "[0:v][wm]"
                "overlay="
                "(main_w-overlay_w)/2:"
                "(main_h-overlay_h)/2:"
                "shortest=1"
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

            output_file,

            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            logger.error(
                "FFmpeg error: %s",
                stderr.decode(
                    "utf-8",
                    errors="ignore",
                )[-4000:],
            )

            raise RuntimeError(
                "FFmpeg не смог обработать видео"
            )

        # ---------------------------------------------
        # Результат
        # ---------------------------------------------

        with open(
            output_file,
            "rb",
        ) as f:
            result = f.read()

        return result

    finally:

        # ---------------------------------------------
        # Удаляем временные файлы
        # ---------------------------------------------

        for path in (
            video_file,
            watermark_file,
            output_file,
        ):

            if (
                path
                and os.path.exists(path)
            ):
                try:
                    os.remove(path)
                except Exception:
                    pass


# =========================================================
# УНИВЕРСАЛЬНАЯ ФУНКЦИЯ
# =========================================================

async def apply_watermark(
    media_type: str,
    media_data: bytes,
    watermark_data: bytes,
) -> bytes:
    """
    Универсальная функция.

    media_type:
        photo
        video
    """

    if media_type == "photo":

        return add_watermark_to_image(
            media_data,
            watermark_data,
        )

    if media_type == "video":

        return await add_watermark_to_video(
            media_data,
            watermark_data,
        )

    # Неизвестный тип — возвращаем
    # оригинальный файл.
    return media_data