from desktop.recipe_details import RecipeDetailsWindow
from concurrent.futures import ThreadPoolExecutor
from queue import Empty, Queue
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable

from desktop.api_client import APIClient, APIClientError

from desktop.admin_window import AdminWindow

from desktop.theme import apply_theme

from desktop.start_page import StartPage


class RecipeApplication(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        self.title("Книга рецептов")
        self.geometry("1200x760")
        self.minsize(1000, 650)

        self.api_client = APIClient()
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.task_queue: Queue = Queue()

        self.categories: list[dict] = []
        self.ingredients: list[dict] = []
        self.recipes: dict[int, dict] = {}

        self.title_query_var = tk.StringVar()
        self.ingredient_query_var = tk.StringVar()
        self.max_time_var = tk.StringVar()
        self.max_calories_var = tk.StringVar()
        self.exclude_allergens_var = tk.BooleanVar(
            value=False
        )
        self.ingredient_match_var = tk.StringVar(
            value="all"
        )
        self.sort_var = tk.StringVar()

        self.sort_options = {
            "Название: А–Я": "title_asc",
            "Название: Я–А": "title_desc",
            "Сначала быстрые": "time_asc",
            "Сначала долгие": "time_desc",
            "Сначала менее калорийные": "calories_asc",
            "Сначала более калорийные": "calories_desc",
        }

        self.configure_styles()

        self.main_interface_open = False
        self.start_page: StartPage | None = None

        self.show_start_page()

        self.protocol(
            "WM_DELETE_WINDOW",
            self.close_application,
        )

        self.after(100, self.process_task_queue)

    def configure_styles(self) -> None:
        apply_theme(self)

    def show_start_page(self) -> None:
        self.start_page = StartPage(
            parent=self,
            on_start=self.open_main_interface,
        )

        self.start_page.pack(
            fill="both",
            expand=True,
        )

    def open_main_interface(self) -> None:
        if self.main_interface_open:
            return

        self.main_interface_open = True

        if self.start_page is not None:
            self.start_page.destroy()
            self.start_page = None

        self.create_widgets()

        # Загружаем данные только после открытия
        # основного меню.
        self.after(
            150,
            self.load_initial_data,
        )

    def create_widgets(self) -> None:
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.create_search_panel()
        self.create_content_panel()
        self.create_status_bar()

    def create_search_panel(self) -> None:
        panel = ttk.Frame(self, padding=12)
        panel.grid(
            row=0,
            column=0,
            sticky="ew",
        )

        panel.grid_columnconfigure(1, weight=1)
        panel.grid_columnconfigure(3, weight=1)

        ttk.Label(
            panel,
            text="Поиск рецептов",
            font=("Segoe UI", 18, "bold"),
        ).grid(
            row=0,
            column=0,
            columnspan=6,
            sticky="w",
            pady=(0, 10),
        )

        ttk.Label(
            panel,
            text="Название:",
        ).grid(
            row=1,
            column=0,
            sticky="w",
            padx=(0, 5),
        )

        title_entry = ttk.Entry(
            panel,
            textvariable=self.title_query_var,
        )
        title_entry.grid(
            row=1,
            column=1,
            sticky="ew",
            padx=(0, 15),
        )

        title_entry.bind(
            "<Return>",
            lambda event: self.search_recipes(),
        )

        ttk.Label(
            panel,
            text="Название ингредиента:",
        ).grid(
            row=1,
            column=2,
            sticky="w",
            padx=(0, 5),
        )

        ingredient_entry = ttk.Entry(
            panel,
            textvariable=self.ingredient_query_var,
        )
        ingredient_entry.grid(
            row=1,
            column=3,
            sticky="ew",
            padx=(0, 15),
        )

        ingredient_entry.bind(
            "<Return>",
            lambda event: self.search_recipes(),
        )

        self.search_button = ttk.Button(
            panel,
            text="Найти",
            command=self.search_recipes,
        )
        self.search_button.grid(
            row=1,
            column=4,
            sticky="e",
        )

        ttk.Button(
            panel,
            text="Управление",
            command=self.open_admin_window,
        ).grid(
            row=1,
            column=5,
            padx=(8, 0),
        )

    def create_content_panel(self) -> None:
        content = ttk.Frame(
            self,
            padding=(12, 0, 12, 8),
        )
        content.grid(
            row=1,
            column=0,
            sticky="nsew",
        )

        content.grid_rowconfigure(0, weight=1)
        content.grid_columnconfigure(1, weight=1)

        self.create_filters_panel(content)
        self.create_results_panel(content)

    def create_filters_panel(
        self,
        parent: ttk.Frame,
    ) -> None:
        filters = ttk.LabelFrame(
            parent,
            text="Фильтры",
            padding=10,
        )
        filters.grid(
            row=0,
            column=0,
            sticky="ns",
            padx=(0, 10),
        )

        notebook = ttk.Notebook(filters)
        notebook.grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="nsew",
            pady=(0, 10),
        )

        self.category_listbox = self.create_listbox_tab(
            notebook,
            "Категории",
        )

        self.included_ingredient_listbox = (
            self.create_listbox_tab(
                notebook,
                "Добавить",
            )
        )

        self.excluded_ingredient_listbox = (
            self.create_listbox_tab(
                notebook,
                "Исключить",
            )
        )

        ttk.Label(
            filters,
            text="Режим ингредиентов:",
        ).grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="w",
        )

        ttk.Radiobutton(
            filters,
            text="Должны быть все",
            variable=self.ingredient_match_var,
            value="all",
        ).grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="w",
        )

        ttk.Radiobutton(
            filters,
            text="Достаточно одного",
            variable=self.ingredient_match_var,
            value="any",
        ).grid(
            row=3,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(0, 8),
        )

        ttk.Checkbutton(
            filters,
            text="Исключить распространённые аллергены",
            variable=self.exclude_allergens_var,
        ).grid(
            row=4,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(0, 10),
        )

        ttk.Label(
            filters,
            text="Максимальное время:",
        ).grid(
            row=5,
            column=0,
            sticky="w",
            pady=3,
        )

        ttk.Entry(
            filters,
            textvariable=self.max_time_var,
            width=10,
        ).grid(
            row=5,
            column=1,
            sticky="ew",
            pady=3,
        )

        ttk.Label(
            filters,
            text="Максимум ккал:",
        ).grid(
            row=6,
            column=0,
            sticky="w",
            pady=3,
        )

        ttk.Entry(
            filters,
            textvariable=self.max_calories_var,
            width=10,
        ).grid(
            row=6,
            column=1,
            sticky="ew",
            pady=3,
        )

        ttk.Label(
            filters,
            text="Сортировка:",
        ).grid(
            row=7,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(10, 3),
        )

        sort_combobox = ttk.Combobox(
            filters,
            textvariable=self.sort_var,
            values=list(self.sort_options),
            state="readonly",
            width=28,
        )
        sort_combobox.grid(
            row=8,
            column=0,
            columnspan=2,
            sticky="ew",
        )
        sort_combobox.current(0)

        ttk.Button(
            filters,
            text="Сбросить фильтры",
            command=self.reset_filters,
        ).grid(
            row=9,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(12, 0),
        )

    def create_listbox_tab(
        self,
        notebook: ttk.Notebook,
        title: str,
    ) -> tk.Listbox:
        frame = ttk.Frame(notebook, padding=5)
        notebook.add(frame, text=title)

        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        listbox = tk.Listbox(
            frame,
            selectmode=tk.EXTENDED,
            exportselection=False,
            width=32,
            height=12,
            font=("Segoe UI", 10),
        )
        listbox.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

        scrollbar = ttk.Scrollbar(
            frame,
            orient="vertical",
            command=listbox.yview,
        )
        scrollbar.grid(
            row=0,
            column=1,
            sticky="ns",
        )

        listbox.configure(
            yscrollcommand=scrollbar.set
        )

        return listbox

    def create_results_panel(
        self,
        parent: ttk.Frame,
    ) -> None:
        results = ttk.LabelFrame(
            parent,
            text="Найденные рецепты",
            padding=8,
        )
        results.grid(
            row=0,
            column=1,
            sticky="nsew",
        )

        results.grid_rowconfigure(0, weight=1)
        results.grid_columnconfigure(0, weight=1)

        columns = (
            "title",
            "categories",
            "time",
            "calories",
        )

        self.recipe_tree = ttk.Treeview(
            results,
            columns=columns,
            show="headings",
            selectmode="browse",
        )

        self.recipe_tree.heading(
            "title",
            text="Название",
        )
        self.recipe_tree.heading(
            "categories",
            text="Категории",
        )
        self.recipe_tree.heading(
            "time",
            text="Время",
        )
        self.recipe_tree.heading(
            "calories",
            text="Ккал",
        )

        self.recipe_tree.column(
            "title",
            width=250,
            minwidth=150,
        )
        self.recipe_tree.column(
            "categories",
            width=230,
            minwidth=120,
        )
        self.recipe_tree.column(
            "time",
            width=90,
            anchor="center",
        )
        self.recipe_tree.column(
            "calories",
            width=90,
            anchor="center",
        )

        self.recipe_tree.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

        scrollbar = ttk.Scrollbar(
            results,
            orient="vertical",
            command=self.recipe_tree.yview,
        )
        scrollbar.grid(
            row=0,
            column=1,
            sticky="ns",
        )

        self.recipe_tree.configure(
            yscrollcommand=scrollbar.set
        )

        buttons = ttk.Frame(results)
        buttons.grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(8, 0),
        )

        ttk.Button(
            buttons,
            text="Открыть рецепт",
            command=self.open_selected_recipe,
        ).pack(
            side="right",
        )

        self.recipe_tree.bind(
            "<Double-1>",
            lambda event: self.open_selected_recipe(),
        )

        self.recipe_tree.bind(
            "<Return>",
            lambda event: self.open_selected_recipe(),
        )

    def create_status_bar(self) -> None:
        self.status_var = tk.StringVar(
            value="Подключение к серверу..."
        )

        ttk.Label(
            self,
            textvariable=self.status_var,
            style="Status.TLabel",
            relief="sunken",
            anchor="w",
        ).grid(
            row=2,
            column=0,
            sticky="ew",
        )

    def run_background(
        self,
        task: Callable[[], Any],
        on_success: Callable[[Any], None],
        on_error: Callable[[Exception], None] | None = None,
    ) -> None:
        def worker() -> None:
            try:
                result = task()
            except Exception as error:
                self.task_queue.put(
                    (
                        "error",
                        (on_error, error),
                    )
                )
            else:
                self.task_queue.put(
                    (
                        "success",
                        (on_success, result),
                    )
                )

        self.executor.submit(worker)

    def process_task_queue(self) -> None:
        try:
            while True:
                task_type, payload = (
                    self.task_queue.get_nowait()
                )

                if task_type == "success":
                    callback, result = payload
                    callback(result)
                else:
                    error_callback, error = payload

                    if error_callback is not None:
                        error_callback(error)
                    else:
                        self.handle_background_error(
                            error
                        )

        except Empty:
            pass

        self.after(100, self.process_task_queue)

    def handle_background_error(
        self,
        error: Exception,
    ) -> None:
        self.search_button.configure(
            state="normal"
        )
        self.status_var.set("Произошла ошибка")

        if isinstance(error, APIClientError):
            message = str(error)
        else:
            message = f"Неожиданная ошибка: {error}"

        messagebox.showerror(
            "Ошибка",
            message,
        )

    def load_initial_data(self) -> None:
        self.status_var.set(
            "Загрузка категорий и ингредиентов..."
        )

        def task() -> tuple[list[dict], list[dict]]:
            self.api_client.check_database()

            return (
                self.api_client.get_categories(),
                self.api_client.get_ingredients(),
            )

        self.run_background(
            task,
            self.initial_data_loaded,
        )

    def initial_data_loaded(
        self,
        result: tuple[list[dict], list[dict]],
    ) -> None:
        self.categories, self.ingredients = result

        self.fill_listbox(
            self.category_listbox,
            self.categories,
        )

        self.fill_listbox(
            self.included_ingredient_listbox,
            self.ingredients,
        )

        self.fill_listbox(
            self.excluded_ingredient_listbox,
            self.ingredients,
        )

        self.status_var.set(
            "Данные загружены"
        )

        self.search_recipes()

    @staticmethod
    def fill_listbox(
        listbox: tk.Listbox,
        items: list[dict],
    ) -> None:
        listbox.delete(0, tk.END)

        for item in items:
            listbox.insert(
                tk.END,
                item["name"],
            )

    @staticmethod
    def selected_ids(
        listbox: tk.Listbox,
        items: list[dict],
    ) -> list[int]:
        return [
            items[index]["id"]
            for index in listbox.curselection()
        ]

    def parse_positive_integer(
        self,
        value: str,
        field_name: str,
    ) -> int | None:
        value = value.strip()

        if not value:
            return None

        try:
            number = int(value)
        except ValueError:
            raise ValueError(
                f"Поле «{field_name}» должно быть целым числом"
            )

        if number <= 0:
            raise ValueError(
                f"Поле «{field_name}» должно быть больше нуля"
            )

        return number

    def parse_positive_float(
        self,
        value: str,
        field_name: str,
    ) -> float | None:
        value = value.strip().replace(",", ".")

        if not value:
            return None

        try:
            number = float(value)
        except ValueError:
            raise ValueError(
                f"Поле «{field_name}» должно быть числом"
            )

        if number < 0:
            raise ValueError(
                f"Поле «{field_name}» не может быть отрицательным"
            )

        return number

    def search_recipes(self) -> None:
        try:
            max_time = self.parse_positive_integer(
                self.max_time_var.get(),
                "Максимальное время",
            )

            max_calories = self.parse_positive_float(
                self.max_calories_var.get(),
                "Максимум ккал",
            )
        except ValueError as error:
            messagebox.showwarning(
                "Некорректные фильтры",
                str(error),
            )
            return

        category_ids = self.selected_ids(
            self.category_listbox,
            self.categories,
        )

        ingredient_ids = self.selected_ids(
            self.included_ingredient_listbox,
            self.ingredients,
        )

        excluded_ids = self.selected_ids(
            self.excluded_ingredient_listbox,
            self.ingredients,
        )

        query = self.title_query_var.get().strip()
        ingredient_query = (
            self.ingredient_query_var.get().strip()
        )

        sort_value = self.sort_options[
            self.sort_var.get()
        ]

        self.search_button.configure(
            state="disabled"
        )
        self.status_var.set("Поиск рецептов...")

        def task() -> list[dict]:
            return self.api_client.get_recipes(
                query=query or None,
                ingredient_query=(
                    ingredient_query or None
                ),
                category_ids=category_ids,
                ingredient_ids=ingredient_ids,
                excluded_ingredient_ids=excluded_ids,
                ingredient_match=(
                    self.ingredient_match_var.get()
                ),
                exclude_common_allergens=(
                    self.exclude_allergens_var.get()
                ),
                max_time_minutes=max_time,
                max_calories=max_calories,
                sort=sort_value,
            )

        self.run_background(
            task,
            self.recipes_loaded,
        )

    def recipes_loaded(
        self,
        recipes: list[dict],
    ) -> None:
        self.search_button.configure(
            state="normal"
        )

        self.recipe_tree.delete(
            *self.recipe_tree.get_children()
        )

        self.recipes = {
            recipe["id"]: recipe
            for recipe in recipes
        }

        for recipe in recipes:
            category_names = ", ".join(
                category["name"]
                for category in recipe["categories"]
            )

            calories = float(
                recipe["calories_per_serving"]
            )

            self.recipe_tree.insert(
                "",
                tk.END,
                iid=str(recipe["id"]),
                values=(
                    recipe["title"],
                    category_names,
                    f"{recipe['total_time_minutes']} мин.",
                    f"{calories:.0f}",
                ),
            )

        if recipes:
            self.status_var.set(
                f"Найдено рецептов: {len(recipes)}"
            )
        else:
            self.status_var.set(
                "Рецепты не найдены"
            )

    def open_selected_recipe(self) -> None:
        selected_items = (
            self.recipe_tree.selection()
        )

        if not selected_items:
            messagebox.showinfo(
                "Рецепт не выбран",
                "Выберите рецепт в таблице.",
            )
            return

        recipe_id = int(selected_items[0])

        self.status_var.set(
            "Загрузка рецепта..."
        )

        def task() -> tuple[dict, bytes | None]:
            recipe = self.api_client.get_recipe(
                recipe_id
            )

            image_content: bytes | None = None
            image_path = recipe.get("image_path")

            if image_path:
                try:
                    image_content = (
                        self.api_client.download_image(
                            image_path
                        )
                    )
                except APIClientError:
                    # Рецепт всё равно откроется,
                    # но с заглушкой вместо фотографии.
                    image_content = None

            return recipe, image_content

        self.run_background(
            task,
            self.recipe_details_loaded,
        )

    def recipe_details_loaded(
        self,
        result: tuple[dict, bytes | None],
    ) -> None:
        recipe, image_content = result

        self.status_var.set(
            f"Открыт рецепт: {recipe['title']}"
        )

        RecipeDetailsWindow(
            parent=self,
            api_client=self.api_client,
            recipe=recipe,
            image_content=image_content,
            run_background=self.run_background,
        )

    def reset_filters(self) -> None:
        self.title_query_var.set("")
        self.ingredient_query_var.set("")
        self.max_time_var.set("")
        self.max_calories_var.set("")
        self.exclude_allergens_var.set(False)
        self.ingredient_match_var.set("all")
        self.sort_var.set(
            next(iter(self.sort_options))
        )

        self.category_listbox.selection_clear(
            0,
            tk.END,
        )
        self.included_ingredient_listbox.selection_clear(
            0,
            tk.END,
        )
        self.excluded_ingredient_listbox.selection_clear(
            0,
            tk.END,
        )

        self.search_recipes()

    def close_application(self) -> None:
        self.executor.shutdown(
            wait=False,
            cancel_futures=True,
        )
        self.api_client.close()
        self.destroy()

    def open_admin_window(self) -> None:
        AdminWindow(
            parent=self,
            api_client=self.api_client,
            run_background=self.run_background,
            on_data_changed=self.load_initial_data,
        )    


if __name__ == "__main__":
    application = RecipeApplication()
    application.mainloop()