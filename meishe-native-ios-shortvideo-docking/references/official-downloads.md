# 原生 iOS 官方包获取

本 skill 不下载或伪造美摄 SDK。缺少包时必须在当前最终可见回复中完整给出以下获取方法，不得只引用本文：

1. 打开 `https://www.meishesdk.com/developers`。
2. 进入「开发者中心」->「产品及DEMO下载」->「移动端」->「短视频Demo」。
3. 下载「iOS App vX.x.x」或「iOS&Android vX.x.x」并解压，找到 `native/ios/Pods-NvShortVideoEdit/NvShortVideoEdit.podspec`。

用户可任选一种方式提供输入：

- 将解压包根目录或 `Pods-NvShortVideoEdit` 目录复制到 `--target-root` 目标项目内，并告知项目内路径；脚本只在目标项目中自动发现。
- 保留在其他本地位置，直接提供解压包根目录或 `Pods-NvShortVideoEdit` 目录的绝对路径，并作为 `--plugin-path` 传入。

脚本验证输入后复制到项目本地 `vendor/meishe/Pods-NvShortVideoEdit`。详细结构以 `references/packages/native-ios.md` 为准。不得扫描 Downloads、父目录、兄弟项目或全局磁盘，也不得提供 Flutter 插件、React Native 包或 Android AAR 代替。
