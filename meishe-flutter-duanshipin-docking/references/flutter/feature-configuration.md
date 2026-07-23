# Flutter 功能配置

本清单只适用于官方 Flutter 包 `2.0.2.1` 的 Dart API。用户入口是生成项目中的 `lib/meishe_feature_config.dart`；不要修改 `ios/`、`android/` 或插件桥接源码来配置业务功能。

机器可查询的字段、别名、平台状态和证据等级位于 `references/config-capabilities/flutter.json`；修改前先运行 `scripts/query_feature_config.py --track flutter --platform <android|ios> --version 2.0.2.1 --query <自然语言>`。

## UI 与修改规则

- `captureMenuItems`、`captureBottomMenuItems`、`dualMenuItems`、`editMenuItems` 是有序数据源。删除枚举会删除对应控件和下级入口，剩余控件由 SDK 重排；禁止用 `null`、空值、透明控件或隐藏 Widget 占位。
- 删除 `NvEditMenuItem.text` 会删除文字及其内部入口，后续菜单上移，不留空白。
- 拍摄底部数组不能为空，默认项必须存在，`template` 存在时必须最后，菜单数组不能重复。
- 删除 `release`、`download` 前必须确认发布、导出和草稿流程仍可达。
- 配置文件首次生成后必须保留用户手改。Flutter 配置同时下发 iOS、Android；桥接差异写入注释和本清单，不生成两份用户配置。

## 修改后生效

- 以生成项目 `meishe_configuration_handoff.md` 的绝对路径和命令为准。活动 Debug 会话修改 Dart 后至少在 `flutter run` 终端执行大写 `R`（Hot Restart）；小写 `r` 的 Hot Reload 不保证重建 `NvVideoConfig`。
- 没有活动会话、当前是 Release 包，或原生文件、包名、Bundle Identifier、License、签名和资源发生变化时，执行当前子平台的 `flutter run -d <DEVICE_ID>` 重新构建安装。
- 只有 `pubspec.yaml`、Podfile 或原生依赖声明变化时才重新解析依赖；普通配置修改不要求 `flutter pub get` 或 `flutter clean`。

## NvVideoConfig

| 字段 | 类型/默认值 | 功能与边界 |
| --- | --- | --- |
| `primaryColor` | `String`, `#FC3E5A` | 主色，`#RRGGBB`。 |
| `backgroundColor` | `String`, `#000000` | 页面背景。 |
| `panelBackgroundColor` | `String`, `#1C1C1C` | 面板背景。 |
| `textColor` | `String`, `#FFFFFF` | 主文字。 |
| `secondaryTextColor` | `String`, `#6C6C77` | 次级文字。 |
| `enableLocalMusic` | `bool`, `true` | 本地音乐入口，仍受系统权限约束。 |
| `shadowOffset` | `Size`, `(0,0.5)` | 文字阴影偏移。 |
| `shadowColor` | `String`, `#00000080` | RGBA 阴影色。 |
| `albumConfig` | `NvAlbumConfig` | 相册配置。 |
| `captureConfig` | `NvCaptureConfig` | 拍摄/合拍配置。 |
| `editConfig` | `NvEditConfig` | 编辑配置。 |
| `compileConfig` | `NvCompileConfig` | 导出配置。 |
| `templateConfig` | `NvTemplateConfig` | 模板/一键成片配置。 |
| `modelConfig` | `NvModelConfig` | 模型路径，只接受当前 SDK 的真实模型。 |

## 相册与模板

| 对象.字段 | 类型/默认值 | 功能与边界 |
| --- | --- | --- |
| `albumConfig.customTheme` | `Map?` | 高级主题，键和值必须来自当前 Flutter 包。 |
| `albumConfig.type` | `int`, `0` | `0` 全部、`1` 视频、`2` 图片。 |
| `albumConfig.maxSelectCount` | `int`, `50` | 最大素材数，必须大于 0。 |
| `albumConfig.useAutoCut` | `bool`, `true` | 素材选择页一键成片，不控制拍摄模板模式。 |
| `templateConfig.customTheme` | `Map?` | 模板页高级主题。 |
| `templateConfig.maxSelectCount` | `int`, `50` | 模板/一键成片最大片段数。 |
| `templateConfig.useAutoCut` | `bool`, `true` | 模板页一键成片。 |
| `templateConfig.maxRecommandTemplateCount` | `int`, `20` | 推荐模板上限；字段名沿用官方拼写。 |

