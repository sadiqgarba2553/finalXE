"""Install only the completely built HP stack; do not activate it before reboot."""
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import tempfile
import time

BASE=Path('/Volumes/MACOS_BOOT')
KIT=BASE/'Davghz-Port'
PROFILE=BASE/'EFI/HP-PORT'


def run(args):
    print('$ '+' '.join(map(str,args)),flush=True)
    subprocess.run(list(map(str,args)),check=True,timeout=300)


def main(payload):
    if os.geteuid()!=0:raise RuntimeError('Installation requires sudo.')
    args=subprocess.check_output(['/usr/sbin/sysctl','-n','kern.bootargs'],text=True).split()
    if '-nvoff' not in args:raise RuntimeError('Install from the parked NMX-OFF profile.')
    if subprocess.check_output(['/usr/sbin/sysctl','-n','kern.uuid'],text=True).strip()!='28267FD5-3E1E-3686-8A1C-E73E2466FCFB':
        raise RuntimeError('The running kernel differs from the qualified port.')
    payload=payload.resolve()
    if payload.name!='payload' or payload.parent.parent.name!='HP-Davghz-Port':raise RuntimeError('Unexpected build output path.')
    config_path=PROFILE/'config.plist';original_config=config_path.read_bytes()
    config=plistlib.loads(original_config)
    entries=[e for e in config['Kernel']['Add'] if e['BundlePath']=='NootedGreenHP.kext']
    if len(entries)!=1 or entries[0]['Enabled']:raise RuntimeError('Expected one not-yet-enabled HP-PORT entry.')
    efi_plugin=PROFILE/'Kexts/NootedGreenHP.kext'
    if efi_plugin.exists():raise RuntimeError('A previous HP-PORT binary exists; review before replacing it.')
    for name in ['NootedGreenHP.kext','HookCase.kext','AppleIntelTGLGraphics.kext','AppleIntelTGLGraphicsFramebuffer.kext']:
        source=payload/('EFI' if name.startswith('Nooted') else 'Extensions')/name
        run(['/usr/bin/codesign','--verify','--strict',source])
    units=[]
    for folder,target in [('Extensions','/Library/Extensions'),('GPUBundles','/Library/GPUBundles'),
                          ('SystemCaches','/System/Library/Caches'),('LaunchDaemons','/Library/LaunchDaemons')]:
        units += [(p,Path(target)/p.name) for p in (payload/folder).iterdir()]
    units.append((payload/'Support',Path('/Library/Application Support/HP-Davghz-Port/tools')))
    old=[Path('/Library/Extensions')/(n+'.kext') for n in
         ['NMXGPU','NMXAccel','NVRMAGDC','NMIntelFB','WhateverXe','AppleIntelTGLCompat','NootedGreen','NootedGreenHP']]
    old += [Path('/Library/GPUBundles')/n for n in ['NVMTLDriver.bundle','nvmtl','nvmtl-allow.txt',
             'XeCompilerAdapter.bundle','XeMetalCompiler.bundle','XeOpenCL']]
    for folder in ['/Library/LaunchDaemons','/Library/LaunchAgents']:
        old += list(Path(folder).glob('*nullmoth*.plist'))
    old.append(Path('/Library/LaunchDaemons/local.hp.nmx-full-report.plist'))
    state=Path('/Library/Application Support/HP-Davghz-Port')/time.strftime('install-%Y%m%d-%H%M%S')
    state.mkdir(parents=True,exist_ok=False)
    actions=[];plugin_copy_started=False
    def replace(destination,source=None):
        if destination.is_symlink():raise RuntimeError('Unexpected destination symlink: '+str(destination))
        saved=state/'previous'/destination.relative_to('/')
        action={'path':str(destination),'saved':None,'installed':False};actions.append(action)
        if destination.exists():
            saved.parent.mkdir(parents=True,exist_ok=True);os.replace(destination,saved);action['saved']=str(saved)
        if source is not None:
            destination.parent.mkdir(parents=True,exist_ok=True)
            action['installed']=True
            if source.is_dir():shutil.copytree(source,destination,symlinks=True)
            else:shutil.copy2(source,destination)
            for p in [destination]+(list(destination.rglob('*')) if destination.is_dir() else []):
                if not p.is_symlink():
                    os.chown(p,0,0)
                    os.chmod(p,0o755 if p.is_dir() or (p.stat().st_mode & 0o111 and p.suffix!='.plist') else 0o644)
        (state/'changes.json').write_text(json.dumps(actions,indent=2)+'\n')
    try:
        for destination in dict.fromkeys(old):
            if destination.exists():replace(destination)
        for source,destination in units:replace(destination,source)
        cache=Path('/Library/KernelCollections/AuxiliaryKernelExtensions.kc')
        temporary=Path(tempfile.mkdtemp(prefix='.hp-port-',dir=str(cache.parent)))
        new_cache=temporary/cache.name
        command=['/usr/bin/kmutil','create','-n','aux','-x','-z','-V','release',
                 '-r','/Library/Extensions','--allow-missing-kdk']
        for p in sorted(Path('/Library/Extensions').glob('*.kext')):command+=['-p',str(p)]
        command+=['-B','/System/Library/KernelCollections/BootKernelExtensions.kc',
                  '-S','/System/Library/KernelCollections/SystemKernelExtensions.kc',
                  '-A',str(new_cache),'--no-authentication']
        run(command)
        if not new_cache.exists() or new_cache.stat().st_size<4096:raise RuntimeError('No complete auxiliary collection produced.')
        os.chmod(new_cache,0o644);replace(cache,new_cache)
        new_cache.unlink();temporary.rmdir()
        plugin_copy_started=True
        shutil.copytree(payload/'EFI/NootedGreenHP.kext',efi_plugin)
        entries[0]['Enabled']=True
        entries[0]['Comment']='HP 8BDF port 1.0.13: exact 25G332 kernel and qualified native images'
        config_path.write_bytes(plistlib.dumps(config,sort_keys=False))
        validator=state/'ocvalidate';shutil.copy2(KIT/'ocvalidate',validator);os.chmod(validator,0o755)
        run([validator,config_path])
        hashes={p.relative_to(PROFILE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                for p in PROFILE.rglob('*') if p.is_file()}
        (KIT/'hp-port-installed-hashes.json').write_text(json.dumps(hashes,indent=2)+'\n')
    except Exception:
        config_path.write_bytes(original_config)
        if plugin_copy_started and efi_plugin.exists():
            assert efi_plugin.resolve().parent==(PROFILE/'Kexts').resolve()
            shutil.move(str(efi_plugin),str(state/'failed-efi-plugin'))
        for action in reversed(actions):
            destination=Path(action['path'])
            if action['installed'] and destination.exists():
                failed=state/'failed'/destination.relative_to('/');failed.parent.mkdir(parents=True,exist_ok=True)
                os.replace(destination,failed)
            if action['saved']:os.replace(action['saved'],destination)
        raise
    (KIT/'installation.json').write_text(json.dumps({'installed':True,'version':'1.0.13',
                                                  'target':'25G332','hardwareValidated':False,
                                                  'previousFiles':str(state/'previous')},indent=2)+'\n')
    print('Complete HP stack installed and HP-PORT enabled. No live GPU takeover attempted.',flush=True)


if __name__=='__main__':
    try:main(Path(sys.argv[1]))
    except Exception as error:print('STOPPED:',error,flush=True);raise SystemExit(1)
