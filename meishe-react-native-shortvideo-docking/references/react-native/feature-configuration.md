# React Native 功能配置

本清单只适用于官方 React Native 包 `2.0.2.1` 的 TypeScript API。用户入口是生成项目中的 `src/meisheFeatureConfig.ts`（JavaScript 工程为 `.js`）；不要修改 `ios/` 或 `android/` 内的原生桥接来配置业务功能。

字段是否在 Android/iOS 真正生效、证据等级和自然语言别名以 `references/config-capabilities/react-native.json` 为准。使用 `scripts/query_feature_config.py --track react-native --platform <android|ios> --version 2.0.2.1 --query <字段或描述>` 查询，不得把桥接下传或序列化通过描述成真机效果通过。

## UI 与修改规则

- `captureMenuItems`、`captureBottomMenuItems`、`dualMenuItems`、`editMenuItems` 都是有序数据源。删除枚举会删除对应控件及其下级入口，剩余控件由 SDK 重排；禁止用 `null`、空字符串、透明控件或隐藏样式占位。
- 删除 `NvEditMenuItem.text` 会同时移除文字入口及其内部功能，后续菜单上移，不应留下空白。
- 拍摄底部数组不能为空；默认项必须存在；`template` 存在时必须放在最后；所有菜单数组禁止重复项。
- `release`、`download` 影响发布和保存能力。删除前必须确认仍有可达的发布、导出和草稿流程。
- 配置文件只在首次接入时生成，之后重新运行 Skill 必须保留用户手动修改。
- RN 配置同时生成 iOS、Android 参数。若桥接实现存在端差异，在本文件注释和本清单标记，不生成两份用户配置。

## 修改后生效

- 以生成项目 `meishe_configuration_handoff.md` 的绝对路径和命令为准。Debug 包修改 TS/JS 后启动已有包管理器的 Metro，并执行完整 Reload；不能只依赖 Fast Refresh，因为页面可能保留旧的 `NvVideoConfig`。
- Release bundle，或 Android/iOS 原生文件、包名、Bundle Identifier、License、签名和资源发生变化时，执行交接文件中当前子平台的重新构建安装命令。
- 只有 `package.json`、锁文件、Podfile 或原生依赖声明变化时才重新安装依赖；配置值变化不要求删除 `node_modules`、Pods 或执行 clean。

## NvVideoConfig

| 字段 | 类型/默认值 | 功能与边界 |
| --- | --- | --- |
| `primaryColor` | `string`, `#FC3E5A` | 主色，格式 `#RRGGBB`。 |
| `backgroundColor` | `string`, `#000000` | 页面背景色。 |
| `panelBackgroundColor` | `string`, `#1C1C1C` | 面板背景色。 |
| `textColor` | `string`, `#FFFFFF` | 主文字颜色。 |
| `secondaryTextColor` | `string`, `#6C6C77` | 次级文字颜色。 |
| `enableLocalMusic` | `boolean`, `true` | 是否显示本地音乐；系统权限仍必须满足。 |
| `shadowOffset` | `{width,height}`, `{0,0.5}` | 文字阴影偏移。 |
| `shadowColor` | `string`, `#00000080` | RGBA 阴影颜色。 |
| `albumConfig` | `NvAlbumConfig` | 相册配置。 |
| `captureConfig` | `NvCaptureConfig` | 拍摄与合拍配置。 |
| `editConfig` | `NvEditConfig` | 编辑配置。 |
| `compileConfig` | `NvCompileConfig` | 导出配置。 |
| `templateConfig` | `NvTemplateConfig` | 模板/一键成片配置。 |
| `modelConfig` | `NvModelConfig` | 模型路径；只能使用与当前 SDK 匹配的真实文件。 |

## 相册与模板

| 对象.字段 | 类型/默认值 | 功能与边界 |
| --- | --- | --- |
| `albumConfig.customTheme` | `Map`, 未设置 | 高级主题覆盖；键和值必须来自当前 RN 包公开主题 API。 |
| `albumConfig.type` | `number`, `0` | 顶部标签：`0` 全部、`1` 视频、`2` 图片。 |
| `albumConfig.maxSelectCount` | `number`, `50` | 最大素材数，必须大于 0。 |
| `albumConfig.useAutoCut` | `boolean`, `true` | 素材选择页一键成片入口，不控制拍摄页模板模式。 |
| `templateConfig.customTheme` | `Map`, 未设置 | 模板页高级主题。 |
| `templateConfig.maxSelectCount` | `number`, `50` | 模板/一键成片最大片段数，必须大于 0。 |
| `templateConfig.useAutoCut` | `boolean`, `true` | 模板页一键成片入口。 |
| `templateConfig.maxRecommandTemplateCount` | `number`, `20` | 推荐模板最大数量，必须大于 0；字段名沿用官方拼写。 |

