"""Persistent provider selection. Session invitations and tokens are never saved here."""
import json,os,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/'private/settings/online-service.json'
def validate(value):
    if not isinstance(value,dict) or set(value)-{'backend','url'}:raise ValueError('Invalid online configuration.')
    backend=value.get('backend','rooms');url=value.get('url','')
    if backend not in ('rooms','steam') or not isinstance(url,str):raise ValueError('Unknown online provider.')
    if url:
        from online_agent import service_url
        service_url(url)
    return dict(backend=backend,url=url)
def load(path=CONFIG):
    path=Path(path).resolve()
    if not path.is_relative_to(ROOT/'private') or path.suffix!='.json':raise ValueError('Online configuration must be private.')
    return validate(json.loads(path.read_text())) if path.exists() else validate({})
def save(value,path=CONFIG):
    path=Path(path).resolve();load(path);value=validate(value);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=None
    try:
        with tempfile.NamedTemporaryFile('w',dir=path.parent,suffix='.tmp',encoding='utf-8',delete=False) as stream:
            temporary=Path(stream.name);json.dump(value,stream);stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,path);temporary=None
    finally:
        if temporary:temporary.unlink(missing_ok=True)
