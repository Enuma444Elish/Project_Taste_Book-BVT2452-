import tkinter as tk
from tkinter import ttk


COLORS = {
    "background": "#F7F1E5",
    "surface": "#FFFDF8",
    "surface_dark": "#EFE4D2",
    "primary": "#6F8F5E",
    "primary_hover": "#557447",
    "accent": "#C9794F",
    "text": "#3F342C",
    "muted": "#76685E",
    "border": "#D9CBB9",
    "selection": "#DCE8D5",
    "danger": "#A94A43",
}


def apply_theme(root: tk.Misc) -> None:
    style = ttk.Style(root)

    # Clam лучше поддерживает собственные цвета.
    style.theme_use("clam")

    root.configure(
        background=COLORS["background"]
    )

    root.option_add(
        "*Font",
        "{Segoe UI} 10",
    )

    root.option_add(
        "*Listbox.background",
        COLORS["surface"],
    )
    root.option_add(
        "*Listbox.foreground",
        COLORS["text"],
    )
    root.option_add(
        "*Listbox.selectBackground",
        COLORS["primary"],
    )
    root.option_add(
        "*Listbox.selectForeground",
        "#FFFFFF",
    )

    root.option_add(
        "*Text.background",
        COLORS["surface"],
    )
    root.option_add(
        "*Text.foreground",
        COLORS["text"],
    )
    root.option_add(
        "*Text.insertBackground",
        COLORS["text"],
    )
    root.option_add(
        "*Text.selectBackground",
        COLORS["selection"],
    )

    style.configure(
        ".",
        background=COLORS["background"],
        foreground=COLORS["text"],
        font=("Segoe UI", 10),
    )

    style.configure(
        "TFrame",
        background=COLORS["background"],
    )

    style.configure(
        "TLabel",
        background=COLORS["background"],
        foreground=COLORS["text"],
    )

    style.configure(
        "Title.TLabel",
        font=("Segoe UI Semibold", 22),
        foreground=COLORS["primary_hover"],
    )

    style.configure(
        "Status.TLabel",
        background=COLORS["surface_dark"],
        foreground=COLORS["muted"],
        padding=(10, 6),
    )

    style.configure(
        "TLabelframe",
        background=COLORS["surface"],
        bordercolor=COLORS["border"],
        relief="solid",
        borderwidth=1,
    )

    style.configure(
        "TLabelframe.Label",
        background=COLORS["surface"],
        foreground=COLORS["primary_hover"],
        font=("Segoe UI Semibold", 10),
    )

    style.configure(
        "TButton",
        background=COLORS["primary"],
        foreground="#FFFFFF",
        borderwidth=0,
        padding=(12, 7),
        font=("Segoe UI Semibold", 10),
    )

    style.map(
        "TButton",
        background=[
            ("pressed", COLORS["primary_hover"]),
            ("active", COLORS["primary_hover"]),
            ("disabled", "#B7C1B1"),
        ],
        foreground=[
            ("disabled", "#EEEEEE"),
        ],
    )

    style.configure(
        "Start.TButton",
        background=COLORS["primary"],
        foreground="#FFFFFF",
        borderwidth=0,
        padding=(50, 14),
        font=("Segoe UI Semibold", 16),
    )

    style.map(
        "Start.TButton",
        background=[
            ("pressed", COLORS["primary_hover"]),
            ("active", COLORS["primary_hover"]),
            ("disabled", "#AEB9A8"),
        ],
        foreground=[
            ("disabled", "#EEEEEE"),
        ],
    )    

    style.configure(
        "Danger.TButton",
        background=COLORS["danger"],
        foreground="#FFFFFF",
    )

    style.map(
        "Danger.TButton",
        background=[
            ("active", "#873A35"),
            ("pressed", "#873A35"),
        ],
    )

    style.configure(
        "TEntry",
        fieldbackground=COLORS["surface"],
        foreground=COLORS["text"],
        bordercolor=COLORS["border"],
        padding=6,
    )

    style.map(
        "TEntry",
        bordercolor=[
            ("focus", COLORS["primary"]),
        ],
    )

    style.configure(
        "TCombobox",
        fieldbackground=COLORS["surface"],
        background=COLORS["surface"],
        foreground=COLORS["text"],
        bordercolor=COLORS["border"],
        padding=5,
    )

    style.configure(
        "TSpinbox",
        fieldbackground=COLORS["surface"],
        foreground=COLORS["text"],
        bordercolor=COLORS["border"],
        padding=5,
    )

    style.configure(
        "TCheckbutton",
        background=COLORS["background"],
        foreground=COLORS["text"],
        padding=3,
    )

    style.configure(
        "TRadiobutton",
        background=COLORS["background"],
        foreground=COLORS["text"],
        padding=3,
    )

    style.configure(
        "Treeview",
        background=COLORS["surface"],
        fieldbackground=COLORS["surface"],
        foreground=COLORS["text"],
        bordercolor=COLORS["border"],
        rowheight=30,
        font=("Segoe UI", 10),
    )

    style.configure(
        "Treeview.Heading",
        background=COLORS["primary"],
        foreground="#FFFFFF",
        relief="flat",
        padding=(8, 7),
        font=("Segoe UI Semibold", 10),
    )

    style.map(
        "Treeview",
        background=[
            ("selected", COLORS["selection"]),
        ],
        foreground=[
            ("selected", COLORS["text"]),
        ],
    )

    style.map(
        "Treeview.Heading",
        background=[
            ("active", COLORS["primary_hover"]),
        ],
    )

    style.configure(
        "TNotebook",
        background=COLORS["background"],
        borderwidth=0,
    )

    style.configure(
        "TNotebook.Tab",
        background=COLORS["surface_dark"],
        foreground=COLORS["text"],
        padding=(14, 8),
    )

    style.map(
        "TNotebook.Tab",
        background=[
            ("selected", COLORS["primary"]),
            ("active", COLORS["selection"]),
        ],
        foreground=[
            ("selected", "#FFFFFF"),
        ],
    )