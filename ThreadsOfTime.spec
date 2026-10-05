from pathlib import Path


ROOT = Path(SPECPATH).resolve()
ENTRY_POINT = ROOT / "main.py"
ASSET_SUFFIXES = {
    ".avif",
    ".bmp",
    ".gif",
    ".jpeg",
    ".jpg",
    ".json",
    ".m4a",
    ".mid",
    ".midi",
    ".mp3",
    ".ogg",
    ".otf",
    ".png",
    ".ttf",
    ".wav",
    ".webp",
}
EXCLUDED_PARTS = {".git", ".venv", "venv", "build", "dist", "__pycache__"}

datas = [
    (str(path), str(path.relative_to(ROOT).parent))
    for path in ROOT.rglob("*")
    if path.is_file()
    and path.suffix.lower() in ASSET_SUFFIXES
    and path.name != "game_save.json"
    and not EXCLUDED_PARTS.intersection(path.relative_to(ROOT).parts)
]

a = Analysis(
    [str(ENTRY_POINT)],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="ThreadsOfTime",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)