"""Build AX211 Wi-Fi/brightness support and assemble a separate HP-DAILY EFI."""
import copy
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import struct
import subprocess
import sys
import time
import zipfile

KIT=Path('/Volumes/MACOS_BOOT/HP-Extras')
BASE=Path('/Volumes/MACOS_BOOT/EFI/HP-PORT')
DEST=BASE.parent/'HP-DAILY'
PY='/Library/Developer/CommandLineTools/usr/bin/python3'
GUID='7C436110-AB2A-4BBB-A880-FE41995C9F82'
NEW=['BlueToolFixup.kext','IntelBTPatcher.kext','IntelBluetoothFirmware.kext',
     'BrightnessKeys.kext','AirportItlwmHP.kext']


def run(args,cwd=None):
    print('$ '+' '.join(map(str,args)),flush=True)
    subprocess.run(list(map(str,args)),cwd=cwd,check=True,timeout=900)


def verify(base,hashes):
    for name,digest in hashes.items():
        if hashlib.sha256((base/name).read_bytes()).hexdigest()!=digest:
            raise RuntimeError('Checksum mismatch: '+name)


def extract(archive,destination):
    with zipfile.ZipFile(archive) as z:
        for item in z.infolist():
            p=Path(item.filename)
            if p.is_absolute() or '..' in p.parts or (item.external_attr>>16)&0o170000==0o120000:
                raise RuntimeError('Unexpected source archive path.')
        z.extractall(destination)


def make_config(original):
    config=copy.deepcopy(original)
    entries=config['Kernel']['Add']
    if not any(e['BundlePath']=='NootedGreenHP.kext' and e['Enabled'] for e in entries):
        raise RuntimeError('The working HP graphics driver must remain enabled.')
    if any(e['BundlePath'] in NEW for e in entries):raise RuntimeError('Extras already exist in the source profile.')
    for entry in entries:
        if entry['BundlePath']=='itlwm.kext':entry['Enabled']=False
    for name in NEW:
        entries.append({'Arch':'x86_64','BundlePath':name,'Comment':'HP daily candidate: '+name,
                        'Enabled':True,'ExecutablePath':'Contents/MacOS/'+name[:-5],
                        'PlistPath':'Contents/Info.plist','MinKernel':'25.6.0',
                        'MaxKernel':'25.6.0' if name=='AirportItlwmHP.kext' else '25.99.99'})
    nv=config['NVRAM']['Add'][GUID]
    nv['bluetoothExternalDongleFailed']=bytes(1)
    nv['bluetoothInternalControllerInfo']=bytes(14)
    args=nv['boot-args'].split()
    if 'hp-extras=1' not in args:args.append('hp-extras=1')
    nv['boot-args']=' '.join(args)
    if len(nv['boot-args'].encode())>228:raise RuntimeError('Boot arguments exceed this profile\'s tested bound.')
    return config


