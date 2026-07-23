# React Native iOS 错误现象、原因与自检

仅用于 React Native iOS 子路由。已验证组合为 ShortVideo `2.0.2.1` 官方 RN 包、React Native `0.78.0` 和 `com.meishe.duanshipindemo` 官方 Demo 服务身份。包内 npm version 为 `1.0.0`，不能只凭该字段识别 ShortVideo 发布版本；未验证包必须同时匹配桥接 API 形状才使用对应保护逻辑。

## 拍摄页在线素材全部为空

现象：拍摄、合拍、编辑和草稿可用，但拍摄内的美颜、滤镜、贴纸或音乐列表为空。

已验证原因：

- 官方 `configServerInfo()` 的 JS 方法返回 `void`，内部原生调用失败也只写日志；包装成 `Promise.resolve()` 不能代表 iOS `ConfigServerInfo` 已完成。
- `downloadPrefabricatedMaterial()` 失败时可能 resolve `false`。忽略布尔值会错误设置“素材已完成”，从而关闭前台恢复重试。
- 官方 `2.0.2.1` RN Demo 在进入拍摄、合拍和编辑前会再次非阻塞触发预制素材下载；仅在首屏后台调用一次不等价。
- 官方 RN iOS Demo 使用 `NSAllowsArbitraryLoads = true`。官方 Demo 身份的临时工程收紧 ATS 后，素材/CDN子链路可能被拦截。

生成修复：

- iOS 有 `NativeModules.VideoEditPlugin.sendMessageToNative` 时，直接发送 `ConfigServerInfo` 并等待原生 Promise；Android 和不匹配的桥接形状继续使用官方操作器。
- 仅当预制素材结果严格等于 `true` 时标记完成；`false` 或 reject 均保持失败/可重试。
- iOS 进入拍摄、合拍或编辑前先确认配置，再由 `runFeature` 直接启动非阻塞素材刷新，然后打开功能。入口不得调用首页 `prepareMaterials()`，也不得因 `preparePromise.current` 或 `materialReady.current` 而跳过；素材失败不得阻塞入口。
- 只有官方 Demo Bundle Identifier `com.meishe.duanshipindemo` 的临时验证路径自动设置全局 ATS；客户/正式工程不得继承该设置。

自检：

1. 检查 Bundle Identifier、host 和服务白名单是否属于同一环境。
2. 检查生成 wrapper 是否包含原生 `ConfigServerInfo` Promise 分支和官方操作器回退。
3. 检查 `completed !== true` 失败分支、前台恢复重试和手工重试入口。
4. 检查 iOS 点击路径的顺序为配置、直接发起素材刷新、打开功能，三个入口都传入刷新标志；确认函数体不调用 `prepareMaterials()`，且 Android 点击路径不被此补丁改变。
5. 官方 Demo 临时身份检查最终 App Info.plist 的 ATS；客户身份检查没有自动开启全局 ATS。
6. 真机手工检查美颜、滤镜、贴纸和音乐列表，至少下载并实际使用一个在线素材；页面能打开不等于请求成功。

## 一键成片自检

- 入口缺失：检查生成 wrapper 显式开启两个 `useAutoCut`，且拍摄菜单包含 `NvCaptureBottomMenuItem.template`。
- 模板为空：检查共享配置仍为官方 `https://creative.meishesdk.com/api/app` 基础地址、Bundle Identifier、ATS、标签接口和 AutoCut HTTP/业务码；不要替换成原生 iOS 完整端点。
- 完成后跳回首页：检查 `VideoEditResultEvent` 必须先于 iOS editor dismiss，并确认结果先进入标准编辑页、再由 Next 进入作品发布。
- 发布页看不到保存草稿：生成按钮必须固定在安全区域底部，不能放在长 `ScrollView` 的末尾；ShortVideo `2.0.2.1` 的 `hasDraft = false` 也不得让已验证补丁隐藏该入口。
- 保存后草稿箱为空或继续编辑全黑：不要直接持久化 `pendingPublishProjectId`，它是 AutoCut 临时任务 ID。检查 `NvDraftSnapshotBridge` 是否已加入 App target，是否生成独立标准草稿 ID，运行时视频副本是否仍存在，以及新 ID 是否能通过 `projectInfoForProject` 反查。失败必须停留发布页，不得返回首页形成假成功。
- 导出一直显示“导出中”且进度不动：官方 iOS JS operator 在该版本没有可靠转发编译事件。直接监听 `VideoEditCallbackMethodChannel` 并映射三个原生 method；同时兼容 `0...1` 和 `0...100` 进度。不得改坏 Android 的原 handler。
- 发布页应同时能保存草稿和导出视频，保存后的草稿必须能继续编辑。

仍为空时收集 Xcode 中 `ConfigServerInfo`、ATS、HTTP 状态、业务码、Bundle Identifier 白名单和 CDN 下载日志。需要真机时先列出全部设备操作和预期信息，让用户选择 `用户执行` 或 `自动执行`；自动执行会额外消耗 Token 和时间。

## CocoaPods 安装失败

- SDWebImage 等 Git Pod 报 `curl 92`、HTTP/2 `CANCEL`、`early EOF` 或 `invalid index-pack output`：这是依赖下载链路中断，不是美摄接入源码错误。保持目录、Podfile 和仓库不变，以 `GIT_HTTP_VERSION=HTTP/1.1 <报告中的 CocoaPods 命令>` 做一次进程级重试；不得写入 Git 全局配置。
- `bundle exec pod install` 报 `cannot load such file -- kconv`：检查 `ruby --version` 与 `Gemfile.lock`。精确匹配 Ruby 4.x + CocoaPods 1.15.2 时，确认项目 Gemfile 已包含 `gem 'nkf'`，执行 `bundle install` 后再执行 `bundle exec pod install`。该修复只改项目 Gemfile，不修改全局 Ruby/CocoaPods；未知版本停止自动补丁并让用户选择兼容工具链。
- Gemfile 路线必须先完成 `bundle install`，并以 `bundle exec pod --version` 作为成功标志，不能只给出后续 `bundle exec pod install`。
- 安装完成检查 `Podfile.lock`、`Pods/Manifest.lock` 和 `.xcworkspace`；前两个锁文件内容应一致，Xcode 必须打开 workspace。
