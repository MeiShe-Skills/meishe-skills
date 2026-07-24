# React Native iOS 子路由

仅在 RN 目标存在 `ios/` 时加载和执行。

- 当前任务新建的 RN iOS 工程必须以 `--ios-bundle-identifier com.meishe.duanshipindemo` 接入。已有项目不自动改身份；现有值不等于该精确值时，官方 Demo 素材服务请求无法走通，必须在运行前选择临时官方身份或客户服务器、匹配 License 与白名单路径。
- 客户/正式工程默认只补齐 SDK 所需隐私权限，不写入全局 `NSAllowsArbitraryLoads`。已验证的官方 Demo Bundle Identifier `com.meishe.duanshipindemo` 临时接入路径与官方 RN Demo 对齐为 `NSAllowsArbitraryLoads = true`，必须在交接报告中标记并在生产前收紧。
- 检查项目本地 npm 包的 podspec、`ios/Classes`、`ios/Assets` 和 `ios/Frameworks/*.xcframework`，并修补应用 Info.plist；保持现有 `use_frameworks!` 策略不变。
- 缺少插件 iOS 内容时要求完整 `React Native工程` 包，不创建伪 bridge/framework，也不改用原生 iOS CocoaPods 包。
- 项目本地 `VideoEditPlugin.m` 在 bridge 调用前重新绑定弱 delegate，并在关闭 SDK 编辑器之前发送 `VideoEditResultEvent`。
- 对精确匹配 ShortVideo `2.0.2.1` 的 iOS bridge，发布回调 `projectId` 仅作为 AutoCut 临时任务 ID。生成器把 `NvDraftSnapshotBridge.swift` 加入应用 target：优先复制当前时间线模型，没有可编辑模型时把渲染结果复制到 App 运行时沙箱并通过 `NvTimelineDataManager.newProject` 创建新标准草稿。只有新草稿 ID 可列出时才 resolve 成功，删除或放弃时清理映射媒体。未知源码、Swift API 或 Xcode target 形状只警告，不进行部分改写。
- iOS 导出回调直接订阅原生 `VideoEditCallbackMethodChannel`；Android 保留官方 operator handler。进度值兼容 `0...1` 和 `0...100`，避免导出实际执行但 UI 永远停在初始状态。
- JS/TS 使用 `NativeEventEmitter(NativeModules.VideoEditPlugin)` 直接订阅 `VideoEditMethodChannel`，不依赖官方二级回调完成关键发布跳转。
- 生成 wrapper 必须显式设置 `albumConfig.useAutoCut = true`、`templateConfig.useAutoCut = true`，并在 `captureBottomMenuItems` 中保留 `NvCaptureBottomMenuItem` 的 image/video/smart/template；共享 `assetAutoCutUrl` 保持官方 `/api/app` 基础地址，由 iOS bridge 按官方契约补齐端点。
- iOS `configServerInfo()` 的官方 JS 包装不返回原生 Promise。生成 wrapper 在 `sendMessageToNative` 可用时直接等待 `ConfigServerInfo` 回执；能力不匹配时回退官方操作器，不修改 vendor API。
- `downloadPrefabricatedMaterial()` 只有严格返回 `true` 才标记完成；生成代码必须保留 `completed !== true` 失败分支。`false` 或 reject 保持失败和可重试，且不得阻塞拍摄、合拍、编辑和草稿。
- 生成的作品发布页必须使用 iOS `KeyboardAvoidingView`，支持点击输入框外 `Keyboard.dismiss()`、拖动滚动区交互式收起，并保留键盘期间的页面滚动和按钮点击能力；“保存草稿”和“导出视频”固定在安全区域底部，不依赖滚动到底部才能看到。
- ShortVideo `2.0.2.1` 一键成片可能回调 `hasDraft = false`，它只控制 SDK 默认发布页的草稿入口，不代表项目已落库。RN 发布页仍提供保存入口，但必须以转换后生成的新标准草稿 ID 作为成功条件，不能反查或直接落库 callback task ID。
- 一键成片验收固定为进入标准编辑页，再点击 Next 进入作品发布页，随后分别验证保存草稿、草稿继续编辑和导出视频；不使用独立同款模板直出路径替代。
- ShortVideo `2.0.2.1` 已验证在 iOS 点击拍摄、合拍或编辑时先确认服务配置，随后由 `runFeature` 直接、非阻塞触发素材刷新，再打开功能；不得调用受 `preparePromise.current` / `materialReady.current` 保护的首页 `prepareMaterials()`，Android 路线不得套用该点击补丁。
- 出现“功能可用但拍摄内在线素材全部为空”时读取 `references/react-native/ios-troubleshooting.md`。
- 仅在 React Native `0.78.x` 且执行机器检测到 Xcode `26.x` 时应用已验证 fmt 补丁；其他组合记录真实工具链与错误，不猜测补丁。
- Team、证书、profile 和设备是用户配置。Debug 通常使用 Metro；`FORCE_BUNDLING=1` 仅作临时自包含 JS 验证，不能代替美摄网络服务验收。
- 包管理器与 CocoaPods 命令只登记到 `Dependency Installation`，按 `references/dependency-installation.md` 获得用户选择后执行。Windows 只做静态检查并把 Pods 明确延后到 macOS；依赖完成后再进行 Xcode/xcodebuild 和真机流程。
- iOS-only RN 项目不得创建或修改 Android Manifest、Gradle、AAR、仓库和 Android 后续步骤。
