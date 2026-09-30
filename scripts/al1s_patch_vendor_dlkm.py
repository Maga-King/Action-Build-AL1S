#!/usr/bin/env python3
"""Apply the optional AL1S ABI only to the vendor msm_drm module source."""
import argparse
import hashlib
import json
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('workspace', type=Path)
p.add_argument('payload', type=Path)
a = p.parse_args()
display = a.workspace / 'vendor/qcom/opensource/display-drivers'
driver = display / 'msm/msm_drv.c'
build = display / 'display_modules.bzl'
ofp = display / 'oplus/SM8750/oplus_onscreenfingerprint.c'
required = ['oplus_ofp_set_longrui_aod_mode', 'oplus_ofp_set_ultra_low_power_aod_mode',
            'oplus_ofp_get_aod_state', 'oplus_ofp_aod_off_handle',
            'oplus_ofp_full_screen_aod_mode_is_enabled']
source = ofp.read_text()
for symbol in required:
    if symbol not in source:
        raise SystemExit('Required OnePlus display interface missing: ' + symbol)
d = driver.read_text()
b = build.read_text()
if 'al1s_originos_init' in d:
    raise SystemExit('AL1S patch already applied; use a clean source checkout')
init_marker = 'static int __init msm_drm_register(void)'
exit_marker = 'static void __exit msm_drm_unregister(void)\n{'
src_marker = '             "oplus/SM8750/oplus_display_utils.c",'
init_tail = '\tbl_ic_ktz8868_init();\n#endif /* OPLUS_FEATURE_DISPLAY */\n\treturn 0;'
for text, marker in [(d, init_marker), (d, exit_marker), (d, init_tail), (b, src_marker)]:
    if text.count(marker) != 1:
        raise SystemExit('Source layout changed; refusing an ambiguous patch: ' + marker)
d = d.replace(init_marker, '#ifdef OPLUS_FEATURE_DISPLAY\nvoid al1s_originos_init(void);\nvoid al1s_originos_exit(void);\n#endif\n\n' + init_marker)
d = d.replace(init_tail, '\tbl_ic_ktz8868_init();\n\tal1s_originos_init();\n#endif /* OPLUS_FEATURE_DISPLAY */\n\treturn 0;')
d = d.replace(exit_marker, exit_marker + '\n#ifdef OPLUS_FEATURE_DISPLAY\n\tal1s_originos_exit();\n#endif')
b = b.replace(src_marker, src_marker + '\n             "oplus/SM8750/al1s_originos.c",')
payload = a.payload.read_bytes()
if any(s in payload for s in [b'sel_read_enforce', b'fake_enforcing', b'/sys/selinux']):
    raise SystemExit('Excluded SELinux behavior found in payload')
(display / 'oplus/SM8750/al1s_originos.c').write_bytes(payload)
driver.write_text(d)
build.write_text(b)
record = {'scope': 'vendor_dlkm/msm_drm.ko only', 'payload_sha256': hashlib.sha256(payload).hexdigest(),
          'selinux_spoofing': False, 'kernel_node_patch': False,
          'files': [str(x.relative_to(a.workspace)) for x in [driver, build, display/'oplus/SM8750/al1s_originos.c']]}
(a.workspace/'al1s-originos-patch.json').write_text(json.dumps(record, indent=2))
print(json.dumps(record, indent=2))
