# 原生 iOS 已验证边界

- Xcode `26.x` 已验证 CocoaPods 脚本阶段需要 App 工程 Build Settings 中的 `ENABLE_USER_SCRIPT_SANDBOXING = NO`。生成器只在精确检测到 Xcode 主版本 26 时条件式、幂等写入；无法检测、旧版本或未来版本均不继承该补丁。
- 官方 Demo 服务配置只在 Bundle Identifier 为 `com.meishe.duanshipindemo` 时使用；其他身份必须由用户提供客户服务器并单独验收。
- ShortVideo `2.0.2.1` 原生 iOS 已验证：官方 Example 的应用 plist声明 `NSAllowsArbitraryLoads = true`。生成器仅在目标为 `com.meishe.duanshipindemo` 且当前输入包 Example 仍声明该项时同步到应用 plist；客户身份、缺少 Example 或 Example 未声明时均不启用。
- 同一版本已验证拍摄、合拍、编辑入口前必须无条件、非阻塞调用 `downloadPrefabricatedMaterialCompletion(nil)`；首页单飞状态不得抑制入口刷新。在线列表为空时生成 `meishe_native_ios_self_check.md`，并要求检查 ATS、HTTP/业务码、Bundle Identifier 白名单和 CDN。
- ShortVideo `2.0.2.1` 的 `NvHttpRequest` 未暴露可写 `clientId`、`clientSecret`、`assemblyId` 属性；生成模板禁止直接赋值，客户鉴权只按美摄请求委托/服务合同接入。
- 应用权限补丁只处理 Xcode 应用 Target plist，不得修改 vendored Pod、Example、framework 或 xcframework plist。
- 已生成流程覆盖首页、拍摄、合拍、编辑、作品发布、保存草稿、草稿列表和继续编辑；签名、正式 License 和客户服务均保持用户专属。
- ShortVideo `2.0.2.1` 配置 API 支持显式开启相册/模板 `useAutoCut` 和 `NvCaptureBottomMenu.template`；原生 iOS 使用完整 `/api/app/aivideo/asset/all/1` AutoCut 端点。实际一键成片、草稿和导出仍由用户真机验收。
- ShortVideo `2.0.2.1` 已验证 AutoCut 回调 ID 不是可直接继续编辑的标准草稿 ID。生成器仅在同时检测到 project-manager 与 `NvTimelineDataManager.newProject` 等 Swift timeline API 时启用补偿：把渲染结果复制到 App 运行时沙箱，生成并保存新的标准草稿，删除草稿时清理映射媒体；原任务 ID 只用于退出 SDK。未知版本保持原 `hasDraft` 行为并告警。该路径已在真机验证可保存并继续编辑。
- ShortVideo `2.0.2.1` 原生 iOS 空工程黑盒接入已验证：新 Podfile 不应写入 `https://github.com/CocoaPods/Specs.git`，应使用 CocoaPods 已配置的 CDN/source。旧生成结果命中该精确 URL 时可安全迁移删除；不得删除客户私有 Specs source。依赖安装、无签名 Debug 构建和用户真机功能均已通过。
- ShortVideo `2.0.2.1` 已重测 `shadowOffset/shadowColor`、拍摄自动静音、最小特效/录音时长、`supportedEditModes` 和封面水印；在当前标准路径未观察到生效。公开 `NvEditConfig` 不包含 `disableTimeEffect`，不得生成该属性。
- 拍摄 15/30fps 的媒体输出符合配置，5fps 会回退；4K 可能回退到 1080p。`maxVolume` 的稳定范围收紧为 `(0,8]`。
- 交接命令只使用项目中实际发现的共享 App scheme；没有唯一共享 scheme 时先执行 `xcodebuild -list -workspace <实际 workspace>`，不得用 Target 名猜测 scheme。
