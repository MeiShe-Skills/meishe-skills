# Flutter 已验证版本补丁

- ShortVideo `2.0.2.0`、Flutter `3.44.4`、AGP `9.0.1` 的旧 support 依赖形状需要 AndroidX 和 Jetifier；仅在依赖标记匹配时应用。
- `2.0.2.0` Flutter AAR 已验证缺少两个核心引擎库；允许从兼容官方 Android AAR只补 arm64-v8a、armeabi-v7a 的四个 `.so`，未验证版本不推广。
- Android bridge 的 `CONFIG_SERVER_INFO` 必须完成回调，避免 Dart 配置 Future 永不结束。
- Redmi Note 7 profile 验证表明首帧后 single-flight 素材准备和点击路径解耦可明显降低卡顿；SDK 初始化仍保持官方主线程路径。
- ShortVideo `2.0.2.1`、Flutter `3.44.4`、`com.meishe.duanshipindemo` 的 iOS 拍摄在线素材空列表已定位为官方 Demo ATS 差异和入口刷新时序缺失。仅该官方 Demo 临时身份启用全局 ATS；iOS 点击先等待配置回执、非阻塞刷新素材再打开功能，Android 不变。
- `2.0.2.1` 官方 Flutter Demo 服务配置不包含 clientId、clientSecret、assemblyId；生成模板不得发送这些占位值，客户字段按真实合同添加。
- ShortVideo `2.0.2.1` Flutter 配置 API支持显式开启两个 `useAutoCut` 和拍摄模板菜单。Android `VideoEditPlugin.java` 的已验证 `goPublish` 源码形状在封面失败时不回调；仅精确匹配该形状时补空封面发布事件，其他版本不改 vendor。
- ShortVideo `2.0.2.1` Flutter iOS 的 AutoCut callback ID 是临时任务 ID，旧的直接落库补偿已禁用。仅在 bridge、Swift timeline API 和 Pod source 形状精确匹配时生成 `NvDraftSnapshotBridge`，把模型或渲染结果转换为新标准草稿，并管理暂存、提交、放弃和删除清理；事件仍先于 dismiss。未知版本不改 vendor。该路径的草稿、继续编辑和导出已由用户真机确认。
- ShortVideo `2.0.2.1`、Flutter `3.44.4` 双端黑盒接入已验证：Android Debug APK 构建与 iOS CocoaPods 安装均通过，双端功能由用户确认正常。现代 Flutter iOS 模板缺少 Podfile/Profile 配置时，需生成显式 iOS 13.0 Podfile、三套按实际 App Target 命名的 Pods xcconfig include，并把应用 Profile 指向 `Profile.xcconfig`。
- 同一验证组合确认兼容参数 `--package-name` 可同时更新双端身份；`--android-package-name`、`--ios-bundle-identifier` 用于双端不同身份。运行 README 使用受控标记块更新，重复接入不得覆盖用户说明或重复生成平台章节。
- ShortVideo `2.0.2.1` Flutter Android 已完成 117 个合法序列化/桥接输入和 28 个非法输入拒绝校验；未逐项真机观察的字段只标记 `transport_verified`。
- Flutter Android `customTheme` 的已测速度按钮/标题键未生效，菜单裁剪使用 Dart 有序数组。Flutter iOS 的自动静音、最小时长、`supportedEditModes`、封面水印和 `disableTimeEffect` 未生效或静默忽略。
- 水印只在生成的 Android drawable、iOS Asset Catalog 和 Flutter asset 都含真实图片，且尺寸、偏移、位置通过预校验时才启用。
- Flutter Android AAR 预检区分核心引擎 `.so` 与可选 Shape/MicroShape 固定资源；后者缺失只限制相应美颜分类，不冒充在线素材请求或整个接入失败。
- Flutter iOS Debug 必须通过 `flutter run` 或 Xcode 启动；直接 `devicectl` 启动触发 Debug Engine 限制属于 Flutter 调试机制。`NvCodable` 截断 JSON 和 `fxExpression` 未授权分别按供应商载荷诊断与 License 权益边界记录。
