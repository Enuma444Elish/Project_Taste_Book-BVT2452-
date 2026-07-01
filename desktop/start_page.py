from pathlib import Path
import sys
import tkinter as tk
from tkinter import ttk
from typing import Callable

from PIL import Image, ImageOps, ImageTk


def get_asset_path(filename: str) -> Path:
    # Путь при запуске обычного Python-проекта.
    if not hasattr(sys, "_MEIPASS"):
        return (
            Path(__file__).resolve().parent
            / "assets"
            / filename
        )

    # Путь после будущей сборки через PyInstaller.
    return (
        Path(sys._MEIPASS)
        / "desktop"
        / "assets"
        / filename
    )


class StartPage(ttk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        on_start: Callable[[], None],
    ) -> None:
        super().__init__(
            parent,
            padding=(30, 25),
        )

        self.on_start = on_start
        self.original_image: Image.Image | None = None
        self.photo_image: ImageTk.PhotoImage | None = None
        self.resize_job: str | None = None

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.create_widgets()
        self.load_image()

    def create_widgets(self) -> None:
        image_frame = ttk.Frame(self)
        image_frame.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

        image_frame.grid_rowconfigure(0, weight=1)
        image_frame.grid_columnconfigure(0, weight=1)

        self.image_canvas = tk.Canvas(
            image_frame,
            background="#F7F1E5",
            highlightbackground="#D9CBB9",
            highlightthickness=1,
        )
        self.image_canvas.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

        self.image_canvas.bind(
            "<Configure>",
            self.schedule_image_resize,
        )

        button_container = ttk.Frame(self)
        button_container.grid(
            row=1,
            column=0,
            pady=(20, 5),
        )

        self.start_button = ttk.Button(
            button_container,
            text="Начать",
            command=self.start_application,
            style="Start.TButton",
            cursor="hand2",
        )
        self.start_button.pack()

    def load_image(self) -> None:
        image_path = get_asset_path("Main.jpg")

        try:
            with Image.open(image_path) as image:
                image = ImageOps.exif_transpose(image)
                image = image.convert("RGB")
                self.original_image = image.copy()

        except OSError:
            self.original_image = None

            self.image_canvas.create_text(
                400,
                250,
                text=(
                    "Не удалось загрузить стартовое "
                    "изображение"
                ),
                fill="#76685E",
                font=("Segoe UI", 15),
            )
            return

        self.after_idle(self.render_image)

    def schedule_image_resize(
        self,
        event: tk.Event | None = None,
    ) -> None:
        if self.resize_job is not None:
            self.after_cancel(self.resize_job)

        # Небольшая задержка исключает постоянное
        # масштабирование во время изменения окна.
        self.resize_job = self.after(
            60,
            self.render_image,
        )

    def render_image(self) -> None:
        self.resize_job = None

        if self.original_image is None:
            return

        canvas_width = max(
            self.image_canvas.winfo_width() - 20,
            1,
        )
        canvas_height = max(
            self.image_canvas.winfo_height() - 20,
            1,
        )

        resized_image = ImageOps.contain(
            self.original_image,
            (canvas_width, canvas_height),
            method=Image.Resampling.LANCZOS,
        )

        self.photo_image = ImageTk.PhotoImage(
            resized_image
        )

        self.image_canvas.delete("all")

        canvas_center_x = (
            self.image_canvas.winfo_width() // 2
        )
        canvas_center_y = (
            self.image_canvas.winfo_height() // 2
        )

        self.image_canvas.create_image(
            canvas_center_x,
            canvas_center_y,
            image=self.photo_image,
            anchor="center",
        )

        displayed_width, displayed_height = (
            resized_image.size
        )

        image_top = (
            canvas_center_y
            - displayed_height // 2
        )

        # Заголовок располагается относительно
        # верхней границы отображаемой картинки.
        title_y = image_top + max(
            40,
            int(displayed_height * 0.075),
        )

        font_size = max(
            22,
            min(
                38,
                int(displayed_width * 0.032),
            ),
        )

        title_font = (
            "Georgia",
            font_size,
            "bold",
        )

        # Светлая тень улучшает читаемость.
        self.image_canvas.create_text(
            canvas_center_x + 2,
            title_y + 2,
            text="Книга рецептов",
            fill="#FFF4D6",
            font=title_font,
            anchor="center",
        )

        self.image_canvas.create_text(
            canvas_center_x,
            title_y,
            text="Книга рецептов",
            fill="#465C32",
            font=title_font,
            anchor="center",
        )

    def start_application(self) -> None:
        self.start_button.configure(
            state="disabled"
        )
        self.on_start()