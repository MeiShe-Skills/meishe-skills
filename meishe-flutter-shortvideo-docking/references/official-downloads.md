# Flutter 官方包获取

本 skill 不下载或伪造美摄 SDK。用户必须从美摄官网取得并解压 Flutter ShortVideo 包，然后提供以下任一准确路径：

- 解压包根目录；脚本会在其下寻找唯一 `flutter/nvshortvideo`。
- 直接提供 `nvshortvideo` 插件目录。

输入目录必须包含声明 `name: nvshortvideo` 的 `pubspec.yaml` 和对应原生目录。详细结构以 `references/packages/flutter.md` 为准。不得提供 React Native 包、原生 Android AAR 或原生 iOS Pod 包作为 Flutter 主输入。

自动发现只允许搜索 `--target-root`；不得扫描 Downloads、父目录、兄弟项目或全局磁盘。找不到或找到多个候选时停止，让用户提供准确路径。
