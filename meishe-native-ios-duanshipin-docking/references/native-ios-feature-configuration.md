# 原生 iOS 功能配置

本清单只适用于原生 iOS ShortVideo `2.0.2.1` 的 `NvShortVideoCore` Swift API。用户入口是 `MeisheShortVideo/MeisheFeatureConfig.swift`；不得套用 Android、React Native 或 Flutter 的字段和枚举。

机器可查询的字段与已验证边界位于 `references/config-capabilities/native-ios.json`；修改前先运行 `scripts/query_feature_config.py --track native-ios --platform ios --version 2.0.2.1 --query <自然语言>`。

## UI 与修改规则

- `captureMenuItems`、`captureBottomMenuItems`、`dualMenuItems`、`editMenuItems` 是有序字符串数组。删除常量会删除控件和下级入口，SDK 重排其余 UI；禁止空字符串占位。
- 删除 `NvEditMenuItemConstants.text` 会删除文字及其内部入口，后续菜单上移。
- 底部模式不能为空；默认项必须存在；模板存在时必须最后；数组不能重复。
- iOS 的 `editMenuItems` 只公开七项，不包含发布、下载、自动字幕。发布页的保存草稿和导出由生成的发布控制器负责，不能把其他平台枚举写入 iOS。
- 配置文件首次生成后保留手改；未验证 SDK 版本必须重新读取 Swift interface/header，不能沿用本清单猜测。

## 修改后生效

- 以生成项目 `meishe_configuration_handoff.md` 为准；从其中给出的绝对路径打开 `.xcworkspace`，确认 Swift/License/Asset Catalog 的 Target Membership，再选择实际 App scheme、Team 和设备执行 `Product > Run`（`Command-R`）。
- Swift 配置、Bundle Identifier、License、签名、Info.plist 和资源都会编译进 App，修改后必须重新 Build & Run，不能只重启旧安装包。
- 只有 Podfile、podspec 或 Pod 依赖变化时才重新执行报告中的 CocoaPods 命令；普通配置修改不默认执行 `pod install` 或 Clean Build Folder。

## NvVideoConfig

| 字段 | 类型/默认行为 | 功能与边界 |
| --- | --- | --- |
| `primaryColor` | `UIColor` | 主色。 |
| `backgroundColor` | `UIColor` | 页面背景。 |
| `panelBackgroundColor` | `UIColor` | 面板背景。 |
| `textColor` | `UIColor` | 主文字。 |
| `secondaryTextColor` | `UIColor` | 次级文字。 |
| `enableLocalMusic` | `Bool` | 本地音乐入口，仍受系统权限约束。 |
| `shadowOffset` | `CGSize` | 文字阴影偏移。 |
| `shadowColor` | `UIColor` | 阴影颜色。 |
| `albumConfig` | `NvAlbumConfig` | 相册配置。 |
| `captureConfig` | `NvCaptureConfig` | 拍摄/合拍配置。 |
| `editConfig` | `NvEditConfig` | 编辑配置。 |
| `compileConfig` | `NvCompileConfig` | 导出配置。 |
| `templateConfig` | `NvTemplateConfig` | 模板/一键成片配置。 |
| `modelConfig` | `NvModelConfig` | 模型路径，只接受当前 iOS SDK 的真实文件。 |

## 相册与模板

| 对象.字段 | 类型/生成默认值 | 功能与边界 |
| --- | --- | --- |
| `albumConfig.customTheme` | `[String:NvViewTheme]` | 高级主题，键必须来自当前 iOS `NvThemeElementKey`。 |
| `albumConfig.type` | `Int`, `0` | `0` 全部、`1` 视频、`2` 图片。 |
| `albumConfig.maxSelectCount` | `Int`, `50` | 最大素材数，必须大于 0。 |
| `albumConfig.useAutoCut` | `Bool`, `true` | 素材选择页一键成片。 |
| `templateConfig.customTheme` | `[String:NvViewTheme]` | 模板页主题。 |
| `templateConfig.maxSelectCount` | `Int`, `50` | 模板/一键成片最大片段数。 |
| `templateConfig.useAutoCut` | `Bool`, `true` | 模板页一键成片。 |
| `templateConfig.maxRecommandTemplateCount` | `Int`, `20` | 推荐模板上限；字段名沿用官方拼写。 |

