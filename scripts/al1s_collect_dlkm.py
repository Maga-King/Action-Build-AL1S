#!/usr/bin/env python3
"""Collect the explicit display DDK output; do not mislabel an OSS image."""
import argparse, hashlib, json, shutil
from pathlib import Path

p=argparse.ArgumentParser()
p.add_argument('workspace',type=Path)
p.add_argument('output',type=Path)
a=p.parse_args()
module=a.workspace/'kernel_platform/out/al1s-display/msm_drm.ko'
if not module.is_file():
    raise SystemExit('External display DDK output missing: '+str(module))
data=module.read_bytes()
if not data.startswith(b'\x7fELF') or b'al1s_originos_init' not in data:
    raise SystemExit('msm_drm.ko is not an ELF containing the AL1S adapter')
a.output.mkdir(parents=True,exist_ok=True)
chosen={'msm_drm.ko':module}
dist=(a.workspace/'kernel_platform/common/out' if (a.workspace/'al1s-fast-prebuilt.json').is_file()
      else a.workspace/'kernel_platform/out/msm-kernel-sun-perf/dist')
for name in ['Module.symvers','kernel.release','vmlinux.symvers','.config']:
    source=dist/name
    if name=='kernel.release' and not source.is_file():source=dist/'include/config/kernel.release'
    if source.is_file():chosen['kernel-'+name.lstrip('.')]=source
record={'artifact_type':'vendor_dlkm_module_update','complete_dsu_image':False,
        'requires_original_oneplus13_vendor_dlkm':True,'files':{}}
for name,path in chosen.items():
    shutil.copy2(path,a.output/name)
    with path.open('rb') as f:sha=hashlib.file_digest(f,'sha256').hexdigest()
    record['files'][name]={'source':str(path.relative_to(a.workspace)),
                         'bytes':path.stat().st_size,'sha256':sha}
patch=a.workspace/'al1s-originos-patch.json'
if patch.is_file():shutil.copy2(patch,a.output/patch.name)
for name in ['al1s-fast-prebuilt.json','al1s-module-actions.json']:
    source=a.workspace/name
    if source.is_file():shutil.copy2(source,a.output/name)
(a.output/'build-artifacts.json').write_text(json.dumps(record,indent=2))
(a.output/'SHA256SUMS').write_text(''.join(f'{v["sha256"]}  {k}\n' for k,v in record['files'].items()))
(a.output/'README.txt').write_text(
    'This is a vendor_dlkm module update, NOT a complete DSU partition image.\n'
    'Preserve the original OnePlus 13 vendor_dlkm image and its other modules.\n'
    'Verify symbol versions/dependencies before replacing lib/modules/msm_drm.ko.\n'
    'The generic OSS vendor_dlkm.img omits external/proprietary device modules\n'
    'and is intentionally excluded from this artifact.\n'
    'Compilation is not proof of runtime compatibility.\n')
print(json.dumps(record,indent=2))
