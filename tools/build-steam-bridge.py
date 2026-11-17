"""Build the optional Spacewar development adapter against an official local SDK.

This command never downloads or accepts SDK terms. The user supplies the SDK.
Only original adapter source belongs in Git; all SDK files remain private.
"""
import argparse,hashlib,json,os,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DEFAULT=ROOT/'private/tools/steamworks-sdk'
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--sdk',type=Path,default=DEFAULT);parser.add_argument('--check',action='store_true');args=parser.parse_args()
    sdk=args.sdk.resolve()
    if not (sdk/'public/steam/steam_api.h').is_file() and (sdk/'sdk/public/steam/steam_api.h').is_file():sdk=sdk/'sdk'
    required=['public/steam/steam_api.h','public/steam/isteamnetworkingmessages.h','redistributable_bin/win64/steam_api64.dll','redistributable_bin/win64/steam_api64.lib']
    missing=[name for name in required if not (sdk/name).is_file()]
    folder=ROOT/'private/steam-test';folder.mkdir(exist_ok=True)
    status=dict(scope='official-local-SDK-preflight-not-a-Steam-connection',sdk=str(sdk),app_id=480,ready=not missing,missing=missing)
    (folder/'sdk-check.json').write_text(json.dumps(status,indent=2)+'\n')
    if args.check or missing:
        print(json.dumps(status,indent=2))
        if missing:print('Review Valve SDK terms and put the official SDK in private/tools/steamworks-sdk/. No replacement DLLs are used.')
        return int(bool(missing))
    compiler=ROOT/'private/toolchain/prerequisites/msys64/ucrt64/bin/g++.exe'
    env=dict(os.environ);env['PATH']=str(compiler.parent)+os.pathsep+env['PATH']
    source=ROOT/'tools/steam_bridge.cpp';dll=folder/'loa_steam_bridge.dll'
    command=[str(compiler),'-std=c++17','-O2','-Wall','-Wextra','-shared','-static-libgcc','-static-libstdc++',
             '-I'+str(sdk/'public'),str(source),str(sdk/'redistributable_bin/win64/steam_api64.lib'),'-o',str(dll)]
    build=subprocess.run(command,env=env,capture_output=True,text=True);(folder/'build.log').write_text(build.stdout+build.stderr)
    if build.returncode:print(build.stderr);return build.returncode
    api=folder/'steam_api64.dll';shutil.copy2(sdk/'redistributable_bin/win64/steam_api64.dll',api)
    fingerprints={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (source,ROOT/'tools/steam_flat.h',dll,api)}
    headers={p.relative_to(sdk/'public').as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((sdk/'public/steam').glob('*.h'))}
    (folder/'bridge.json').write_text(json.dumps(dict(app_id=480,scope='development-test-only',sdk_headers_sha256=headers,sha256=fingerprints),indent=2)+'\n')
    print('Built standalone Steam test adapter. No Steam session or game co-op is implied.');return 0
if __name__=='__main__':raise SystemExit(main())
