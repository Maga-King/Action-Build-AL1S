#!/usr/bin/env python3
"""Offline source-routing tests, not proof that every Qualcomm SoC can build."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
REFERENCES = []
REQUIRED = ['oplus_ofp_set_longrui_aod_mode', 'oplus_ofp_set_ultra_low_power_aod_mode',
            'oplus_ofp_get_aod_state', 'oplus_ofp_aod_off_handle',
            'oplus_ofp_full_screen_aod_mode_is_enabled']


def put(root, relative, value):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding='utf-8', newline='\n')


class SourceRouting(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='al1s-routing-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.display = self.root / 'vendor/qcom/opensource/display-drivers'
        put(self.root, 'kernel_platform/msm-kernel/android/abi_gki_aarch64_qcom', '[abi_symbol_list]\n')
        put(self.root, 'kernel_platform/build/kernel/abi/symbols.deny', '# test policy\n')

    def fixture(self, directory):
        put(self.display, directory + '/oplus_onscreenfingerprint.c', '\n'.join(REQUIRED))
        put(self.display, 'display_modules.bzl', '    "' + directory + '/oplus_display_utils.c",\n')
        put(self.display, 'msm/msm_drv.c', '''static int __init msm_drm_register(void)
{
\tif (platform_driver_register(&msm_platform_driver))
\t\treturn -1;
\treturn 0;
}
static void __exit msm_drm_unregister(void)
{
\tplatform_driver_unregister(&msm_platform_driver);
}
''')

    def patch(self, soc):
        return subprocess.run([sys.executable, str(ROOT/'scripts/al1s_patch_vendor_dlkm.py'),
            str(self.root), str(ROOT/'patches/originos/al1s_originos.c'), '--soc', soc],
            capture_output=True, text=True)

    def check_route(self, directory, soc):
        result = self.patch(soc)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        record = json.loads((self.root/'al1s-originos-patch.json').read_text())
        self.assertEqual(record['display_source_dir'], directory)
        self.assertTrue((self.root/record['payload_path']).is_file())
        source = (self.display/'msm/msm_drv.c').read_text()
        self.assertEqual(source.count('\tal1s_originos_init();'), 1)
        self.assertEqual(source.count('\tal1s_originos_exit();'), 1)

    def test_sm8750(self):
        self.fixture('oplus/SM8750')
        self.check_route('oplus/SM8750', 'sm8750')

    def test_other_soc_is_not_redirected_to_sm8750(self):
        self.fixture('oplus/SM8650')
        self.check_route('oplus/SM8650', 'sm8650')

    def test_flat_directory_relative_header(self):
        self.fixture('oplus')
        self.check_route('oplus', 'sm8550')
        self.assertIn('"../msm/dsi/dsi_display.h"',
                      (self.display/'oplus/al1s_originos.c').read_text())

    def test_wrong_soc_not_silently_borrowed(self):
        self.fixture('oplus/SM8750')
        before = (self.display/'msm/msm_drv.c').read_bytes()
        self.assertNotEqual(self.patch('sm8650').returncode, 0)
        self.assertEqual((self.display/'msm/msm_drv.c').read_bytes(), before)

    def test_selected_real_sources(self):
        if not REFERENCES:
            self.skipTest('Pass --reference for actual upstream source-layout tests')
        for reference in REFERENCES:
            with self.subTest(reference=str(reference)):
                # Copy only patch inputs, never touch the upstream checkout.
                for name in ['msm/msm_drv.c', 'display_modules.bzl',
                             'oplus/SM8750/oplus_onscreenfingerprint.c']:
                    path = self.display/name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(reference/name, path)
                self.check_route('oplus/SM8750', 'sm8750')

    @unittest.skipIf(os.name == 'nt', 'Kleaf symlink fixtures use the Linux build host')
    def test_fast_base_uses_selected_target(self):
        put(self.root, 'kernel_platform/common/build.config.constants', 'CLANG_VERSION=r123test\n')
        put(self.root, 'kernel_platform/msm-kernel/msm_kernel_la.bzl', '        base_kernel = base_kernel,\n')
        (self.root/'kernel_platform/build/kernel/kleaf').mkdir(parents=True)
        result = subprocess.run([sys.executable, str(ROOT/'scripts/al1s_fast_prebuilt.py'),
            str(self.root), '--platform', 'pineapple', '--variant', 'perf', '--analysis-only'],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        macro = (self.root/'kernel_platform/msm-kernel/msm_kernel_la.bzl').read_text()
        self.assertIn('target == "pineapple_perf"', macro)
        self.assertNotIn('sun_perf', macro)

    def test_workflow_keeps_full_and_resume_routes(self):
        workflow = (ROOT/'.github/workflows/Build Kernel OnePlus.yml').read_text(encoding='utf-8')
        self.assertNotIn('"$FILE" != "oneplus_13_b"', workflow)
        self.assertIn('高通专属', workflow)
        self.assertIn("inputs.FAST_BASE_RUN == ''", workflow)
        self.assertIn('pattern: AL1S-FAST-base-${{ inputs.FILE }}-*', workflow)
        self.assertIn('--soc "${{ env.CPU }}"', workflow)
        self.assertIn('"${{ env.CPUD }}" "${{ env.BUILD_METHOD }}"', workflow)
        self.assertNotIn('cp AL1S-vendor_dlkm/msm_drm.ko ./AnyKernel3', workflow)

    def test_shared_identity_nodes_retained(self):
        source = (ROOT/'patches/originos/al1s_originos.c').read_text()
        for marker in ['make_root_group("fp_id",', 'make_root_group("ufs",',
                       'make_root_group("cpu_info",', 'root_device_register("soc1")',
                       '__ATTR(fp_id, 0444, fp_show, NULL)', '__ATTR(ufsid, 0444, ufs_show, NULL)',
                       '/sys/devices/soc0/serial_number', 'ultrasonic_fake_nyako',
                       'CPU_RO(cpu_freq)', 'CPU_RO(core_num)', 'CPU_RO(cpu_set)',
                       'CPU_RO(user_cpu_freq)', 'SOC_RO(cpu_type)']:
            self.assertIn(marker, source)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--reference', action='append', type=Path, default=[])
    args, remaining = parser.parse_known_args()
    REFERENCES = args.reference
    unittest.main(argv=[sys.argv[0]] + remaining, verbosity=2)