## 拍摄与合拍

| 字段 | 类型/默认值 | 功能与边界 |
| --- | --- | --- |
| `customTheme` | `Map`, 未设置 | 拍摄页高级主题。 |
| `captureMenuItems` | `NvCaptureMenuItem[]`, 全部 | 拍摄右侧菜单，有序。 |
| `captureBottomMenuItems` | `NvCaptureBottomMenuItem[]`, 全部 | 拍摄底部模式，有序，模板必须最后。 |
| `defaultBottomMenuSelectItem` | `video` | 默认模式，必须包含在底部数组。 |
| `captureDeviceIndex` | `number`, `1` | `0` 后置、`1` 前置。 |
| `resolution` | `NvVideoPreviewResolution`, `1080` | 只公开 720、1080。 |
| `ignoreVideoRotation` | `boolean`, `true` | 是否忽略设备旋转信息。 |
| `imageDuration` | `number`, `3000` | 图片默认时长，毫秒，必须大于 0。 |
| `autoSavePhotograph` | `boolean`, `false` | 拍照后进入编辑前是否保存系统相册。 |
| `timeRanges` | `NvTimePair[]` | 普通录制时长档位，毫秒，要求 `0 <= min < max`。 |
| `smartTimeRange` | `NvTimePair` | 快拍时长，毫秒。 |
| `beautyConfig` | `NvBeautyConfig?` | 美颜分类和子项。 |
| `dualMenuItems` | `NvCaptureMenuItem[]` | 合拍右侧菜单，独立且有序。 |
| `dualConfig` | `NvDualConfig?` | 合拍布局、样式和声音。 |
| `filterDefaultValue` | `number`, `0.8` | 滤镜强度，范围 `0.0-1.0`。 |
| `enableCaptureAlbum` | `boolean?` | 拍摄页相册快捷入口；生成默认 `false`。 |
| `autoDisablesMic` | `boolean`, `false` | 是否自动禁用原声/麦克风。 |
| `fps` | `number`, `30` | 拍摄帧率；修改需验证两端设备与桥接。 |
| `recordConfiguration` | `Map<string,any>?` | 底层录制字典；已知键包括 `bitrate`、`gopsize`、`video encoder name`，未知键禁止写入。 |

`NvCaptureMenuItem` 全量：`device` 翻转、`speed` 快慢速、`timer` 倒计时、`beauty` 美颜、`makeup` 美妆、`prop` 人脸道具、`matting` 抠像、`flashlight` 闪光灯、`filter` 滤镜、`original` 原声、`dualtype` 合拍样式。`dualtype` 通常只放入合拍菜单。

`NvCaptureBottomMenuItem` 全量：`image` 拍照、`video` 录制、`smart` 快拍、`template` 模板。

`NvDualConfig`：`left=17/375`、`top=18/666.67`、`limitWidth=153.5/375`、`defaultType=leftRight`、`supportedTypes`、`autoDisablesMic=false`、`muteOriginal=true`。样式全量为 `leftRight`、`topDown`、`leftRect`、`leftCircle`、`topCircle`；默认样式必须在支持列表中。

`NvBeautyConfig` 字段全量：`categoricalArray`、`beautyEffectArray`、`beautyShapeArray`、`beautyMicroShapeArray`、`beautyAdjustArray`。分类为 `Skin`、`Shape`、`MicroShape`、`Adjust`；子项必须使用当前包的 `NvBeautyEffect`、`NvBeautyShape`、`NvBeautyMicroShape`、`NvBeautyAdjust`。官方根导出未导出 `NvBeautyMicroShape`，不要为了配置它依赖未承诺的深层路径；需要时先确认包导出契约。

## 编辑

