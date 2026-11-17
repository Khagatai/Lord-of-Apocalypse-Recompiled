"""Inventory exact local title network imports against pinned implementation sources."""
import json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import title
def main():
    title.verify_inputs()
    survey=json.loads((ROOT/'private/eboot-survey.json').read_text())
    if survey['sha256']!='e2199a4797680f5956f357757bf9987c592f1ea002001a7a9557a36ecf51fb5f':raise ValueError('Module identity differs')
    reference=ROOT/'private/tools/ppsspp/Core/HLE'
    names={}
    for path in reference.glob('sceNet*.cpp'):
        for line in path.read_text(errors='replace').splitlines():
            match=re.search(r'\{0[xX]([0-9a-fA-F]+),.*?"(sceNet[^\"]+)"',line)
            if match:names[int(match[1],16)]=match[2]
    source=(title.FRAMEWORK/'src/rt/hle_network.c').read_text()
    rows=[]
    for row in survey['imports']:
        if not row['library'].startswith(('sceNet','sceWlan')):continue
        nid=int(row['nid'],16);name=names.get(nid,'unknown')
        registration=next((line.strip() for line in source.splitlines() if re.search(r'0x0?'+f'{nid:x}'+r'u?\b',line,re.I) and 'register' in line),'not in hle_network.c')
        rows.append(dict(library=row['library'],nid=f'{nid:08x}',name=name,registration=registration))
    report=dict(framework_commit=title.CONFIG['runtime']['commit'],module_sha256=survey['sha256'],network_imports=rows,
        native_multiplayer_validated=False)
    (ROOT/'private/network-survey.json').write_text(json.dumps(report,indent=2)+'\n')
    for row in rows:print(row['nid'],row['name'], '[unsupported]' if 'unsupported' in row['registration'] else '')
if __name__=='__main__':main()
