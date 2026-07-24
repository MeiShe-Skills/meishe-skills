"""Native Android route constants and user guidance."""

DEMO_BANNER_FILE = "meishe_home_banner.jpg"

ANDROID_STUDIO_PROJECT_HELP = """未检测到可接入的原生 Android 项目。

请先在 Android Studio 中新建项目，再重新运行 skill：
1. New Project -> Phone and Tablet -> Empty Activity
2. Name: 自定义，例如 DuanshipinDemoAndroid
3. Package name: 自定义正式包名，例如 com.example.duanshipin.demo；后续申请 license/appid 时需要使用同一个包名
4. Save location: 选择目标项目目录
5. Minimum SDK: API 24 ("Nougat"; Android 7.0)
6. Build configuration language: Groovy DSL (build.gradle)

然后从美摄官网下载真实短视频 native Demo 包：
1. 打开 https://www.meishesdk.com/developers
2. 进入「开发者中心」->「产品及DEMO下载」->「移动端」->「短视频Demo」
3. 点击「iOS&Android vX.x.x」下载并解压
4. 从压缩包内 native/android/ShortVideo/app/libs/NvShortVideoCore.aar 取得 AAR

项目创建完成后，可以将 AAR 放到目标 app module 的 app/libs/NvShortVideoCore.aar 并告知项目内路径，
或保留在其他本地位置，直接提供 AAR 的绝对路径并传入 --aar-path <absolute-path-to-NvShortVideoCore.aar>。脚本会验证输入并把它复制为项目内 app/libs/NvShortVideoCore.aar，
Gradle 不会引用外部下载/解压目录。
自动查找只会检查 --target-root 指向的当前项目目录，不会扫描父目录、下载目录、用户目录、其他盘符或全局文件系统。
"""

AAR_HELP = """缺少原生 Android 接入必需的 NvShortVideoCore.aar。

只有原生 Android 使用直接 AAR 接入。请先获取真实 AAR：
1. 打开 https://www.meishesdk.com/developers
2. 进入「开发者中心」->「产品及DEMO下载」。
3. 找到「移动端」->「短视频Demo」。
4. 点击「iOS&Android vX.x.x」下载 native Demo 包和文档。
5. 解压后从 native/android/ShortVideo/app/libs/NvShortVideoCore.aar 获取 AAR。
6. 以下方式任选其一：
   - 将 AAR 复制到目标 app module 的 app/libs/NvShortVideoCore.aar，并告知项目内路径；
   - 保留在其他本地位置，直接提供 AAR 的绝对路径，重新运行并传入 --aar-path <absolute-path-to-NvShortVideoCore.aar>。
7. 脚本会验证输入并把 AAR 复制为项目内 app/libs/NvShortVideoCore.aar，Gradle 不会引用外部下载/解压目录。

自动查找范围仅限 --target-root 当前项目目录。如果当前项目目录内没有 AAR，脚本会停止并要求你提供路径，不会在全局范围内查找。

Android Studio 新建项目建议：
- Template: Empty Activity
- Name: 自定义，例如 DuanshipinDemoAndroid
- Package name: 自定义正式包名，例如 com.example.duanshipin.demo；后续申请 license/appid 时需要保持一致
- Save location: 目标项目目录
- Minimum SDK: API 24 (Nougat; Android 7.0)
- Build configuration language: Groovy DSL (build.gradle)
"""

MINIMAL_CONFIG_JSON = {
    "primaryColor": "#FC3E5A",
    "backgroundColor": "#111111",
    "panelBackgroundColor": "#1F1F1F",
    "textColor": "#FFFFFF",
    "secondaryTextColor": "#9E9E9E",
    "enableLocalMusic": False,
    "modelConfig": {"use240": True},
    "captureConfig": {
        "captureDeviceIndex": 1,
        "resolution": 1,
        "imageDuration": 3000,
        "autoSavePhotograph": False,
        "timeRanges": [
            {"minDuration": 2000, "maxDuration": 15000},
            {"minDuration": 2000, "maxDuration": 60000},
        ],
        "smartTimeRange": {"minDuration": 2000, "maxDuration": 60000},
        "face240": True,
        "autoDisablesMic": False,
        "enableCaptureAlbum": False,
        "captureBottomMenuItems": [
            "capture_bottom_menu_image",
            "capture_bottom_menu_video",
            "capture_bottom_menu_smart",
            "capture_bottom_menu_template",
        ],
        "defaultBottomMenuSelectItem": "capture_bottom_menu_video",
    },
    "editConfig": {
        "resolution": 1,
        "fps": 30,
        "minEffectDuration": 100,
        "minAudioDuration": 10000,
        "filterDefaultValue": 0.5,
        "maxVolume": 8,
        "disableTimeEffect": False,
    },
    "compileConfig": {
        "resolution": 1,
        "fps": 30,
        "bitrateGrade": 0,
        "bitrate": -1,
        "autoSaveVideo": True,
    },
    "albumConfig": {"type": 0, "maxSelectCount": 50, "useAutoCut": True},
    "templateConfig": {"maxSelectCount": 50, "useAutoCut": True},
}