## 拍摄与合拍

| 字段 | 类型/默认值 | 功能与边界 |
| --- | --- | --- |
| `customTheme` | `Map?` | 拍摄页高级主题。 |
| `captureMenuItems` | `List<NvCaptureMenuItem>`, 全部 | 拍摄右侧菜单，有序。 |
| `captureBottomMenuItems` | `List<NvCaptureBottomMenuItem>`, 全部 | 拍摄底部模式，有序，模板最后。 |
| `defaultBottomMenuSelectItem` | `video` | 默认项，必须存在于底部数组。 |
| `captureDeviceIndex` | `int`, `1` | `0` 后置、`1` 前置。 |
| `resolution` | `NvVideoPreviewResolution`, `1080` | 720、1080。 |
| `ignoreVideoRotation` | `bool`, `true` | 忽略设备旋转。 |
| `imageDuration` | `int`, `3000` | 图片默认时长，毫秒。 |
| `autoSavePhotograph` | `bool`, `false` | 拍照后是否保存系统相册。 |
| `timeRanges` | `List<NvTimePair>` | 普通录制档位，毫秒，`0 <= min < max`。 |
| `smartTimeRange` | `NvTimePair` | 快拍范围。 |
| `beautyConfig` | `NvBeautyConfig?` | 美颜分类和子项。 |
| `dualMenuItems` | `List<NvCaptureMenuItem>` | 合拍右侧菜单，独立且有序。 |
| `dualConfig` | `NvDualConfig?` | 合拍布局、样式、声音。 |
| `filterDefaultValue` | `double`, `0.8` | 滤镜强度 `0.0-1.0`。 |
| `enableCaptureAlbum` | `bool`, 默认未显式说明 | 拍摄页相册入口；生成默认 `false`。 |
| `autoDisablesMic` | `bool`, `false` | 自动禁用原声/麦克风。 |
| `fps` | `int`, `30` | 拍摄帧率，修改需验证两端。 |
| `recordConfiguration` | `Map<String,dynamic>?`, `{}` | 底层录制字典；已知键为 `bitrate`、`gopsize`、`video encoder name`。 |

拍摄菜单全量：`device` 翻转、`speed` 快慢速、`timer` 倒计时、`beauty` 美颜、`makeup` 美妆、`prop` 人脸道具、`matting` 抠像、`flashlight` 闪光灯、`filter` 滤镜、`original` 原声、`dualtype` 合拍样式。底部模式全量：`image`、`video`、`smart`、`template`。

`NvDualConfig` 全量：`left=17/375`、`top=18/666.67`、`limitWidth=153.5/375`、`defaultType=leftRight`、`supportedTypes`、`autoDisablesMic=false`、`muteOriginal=true`。样式为 `leftRight`、`topDown`、`leftRect`、`leftCircle`、`topCircle`。

`NvBeautyConfig` 全量：`categoricalArray`、`beautyEffectArray`、`beautyShapeArray`、`beautyMicroShapeArray`、`beautyAdjustArray`。分类为 `Skin`、`Shape`、`MicroShape`、`Adjust`；子项分别使用 `NvBeautyEffect`、`NvBeautyShape`、`NvBeautyMicroShape`、`NvBeautyAdjust` 当前 Dart 枚举。

## 编辑

