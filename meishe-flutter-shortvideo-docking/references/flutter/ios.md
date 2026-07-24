# Flutter iOS 子路由

仅在 Flutter 目标存在 `ios/` 时加载和执行。

- 当前任务新建的 Flutter iOS 工程必须以 `--ios-bundle-identifier com.meishe.duanshipindemo` 接入。已有项目不自动改身份；现有值不等于该精确值时，官方 Demo 素材服务请求无法走通，必须在运行前选择临时官方身份或客户服务器、匹配 License 与白名单路径。
- 检查项目本地插件的 `ios/nvshortvideo.podspec`、`ios/Classes/VideoEditPlugin.swift`、`ios/Assets` 和 `ios/Frameworks/*.xcframework`。
- 修补应用 `Info.plist` 的相机、麦克风、相册、音乐和本地网络权限；在形状可识别时将 Podfile 的显式部署版本提升到 podspec 最低要求。
- 指定 `--ios-bundle-identifier`（或兼容的 `--package-name`）时，将检测到的应用 Target 的 Debug/Release/Profile Bundle Identifier 改为该值，并保留测试 Target 的 `.<Target>Tests` 后缀。
- Flutter 新模板可能在 `flutter create --no-pub` 后没有 `ios/Podfile`。此时根据应用 target 和插件 podspec 最低版本生成标准 Flutter Podfile，显式写入 `platform :ios`、`flutter_ios_podfile_setup`、`flutter_install_all_ios_pods` 和 `post_install`；脚本仍不执行 `pod install`。
- `ios/Flutter/Debug.xcconfig`、`Release.xcconfig`、`Profile.xcconfig` 必须分别可选包含检测到的 `Pods-<AppTarget>.<mode>.xcconfig`，并继续包含 `Generated.xcconfig`。应用 Target 的 Profile build configuration 必须显式引用 `Profile.xcconfig`。
- 客户/正式工程默认不写入全局 `NSAllowsArbitraryLoads`。已验证的 ShortVideo `2.0.2.1` 官方 Flutter Demo Bundle Identifier `com.meishe.duanshipindemo` 临时验证路径与官方 Demo 对齐为 `NSAllowsArbitraryLoads = true`，必须在交接报告中标记并在生产前收紧。
- 检查 `ConfigServerInfo` 和 `DownloadPrefabricatedMaterialCompletionMethod` 的 Swift bridge 分支是否调用 `completion(...)`。
- 官方 Flutter Demo 在进入拍摄、合拍和编辑前会再次触发预制素材下载。生成页仅在 iOS 点击路径先等待服务配置回执，再由 `_runFeature` 直接、非阻塞发起素材刷新并打开功能；不得调用受 `_materialPreparation` / `_isPreparingMaterials` 保护的首页 `_prepareMaterialsInBackground()`，Android 点击路径也不得继承该补丁。
- 生成 wrapper 必须显式设置 `albumConfig.useAutoCut = true`、`templateConfig.useAutoCut = true`，并在 `captureBottomMenuItems` 中保留 `NvCaptureBottomMenuItem` 的 image/video/smart/template。共享 `assetAutoCutUrl` 使用官方 `/api/app` 基础地址，由 iOS bridge 按官方契约处理。
- 官方 Demo 服务配置不得发送 `<YOUR_MEISHE_...>` 占位鉴权字段。客户服务只按真实合同添加 `clientId`、`clientSecret` 和 `assemblyId`。
- 生成的作品发布页必须通过页面空白点击取消输入焦点，使用 `ScrollViewKeyboardDismissBehavior.onDrag` 支持拖动收起，并保持 `Scaffold` 键盘避让，使草稿描述、状态和底部操作在 iOS 键盘展开时仍可滚动访问。
- ShortVideo `2.0.2.1` iOS 一键成片可能回调 `hasDraft = false`；callback `projectId` 是临时任务 ID，禁止直接落库。仅当 `VideoEditPlugin.swift`、Swift timeline API 和 Pod source 形状全部匹配时生成 `NvDraftSnapshotBridge.swift`：优先暂存当前模型，没有模型时复制渲染结果到 App 运行时沙箱并以 `NvTimelineDataManager.newProject` 新建标准草稿。只有新草稿可列出时才向 Dart 返回成功，删除或放弃时清理映射媒体。
- iOS publish 事件必须先送达 Flutter 页面再关闭 SDK 编辑器。源码形状未知时不修改 vendor bridge，只输出版本核对警告并保留原行为。
- 一键成片结果必须先进入标准编辑页，再由 Next 进入作品发布页；发布页分别验证保存草稿、草稿继续编辑和导出视频，不使用独立模板直出路径替代。
- 缺少插件 iOS 目录时要求用户重新提供完整 `Flutter工程` 包，不创建伪文件，也不改用原生 iOS CocoaPods 包。
- 签名 Team、证书和 profile 是用户专属配置，只检查和报告，不写入通用模板。
- `flutter pub get` 和 CocoaPods 只登记到 `Dependency Installation`，按 `references/dependency-installation.md` 取得用户选择后执行。Windows 不登记可执行的 Pods 步骤，只提示转到 macOS；依赖完成后再使用 Xcode/xcodebuild 和真机验证。
- CocoaPods 完成后必须打开由实际 `.xcodeproj` 推导或唯一检测到的 workspace，不得用 Target 名猜测 Workspace，也不得打开 `.xcodeproj`。生成的 iOS-only README 不得出现 Android Gradle、APK 或 Android 设备命令。
- iOS-only Flutter 项目不得生成 Android Gradle、AAR、仓库或权限提示。
- iOS 故障读取 `references/flutter/ios-troubleshooting.md`；Flutter 的条件 ATS 和点击刷新规则必须依据本路由已验证组合，不得套用 RN 实现代码。
