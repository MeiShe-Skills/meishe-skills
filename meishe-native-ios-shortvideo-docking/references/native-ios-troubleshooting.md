# 原生 iOS 错误现象、原因与自检

仅用于原生 iOS 路由。

- CocoaPods 找不到 SDK：检查项目本地 `vendor/meishe/Pods-NvShortVideoEdit/NvShortVideoEdit.podspec` 和 Podfile 相对路径，不能引用下载目录。
- Xcode 26 的 CocoaPods `[CP]` 脚本阶段报 sandbox/文件访问拒绝：确认 `xcodebuild -version` 精确为 26.x，并检查 App 工程 Build Settings 的 User Script Sandboxing 为 No（`ENABLE_USER_SCRIPT_SANDBOXING = NO`）。生成器只对 Xcode 26 自动应用；未知或其他版本先按实际错误分析，不套用该补丁。
- workspace 中 scheme 名不确定：先在项目根目录执行 `xcodebuild -list -workspace "<实际 .xcworkspace 绝对路径>"`，再在 Xcode 顶部选择输出中确认的 App scheme。Target 名和 scheme 名不保证相同，交接不得猜测。
- `Unable to add a source with url https://github.com/CocoaPods/Specs.git`：旧 Podfile 强制使用了体积很大的 Git Specs 仓库。删除这一条精确的 `source` 声明，让 CocoaPods 使用本机已配置的 `trunk` CDN（通常是 `https://cdn.cocoapods.org/`）后重新执行获准的 `pod install`；不要执行 `pod repo add`，不要修改全局 Git、代理、镜像或证书配置。用户自定义私有 Specs source 必须保留。
- 官方素材接口被拒绝或列表为空：官方 Demo host 只允许精确 Bundle Identifier `com.meishe.duanshipindemo`；其他身份必须使用美摄提供的客户服务。
- ShortVideo `2.0.2.1` 官方原生 iOS Example 的应用 plist 使用 `NSAllowsArbitraryLoads = true`。临时官方 Demo 身份缺失该项时，素材/CDN子链路可能被 ATS 拦截，表现为编辑器可打开、内置效果存在但在线列表全空。
- ATS 补丁只允许写入应用 Target 的 Info.plist。必须确认 `vendor/meishe/Pods-NvShortVideoEdit` 内的 Example、framework 和 xcframework plist 未被修改。
- 拍摄、合拍、编辑入口都要在打开 SDK 页面前无条件、非阻塞调用 `downloadPrefabricatedMaterialCompletion(nil)`；不能只依赖首页首次请求，也不能因为首页请求仍处于 `isMaterialRequestInProgress` 而跳过。
- ShortVideo `2.0.2.1` 编译报 `NvHttpRequest` 没有 `clientId`、`clientSecret` 或 `assemblyId`：删除直接属性赋值，客户鉴权改用美摄提供的请求委托/服务合同，不得伪造 SDK API。
- 若列表仍为空，按顺序检查 Bundle Identifier、最终 host、应用 ATS、请求 URL、HTTP 状态、业务码、白名单和 CDN 错误，并至少下载使用一个在线素材验证闭环。
- 一键成片入口缺失：检查 `albumConfig.useAutoCut`、`templateConfig.useAutoCut` 和 `NvCaptureBottomMenu.template`，确认生成代码没有只依赖 SDK 默认值。
- 一键成片模板为空：原生 iOS 必须使用完整 `assetAutoCutUrl`，并检查 Bundle Identifier 白名单、ATS、模板标签、AutoCut HTTP/业务码；不要套用 RN/Flutter 的 `/api/app` 基础地址写法。
- 一键成片后没有发布页：确认先进入标准编辑页，再由 Next 触发 `NvModuleManagerDelegate.publish`；发布页必须同时保留 `saveCurrentDraft` 和 `compileCurrentTimeline`。
- 一键成片发布页没有“保存草稿”：ShortVideo `2.0.2.1` 可能回调 `hasDraft = false`。确认输入 SDK 同时暴露已验证的 project-manager 与 Swift timeline API；匹配后生成页始终展示按钮，未知 API 形状只告警、不盲补丁。
- 点击保存后提示成功但草稿箱为空，或继续编辑时全黑：AutoCut 回调 `projectId` 是临时任务 ID，不能直接 `storeCurrentProject`。应复制回调视频到 App 运行时沙箱，用 `NvTimelineDataManager.newProject(localFilePaths:)` 新建标准单片段工程，保存并反查新草稿 ID；退出编辑仍使用原任务 ID。
- 删除该草稿后媒体残留：标准草稿需要记录“新草稿 ID -> 运行时视频路径”，`deleteDraft` 成功后同步删除映射视频。不得把运行时视频、测试视频或用户素材放入 skill。
- 保存草稿后回素材选择页：完成保存后关闭完整 SDK presented navigation chain，再调用 `exitVideoEdit`，不要 pop 到 SDK 导航根页。
- 草稿无法点击：检查装饰子视图不抢事件，长按删除手势不取消短点击。
- 素材失败不得禁用拍摄、合拍、编辑和草稿入口；仍需检查回调、ATS、HTTP/业务码和至少一个在线素材闭环。

Xcode target membership、签名、License 和真机流程由用户手动验证。
