# React Native Android 错误现象、原因与自检

仅用于 React Native Android 子路由。

- 构建成功但启动崩溃或 SDK 初始化失败：检查官方 RN AAR或插件 `jniLibs` 中 arm64-v8a、armeabi-v7a 的 `libNvStreamingSdkCore.so` 和 `libNvMSAICutter.so`。`2.0.2.0` 已验证缺库，必须停止；不得用原生 AAR掩盖 RN 包不完整。
- 日志提示 `beauty/shapePackage/facemesh/info.json` 或 `beauty/shapePackage/warp/info.json` 缺失：这是 Shape/MicroShape 美颜的配套固定资源，不是在线素材接口。核心 RN、拍摄、编辑和草稿仍可验证；对应美颜分类可能为空或不完整。向美摄索取与当前 RN AAR 匹配的资源交付，不猜测下载地址。
- 编辑完成后回首页而非作品发布：检查 Fabric/Bridgeless 是否通过 `DeviceEventEmitter` 直接监听 `VideoEditMethodChannel` 的 `VideoEditResultEvent`。
- 一键成片入口缺失：检查两个 `useAutoCut` 均为 `true`，且 `NvCaptureBottomMenuItem.template` 存在于拍摄底部菜单；不得只假设插件默认值未被其他配置覆盖。
- 一键成片模板为空或生成失败：检查 `applicationId`、官方 `/api/app` AutoCut 基础地址、服务白名单、模板标签、HTTP/业务码和素材下载。
- 一键成片后不进入作品发布：检查项目本地 `VideoEditPlugin.java`。已验证 `2.0.2.1` 的封面失败空回调必须改为发送一次空封面 `VideoEditResultEvent`，并在事件后关闭编辑页；源码形状不同不得强改。
- 发布页已进入但不能保存/导出：确认 AutoCut 结果走标准编辑页的 Next 回调，`hasDraft`、`saveDraft`、`compileCurrentTimeline` 和导出事件均正常。
- 素材列表为空：先核对 `applicationId`、官方 Demo host 白名单、权限、HTTP/业务码和预制素材布尔结果，再检查是否至少成功下载一个在线素材。
- 依赖或重复类错误：检查 AndroidX/Jetifier、仓库顺序、应用 `libs` AAR依赖和旧 support 排除项。

真机验收由用户手动覆盖初始化、拍摄、合拍、编辑发布、保存草稿和继续编辑。
