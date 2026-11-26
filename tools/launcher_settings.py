"""Read/save the shared launcher and F1 preferences. No game or networking starts."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import graphics_settings as settings
import setup_resources
import controller_settings
ROOT=Path(__file__).resolve().parents[1]

def snapshot(path=settings.SETTINGS):
    with settings.preference_lock(path):
        value=settings.load(path);token=settings.fingerprint(path)
    return value,token

def controls_reference(profile):
    names={'south':'Cross/A','east':'Circle/B','west':'Square/X','north':'Triangle/Y',
           'left_shoulder':'L1/LB','right_shoulder':'R1/RB','left_trigger':'L2/LT','right_trigger':'R2/RT',
           'start':'Options/Menu','back':'Create/View','none':'Unbound'}
    bindings={row['control']:row for row in profile['psp_bindings']}
    def binding(key):
        row=bindings.get(key,{})
        return '+'.join(names.get(row[k],'Custom binding') for k in ('primary','secondary') if row.get(k) and row[k]!='none') or 'Unbound'
    camera=all('right' in bindings.get(key,{}).get('secondary','') for key in ('up','down','left','right'))
    axis=profile.get('calibration',{})
    normal=axis.get('analog_x',{}).get('host_axis')=='leftx' and axis.get('analog_y',{}).get('host_axis')=='lefty'
    return '\n'.join(['PLAYSTATION / XBOX BUTTON LABELS',
        'Move                 '+('Left stick' if normal else 'Custom analog mapping'),
        'Camera / menus       '+('Right stick + D-pad' if camera else 'See in-game Controls'),
        'Cross / Circle       '+binding('cross')+' / '+binding('circle'),
        'Square / Triangle    '+binding('square')+' / '+binding('triangle'),
        'L / R shoulder       '+binding('ltrigger')+'; '+binding('rtrigger'),
        'Start / Select       '+binding('start')+' / '+binding('select'),
        '', 'F1 or Escape opens the in-game menu.',
        'DualSense: USB / Bluetooth. PS4 Share = Create.'])

def emit(path, include_build=False):
    with settings.preference_lock(path):
        value,build = settings.read_preferences(path)
        token = settings.fingerprint(path)
    print('LOA_SETTINGS 1',token,*settings.menu_codes(value))
    if include_build:print('LOA_BUILD',*setup_resources.codes(build))
    profile=controller_settings.profile()
    print(controls_reference(profile))

def main():
    parser=argparse.ArgumentParser(description=__doc__);group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--read',action='store_true');group.add_argument('--save',nargs=len(settings.OPTIONS),type=int)
    group.add_argument('--edit-controls',action='store_true')
    parser.add_argument('--expected');parser.add_argument('--preferences',type=Path,default=settings.SETTINGS)
    parser.add_argument('--include-build',action='store_true')
    parser.add_argument('--build-codes',type=int,nargs=len(setup_resources.OPTIONS))
    args=parser.parse_args();path=args.preferences.resolve()
    if not path.is_relative_to(ROOT/'private') or path.suffix!='.json':raise ValueError('Keep preferences in private storage.')
    if args.edit_controls:controller_settings.edit()
    if args.save is not None:
        if args.expected is None:raise ValueError('Load the current settings before saving.')
        build = setup_resources.from_codes(args.build_codes) if args.build_codes is not None else None
        settings.save(settings.from_menu(args.save),path,expected=args.expected,setup=build)
    elif args.build_codes is not None:
        parser.error('--build-codes requires --save')
    emit(path,args.include_build)

if __name__=='__main__':
    try:main()
    except (ValueError,OSError,KeyError,RuntimeError) as error:print(str(error),file=sys.stderr);raise SystemExit(1)
