# KERNELSU-NEXT-PURE

以 [Numbersf/Action-Build 的 KernelSU-Next 分支](https://github.com/Numbersf/Action-Build/tree/KernelSU-Next)
为基线，包含上游 `968fa2a6431b48464f5cf5c9824c9bb526c70bf9` 的清理工作流更新。

Actions 保留上游全部 22 个构建选项，增加 `NOMOUNT`，共 23 项。
以下两项默认值为适配 [Maga-King/KernelSU-Next](https://github.com/Maga-King/KernelSU-Next) 调整：

| 选项 | PURE 默认值 | 原因 |
| --- | --- | --- |
| `KSU_META` | `dev/dev/` | 使用自用 fork 的 `dev` 分支；该 fork 没有 `dev-susfs` 分支。第三段仍可指定提交。 |
| `SUSFS_META` | `-1` | 当前 fork 未集成上游原生 SUSFS；误开启时会明确报错。 |
| `NOMOUNT`（新增） | `true` | 使用 `maxsteeel/nomount@6b1be186322d4e0bdc465cf27f6fc0d3679087c6`，与原分支一致。 |

其他选项、默认值、补丁、FAST/完整构建及 AnyKernel3 打包流程保持上游方案。
默认机型因此仍是 `oneplus_15`；一加 13 构建时需选择对应清单，例如 `oneplus_13_b`。
NoMount 运行时功能仍需配套用户态模块；可以取消勾选进行对照测试。

内核从自用 fork 获取，保留其官方管理器证书和自用管理器证书的双签名认证。
附带 APK 只从该 fork 与内核源码同一提交的成功 CI 下载，并检查证书；没有匹配产物时跳过 APK。
双签名表示两种受信任证书均可识别，不表示同时激活两个管理器 UID。

PURE 不包含原分支的 OriginOS 显示适配、外部 `msm_drm.ko` 构建和 FAST 基础产物复用。
静态 SELinux 参考策略固定关闭。原 `KernelSU-Next` 分支继续保留这些可选功能。

此分支用于以较少改动对照刷机结果。工作流与源码接入检查不能确认实机闪屏已解决；
请使用相同机型/系统清单构建新 AK3 包，再比较实际显示表现。