| 字段 | 类型/默认值 | 功能与边界 |
| --- | --- | --- |
| `customTheme` | `Map`, 未设置 | 编辑页高级主题。 |
| `editMenuItems` | `NvEditMenuItem[]`, 全部 | 编辑菜单，有序，删除项后 UI 重排。 |
| `resolution` | `NvVideoPreviewResolution`, `1080` | 编辑预览分辨率。 |
| `fps` | `number`, `25` | 编辑预览帧率。 |
| `minEffectDuration` | `number`, `500` | 最小特效时长，毫秒。 |
| `minAudioDuration` | `number`, `500` | 最小录音时长，毫秒；以当前 TS 源码值为准。 |
| `defaultImageDuration` | `number`, `4000` | 图片默认时长，毫秒。 |
| `captionColor` | `string`, `#FFFFFF` | 默认字幕颜色。 |
| `captionColorList` | `string[]`, 20 色 | 字幕颜色列表，有序。 |
| `supportedCaptionStyles` | `NvImageCaptionStyle[]`, 全部 | `none`、`bg`、`bgAlpha`、`outline`。 |
| `editModeSource` | `firstAsset` | `fixed` 固定画幅，`firstAsset` 由首素材决定。 |
| `editMode` | `9v16` | 固定画幅；使用 `fixed` 时必须在支持列表。 |
| `supportedEditModes` | `NvEditMode[]`, 全部 | `9v16`、`16v9`、`3v4`、`4v3`、`1v1`、`18v9`、`9v18`、`8v9`、`9v8`。 |
| `bubbleConfig` | `NvBubbleConfig?` | 气泡图标、标题主题、背景色、模糊样式。 |
| `filterDefaultValue` | `number`, `0.8` | 编辑滤镜强度 `0.0-1.0`。 |
| `maxVolume` | `number`, `4` | 最大音量，已验证稳定范围 `(0,8]`；`0` 会导致 iOS 异常显示，不用它表达静音。 |
| `disableTimeEffect` | `boolean`, `false` | `true` 禁用反复、慢动作时间特效。 |

`NvEditMenuItem` 全量：`release` 发布、`download` 保存、`edit` 裁剪、`text` 文字、`sticker` 贴纸、`effect` 特效、`filter` 滤镜、`caption` 自动字幕、`audio` 音效、`record` 录音。

`NvBubbleConfig` 全量：`editImageName`、`durationImageName`、`titleTheme`、`backgroundColor`、`backgroundBlurStyle`；模糊样式为 `none`、`light`、`dark`。

## 导出、水印与模型

| 字段 | 类型/默认值 | 功能与边界 |
| --- | --- | --- |
| `compileConfig.resolution` | `1080` | 720、1080、4K；4K 必须做内存和设备验证。 |
| `compileConfig.fps` | `25` | 导出帧率。 |
| `compileConfig.bitrateGrade` | `High` | Low、Medium、High；`bitrate=-1` 时使用。 |
| `compileConfig.imageType` | `PNG` | 封面导出格式 PNG/JPEG。 |
| `compileConfig.bitrate` | `-1` | 精确码率，非 `-1` 时优先于等级。 |
| `compileConfig.autoSaveVideo` | `true` | 导出后是否保存系统相册。 |
| `compileConfig.watermarkConfig` | 空水印对象 | 视频水印；必须提供真实图片和合法尺寸。 |
| `compileConfig.coverWatermarkConfig` | 空水印对象 | 封面水印。 |
| `compileConfig.configure` | 未设置 | 底层合成字典；未知键禁止写入。 |

`NvWatermarkConfig` 全量：`watermark`、`width`、`height`、`offsetX`、`offsetY`、`position`；位置为 `TopRight`、`TopLeft`、`BottomLeft`、`BottomRight`。`NvImageConfig` 使用 `imagePath` 或 `imageName`。

`modelConfig` 全量：`use240`、`fakeface`、`face`、`face240`、`avatar`、`hand`、`humanseg`、`skysegment`、`eyecontour`、`advancedbeauty`、`facecommon`、`autoCutActivity`、`autoCutFaceAttri`、`autoCutFace`、`autoCutImagecls`、`autoCutPf`、`autoCutPhoto`。所有路径都必须来自当前版本官方包或美摄交付，不得伪造、跨版本复制或当作网络地址。

## 2.0.2.1 已验证平台边界

- Android：117 个合法配置场景均通过真实 RN bridge 载荷，28 个非法场景在调用 SDK 前被拒绝；代表性菜单删除和完整编辑、发布、草稿流程通过。`transport_verified` 只表示下传完整，不能替代每个字段的独立真机行为。
- Android：`customTheme` 的拍摄快慢速和相册标题隐藏键已进入 JSON，但当前 AAR 不应用；功能裁剪必须修改有序菜单数组。
- iOS：`autoDisablesMic`、`minEffectDuration`、`minAudioDuration`、`supportedEditModes`、`coverWatermarkConfig` 已重测仍未体现声明行为；`disableTimeEffect` 被 2.0.2.1 iOS bridge 静默忽略。
- iOS：`recordConfiguration` 必须使用可序列化普通对象，ES6 `Map` 会被静默忽略；视频水印需要把 Asset Catalog 图片解析为稳定文件路径。
- 两端：模型、客户服务器、正式 License 和未知 `compileConfig.configure` 键没有真实输入时保持 `limited`。
