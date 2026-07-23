# 原生 Android 执行方式与依赖命令

集成脚本不执行 Gradle Sync、依赖下载或远程构建。首次到达依赖、构建或设备操作边界时，一次性列出当前阶段每一步的绝对工作目录、完整命令/操作、执行顺序、用途和成功标志，然后只提供以下两种选择；未选择时暂停。

| 选择 | 行为 |
| --- | --- |
| `用户执行`（推荐） | 用户按清单自行执行；Agent 不再逐条询问，收到全部结果后继续。 |
| `自动执行` | Agent 执行清单中的任务内操作；选择前必须提示这会额外消耗 Token 和时间。 |

二选一与完整清单必须出现在当前轮次的最终可见回复中。即使 commentary、工具输出或报告已经展示过，也要在最终回复中重新完整列出；不得只放在折叠的“处理中”区域，不得写“命令见上文/报告”。`自动执行` 也要先展示同一份命令清单，发送后停止本轮工具调用，等用户选择后再执行。

不要改写成“是否授权”“能否操作真机”等逐项权限问题。若后续确实需要真机、截图或 Android Studio 操作，先把设备、动作、原因和预期信息补入同一份清单，再让用户重新选择。系统密码或系统安全弹窗仍由用户在系统界面确认。

## 创建工程

- 原生 Android 工程必须由用户先在 Android Studio 创建并完成所需基础设置；skill 不伪造 `settings.gradle`、wrapper 或应用 module。
- Gradle Sync 属于依赖安装边界，执行前同样需要执行方式选择。

## Gradle

- 有 Gradle Wrapper 时，在 Android 工程根目录执行 macOS/Linux `./gradlew :app:assembleDebug`，Windows `gradlew.bat :app:assembleDebug`；若 module 不是 `app`，根据实际工程替换。
- macOS 当前 Android Gradle Plugin 要求 Java 17 时，优先显式使用 Android Studio JBR，例如 `JAVA_HOME='/Applications/Android Studio.app/Contents/jbr/Contents/Home' ./gradlew :app:assembleDebug`，不得擅自修改全局 `JAVA_HOME`。
- 没有 Wrapper 时给出 Android Studio `File > Sync Project with Gradle Files` 和 `Build > Make Project`。
- 成功标志：Debug APK 生成，AAR 从应用 module 的本地 `libs/NvShortVideoCore.aar` 打包，且适用 License 位于最终 assets 输入位置。

## 真机运行

- 美摄短视频 Demo 只能运行和验收于真实 Android 设备；Android Emulator 和其他虚拟设备不受支持。
- 先运行 `adb devices` 确认真实设备，再按实际 module 执行 `./gradlew :app:installDebug`，并用 Android Studio Run 或 `adb shell am start -n <APPLICATION_ID>/<LAUNCHER_ACTIVITY>` 启动。
- Agent 在选择边界必须把 module、Application ID、Launcher Activity、设备标识和绝对工作目录替换为项目实际值，不得把未解析模板直接交给用户。

`自动执行` 只覆盖已列出的当前任务操作，不得自动修改 Gradle 镜像、代理、证书、全局 JDK 或 Android Studio 配置。网络失败先分类，再按二选一执行方式处理。
