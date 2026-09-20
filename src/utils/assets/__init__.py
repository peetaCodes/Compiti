import sys
from pathlib import Path

PROJ_DIR = Path(sys.path[1])
ASSETS_DIR = PROJ_DIR / "assets"
IMAGES_DIR = ASSETS_DIR / "images"
FONTS_DIR = ASSETS_DIR / "fonts"

FONTS = {file.name.partition(".")[0]: str(file.absolute()) for file in FONTS_DIR.rglob("*.ttf")}

#print(FONTS, FONTS_DIR, FONTS_DIR.rglob("*.ttf"))
