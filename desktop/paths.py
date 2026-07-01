from pathlib import Path
import sys


def get_application_root() -> Path:
    if getattr(sys, "frozen", False):
        # Каталог, в котором находится RecipeBook.exe.
        return Path(sys.executable).resolve().parent

    # Корень проекта при запуске через Python.
    return Path(__file__).resolve().parent.parent