# 原生 iOS 执行方式与依赖命令

集成脚本不执行 CocoaPods 下载、`xcodebuild` 或远程依赖解析。首次到达依赖、构建或设备操作边界时，一次性列出当前阶段每一步的绝对工作目录、完整命令/操作、执行顺序、用途和成功标志，然后只提供以下两种选择；未选择时暂停。

| 选择 | 行为 |
| --- | --- |
| `用户执行`（推荐） | 用户按清单自行执行；Agent 不再逐条询问，收到全部结果后继续。 |
| `自动执行` | Agent 执行清单中的任务内操作；选择前必须提示这会额外消耗 Token 和时间。 |

二选一与完整清单必须出现在当前轮次的最终可见回复中。即使 commentary、工具输出或报告已经展示过，也要在最终回复中重新完整列出；不得只放在折叠的“处理中”区域，不得写“命令见上文/报告”。`自动执行` 也要先展示同一份命令清单，发送后停止本轮工具调用，等用户选择后再执行。

不要改写成“是否授权”“能否操作真机”等逐项权限问题。若后续确实需要真机、截图或 Xcode 操作，先把设备、动作、原因和预期信息补入同一份清单，再让用户重新选择。系统密码、钥匙串或系统安全弹窗仍由用户在系统界面确认。

受操作系统、Ruby/CocoaPods、Xcode、网络、签名和设备环境差异影响，手动接入或运行可能报错。遇到任何报错，提示用户复制执行命令和完整原始报错信息发给当前 Agent 继续处理；不要只截取最后一行，也不要求用户自行猜测修复。

## 新建工程身份

- 当前任务新建原生 iOS 工程时，接入脚本必须追加：`--ios-bundle-identifier com.meishe.duanshipindemo`。
- 已有工程不默认追加该参数；先报告 App Target 当前值和官方服务限制，再按用户选择决定是否修改。

## CocoaPods

- 在包含 `Podfile` 的原生 iOS 工程根目录执行 `bundle install`，随后优先执行 `bundle exec pod install`；项目未使用 Bundler 时才执行 `pod install`。
- 成功标志：生成或更新 `.xcworkspace` 和 `Pods/Manifest.lock`，`NvShortVideoEdit` 路径指向项目本地 `vendor/meishe/Pods-NvShortVideoEdit`。
- Ruby 4.x 与 CocoaPods 1.15.2 出现 `cannot load such file -- kconv` 时属于工具链兼容问题，按报告使用兼容 Ruby/CocoaPods 组合，不修改业务 Pod 或 vendored SDK。
- Git CDN/Specs 网络异常只可对当前命令临时使用 `GIT_HTTP_VERSION=HTTP/1.1`，不得执行 `pod repo add`、写入 Git 全局 HTTP 配置、删除客户私有 Specs source 或擅自切换镜像。

## 静态构建

- 依赖完成后，**推荐使用 Xcode** 打开生成的 `.xcworkspace`，选择实际 Scheme、签名 Team 和真实设备，执行 `Product > Run`。
- **命令行运行方式也必须完整提供**：列出设备查询、`xcodebuild` 真机构建、`xcrun devicectl device install app` 安装和 `xcrun devicectl device process launch` 启动命令。不得把命令行称为备选、可选或省略。
- 无签名静态构建需要根据实际 workspace/scheme 给出准确 `xcodebuild` 命令；不得猜测 scheme。
- 成功标志：Pod 能链接，Swift 编译无错误；签名、License 和真机行为仍分别验收。

## 真机运行

- 美摄短视频 Demo 只能运行和验收于真实 iPhone 或 iPad；iOS Simulator 和其他虚拟设备不受支持。
- 先运行 `xcrun devicectl list devices` 确认真实设备。推荐在 Xcode 打开实际 `.xcworkspace`，选择 App Scheme、签名 Team 和真实设备，执行 `Product > Run`；同时提供完整命令行构建、安装和启动流程。
- Agent 在选择边界必须列出实际 workspace 绝对路径、Scheme、Bundle Identifier、设备标识、构建产物路径、完整 Xcode 操作、完整命令行和成功标志；不得保留可由工程检测确定的占位符。

`自动执行` 只覆盖已列出的当前任务操作，不得自动修改证书、Team、profile、Keychain、代理或全局 Ruby 配置。接入后明确提示用户查看目标项目根目录 `README.md`，其中包含项目运行详细说明。
