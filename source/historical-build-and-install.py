"""Build the qualified 25G332 HP port locally, then install the complete stack."""
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import time
import zipfile

KIT=Path('/Volumes/MACOS_BOOT/Davghz-Port')
PY='/Library/Developer/CommandLineTools/usr/bin/python3'


def run(args,cwd=None,env=None,timeout=900):
    print('$ '+' '.join(map(str,args)),flush=True)
    subprocess.run(list(map(str,args)),cwd=cwd,env=env,check=True,timeout=timeout)


def finish_install(work):
    payload=work/'payload'
    # The pinned framebuffer donor is unsigned. Sign its copied payload before
    # the root installer's existing strict checks, for new and resumed builds.
    run(['/usr/bin/codesign','--force','--sign','-',
         payload/'Extensions/AppleIntelTGLGraphicsFramebuffer.kext'])
    run(['sudo',PY,KIT/'install-port.py',payload],timeout=600)
    record=json.loads((KIT/'last-build.json').read_text())
    record['installed']=True
    (KIT/'last-build.json').write_text(json.dumps(record,indent=2)+'\n')
    print('READY: restart through EFI/HP-PORT/OpenCore.efi. Feedback is captured automatically.',flush=True)


def main():
    if sys.argv[1:] not in ([],['--resume']):raise RuntimeError('Expected no arguments or --resume.')
    if os.geteuid()==0:raise RuntimeError('Run this build command without sudo; installation asks for sudo at the end.')
    if subprocess.check_output(['/usr/bin/sw_vers','-buildVersion'],text=True).strip()!='25G332':
        raise RuntimeError('This candidate requires macOS build 25G332.')
    inputs=json.loads((KIT/'inputs.json').read_text())
    for rel,h in inputs['files'].items():
        if hashlib.sha256((KIT/rel).read_bytes()).hexdigest()!=h:raise RuntimeError('Input checksum failed: '+rel)
    for path,h in inputs['systemFiles'].items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=h:raise RuntimeError('Installed system image changed: '+path)
    for relative,h in inputs['profileFiles'].items():
        path=Path('/Volumes/MACOS_BOOT/EFI/HP-PORT')/relative
        if hashlib.sha256(path.read_bytes()).hexdigest()!=h:raise RuntimeError('The staged HP-PORT profile changed: '+relative)
    if sys.argv[1:]==['--resume']:
        record=json.loads((KIT/'last-build.json').read_text())
        if (record.get('build'),record.get('version'),record.get('built'),record.get('installed'))!=('25G332','1.0.13',True,False):
            raise RuntimeError('No completed, uninstalled 1.0.13 build is recorded.')
        work=Path(record['work']).resolve()
        if work.parent!=(Path.home()/'HP-Davghz-Port').resolve() or not (work/'payload').is_dir():
            raise RuntimeError('The recorded build is not in your HP-Davghz-Port home folder.')
        print('Reusing the completed build; correcting the framebuffer signature.',flush=True)
        finish_install(work)
        return
    work=Path.home()/'HP-Davghz-Port'/time.strftime('%Y%m%d-%H%M%S')
    work.mkdir(parents=True,exist_ok=False)
    with zipfile.ZipFile(KIT/'project.zip') as z:
        for f in z.infolist():
            p=Path(f.filename)
            if p.is_absolute() or '..' in p.parts or (f.external_attr>>16)&0o170000==0o120000:
                raise RuntimeError('Unexpected project archive path or link.')
        z.extractall(work)
    project=work/'project'
    env=dict(os.environ)
    # Trust only the checksum-verified generated FAT32 source caches for cloning.
    cache=KIT/'cache'
    paths=[cache/'graphics/source/XPS-IrisXe',cache/'fixes-20261024/wifi-native-pnvm/source',
           cache/'graphics/source/XPS-IrisXe/build/deps/MacKernelSDK',
           cache/'graphics/source/XPS-IrisXe/build/deps/NootedGreen']
    env['GIT_CONFIG_COUNT']=str(len(paths))
    for i,p in enumerate(paths):env['GIT_CONFIG_KEY_'+str(i)]='safe.directory';env['GIT_CONFIG_VALUE_'+str(i)]=str(p)
    run([PY,'tools/prepare-build.py','--local-cache',cache],project,env)
    xps=project/'deps/XPS-IrisXe'
    native=xps/'build/deps/NootedGreen'
    run(['git','clone','--no-hardlinks','--no-checkout',paths[3],native],env=env)
    run(['git','checkout','--detach','95f81898be65cb9f7b3d370ca78054be4cc8a62d'],native,env)
    sle=native/'sle_Internal/sle';le=native/'sle_Internal/le'
    if not (sle/'AppleIntelGraphicsShared.bundle').exists():
        shutil.copytree(le/'AppleIntelGraphicsShared.bundle',sle/'AppleIntelGraphicsShared.bundle',symlinks=True)
    runtime=work/'runtime';runtime.mkdir()
    run(['clang','-arch','x86_64','-fno-objc-arc','-framework','Foundation','-framework','Metal',
         KIT/'metal_layout_probe.m','-o',runtime/'metal-layout-probe'])
    run([runtime/'metal-layout-probe'])
    try:
        run([PY,'drivers/graphics/build.py'],project,env)
    finally:
        build_log=project/'drivers/graphics/build-v1.0.13/build.log'
        if build_log.is_file():shutil.copy2(build_log,KIT.parent/'hp-port-compile.txt')
    run(['/bin/zsh','build-hookcase.sh'],xps,env)
    run(['/bin/zsh','macos/build-all.sh',sle],xps,env)
    # Link the guarded HP cleanup into the adapter, using the untouched donor.
    mtl=xps/'macos/out/AppleIntelTGLGraphicsMTLDriver.bundle'
    adapter=runtime/'libxedrv.o';posh=runtime/'hp-posh.o'
    run(['clang','-arch','x86_64','-mmacosx-version-min=15.0','-fno-objc-arc','-O2',
         '-c',xps/'macos/src/libxedrv.m','-o',adapter])
    run(['clang++','-arch','x86_64','-mmacosx-version-min=15.0','-std=c++17','-fno-objc-arc','-O2',
         '-DHP_POSH_AUTOINSTALL','-c',project/'drivers/graphics/tools/hp_metal_posh_fix.mm','-o',posh])
    lib=runtime/'libxedrv.dylib'
    run(['clang++','-arch','x86_64','-mmacosx-version-min=15.0','-dynamiclib',adapter,posh,
         '-framework','Foundation','-framework','Metal','-framework','IOSurface','-framework','IOKit','-lobjc',
         '-install_name','/Library/GPUBundles/AppleIntelTGLGraphicsMTLDriver.bundle/Contents/MacOS/libxedrv.dylib',
         '-o',lib])
    run(['codesign','--force','--sign','-',lib])
    shutil.copy2(lib,mtl/'Contents/MacOS/libxedrv.dylib')
    run(['codesign','--force','--deep','--sign','-',mtl])
    run(['codesign','--verify','--deep','--strict',mtl])
    payload=work/'payload';payload.mkdir()
    def copy(source,relative):
        destination=payload/relative;destination.parent.mkdir(parents=True,exist_ok=True)
        if source.is_dir():shutil.copytree(source,destination,symlinks=True)
        else:shutil.copy2(source,destination)
    for name in ['AppleIntelTGLGraphics','AppleIntelTGLGraphicsFramebuffer']:
        copy(le/(name+'.kext'),'Extensions/'+name+'.kext')
    info=payload/'Extensions/AppleIntelTGLGraphics.kext/Contents/Info.plist'
    p=plistlib.loads(info.read_bytes());p['IOKitPersonalities']['Gen7']['IOPCIPrimaryMatch']='0x9a498086';p['CFBundleVersion']='16.0.2';info.write_bytes(plistlib.dumps(p))
    run(['codesign','--force','--sign','-',payload/'Extensions/AppleIntelTGLGraphics.kext'])
    copy(xps/'build/HookCase.kext','Extensions/HookCase.kext')
    for name in ['AppleIntelTGLGraphicsMTLDriver','AppleIntelTGLGraphicsGLDriver',
                 'AppleIntelTGLGraphicsVADriver','AppleIntelTGLGraphicsVAME','AppleIntelGraphicsShared']:
        copy(sle/(name+'.bundle'),'Extensions/'+name+'.bundle')
    copy(mtl,'GPUBundles/AppleIntelTGLGraphicsMTLDriver.bundle')
    copy(sle/'AppleIntelGraphicsShared.bundle','GPUBundles/AppleIntelGraphicsShared.bundle')
    copy(xps/'macos/out/xe.bundle','SystemCaches/xe.bundle')
    copy(project/'drivers/graphics/build-v1.0.13/NootedGreenHP.kext','EFI/NootedGreenHP.kext')
    copy(KIT/'hp-port-report.py','Support/hp-port-report.py')
    copy(KIT/'local.hp.davghz-report.plist','LaunchDaemons/local.hp.davghz-report.plist')
    probes=payload/'Support';probes.mkdir(exist_ok=True)
    for name in ['metal_compute_probe','metal_render_probe']:
        run(['clang','-arch','x86_64','-fno-objc-arc','-fblocks','-framework','Foundation','-framework','Metal',
             project/'drivers/graphics/tools'/(name+'.m'),'-o',probes/name])
    (KIT/'last-build.json').write_text(json.dumps({'work':str(work),'build':'25G332','version':'1.0.13',
                                                'built':True,'installed':False},indent=2)+'\n')
    print('All components built. Installing the complete HP stack now.',flush=True)
    finish_install(work)


if __name__=='__main__':
    try:main()
    except Exception as error:
        print('STOPPED:',error,flush=True);raise SystemExit(1)
