"""Use the pinned framework's existing CSO/CHD import, never a second decoder."""
import importlib.util,os,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def normalize(image,root=ROOT):
    image=Path(image).resolve(strict=True)
    with image.open('rb') as stream:magic=stream.read(8)
    if not any(magic.startswith(value) for value in (b'CISO',b'ZISO',b'MComprHD')):
        return image
    # All imported game data stays in ignored local storage. The upstream helper
    # caches its game-independent compiler output in external/.../build.
    framework=root/'external/nakagawa-recomp'
    import source_identity,title
    source_identity.verify(root,'framework')
    spec=importlib.util.spec_from_file_location('loa_disc_expand',framework/'tools/nk_core/disc_expand_tool.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    env=os.environ.copy()
    try:
        os.environ['CC']=str(title.SDK/'bin/gcc.exe')
        os.environ['PATH']=str(title.SDK/'bin')+os.pathsep+env.get('PATH','')
        print('Expanding compressed PSP image with the pinned local disc reader...',flush=True)
        return module.ensure_plain_iso(image,root/'private/recomplauncher/cache',root=framework)
    finally:
        os.environ.clear();os.environ.update(env)
