from pathlib import Path

from PIL import Image


project_root = Path(__file__).resolve().parent.parent

source = (
    project_root
    / "desktop"
    / "assets"
    / "Main.jpg"
)

destination = (
    project_root
    / "desktop"
    / "assets"
    / "RecipeBook.ico"
)

with Image.open(source) as image:
    image = image.convert("RGBA")
    image.thumbnail((240, 240))

    icon = Image.new(
        "RGBA",
        (256, 256),
        (247, 241, 229, 255),
    )

    position = (
        (256 - image.width) // 2,
        (256 - image.height) // 2,
    )

    icon.paste(
        image,
        position,
        image,
    )

    icon.save(
        destination,
        format="ICO",
        sizes=[
            (16, 16),
            (24, 24),
            (32, 32),
            (48, 48),
            (64, 64),
            (128, 128),
            (256, 256),
        ],
    )

print(destination)