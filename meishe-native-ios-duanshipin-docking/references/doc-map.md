# 原生 iOS 文档索引

本 skill 的唯一业务路线是原生 iOS。功能字段以 `references/native-ios-feature-configuration.md` 为准，版本行为和中英文映射以 `references/config-capabilities/native-ios.json` 为准。

## 必读顺序

1. `references/native-ios.md`
2. `references/native-ios-feature-configuration.md`
3. `references/packages/native-ios.md`
4. `references/verified/native-ios.md`
5. 仅在失败时读取 `references/native-ios-troubleshooting.md`

共享规则按需读取 `official-downloads.md`、`dependency-installation.md`、`customer-server.md`、`demo-ui-style.md` 和 `placeholders-and-config.md`。

## 增强官方资料

- 中文快速接入：`assets/shortvideo-docs/markdown/native_quickstart/doc_ch/quickstart_ch.md`
- 英文快速接入：`assets/shortvideo-docs/markdown/native_quickstart/doc_en/quickstart_en.md`
- 功能配置：`assets/shortvideo-docs/markdown/native_quickstart/doc_ch/functionConfiguration_ch.md`
- 预制素材：`assets/shortvideo-docs/markdown/native_quickstart/doc_ch/PrefabricatedMaterial_ch.md`

完整增强文档、图片及 `doc-map.json`、`tag-index.json`、`image-index.json` 均保存在 `assets/shortvideo-docs`。机器查询必须固定 `--track native --platform ios`；不得查询 Android、Flutter 或 React Native track 来补全属性。
