"""Read/save the shared launcher and F1 preferences. No game or networking starts."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import graphics_settings as settings
ROOT=Path(__file__).resolve().parents[1]

def snapshot(path=settings.SETTINGS):
    with settings.preference_lock(path):
        value=settings.load(path);token=settings.fingerprint(path)
    return value,token

def controls_reference(profile):
    names={'south':'A','east':'B','west':'X','north':'Y','left_shoulder':'LB','right_shoulder':'RB',
           'left_trigger':'LT','right_trigger':'RT','start':'Menu','back':'View','none':'Unbound'}
    bindings={row['control']:row for row in profile['psp_bindings']}
    def binding(key):
        row=bindings.get(key,{})
        return ' / '.join(names.get(row[k],'Custom binding') for k in ('primary','secondary') if row.get(k) and row[k]!='none') or 'Unbound'
    camera=all('right' in bindings.get(key,{}).get('secondary','') for key in ('up','down','left','right'))
    axis=profile.get('calibration',{})
    normal=axis.get('analog_x',{}).get('host_axis')=='leftx' and axis.get('analog_y',{}).get('host_axis')=='lefty'
    return '\n'.join(['XBOX CONTROLLER',
        'Move                 '+('Left stick' if normal else 'Custom analog mapping'),
        'Camera / menus       '+('Right stick + D-pad' if camera else 'See in-game Controls'),
        'Cross / Circle       '+binding('cross')+' / '+binding('circle'),
        'Square / Triangle    '+binding('square')+' / '+binding('triangle'),
        'L / R shoulder       '+binding('ltrigger')+' / '+binding('rtrigger'),
        'Start / Select       '+binding('start')+' / '+binding('select'),
        '', 'F1 or Escape opens the in-game menu.',
        'The in-game Controls page shows the full active bindings.'])

def emit(path):
    value,token=snapshot(path)
    print('LOA_SETTINGS 1',token,*settings.menu_codes(value))
    profile=json.loads((ROOT/'config/controller-camera.json').read_text(encoding='utf-8'))
    print(controls_reference(profile))

def main():
    parser=argparse.ArgumentParser(description=__doc__);group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--read',action='store_true');group.add_argument('--save',nargs=len(settings.OPTIONS),type=int)
    parser.add_argument('--expected');parser.add_argument('--preferences',type=Path,default=settings.SETTINGS)
    args=parser.parse_args();path=args.preferences.resolve()
    if not path.is_relative_to(ROOT/'private') or path.suffix!='.json':raise ValueError('Keep preferences in private storage.')
    if args.save is not None:
        if args.expected is None:raise ValueError('Load the current settings before saving.')
        settings.save(settings.from_menu(args.save),path,expected=args.expected)
    emit(path)

if __name__=='__main__':
    try:main()
    except (ValueError,OSError,KeyError) as error:print(str(error),file=sys.stderr);raise SystemExit(1)
