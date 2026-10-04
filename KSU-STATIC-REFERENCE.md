# Official KernelSU fork integration

Only the `KernelSU` branch of `Maga-King/Action-Build-AL1S` is changed.
Other root-provider branches, including `KernelSU-Next`, are left untouched.

The kernel source comes from `Maga-King/KernelSU` (based on official
`tiann/KernelSU`). `KSU_META` remains `main/main/`: the first field selects
the official Manager branch, the second selects the fork kernel branch, and
the optional third field selects a commit. The official Manager is retained
because no Manager or ksud behavior was changed, and the kernel retains the
official signature acceptance values.

`KSU_STATIC_SELINUX_REFERENCE` is labelled with the same dedicated-platform
warning as the KernelSU-Next branch and defaults to false. Enabling it sets
`CONFIG_KSU_STATIC_SELINUX_REFERENCE=y`; disabling it explicitly sets `n`.
All existing device selections can use the option; no CPU validation or new
test/verification step is added to the build workflow. There are 23 inputs,
below GitHub's 25-input limit. Existing cleanup/cache switches are retained.

The feature only changes SELinux Hide's backup/query reference. Active
enforcement is unchanged. Enable the normal `selinux_hide` runtime feature
in KernelSU as well. The fixed reference is not universal across ROMs; format
or class/permission mismatch falls back to the official dynamic backup.

The fork is explicitly cloned before local setup runs. Version numbers use
the selected checkout's full history and do not depend on tags or API commit
pagination. Manual commit selection does not make the repository shallow.
Build helper scripts are loaded from this exact workflow commit, not the
unmodified Numbersf repository.

No install-time network risk scanner was found in this official ksud version,
so no extra off switch or daemon patch is needed. Kernel compile checks, if
run, use the fork's separate compile-only workflow, not this build pipeline.
