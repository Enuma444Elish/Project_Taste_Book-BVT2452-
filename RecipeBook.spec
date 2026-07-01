from pathlib import Path


project_root = Path(SPECPATH).resolve()


analysis = Analysis(
    ["desktop/main.py"],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        (
            "desktop/assets/Main.jpg",
            "desktop/assets",
        ),
        (
            "desktop/assets/RecipeBook.ico",
            "desktop/assets",
        ),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)


pyz = PYZ(analysis.pure)


exe = EXE(
    pyz,
    analysis.scripts,
    analysis.binaries,
    analysis.datas,
    [],
    name="RecipeBook",
    icon="desktop/assets/RecipeBook.ico",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
)