# Flutter Android 错误现象、原因与自检

仅用于 Flutter Android 子路由。

- `NvModuleManager.initSdk()` 崩溃后出现 `MissingPluginException`：先检查核心 SO，不要先判定为 Dart 注册错误。
- 已验证 `2.0.2.0` Flutter 包缺少 `libNvStreamingSdkCore.so` 和 `libNvMSAICutter.so` 时，只有该实际缺库场景可使用版本兼容的 `--aar-path` 补四个 SO；不得整体替换 Flutter AAR。
- `configureServer()` 长时间不返回：检查 Android bridge 的 `CONFIG_SERVER_INFO` 在 `initModel()` 后是否调用 completion，并保留有界超时。
- 一键成片入口缺失：检查两个 `useAutoCut` 和 `NvCaptureBottomMenuItem.template`，不要只依赖插件构造器默认值。
- 一键成片模板为空或生成失败：核对 applicationId、官方 `/api/app` AutoCut 基础地址、白名单、模板标签、HTTP/业务码和素材下载。
- 一键成片后不进入发布页：已验证 `2.0.2.1` 的 `goPublish` 封面失败分支必须发送一次空封面 `VideoEditResultEvent`，事件后再关闭编辑页；形状不匹配时人工检查，不自动套补丁。
- 发布页不能保存/导出：确认结果先进入标准编辑页并由 Next 触发发布，检查 `hasDraft`、`saveDraft`、`compileCurrentTimeline` 和编译事件。
- 页面卡顿：区分 debug、profile、release，测量冷/热启动和首次/再次进入；没有 SDK 线程安全合同不得把初始化迁到后台线程。
- 日志提示 `beauty/shapePackage/facemesh/info.json` 或 `beauty/shapePackage/warp/info.json` 缺失：这是 Shape/MicroShape 美颜的配套固定资源，不是在线素材接口。核心拍摄、编辑和草稿仍可验证；对应美颜分类可能为空或不完整。向美摄索取与当前 Flutter AAR 匹配的资源交付，不猜测下载地址。
- `Impeller opt-out` 弃用或 `androidx.window.sidecar` `ClassNotFound` 在主链路正常时归入 Flutter/兼容库工具链告警，不误判为美摄 SDK 接入失败。仍需用构建结果和实际短视频入口判断业务状态。

真机验收由用户手动完成，不以 Gradle 构建成功推断 SDK 功能通过。
