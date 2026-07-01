import logging
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageOps, UnidentifiedImageError


logger = logging.getLogger(__name__)

RECIPES_MEDIA_DIRECTORY = Path("media") / "recipes"

MAX_IMAGE_FILE_SIZE = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 30_000_000
MAX_IMAGE_WIDTH = 1600
MAX_IMAGE_HEIGHT = 1200

RECIPES_MEDIA_DIRECTORY.mkdir(
    parents=True,
    exist_ok=True,
)


class ImageValidationError(ValueError):
    pass


class ImageTooLargeError(ImageValidationError):
    pass


def save_recipe_image(
    content: bytes,
    recipe_id: int,
) -> str:
    if not content:
        raise ImageValidationError("Загружен пустой файл")

    if len(content) > MAX_IMAGE_FILE_SIZE:
        raise ImageTooLargeError(
            "Размер фотографии не должен превышать 10 МБ"
        )

    try:
        with Image.open(BytesIO(content)) as image:
            if image.format != "JPEG":
                raise ImageValidationError(
                    "Поддерживаются только изображения JPG/JPEG"
                )

            if image.width * image.height > MAX_IMAGE_PIXELS:
                raise ImageTooLargeError(
                    "Разрешение фотографии слишком большое"
                )

            image.verify()

        # После verify() изображение необходимо открыть заново.
        with Image.open(BytesIO(content)) as image:
            image = ImageOps.exif_transpose(image)
            image = image.convert("RGB")

            image.thumbnail(
                (MAX_IMAGE_WIDTH, MAX_IMAGE_HEIGHT),
                Image.Resampling.LANCZOS,
            )

            filename = (
                f"{recipe_id}_{uuid4().hex}.jpg"
            )

            destination = (
                RECIPES_MEDIA_DIRECTORY / filename
            )

            image.save(
                destination,
                format="JPEG",
                quality=88,
                optimize=True,
            )

    except ImageValidationError:
        raise
    except Image.DecompressionBombError as error:
        raise ImageTooLargeError(
            "Разрешение фотографии слишком большое"
        ) from error
    except (UnidentifiedImageError, OSError, SyntaxError) as error:
        raise ImageValidationError(
            "Файл повреждён или не является изображением"
        ) from error

    return f"/media/recipes/{filename}"


def delete_recipe_image(
    image_path: str | None,
) -> None:
    if not image_path:
        return

    # Берём только имя файла, исключая переход в другие каталоги.
    filename = Path(image_path).name
    destination = RECIPES_MEDIA_DIRECTORY / filename

    try:
        destination.unlink(missing_ok=True)
    except OSError:
        logger.exception(
            "Не удалось удалить фотографию %s",
            destination,
        )