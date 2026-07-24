# 原生 Android 文档索引

本 skill 的唯一业务路线是原生 Android。功能字段以 `references/native-android-feature-configuration.md` 为准，版本行为和中英文映射以 `references/config-capabilities/native-android.json` 为准。

## 必读顺序

1. `references/native-android.md`
2. `references/native-android-feature-configuration.md`
3. `references/packages/native-android.md`
4. `references/verified/native-android.md`
5. AAR 缺失时读取 `references/aar-acquisition.md`
6. 仅在失败时读取 `references/native-android-troubleshooting.md`

`references/android-source-config-summary.md` 只作为当前原生 Android 官方源码配置背景。共享规则按需读取 `official-downloads.md`、`dependency-installation.md`、`customer-server.md`、`demo-ui-style.md` 和 `placeholders-and-config.md`。

## 增强官方资料

- 中文快速接入：`assets/shortvideo-docs/markdown/native_quickstart/doc_ch/quickstart_android_ch.md`
- 英文快速接入：`assets/shortvideo-docs/markdown/native_quickstart/doc_en/quickstart_android_en.md`
- 功能配置：`assets/shortvideo-docs/markdown/native_quickstart/doc_ch/functionConfiguration_ch.md`
- 预制素材：`assets/shortvideo-docs/markdown/native_quickstart/doc_ch/PrefabricatedMaterial_ch.md`

完整增强文档、图片及 `doc-map.json`、`tag-index.json`、`image-index.json` 均保存在 `assets/shortvideo-docs`。机器查询必须固定 `--track native --platform android`；不得查询 iOS、Flutter 或 React Native track 来补全字段。
