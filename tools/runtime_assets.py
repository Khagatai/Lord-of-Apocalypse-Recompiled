"""Use the normal title's font assets for both release and relocated QA executables."""
from pathlib import Path
import save_storage


def configure_fonts(env, release_directory):
    configured=env.get('SR_FONTDIR')
    root=Path(configured) if configured is not None else Path(release_directory)/'font'
    if not root.is_absolute():
        raise ValueError('Configured font directory must be absolute')
    root=root.resolve()
    if not root.is_dir():
        raise FileNotFoundError('Required diagnostic font directory is missing')
    hashes=save_storage.tree_hashes(root)
    if not any(Path(name).suffix.lower()=='.pgf' for name in hashes):
        raise FileNotFoundError('Diagnostic font directory contains no PGF files')
    env['SR_FONTDIR']=str(root)
    return root,hashes
