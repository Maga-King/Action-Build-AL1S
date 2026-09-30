# AL1S / OnePlus 13

This fork adds two independent inputs to **Build All OnePlus Kernels**, on the
`KernelSU-Next` branch. All compilation runs on GitHub Actions.

| Input | Default | Effect |
|---|---|---|
| `NOMOUNT` | on | Build upstream `maxsteeel/nomount` into the kernel, pinned to `6b1be186322d4e0bdc465cf27f6fc0d3679087c6`. Runtime activation still needs the matching NoMount userspace module. |
| `ORIGINOS_DLKM` | off | Add the OriginOS compatibility ABI to OnePlus 13's **vendor `msm_drm.ko`**, including the information nodes previously implemented in the 13T boot kernel. Currently restricted to `oneplus_13_b`. Forces the full module build path. |

With `ORIGINOS_DLKM=off`, no compatibility source or init/exit hook is injected.
NoMount and the existing kernel options remain independently selectable.

## OriginOS interface scope

- `/sys/fp_id/fp_id`: compatibility identity `ultrasonic_fake_nyako`.
- `/sys/ufs/ufsid`: forwards `/sys/devices/soc0/serial_number`.
- `/sys/cpu_info` and `/sys/devices/soc1`: CPU identity/frequency display tables;
  the writable `type` field does not change CPU clocks.
- `/sys/class/fuelsummary/{soh,cycle}`: forwards Oplus battery metrics.
- `/sys/lcm` and `/sys/lcm1`: 23 display attributes each, sharing compatibility
  state. Full/partial AOD and fingerprint low-power AOD use the existing Oplus
  functions inside the same module. SRE/ORE/ESD compatibility state does not add
  new hardware functionality. Enabling `aod_1hz_enable` remains unsupported,
  matching the inspected 13T adapter's limitation.

There is no `/sys/selinux/fake`, no `sel_read_enforce` patch, and no SELinux policy
relaxation added by this adaptation. Device-specific policy and writable-node
ownership must be supplied by the DSU ROM integrator. This does not implement
fingerprint authentication/TEE or replace the system/ODM HALs and scripts.

The adapter is a source reimplementation based on local inspection of the 13T
OriginOS ABI. The original 13T binary is not redistributed. It keeps the
OnePlus 13 display source and panel configuration, and introduces no runtime
symbol-address hooks. A node initialization failure is logged and rolled back
without preventing the native display driver from loading.

## Requested build profile

`oneplus_13_b`, KernelSU Next, suffix `AL1S`, NoMount on, HMBIRD on, DroidSpaces
on, SUSFS module `N/A`, SUSFS rollback `-1`, KPM/KPN `N/A`, ZRAM override off,
Unicode bypass fix off. Network options retain upstream defaults. This fork
also fixes the upstream configuration branch which enabled `CONFIG_KPM` for
`N/A`; `N/A` now disables it.

## Outputs and verification

The existing AnyKernel3 artifact packages the kernel. When OriginOS is enabled,
an additional step builds the external display DDK target
`//vendor/qcom/opensource/display-drivers:sun_perf_display_drivers_dist`
against that kernel. The separate `AL1S-OriginOS-vendor_dlkm-*` artifact contains
the patched `msm_drm.ko`, hashes and build provenance. A missing patched module
fails the workflow.

This artifact is a **module update, not a complete DSU image**. The generic OSS
`vendor_dlkm.img` contains only the selected in-tree modules; it is deliberately
excluded because replacing the phone's partition with it would lose other
device modules. A complete image must be prepared from the original OnePlus 13
`vendor_dlkm`, preserving its other modules, metadata and load lists, after
checking the new display module's symbol versions and dependencies. The user's
original image is kept locally and is not uploaded to this public repository.

Successful compilation does not establish DSU boot or display correctness.
Use a matching kernel/module build and validate module loading, node labels,
AOD transitions, fingerprint HBM and suspend/resume on the actual device.
Do not substitute the 13T's complete vendor module image for OnePlus 13.
