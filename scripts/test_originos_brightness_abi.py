#!/usr/bin/env python3
"""Source invariants only: not a substitute for DDK compile/boot/device tests."""
from pathlib import Path
import argparse
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ABIInvariants(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT/'patches/originos/al1s_originos.c').read_text()
        cls.base = subprocess.check_output(['git', '-C', str(ROOT), 'show',
            '1be2b7f:patches/originos/al1s_originos.c'], text=True)

    def test_existing_handlers_preserved(self):
        for begin, end in [('enum display_id {', 'static struct kobj_attribute display_attrs'),
                           ('static ssize_t fp_show', 'enum display_id {')]:
            self.assertEqual(self.base.split(begin,1)[1].split(end,1)[0],
                             self.source.split(begin,1)[1].split(end,1)[0])

    def test_new_interfaces_are_read_only(self):
        block = self.source.split('static bool brightness_group_created;')[1].split('static ssize_t read_metric')[0]
        self.assertIn('__ATTR(n, 0444, brightness_show, NULL)', block)
        self.assertIn('get_main_display()', block)
        self.assertIn('mutex_lock(&panel->panel_lock)', block)
        self.assertIn('return -ENODEV', block)
        for forbidden in ['set_backlight', 'set_global_hbm_status', 'get_sec_display',
                          'kernel_write', 'kthread', 'queue_work', 'schedule_work', 'timer_setup']:
            self.assertNotIn(forbidden, block)
        self.assertEqual(re.findall(r'^BRIGHTNESS_RO\((\w+)\);', block, re.M),
            ['bl_level','hbm_max_brightness','normal_max_brightness','oled_hbm','al1s_bl_abi'])

    def test_group_lifetime_primary_only(self):
        self.assertIn('sysfs_create_group(lcm_kobj[0], &brightness_group)', self.source)
        self.assertNotIn('sysfs_create_group(lcm_kobj[1], &brightness_group)', self.source)
        cleanup = self.source.split('void al1s_originos_exit(void)\n{')[1].split('void al1s_originos_init')[0]
        self.assertLess(cleanup.index('sysfs_remove_group(lcm_kobj[0], &brightness_group)'),
                        cleanup.index('kobject_put(lcm_kobj[i])'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
