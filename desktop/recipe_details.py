from io import BytesIO
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable

from PIL import Image, ImageOps, ImageTk

from desktop.api_client import APIClient


BackgroundRunner = Callable[
    [Callable[[], Any], Callable[[Any], None]],
    None,
]


class RecipeDetailsWindow(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        api_client: APIClient,
        recipe: dict,
        image_content: bytes | None,
        run_background: BackgroundRunner,
    ) -> None:
        super().__init__(parent)

        self.api_client = api_client
        self.recipe = recipe
        self.run_background = run_background
        self.original_photo: Image.Image | None = None
        self.photo_image: ImageTk.PhotoImage | None = None

        self.servings_var = tk.StringVar(
            value=str(recipe["base_servings"])
        )

        self.calories_var = tk.StringVar()

        self.title(recipe["title"])
        self.geometry("1150x820")
        self.minsize(980, 720)

        self.transient(parent)

        self.create_widgets()
        self.fill_recipe_data()
        self.display_photo(image_content)

    def create_widgets(self) -> None:
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.create_header()
        self.create_content()

    def create_header(self) -> None:
        header = ttk.Frame(
            self,
            padding=(15, 12),
        )
        header.grid(
            row=0,
            column=0,
            sticky="ew",
        )

        header.grid_columnconfigure(0, weight=1)

        ttk.Label(
            header,
            text=self.recipe["title"],
            font=("Segoe UI", 22, "bold"),
        ).grid(
            row=0,
            column=0,
            sticky="w",
        )

        category_names = ", ".join(
            category["name"]
            for category in self.recipe["categories"]
        )

        metadata = (
            f"Категории: {category_names or 'не указаны'}  •  "
            f"Время: {self.recipe['total_time_minutes']} мин.  •  "
            f"Порций: {self.recipe['base_servings']}"
        )

        ttk.Label(
            header,
            text=metadata,
            font=("Segoe UI", 10),
        ).grid(
            row=1,
            column=0,
            sticky="w",
            pady=(4, 0),
        )

    def create_content(self) -> None:
        container = ttk.Panedwindow(
            self,
            orient=tk.HORIZONTAL,
        )
        container.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=12,
            pady=(0, 12),
        )

        left_panel = ttk.Frame(container)
        right_panel = ttk.Frame(container)

        container.add(
            left_panel,
            weight=1,
        )
        container.add(
            right_panel,
            weight=1,
        )

        self.create_photo_panel(left_panel)
        self.create_calculator_panel(left_panel)
        self.create_ingredients_panel(left_panel)

        self.create_description_panel(right_panel)
        self.create_steps_panel(right_panel)

    def create_photo_panel(
        self,
        parent: ttk.Frame,
    ) -> None:
        photo_frame = ttk.LabelFrame(
            parent,
            text="Фотография",
            padding=8,
            height=320,
        )
        photo_frame.pack(
            fill="x",
            pady=(0, 8),
        )

        # Не даём другим элементам уменьшить область фотографии.
        photo_frame.pack_propagate(False)

        self.photo_canvas = tk.Canvas(
            photo_frame,
            width=460,
            height=290,
            background="#EFE4D2",
            highlightthickness=0,
        )
        self.photo_canvas.pack(
            fill="both",
            expand=True,
        )

        self.photo_canvas.bind(
            "<Configure>",
            self.resize_photo,
        )

    def create_calculator_panel(
        self,
        parent: ttk.Frame,
    ) -> None:
        frame = ttk.LabelFrame(
            parent,
            text="Калькулятор порций",
            padding=10,
        )
        frame.pack(
            fill="x",
            pady=(0, 8),
        )

        frame.grid_columnconfigure(1, weight=1)

        ttk.Label(
            frame,
            text="Количество порций:",
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 8),
        )

        ttk.Spinbox(
            frame,
            from_=1,
            to=1000,
            textvariable=self.servings_var,
            width=10,
        ).grid(
            row=0,
            column=1,
            sticky="w",
        )

        ttk.Button(
            frame,
            text="Пересчитать",
            command=self.calculate_servings,
        ).grid(
            row=0,
            column=2,
            padx=(8, 0),
        )

        ttk.Label(
            frame,
            textvariable=self.calories_var,
            font=("Segoe UI", 10, "bold"),
        ).grid(
            row=1,
            column=0,
            columnspan=3,
            sticky="w",
            pady=(8, 0),
        )

    def create_ingredients_panel(
        self,
        parent: ttk.Frame,
    ) -> None:
        frame = ttk.LabelFrame(
            parent,
            text="Ингредиенты",
            padding=8,
        )
        frame.pack(
            fill="both",
            expand=True,
        )

        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        columns = (
            "name",
            "amount",
            "unit",
        )

        self.ingredients_tree = ttk.Treeview(
            frame,
            columns=columns,
            show="headings",
            height=10,
        )

        self.ingredients_tree.heading(
            "name",
            text="Ингредиент",
        )
        self.ingredients_tree.heading(
            "amount",
            text="Количество",
        )
        self.ingredients_tree.heading(
            "unit",
            text="Единица",
        )

        self.ingredients_tree.column(
            "name",
            width=230,
        )
        self.ingredients_tree.column(
            "amount",
            width=100,
            anchor="center",
        )
        self.ingredients_tree.column(
            "unit",
            width=90,
            anchor="center",
        )

        self.ingredients_tree.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

        scrollbar = ttk.Scrollbar(
            frame,
            orient="vertical",
            command=self.ingredients_tree.yview,
        )
        scrollbar.grid(
            row=0,
            column=1,
            sticky="ns",
        )

        self.ingredients_tree.configure(
            yscrollcommand=scrollbar.set
        )

    def create_description_panel(
        self,
        parent: ttk.Frame,
    ) -> None:
        frame = ttk.LabelFrame(
            parent,
            text="Описание",
            padding=8,
        )
        frame.pack(
            fill="x",
            pady=(0, 8),
        )

        self.description_text = tk.Text(
            frame,
            height=7,
            wrap="word",
            font=("Segoe UI", 11),
            relief="flat",
            background="#FFFDF8",
            foreground="#3F342C",
        )
        self.description_text.pack(
            fill="both",
            expand=True,
        )

    def create_steps_panel(
        self,
        parent: ttk.Frame,
    ) -> None:
        frame = ttk.LabelFrame(
            parent,
            text="Этапы приготовления",
            padding=8,
        )
        frame.pack(
            fill="both",
            expand=True,
        )

        self.steps_text = tk.Text(
            frame,
            wrap="word",
            font=("Segoe UI", 11),
            padx=8,
            pady=8,
        )
        self.steps_text.pack(
            side="left",
            fill="both",
            expand=True,
        )

        scrollbar = ttk.Scrollbar(
            frame,
            orient="vertical",
            command=self.steps_text.yview,
        )
        scrollbar.pack(
            side="right",
            fill="y",
        )

        self.steps_text.configure(
            yscrollcommand=scrollbar.set
        )

    def fill_recipe_data(self) -> None:
        description = (
            self.recipe.get("description")
            or "Описание отсутствует."
        )

        self.description_text.insert(
            "1.0",
            description,
        )
        self.description_text.configure(
            state="disabled"
        )

        steps = sorted(
            self.recipe["cooking_steps"],
            key=lambda item: item["number"],
        )

        for step in steps:
            self.steps_text.insert(
                tk.END,
                f"Шаг {step['number']}\n",
                "step_title",
            )
            self.steps_text.insert(
                tk.END,
                f"{step['description']}\n\n",
            )

        self.steps_text.tag_configure(
            "step_title",
            font=("Segoe UI", 11, "bold"),
        )
        self.steps_text.configure(
            state="disabled"
        )

        ingredient_names = {
            ingredient["id"]: ingredient["name"]
            for ingredient in self.recipe["ingredients"]
        }

        for item in self.recipe[
            "ingredients_with_amounts"
        ]:
            ingredient_id = item["ingredient_id"]

            self.ingredients_tree.insert(
                "",
                tk.END,
                iid=str(ingredient_id),
                values=(
                    ingredient_names.get(
                        ingredient_id,
                        "Неизвестный ингредиент",
                    ),
                    self.format_amount(item["amount"]),
                    item["unit"],
                ),
            )

        calories = float(
            self.recipe["calories_per_serving"]
        )
        servings = self.recipe["base_servings"]

        self.calories_var.set(
            f"{calories:.0f} ккал на порцию; "
            f"всего: {calories * servings:.0f} ккал"
        )

    def display_photo(
        self,
        image_content: bytes | None,
    ) -> None:
        if not image_content:
            self.show_photo_placeholder(
                "Фотография отсутствует"
            )
            return

        try:
            with Image.open(
                BytesIO(image_content)
            ) as image:
                image = ImageOps.exif_transpose(image)
                image = image.convert("RGB")

                # copy() нужен, поскольку Image.open используется
                # внутри контекстного менеджера.
                self.original_photo = image.copy()

        except (OSError, ValueError):
            self.original_photo = None
            self.show_photo_placeholder(
                "Не удалось открыть фотографию"
            )
            return

        self.after_idle(self.resize_photo)

    def resize_photo(
        self,
        event: tk.Event | None = None,
    ) -> None:
        if self.original_photo is None:
            return

        canvas_width = max(
            self.photo_canvas.winfo_width() - 16,
            1,
        )
        canvas_height = max(
            self.photo_canvas.winfo_height() - 16,
            1,
        )

        # contain вписывает изображение полностью.
        # Части фотографии не обрезаются.
        resized_image = ImageOps.contain(
            self.original_photo,
            (canvas_width, canvas_height),
            method=Image.Resampling.LANCZOS,
        )

        self.photo_image = ImageTk.PhotoImage(
            resized_image
        )

        self.photo_canvas.delete("all")

        self.photo_canvas.create_image(
            canvas_width // 2 + 8,
            canvas_height // 2 + 8,
            image=self.photo_image,
            anchor="center",
        )

    def show_photo_placeholder(
        self,
        message: str,
    ) -> None:
        self.photo_canvas.delete("all")

        width = max(
            self.photo_canvas.winfo_width(),
            460,
        )
        height = max(
            self.photo_canvas.winfo_height(),
            290,
        )

        self.photo_canvas.create_text(
            width // 2,
            height // 2,
            text=message,
            fill="#555555",
            font=("Segoe UI", 11),
            anchor="center",
        )

    def calculate_servings(self) -> None:
        value = self.servings_var.get().strip()

        try:
            servings = int(value)
        except ValueError:
            messagebox.showwarning(
                "Некорректное количество",
                "Количество порций должно быть целым числом.",
                parent=self,
            )
            return

        if not 1 <= servings <= 1000:
            messagebox.showwarning(
                "Некорректное количество",
                "Введите количество порций от 1 до 1000.",
                parent=self,
            )
            return

        recipe_id = self.recipe["id"]

        self.run_background(
            lambda: self.api_client.calculate_recipe(
                recipe_id,
                servings,
            ),
            self.calculation_loaded,
        )

    def calculation_loaded(
        self,
        calculation: dict,
    ) -> None:
        if not self.winfo_exists():
            return

        for ingredient in calculation["ingredients"]:
            ingredient_id = str(
                ingredient["ingredient_id"]
            )

            if self.ingredients_tree.exists(
                ingredient_id
            ):
                self.ingredients_tree.item(
                    ingredient_id,
                    values=(
                        ingredient["name"],
                        self.format_amount(
                            ingredient[
                                "calculated_amount"
                            ]
                        ),
                        ingredient["unit"],
                    ),
                )

        self.calories_var.set(
            f"{calculation['calories_per_serving']:.0f} "
            f"ккал на порцию; всего: "
            f"{calculation['total_calories']:.0f} ккал"
        )

    @staticmethod
    def format_amount(value: int | float) -> str:
        number = float(value)

        if number.is_integer():
            return str(int(number))

        return (
            f"{number:.3f}"
            .rstrip("0")
            .rstrip(".")
        )