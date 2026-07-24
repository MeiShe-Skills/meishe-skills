"""Flutter route package guidance."""

FLUTTER_PACKAGE_HELP = """缺少 Flutter 接入必需的 nvshortvideo 本地插件目录。

请先获取真实 Flutter 插件包：
1. 打开 https://www.meishesdk.com/developers
2. 进入「开发者中心」->「产品及DEMO下载」。
3. 找到「移动端」->「短视频Demo」。
4. 点击「Flutter工程 vX.x.x」下载 zip 包。
5. 解压后在压缩包内找到 flutter/nvshortvideo。
6. 以下方式任选其一：
   - 将解压包根目录或 nvshortvideo 目录复制到 --target-root 目标项目内，并告知项目内路径；
   - 保留在其他本地位置，直接提供绝对路径：
     --plugin-path <absolute-extracted-package-root-or-nvshortvideo-folder>

未传 --plugin-path 时，自动查找范围仅限 --target-root 当前项目目录。如果当前项目目录内没有 nvshortvideo，脚本会停止并要求你提供路径，不会在全局范围内查找。
传入 --plugin-path 时，脚本只检查你提供的本地路径。脚本会验证真实 nvshortvideo 文件夹，并复制到目标项目 vendor/meishe/nvshortvideo。
pubspec.yaml 会使用项目内相对路径 path: vendor/meishe/nvshortvideo，不会引用外部下载/解压目录。
Flutter 的 Android 和 iOS 使用同一个官方 nvshortvideo 插件包；不要为 Flutter 额外提供 native Android AAR 或 native iOS Pods-NvShortVideoEdit。
如果 iOS quick verify 提示缺少 ios/Classes、ios/Assets 或 ios/Frameworks，请重新提供完整的「Flutter工程」zip 解压目录或其中的 flutter/nvshortvideo，不要改用 native iOS 包。
"""