## 拍摄与合拍

| 字段 | 类型/生成默认值 | 功能与边界 |
| --- | --- | --- |
| `customTheme` | `[String:NvViewTheme]` | 拍摄主题。 |
| `captureMenuItems` | `[String]`, 全部公开项 | 拍摄右侧菜单，有序。 |
| `captureBottomMenuItems` | `[String]`, 四项 | 底部模式，有序，模板最后。 |
| `defaultBottomMenuSelectItem` | `video` | 默认模式，必须存在。 |
| `captureDeviceIndex` | `UInt`, `1` | `0` 后置、`1` 前置。 |
| `resolution` | `NvVideoPreviewResolution`, `1080` | 720、1080。 |
| `ignoreVideoRotation` | `Bool`, `true` | 忽略设备旋转。 |
| `imageDuration` | `Int64`, `3000` | 图片默认时长，毫秒。 |
| `autoSavePhotograph` | `Bool`, `false` | 拍照后保存系统相册。 |
| `timeRanges` | `[NvTimePair]` | 普通录制档位，毫秒，`0 <= min < max`。 |
| `smartTimeRange` | `NvTimePair` | 快拍范围。 |
| `beautyConfig` | `NvBeautyConfig` | 美颜分类和子项。 |
| `dualMenuItems` | `[String]` | 合拍右侧菜单，独立且有序。 |
| `dualConfig` | `NvDualConfig` | 合拍布局、样式、声音。 |
| `filterDefaultValue` | `CGFloat`, `0.8` | 滤镜强度 `0.0-1.0`。 |
| `enableCaptureAlbum` | `Bool`, `false` | 拍摄页相册入口。 |
| `autoDisablesMic` | `Bool`, `false` | 自动禁用原声/麦克风。 |
| `fps` | `Int32`, `30` | iOS 有效范围 5-30。 |
| `recordConfiguration` | `[String:Any]`, 空 | 底层录制字典；已知键 `bitrate`、`gopsize`、`video encoder name`。 |

`NvCaptureMenu` 全量：`device` 翻转、`speed` 快慢速、`timer` 倒计时、`beauty` 美颜、`makeup` 美妆、`prop` 人脸道具、`matting` 抠像、`flashlight` 闪光灯、`filter` 滤镜、`original` 原声、`dualType` 合拍样式。底部全量：`image`、`video`、`smart`、`template`。

`NvDualConfig` 全量：`left`、`top`、`limitWidth`、`defaultType`、`supportedTypes` 位掩码、`autoDisablesMic`、`muteOriginal`。样式全量：`leftRight=1`、`topDown=2`、`leftRect=4`、`leftCircle=8`、`topCircle=16`。

`NvBeautyConfig` 全量：`categoricalArray`、`beautyEffectArray`、`beautyShapeArray`、`beautyMicroShapeArray`、`beautyAdjustArray`。只能使用当前模块的 `NvBeautyCategoricalItem`、`NvBeautyEffectItem`、`NvBeautyShapeItem`、`NvBeautyMicroShapeItem`、`NvBeautyAdjustItem` 字符串常量。

## 编辑

