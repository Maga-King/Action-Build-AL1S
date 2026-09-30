#!/usr/bin/env python3
"""Collect real full-build outputs; never label a boot-only build as DLKM."""
import argparse, hashlib, json, shutil
from pathlib import Path

p=argparse.ArgumentParser()
p.add_argument('workspace',type=Path)
p.add_argument('output',type=Path)
a=p.parse_args()
a.output.mkdir(parents=True,exist_ok=True)
roots=[a.workspace/'kernel_platform/out', a.workspace/'out']
def candidates(name):
    paths=[]
    for root in roots:
        if root.exists():
            paths.extend(x for x in root.rglob(name) if x.is_file())
    return sorted(paths,key=lambda x: ('/dist/' not in x.as_posix(),len(x.parts),str(x)))
def digest(path):
    with path.open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()
modules=candidates('msm_drm.ko')
modules=[x for x in modules if b'al1s_originos_init' in x.read_bytes()]
if not modules:
    raise SystemExit('No built msm_drm.ko containing AL1S found. DLKM build is incomplete.')
images=candidates('vendor_dlkm.img')
if not images:
    shutil.copy2(modules[0],a.output/'msm_drm.ko')
    raise SystemExit('Patched module exists, but no vendor_dlkm.img was built. Not a complete DSU image.')
chosen={'msm_drm.ko':modules[0],'vendor_dlkm.img':images[0]}
record={}
for name,path in chosen.items():
    shutil.copy2(path,a.output/name)
    record[name]={'source':str(path.relative_to(a.workspace)), 'bytes':path.stat().st_size,'sha256':digest(path)}
for name in ['modules.load','modules.dep','modules.alias','Module.symvers']:
    found=candidates(name)
    if found: shutil.copy2(found[0],a.output/name)
patch=a.workspace/'al1s-originos-patch.json'
if patch.exists(): shutil.copy2(patch,a.output/patch.name)
(a.output/'build-artifacts.json').write_text(json.dumps(record,indent=2))
(a.output/'SHA256SUMS').write_text(''.join(f'{v["sha256"]}  {k}\n' for k,v in record.items()))
print(json.dumps(record,indent=2))
