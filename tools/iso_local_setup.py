"""Create verified native build inputs from the player's ISO, never from bundled game bytes.

This is a build stage, not the complete English/HD installer. It fails before
changing game inputs if the disc, module or captured boot-state identity differs.
"""
import argparse,ctypes,gzip,hashlib,importlib.util,json,os,subprocess,sys,tempfile,tomllib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))

def file_hash(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def private_path(root,name):
    root=Path(root).resolve();path=(root/name).resolve()
    if not path.is_relative_to(root/'private'):raise ValueError('Local output escapes private storage: '+name)
    return path

def install_exact(root,name,raw):
    """Idempotent write; never overwrite an unknown existing file."""
    path=private_path(root,name)
    if path.exists():
        if path.read_bytes()!=raw:raise ValueError('Existing local build input differs: '+name)
        return path
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='loa-build-',suffix='.tmp',dir=path.parent)
    temporary=Path(tmp)
    try:
        with os.fdopen(fd,'wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
        try:os.link(temporary,path)
        except FileExistsError:
            if path.read_bytes()!=raw:raise ValueError('Concurrent local build input differs: '+name)
    finally:temporary.unlink(missing_ok=True)
    return path

def decrypt_module(data,bridge):
    if data[:4]==b'~SCE':
        offset=int.from_bytes(data[4:8],'little')
        if offset<8 or offset+0x150>len(data):raise ValueError('Invalid SCE wrapper')
        data=data[offset:]
    if len(data)<0x150 or data[:4]!=b'~PSP':raise ValueError('Expected encrypted PSP module')
    length=int.from_bytes(data[0x28:0x2c],'little')
    if not 52<=length<=64*1024*1024:raise ValueError('Invalid decrypted ELF size')
    library=ctypes.CDLL(str(bridge));fn=library.decrypt_prx
    fn.argtypes=(ctypes.c_void_p,ctypes.c_void_p,ctypes.c_uint);fn.restype=ctypes.c_int
    source=ctypes.create_string_buffer(data);output=ctypes.create_string_buffer(max(len(data),length))
    count=fn(source,output,len(data))
    if not 0<count<=len(output):raise RuntimeError('PRX decryption failed: '+str(count))
    raw=output.raw[:count]
    if raw[:2]==b'\x1f\x8b':raw=gzip.decompress(raw)
    if len(raw)!=length or raw[:4]!=b'\x7fELF':raise ValueError('Decrypted module is not the expected ELF')
    return raw

def boot_seed(config,seed):
    if seed.get('schema')!=1 or seed.get('kind')!='measured-register-seed':raise ValueError('Invalid measured startup seed')
    expected={'disc_sha256':config['disc']['iso_sha256'],'module_sha256':config['module']['sha256'],
              'base':config['module']['base'],'entry':config['module']['entry'],
              'ppsspp_revision':config['evidence']['ppsspp_revision']}
    if any(seed.get(key)!=value for key,value in expected.items()):raise ValueError('Startup seed title identity mismatch')
    registers=seed['registers'];names=['r'+str(i) for i in range(1,32)]+['hi','lo']
    if set(registers)!=set(names) or any(type(registers[n]) is not int or not 0<=registers[n]<=0xffffffff for n in names):raise ValueError('Invalid measured registers')
    return '# init '+' '.join(name+'=0x'+format(registers[name],'08x') for name in names)

def prepare_inputs(image,root=ROOT,bridge=None):
    root=Path(root).resolve();image=Path(image).resolve(strict=True)
    config=tomllib.loads((root/'config/lordofapocalypse.toml').read_text())
    expected=config['disc']
    if image.stat().st_size!=expected['iso_size'] or file_hash(image)!=expected['iso_sha256']:raise ValueError('Wrong ISO: requires unmodified NPJH50503 Japan, disc 1.01')
    seed=json.loads((root/'config/startup-registers.json').read_text());init=boot_seed(config,seed)
    spec=importlib.util.spec_from_file_location('local_disc_survey',root/'tools/survey-disc.py')
    survey=importlib.util.module_from_spec(spec);spec.loader.exec_module(survey)
    bridge=Path(bridge or root/'private/tools/decrypt-build/prx-decrypt.dll').resolve(strict=True)
    modules=[('PSP_GAME/SYSDIR/EBOOT.BIN',config['module']),
             ('PSP_GAME/USRDIR/UPDATA/MODULE/LIBFONT.PRX',config['dynamic_modules']['libfont'])]
    # Validate/decrypt everything before promoting any game input.
    prepared=[]
    with image.open('rb') as stream:
        iso=survey.ISO(stream);files=iso.files();sfo=files['PSP_GAME/PARAM.SFO']
        metadata=survey.sfo(iso.read(sfo['lba']*survey.SECTOR,sfo['size']))
        if (metadata['DISC_ID'],metadata['DISC_VERSION'],metadata['APP_VER'])!=(expected['id'],expected['version'],expected['app_version']):raise ValueError('Disc metadata mismatch')
        for name,module in modules:
            item=files[name];raw=iso.read(item['lba']*survey.SECTOR,item['size'])
            if hashlib.sha1(raw).hexdigest()!=expected['files'][name]:raise ValueError('Encrypted module identity mismatch: '+name)
            plain=decrypt_module(raw,bridge)
            if hashlib.sha256(plain).hexdigest()!=module['sha256']:raise ValueError('Decrypted module identity mismatch: '+name)
            prepared.extend([('private/disc/'+name,raw),(module['file'],plain)])
    from graphics_settings import preference_lock
    with preference_lock(root/'private/local-build/setup.lock'):
        for name,raw in prepared:
            path=private_path(root,name)
            if path.exists() and path.read_bytes()!=raw:raise ValueError('Existing local input differs: '+name)
        prefix=private_path(root,'private/oracle-prefix/entry-prefix.trace')
        if prefix.exists():
            existing=[line for line in prefix.read_text().splitlines() if line.startswith('# init ')]
            if existing!=[init]:raise ValueError('Existing startup registers differ')
        else:
            prepared.append(('private/oracle-prefix/entry-prefix.trace',('# Local startup register seed; measured from pinned PPSSPP.\n# No instruction trace or new validation is claimed.\n'+init+'\n').encode()))
        outputs=[]
        for name,raw in prepared:
            install_exact(root,name,raw);outputs.append(dict(path=name,size=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
        if file_hash(image)!=expected['iso_sha256']:raise ValueError('Original ISO changed during preparation')
        report=dict(schema=1,state='INPUTS_VERIFIED',disc_sha256=expected['iso_sha256'],original_ISO_unchanged=True,
                    outputs=outputs,native_compilation_complete=False,english_prepared=False,HD_prepared=False,ready_to_play=False)
        destination=private_path(root,'private/local-build/inputs.json');destination.parent.mkdir(parents=True,exist_ok=True)
        destination.write_text(json.dumps(report,indent=2)+'\n')
        return report

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--image',type=Path,required=True)
    parser.add_argument('--build-native',action='store_true');parser.add_argument('--jobs',type=int,choices=range(1,9),default=4)
    args=parser.parse_args();report=prepare_inputs(args.image)
    if args.build_native:
        for stage in ('generate','build'):
            subprocess.run([sys.executable,str(ROOT/'tools/title.py'),stage,'--profile','release','--jobs',str(args.jobs)],check=True)
        import title
        title.verify_launch_inputs('release')
        report.update(state='NATIVE_COMPILED',native_compilation_complete=True)
        (ROOT/'private/local-build/inputs.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
