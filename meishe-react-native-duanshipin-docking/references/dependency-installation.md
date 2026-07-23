# React Native 执行方式与依赖命令

集成脚本不执行 npm/Yarn/pnpm、CocoaPods、Gradle 下载或远程构建。首次到达依赖、构建或设备操作边界时，一次性列出当前阶段每一步的绝对工作目录、完整命令/操作、执行顺序、用途和成功标志，然后只提供以下两种选择；未选择时暂停。

| 选择 | 行为 |
| --- | --- |
| `用户执行`（推荐） | 用户按清单自行执行；Agent 不再逐条询问，收到全部结果后继续。 |
| `自动执行` | Agent 执行清单中的任务内操作；选择前必须提示这会额外消耗 Token 和时间。 |

二选一与完整清单必须出现在当前轮次的最终可见回复中。即使 commentary、工具输出或报告已经展示过，也要在最终回复中重新完整列出；不得只放在折叠的“处理中”区域，不得写“命令见上文/报告”。`自动执行` 也要先展示同一份命令清单，发送后停止本轮工具调用，等用户选择后再执行。

不要改写成“是否授权”“能否操作真机”等逐项权限问题。若后续确实需要真机、截图或 IDE 操作，先把设备、动作、原因和预期信息补入同一份清单，再让用户重新选择。系统密码、钥匙串或系统安全弹窗仍由用户在系统界面确认。

## 创建项目

- 已验证 React Native `0.78.0` / Community CLI `15.0.1` 可使用：`npx @react-native-community/cli@15.0.1 init <project-name> --version 0.78.0 --skip-install`。
- 当前任务新建且包含 iOS 时，随后执行接入脚本必须追加：`--ios-bundle-identifier com.meishe.duanshipindemo`。
- `npx` 仍可能下载 CLI，因此执行前同样需要执行方式选择。已有项目时不得重新初始化。

## JavaScript 依赖

- 优先读取 `package.json#packageManager`；否则只允许一个 `pnpm-lock.yaml`、`yarn.lock` 或 `package-lock.json`。
- 对应命令分别为 `pnpm install`、`yarn install`、`npm install`。多个锁文件且未声明 package manager 时，在目标写入前失败，不猜测。
- 成功标志：`node_modules/react-native-nvshortvideo` 能解析到项目本地 `vendor/meishe/react-native-nvshortvideo`。

## iOS

- 在实际 `ios/` 目录执行 `bundle install`，随后优先执行 `bundle exec pod install`；项目未使用 Bundler 时才执行 `pod install`。
- 已验证的 Ruby 4.x + CocoaPods 1.15.2 组合由 Skill 在项目 Gemfile 中幂等加入 `gem 'nkf'`，继续执行 `bundle install` 和 `bundle exec pod install`，不要求修改全局 Ruby 或 CocoaPods。
- 成功标志：生成或更新 `.xcworkspace`、`Pods/Manifest.lock`，且 Pod 路径指向项目本地 vendor。
- Ruby 4.x 与 CocoaPods 1.15.2 出现 `cannot load such file -- kconv` 时属于工具链问题；先确认项目 Gemfile 含 `gem 'nkf'` 并重新执行 Bundler。未知 CocoaPods 版本不得自动套用该补丁。
- Git CDN/Specs 网络异常只可对当前命令临时使用 `GIT_HTTP_VERSION=HTTP/1.1`，不得写入 Git 全局配置或擅自切换镜像。

## Android

- 有 Gradle Wrapper 时，在 `android/` 执行 macOS/Linux `./gradlew :app:assembleDebug`，Windows `gradlew.bat :app:assembleDebug`。
- 没有 Wrapper 时给出 Android Studio `File > Sync Project with Gradle Files` 和 `Build > Make Project`。
- 成功标志：Debug APK 生成，且最终打包输入包含项目本地插件和适用 License。

## 真机运行

- 美摄短视频 Demo 只能运行和验收于真实设备；Android Emulator、iOS Simulator 和其他虚拟设备不受支持。
- Android 先运行 `adb devices` 确认真实设备，再在项目根目录运行 `npm run android -- --deviceId <ANDROID_DEVICE_ID>`。
- iOS 先运行 `xcrun devicectl list devices` 确认真实 iPhone/iPad，再在项目根目录运行 `npm run ios -- --udid <IOS_DEVICE_UDID>`；也可打开实际 `.xcworkspace`，选择真实设备后执行 Product > Run。
- Agent 在选择边界必须把占位符替换成已检测到的实际设备标识、绝对工作目录和适用平台命令；单端项目不得展示另一端命令。

双端项目按 JavaScript、iOS、Android 顺序展示；单端项目不得包含另一端命令。`自动执行` 只覆盖已列出的当前任务操作，不得自动改 registry、代理、证书、Gradle 镜像或全局工具配置。
