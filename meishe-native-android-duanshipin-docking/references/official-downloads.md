# 原生 Android 官方包获取

本 skill 不下载或伪造美摄 SDK。用户必须从美摄官网取得并解压原生 ShortVideo Android 包，然后提供准确的 `NvShortVideoCore.aar` 文件路径。

常见位置为官方 Demo 的应用 `libs/NvShortVideoCore.aar`，但必须以用户当前解压包为准。详细要求读取 `references/aar-acquisition.md` 和 `references/packages/native-android.md`。不得提供 Flutter 插件 AAR、React Native 包或 iOS Pod 代替。

自动发现只允许搜索 `--target-root`；不得扫描 Downloads、父目录、兄弟项目或全局磁盘。找不到 AAR 时停止，让用户提供准确路径；不得创建空 AAR 或从其他框架包猜测。
