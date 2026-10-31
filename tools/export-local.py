#!/usr/bin/env python3
"""Make a sanitized personal backup of a matching local deployment; never install."""
import argparse
import hashlib
import json
from pathlib import Path
import plistlib
import shutil
import subprocess


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--profile',type=Path,required=True)
    p.add_argument('--destination',type=Path,required=True)
    args=p.parse_args()
    profile=args.profile.resolve(strict=True)
    dest=args.destination.expanduser().resolve()
    repository=Path(__file__).resolve().parents[1]
    if dest==repository or repository in dest.parents:
        p.error('Keep personal runtime backups outside the public repository.')
    if dest.exists():p.error('Destination already exists; choose a new directory.')
    build=subprocess.check_output(['/usr/bin/sw_vers','-buildVersion'],text=True).strip()
    if build!='25G332':p.error('This snapshot targets macOS build 25G332.')
    config=plistlib.loads((profile/'config.plist').read_bytes())
    # Refuse a profile with missing enabled inputs before copying anything.
    for entry in config['Kernel']['Add']:
        if not entry['Enabled']:continue
        base=profile/'Kexts'/entry['BundlePath']
        for key in ['PlistPath','ExecutablePath']:
            if entry[key] and not (base/entry[key]).is_file():
                p.error('Missing enabled driver input: '+str(base/entry[key]))
    for entry in config['ACPI']['Add']:
        if entry['Enabled'] and not (profile/'ACPI'/entry['Path']).is_file():
            p.error('Missing enabled ACPI input: '+entry['Path'])
    dest.mkdir(parents=True)
    out=dest/'EFI/OC'
    shutil.copytree(profile,out)
    for section in ['Generic','DataHub','PlatformNVRAM','SMBIOS']:
        for key in config['PlatformInfo'].get(section,{}):
            if key in ['MLB','BoardSerialNumber','SystemSerialNumber','SystemUUID','SmUUID']:
                config['PlatformInfo'][section][key]=''
            elif key=='ROM':config['PlatformInfo'][section][key]=bytes(6)
    config['Misc']['Security']['PasswordHash']=b''
    config['Misc']['Security']['PasswordSalt']=b''
    config['Misc']['Security']['ExposeSensitiveData']=0
    (out/'config.plist').write_bytes(plistlib.dumps(config,sort_keys=False))
    boot=profile.parent/'BOOT/BOOTx64.efi'
    if boot.is_file():
        (dest/'EFI/BOOT').mkdir()
        shutil.copy2(boot,dest/'EFI/BOOT/BOOTx64.efi')
    for record in json.loads((repository/'manifest/system-runtime.json').read_text()):
        source=Path(record['installed_path'])
        if not source.is_dir():raise RuntimeError('Missing runtime: '+str(source))
        shutil.copytree(source,dest/'system-runtime'/source.relative_to('/'),symlinks=False)
    for source in [Path('/Library/Application Support/HP-Davghz-Port/tools'),
                   Path('/Library/LaunchDaemons/local.hp.davghz-report.plist')]:
        if source.exists():
            target=dest/'local-support'/source.relative_to('/')
            target.parent.mkdir(parents=True,exist_ok=True)
            if source.is_dir():shutil.copytree(source,target)
            else:shutil.copy2(source,target)
    (dest/'PERSONAL-BACKUP-ONLY.txt').write_text(
        'Local backup; contains Apple/proprietary runtime and board firmware.\n'
        'Do not publish. Serial/MLB/UUID/ROM cleared in copied config.plist.\n'
        'Not an installer or a boot-qualified image. Supply your own SMBIOS\n'
        'identity and EFI/BOOT if missing. Driver caches are not copied.\n'
        'No system/EFI/NVRAM settings were changed by this export.\n')
    hashes={str(f.relative_to(dest)):hashlib.sha256(f.read_bytes()).hexdigest()
            for f in dest.rglob('*') if f.is_file()}
    (dest/'SHA256.json').write_text(json.dumps(hashes,indent=2)+'\n')
    print('Exported',len(hashes),'files to',dest)


if __name__=='__main__':main()
