# Flutter 官方包获取

本 skill 不下载或伪造美摄 SDK。缺少包时必须在当前最终可见回复中完整给出以下获取方法，不得只引用本文：

1. 打开 `https://www.meishesdk.com/developers`。
2. 进入「开发者中心」->「产品及DEMO下载」->「移动端」->「短视频Demo」。
3. 下载「Flutter工程 vX.x.x」并解压，找到 `flutter/nvshortvideo`。

用户可任选一种方式提供输入：

- 将解压包根目录或 `nvshortvideo` 目录复制到 `--target-root` 目标项目内，并告知项目内路径；脚本只在目标项目中自动发现。
- 保留在其他本地位置，直接提供解压包根目录或 `nvshortvideo` 目录的绝对路径，并作为 `--plugin-path` 传入。

输入目录必须包含声明 `name: nvshortvideo` 的 `pubspec.yaml` 和对应原生目录。详细结构以 `references/packages/flutter.md` 为准。不得提供 React Native 包、原生 Android AAR 或原生 iOS Pod 包作为 Flutter 主输入。

脚本验证输入后复制到项目本地 `vendor/meishe/nvshortvideo`。不得扫描 Downloads、父目录、兄弟项目或全局磁盘；找不到或找到多个候选时停止，让用户提供准确路径。
