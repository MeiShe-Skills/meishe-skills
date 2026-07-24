# Flutter iOS 错误现象、原因与自检

仅用于 Flutter iOS 子路由。素材空列表问题已验证于 ShortVideo `2.0.2.1` 官方 Flutter 包、Flutter `3.44.4` 和官方 Demo 身份 `com.meishe.duanshipindemo`。

- `configureServer()` 或预制素材 Future 一直不结束：检查 `VideoEditPlugin.swift` 的 `ConfigServerInfo` 和 `DownloadPrefabricatedMaterialCompletionMethod` 分支是否在所有结果路径调用 completion，并保留有界超时。
- 在线素材为空但拍摄等页面能打开：对比官方 Demo 后确认其 `Info.plist` 使用 `NSAllowsArbitraryLoads = true`，且每次进入拍摄、合拍、编辑前都会再次非阻塞调用预制素材下载。官方 Demo 身份临时工程应对齐这两项；客户身份只使用真实域名级 ATS 例外。
- 生成自检：确认 iOS 点击顺序为等待 `ConfigServerInfo` 回执、由 `_runFeature` 直接非阻塞发起素材刷新、打开功能；三个入口都传入 `refreshMaterials: true`。入口不得调用首页 `_prepareMaterialsInBackground()`，也不得因 `_materialPreparation` / `_isPreparingMaterials` 而跳过；Android 点击路径不变。
- 配置自检：官方 Demo map 只包含 host、素材接口和 `isAbroad`，不得发送 `<YOUR_MEISHE_CLIENT_ID>` 等伪值。客户鉴权字段必须来自真实服务器合同。
- Pod 构建失败：检查项目本地 `ios/nvshortvideo.podspec`、Frameworks、Assets、Podfile 部署版本和 `pod install` 结果。
- `Automatically assigning platform iOS`：Podfile 缺少显式 `platform :ios`；使用插件 podspec 的最低版本生成或修正 Podfile，不要依赖 CocoaPods 推断。
- `CocoaPods did not set the base configuration`：先确认实际 App Target，再检查三套 xcconfig 是否分别包含对应 `Pods-<AppTarget>` 配置，Profile 是否仍误指向 `Release.xcconfig`。
- `pod install` 成功但 Xcode 链接不到 Pod：关闭当前 `.xcodeproj` 窗口，改为打开实际工程对应的 `.xcworkspace`；该现象不是美摄 SDK 资源请求失败。
- 签名失败：Team、证书和 profile 只报告给用户配置，不写入通用 skill。
- 一键成片入口缺失：检查两个 `useAutoCut` 均为 `true`，并确认拍摄菜单包含 `NvCaptureBottomMenuItem.template`。
- 一键成片模板为空：共享配置必须保持 `https://creative.meishesdk.com/api/app` 基础地址；继续检查 Bundle Identifier、ATS、模板标签和 AutoCut HTTP/业务码，不套用原生 iOS 完整端点。
- 一键成片完成后跳回首页：确认结果先进入标准编辑页，再由 Next 的 `NvVideoEditEvent.publish` 进入作品发布页。
- 一键成片点击保存后草稿箱为空或继续编辑全黑：`hasDraft = false` 只表示 SDK 默认发布页不提供草稿入口；callback `projectId` 是临时任务 ID，不能直接 `storeCurrentProject`。检查 `NvDraftSnapshotBridge.swift` 是否进入 Pod source、是否生成新标准草稿 ID、运行时媒体副本是否存在，以及删除/放弃清理是否执行。
- 发布页必须同时验证保存草稿、草稿继续编辑和导出视频；原生保存失败时必须留在当前页显示错误，不能先 pop 页面或调用 `exitVideoEdit` 形成假成功。
- 日志出现 `NvCodable.swift ... invalid JSON ... unexpected EOF`：记录发生入口、桥接原始值是否为空、字符串长度和前后截断片段；不得吞掉异常或把截断 JSON 当作成功数据。若编辑、发布、草稿保存和续编均完成，可暂记为非阻塞供应商诊断，但复现时仍需把完整上下文交给美摄。
- 日志出现 `Functionality fxExpression is not authorised!`：这是当前 License 对特定表达式能力的授权边界，不等于 SDK 初始化或基础编辑失败。单独验证该功能，并使用与最终 Bundle Identifier 匹配且包含对应权益的正式 License 复测。
- Flutter iOS Debug 包应通过活动 `flutter run -d <IOS_DEVICE_ID>` 会话或 Xcode Product > Run 启动。直接用 `devicectl` 启动可能触发 Flutter Debug Engine 限制，可用于设备/安装诊断，但不能作为默认启动方式或接入失败证据。

仍为空时检查 Xcode 中的 ATS、`ConfigServerInfo`、HTTP 状态、业务码、Bundle Identifier 白名单和 CDN 下载日志。Windows 只做静态检查；Mac 需要构建或真机时先列出全部操作，让用户选择 `用户执行` 或 `自动执行`，并提示自动执行会额外消耗 Token 和时间。