| 字段 | 类型/默认值 | 功能与边界 |
| --- | --- | --- |
| `customTheme` | `Map?` | 编辑页高级主题。 |
| `editMenuItems` | `List<NvEditMenuItem>`, 全部 | 有序菜单，删除后 UI 重排。 |
| `resolution` | `NvVideoPreviewResolution`, `1080` | 编辑预览分辨率。 |
| `fps` | `num`, `25` | 编辑预览帧率。 |
| `minEffectDuration` | `num`, `500` | 最小特效时长，毫秒。 |
| `minAudioDuration` | `num`, `1000` | 最小录音时长，毫秒。 |
| `defaultImageDuration` | `num`, `3000` | 图片默认时长，毫秒。 |
| `captionColor` | `String`, `#FFFFFF` | 默认字幕颜色。 |
| `captionColorList` | `List<String>`, 20 色 | 字幕颜色，有序。 |
| `supportedCaptionStyles` | `List<NvImageCaptionStyle>`, 全部 | `none`、`bg`、`bgAlpha`、`outline`。 |
| `editModeSource` | `firstAsset` | `fixed` 或首素材决定。 |
| `editMode` | `9v16` | 固定画幅。 |
| `supportedEditModes` | 全部九种 | `9v16`、`16v9`、`3v4`、`4v3`、`1v1`、`18v9`、`9v18`、`8v9`、`9v8`。 |
| `bubbleConfig` | `NvBubbleConfig?` | 气泡图标、标题、背景、模糊样式。 |
| `filterDefaultValue` | `num`, `0.8` | 编辑滤镜强度 `0.0-1.0`。 |
| `maxVolume` | `num`, `4.0` | 稳定范围 `(0,8]`；`0` 会导致 iOS 音量显示异常，必须在调用 SDK 前拒绝。 |
| `disableTimeEffect` | `bool`, `false` | Android 按当前版本能力目录处理；iOS 2.0.2.1 静默忽略，不得承诺可用。 |

编辑菜单全量：`release` 发布、`download` 保存、`edit` 裁剪、`text` 文字、`sticker` 贴纸、`effect` 特效、`filter` 滤镜、`caption` 自动字幕、`audio` 音效、`record` 录音。

`NvBubbleConfig` 全量：`editImageName`、`durationImageName`、`titleTheme`、`backgroundColor`、`backgroundBlurStyle`；模糊样式为 `none`、`light`、`dark`。

## 导出、水印与模型

| 字段 | 类型/默认值 | 功能与边界 |
| --- | --- | --- |
| `compileConfig.resolution` | `1080` | 720、1080、4K；4K 需设备验证。 |
| `compileConfig.fps` | `25` | 导出帧率。 |
| `compileConfig.bitrateGrade` | `High` | Low、Medium、High；`bitrate=-1` 时使用。 |
| `compileConfig.imageType` | `PNG` | PNG/JPEG。 |
| `compileConfig.bitrate` | `-1` | 非 `-1` 时覆盖等级。 |
| `compileConfig.autoSaveVideo` | `true` | 导出后保存系统相册。 |
| `compileConfig.watermarkConfig` | `null` | 视频水印。 |
| `compileConfig.coverWatermarkConfig` | `null` | 封面水印。 |
| `compileConfig.configure` | `Map?` | 底层合成字典；未知键禁止写入。 |

`NvWatermarkConfig` 全量：`watermark`、`width`、`height`、`offsetX`、`offsetY`、`position`；位置为右上、左上、左下、右下。`NvImageConfig` 使用资源名或文件路径。

`modelConfig` 全量：`use240`、`fakeface`、`face`、`face240`、`avatar`、`hand`、`humanseg`、`skysegment`、`eyecontour`、`advancedbeauty`、`facecommon`、`autoCutActivity`、`autoCutFaceAttri`、`autoCutFace`、`autoCutImagecls`、`autoCutPf`、`autoCutPhoto`。路径必须来自当前版本官方包或美摄交付。

## 2.0.2.1 已验证平台边界

- Android 已对 117 个合法场景完成 Dart 序列化/桥接输入校验，28 个非法场景在 SDK 调用前拒绝；未逐项真机观察的字段仅标记 `transport_verified`，不等于真机功能通过。
- Android `customTheme` 的已测速度按钮和标题键未生效；功能裁剪使用有序菜单数组，不使用主题隐藏。
- iOS 已重测拍摄自动静音、最小特效/录音时长、`supportedEditModes`、封面水印和 `disableTimeEffect`；这些项在 2.0.2.1 的标准路径中未生效或被静默忽略。
- iOS 视频水印使用真实图片文件路径后可用；4K 可能回退到 1080p，必须读取实际媒体输出判定。
- 静态检查必须分开 `lib/` 生成业务代码和官方插件告警，不得把第三方告警冒充为生成代码错误。
- 外部模型、客户服务器、正式 License、未知 `configure` 字典和物理旋转保持 `limited`，需要真实外部输入或人工验收。
