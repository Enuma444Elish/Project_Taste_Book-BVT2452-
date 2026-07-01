import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable

from desktop.api_client import APIClient
from desktop.recipe_editor import RecipeEditorWindow

from desktop.backup_tab import BackupTab


class AdminWindow(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        api_client: APIClient,
        run_background: Callable,
        on_data_changed: Callable,
    ) -> None:
        super().__init__(parent)

        self.api_client = api_client
        self.run_background = run_background
        self.on_data_changed = on_data_changed

        self.categories: list[dict] = []
        self.ingredients: list[dict] = []
        self.recipes: list[dict] = []

        self.title("Управление базой рецептов")
        self.geometry("900x650")
        self.minsize(800, 550)
        self.transient(parent)

        notebook = ttk.Notebook(self)
        notebook.pack(
            fill="both",
            expand=True,
            padx=12,
            pady=12,
        )

        self.category_tab = CategoryTab(notebook, self)
        self.ingredient_tab = IngredientTab(notebook, self)
        self.recipe_tab = RecipeTab(notebook, self)
        self.backup_tab = BackupTab(
            notebook,
            self,
        )

        notebook.add(
            self.category_tab,
            text="Категории",
        )
        notebook.add(
            self.ingredient_tab,
            text="Ингредиенты",
        )
        notebook.add(
            self.recipe_tab,
            text="Рецепты",
        )
        notebook.add(
            self.backup_tab,
            text="Резервные копии",
        )

        self.status_var = tk.StringVar(
            value="Загрузка данных..."
        )

        ttk.Label(
            self,
            textvariable=self.status_var,
            relief="sunken",
            anchor="w",
            padding=5,
        ).pack(fill="x")

        self.after(100, self.refresh_all)
        self.after(
            150,
            self.backup_tab.refresh,
        )

    def refresh_all(self) -> None:
        self.status_var.set("Обновление данных...")

        def task() -> tuple:
            return (
                self.api_client.get_categories(),
                self.api_client.get_ingredients(),
                self.api_client.get_recipes(),
            )

        self.run_background(
            task,
            self.data_loaded,
        )

    def data_loaded(self, result: tuple) -> None:
        if not self.winfo_exists():
            return

        (
            self.categories,
            self.ingredients,
            self.recipes,
        ) = result

        self.category_tab.load(self.categories)
        self.ingredient_tab.load(self.ingredients)
        self.recipe_tab.load(self.recipes)

        self.status_var.set("Данные загружены")

    def perform_action(
        self,
        task: Callable[[], Any],
        success_message: str,
        after_success: Callable[[Any], None] | None = None,
    ) -> None:
        def completed(result: Any) -> None:
            if after_success:
                after_success(result)

            messagebox.showinfo(
                "Готово",
                success_message,
                parent=self,
            )

            self.refresh_all()
            self.on_data_changed()

        self.run_background(task, completed)

    def save_recipe(
        self,
        editor: RecipeEditorWindow,
        recipe_id: int | None,
        payload: dict,
        image_path: str | None,
        remove_image: bool,
    ) -> None:
        def task() -> dict:
            if recipe_id is None:
                recipe = self.api_client.create_recipe(
                    payload
                )
            else:
                recipe = self.api_client.update_recipe(
                    recipe_id,
                    payload,
                )

            saved_id = recipe["id"]

            if image_path:
                recipe = (
                    self.api_client.upload_recipe_image(
                        saved_id,
                        image_path,
                    )
                )
            elif remove_image and recipe_id is not None:
                self.api_client.delete_recipe_image(
                    saved_id
                )

            return recipe

        self.perform_action(
            task,
            "Рецепт сохранён.",
            after_success=lambda result: editor.destroy(),
        )


