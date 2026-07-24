"""Native iOS route constants and user guidance."""

DEMO_BANNER_FILE = "meishe_home_banner.jpg"

IOS_NATIVE_SCOPE_NOTE = (
    "Native iOS integration uses safe automation for Podfile, Info.plist, "
    "license/config files, and a handoff report. Xcode target membership and "
    "custom navigation wiring may still need verification in Xcode."
)

IOS_NATIVE_PACKAGE_HELP = """缺少 native iOS 接入必需的 Pods-NvShortVideoEdit 本地 CocoaPods 包。

请先获取真实 native iOS 短视频包：
1. 打开 https://www.meishesdk.com/developers
2. 进入「开发者中心」->「产品及DEMO下载」。
3. 找到「移动端」->「短视频Demo」。
4. 点击「iOS App vX.x.x」或「iOS&Android vX.x.x」下载 native Demo 包和文档。
5. 解压后在压缩包内找到 native/ios/Pods-NvShortVideoEdit。
6. 以下方式任选其一：
   - 将解压包根目录或 Pods-NvShortVideoEdit 目录复制到 --target-root 目标项目内，并告知项目内路径；
   - 保留在其他本地位置，直接提供绝对路径：
     --plugin-path <absolute-extracted-package-root-or-Pods-NvShortVideoEdit-folder>

脚本会验证输入，并把 Pods-NvShortVideoEdit 复制到目标项目 vendor/meishe/Pods-NvShortVideoEdit，
Podfile 会使用项目内相对路径 ./vendor/meishe/Pods-NvShortVideoEdit，不会引用外部下载/解压目录。
"""
