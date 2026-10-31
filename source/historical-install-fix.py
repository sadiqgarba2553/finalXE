"""Assemble an EFI-only USB/backlight/host-audio trial from working HP-DAILY."""
import copy
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import time

KIT=Path('/Volumes/MACOS_BOOT/HP-Fix')
BASE=Path('/Volumes/MACOS_BOOT/EFI/HP-DAILY')
DEST=BASE.parent/'HP-FIX'
PY='/Library/Developer/CommandLineTools/usr/bin/python3'
NEW=['USBMapHP8BDF.kext','AppleALC.kext','SimpleHDA.kext']


def run(args):
    print('$ '+' '.join(map(str,args)),flush=True)
    subprocess.run(list(map(str,args)),check=True,timeout=180)


def verify(base,files):
    for name,digest in files.items():
        if hashlib.sha256((base/name).read_bytes()).hexdigest()!=digest:
            raise RuntimeError('File changed: '+name)


def make_config(base):
    config=copy.deepcopy(base)
    entries=config['Kernel']['Add']
    for name in ['NootedGreenHP.kext','AirportItlwmHP.kext']:
        if not any(e['BundlePath']==name and e['Enabled'] for e in entries):
            raise RuntimeError('Working graphics and native Wi-Fi must be enabled.')
    if any(e['BundlePath'] in NEW for e in entries):raise RuntimeError('A repair component already exists.')
    for name in NEW:
        entries.append({'Arch':'Any' if name.startswith('USBMap') else 'x86_64',
          'BundlePath':name,'Comment':'HP repair candidate: '+name,'Enabled':True,
          'ExecutablePath':'' if name.startswith('USBMap') else 'Contents/MacOS/'+name[:-5],
          'PlistPath':'Contents/Info.plist','MinKernel':'25.6.0','MaxKernel':'25.6.99'})
    if any(e['Path']=='SSDT-HP-PNLF.aml' for e in config['ACPI']['Add']):raise RuntimeError('PNLF trial already exists.')
    config['ACPI']['Add'].append({'Comment':'HP GFX0 declarative PNLF; no MMIO writes',
                                'Enabled':True,'Path':'SSDT-HP-PNLF.aml'})
    audio=config['DeviceProperties']['Add'].setdefault('PciRoot(0x0)/Pci(0x1F,0x3)',{})
    if 'layout-id' in audio or 'alc-layout-id' in audio:raise RuntimeError('Existing audio layout needs review.')
    # AppleALC explicitly supports 51CA. Its HP ALC245 layout13 is a trial
    # codec route, not a qualification of the Envy's smart speaker amplifiers.
    audio['layout-id']=(13).to_bytes(4,'little')
    audio['class-code']=bytes.fromhex('00030400')
    return config


def main():
    if os.geteuid()==0:raise RuntimeError('Run without sudo.')
    if subprocess.check_output(['/usr/bin/sw_vers','-buildVersion'],text=True).strip()!='25G332':
        raise RuntimeError('This candidate targets 25G332.')
    if DEST.exists():raise RuntimeError('HP-FIX exists already; review it before replacing it.')
    manifest=json.loads((KIT/'inputs.json').read_text())
    verify(KIT,manifest['files']);verify(BASE,manifest['baseProfile'])
    work=Path.home()/'HP-Extras-Drivers'/time.strftime('fix-%Y%m%d-%H%M%S');work.mkdir(parents=True)
    candidate=work/'HP-FIX';shutil.copytree(BASE,candidate)
    for name in NEW:
        target=candidate/'Kexts'/name;shutil.copytree(KIT/'payload'/name,target)
        if not name.startswith('USBMap'):
            # AppleALC ships an i386 MH_OBJECT slice that modern codesign
            # rejects. This profile loads only x86_64; thin the staging copy.
            executable=target/'Contents/MacOS'/name[:-5]
            architectures=subprocess.check_output(
                ['/usr/bin/lipo','-archs',str(executable)],text=True).split()
            if 'x86_64' not in architectures:
                raise RuntimeError('Missing x86_64 driver: '+name)
            if architectures!=['x86_64']:
                thin=executable.with_name(executable.name+'.x86_64')
                run(['/usr/bin/lipo',executable,'-thin','x86_64','-output',thin])
                thin.replace(executable)
            run(['/usr/bin/codesign','--force','--deep','--sign','-',target])
            run(['/usr/bin/codesign','--verify','--deep','--strict',target])
    shutil.copy2(KIT/'SSDT-HP-PNLF.aml',candidate/'ACPI/SSDT-HP-PNLF.aml')
    config=make_config(plistlib.loads((BASE/'config.plist').read_bytes()))
    (candidate/'config.plist').write_bytes(plistlib.dumps(config,sort_keys=False))
    validator=work/'ocvalidate';shutil.copy2(KIT/'ocvalidate',validator);os.chmod(validator,0o755)
    run([validator,candidate/'config.plist'])
    hashes={p.relative_to(candidate).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for p in candidate.rglob('*') if p.is_file()}
    try:
        shutil.copytree(candidate,DEST);verify(DEST,hashes)
        # The existing user report agent reads this file on the next login.
        support=Path.home()/'HP-Extras-Drivers'
        shutil.copy2(KIT/'extras-report.py',support/'extras-report.py')
        verify(BASE,manifest['baseProfile'])
    except Exception:
        if DEST.exists():
            if DEST.resolve().parent!=BASE.parent.resolve():raise RuntimeError('Unexpected profile destination.')
            shutil.move(str(DEST),str(work/'incomplete-EFI'))
        raise
    (KIT/'hp-fix-hashes.json').write_text(json.dumps(hashes,indent=2)+'\n')
    (KIT/'result.json').write_text(json.dumps({'profileReady':True,'profile':'EFI/HP-FIX',
        'bluetooth':'USB map preserves HS10; cold-boot test pending',
        'backlight':'Declarative PNLF added; brightness test pending',
        'audio':'AppleALC + SimpleHDA, HP ALC245 layout13 trial; no Cirrus amplifier driver',
        'hardwareTested':False,'work':str(work)},indent=2)+'\n')
    print('READY: shut down completely, then power on through EFI/HP-FIX/OpenCore.efi.',flush=True)
    print('Try Bluetooth, brightness keys and headphones. Speaker amplifiers are not enabled by this trial.',flush=True)


if __name__=='__main__':
    try:main()
    except Exception as error:print('STOPPED:',error,flush=True);raise SystemExit(1)
