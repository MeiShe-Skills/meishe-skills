# React Native Android 子路由

仅在 RN 目标存在 `android/` 时加载和执行。

- RN 正常输入只有官方 `react-native-nvshortvideo` 包。检查其 AAR或 `jniLibs` 是否包含 arm64-v8a、armeabi-v7a 的 `libNvStreamingSdkCore.so` 和 `libNvMSAICutter.so`。
- `2.0.2.0` 已验证为 Android runtime 不完整包；缺库时列出条目并停止，要求修正后的完整 `React Native工程` 包。不要默认要求原生 Android Demo/AAR，也不能以 `assembleDebug` 成功掩盖真机必崩。
- `2.0.2.1` 已验证包含完整引擎库。将插件自带 AAR复制到 `android/app/libs`，修补应用 `fileTree`、插件 Gradle、AndroidX/Jetifier、媒体权限和仓库顺序。
- Android 最终打包输入只检查 `android/app/src/main/assets/meishesdk.lic`。只当 applicationId 精确为 `com.meishe.duanshipindemo` 且用户明确提供的官方 RN 解压包含 Example License 时自动复制；自定义包名不复用 Demo License，只接受 `--license-path` 提供的匹配文件。
- `google()`、`mavenCentral()`、JitPack 和本地仓库优先于旧 Demo 镜像。
- Fabric/Bridgeless 发布跳转直接通过 `DeviceEventEmitter` 监听 `VideoEditMethodChannel`，仅处理 `VideoEditResultEvent`，卸载时移除订阅。
- 生成 wrapper 必须显式设置 `albumConfig.useAutoCut = true`、`templateConfig.useAutoCut = true`，并在 `captureBottomMenuItems` 中保留 image/video/smart/template；不要只依赖插件默认值。
- ShortVideo `2.0.2.1` 已验证 Android bridge 的 `goPublish` 只有封面保存成功才发送事件，封面保存失败为空回调。仅在源码块精确匹配时加入单次 `VideoEditResultEvent` 帮助方法：成功使用真实封面，失败使用空封面，事件发送后再关闭 SDK 编辑页。形状不匹配时只警告，不改 vendor。
- 一键成片必须进入标准编辑页，再由 Next 进入生成作品发布页；发布页提供保存草稿和导出视频。RN 共享 `assetAutoCutUrl` 保持官方 `/api/app` 基础地址，不改成原生 iOS 完整端点。
- 默认服务 Map 不包含 clientId/clientSecret/assemblyId 占位值；客户字段只在真实非空时加入，wrapper 在进入桥接前移除 `null`、`undefined` 和空字符串。
- Android-only RN 项目不得生成 iOS bridge、Pod、签名或 Xcode 提示。
- 依赖报告在 `android/` 根目录登记 Wrapper Debug 构建；macOS/Linux 使用 `./gradlew :app:assembleDebug`，Windows 使用 `gradlew.bat :app:assembleDebug`。执行前必须完成 `references/dependency-installation.md` 的会话选择。
- 真机验收覆盖初始化、素材准备、三个一键成片入口、标准编辑、作品发布、导出视频、保存草稿和继续编辑。
- Android 故障只读取 `references/react-native/android-troubleshooting.md`，不得套用 RN iOS 的原生 Promise、点击刷新或 ATS 补丁。
