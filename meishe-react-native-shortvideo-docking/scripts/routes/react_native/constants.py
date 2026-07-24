"""React Native route package guidance."""

REACT_NATIVE_PLUGIN_NAME = "react-native-nvshortvideo"

REACT_NATIVE_PACKAGE_HELP = """缺少 React Native 接入必需的 react-native-nvshortvideo 本地插件目录。

请先获取真实 React Native 插件包：
1. 打开 https://www.meishesdk.com/developers
2. 进入「开发者中心」->「产品及DEMO下载」。
3. 找到「移动端」->「短视频Demo」。
4. 点击「React Native工程 vX.x.x」下载 zip 包。
5. 解压后在压缩包内找到 react_native/react-native-nvshortvideo。
6. 重新运行时提供包含 react_native/react-native-nvshortvideo 的解压根目录，或直接提供 react-native-nvshortvideo 插件目录：
   --plugin-path <extracted-package-root-or-react-native-nvshortvideo-folder>

未传 --plugin-path 时，自动查找范围仅限 --target-root 当前项目目录。如果当前项目目录内没有 react-native-nvshortvideo，脚本会停止并要求你提供路径，不会在全局范围内查找。
传入 --plugin-path 时，脚本只检查你提供的路径，找到真实 react-native-nvshortvideo 文件夹，并复制到目标项目 vendor/meishe/react-native-nvshortvideo。
package.json / lockfile 会使用 file:vendor/meishe/react-native-nvshortvideo，不会引用外部下载/解压目录。
React Native 的 Android 和 iOS 使用同一个官方 react-native-nvshortvideo npm 包；不要为 RN 额外提供 native Android AAR 或 native iOS Pods-NvShortVideoEdit。
如果 iOS readiness failed 提示缺少 ios/Classes、ios/Assets 或 ios/Frameworks，请重新提供完整的「React Native工程」zip 解压目录或其中的 react_native/react-native-nvshortvideo，不要改用 native iOS 包。
"""

