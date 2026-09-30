#!/usr/bin/env bash
# Build the external display DDK target against the same kernel/configuration.
set -euo pipefail
workspace=$(realpath "$1")
platform=${2:?platform required}
variant=${3:?variant required}
cd "$workspace/kernel_platform"
target="//vendor/qcom/opensource/display-drivers:${platform}_${variant}_display_drivers_dist"
if [[ ! -e vendor && ! -L vendor ]]; then
  ln -s ../vendor vendor
fi
test -f vendor/qcom/opensource/display-drivers/oplus/SM8750/al1s_originos.c
# Match build_with_bazel.py's cache and options, avoiding a second kernel build.
export TEST_TMPDIR="$workspace/bazel-cache"
./tools/bazel --output_user_root="$workspace/bazel-cache" run \
  --//msm-kernel:skip_abi=true --//msm-kernel:skip_abl=true \
  --config=stamp \
  --user_kmi_symbol_lists=//msm-kernel:android/abi_gki_aarch64_qcom \
  --ignore_missing_projects --incompatible_sandbox_hermetic_tmp=false \
  --nozstd_dwarf_compression \
  "$target" -- --dist_dir="$PWD/out/al1s-display"
test -s out/al1s-display/msm_drm.ko
