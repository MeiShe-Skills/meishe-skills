# 原生 Android 功能配置

本清单只适用于当前逐字段验证的原生 Android `2.0.1.0` `NvShortVideoCore.aar` Java API。`2.0.2.1` 已验证完整接入与核心业务链路，但未逐字段重测，不能自动继承这里的行为结论。用户入口是生成包名下的 `meishe/MeisheFeatureConfig.java`；该文件在 SDK JSON 初始化后应用，是用户功能配置的最终来源。不得套用 iOS、React Native 或 Flutter 枚举。

机器可查询的字段与已验证边界位于 `references/config-capabilities/native-android.json`；修改前先运行 `scripts/query_feature_config.py --track native-android --platform android --version 2.0.1.0 --query <自然语言>`。

若用户提供 `2.0.2.1`，查询器会明确区分“集成兼容性已验证”和“该配置字段未验证”。此时先检查实际 AAR API，再按用户要求做定向验证，不得把 `2.0.1.0` 补丁静默套用到新版本。

## UI 与修改规则

- `captureMenuItems`、`captureBottomMenuItems`、`dualMenuItems`、`editMenuItems` 是有序 List。删除枚举会删除控件及下级入口，SDK 重排其余 UI；禁止 `null` 占位。
- 删除 `NvEditMenuItem.text` 会删除文字及其内部入口，后续菜单上移。
- 底部模式不能为空；默认项必须存在；模板存在时必须最后；菜单不能重复。
- `release`、`download` 影响发布和保存，删除前必须确认发布、导出、草稿仍可达。
- 配置文件首次生成后保留手改。未验证 AAR 必须用 `javap` 或官方源码重新确认公开方法和枚举。

## 修改后生效

- 以生成项目 `meishe_configuration_handoff.md` 为准；其中包含实际 app module、绝对工作目录、`gradlew`/`gradlew.bat :<module>:installDebug` 和短视频 Activity 启动指令。
- Java 配置、JSON、License、applicationId、签名或原生资源都会打包进 APK，修改后必须重新构建并安装，不能只强制停止后重启旧包。
- 只有 Gradle/AAR 依赖声明变化时才需要 Gradle Sync 或依赖解析；普通配置修改不默认执行 clean。

## NvVideoConfig

| 字段 | 类型/生成默认值 | 功能与边界 |
| --- | --- | --- |
| `primaryColor` | `String`, `#FC3E5A` | 主色。 |
| `backgroundColor` | `String`, `#111111` | 页面背景。 |
| `panelBackgroundColor` | `String`, `#1F1F1F` | 面板背景。 |
| `textColor` | `String`, `#FFFFFF` | 主文字。 |
| `secondaryTextColor` | `String`, `#9E9E9E` | 次级文字。 |
| `enableLocalMusic` | `boolean`, `false` | 本地音乐入口。 |
| `albumConfig` | `NvAlbumConfig` | 相册。 |
| `captureConfig` | `NvCaptureConfig` | 拍摄/合拍。 |
| `editConfig` | `NvEditConfig` | 编辑。 |
| `compileConfig` | `NvCompileConfig` | 导出。 |
| `templateConfig` | `NvTemplateConfig` | 模板/一键成片。 |
| `modelConfig` | `NvModelConfig` | 模型路径。 |
| `shadowOffset` | `NvShadowOffsetConfig` | 阴影偏移，必须使用当前 AAR 类型。 |
| `shadowColor` | `String` | 阴影颜色。 |
| `shadowRadius` | 只读 `float` | 当前 AAR 未公开 setter，不能作为可写配置。 |

## 相册与模板

| 对象.字段 | 类型/生成默认值 | 功能与边界 |
| --- | --- | --- |
| `albumConfig.type` | `int`, `0` | `0` 全部、`1` 视频、`2` 图片。 |
| `albumConfig.maxSelectCount` | `int`, `50` | 最大素材数，必须大于 0。 |
| `albumConfig.useAutoCut` | `boolean`, `true` | 素材选择页一键成片。 |
| `templateConfig.maxSelectCount` | `int`, `50` | 模板/一键成片最大片段数。 |
| `templateConfig.useAutoCut` | `boolean`, `true` | 模板页一键成片。 |
| `templateConfig.maxRecommandTemplateCount` | `int`, `20` | 推荐模板上限；字段名沿用官方拼写。 |

