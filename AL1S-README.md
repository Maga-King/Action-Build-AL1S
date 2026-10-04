# AL1S / OnePlus 13

This fork adds three independent inputs to **Build All OnePlus Kernels**, on the
`KernelSU-Next` branch. All compilation runs on GitHub Actions.

| Input | Default | Effect |
|---|---|---|
| `NOMOUNT` | on | Build upstream `maxsteeel/nomount` into the kernel, pinned to `6b1be186322d4e0bdc465cf27f6fc0d3679087c6`. Runtime activation still needs the matching NoMount userspace module. |
| `ORIGINOS_DLKM` | off | Add the OriginOS compatibility ABI to OnePlus 13's **vendor `msm_drm.ko`**, including the information nodes previously implemented in the 13T boot kernel. Currently restricted to `oneplus_13_b`. Builds the matching external display module after the upstream kernel build. |
| `KSU_STATIC_SELINUX_REFERENCE` | off | Labelled `静态 SELinux 参考策略（高通8E专用）`. Build the fork's fixed query reference with `CONFIG_KSU_STATIC_SELINUX_REFERENCE=y`; disabled builds explicitly use `n`. This input is available for every device selection, with no device restriction or added validation step. |

The dispatch form has 24 inputs. The `SPACE_NOCLEAN` and `BUILD_NOCACHE`
switches were removed to stay below GitHub's 25-input limit. Workspace cleanup
and build caching remain enabled, matching both switches' previous default
values. Cache save size/hit conditions and the FAST-only ThinLTO conditions
are retained.

## KernelSU Next source

All device selections on this branch now use `Maga-King/KernelSU-Next` for both
kernel integration and the optional bundled Manager download. `KSU_META`
defaults to `dev/dev/`; its final field still supports a manual commit override.
The fork is cloned before its local setup script runs, so the setup script's
upstream clone URL cannot silently substitute the official source. Version
metadata comes from the selected fork commit rather than a different repository.
Tags are optional: workflow metadata and the integrated Kbuild both fall back
to the selected commit's short ID when no reachable tag exists. Manual commit
selection does not shallow the checkout or truncate the version commit count.
Other root-provider branches are unchanged. The fork currently provides `dev`,
not the previous source's `dev-susfs` branch; this change does not port SUSFS into
the fork.

The static-reference switch changes only `CONFIG_KSU_STATIC_SELINUX_REFERENCE`.
It does not enable `ORIGINOS_DLKM`, change its device restriction or change the
phone's real enforcement policy. KSUN's existing runtime `selinux_hide` feature
must still be enabled. The fixed policy is not a universal ROM reference.
There are no new workflow verification jobs or CPU/ROM compatibility checks.
When reusing `FAST_BASE_RUN`, use a base originally built with the same KSU
source/commit and static-reference setting; restoring a base cannot recompile
this option. Leave `FAST_BASE_RUN` empty when changing the option.

With `ORIGINOS_DLKM=off`, no compatibility source, init/exit hook or extra KMI entries are injected.
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

The optional build retains the existing `filp_open`, `kernel_read` and
`filp_close` exports in the QCOM KMI symbol list and imports their VFS namespaces.
This prevents GKI symbol trimming from breaking the external adapter; the node
implementation stays in `msm_drm.ko` and no VFS function behavior is changed.

For this custom OriginOS build, the GKI `build/kernel/abi/symbols.deny` policy
list is emptied: all symbols are allowed by that policy, as requested. Actual
export availability, symbol versions, namespace imports and module linking
are still checked. The original deny-list hash is recorded in patch provenance.
With `ORIGINOS_DLKM=off`, the upstream deny policy remains unchanged.

## Fast builds

`FAST_BUILD` runs the upstream **Build Kernel FAST** step unchanged, including
its direct make/ccache implementation. Its `common/out` kernel, symbol tables
and modules are packaged as a local Kleaf prebuilt base for the vendor module
build. Only `sun_perf`'s `base_kernel` is redirected; the official vendor
configuration and display DDK are retained. A Bazel action-graph check refuses
to proceed if that module build would compile a second common/GKI kernel.

The module build uses the ordinary sandboxed execution mode. Kleaf
`--config=fast` is no longer used: its local mode broke native Oplus UFS relative
header includes. Vendor module compilation adds time after the upstream fast
kernel build. If upstream requests fallback, the full kernel path is used.
With fast builds disabled, the exact 4K target `//msm-kernel:sun_perf_dist`
avoids the upstream fuzzy query's unnecessary `sun16k_perf_dist` build.

Before FAST compilation, a real Bazel `aquery` validates the complete vendor
dependency graph using temporary analysis-only inputs. It checks toolchain
platforms and rejects a second GKI build. The temporary package is removed and
the vendor macro restored on both success and failure; these inputs are never
compiled or packaged. The prebuilt platforms follow Kleaf's official template,
including target/host architecture and the configured Clang version.

The completed FAST kernel is uploaded as `AL1S-FAST-base-*` before the display
step, preserving its Image, symbol tables, configuration and modules even if
the later module build fails. This is a build checkpoint, not a flashable ZIP.

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
against that kernel. The separate `AL1S-OriginOS-msm_drm-*` artifact contains only the patched
`msm_drm.ko`. The configured Clang toolchain strips debug information; every
allocated ELF section is checked for unchanged contents. Size and SHA256 are
printed in the build log. No partition image, symbol tables or sidecar files
are uploaded in this artifact. A missing or invalid module fails the workflow.

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

## Resume vendor module compilation

Set `FAST_BASE_RUN` to a previous run ID containing `AL1S-FAST-base-*` artifacts,
with `FAST_BUILD` and `ORIGINOS_DLKM` enabled. The completed kernel is restored
and the upstream FAST kernel step is skipped; only the vendor module dependency
build and display DDK continue. Use the same device and kernel options as that
saved base. Leave the field empty for the normal upstream build path.

The FAST output directory `common/out` is excluded in `.bazelignore`. Kbuild
creates `out/source` pointing back to `common`; scanning generated output as
source caused Bazel's infinite-symlink error and could include generated headers.
The ignore rule leaves the existing kernel artifacts and symlink intact.

## Device probe after installation

On the OnePlus 13, the AL1S kernel and replacement display module were observed
loaded successfully. All 60 compatibility attributes were readable as root;
UFS identity and both battery metrics matched their native sources. SELinux
remained Enforcing and no fake enforcement node existed. Display transitions,
fingerprint HBM, suspend/resume and access from individual Android service
domains still require functional testing.
