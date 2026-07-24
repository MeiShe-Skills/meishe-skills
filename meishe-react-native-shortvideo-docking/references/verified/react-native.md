# React Native 已验证版本补丁

- RN `0.78.x`、fmt `11.0.2`、Xcode `26.x` 才应用 `FMT_USE_CONSTEVAL=0` 和对应头文件兼容补丁。
- ShortVideo `2.0.2.0` iOS bridge 已在 RN `0.78.0`、Xcode `26.6`、iPhone 15 验证 delegate 重绑定和事件先于 dismiss；源码形状不匹配时停止自动修改。
- RN Android `2.0.2.0` 包缺少核心 `.so`，判为不完整；不得要求原生 AAR作为正常补充输入。
- RN Android `2.0.2.1` AAR SHA-256 为 `0d062d95a9a5b24bc209d85b5c0db2ed09c3ff56e9a8dffbedc88da8662602a6`，已在 Redmi Note 7 验证初始化、拍摄、合拍、作品发布、保存草稿和继续编辑。
- Android Fabric/Bridgeless 使用 `DeviceEventEmitter`，iOS 使用 `NativeEventEmitter`，两端都直接监听 `VideoEditMethodChannel` 的 `VideoEditResultEvent`。
- ShortVideo `2.0.2.1` RN iOS 已在 `com.meishe.duanshipindemo` 官方 Demo 服务路径验证：官方 `configServerInfo()` JS 方法不返回原生 Promise，预制素材失败可能 resolve `false`，且拍摄/合拍/编辑入口需按官方 Demo 顺序重新非阻塞触发素材下载。
- 同一验证确认官方 RN iOS Demo 使用全局 ATS。自动生成只在官方 Demo Bundle Identifier 的临时验证路径设置 `NSAllowsArbitraryLoads = true`；客户/正式身份保持最小 ATS。未验证版本只使用运行时 API 能力检测，不修改 vendor API 或猜测版本补丁。
- ShortVideo `2.0.2.1` RN 配置 API支持显式开启两个 `useAutoCut` 和拍摄模板菜单。Android `VideoEditPlugin.java` 的已验证 `goPublish` 源码形状在封面失败时不发送事件；仅精确匹配该形状时补空封面 `VideoEditResultEvent`，未知形状保持原样并警告。
- ShortVideo `2.0.2.1` RN iOS 已验证：AutoCut callback ID 是临时任务 ID，直接落库会保存失败或得到黑屏工程。仅在 ObjC bridge、Swift timeline API 和 Xcode target 形状全部匹配时，加入 `NvDraftSnapshotBridge`、标准草稿转换、暂存/提交/放弃/删除清理生命周期及事件先于 dismiss。iOS 编译进度直接监听 `VideoEditCallbackMethodChannel`，Android 不改。真机已验证草稿可继续编辑且导出进度正常。
- ShortVideo `2.0.2.1` RN Android 已完成 117 个合法配置桥接载荷和 28 个非法输入拒绝校验；未逐项观察 UI/媒体的字段只标记 `transport_verified`。`customTheme` 的已测标题/速度键未生效，功能裁剪必须使用 TS/JS 菜单数组。
- RN Android 官方 Demo License 只能在最终 `applicationId` 为 `com.meishe.duanshipindemo` 且用户提供的官方包确实包含该文件时，复制到 `android/app/src/main/assets/meishesdk.lic`。自定义包名不复用 Demo License，只接受 `--license-path` 指定的匹配 License。
- RN 默认服务配置不得发送 `<YOUR_MEISHE_...>` 占位凭据；`clientId/clientSecret/assemblyId` 只有在用户提供真实非空值时才加入 Map。
- RN iOS 2.0.2.1 已重测拍摄自动静音、最小时长、`supportedEditModes`、封面水印和 `disableTimeEffect`，当前路径未生效或被静默忽略。视频水印只在真实图片资源可解析时承诺。
- RN Android AAR 预检区分核心引擎 `.so` 与可选 Shape/MicroShape 固定资源；后者缺失只限制相应美颜分类，不冒充在线素材请求或整个接入失败。
