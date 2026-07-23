# 原生 Android 已验证版本

- ShortVideo `2.0.2.1` 的 AAR 接入、初始化、拍摄、合拍、编辑和草稿主链路已在 Android 真机验证。该证据只证明集成兼容性；逐字段配置行为仍以能力目录中的 `2.0.1.0` 证据为准，查询 `2.0.2.1` 配置时必须返回 `unverified`，不得自动继承旧版本补丁。
- ShortVideo `2.0.1.0`、AGP `9.1.1`、Gradle `9.3.1`、compile SDK `36.1`、target SDK `36`、min SDK `24` 已构建并在 Redmi Note 7 验证。
- Android Studio Compose 模板在 compile SDK `36.1` 下已验证 Core/KTX `1.16.0`、Lifecycle Runtime KTX `2.9.4`、Activity Compose `1.8.2`；`assembleDebug` 可通过。不得恢复官方旧 Demo 的 Core `1.8.0` 强制项，否则现代 `ComponentActivity` 会缺少 `PictureInPictureProvider` 超类型。
- AAR 包含 arm64-v8a、armeabi-v7a 的两个核心引擎库；`assembleDebug`、安装、SDK 初始化通过。
- 模板导出已在 Redmi Note 7（约 3 GB RAM）验证：`compileConfig.resolution = 2` 会按 4K/2160p 导出并触发 `lowmemorykiller` 杀死前台进程，随后恢复页因内存时间线丢失出现黑屏/`timeline is null`；改为 `1`（1080p）并与官方 Demo 对齐双 ABI、`jniLibs.useLegacyPackaging = true` 后，可正常进入作品发布页。
- `--package-name` 必须同步 namespace、applicationId、源码 package/import 和目录；`--demo-launcher` 仅用于新建临时 Demo。
- 拍摄、合拍、编辑、草稿均已手工确认。Demo License、官方包名和 Debug 签名只用于首次验证，不能作为正式配置。
- 该路线的生成配置必须显式开启相册/模板 `useAutoCut` 并保留拍摄模板菜单；一键成片尚需用户按“标准编辑页 -> Next -> 保存草稿/导出视频”手工验收，不能从普通编辑通过推断。
- 当前 2.0.1.0 AAR 的单元素 `supportedEditModes` 会在进入 SDK 时失败，生成配置必须事先拒绝；自定义多元素列表也不作稳定承诺，推荐用 `editModeSource/editMode` 设置初始画幅。
- `maxVolume` 定义的可接受稳定范围为 `(0,8]`；0 必须在 SDK 调用前拒绝。菜单默认项、底部模板顺序和去重也使用同样的前置校验。
- 封面保存入口只在 AAR 精确检测到已验证的 `NvModuleManager.saveCover`、`PathUtils.getCoverDir` 和回调形状时生成；形状不匹配时不猜测调用。
- AAR 预检同时检查 `beauty/shapePackage/facemesh/info.json` 和 `beauty/shapePackage/warp/info.json`。缺少时核心拍摄/编辑仍可运行，但 Shape/MicroShape 美颜分类可能为空或不完整；这属于配套固定资源缺失，不是在线素材请求失败。