## 拍摄与合拍

| 字段 | 类型/生成默认值 | 功能与边界 |
| --- | --- | --- |
| `captureMenuItems` | `List<NvCaptureMenuItem>` | 拍摄右侧菜单，有序。 |
| `captureBottomMenuItems` | `List<NvCaptureBottomMenuItem>` | 底部模式，有序，模板最后。 |
| `defaultBottomMenuSelectItem` | `video` | 默认模式，必须存在。 |
| `captureDeviceIndex` | `int`, `1` | `0` 后置、`1` 前置。 |
| `resolution` | `NvVideoPreviewResolution`, `1080` | 720、1080。 |
| `ignoreVideoRotation` | `boolean`, `true` | 忽略旋转。 |
| `imageDuration` | `long`, `3000` | 图片时长，毫秒。 |
| `autoSavePhotograph` | `boolean`, `false` | 拍照后保存相册。 |
| `timeRanges` | `List<NvTimePair>` | 普通录制档位，`0 <= min < max`。 |
| `smartTimeRange` | `NvTimePair` | 快拍范围。 |
| `beautyConfig` | `NvBeautyConfig` | 美颜分类和子项。 |
| `dualMenuItems` | `List<NvCaptureMenuItem>` | 合拍右侧菜单。 |
| `dualConfig` | `NvDualConfig` | 合拍布局和样式。 |
| `filterDefaultValue` | `double`, `0.8` | 滤镜强度 `0.0-1.0`。 |
| `enableCaptureAlbum` | `boolean`, `false` | 拍摄页相册入口。 |
| `autoDisablesMic` | `boolean`, `false` | 自动禁用原声/麦克风。 |
| `defaultBottomMenuSelectItem` | 枚举 | 默认底部模式。 |
| `recordConfiguration` | `Map<String,Object>` | 底层录制字典，已知键 `bitrate`、`gopsize`、`video encoder name`。 |
| `fps` | `int`, `30` | Android 超过 30 时实际录制可能达不到设定。 |

当前 AAR 的 `NvCaptureMenuItem` 全量：`device` 翻转、`speed` 快慢速、`timer` 倒计时、`beauty` 美颜、`makeup` 美妆、`prop` 人脸道具、`flashlight` 闪光灯、`filter` 滤镜、`original` 原声、`dualtype` 合拍样式、`segment`。该 AAR没有 `matting`；`segment` 的行为未在当前官方功能配置文档中定义，默认不开放，禁止猜测为抠像。底部全量：`image`、`video`、`smart`、`template`。

`NvBeautyConfig` 全量：`categoricalArray`、`beautyEffectArray`、`beautyShapeArray`、`beautyMicroShapeArray`、`beautyAdjustArray`。分类枚举为 `Skin`、`Shape`、`MicroShape`、`Adjust`；子项必须使用当前 AAR 的对应枚举。

`NvDualConfig` 全量：`left`、`top`、`limitWidth`、`defaultType`、`supportedTypes`、`autoDisablesMic`。样式全量：`leftRight`、`topDown`、`leftRect`、`leftCircle`、`topCircle`。当前 AAR 未公开 `muteOriginal`，禁止照搬框架字段。

## 编辑

