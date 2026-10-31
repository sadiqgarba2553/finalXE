#!/usr/bin/env python3
"""Verify a local finalXE backup's hashes, paths and cleared SMBIOS identity."""
import argparse
import hashlib
import json
from pathlib import Path
import plistlib

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('backup',type=Path)
args=p.parse_args()
root=args.backup.resolve(strict=True)
hashes=json.loads((root/'SHA256.json').read_text())
for rel,digest in hashes.items():
    f=(root/rel).resolve()
    if not f.is_relative_to(root):raise SystemExit('Unsafe manifest path: '+rel)
    if hashlib.sha256(f.read_bytes()).hexdigest()!=digest:
        raise SystemExit('Checksum mismatch: '+rel)
profile=root/'EFI/OC'
c=plistlib.loads((profile/'config.plist').read_bytes())
g=c['PlatformInfo']['Generic']
for key in ['SystemSerialNumber','MLB','SystemUUID']:
    if g.get(key):raise SystemExit('Identity not cleared: '+key)
if any(g.get('ROM',b'')):raise SystemExit('ROM not cleared')
for e in c['Kernel']['Add']:
    if e['Enabled']:
        for key in ['PlistPath','ExecutablePath']:
            if e[key] and not (profile/'Kexts'/e['BundlePath']/e[key]).is_file():
                raise SystemExit('Missing kext path: '+e['BundlePath']+'/'+e[key])
for e in c['ACPI']['Add']:
    if e['Enabled'] and not (profile/'ACPI'/e['Path']).is_file():
        raise SystemExit('Missing ACPI: '+e['Path'])
print('PASS:',len(hashes),'file hashes, enabled kext/ACPI paths and cleared SMBIOS identity')
