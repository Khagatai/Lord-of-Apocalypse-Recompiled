"""Personal gamepad bindings; the default profile and host-menu keys stay separate."""
import hashlib,json,os,subprocess
from pathlib import Path
import graphics_settings
from settings_bridge import atomic_json

ROOT=Path(__file__).resolve().parents[1]
SETTINGS=ROOT/'private/settings/controller.json'
PROFILE=ROOT/'private/settings/controller-profile.json'
CONTROLS=('cross','circle','square','triangle','ltrigger','rtrigger','start','select','up','down','left','right')
LABELS=('Cross','Circle','Square','Triangle','L shoulder','R shoulder','Start','Select','D-pad up','D-pad down','D-pad left','D-pad right')
SOURCES=('none','south','east','west','north','back','start','left_stick','right_stick','left_shoulder','right_shoulder',
         'dpad_up','dpad_down','dpad_left','dpad_right','left_trigger','right_trigger',
         '-righty@12000','+righty@12000','-rightx@12000','+rightx@12000')
SOURCE_LABELS=('Unbound','Cross / A','Circle / B','Square / X','Triangle / Y','Create / View','Options / Menu',
               'L3 / LS click','R3 / RS click','L1 / LB','R1 / RB','D-pad up','D-pad down','D-pad left','D-pad right',
               'L2 / LT','R2 / RT','Right stick up','Right stick down','Right stick left','Right stick right')
BINDING_COUNT=len(CONTROLS)*2
CAMERA_MODES=('Original PSP','Smooth 360 camera (experimental)')
CAMERA_SPEEDS=('0.5x','0.75x','1x','1.5x','2x')
COUNT=BINDING_COUNT+2

def defaults():
    base=json.loads((ROOT/'config/controller-camera.json').read_text(encoding='utf-8'))
    rows={row['control']:row for row in base['psp_bindings']}
    return [SOURCES.index(rows[key].get(slot,'none')) for key in CONTROLS for slot in ('primary','secondary')]+[0,2]

def validate(codes):
    lengths=[len(SOURCES)]*BINDING_COUNT+[len(CAMERA_MODES),len(CAMERA_SPEEDS)]
    if not isinstance(codes,list) or len(codes)!=COUNT or any(type(n) is not int or not 0<=n<limit for n,limit in zip(codes,lengths)):
        raise ValueError('Invalid controller binding choices')
    owners={}
    for i,code in enumerate(codes[:BINDING_COUNT]):
        if code and code in owners and owners[code]!=i//2:raise ValueError('A controller input cannot drive two different PSP controls. Reassign the input in the controller editor.')
        if code:owners[code]=i//2
    return list(codes)

def assign(codes,index,source):
    value=validate(codes)
    if type(index) is not int or not 0<=index<BINDING_COUNT or type(source) is not int or not 0<=source<len(SOURCES):raise ValueError('Invalid controller assignment')
    for i,old in enumerate(value[:BINDING_COUNT]):
        if source and i!=index and old==source:value[i]=0
    value[index]=source
    return validate(value)

def edited_codes(before,requested):
    if not isinstance(requested,list) or len(requested)!=COUNT or any(type(n) is not int or not 0<=n<len(SOURCES) for n in requested[:BINDING_COUNT]):raise ValueError('Invalid controller editor result')
    value=validate(before)
    for i,source in enumerate(requested[:BINDING_COUNT]):
        if source!=before[i]:value=assign(value,i,source)
    value[BINDING_COUNT:]=requested[BINDING_COUNT:]
    return validate(value)

def load(path=SETTINGS):
    if not path.exists():return defaults()
    value=json.loads(path.read_text(encoding='utf-8'))
    if set(value)!={'schema','codes'} or value['schema']!=1:raise ValueError('Unsupported controller settings')
    codes=value['codes']
    if isinstance(codes,list) and len(codes)==BINDING_COUNT:codes=[*codes,0,2]
    return validate(codes)

def fingerprint(path=SETTINGS):return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else 'missing'

def profile(codes=None):
    value=json.loads((ROOT/'config/controller-camera.json').read_text(encoding='utf-8'))
    codes=validate(load() if codes is None else codes)
    rows={row['control']:row for row in value['psp_bindings']}
    for i,key in enumerate(CONTROLS):
        for j,slot in enumerate(('primary','secondary')):rows[key][slot]=SOURCES[codes[2*i+j]]
    # Keep direction bindings for the game's target / weak-point selection.
    # The title runtime suppresses stick-driven D-pad steps only in free camera.
    return value

def save(codes,path=SETTINGS,profile_path=PROFILE,expected=None):
    codes=validate(codes)
    with graphics_settings.preference_lock(path):
        if expected is not None and expected!=fingerprint(path):raise ValueError('Controller settings changed elsewhere. Reload before saving.')
        path.parent.mkdir(parents=True,exist_ok=True);profile_path.parent.mkdir(parents=True,exist_ok=True)
        atomic_json(profile_path,profile(codes));atomic_json(path,dict(schema=1,codes=codes))
    return codes

def prepare():
    with graphics_settings.preference_lock(SETTINGS):
        PROFILE.parent.mkdir(parents=True,exist_ok=True);codes=load()
        value=profile(codes)
        if not PROFILE.exists() or json.loads(PROFILE.read_text())!=value:atomic_json(PROFILE,value)
    return codes

