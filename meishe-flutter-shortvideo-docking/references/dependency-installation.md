# Flutter 执行方式与依赖命令

集成脚本不执行 Flutter Pub、CocoaPods、Gradle 下载或远程构建。首次到达依赖、构建或设备操作边界时，一次性列出当前阶段每一步的绝对工作目录、完整命令/操作、执行顺序、用途和成功标志，然后只提供以下两种选择；未选择时暂停。

| 选择 | 行为 |
| --- | --- |
| `用户执行`（推荐） | 用户按清单自行执行；Agent 不再逐条询问，收到全部结果后继续。 |
| `自动执行` | Agent 执行清单中的任务内操作；选择前必须提示这会额外消耗 Token 和时间。 |

二选一与完整清单必须出现在当前轮次的最终可见回复中。即使 commentary、工具输出或报告已经展示过，也要在最终回复中重新完整列出；不得只放在折叠的“处理中”区域，不得写“命令见上文/报告”。`自动执行` 也要先展示同一份命令清单，发送后停止本轮工具调用，等用户选择后再执行。

不要改写成“是否授权”“能否操作真机”等逐项权限问题。若后续确实需要真机、截图或 IDE 操作，先把设备、动作、原因和预期信息补入同一份清单，再让用户重新选择。系统密码、钥匙串或系统安全弹窗仍由用户在系统界面确认。

受操作系统、Flutter/Dart、Ruby/CocoaPods、JDK/Gradle、Xcode、网络、签名和设备环境差异影响，手动接入或运行可能报错。遇到任何报错，提示用户复制执行命令和完整原始报错信息发给当前 Agent 继续处理；不要只截取最后一行，也不要求用户自行猜测修复。

## 创建项目与 Dart 依赖

- 新项目优先在目标父目录执行 `flutter create --no-pub <project-name>`；已有项目不得重新初始化。
- 当前任务新建且包含 iOS 时，随后执行接入脚本必须追加：`--ios-bundle-identifier com.meishe.duanshipindemo`。
- 接入完成后在应用根目录执行 `flutter pub get`。
- 成功标志：`.dart_tool/package_config.json` 中 `nvshortvideo` 解析到项目本地 `vendor/meishe/nvshortvideo`。

## iOS

- 在实际 `ios/` 目录执行 `bundle install`，随后优先执行 `bundle exec pod install`；项目未使用 Bundler 时才执行 `pod install`。
- 成功标志：实际 Xcode 工程对应的 `.xcworkspace`、`Pods/Manifest.lock` 存在，Pod 与 Flutter plugin 都指向项目本地路径。
- Ruby 4.x 与 CocoaPods 1.15.2 出现 `cannot load such file -- kconv` 时属于工具链问题，按报告使用兼容 Ruby/CocoaPods 组合，不修改业务 Pod。
- Git CDN/Specs 网络异常只可对当前命令临时使用 `GIT_HTTP_VERSION=HTTP/1.1`，不得写入 Git 全局配置或擅自切换镜像。
- 依赖完成后，**推荐使用 Xcode** 打开实际 `.xcworkspace`，选择 App Scheme、签名 Team 和真实设备后执行 `Product > Run`。
- **命令行运行方式也必须完整提供**：在项目根目录执行 `flutter run -d <IOS_DEVICE_ID>`。不得把命令行称为备选、可选或省略。

## Android

- 在应用根目录执行 `flutter build apk --debug`；需要指定设备运行时执行 `flutter run -d <ANDROID_DEVICE_ID>`。
- 成功标志：`build/app/outputs/flutter-apk/app-debug.apk` 生成，且最终打包输入包含项目本地插件和适用 License。

## 真机运行

- 美摄短视频 Demo 只能运行和验收于真实设备；Android Emulator、iOS Simulator 和其他虚拟设备不受支持。
- 在项目根目录运行 `flutter devices`，确认目标是已连接的真实设备。Android 运行 `flutter run -d <ANDROID_DEVICE_ID>`；iOS 推荐用 Xcode 打开实际 `.xcworkspace` 执行 `Product > Run`，同时必须提供 `flutter run -d <IOS_DEVICE_ID>` 命令行。
- Agent 在选择边界必须把占位符替换成 `flutter devices` 返回的实际设备标识和绝对项目目录；双端分别列命令，单端项目不得展示另一端命令。

双端项目按 Dart、iOS、Android 顺序展示；单端项目不得包含另一端命令。`自动执行` 只覆盖已列出的当前任务操作，不得自动改 Pub 源、Gradle 镜像、代理、证书或全局工具配置。接入后明确提示用户查看目标项目根目录 `README.md`，其中包含项目运行详细说明。