class CategoryTab(ttk.Frame):
    def __init__(
        self,
        parent: ttk.Notebook,
        admin: AdminWindow,
    ) -> None:
        super().__init__(parent, padding=12)

        self.admin = admin
        self.name_var = tk.StringVar()

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            self,
            columns=("id", "name"),
            show="headings",
        )
        self.tree.heading("id", text="ID")
        self.tree.heading("name", text="Название")
        self.tree.column("id", width=70)
        self.tree.grid(
            row=0,
            column=0,
            columnspan=3,
            sticky="nsew",
        )
        self.tree.bind(
            "<<TreeviewSelect>>",
            self.selected,
        )

        ttk.Entry(
            self,
            textvariable=self.name_var,
        ).grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(10, 0),
        )

        ttk.Button(
            self,
            text="Добавить",
            command=self.add,
        ).grid(row=1, column=1, padx=5, pady=(10, 0))

        ttk.Button(
            self,
            text="Изменить",
            command=self.update,
        ).grid(row=1, column=2, pady=(10, 0))

        ttk.Button(
            self,
            text="Удалить",
            command=self.delete,
            style="Danger.TButton",
        ).grid(row=2, column=2, pady=(8, 0))

    def load(self, items: list[dict]) -> None:
        self.tree.delete(*self.tree.get_children())

        for item in items:
            self.tree.insert(
                "",
                tk.END,
                iid=str(item["id"]),
                values=(item["id"], item["name"]),
            )

    def selected(self, event=None) -> None:
        selection = self.tree.selection()

        if selection:
            self.name_var.set(
                self.tree.item(
                    selection[0],
                    "values",
                )[1]
            )

    def selected_id(self) -> int | None:
        selection = self.tree.selection()
        return int(selection[0]) if selection else None

    def add(self) -> None:
        name = self.name_var.get().strip()

        if not name:
            return

        self.admin.perform_action(
            lambda: self.admin.api_client.create_category(name),
            "Категория добавлена.",
            lambda result: self.name_var.set(""),
        )

    def update(self) -> None:
        category_id = self.selected_id()
        name = self.name_var.get().strip()

        if category_id is None or not name:
            return

        self.admin.perform_action(
            lambda: self.admin.api_client.update_category(
                category_id,
                name,
            ),
            "Категория изменена.",
        )

    def delete(self) -> None:
        category_id = self.selected_id()

        if category_id is None:
            return

        if not messagebox.askyesno(
            "Удаление",
            "Удалить выбранную категорию?",
            parent=self,
        ):
            return

        self.admin.perform_action(
            lambda: self.admin.api_client.delete_category(
                category_id
            ),
            "Категория удалена.",
        )


class IngredientTab(CategoryTab):
    def __init__(
        self,
        parent: ttk.Notebook,
        admin: AdminWindow,
    ) -> None:
        ttk.Frame.__init__(self, parent, padding=12)

        self.admin = admin
        self.name_var = tk.StringVar()
        self.allergen_var = tk.BooleanVar()

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            self,
            columns=("id", "name", "allergen"),
            show="headings",
        )

        for column, title in (
            ("id", "ID"),
            ("name", "Название"),
            ("allergen", "Аллерген"),
        ):
            self.tree.heading(column, text=title)

        self.tree.grid(
            row=0,
            column=0,
            columnspan=4,
            sticky="nsew",
        )
        self.tree.bind(
            "<<TreeviewSelect>>",
            self.selected,
        )

        ttk.Entry(
            self,
            textvariable=self.name_var,
        ).grid(row=1, column=0, sticky="ew", pady=(10, 0))

        ttk.Checkbutton(
            self,
            text="Распространённый аллерген",
            variable=self.allergen_var,
        ).grid(row=1, column=1, pady=(10, 0))

        ttk.Button(
            self,
            text="Добавить",
            command=self.add,
        ).grid(row=1, column=2, padx=5, pady=(10, 0))

        ttk.Button(
            self,
            text="Изменить",
            command=self.update,
        ).grid(row=1, column=3, pady=(10, 0))

        ttk.Button(
            self,
            text="Удалить",
            command=self.delete,
            style="Danger.TButton",
        ).grid(row=2, column=3, pady=(8, 0))

    def load(self, items: list[dict]) -> None:
        self.tree.delete(*self.tree.get_children())

        for item in items:
            self.tree.insert(
                "",
                tk.END,
                iid=str(item["id"]),
                values=(
                    item["id"],
                    item["name"],
                    "Да" if item["is_common_allergen"] else "Нет",
                ),
            )

    def selected(self, event=None) -> None:
        selection = self.tree.selection()

        if selection:
            values = self.tree.item(
                selection[0],
                "values",
            )
            self.name_var.set(values[1])
            self.allergen_var.set(values[2] == "Да")

    def add(self) -> None:
        name = self.name_var.get().strip()

        if not name:
            return

        self.admin.perform_action(
            lambda: self.admin.api_client.create_ingredient(
                name,
                self.allergen_var.get(),
            ),
            "Ингредиент добавлен.",
        )

    def update(self) -> None:
        ingredient_id = self.selected_id()
        name = self.name_var.get().strip()

        if ingredient_id is None or not name:
            return

        self.admin.perform_action(
            lambda: self.admin.api_client.update_ingredient(
                ingredient_id,
                name,
                self.allergen_var.get(),
            ),
            "Ингредиент изменён.",
        )

    def delete(self) -> None:
        ingredient_id = self.selected_id()

        if ingredient_id is None:
            return

        if not messagebox.askyesno(
            "Удаление",
            "Удалить выбранный ингредиент?",
            parent=self,
        ):
            return

        self.admin.perform_action(
            lambda: self.admin.api_client.delete_ingredient(
                ingredient_id
            ),
            "Ингредиент удалён.",
        )


