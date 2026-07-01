from pathlib import Path
import ctypes
import subprocess
import sys


def show_error(message: str) -> None:
    ctypes.windll.user32.MessageBoxW(
        0,
        message,
        "Книга рецептов",
        0x10,
    )


def get_application_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    return Path(__file__).resolve().parent


def main() -> None:
    project_root = get_application_root()
    start_script = project_root / "Start.bat"

    if not start_script.is_file():
        show_error(
            "Файл Start.bat не найден рядом "
            "с RecipeBookLauncher.exe."
        )
        return

    try:
        subprocess.Popen(
            [
                "cmd.exe",
                "/c",
                str(start_script),
            ],
            cwd=project_root,
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )
    except OSError as error:
        show_error(
            f"Не удалось запустить приложение:\n{error}"
        )


if __name__ == "__main__":
    main()