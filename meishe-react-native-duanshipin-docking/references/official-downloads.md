# React Native 官方包获取

本 skill 不下载或伪造美摄 SDK。用户必须从美摄官网取得并解压 React Native ShortVideo 包，然后提供以下任一准确路径：

- 解压包根目录；脚本会在其下寻找唯一 `react_native/react-native-nvshortvideo`。
- 直接提供 `react-native-nvshortvideo` 插件目录。

输入目录必须包含声明 React Native 插件的 `package.json`、`android/` 和/或 `ios/`。详细结构以 `references/packages/react-native.md` 为准。不得提供 Flutter 插件、原生 Android AAR 或原生 iOS Pod 包代替。

自动发现只允许搜索 `--target-root`；不得扫描 Downloads、父目录、兄弟项目或全局磁盘。找不到或找到多个候选时停止，让用户提供准确路径。