def build_brightness(work,project):
    source=work/'brightness';extract(KIT/'BrightnessKeys-source.zip',source)
    source=source/'BrightnessKeys-36820d11327f8aee859997c19f46e24d854ddee7/BrightnessKeys'
    sdk=project/'deps/XPS-IrisXe/build/deps/MacKernelSDK'
    lilu=project/'deps/XPS-IrisXe/build/deps/Lilu.kext/Contents/Resources'
    out=work/'brightness-build';out.mkdir()
    kext=out/'BrightnessKeys.kext';(kext/'Contents/MacOS').mkdir(parents=True)
    info=plistlib.loads((source/'Info.plist').read_bytes())
    replacements={'$(DEVELOPMENT_LANGUAGE)':'en','$(EXECUTABLE_NAME)':'BrightnessKeys',
                  '$(PRODUCT_BUNDLE_IDENTIFIER)':'as.acidanthera.BrightnessKeys',
                  '$(PRODUCT_NAME)':'BrightnessKeys','$(PRODUCT_BUNDLE_PACKAGE_TYPE)':'KEXT',
                  '$(MARKETING_VERSION)':'1.0.3','$(CURRENT_PROJECT_VERSION)':'1.0.3'}
    def substitute(v):
        if isinstance(v,str):
            for key,value in replacements.items():v=v.replace(key,value)
        elif isinstance(v,dict):v={k:substitute(x) for k,x in v.items()}
        elif isinstance(v,list):v=[substitute(x) for x in v]
        return v
    (kext/'Contents/Info.plist').write_bytes(plistlib.dumps(substitute(info)))
    mod=out/'kmod.c'
    mod.write_text('''#include <mach/mach_types.h>
extern kern_return_t _start(kmod_info_t *, void *);
extern kern_return_t _stop(kmod_info_t *, void *);
KMOD_EXPLICIT_DECL(as.acidanthera.BrightnessKeys, "1.0.3", _start, _stop)
__private_extern__ kmod_start_func_t *_realmain = 0;
__private_extern__ kmod_stop_func_t *_antimain = 0;
__private_extern__ int _kext_apple_cc = __APPLE_CC__;
''')
    flags=['-target','x86_64-apple-macos13','-mkernel','-nostdinc','-fno-builtin','-fno-common',
           '-fno-stack-protector','-mno-red-zone','-mno-mmx','-mno-sse','-mno-sse2',
           '-fno-vectorize','-fno-slp-vectorize','-DKERNEL','-DKERNEL_PRIVATE','-DDRIVER_PRIVATE',
           '-DAPPLE','-DNeXT','-DPRODUCT_NAME=BrightnessKeys','-DMODULE_VERSION=1.0.3',
           '-isystem',sdk/'Headers','-I',lilu,'-O2','-g']
    run(['clang',*flags,'-c',mod,'-o',out/'kmod.o'])
    run(['clang++',*flags,'-std=gnu++17','-nostdinc++','-fno-exceptions','-fno-rtti','-fapple-kext',
         '-mllvm','-disable-atexit-based-global-dtor-lowering','-Wno-deprecated-declarations',
         '-Wno-inconsistent-missing-override','-c',source/'BrightnessKeys.cpp','-o',out/'brightness.o'])
    binary=kext/'Contents/MacOS/BrightnessKeys'
    run(['clang++','-arch','x86_64','-mkernel','-nostdlib','-static','-Xlinker','-kext',
         '-Xlinker','-export_dynamic','-mmacosx-version-min=13.0',out/'kmod.o',out/'brightness.o',
         sdk/'Library/x86_64/libkmod.a','-lcc_kext','-o',binary])
    if struct.unpack_from('<IIII',binary.read_bytes())!=(0xfeedfacf,0x1000007,3,11):
        raise RuntimeError('Invalid brightness kernel bundle.')
    run(['codesign','--force','--sign','-',kext])
    return kext