| 字段 | 类型/生成默认值 | 功能与边界 |
| --- | --- | --- |
| `editMenuItems` | `List<NvEditMenuItem>`, 全部 | 编辑菜单，有序。 |
| `resolution` | `NvVideoPreviewResolution`, `1080` | 编辑预览分辨率。 |
| `fps` | `int`, `30` | 编辑预览帧率。 |
| `minEffectDuration` | `long`, `100` | 最小特效时长，毫秒。 |
| `minAudioDuration` | `long`, `10000` | 最小录音时长，毫秒。 |
| `defaultImageDuration` | `long`, `4000` | 图片默认时长，毫秒。 |
| `captionColor` | `String`, `#FFFFFF` | 默认字幕颜色。 |
| `captionColorList` | `List<String>` | 字幕颜色，有序。 |
| `supportedCaptionStyles` | `List<NvImageCaptionStyle>` | `none`、`bg`、`bgAlpha`、`outline`。 |
| `editModeSource` | `firstAsset` | `fixed` 或首素材决定。 |
| `editMode` | `NvEditMode9v16` | 固定画幅。 |
| `supportedEditModes` | 九种枚举 | 当前 AAR 的单元素列表在进入 SDK 前拒绝；自定义多元素列表不可靠，推荐只用 `editModeSource/editMode` 设置初始画幅。 |
| `bubbleConfig` | `NvBubbleConfig` | 编辑图标、时长图标、标题、背景、模糊。 |
| `filterDefaultValue` | `float`, `0.5` | 编辑滤镜强度。 |
| `maxVolume` | `float`, `8` | 稳定范围 `(0,8]`；`0` 和超过 8 在调用 SDK 前拒绝。 |
| `disableTimeEffect` | `boolean`, `false` | 字段可传输，但当前默认编辑页没有可达的时间特效入口，只能标记边界已验证。 |

编辑菜单全量：`release` 发布、`download` 保存、`edit` 裁剪、`text` 文字、`sticker` 贴纸、`effect` 特效、`filter` 滤镜、`caption` 自动字幕、`audio` 音效、`record` 录音。

`NvBubbleConfig` 全量：`editImageName`、`durationImageName`、`titleTheme`、`backgroundColor`、`backgroundBlurStyle`；模糊样式 `none`、`light`、`dark`。

## 导出、水印与模型

| 字段 | 类型/生成默认值 | 功能与边界 |
| --- | --- | --- |
| `compileConfig.resolution` | `1080` | 720、1080、4K；4K 需设备验证。 |
| `compileConfig.fps` | `int`, `30` | 导出帧率。 |
| `compileConfig.bitrateGrade` | `Low` | Low、Medium、High；`bitrate=-1` 时使用。 |
| `compileConfig.imageType` | `PNG` | PNG/JPEG。 |
| `compileConfig.bitrate` | `int`, `-1` | 非 `-1` 时覆盖等级。 |
| `compileConfig.autoSaveVideo` | `boolean`, `true` | 导出后保存相册。 |
| `compileConfig.watermarkConfig` | `NvWatermarkConfig?` | 视频水印。 |
| `compileConfig.coverWatermarkConfig` | `NvWatermarkConfig?` | 封面水印。 |
| `compileConfig.configure` | `Map<String,Object>` | 底层合成字典，未知键禁止写入。 |

`NvWatermarkConfig` 全量：`nvImageConfig`、`offsetX`、`offsetY`、`width`、`height`、`position`；位置常量为右上、左上、左下、右下。图片必须是当前项目的真实资源或文件路径。

`modelConfig` 全量：`fakeface`、`use240`、`face`、`face240`、`avatar`、`makeup`、`hand`、`humanseg`、`eyecontour`、`faceCommonModel`、`advancedBeautyModel`、`autoCutActivity`、`autoCutFaceAttri`、`autoCutFace`、`autoCutImagecls`、`autoCutPf`、`autoCutPhoto`。路径必须来自当前 AAR 配套官方包或美摄交付。

## 2.0.1.0 已验证边界

- 配置类、枚举和菜单依赖必须在 SDK 调用前校验；`maxVolume=0`、空底部菜单、默认项不在菜单内和单元素 `supportedEditModes` 均应立即失败。
- 单元素 `supportedEditModes` 在当前 AAR 中会触发 SDK 异常；多元素自定义列表也不作为稳定承诺。
- `captionColor`、默认合拍版式、音量范围、录音和最短时长的真实行为以能力目录状态为准；仅序列化成功的项不冒充真机通过。
- 封面保存只在 AAR 精确包含已验证的 `saveCover` / `PathUtils.getCoverDir` / 回调 API 形状时生成；不匹配时不猜测调用。
- 外部模型、客户服务器、正式 License、未知 `configure` 字典和物理旋转保持 `limited`。