class RecipeTab(ttk.Frame):
    def __init__(
        self,
        parent: ttk.Notebook,
        admin: AdminWindow,
    ) -> None:
        super().__init__(parent, padding=12)

        self.admin = admin

        self.pack_propagate(False)

        self.tree = ttk.Treeview(
            self,
            columns=("title", "category", "time", "calories"),
            show="headings",
        )

        for column, title in (
            ("title", "Название"),
            ("category", "Категории"),
            ("time", "Время"),
            ("calories", "Ккал"),
        ):
            self.tree.heading(column, text=title)

        self.tree.pack(fill="both", expand=True)

        buttons = ttk.Frame(self)
        buttons.pack(fill="x", pady=(10, 0))

        ttk.Button(
            buttons,
            text="Добавить",
            command=self.add,
        ).pack(side="left")

        ttk.Button(
            buttons,
            text="Изменить",
            command=self.update,
        ).pack(side="left", padx=5)

        ttk.Button(
            buttons,
            text="Удалить",
            command=self.delete,
            style="Danger.TButton",
        ).pack(side="left")

    def load(self, items: list[dict]) -> None:
        self.tree.delete(*self.tree.get_children())

        for recipe in items:
            self.tree.insert(
                "",
                tk.END,
                iid=str(recipe["id"]),
                values=(
                    recipe["title"],
                    ", ".join(
                        item["name"]
                        for item in recipe["categories"]
                    ),
                    recipe["total_time_minutes"],
                    recipe["calories_per_serving"],
                ),
            )

    def selected_recipe(self) -> dict | None:
        selection = self.tree.selection()

        if not selection:
            return None

        recipe_id = int(selection[0])

        return next(
            (
                recipe
                for recipe in self.admin.recipes
                if recipe["id"] == recipe_id
            ),
            None,
        )

    def add(self) -> None:
        RecipeEditorWindow(
            self.admin,
            recipe=None,
            categories=self.admin.categories,
            ingredients=self.admin.ingredients,
            on_submit=self.admin.save_recipe,
        )

    def update(self) -> None:
        recipe = self.selected_recipe()

        if recipe is None:
            return

        RecipeEditorWindow(
            self.admin,
            recipe=recipe,
            categories=self.admin.categories,
            ingredients=self.admin.ingredients,
            on_submit=self.admin.save_recipe,
        )

    def delete(self) -> None:
        recipe = self.selected_recipe()

        if recipe is None:
            return

        if not messagebox.askyesno(
            "Удаление",
            f"Удалить рецепт «{recipe['title']}»?",
            parent=self,
        ):
            return

        self.admin.perform_action(
            lambda: self.admin.api_client.delete_recipe(
                recipe["id"]
            ),
            "Рецепт удалён.",
        )