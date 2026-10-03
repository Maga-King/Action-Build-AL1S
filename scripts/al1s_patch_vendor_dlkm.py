#!/usr/bin/env python3
"""Apply the optional vendor AL1S ABI and retain its existing kernel exports."""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('workspace', type=Path)
p.add_argument('payload', type=Path)
p.add_argument('--soc', default='', help='Selected manifest CPU, e.g. sm8750; not a phone-model whitelist')
a = p.parse_args()
display = a.workspace / 'vendor/qcom/opensource/display-drivers'
driver = display / 'msm/msm_drv.c'
build = display / 'display_modules.bzl'
if not driver.is_file() or not build.is_file():
    raise SystemExit('Qualcomm display DDK source layout missing in the selected source tree')
d = driver.read_text()
b = build.read_text()
# Select only a directory referenced by this tree's build definition. Never
# borrow another phone's source. Prefer its SoC directory when several exist.
candidates = []
for match in re.finditer(r'(?m)^([ \t]*)"(oplus/[^"\n]*oplus_display_utils\.c)",', b):
    directory = (display / match[2]).parent
    if (directory / 'oplus_onscreenfingerprint.c').is_file():
        candidates.append((match, directory))
if a.soc:
    exact = [item for item in candidates if item[1].name.casefold() == a.soc.casefold()]
    if exact:
        candidates = exact
    else:
        # Older sources put the implementation directly under oplus/.
        candidates = [item for item in candidates if item[1] == display / 'oplus']
if len(candidates) != 1:
    raise SystemExit('Cannot uniquely select the Oplus display source for ' + (a.soc or 'this tree'))
source_match, oplus = candidates[0]
ofp = oplus / 'oplus_onscreenfingerprint.c'
required = ['oplus_ofp_set_longrui_aod_mode', 'oplus_ofp_set_ultra_low_power_aod_mode',
            'oplus_ofp_get_aod_state', 'oplus_ofp_aod_off_handle',
            'oplus_ofp_full_screen_aod_mode_is_enabled']
source = ofp.read_text()
for symbol in required:
    if symbol not in source:
        raise SystemExit('Required OnePlus display interface missing: ' + symbol)
if 'al1s_originos_init' in d:
    raise SystemExit('AL1S patch already applied; use a clean source checkout')
init_marker = 'static int __init msm_drm_register(void)'
exit_marker = 'static void __exit msm_drm_unregister(void)\n{'
src_marker = source_match[0]
for text, marker in [(d, init_marker), (d, exit_marker), (b, src_marker)]:
    if text.count(marker) != 1:
        raise SystemExit('Source layout changed; refusing an ambiguous patch: ' + marker)
init_match = re.search(r'(?m)^static int __init msm_drm_register\(void\)\n\{\n[\s\S]*?^\}', d)
if not init_match:
    raise SystemExit('Cannot locate display module registration function')
body = init_match[0]
tail = re.search(r'(?m)^([ \t]*)return 0;\n\}$', body)
if not tail:
    raise SystemExit('Display module registration has no unambiguous successful return')
body = body[:tail.start()] + '#ifdef OPLUS_FEATURE_DISPLAY\n\tal1s_originos_init();\n#endif\n' + body[tail.start():]
d = d[:init_match.start()] + body + d[init_match.end():]
d = d.replace(init_marker, '#ifdef OPLUS_FEATURE_DISPLAY\nvoid al1s_originos_init(void);\nvoid al1s_originos_exit(void);\n#endif\n\n' + init_marker)
d = d.replace(exit_marker, exit_marker + '\n#ifdef OPLUS_FEATURE_DISPLAY\n\tal1s_originos_exit();\n#endif')
destination = oplus / 'al1s_originos.c'
b = b.replace(src_marker, src_marker + '\n' + source_match[1] +
              '"' + destination.relative_to(display).as_posix() + '",')
# Retain existing file APIs through GKI's symbol trimming. No VFS behavior changes.
abi = a.workspace / 'kernel_platform/msm-kernel/android/abi_gki_aarch64_qcom'
abi_text = abi.read_text()
if '[abi_symbol_list]' not in abi_text:
    raise SystemExit('Unrecognized QCOM KMI symbol list')
required_exports = ['filp_open', 'kernel_read', 'filp_close']
present = {line.strip() for line in abi_text.splitlines()}
added_exports = [name for name in required_exports if name not in present]
abi_text = abi_text.rstrip() + '\n' + ''.join('  ' + name + '\n' for name in added_exports)
# This script runs only when ORIGINOS_DLKM is enabled. The requested custom
# build allows every symbol through the GKI deny-list policy. Keep the actual
# symbol-list processing, tracepoint validation and modpost checks intact.
deny = a.workspace / 'kernel_platform/build/kernel/abi/symbols.deny'
deny_original = deny.read_bytes()
deny_text = '# AL1S OriginOS custom build: no ABI symbols are denied by policy.\n'
payload = a.payload.read_bytes()
if any(s in payload for s in [b'sel_read_enforce', b'fake_enforcing', b'/sys/selinux']):
    raise SystemExit('Excluded SELinux behavior found in payload')
# Preserve the shared implementation, adjusting only the relative DSI include
# for layouts with or without an intermediate SoC directory.
dsi_header = os.path.relpath(display / 'msm/dsi/dsi_display.h', oplus).replace(os.sep, '/')
payload = payload.replace(b'"../../msm/dsi/dsi_display.h"', ('"' + dsi_header + '"').encode())
destination.write_bytes(payload)
abi.write_text(abi_text, encoding='utf-8', newline='\n')
deny.write_text(deny_text, encoding='utf-8', newline='\n')
driver.write_text(d, encoding='utf-8', newline='\n')
build.write_text(b, encoding='utf-8', newline='\n')
record = {'scope': 'vendor_dlkm/msm_drm.ko implementation; existing kernel exports retained', 'payload_sha256': hashlib.sha256(payload).hexdigest(),
          'selinux_spoofing': False, 'kernel_node_patch': False, 'retained_kernel_exports': required_exports,
          'added_kmi_entries': added_exports,
          'soc': a.soc, 'display_source_dir': oplus.relative_to(display).as_posix(),
          'payload_path': str(destination.relative_to(a.workspace)),
          'symbol_deny_policy': 'allow_all',
          'original_symbols_deny_sha256': hashlib.sha256(deny_original).hexdigest(),
          'files': [str(x.relative_to(a.workspace)) for x in [abi, deny, driver, build, destination]]}
(a.workspace/'al1s-originos-patch.json').write_text(json.dumps(record, indent=2))
print(json.dumps(record, indent=2))
