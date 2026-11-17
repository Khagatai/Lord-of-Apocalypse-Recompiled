"""Check the pause menu's dynamically loaded runtime before opening the game."""
import ctypes,os
from pathlib import Path
FONT_FILES=('geist/Geist-Regular.ttf','geist/Geist-Medium.ttf','geist/Geist-SemiBold.ttf',
    'geist-mono/GeistMono-Regular.ttf','geist-mono/GeistMono-Medium.ttf',
    'chakra-petch/ChakraPetch-SemiBold.ttf','chakra-petch/ChakraPetch-Bold.ttf',
    'noto-sans-jp/NotoSansJP-Regular.ttf')

def verify(root):
    root=Path(root)
    folder=root/'private/toolchain/prerequisites/msys64/ucrt64/bin'
    library=folder/'SDL3_ttf.dll'
    if not library.is_file():raise FileNotFoundError('Pause menu library SDL3_ttf.dll is missing. Extract the menu-fix ZIP into the folder containing Start-Game.cmd, or extract the corrected full tester ZIP.')
    fonts=root/'external/nakagawa-recomp/assets/fonts/ui'
    for name in FONT_FILES:
        if not (fonts/name).is_file():raise FileNotFoundError('Pause menu font missing: '+name+'. Extract the complete tester ZIP.')
    try:
        with os.add_dll_directory(str(folder)):
            dll=ctypes.CDLL(str(library))
            for name in ('TTF_Init','TTF_CreateText','TTF_GetGlyphImageForIndex'):getattr(dll,name)
    except (OSError,AttributeError) as error:
        raise RuntimeError('Pause menu library could not load. Extract all DLLs from the menu-fix ZIP together; do not copy SDL3_ttf.dll alone.') from error
    return {'dynamic_library':'SDL3_ttf.dll','fonts_checked':len(FONT_FILES),'load':'PASS'}
