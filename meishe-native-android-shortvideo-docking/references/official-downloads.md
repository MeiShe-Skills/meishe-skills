# 原生 Android 官方包获取

本 skill 不下载或伪造美摄 SDK。缺少包时必须在当前最终可见回复中完整给出以下获取方法，不得只引用本文：

1. 打开 `https://www.meishesdk.com/developers`。
2. 进入「开发者中心」->「产品及DEMO下载」->「移动端」->「短视频Demo」。
3. 下载「iOS&Android vX.x.x」并解压，取得 `native/android/ShortVideo/app/libs/NvShortVideoCore.aar`。

用户可任选一种方式提供输入：

- 将 AAR 复制到目标项目，例如 `<target>/app/libs/NvShortVideoCore.aar`，并告知项目内路径；脚本只在 `--target-root` 中自动发现。
- 保留在其他本地位置，直接提供 `NvShortVideoCore.aar` 的绝对路径，并作为 `--aar-path` 传入。

脚本验证输入后复制到应用 module 的 `libs/NvShortVideoCore.aar`。详细要求读取 `references/aar-acquisition.md` 和 `references/packages/native-android.md`。不得扫描 Downloads、父目录、兄弟项目或全局磁盘，不得创建空 AAR，也不得提供 Flutter 插件 AAR、React Native 包或 iOS Pod 代替。
