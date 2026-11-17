"""Register verified local mip experiments and isolate their saves/preferences."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import mip_runtime_patch
import save_storage
import texture_pack


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def private_path(path):
    path=Path(path).resolve()
    if not path.is_relative_to(ROOT/'private'):
        raise ValueError('Mip preview evidence must stay under private/')
    return path


def check_reports(build,gpu,native,negative):
    metadata=json.loads((build/'build.json').read_text())
    executable=build/'mip-prototype.exe'
    if digest(executable)!=metadata['prototype_executable_sha256'] or metadata['selftest_returncode']!=0:
        raise ValueError('Prototype executable or CPU selftest identity differs')
    gpu_data=json.loads(gpu.read_text());negative_data=json.loads(negative.read_text())
    native_data=json.loads(native.read_text())
    for report,want_negative in ((gpu_data,False),(negative_data,True)):
        if report.get('passed') is not True or report.get('negative_control') is not want_negative or report['source_patch']!=metadata['source_patch']:
            raise ValueError('GPU evidence failed or does not match this prototype source')
    if metadata['source_patch']['upstream_sha256']!=mip_runtime_patch.PINNED_GE_SHA256:
        raise ValueError('Prototype source pin differs')
    legacy_helpers={'mip_chain.c','mip_gpu.c','mip_gpu_selftest.c','mip_runtime_patch.py'}
    if set(metadata['source_patch']['extension_sha256']) not in (legacy_helpers,legacy_helpers|{'sampler_pack.c'}):
        raise ValueError('Prototype helper fingerprint set is incomplete')
    for name,expected in metadata['source_patch']['extension_sha256'].items():
        snapshot=build/name
        source=snapshot if snapshot.is_file() else ROOT/'tools'/name
        if name not in legacy_helpers|{'sampler_pack.c'} or digest(source)!=expected:
            raise ValueError('Prototype helper changed; rebuild and revalidate')
    run=native_data['native'];counts=native_data['mip_texture_counters']
    if run['executable_sha256']!=metadata['prototype_executable_sha256'] or run['returncode']!=0 or run['timed_out']:
        raise ValueError('Native checkpoint did not pass with this executable')
    if not (run['save_fixture_source_unchanged'] and run['font_files_unchanged'] and native_data['preferences_unchanged']):
        raise ValueError('Native checkpoint changed protected source data')
    if counts.get('uploaded',0)<1 or counts.get('bound',0)<1 or counts.get('failed',0):
        raise ValueError('Native checkpoint did not successfully draw authored mip copies')
    return metadata


def register(build,gpu,native,negative,pack=None):
    build,gpu,native,negative=map(private_path,(build,gpu,native,negative))
    check_reports(build,gpu,native,negative)
    report={'scope':'local-mip-preview-evidence','reports':{name:{'path':str(path),'sha256':digest(path)}
            for name,path in (('gpu',gpu),('native',native),('negative',negative))},
            'build_sha256':digest(build/'build.json'),'experimental':True,'full_remaster_complete':False}
    if pack is not None:
        pack=private_path(pack);verified=texture_pack.verify_sample(pack)
        observed=json.loads(native.read_text());counts=observed['mip_texture_counters']
        if not verified.get('mip_chains') or not counts.get('replacement_queued') or counts.get('replacement_rejected') or observed.get('texture_pack_unchanged') is not True or observed.get('texture_pack_manifest_sha256')!=verified['sample_manifest_sha256']:
            raise ValueError('Pack was not validated as a successful unchanged mip replacement pack')
        report['texture_pack']={'folder':str(pack),'manifest_sha256':verified['sample_manifest_sha256']}
    (build/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def verify(build,framework_commit):
    build=private_path(build)
    validation=json.loads((build/'validation.json').read_text())
    if digest(build/'build.json')!=validation['build_sha256']:
        raise ValueError('Registered prototype build metadata changed')
    paths={}
    for name in ('gpu','native','negative'):
        row=validation['reports'][name];path=private_path(row['path'])
        if digest(path)!=row['sha256']:
            raise ValueError('Registered mip preview evidence changed')
        paths[name]=path
    metadata=check_reports(build,paths['gpu'],paths['native'],paths['negative'])
    if metadata['framework_commit']!=framework_commit:
        raise ValueError('Registered prototype framework revision differs')
    if 'texture_pack' in validation:
        pack=validation['texture_pack'];verified=texture_pack.verify_sample(private_path(pack['folder']))
        if verified['sample_manifest_sha256']!=pack['manifest_sha256']:
            raise ValueError('Registered replacement pack changed; rerun native validation')
    return {'executable':str(build/'mip-prototype.exe'),'experimental':True,
            'validation_sha256':digest(build/'validation.json'),'full_remaster_complete':False}


def seed_saves(source,destination):
    source=private_path(source);destination=private_path(destination)
    if destination.exists():return
    destination.parent.mkdir(parents=True,exist_ok=True)
    with save_storage.save_session(source):
        before=save_storage.tree_hashes(source)
        temporary=Path(tempfile.mkdtemp(prefix='remaster-seed-',dir=destination.parent)).resolve()
        if not temporary.is_relative_to(ROOT/'private') or not destination.is_relative_to(ROOT/'private'):
            raise ValueError('Preview save copy escapes private workspace')
        shutil.copytree(source,temporary,dirs_exist_ok=True,ignore=shutil.ignore_patterns('.preview.lock'))
        if save_storage.tree_hashes(temporary)!=before or save_storage.tree_hashes(source)!=before:
            raise RuntimeError('Preview save copy failed verification; source left unchanged')
        os.replace(temporary,destination)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('build','gpu','native','negative'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--pack',type=Path,help='Bind the preview to a successfully tested complete-chain pack')
    args=parser.parse_args()
    print(json.dumps(register(args.build,args.gpu,args.native,args.negative,args.pack),indent=2))
