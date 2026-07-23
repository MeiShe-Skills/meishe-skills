# React Native 路由索引

仅当目标存在 `package.json` 且声明 React Native 依赖时使用本路由。确认子平台后按顺序加载：

1. 始终读取 `references/react-native/common.md`。
2. 需要生成、修改或回答全部功能配置时读取 `references/react-native/feature-configuration.md`。
3. 存在 `android/` 时读取 `references/react-native/android.md`。
4. 存在 `ios/` 时读取 `references/react-native/ios.md`。
5. 排查 Android 时只追加 `references/react-native/android-troubleshooting.md`；排查 iOS 时只追加 `references/react-native/ios-troubleshooting.md`。
6. 读取 `references/packages/react-native.md` 和 `references/verified/react-native.md`。

双端项目加载 RN 公共规则及两个 RN 子平台文档。不得加载 Flutter、原生 Android 或原生 iOS 的实现文档，也不得要求这些路线的 SDK 包作为 RN 正常输入。

功能配置始终位于 React Native 层的 `src/meisheFeatureConfig.ts|js`。同一份配置服务 iOS、Android，不生成两份原生用户配置；菜单删除必须依赖有序数组让 SDK 重排 UI。

执行入口：

```shell
python scripts/integrate_react_native.py --target-root <rn-app> --plugin-path <rn-package-or-react-native-nvshortvideo>
```
