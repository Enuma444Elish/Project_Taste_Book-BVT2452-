from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Callable


class RecipeEditorWindow(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        recipe: dict | None,
        categories: list[dict],
        ingredients: list[dict],
        on_submit: Callable,
    ) -> None:
        super().__init__(parent)

        self.recipe = recipe
        self.categories = categories
        self.ingredients = ingredients
        self.on_submit = on_submit

        self.selected_ingredients: dict[int, dict] = {}

        self.title_var = tk.StringVar()
        self.servings_var = tk.StringVar(value="1")
        self.time_var = tk.StringVar()
        self.calories_var = tk.StringVar(value="0")
        self.photo_path_var = tk.StringVar()
        self.remove_photo_var = tk.BooleanVar(value=False)

        self.ingredient_var = tk.StringVar()
        self.amount_var = tk.StringVar()
        self.unit_var = tk.StringVar()

        self.title(
            "Изменение рецепта"
            if recipe
            else "Добавление рецепта"
        )
        self.geometry("900x720")
        self.minsize(800, 650)
        self.transient(parent)

        self.create_widgets()
        self.fill_existing_recipe()

    def create_widgets(self) -> None:
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        notebook = ttk.Notebook(self)
        notebook.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=12,
            pady=12,
        )

        self.create_main_tab(notebook)
        self.create_ingredients_tab(notebook)
        self.create_steps_tab(notebook)

        buttons = ttk.Frame(self, padding=(12, 0, 12, 12))
        buttons.grid(row=1, column=0, sticky="ew")

        ttk.Button(
            buttons,
            text="Отмена",
            command=self.destroy,
        ).pack(side="right")

        ttk.Button(
            buttons,
            text="Сохранить",
            command=self.submit,
        ).pack(side="right", padx=(0, 8))

    def create_main_tab(
        self,
        notebook: ttk.Notebook,
    ) -> None:
        frame = ttk.Frame(notebook, padding=15)
        notebook.add(frame, text="Основное")

        frame.grid_columnconfigure(1, weight=1)

        ttk.Label(frame, text="Название:").grid(
            row=0, column=0, sticky="w", pady=4
        )
        ttk.Entry(
            frame,
            textvariable=self.title_var,
        ).grid(
            row=0,
            column=1,
            sticky="ew",
            pady=4,
        )

        ttk.Label(frame, text="Описание:").grid(
            row=1, column=0, sticky="nw", pady=4
        )

        self.description_text = tk.Text(
            frame,
            height=8,
            wrap="word",
            font=("Segoe UI", 10),
        )
        self.description_text.grid(
            row=1,
            column=1,
            sticky="ew",
            pady=4,
        )

        ttk.Label(frame, text="Количество порций:").grid(
            row=2, column=0, sticky="w", pady=4
        )
        ttk.Entry(
            frame,
            textvariable=self.servings_var,
        ).grid(
            row=2, column=1, sticky="ew", pady=4
        )

        ttk.Label(frame, text="Время, минут:").grid(
            row=3, column=0, sticky="w", pady=4
        )
        ttk.Entry(
            frame,
            textvariable=self.time_var,
        ).grid(
            row=3, column=1, sticky="ew", pady=4
        )

        ttk.Label(frame, text="Ккал на порцию:").grid(
            row=4, column=0, sticky="w", pady=4
        )
        ttk.Entry(
            frame,
            textvariable=self.calories_var,
        ).grid(
            row=4, column=1, sticky="ew", pady=4
        )

        ttk.Label(frame, text="Категории:").grid(
            row=5, column=0, sticky="nw", pady=4
        )

        self.category_listbox = tk.Listbox(
            frame,
            selectmode=tk.EXTENDED,
            exportselection=False,
            height=8,
        )
        self.category_listbox.grid(
            row=5,
            column=1,
            sticky="ew",
            pady=4,
        )

        for category in self.categories:
            self.category_listbox.insert(
                tk.END,
                category["name"],
            )

        ttk.Label(frame, text="Новая фотография:").grid(
            row=6, column=0, sticky="w", pady=4
        )

        photo_frame = ttk.Frame(frame)
        photo_frame.grid(
            row=6,
            column=1,
            sticky="ew",
            pady=4,
        )
        photo_frame.grid_columnconfigure(0, weight=1)

        ttk.Entry(
            photo_frame,
            textvariable=self.photo_path_var,
            state="readonly",
        ).grid(
            row=0,
            column=0,
            sticky="ew",
        )

        ttk.Button(
            photo_frame,
            text="Выбрать JPG",
            command=self.select_photo,
        ).grid(
            row=0,
            column=1,
            padx=(6, 0),
        )

        ttk.Checkbutton(
            frame,
            text="Удалить текущую фотографию",
            variable=self.remove_photo_var,
        ).grid(
            row=7,
            column=1,
            sticky="w",
            pady=4,
        )

    def create_ingredients_tab(
        self,
        notebook: ttk.Notebook,
    ) -> None:
        frame = ttk.Frame(notebook, padding=12)
        notebook.add(frame, text="Ингредиенты")

        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        controls = ttk.Frame(frame)
        controls.grid(row=0, column=0, sticky="ew")
        controls.grid_columnconfigure(0, weight=1)

        ingredient_names = [
            item["name"]
            for item in self.ingredients
        ]

        ttk.Combobox(
            controls,
            textvariable=self.ingredient_var,
            values=ingredient_names,
            state="readonly",
        ).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(0, 5),
        )

        ttk.Entry(
            controls,
            textvariable=self.amount_var,
            width=12,
        ).grid(row=0, column=1, padx=5)

        ttk.Entry(
            controls,
            textvariable=self.unit_var,
            width=12,
        ).grid(row=0, column=2, padx=5)

        ttk.Button(
            controls,
            text="Добавить/изменить",
            command=self.add_ingredient,
        ).grid(row=0, column=3, padx=(5, 0))

        columns = ("name", "amount", "unit")

        self.ingredients_tree = ttk.Treeview(
            frame,
            columns=columns,
            show="headings",
        )
        self.ingredients_tree.grid(
            row=1,
            column=0,
            sticky="nsew",
            pady=(10, 5),
        )

        for column, title in (
            ("name", "Ингредиент"),
            ("amount", "Количество"),
            ("unit", "Единица"),
        ):
            self.ingredients_tree.heading(
                column,
                text=title,
            )

        self.ingredients_tree.bind(
            "<<TreeviewSelect>>",
            self.ingredient_selected,
        )

        ttk.Button(
            frame,
            text="Удалить выбранный ингредиент",
            command=self.remove_ingredient,
        ).grid(
            row=2,
            column=0,
            sticky="e",
        )

        if ingredient_names:
            self.ingredient_var.set(
                ingredient_names[0]
            )

    def create_steps_tab(
        self,
        notebook: ttk.Notebook,
    ) -> None:
        frame = ttk.Frame(notebook, padding=12)
        notebook.add(frame, text="Этапы приготовления")

        ttk.Label(
            frame,
            text=(
                "Введите каждый этап с новой строки. "
                "Нумерация будет создана автоматически."
            ),
        ).pack(anchor="w", pady=(0, 8))

        self.steps_text = tk.Text(
            frame,
            wrap="word",
            font=("Segoe UI", 11),
        )
        self.steps_text.pack(
            fill="both",
            expand=True,
        )

    def fill_existing_recipe(self) -> None:
        if not self.recipe:
            return

        self.title_var.set(self.recipe["title"])
        self.servings_var.set(
            str(self.recipe["base_servings"])
        )
        self.time_var.set(
            str(self.recipe["total_time_minutes"])
        )
        self.calories_var.set(
            str(self.recipe["calories_per_serving"])
        )

        self.description_text.insert(
            "1.0",
            self.recipe.get("description") or "",
        )

        selected_category_ids = {
            item["id"]
            for item in self.recipe["categories"]
        }

        for index, category in enumerate(self.categories):
            if category["id"] in selected_category_ids:
                self.category_listbox.selection_set(index)

        ingredient_names = {
            item["id"]: item["name"]
            for item in self.ingredients
        }

        for item in self.recipe[
            "ingredients_with_amounts"
        ]:
            ingredient_id = item["ingredient_id"]

            self.selected_ingredients[ingredient_id] = {
                "ingredient_id": ingredient_id,
                "amount": float(item["amount"]),
                "unit": item["unit"],
            }

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

        for step in self.recipe["cooking_steps"]:
            self.steps_text.insert(
                tk.END,
                f"{step['description']}\n",
            )

    def select_photo(self) -> None:
        filename = filedialog.askopenfilename(
            parent=self,
            title="Выберите фотографию",
            filetypes=[
                ("JPEG", "*.jpg *.jpeg"),
            ],
        )

        if filename:
            self.photo_path_var.set(filename)
            self.remove_photo_var.set(False)

    def add_ingredient(self) -> None:
        ingredient_name = self.ingredient_var.get()

        ingredient = next(
            (
                item
                for item in self.ingredients
                if item["name"] == ingredient_name
            ),
            None,
        )

        if ingredient is None:
            messagebox.showwarning(
                "Ингредиент",
                "Выберите ингредиент.",
                parent=self,
            )
            return

        try:
            amount = float(
                self.amount_var.get()
                .strip()
                .replace(",", ".")
            )
        except ValueError:
            messagebox.showwarning(
                "Количество",
                "Введите числовое количество.",
                parent=self,
            )
            return

        unit = self.unit_var.get().strip()

        if amount <= 0 or not unit:
            messagebox.showwarning(
                "Ингредиент",
                "Количество должно быть больше нуля, "
                "а единица измерения заполнена.",
                parent=self,
            )
            return

        ingredient_id = ingredient["id"]

        self.selected_ingredients[ingredient_id] = {
            "ingredient_id": ingredient_id,
            "amount": amount,
            "unit": unit,
        }

        values = (
            ingredient["name"],
            self.format_amount(amount),
            unit,
        )

        if self.ingredients_tree.exists(
            str(ingredient_id)
        ):
            self.ingredients_tree.item(
                str(ingredient_id),
                values=values,
            )
        else:
            self.ingredients_tree.insert(
                "",
                tk.END,
                iid=str(ingredient_id),
                values=values,
            )

    def ingredient_selected(
        self,
        event: tk.Event | None = None,
    ) -> None:
        selected = self.ingredients_tree.selection()

        if not selected:
            return

        ingredient_id = int(selected[0])
        item = self.selected_ingredients[ingredient_id]

        ingredient = next(
            item
            for item in self.ingredients
            if item["id"] == ingredient_id
        )

        self.ingredient_var.set(ingredient["name"])
        self.amount_var.set(
            self.format_amount(item["amount"])
        )
        self.unit_var.set(item["unit"])

    def remove_ingredient(self) -> None:
        selected = self.ingredients_tree.selection()

        if not selected:
            return

        ingredient_id = int(selected[0])

        self.selected_ingredients.pop(
            ingredient_id,
            None,
        )
        self.ingredients_tree.delete(selected[0])

    def submit(self) -> None:
        try:
            payload = self.build_payload()
        except ValueError as error:
            messagebox.showwarning(
                "Проверка данных",
                str(error),
                parent=self,
            )
            return

        image_path = (
            self.photo_path_var.get().strip()
            or None
        )

        if image_path:
            path = Path(image_path)

            if (
                not path.is_file()
                or path.suffix.lower()
                not in {".jpg", ".jpeg"}
            ):
                messagebox.showwarning(
                    "Фотография",
                    "Выберите существующий JPG-файл.",
                    parent=self,
                )
                return

        self.on_submit(
            self,
            self.recipe["id"] if self.recipe else None,
            payload,
            image_path,
            self.remove_photo_var.get(),
        )

    def build_payload(self) -> dict:
        title = self.title_var.get().strip()

        if not title:
            raise ValueError("Введите название рецепта.")

        try:
            servings = int(self.servings_var.get())
            cooking_time = int(self.time_var.get())
            calories = float(
                self.calories_var.get().replace(",", ".")
            )
        except ValueError:
            raise ValueError(
                "Порции и время должны быть целыми числами, "
                "а калорийность — числом."
            )

        if servings <= 0 or cooking_time <= 0:
            raise ValueError(
                "Количество порций и время должны быть больше нуля."
            )

        if calories < 0:
            raise ValueError(
                "Калорийность не может быть отрицательной."
            )

        category_ids = [
            self.categories[index]["id"]
            for index in self.category_listbox.curselection()
        ]

        if not category_ids:
            raise ValueError(
                "Выберите хотя бы одну категорию."
            )

        if not self.selected_ingredients:
            raise ValueError(
                "Добавьте хотя бы один ингредиент."
            )

        step_descriptions = [
            line.strip()
            for line in self.steps_text.get(
                "1.0",
                tk.END,
            ).splitlines()
            if line.strip()
        ]

        if not step_descriptions:
            raise ValueError(
                "Добавьте хотя бы один этап приготовления."
            )

        return {
            "title": title,
            "description": (
                self.description_text.get(
                    "1.0",
                    tk.END,
                ).strip()
                or None
            ),
            "base_servings": servings,
            "total_time_minutes": cooking_time,
            "calories_per_serving": calories,
            "category_ids": category_ids,
            "ingredients_with_amounts": list(
                self.selected_ingredients.values()
            ),
            "cooking_steps": [
                {
                    "number": index,
                    "description": description,
                }
                for index, description in enumerate(
                    step_descriptions,
                    start=1,
                )
            ],
        }

    @staticmethod
    def format_amount(value: float) -> str:
        number = float(value)

        if number.is_integer():
            return str(int(number))

        return f"{number:.3f}".rstrip("0").rstrip(".")