def edit():
    with graphics_settings.preference_lock(SETTINGS):codes=load();token=fingerprint()
    data=dict(labels=LABELS,sources=SOURCE_LABELS,codes=codes,defaults=defaults(),camera_modes=CAMERA_MODES,camera_speeds=CAMERA_SPEEDS)
    # Fixed script; all user data arrives as JSON on stdin, not shell syntax.
    script=r'''
[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false)
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$data=ConvertFrom-Json ([Console]::In.ReadToEnd())
$form=[Windows.Forms.Form]::new();$form.Text='Controller bindings';$form.ClientSize=[Drawing.Size]::new(660,630)
$form.StartPosition='CenterScreen';$form.FormBorderStyle='FixedDialog';$form.MaximizeBox=$false;$form.MinimizeBox=$false
$form.BackColor=[Drawing.Color]::FromArgb(13,18,26);$form.ForeColor=[Drawing.Color]::FromArgb(238,242,247)
$form.Font=[Drawing.Font]::new('Segoe UI',10);$form.AutoScaleMode='Dpi'
function Label($text,$x,$y,$w){$l=[Windows.Forms.Label]::new();$l.Text=$text;$l.SetBounds($x,$y,$w,28);$form.Controls.Add($l)}
Label 'Choose PlayStation / Xbox inputs for each PSP control.' 20 15 620
Label 'PSP control' 20 53 130;Label 'Primary input' 150 53 235;Label 'Secondary input' 395 53 235
$combos=@()
for($i=0;$i -lt 12;$i++){
 Label $data.labels[$i] 20 (86+$i*30) 125
 for($j=0;$j -lt 2;$j++){
  $c=[Windows.Forms.ComboBox]::new();$c.DropDownStyle='DropDownList';$c.SetBounds((150+$j*245),(82+$i*30),235,28)
  foreach($s in $data.sources){[void]$c.Items.Add($s)};$c.SelectedIndex=$data.codes[2*$i+$j];$form.Controls.Add($c);$combos+=$c
 }
}
Label 'Camera mode' 20 455 125;Label 'Rotation speed' 20 490 125
foreach($entry in @(@($data.camera_modes,24,450),@($data.camera_speeds,25,485))){
 $c=[Windows.Forms.ComboBox]::new();$c.DropDownStyle='DropDownList';$c.SetBounds(150,$entry[2],485,28)
 foreach($s in $entry[0]){[void]$c.Items.Add($s)};$c.SelectedIndex=$data.codes[$entry[1]];$form.Controls.Add($c);$combos+=$c
}
Label 'Saving a used input unbinds its old slot. Left stick and host-menu keys stay active.' 20 530 625
Label 'Right stick: smooth free camera; original target switching while locked on.' 20 557 625
$reset=[Windows.Forms.Button]::new();$reset.Text='Restore defaults';$reset.SetBounds(20,590,155,30)
$reset.Add_Click({for($i=0;$i -lt $combos.Count;$i++){$combos[$i].SelectedIndex=$data.defaults[$i]}});$form.Controls.Add($reset)
$cancel=[Windows.Forms.Button]::new();$cancel.Text='Cancel';$cancel.SetBounds(430,590,95,30);$cancel.DialogResult='Cancel';$form.Controls.Add($cancel);$form.CancelButton=$cancel
$save=[Windows.Forms.Button]::new();$save.Text='Save';$save.SetBounds(540,590,95,30);$save.DialogResult='OK';$form.Controls.Add($save);$form.AcceptButton=$save
if($form.ShowDialog() -eq [Windows.Forms.DialogResult]::OK){$codes=@($combos | ForEach-Object {$_.SelectedIndex});[Console]::Write((ConvertTo-Json -Compress -InputObject $codes))}
$form.Dispose()
'''
    powershell=Path(os.environ.get('SystemRoot','C:/Windows'))/'System32/WindowsPowerShell/v1.0/powershell.exe'
    result=subprocess.run([str(powershell),'-NoProfile','-STA','-Command',script],input=json.dumps(data),capture_output=True,text=True,encoding='utf-8')
    if result.returncode:raise RuntimeError('Controller editor failed: '+result.stderr.strip())
    if result.stdout.strip():save(edited_codes(codes,json.loads(result.stdout)),expected=token)

class Bridge:
    def __init__(self,folder,preferences=SETTINGS,profile_path=PROFILE):
        self.folder=Path(folder);self.sequence=0;self.preferences=preferences;self.profile_path=profile_path
    def environment(self):
        with graphics_settings.preference_lock(self.preferences):
            codes=load(self.preferences);value=profile(codes);self.profile_path.parent.mkdir(parents=True,exist_ok=True)
            if not self.profile_path.exists() or json.loads(self.profile_path.read_text())!=value:atomic_json(self.profile_path,value)
        return dict(NK_INPUT_PROFILE=str(self.profile_path),LOA_CONTROLLER_CODES=' '.join(map(str,codes)),LOA_CAMERA_MODE='smooth' if codes[BINDING_COUNT] else 'original',LOA_CAMERA_SPEED=str(codes[BINDING_COUNT+1]))
    def poll(self):
        path=self.folder/'controller-request.json'
        if not path.is_file():return
        try:
            value=json.loads(path.read_text());seq=value.get('sequence')
            if type(seq) is not int or not 1<=seq<=1000000:raise ValueError('Invalid controller sequence')
            if seq<=self.sequence:return
            self.sequence=seq
            if set(value)!={'sequence','codes'}:raise ValueError('Invalid controller request')
            save(value['codes'],self.preferences,self.profile_path);atomic_json(self.folder/'controller-ack.json',dict(sequence=seq,ok=True))
        except (OSError,ValueError,TypeError,KeyError) as error:
            (self.folder/'controller-error.txt').write_text(str(error)+'\n')
            atomic_json(self.folder/'controller-ack.json',dict(sequence=self.sequence,ok=False))
