# Flutter Android 子路由

仅在 Flutter 目标存在 `android/` 时加载和执行。

- 检查插件 `android/libs/NvShortVideoCore.aar` 或插件 `jniLibs` 是否包含 arm64-v8a、armeabi-v7a 的 `libNvStreamingSdkCore.so` 和 `libNvMSAICutter.so`。
- 已验证的 Flutter `2.0.2.0` 包缺少上述引擎库。仅此类实际缺失场景可要求 `--aar-path` 指向版本兼容的官方 Android AAR，并且只把四个 `.so` 提取到项目本地 Flutter 插件；不得整体替换 Flutter AAR 或要求原生 Demo 成为正常第二输入。
- 补充 AAR仍缺条目时立即停止。不要把 `NvModuleManager.initSdk()` 崩溃后出现的 `MissingPluginException` 误判为 Dart 注册问题。
- 识别到已验证的旧 support 依赖形状时，在应用 `android/gradle.properties` 设置 `android.useAndroidX=true` 和 `android.enableJetifier=true`；形状不匹配时依据真实 Gradle 错误处理。
- 指定 `--android-package-name`（或兼容的 `--package-name`）时同时修改 `android/app/build.gradle.kts` 或 `build.gradle` 中的 `namespace`、`applicationId`，并更新 Kotlin/Java `MainActivity` 的 package 声明和源码目录。Kotlin DSL 与 Groovy DSL 都必须覆盖；不得只改 manifest 或只改 applicationId。
- 项目本地 `VideoEditPlugin.java` 的 `CONFIG_SERVER_INFO` 分支必须在 `initModel()` 后调用 `methodCallListener.completion(null, null)`。
- 生成 wrapper 必须显式设置 `albumConfig.useAutoCut = true`、`templateConfig.useAutoCut = true`，并在 `captureBottomMenuItems` 中保留 image/video/smart/template。
- ShortVideo `2.0.2.1` 已验证 Android bridge 的 `goPublish` 在封面保存失败时为空回调。仅在源码块精确匹配时加入单次发布帮助方法：成功发送真实封面，失败发送空封面，事件后关闭 SDK 编辑页；其他形状只报告人工检查。
- 一键成片走标准编辑页和 Next 发布页，发布页必须支持保存草稿和导出视频。Flutter 共享 `assetAutoCutUrl` 保持官方 `/api/app` 基础地址。
- 默认服务配置不含 clientId/clientSecret/assemblyId，不从 RN 路由导入服务常量。客户字段只按真实合同添加。
- 生成水印图片同时放入 Flutter `assets/`、Android `drawable-nodpi` 和 iOS Asset Catalog。默认不启用；启用前校验真实图片、正数宽高、非负偏移与合法位置。
- profile/release 真机验收分别测量冷启动、热启动和首次/再次进入原生页面。不要根据 debug 跳帧下发布性能结论，也不要在没有线程安全合同的情况下把 SDK 初始化迁到后台线程。
- Android-only Flutter 项目不得生成 iOS Pod、签名或 Xcode 后续操作。
- 生成的 Android-only README 只列 `flutter pub get`、Android Debug 构建和 `flutter run -d <ANDROID_DEVICE_ID>`，不得混入 Pod、workspace 或 iOS 设备步骤。
- 静态检查分开 `flutter analyze lib` 的生成业务代码结果与 `vendor/meishe` 官方插件告警，报告不合并两者。
- 依赖报告在应用根目录依次登记 `flutter pub get` 和 `flutter build apk --debug`；执行前必须完成 `references/dependency-installation.md` 的会话选择。
- Android 故障读取 `references/flutter/android-troubleshooting.md`。
