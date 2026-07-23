# React Native 文档索引

本 skill 的唯一业务路线是 React Native。功能字段以 `references/react-native/feature-configuration.md` 为准，版本行为和中英文映射以 `references/config-capabilities/react-native.json` 为准。

## 必读顺序

1. `references/react-native.md`
2. `references/react-native/common.md`
3. `references/react-native/feature-configuration.md`
4. `references/packages/react-native.md`
5. `references/verified/react-native.md`
6. 按目标平台读取 `references/react-native/android.md` 或 `references/react-native/ios.md`
7. 仅在失败时读取对应 `android-troubleshooting.md` 或 `ios-troubleshooting.md`

共享规则按需读取 `official-downloads.md`、`dependency-installation.md`、`customer-server.md`、`demo-ui-style.md` 和 `placeholders-and-config.md`。

## 增强官方资料

- 中文：`assets/shortvideo-docs/markdown/react_native_quickstart/doc_ch/quickstart_ch.md`
- 英文：`assets/shortvideo-docs/markdown/react_native_quickstart/doc_en/quickstart_en.md`
- 共享功能配置背景证据：`assets/shortvideo-docs/markdown/native_quickstart/doc_ch/functionConfiguration_ch.md`
- 共享预制素材背景证据：`assets/shortvideo-docs/markdown/native_quickstart/doc_ch/PrefabricatedMaterial_ch.md`

完整增强文档、图片及 `doc-map.json`、`tag-index.json`、`image-index.json` 均保存在 `assets/shortvideo-docs`。机器查询必须同时指定 `--track react-native` 和实际 `--platform`；不得查询 Flutter 或原生 track 来补全字段。