def main():
    if os.geteuid()==0:raise RuntimeError('Run without sudo, from your usual macOS login.')
    if subprocess.check_output(['/usr/bin/sw_vers','-buildVersion'],text=True).strip()!='25G332':
        raise RuntimeError('This kit targets the current 25G332 system only.')
    if subprocess.check_output(['/usr/sbin/sysctl','-n','kern.uuid'],text=True).strip()!='28267FD5-3E1E-3686-8A1C-E73E2466FCFB':
        raise RuntimeError('Running kernel differs from the working port.')
    if DEST.exists():raise RuntimeError('HP-DAILY already exists; review it before replacing it.')
    inputs=json.loads((KIT/'inputs.json').read_text());verify(KIT,inputs['files']);verify(BASE,inputs['baseProfile'])
    previous=json.loads((KIT.parent/'Davghz-Port/last-build.json').read_text())
    original=Path(previous['work']).resolve()
    if original.parent!=(Path.home()/'HP-Davghz-Port').resolve() or not previous.get('installed'):
        raise RuntimeError('The completed HP graphics build was not found in your home folder.')
    work=Path.home()/'HP-Extras-Drivers'/time.strftime('build-%Y%m%d-%H%M%S')
    work.mkdir(parents=True)
    run([PY,KIT/'extras-report.py','--quick'])
    project=work/'project';extract(KIT/'wifi-source.zip',work)
    (project/'deps').symlink_to(original/'project/deps',target_is_directory=True)
    wifi=project/'drivers/wifi'
    for source in (wifi/'overlay').rglob('*'):
        if source.is_file() and source.read_bytes()!=(project/'deps/itlwm'/source.relative_to(wifi/'overlay')).read_bytes():
            raise RuntimeError('The prepared HP Wi-Fi overlay changed: '+source.name)
    print('Building the fitted AX211 native Wi-Fi candidate with its required PNVM.',flush=True)
    try:run([PY,wifi/'build.py'])
    finally:
        logs=list((wifi/'build/logs').glob('*.log'))+[wifi/'build/link.log']
        with (KIT.parent/'hp-extras-wifi-compile.txt').open('w') as output:
            for log in logs:
                if log.is_file():output.write('\n=== '+log.name+' ===\n'+'\n'.join(log.read_text(errors='replace').splitlines()[-80:])+'\n')
    brightness=build_brightness(work,project)
    candidate=work/'HP-DAILY';shutil.copytree(BASE,candidate)
    for name in NEW:
        source=(wifi/'build'/name if name=='AirportItlwmHP.kext' else
                brightness if name=='BrightnessKeys.kext' else KIT/'payload'/name)
        target=candidate/'Kexts'/name
        shutil.copytree(source,target)
        run(['/usr/bin/codesign','--force','--deep','--sign','-',target])
        run(['/usr/bin/codesign','--verify','--deep','--strict',target])
    original_config=plistlib.loads((BASE/'config.plist').read_bytes())
    (candidate/'config.plist').write_bytes(plistlib.dumps(make_config(original_config),sort_keys=False))
    validator=work/'ocvalidate';shutil.copy2(KIT/'ocvalidate',validator);os.chmod(validator,0o755)
    run([validator,candidate/'config.plist'])
    expected={p.relative_to(candidate).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
              for p in candidate.rglob('*') if p.is_file()}
    try:
        shutil.copytree(candidate,DEST)
        verify(DEST,expected)
        # This user agent runs after the next login and only reads system state.
        support=Path.home()/'HP-Extras-Drivers';shutil.copy2(KIT/'extras-report.py',support/'extras-report.py')
        agent=Path.home()/'Library/LaunchAgents/local.hp.extras-report.plist';agent.parent.mkdir(parents=True,exist_ok=True)
        if agent.exists():raise RuntimeError('An extras report agent already exists; review it first.')
        agent.write_bytes(plistlib.dumps({'Label':'local.hp.extras-report','RunAtLoad':True,
              'ProgramArguments':[PY,str(support/'extras-report.py')],
              'StandardOutPath':str(support/'report-service.log'),'StandardErrorPath':str(support/'report-service.log')}))
        verify(BASE,inputs['baseProfile'])
    except Exception:
        if DEST.exists():
            if DEST.resolve().parent!=BASE.parent.resolve():raise RuntimeError('Unexpected profile destination.')
            shutil.move(str(DEST),str(work/'incomplete-EFI'))
        raise
    (KIT/'hp-daily-hashes.json').write_text(json.dumps(expected,indent=2)+'\n')
    (KIT/'result.json').write_text(json.dumps({'built':True,'profileReady':True,'profile':'EFI/HP-DAILY',
          'wifi':'AirportItlwmHP 0.1.4','bluetooth':'Intel 2.5.2 + BlueToolFixup 2.7.2',
          'brightnessKeys':'source-built 1.0.3','audio':'hardware report only; speaker amplifiers unresolved',
          'hardwareTested':False,'work':str(work)},indent=2)+'\n')
    print('READY: restart through EFI/HP-DAILY/OpenCore.efi. Connect in the native Wi-Fi menu.',flush=True)
    print('Bluetooth pairing and brightness keys need testing. Audio details will be recorded automatically.',flush=True)


if __name__=='__main__':
    try:main()
    except Exception as error:print('STOPPED:',error,flush=True);raise SystemExit(1)
