# 原生 Android 错误现象、原因与自检

仅用于原生 Android 路由。

- 新项目尚不存在：停止并要求用户先用 Android Studio 创建真实工程，不生成伪工程。
- 初始化或页面启动失败：检查项目本地 `NvShortVideoCore.aar`、ABI、AndroidX/Jetifier、依赖仓库、权限、`init/initSdk/initModel/initConfig` 顺序和 License。
- 日志提示 `beauty/shapePackage/facemesh/info.json` 或 `beauty/shapePackage/warp/info.json` 缺失：这是 Shape/MicroShape 美颜所需的配套固定资源，不是在线素材接口。核心拍摄、合拍、编辑和草稿可以继续验证；对应美颜分类可能为空或不完整。向美摄索取与当前 AAR 匹配的资源交付，在拿到真实目录约定前不要猜测下载地址或把文件写进错误位置。
- Gradle 提示 Jetifier 已弃用：生成器为已验证的供应商依赖保留 `android.enableJetifier=true`。该提示属于工具链兼容告警，不等于 AAR 初始化失败；只有依赖报告确认所有传递依赖都已完全 AndroidX 化后才移除。`minSdk >= 21` 时生成器不再加入旧 multidex runtime，低版本或无法识别 minSdk 时才保守启用。
- 旧设备冷启动或首次进入拍摄较慢：先分段记录 Application 初始化、SDK 初始化、首页首帧、首次/再次进入各入口耗时，并区分 Debug/Release 与冷/热启动。只在 SDK 明确允许时做预加载；不得在没有线程安全合同的情况下把初始化搬到后台线程。卡顿本身不等于功能失败。
- MIUI 普通 `adb install` 返回 `INSTALL_FAILED_USER_RESTRICTED`：先让用户确认设备上的 USB 安装/安全授权和安装弹窗。只有用户明确同意设备操作后，才把 `adb push <apk> /data/local/tmp/app-debug.apk` 与 `adb shell pm install --user 0 -r /data/local/tmp/app-debug.apk` 作为 MIUI 排障路径；不得设为默认安装命令。
- Kotlin 报 `Cannot access 'PictureInPictureProvider'`，同时 `checkDebugAarMetadata` 报依赖要求更高 compile SDK：这不是美摄 AAR 缺库。原因通常是现代 Activity/Compose 与被强制降级的 AndroidX Core 不兼容，并且新模板的 Core/Lifecycle 版本要求 SDK 37，而宿主仍为 36.1。删除 Core `1.8.0` 强制降级；已验证的 compile SDK `36.1` 模板使用 Core/KTX `1.16.0`、Lifecycle Runtime KTX `2.9.4`、Activity Compose `1.8.2`。重新 Sync 后执行 `./gradlew :app:assembleDebug`，必须同时通过 `:app:checkDebugAarMetadata`、Kotlin 和 Java 编译。
- 未验证的 Compose/AndroidX 版本：先读取实际 `compileSdk` 与 Gradle 错误，不自动升级 SDK、不猜测自定义 version-catalog alias，也不把依赖元数据错误归因于短视频运行时。必要时让用户选择安装对应 SDK 或调整宿主依赖。
- 下一步无响应：检查 `setModuleManagerCallback` 和发布页路由，不能只检查拍摄/编辑入口。
- 素材一直加载或为空：所有素材、拍摄、编辑和合拍调用必须传非空 `OnAssetsRequestListener`；检查 package name/host 白名单、回调结果和至少一个在线素材闭环。
- 一键成片入口缺失：检查 `albumConfig.useAutoCut`、`templateConfig.useAutoCut` 均为 `true`，且 `captureBottomMenuItems` 包含 `capture_bottom_menu_template`；不得恢复旧的隐藏模板入口限制。
- 一键成片模板为空或生成失败：分别检查官方 Demo package name、AutoCut 服务授权、素材/标签接口、HTTP/业务码和下载链路。页面存在不代表 AutoCut 服务可用。
- 模板编辑右上角导出进行到一半后退出、返回黑屏模板页或日志出现 `timeline is null`：先检查系统日志是否包含 `lowmemorykiller: Killing '<package>'`。已验证 AAR 中 `compileConfig.resolution` 的 `0/1/2` 分别对应 720p/1080p/4K；旧模板误把 `2` 作为默认值，模板导出会按 2160p 计算，在约 3 GB RAM 真机上可触发前台进程被低内存机制杀死。生成配置必须使用 `1`（1080p），不得用 `android:largeHeap` 掩盖默认 4K 配置。
- 上述低内存问题修复后：重新构建并覆盖安装，确认 APK 内 `assets/config/config_example.json` 的 `compileConfig.resolution` 为 `1`；执行模板导出时应用 PID 不变化、日志不再出现当前包名的 `lowmemorykiller` 记录，并能进入作品发布页。只有明确需要 4K 且目标设备完成内存验收时，才允许用户主动改为 `2`。
- 一键成片后无法保存草稿或导出：确认结果进入标准编辑页，再由 Next 触发 `publishWithInfo`；检查回调中的 `needSaveDraft` / `needSaveVideo` 和生成发布页，不用独立同款模板直出流程代替验收。
- 构建成功不代表真机成功；真机安装、授权和功能验证由用户操作。
