# 原生 iOS 官方包获取

本 skill 不下载或伪造美摄 SDK。用户必须从美摄官网取得并解压原生 ShortVideo iOS 包，然后提供以下任一准确路径：

- 解压后的原生 iOS 包根目录；脚本会寻找唯一 `Pods-NvShortVideoEdit/NvShortVideoEdit.podspec`。
- 直接提供包含该 podspec 的 `Pods-NvShortVideoEdit` 父级目录。

详细结构以 `references/packages/native-ios.md` 为准。不得提供 Flutter 插件、React Native 包或 Android AAR 代替。

自动发现只允许搜索 `--target-root`；不得扫描 Downloads、父目录、兄弟项目或全局磁盘。找不到或找到多个候选时停止，让用户提供准确路径。
