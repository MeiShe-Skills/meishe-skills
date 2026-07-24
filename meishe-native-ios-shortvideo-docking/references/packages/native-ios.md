# 原生 iOS 官方包事实

- 下载 `iOS App vX.x.x` 或 `iOS&Android vX.x.x`，输入为 `native/ios/Pods-NvShortVideoEdit`。
- 目标项目使用 `vendor/meishe/Pods-NvShortVideoEdit` 和项目本地 Podfile 相对路径。
- 官方最低示例为 iOS 12，使用 `NvShortVideoEdit`、`use_frameworks!` 和必要隐私权限。
- ShortVideo `2.0.2.1` 官方 `Pods-NvShortVideoEdit/Example` 应用 plist包含 `NSAllowsArbitraryLoads = true`；这是一项可检测的输入包事实，只能条件化同步到官方 Demo 身份的应用 plist，不能修改 SDK 内 plist。
- Swift 锚点包括 `NvModuleManager.sharedInstance()`、拍摄、合拍、编辑、`projectList()`、`reeditProject` 和 `deleteDraft`。
- 官方 Demo host 仅适用于规定 Bundle Identifier；具体限制读取 `references/native-ios.md`。