| 字段 | 类型/生成默认值 | 功能与边界 |
| --- | --- | --- |
| `customTheme` | `[String:NvViewTheme]` | 编辑主题。 |
| `editMenuItems` | `[String]`, 七项 | 编辑菜单，有序，删除后 UI 重排。 |
| `resolution` | `NvVideoPreviewResolution`, `1080` | 编辑预览分辨率。 |
| `fps` | `Int32`, `25` | 编辑预览帧率。 |
| `minEffectDuration` | `Int64`, `500` | 最小特效时长，毫秒。 |
| `minAudioDuration` | `Int64`, `1000` | 最小录音时长，毫秒。 |
| `defaultImageDuration` | `Int64`, `4000` | 图片默认时长，毫秒。 |
| `captionColor` | `String`, `#FFFFFF` | 默认字幕颜色。 |
| `captionColorList` | `[String]`, 20 色 | 字幕颜色列表。 |
| `supportedCaptionStyles` | `Int` 位掩码 | `none=1`、`bg=2`、`bgAlpha=4`、`outline=8`。 |
| `editModeSource` | `firstAsset` | `fixed` 或首素材决定。 |
| `editMode` | `mode9v16` | 固定画幅。 |
| `supportedEditModes` | `Int` 位掩码 | 九种画幅，rawValue 从 1 到 256。 |
| `bubbleConfig` | `NvBubbleConfig` | 气泡图标、标题主题、背景和模糊。 |
| `filterDefaultValue` | `CGFloat`, `0.8` | 编辑滤镜强度。 |
| `maxVolume` | `Float`, `4` | 稳定范围 `(0,8]`；`0` 会导致音量显示异常，必须在调用 SDK 前拒绝。 |

`NvEditMenuItemConstants` 全量：`edit` 裁剪、`text` 文字、`sticker` 贴纸、`effect` 特效、`filter` 滤镜、`audio` 音效、`record` 录音。原生 iOS `2.0.2.1` 未公开 `disableTimeEffect`、`release`、`download`、`caption`，禁止照搬其他路线。

`NvBubbleConfig` 全量：`editImageName`、`durationImageName`、`titleTheme`、`backgroundColor`、`backgroundBlurStyle`；模糊样式 `none=0`、`light=1`、`dark=2`。

## 导出、水印与模型

| 字段 | 类型/生成默认值 | 功能与边界 |
| --- | --- | --- |
| `compileConfig.resolution` | `1080` | 720、1080、4K；4K 需设备验证。 |
| `compileConfig.fps` | `Int`, `25` | 导出帧率。 |
| `compileConfig.bitrateGrade` | `High` | 低、中、高；`bitrate=-1` 时使用。 |
| `compileConfig.imageType` | `png` | PNG/JPEG。 |
| `compileConfig.bitrate` | `Int64`, `-1` | 非 `-1` 时覆盖等级。 |
| `compileConfig.configure` | `[String:Any]`, 空 | 底层合成字典，未知键禁止写入。 |
| `compileConfig.autoSaveVideo` | `Bool`, `true` | 导出后保存相册。 |
| `compileConfig.watermarkConfig` | `NvWatermarkConfig?` | 视频水印。 |
| `compileConfig.coverWatermarkConfig` | `NvWatermarkConfig?` | 封面水印。 |

`NvWatermarkConfig` 全量：`watermark`、`width`、`height`、`offsetX`、`offsetY`、`position`；位置为 `topRight`、`topLeft`、`bottomLeft`、`bottomRight`。图片必须是目标中的真实 `NvImageConfig` 资源名或文件路径。

`modelConfig` 全量：`use240`、`fakeface`、`face`、`face240`、`avatar`、`hand`、`humanseg`、`skysegment`、`eyecontour`、`advancedbeauty`、`facecommon`。原生 iOS `2.0.2.1` 未公开框架路线中的 AutoCut 模型路径字段；路径必须来自当前 iOS 官方包或美摄交付。

## 2.0.2.1 已验证边界

- `shadowOffset/shadowColor`、拍摄自动静音、最小特效/录音时长、`supportedEditModes` 和封面水印已重测，在当前标准入口中未观察到生效。
- 原生 iOS 2.0.2.1 没有公开 `disableTimeEffect`；生成器和自然语言修改都不得写入该属性。
- 拍摄 15/30fps 实际输出与配置一致；5fps 会发生 SDK/设备回退，必须以媒体输出为准。
- 4K 配置可稳定完成但可能回退到 1080p；`maxVolume` 只允许 `(0,8]`。
- 字幕样式列表在 `none` 与非 `none` 单元素下的 UI 行为不同，不得只以位掩码已设置推断精确裁剪。
- 外部模型、客户服务器、正式 License、未知 `configure` 字典和物理旋转保持 `limited`。
