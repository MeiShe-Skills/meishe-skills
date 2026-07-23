# Flutter 路由索引

仅当目标根目录存在 `pubspec.yaml` 时使用本路由。确认目标中实际存在的子平台后，按顺序加载：

1. 始终读取 `references/flutter/common.md`。
2. 需要生成、修改或回答全部功能配置时读取 `references/flutter/feature-configuration.md`。
3. 存在 `android/` 时读取 `references/flutter/android.md`。
4. 存在 `ios/` 时读取 `references/flutter/ios.md`。
5. 排查 Android 时只追加 `references/flutter/android-troubleshooting.md`；排查 iOS 时只追加 `references/flutter/ios-troubleshooting.md`。
6. 读取 `references/packages/flutter.md` 和 `references/verified/flutter.md`。

双端项目加载 Flutter 公共规则及两个 Flutter 子平台文档。不得加载 React Native、原生 Android 或原生 iOS 的实现文档，也不得用这些路线的 SDK 包替代 Flutter 插件。

功能配置始终位于 Flutter 层的 `lib/meishe_feature_config.dart`。同一份 Dart 配置服务 iOS、Android，不生成两份原生用户配置；菜单删除必须依赖有序数组让 SDK 重排 UI。

执行入口：

```shell
python scripts/integrate_flutter.py --target-root <flutter-app> --plugin-path <flutter-package-or-nvshortvideo>
```

公开参数保持不变。Android 原生引擎补充仅在 `references/flutter/android.md` 规定的已验证缺库场景使用 `--aar-path`。
