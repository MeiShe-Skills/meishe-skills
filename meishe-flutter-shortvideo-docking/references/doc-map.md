# Flutter 文档索引

本 skill 的唯一业务路线是 Flutter。功能字段以 `references/flutter/feature-configuration.md` 为准，版本行为和中英文映射以 `references/config-capabilities/flutter.json` 为准。

## 必读顺序

1. `references/flutter.md`
2. `references/flutter/common.md`
3. `references/flutter/feature-configuration.md`
4. `references/packages/flutter.md`
5. `references/verified/flutter.md`
6. 按目标平台读取 `references/flutter/android.md` 或 `references/flutter/ios.md`
7. 仅在失败时读取对应 `android-troubleshooting.md` 或 `ios-troubleshooting.md`

共享规则按需读取 `official-downloads.md`、`dependency-installation.md`、`customer-server.md`、`demo-ui-style.md` 和 `placeholders-and-config.md`。

## 增强官方资料

- 中文：`assets/shortvideo-docs/markdown/flutter_quickstart/doc_ch/quickstart_ch.md`
- 英文：`assets/shortvideo-docs/markdown/flutter_quickstart/doc_en/quickstart_en.md`
- 共享功能配置背景证据：`assets/shortvideo-docs/markdown/native_quickstart/doc_ch/functionConfiguration_ch.md`
- 共享预制素材背景证据：`assets/shortvideo-docs/markdown/native_quickstart/doc_ch/PrefabricatedMaterial_ch.md`

完整增强文档、图片及 `doc-map.json`、`tag-index.json`、`image-index.json` 均保存在 `assets/shortvideo-docs`。机器查询必须同时指定 `--track flutter` 和实际 `--platform`；不得查询 React Native 或原生 track 来补全字段。
