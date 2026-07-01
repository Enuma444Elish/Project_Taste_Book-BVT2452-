import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from desktop.backup_manager import (
    BackupManager,
)


class BackupTab(ttk.Frame):
    def __init__(
        self,
        parent: ttk.Notebook,
        admin,
    ) -> None:
        super().__init__(
            parent,
            padding=12,
        )

        self.admin = admin
        self.manager = BackupManager()
        self.backups: dict[str, dict] = {}
        self.busy = False

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        columns = (
            "label",
            "type",
            "created",
            "recipes",
            "protected",
        )

        self.tree = ttk.Treeview(
            self,
            columns=columns,
            show="headings",
            selectmode="browse",
        )
        self.tree.bind(
            "<<TreeviewSelect>>",
            self.selection_changed,
        )        
        self.tree.grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="nsew",
        )

        headings = {
            "label": "Название",
            "type": "Тип",
            "created": "Создан",
            "recipes": "Рецептов",
            "protected": "Защищён",
        }

        for column, heading in headings.items():
            self.tree.heading(
                column,
                text=heading,
            )

        self.tree.column(
            "label",
            width=230,
        )
        self.tree.column(
            "type",
            width=130,
        )
        self.tree.column(
            "created",
            width=170,
        )
        self.tree.column(
            "recipes",
            width=90,
            anchor="center",
        )
        self.tree.column(
            "protected",
            width=100,
            anchor="center",
        )

        scrollbar = ttk.Scrollbar(
            self,
            orient="vertical",
            command=self.tree.yview,
        )
        scrollbar.grid(
            row=0,
            column=2,
            sticky="ns",
        )

        self.tree.configure(
            yscrollcommand=scrollbar.set
        )

        buttons = ttk.Frame(self)
        buttons.grid(
            row=1,
            column=0,
            columnspan=3,
            sticky="ew",
            pady=(10, 0),
        )

        self.create_button = ttk.Button(
            buttons,
            text="Создать новый бэкап",
            command=self.create_backup,
        )
        self.create_button.pack(side="left")

        self.restore_button = ttk.Button(
            buttons,
            text="Переключиться на выбранный",
            command=self.restore_selected,
        )
        self.restore_button.pack(
            side="left",
            padx=8,
        )
        self.delete_button = ttk.Button(
            buttons,
            text="Удалить",
            command=self.delete_selected,
            style="Danger.TButton",
            state="disabled",
        )
        self.delete_button.pack(
            side="left",
            padx=(0, 8),
        )        

        ttk.Button(
            buttons,
            text="Обновить список",
            command=self.refresh,
        ).pack(side="left")

        ttk.Label(
            self,
            text=(
                "Перед переключением при необходимости "
                "создайте новый бэкап вручную. "
                "Стартовый бэкап удалить нельзя."
            ),
        ).grid(
            row=2,
            column=0,
            columnspan=3,
            sticky="w",
            pady=(10, 0),
        )

    def refresh(self) -> None:
        backups = self.manager.list_backups()

        self.tree.delete(
            *self.tree.get_children()
        )
        self.backups.clear()

        type_names = {
            "initial": "Стартовый",
            "manual": "Ручной",
            "before_restore": "Перед переключением",
        }

        for backup in backups:
            folder_name = backup["folder_name"]
            self.backups[folder_name] = backup

            label = (
                backup.get("label")
                or folder_name
            )

            self.tree.insert(
                "",
                tk.END,
                iid=folder_name,
                values=(
                    label,
                    type_names.get(
                        backup.get("type"),
                        backup.get("type", "Неизвестный"),
                    ),
                    backup.get("created_at", ""),
                    backup.get("recipe_count", "?"),
                    (
                        "Да"
                        if backup.get("protected")
                        else "Нет"
                    ),
                ),
            )

    def create_backup(self) -> None:
        if self.busy:
            return

        label = simpledialog.askstring(
            "Новый бэкап",
            "Введите название резервной копии:",
            parent=self,
        )

        if label is None:
            return

        label = label.strip()

        if not label:
            label = "Ручной бэкап"

        self.set_busy(True)

        self.admin.run_background(
            lambda: self.manager.create_backup(
                backup_type="manual",
                label=label,
            ),
            self.backup_created,
            self.operation_failed,
        )

    def backup_created(
        self,
        result=None,
    ) -> None:
        self.set_busy(False)
        self.refresh()

        messagebox.showinfo(
            "Резервное копирование",
            "Новый бэкап успешно создан.",
            parent=self,
        )

    def restore_selected(self) -> None:
        if self.busy:
            return

        selection = self.tree.selection()

        if not selection:
            messagebox.showinfo(
                "Выбор бэкапа",
                "Выберите резервную копию.",
                parent=self,
            )
            return

        backup = self.backups[selection[0]]

        if not backup.get("valid"):
            messagebox.showerror(
                "Повреждённый бэкап",
                "В резервной копии отсутствуют необходимые файлы.",
                parent=self,
            )
            return

        label = (
            backup.get("label")
            or backup["folder_name"]
        )

        confirmed = messagebox.askyesno(
            "Переключение базы",
            (
                f"Переключиться на бэкап «{label}»?\n\n"
                "Текущее состояние базы будет заменено.\n"
                "Автоматический бэкап создаваться не будет.\n\n"
                "Если текущие изменения нужны, сначала "
                "нажмите «Создать новый бэкап»."
            ),
            parent=self,
        )

        if not confirmed:
            return

        self.set_busy(True)

        def task() -> None:
            self.manager.restore_backup(
                backup["directory"]
            )

        self.admin.run_background(
            task,
            self.backup_restored,
            self.operation_failed,
        )

    def backup_restored(
        self,
        result=None,
    ) -> None:
        self.set_busy(False)
        self.refresh()

        # Обновляем административное и основное окна.
        self.admin.refresh_all()
        self.admin.on_data_changed()

        messagebox.showinfo(
            "Восстановление",
            "Приложение переключено на выбранный бэкап.",
            parent=self,
        )

    def operation_failed(
        self,
        error: Exception,
    ) -> None:
        self.set_busy(False)

        messagebox.showerror(
            "Ошибка резервного копирования",
            str(error),
            parent=self,
        )

    def set_busy(self, value: bool) -> None:
        self.busy = value

        common_state = (
            "disabled"
            if value
            else "normal"
        )

        self.create_button.configure(
            state=common_state
        )
        self.restore_button.configure(
            state=common_state
        )

        if value:
            self.delete_button.configure(
                state="disabled"
            )
        else:
            self.selection_changed()

    def selection_changed(
        self,
        event: tk.Event | None = None,
    ) -> None:
        if self.busy:
            self.delete_button.configure(
                state="disabled"
            )
            return

        selection = self.tree.selection()

        if not selection:
            self.delete_button.configure(
                state="disabled"
            )
            return

        backup = self.backups.get(selection[0])

        if backup is None:
            self.delete_button.configure(
                state="disabled"
            )
            return

        is_initial = (
            backup.get("protected") is True
            or backup.get("type") == "initial"
            or backup.get("folder_name") == "initial"
        )

        self.delete_button.configure(
            state=(
                "disabled"
                if is_initial
                else "normal"
            )
        )

    def delete_selected(self) -> None:
        if self.busy:
            return

        selection = self.tree.selection()

        if not selection:
            messagebox.showinfo(
                "Удаление бэкапа",
                "Выберите резервную копию.",
                parent=self,
            )
            return

        backup = self.backups[selection[0]]

        is_initial = (
            backup.get("protected") is True
            or backup.get("type") == "initial"
            or backup.get("folder_name") == "initial"
        )

        if is_initial:
            messagebox.showwarning(
                "Защищённый бэкап",
                "Стартовый бэкап удалить нельзя.",
                parent=self,
            )
            return

        label = (
            backup.get("label")
            or backup["folder_name"]
        )

        confirmed = messagebox.askyesno(
            "Удаление бэкапа",
            (
                f"Удалить бэкап «{label}»?\n\n"
                "Восстановить удалённый бэкап "
                "будет невозможно."
            ),
            parent=self,
        )

        if not confirmed:
            return

        self.set_busy(True)

        self.admin.run_background(
            lambda: self.manager.delete_backup(
                backup["directory"]
            ),
            self.backup_deleted,
            self.operation_failed,
        )

    def backup_deleted(
        self,
        result=None,
    ) -> None:
        self.set_busy(False)
        self.refresh()

        messagebox.showinfo(
            "Удаление бэкапа",
            "Резервная копия удалена.",
            parent=self,
        )