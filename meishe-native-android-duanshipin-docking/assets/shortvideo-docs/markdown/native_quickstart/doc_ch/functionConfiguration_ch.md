---
html:
    toc: true
print_background: true
---

<!-- MEISHE_AGENT_DOC_ENHANCED: v1 -->

# 短视频功能配置项

<!-- BEGIN MEISHE_AGENT_QUICK_INDEX -->
> **Agent 快速索引**
> - **Doc ID**: `native-quickstart-doc-ch-functionconfiguration-ch`
> - **语言轨道**: `shared`
> - **平台**: `android, ios`
> - **标签**: `function-config, capture, edit, compile, publish, ui-config, native, flutter, react-native`
> - **图片数**: `0`
> - **用法**: 先按标签定位章节，再读取相邻步骤、配置表和图片解析；不要跳过本页内的注意事项。
<!-- END MEISHE_AGENT_QUICK_INDEX -->




## 工程配置项

<!-- BEGIN MEISHE_AGENT_SECTION_HINT -->
> **Agent 索引提示：** 本节标签 `integration`。接入执行时优先核对本节步骤、配置项、路径和权限要求。
<!-- END MEISHE_AGENT_SECTION_HINT -->


```
primaryColor：主色调
backgroundColor：背景色
panelBackgroundColor：面板色
textColor：文字颜色
secondaryTextColor：二级文字颜色
enableLocalMusic：显示itunes 音乐列表
albumConfig：相册配置
captureConfig：拍摄配置
editConfig：编辑配置
compileConfig：合成配置
watermarkConfig：水印配置
templateConfig：模版配置
modelConfig：模型配置
```
用户通过属性可以进行相关配置，例如：
### ios 
```swift
videoConfig = NvVideoConfig()
guard let videoConfig = videoConfig else { return }
videoConfig.captureConfig.recordConfiguration = ["video encoder name": "hevc","gopsize":10]
videoConfig.primaryColor = UIColor.color(withHex: "#0000FF")
videoConfig.backgroundColor = UIColor.color(withHex: "#00FA9A")
videoConfig.panelBackgroundColor = UIColor.color(withHex: "#000080")
videoConfig.textColor = UIColor.color(withHex: "#FFA500")
videoConfig.secondaryTextColor = UIColor.color(withHex: "#8A2BE2")
videoConfig.enableLocalMusic = false
```
参考文件[**NvVideoConfig**](./interface_nv_video_config.html)

### Android
```java
NvVideoConfig videoConfig = new NvVideoConfig();
           
videoConfig.setCaptureConfig(captureConfig);
videoConfig.setPrimaryColor("#0000FF");
videoConfig.setBackgroundColor("#00FA9A");
videoConfig.setPanelBackgroundColor("#00FA9A");
videoConfig.setTextColor("#FFA500");
videoConfig.setSecondaryTextColor("#8A2BE2");
videoConfig.setEnableLocalMusic(false);
```


参考文件[**NvVideoConfig**](./classcom_1_1meishe_1_1config_1_1_nv_video_config.html)

### flutter
```dart
videoConfig.primaryColor = "#0000FF";
videoConfig.backgroundColor = "#00FA9A";
videoConfig.panelBackgroundColor = "#000080";
videoConfig.textColor = "#FFA500";
videoConfig.secondaryTextColor = "#8A2BE2";
videoConfig.enableLocalMusic = false;
```
参考文件nv_video_config.dart

### react-native
```js
this.videoConfig.primaryColor = "#0000FF";
this.videoConfig.backgroundColor = "#00FA9A";
this.videoConfig.panelBackgroundColor = "#000080";
this.videoConfig.textColor = "#FFA500";
this.videoConfig.secondaryTextColor = "#8A2BE2";
this.videoConfig.enableLocalMusic = false;
```
参考文件NvVideoConfig.js


## 相册配置项
```
type：相册顶部标签
maxSelectCount：可选最大素材数
useAutoCut：是否有一键成片功能
```
```
注：模版、模版页面的一键成片的入口以及合拍，不受此配置影响
```
用户通过属性可以进行相关配置，例如：
### ios 
```swift
// 相册配置 albumConfig
videoConfig.albumConfig.type = 1
videoConfig.albumConfig.maxSelectCount = 5
videoConfig.albumConfig.useAutoCut = false
```
参考文件[NvAlbumConfig](./interface_nv_album_config.html)

### Android

```java
NvAlbumConfig albumConfig = new NvAlbumConfig();
albumConfig.setType(1);
albumConfig.setMaxSelectCount(5);
albumConfig.setUseAutoCut(false);
```

参考文件[NvAlbumConfig](./classcom_1_1meishe_1_1config_1_1_nv_album_config.html)

### flutter
```dart
videoConfig.albumConfig.type = 1;
videoConfig.albumConfig.maxSelectCount = 5;
videoConfig.albumConfig.useAutoCut = false;
```
参考文件nv_album_config.dart

### react-native
```js
this.videoConfig.albumConfig.type = 1;
this.videoConfig.albumConfig.maxSelectCount = 5;
this.videoConfig.albumConfig.useAutoCut = false;
```
参考文件NvAlbumConfig.js

## 拍摄配置项

<!-- BEGIN MEISHE_AGENT_SECTION_HINT -->
> **Agent 索引提示：** 本节标签 `function-config`。接入执行时优先核对本节步骤、配置项、路径和权限要求。
<!-- END MEISHE_AGENT_SECTION_HINT -->


```
captureMenuItems：拍摄右侧菜单 （数组有序）
captureBottomMenuItems：拍摄底部菜单 （数组有序，模版放最后）
captureDeviceIndex：前置摄像头/后置摄像头
resolution：拍摄分辨率
ignoreVideoRotation：忽略设备旋转
imageDuration：拍照时长设置（毫秒）
autoSavePhotograph：拍摄的照片，进入编辑之前，是否保存到相册
timeRanges：录制时长设置
smartTimeRange：快拍设置
beautyConfig：美颜配置项
dualMenuItems：合拍右侧菜单（有序）
dualConfig：合拍设置
filterDefaultValue：滤镜默认值
enableCaptureAlbum：拍摄页显示相册按钮
autoDisablesMic：自动禁掉原声
```
用户通过属性可以进行相关配置，例如：

### ios 
```swift 
private func test() {
    videoConfig = NvVideoConfig()
    guard let videoConfig = videoConfig else { return }
    // 录制配置 recordConfiguration
    videoConfig.captureConfig.recordConfiguration = ["video encoder name": "hevc","gopsize":10]
    // 拍摄配置 captureConfig
    videoConfig.captureConfig.captureMenuItems = [
        NvCaptureMenuItem.device,
        NvCaptureMenuItem.speed,
        NvCaptureMenuItem.beauty,
        NvCaptureMenuItem.original,
        NvCaptureMenuItem.filter,
        NvCaptureMenuItem.matting
    ]
    // 底部菜单配置默认选中 defaultBottomMenuSelectItem
    videoConfig.captureConfig.defaultBottomMenuSelectItem = NvCaptureBottomMenuItem.video
    videoConfig.captureConfig.captureBottomMenuItems = [
        NvCaptureBottomMenuItem.image,
        NvCaptureBottomMenuItem.video,
        NvCaptureBottomMenuItem.smart,
        NvCaptureBottomMenuItem.template
    ]
    videoConfig.captureConfig.fps = 30
    videoConfig.captureConfig.captureDeviceIndex = 0
    videoConfig.captureConfig.resolution = ._720
    videoConfig.captureConfig.ignoreVideoRotation = false
    videoConfig.captureConfig.imageDuration = 6 * 1000
    videoConfig.captureConfig.autoSavePhotograph = true

    let pair1 = NvTimePair()
    pair1.minDuration = 1 * 1000
    pair1.maxDuration = 10 * 1000

    let pair2 = NvTimePair()
    pair2.minDuration = 0
    pair2.maxDuration = 50 * 1000
    videoConfig.captureConfig.timeRanges = [pair2]

    let pair3 = NvTimePair()
    pair3.minDuration = 0
    pair3.maxDuration = 30 * 1000
    videoConfig.captureConfig.smartTimeRange = pair3

    videoConfig.captureConfig.beautyConfig = NvBeautyConfig()
    videoConfig.captureConfig.beautyConfig.categoricalArray = [
        NvBeautyCategorical.skin,
        NvBeautyCategorical.microShape
    ]
    videoConfig.captureConfig.beautyConfig.beautyEffectArray = [
        NvBeautyEffect.standard,
        NvBeautyEffect.whiteA,
        NvBeautyEffect.rosy
    ]

    videoConfig.captureConfig.dualMenuItems = [
        NvCaptureMenuItem.device,
        NvCaptureMenuItem.dualType,
        NvCaptureMenuItem.original
    ]
    videoConfig.captureConfig.dualConfig = NvDualConfig()
    videoConfig.captureConfig.dualConfig.left = 50.0 / 375.0
    videoConfig.captureConfig.dualConfig.top = 50.0 / 666.67
    videoConfig.captureConfig.dualConfig.limitWidth = 200 / 375.0
    videoConfig.captureConfig.dualConfig.defaultType = .topDown
    let types = UInt(NvDualType.topDown.rawValue) | UInt(NvDualType.leftRight.rawValue)
    videoConfig.captureConfig.dualConfig.supportedTypes = types
    videoConfig.captureConfig.dualConfig.autoDisablesMic = true

    videoConfig.captureConfig.filterDefaultValue = 1.0
    videoConfig.captureConfig.enableCaptureAlbum = true
    videoConfig.captureConfig.autoDisablesMic = true
}
```
目前iOS端fps超过30和小于5都是无效值；Android端fps超过30后，录制的视频可能达不到预设期望值。
参考文件[**NvCaptureConfig**](./interface_nv_capture_config.html)

### Android
目前iOS端fps超过30和小于5都是无效值；Android端fps超过30后，录制的视频可能达不到预设期望值。
```java
NvCaptureConfig captureConfig = new NvCaptureConfig();
List<NvCaptureConfig.NvCaptureMenuItem> captureMenuItems = new ArrayList<>(4);
captureMenuItems.add(NvCaptureConfig.NvCaptureMenuItem.device);
captureMenuItems.add(NvCaptureConfig.NvCaptureMenuItem.speed);
captureMenuItems.add(NvCaptureConfig.NvCaptureMenuItem.beauty);
captureMenuItems.add(NvCaptureConfig.NvCaptureMenuItem.original);
captureMenuItems.add(NvCaptureConfig.NvCaptureMenuItem.filter);
captureConfig.setCaptureMenuItems(captureMenuItems);


List<NvCaptureConfig.NvCaptureBottomMenuItem> captureBottomMenuItems = new ArrayList<>(2);
captureBottomMenuItems.add(NvCaptureConfig.NvCaptureBottomMenuItem.image);
captureBottomMenuItems.add(NvCaptureConfig.NvCaptureBottomMenuItem.video);
captureConfig.setCaptureBottomMenuItems(captureBottomMenuItems);

captureConfig.setCaptureDeviceIndex(0);
captureConfig.setResolution(NvCompileConfig.NvVideoPreviewResolution.NvVideoPreviewResolution_720);
captureConfig.setIgnoreVideoRotation(false);
captureConfig.setImageDuration(6 * 1000);
captureConfig.setAutoSavePhotograph(false);
NvTimePair pair1 = new NvTimePair();
pair1.setMinDuration(1* 1000);
pair1.setMaxDuration(10* 1000);

NvTimePair pair2 = new NvTimePair();
pair2.setMinDuration(0);
pair2.setMaxDuration(50* 1000);

List<NvTimePair> timeRanges = new ArrayList<>(2);
timeRanges.add(pair1);
timeRanges.add(pair2);
captureConfig.setTimeRanges(timeRanges);


NvTimePair pair3 = new NvTimePair();
pair3.setMinDuration(0);
pair3.setMaxDuration(20* 1000);

captureConfig.setSmartTimeRange(pair3);
NvBeautyConfig beautyConfig = new NvBeautyConfig();
List<NvBeautyConfig.NvBeautyCategorical> categoricalArray = new ArrayList<>();
categoricalArray.add(NvBeautyConfig.NvBeautyCategorical.Skin);
categoricalArray.add(NvBeautyConfig.NvBeautyCategorical.Shape);
beautyConfig.setCategoricalArray(categoricalArray);

List<NvBeautyConfig.NvBeautyEffect> beautyEffectArray = new ArrayList<>();
beautyEffectArray.add(NvBeautyConfig.NvBeautyEffect.Standard);
beautyEffectArray.add(NvBeautyConfig.NvBeautyEffect.WhiteA);
beautyEffectArray.add(NvBeautyConfig.NvBeautyEffect.Rosy);
beautyConfig.setBeautyEffectArray(beautyEffectArray);

List<NvCaptureConfig.NvCaptureMenuItem> dualMenuItems = new ArrayList<>();
dualMenuItems.add(NvCaptureConfig.NvCaptureMenuItem.device);
dualMenuItems.add(NvCaptureConfig.NvCaptureMenuItem.dualtype);
dualMenuItems.add(NvCaptureConfig.NvCaptureMenuItem.original);

NvDualConfig dualConfig = new NvDualConfig();
dualConfig.setLeft(50.0 / 375.0);
dualConfig.setTop( 50.0 / 666.67);
dualConfig.setLimitWidth(200 / 375.0);
dualConfig.setDefaultType(NvDualConfig.NvDualType.topDown);
List<NvDualConfig.NvDualType> supportedTypes = new ArrayList<>();
supportedTypes.add(NvDualConfig.NvDualType.topDown);
supportedTypes.add(NvDualConfig.NvDualType.leftRight);
dualConfig.setSupportedTypes(supportedTypes);
dualConfig.setAutoDisablesMic(true);

captureConfig.setFilterDefaultValue(1);
captureConfig.setEnableCaptureAlbum(true);
captureConfig.setAutoDisablesMic(true);
```

参考文件[**NvCaptureConfig**](./classcom_1_1meishe_1_1config_1_1_nv_capture_config.html)

### flutter
```dart
videoConfig.captureConfig.captureMenuItems = [
      NvCaptureMenuItem.device,
      NvCaptureMenuItem.speed,
      NvCaptureMenuItem.beauty,
      NvCaptureMenuItem.original,
      NvCaptureMenuItem.filter
    ];
videoConfig.captureConfig.captureBottomMenuItems = [
      NvCaptureBottomMenuItem.image,
      NvCaptureBottomMenuItem.video
    ];
videoConfig.captureConfig.captureDeviceIndex = 0;
videoConfig.captureConfig.resolution =
        NvVideoPreviewResolution.NvVideoPreviewResolution_720;
videoConfig.captureConfig.ignoreVideoRotation = false;
videoConfig.captureConfig.imageDuration = 6 * 1000;
videoConfig.captureConfig.autoSavePhotograph = true;
var pair1 = NvTimePair(1 * 1000, 10 * 1000);
var pair2 = NvTimePair(0, 50 * 1000);
videoConfig.captureConfig.timeRanges = [pair1, pair2];
var pair3 = NvTimePair(0, 30 * 1000);
videoConfig.captureConfig.smartTimeRange = pair3;

videoConfig.captureConfig.beautyConfig = NvBeautyConfig();
videoConfig.captureConfig.beautyConfig?.categoricalArray = [
      NvBeautyCategorical.Skin,
      NvBeautyCategorical.MicroShape
    ];
videoConfig.captureConfig.beautyConfig?.beautyEffectArray = [
      NvBeautyEffect.Standard,
      NvBeautyEffect.WhiteA,
      NvBeautyEffect.Rosy
    ];

videoConfig.captureConfig.dualMenuItems = [
      NvCaptureMenuItem.device,
      NvCaptureMenuItem.dualtype,
      NvCaptureMenuItem.original
    ];
videoConfig.captureConfig.dualConfig = NvDualConfig();
videoConfig.captureConfig.dualConfig?.left = 50.0 / 375.0;
videoConfig.captureConfig.dualConfig?.top = 50.0 / 666.67;
videoConfig.captureConfig.dualConfig?.limitWidth = 200 / 375.0;
videoConfig.captureConfig.dualConfig?.defaultType = NvDualType.topDown;
    videoConfig.captureConfig.dualConfig?.supportedTypes = [
      NvDualType.topDown,
      NvDualType.leftRight
    ];
videoConfig.captureConfig.dualConfig?.autoDisablesMic = true;

videoConfig.captureConfig.filterDefaultValue = 1.0;
videoConfig.captureConfig.enableCaptureAlbum = true;
videoConfig.captureConfig.autoDisablesMic = true;
```
参考文件nv_capture_config.dart

### react-native
```js
this.videoConfig.captureConfig.captureMenuItems = [
      NvCaptureMenuItem.device,
      NvCaptureMenuItem.speed,
      NvCaptureMenuItem.beauty,
      NvCaptureMenuItem.original,
      NvCaptureMenuItem.filter
    ];
this.videoConfig.captureConfig.captureBottomMenuItems = [
      NvCaptureBottomMenuItem.image,
      NvCaptureBottomMenuItem.video
    ];
this.videoConfig.captureConfig.captureDeviceIndex = 0;
this.videoConfig.captureConfig.resolution = NvVideoPreviewResolution.NvVideoPreviewResolution_720;
this.videoConfig.captureConfig.ignoreVideoRotation = false;
this.videoConfig.captureConfig.imageDuration = 6 * 1000;
this.videoConfig.captureConfig.autoSavePhotograph = true;
var pair1 = new NvTimePair(1 * 1000, 10 * 1000);
var pair2 = new NvTimePair(0, 50 * 1000);
this.videoConfig.captureConfig.timeRanges = [pair1, pair2];
var pair3 = new NvTimePair(0, 30 * 1000);
this.videoConfig.captureConfig.smartTimeRange = pair3;

this.videoConfig.captureConfig.beautyConfig = new NvBeautyConfig();
this.videoConfig.captureConfig.beautyConfig.categoricalArray = [
      NvBeautyCategorical.Skin,
      NvBeautyCategorical.MicroShape
    ];
this.videoConfig.captureConfig.beautyConfig.beautyEffectArray = [
      NvBeautyEffect.Standard,
      NvBeautyEffect.WhiteA,
      NvBeautyEffect.Rosy
    ];

this.videoConfig.captureConfig.dualMenuItems = [
      NvCaptureMenuItem.device,
      NvCaptureMenuItem.dualtype,
      NvCaptureMenuItem.original
    ];
this.videoConfig.captureConfig.dualConfig = new NvDualConfig();
this.videoConfig.captureConfig.dualConfig.left = 50.0 / 375.0;
this.videoConfig.captureConfig.dualConfig.top = 50.0 / 666.67;
this.videoConfig.captureConfig.dualConfig.limitWidth = 200 / 375.0;
this.videoConfig.captureConfig.dualConfig.defaultType = NvDualType.topDown;
this.videoConfig.captureConfig.dualConfig.supportedTypes = [
      NvDualType.topDown,
      NvDualType.leftRight
    ];
this.videoConfig.captureConfig.dualConfig.autoDisablesMic = true;

this.videoConfig.captureConfig.filterDefaultValue = 1.0;
this.videoConfig.captureConfig.enableCaptureAlbum = true;
this.videoConfig.captureConfig.autoDisablesMic = true;
```
参考文件NvCaptureConfig.js

## 编辑配置项

<!-- BEGIN MEISHE_AGENT_SECTION_HINT -->
> **Agent 索引提示：** 本节标签 `function-config`。接入执行时优先核对本节步骤、配置项、路径和权限要求。
<!-- END MEISHE_AGENT_SECTION_HINT -->


```
editMenuItems：右侧菜单 （有序）
resolution：编辑预览分辨率
fps：预览fps
minEffectDuration：最小特效时长（毫秒）
minAudioDuration：最小录音时长（毫秒）
captionColor：默认字幕颜色
captionColorList：字幕颜色列表（有序）
supportedCaptionStyles：支持的字幕样式（无序）
editModeSource：画幅比例模式
editMode：固定画幅比例
supportedEditModes：支持的画幅比例
bubbleConfig：气泡配置
filterDefaultValue：滤镜默认值
maxVolume：最大音量， [0-8]
disableTimeEffect：禁用时间特效 (反复、慢动作)
```
用户通过属性可以进行相关配置，例如：

### ios 
```swift
videoConfig.editConfig.editMenuItems = [
    NvEditMenuItem.text,
    NvEditMenuItem.filter,
    NvEditMenuItem.effect
]
videoConfig.editConfig.resolution = ._1080
videoConfig.editConfig.fps = 25
videoConfig.editConfig.minEffectDuration = 1000
videoConfig.editConfig.minAudioDuration = 3000
videoConfig.editConfig.captionColor = "#FFA500"
videoConfig.editConfig.captionColorList = [
    "#FFFFFF",
    "#000000",
    "#0099F6",
    "#50C23B"
]
videoConfig.editConfig.supportedCaptionStyles = 9
videoConfig.editConfig.editModeSource = .firstAsset
videoConfig.editConfig.editMode = .mode9v16
let models: Int32 = Int32(NvEditMode.mode16v9.rawValue) |
Int32(NvEditMode.mode9v16.rawValue) |
Int32(NvEditMode.mode3v4.rawValue) |
Int32(NvEditMode.mode4v3.rawValue) |
Int32(NvEditMode.mode1v1.rawValue) |
Int32(NvEditMode.mode18v9.rawValue) |
Int32(NvEditMode.mode9v18.rawValue) |
Int32(NvEditMode.mode8v9.rawValue) |
Int32(NvEditMode.mode9v8.rawValue)
    
videoConfig.editConfig.supportedEditModes = NvEditMode(rawValue: Int(models))
videoConfig.editConfig.bubbleConfig = NvBubbleConfig()
videoConfig.editConfig.bubbleConfig.titleTheme = NvLabelTheme()
videoConfig.editConfig.bubbleConfig.titleTheme.textColor = UIColor.color(withHex: "#0000FF")
videoConfig.editConfig.bubbleConfig.backgroundBlurStyle = NvBubbleBgBlurStyle.light

videoConfig.editConfig.filterDefaultValue = 1.0
videoConfig.editConfig.maxVolume = 1
```
参考文件[**NvEditConfig**](./interface_nv_edit_config.html)

### Android
```java
NvEditConfig editConfig = new NvEditConfig();
List<NvEditConfig.NvEditMenuItem> editMenuItems = new ArrayList<>();
editMenuItems.add(NvEditConfig.NvEditMenuItem.release);
editMenuItems.add(NvEditConfig.NvEditMenuItem.download);
editMenuItems.add(NvEditConfig.NvEditMenuItem.text);
editConfig.setEditMenuItems(editMenuItems);

editConfig.setResolution(NvCompileConfig.NvVideoPreviewResolution.NvVideoPreviewResolution_1080);
editConfig.setFps(25);
editConfig.setMinEffectDuration(1000);
editConfig.setMinAudioDuration(3000);
editConfig.setCaptionColor("#FFA500");

List<String> captionColorList = new ArrayList<>();
captionColorList.add("#FFFFFF");
captionColorList.add("#000000");
captionColorList.add("#0099F6");
captionColorList.add("#50C23B");
editConfig.setCaptionColorList(captionColorList);
editConfig.setSupportedCaptionStyles(9);
editConfig.setEditModeSource(NvEditConfig.NvEditModeSource.firstAsset);
editConfig.setEditMode(NvEditConfig.NvEditMode.NvEditMode9v16);
List<NvEditConfig.NvEditMode> supportedEditModes = new ArrayList<>();
supportedEditModes.add(NvEditConfig.NvEditMode.NvEditMode9v16);
supportedEditModes.add(NvEditConfig.NvEditMode.NvEditMode16v9);
supportedEditModes.add(NvEditConfig.NvEditMode.NvEditMode3v4);
supportedEditModes.add(NvEditConfig.NvEditMode.NvEditMode4v3);
supportedEditModes.add(NvEditConfig.NvEditMode.NvEditMode1v1);
supportedEditModes.add(NvEditConfig.NvEditMode.NvEditMode18v9);
supportedEditModes.add(NvEditConfig.NvEditMode.NvEditMode9v18);
supportedEditModes.add(NvEditConfig.NvEditMode.NvEditMode8v9);
supportedEditModes.add(NvEditConfig.NvEditMode.NvEditMode9v8);
editConfig.setSupportedEditModes(supportedEditModes);

NvBubbleConfig bubbleConfig = new NvBubbleConfig();
NvLabelTheme titleTheme = new NvLabelTheme();
titleTheme.setTextColor("#0000FF");
bubbleConfig.setTitleTheme(titleTheme);
        
editConfig.setFilterDefaultValue(1);
editConfig.setMaxVolume(1);
```

参考文件[**NvEditConfig**](./classcom_1_1meishe_1_1config_1_1_nv_edit_config.html)

### flutter
```dart
videoConfig.editConfig.editMenuItems = [
      NvEditMenuItem.release,
      NvEditMenuItem.download,
      NvEditMenuItem.text
    ];
videoConfig.editConfig.resolution =
        NvVideoPreviewResolution.NvVideoPreviewResolution_1080;
videoConfig.editConfig.fps = 25;
videoConfig.editConfig.minEffectDuration = 1000;
videoConfig.editConfig.minAudioDuration = 3000;
videoConfig.editConfig.captionColor = "#FFA500";
videoConfig.editConfig.captionColorList = [
      "#FFFFFF",
      "#000000",
      "#0099F6",
      "#50C23B",
    ];
videoConfig.editConfig.supportedCaptionStyles = [
      NvImageCaptionStyle.none,
      NvImageCaptionStyle.outline
    ];
videoConfig.editConfig.editModeSource = NvEditModeSource.firstAsset;
videoConfig.editConfig.editMode = NvEditMode.NvEditMode9v16;
videoConfig.editConfig.supportedEditModes = [
      NvEditMode.NvEditMode9v16,
      NvEditMode.NvEditMode16v9,
      NvEditMode.NvEditMode3v4,
      NvEditMode.NvEditMode4v3,
      NvEditMode.NvEditMode1v1,
      NvEditMode.NvEditMode18v9,
      NvEditMode.NvEditMode9v18,
      NvEditMode.NvEditMode8v9,
      NvEditMode.NvEditMode9v8
    ];
videoConfig.editConfig.bubbleConfig = NvBubbleConfig();
videoConfig.editConfig.bubbleConfig?.titleTheme = NvLabelTheme();
videoConfig.editConfig.bubbleConfig?.titleTheme?.textColor = "#0000FF";
videoConfig.editConfig.bubbleConfig?.backgroundBlurStyle =
        NvBubbleBgBlurStyle.light;

videoConfig.editConfig.filterDefaultValue = 1.0;
videoConfig.editConfig.maxVolume = 1;
```
参考文件nv_edit_config.dart

### react-native
```js
this.videoConfig.editConfig.editMenuItems = [
      NvEditMenuItem.release,
      NvEditMenuItem.download,
      NvEditMenuItem.text
    ];
this.videoConfig.editConfig.resolution = NvVideoPreviewResolution.NvVideoPreviewResolution_1080;
this.videoConfig.editConfig.fps = 25;
this.videoConfig.editConfig.minEffectDuration = 1000;
this.videoConfig.editConfig.minAudioDuration = 3000;
this.videoConfig.editConfig.captionColor = "#FFA500";
this.videoConfig.editConfig.captionColorList = [
      "#FFFFFF",
      "#000000",
      "#0099F6",
      "#50C23B",
    ];
this.videoConfig.editConfig.supportedCaptionStyles = [
      NvImageCaptionStyle.none,
      NvImageCaptionStyle.outline
    ];
this.videoConfig.editConfig.editModeSource = NvEditModeSource.firstAsset;
this.videoConfig.editConfig.editMode = NvEditMode.NvEditMode9v16;
this.videoConfig.editConfig.supportedEditModes = [
      NvEditMode.NvEditMode9v16,
      NvEditMode.NvEditMode16v9,
      NvEditMode.NvEditMode3v4,
      NvEditMode.NvEditMode4v3,
      NvEditMode.NvEditMode1v1,
      NvEditMode.NvEditMode18v9,
      NvEditMode.NvEditMode9v18,
      NvEditMode.NvEditMode8v9,
      NvEditMode.NvEditMode9v8
    ];
this.videoConfig.editConfig.bubbleConfig = new NvBubbleConfig();
this.videoConfig.editConfig.bubbleConfig.titleTheme = new NvLabelTheme();
this.videoConfig.editConfig.bubbleConfig.titleTheme.textColor = "#0000FF";
this.videoConfig.editConfig.bubbleConfig.backgroundBlurStyle = NvBubbleBgBlurStyle.light;

this.videoConfig.editConfig.filterDefaultValue = 1.0;
this.videoConfig.editConfig.maxVolume = 1;
```
参考文件NvEditConfig.js

## 导出配置项

```
resolution：输出视频分辨率
fps：输出视频fps
bitrateGrade：输出视频码率
bitrate：输出视频码率
autoSaveVideo：导出视频是否保存到相册
```
用户通过属性可以进行相关配置，例如：

### ios 
```swift
guard let videoConfig = videoConfig else { return }
// 导出配置 compileConfig
videoConfig.compileConfig.configure = ["video encoder name": "hevc","gopsize":10]
videoConfig.compileConfig.resolution = ._720
videoConfig.compileConfig.fps = 30
videoConfig.compileConfig.bitrateGrade = NvsCompileBitrateGradeHigh
videoConfig.compileConfig.bitrate = -1
videoConfig.compileConfig.autoSaveVideo = true
```
```
注：bitrate和bitrateGrade是互斥的，bitrate不为-1的时候，就使用该参数
```
参考文件[**NvCompileConfig**](./interface_nv_compile_config.html)

### Android
```java
NvCompileConfig compileConfig = new NvCompileConfig();
compileConfig.setResolution(NvCompileConfig.NvVideoCompileResolution.NvVideoCompileResolution_720);
compileConfig.setFps(25);
compileConfig.setBitrateGrade(NvCompileConfig.NvsCompileVideoBitrateGrade.NvsCompileBitrateGradeHigh);
compileConfig.setBitrate(-1);
compileConfig.setAutoSaveVideo(true);
```

参考文件[**NvCompileConfig**](./classcom_1_1meishe_1_1config_1_1_nv_compile_config.html)

### flutter
```dart
videoConfig.compileConfig.resolution =
        NvVideoCompileResolution.NvVideoCompileResolution_720;
videoConfig.compileConfig.fps = 25;
videoConfig.compileConfig.bitrateGrade =
        NvsCompileVideoBitrateGrade.NvsCompileBitrateGradeHigh;
videoConfig.compileConfig.bitrate = -1;
videoConfig.compileConfig.autoSaveVideo = true;
```
参考文件nv_compile_config.dart

### react-native
```js
this.videoConfig.compileConfig.resolution = NvVideoCompileResolution.NvVideoCompileResolution_720;
this.videoConfig.compileConfig.fps = 25;
this.videoConfig.compileConfig.bitrateGrade = NvsCompileVideoBitrateGrade.NvsCompileBitrateGradeHigh;
this.videoConfig.compileConfig.bitrate = -1;
this.videoConfig.compileConfig.autoSaveVideo = true;
```
参考文件NvCompileConfig.js

## 水印配置项
watermark: 图片，可以是asset内置资源，也可以是沙盒下的图片路径
width: 水印的宽，水印的参考范围是timeline的宽高（1080*1920，720*1280），在timeline上水印应该显示的宽高
height: 水印的高，水印的参考范围是timeline的宽高（1080*1920，720*1280），在timeline上水印应该显示的宽高
offsetX: 水平偏移量，参考位置是position，如果在做上角，那么x值就是相对视频左边的距离，如果在右下角，那么x值代表相对视频右边的距离
offsetY: 垂直偏移量，参考位置是position，如果在做上角，那么y值就是相对视频上边的距离，如果在右下角，那么y值代表相对视频下边的距离
position: 水印的位置，代表在timeline的那个角，左上，右上，左下，右下
### ios
```swift
videoConfig = NvVideoConfig()
guard let videoConfig = videoConfig else { return }
let configuration = NvWatermarkConfig()
configuration.watermark = NvImageConfig(name: "homepage_logo")
configuration.width = 150
configuration.height = 150
configuration.position = NvWaterMarkPosition(rawValue: 0)
configuration.offsetX = 40
configuration.offsetY = 40
videoConfig.compileConfig.watermarkConfig = configuration
let coverConfiguration = NvWatermarkConfig()
coverConfiguration.watermark = NvImageConfig(filePath: NSHomeDirectory() + "/Documents/coverlogo.png")
coverConfiguration.width = 150
coverConfiguration.height = 150
coverConfiguration.position = NvWaterMarkPosition(rawValue: 3)
coverConfiguration.offsetX = 40
coverConfiguration.offsetY = 40
videoConfig.compileConfig.coverWatermarkConfig = coverConfiguration
```
参考文件NvWatermarkConfig.h

### android
```java
private void testAddWatermarkConfig() {
    // 增加水印配置 add watermark config
    NvWatermarkConfig configuration = new NvWatermarkConfig();
    NvImageConfig imageConfig = new NvImageConfig();
//   imageConfig.setFilePath("assets:/water_mark/water_mark_meiying.png");
    imageConfig.setImageName("test_meicam_watermark");
    configuration.setNvImageConfig(imageConfig);
    configuration.setHeight(150);
    configuration.setWidth(150);
    configuration.setOffsetX(40);
    configuration.setOffsetY(40);
    configuration.setPosition(NvWatermarkConfig.NvsTimelineWatermarkPosition_BottomRight);
    mVideoConfig = NvModuleManager.get().getConfig();
    if (null == mVideoConfig) {
        mVideoConfig = new NvVideoConfig();
    }
    NvCompileConfig compileConfig = mVideoConfig.getCompileConfig();
    compileConfig.setAutoSaveVideo(true);
    compileConfig.setWatermarkConfig(configuration);
    compileConfig.setCoverWatermarkConfig(configuration);
    mVideoConfig.setCompileConfig(compileConfig);
}
```
参考文件 **NvWatermarkConfig**.java

### flutter
```dart
NvWatermarkConfig watermarkConfig = NvWatermarkConfig();
watermarkConfig.watermark = NvImageConfig.fromName("homepage_logo");
watermarkConfig.width = 150;
watermarkConfig.height = 150;
watermarkConfig.offsetX = 40;
watermarkConfig.offsetY = 40;
watermarkConfig.position =
    NvWaterMarkPosition.NvWaterMarkPositionTopRight;
videoConfig.compileConfig.watermarkConfig = watermarkConfig;
if (Platform.isAndroid) {
  getExternalStorageDirectory().then((directory) async {
    // Android 获取外部存储目录
    // Get external storage directory on Android
    directory ??= await getApplicationDocumentsDirectory();
    final coverPath = '${directory.path}/coverlogo.png';
    NvWatermarkConfig coverWatermarkConfig = NvWatermarkConfig();
    coverWatermarkConfig.width = 150;
    coverWatermarkConfig.height = 150;
    coverWatermarkConfig.offsetX = 40;
    coverWatermarkConfig.offsetY = 40;
    coverWatermarkConfig.position =
        NvWaterMarkPosition.NvWaterMarkPositionBottomRight;
    videoConfig.compileConfig.coverWatermarkConfig = coverWatermarkConfig;
    coverWatermarkConfig.watermark =
        NvImageConfig.fromFilePath(coverPath);
  });
} else if (Platform.isIOS) {
  getApplicationDocumentsDirectory().then((directory) async {
    NvWatermarkConfig coverWatermarkConfig = NvWatermarkConfig();
    coverWatermarkConfig.width = 150;
    coverWatermarkConfig.height = 150;
    coverWatermarkConfig.offsetX = 40;
    coverWatermarkConfig.offsetY = 40;
    coverWatermarkConfig.position =
        NvWaterMarkPosition.NvWaterMarkPositionBottomRight;
    videoConfig.compileConfig.coverWatermarkConfig = coverWatermarkConfig;
    final coverPath = '${directory.path}/coverlogo.png';
    coverWatermarkConfig.watermark =
        NvImageConfig.fromFilePath(coverPath);
  });
}
```
参考文件nv_watermark_config.dart

### ReactNative
```js
const config = videoConfig.current;
const watermarkConfig = new NvWatermarkConfig();
watermarkConfig.watermark = new NvImageConfig()
watermarkConfig.watermark.imageName = 'homepage_logo';
watermarkConfig.width = 150;
watermarkConfig.height = 150;
watermarkConfig.offsetX = 20;
watermarkConfig.offsetY = 20;
watermarkConfig.position = NvWaterMarkPosition.TopRight;
config.compileConfig.watermarkConfig = watermarkConfig;

const coverWatermarkConfig = new NvWatermarkConfig();
coverWatermarkConfig.watermark = new NvImageConfig()
const documentPath = (Platform.OS === 'ios') ? RNFS.DocumentDirectoryPath : RNFS.ExternalDirectoryPath;
coverWatermarkConfig.watermark.imagePath = documentPath + '/coverlogo.png';
coverWatermarkConfig.width = 150;
coverWatermarkConfig.height = 150;
coverWatermarkConfig.offsetX = 20;
coverWatermarkConfig.offsetY = 20;
coverWatermarkConfig.position = NvWaterMarkPosition.BottomRight;
config.compileConfig.coverWatermarkConfig = coverWatermarkConfig;
```
参考文件NvCompileWatermarkConfig.ts

## 模版配置项

```
maxSelectCount：自适应模版、一键成片最大可选片段数量
useAutoCut：是否有一键成片功能
```
用户通过属性可以进行相关配置，例如：
### ios
```Swift
videoConfig.templateConfig.maxSelectCount = 5
videoConfig.templateConfig.useAutoCut = false
```
参考文件[NvTemplateConfig](./interface_nv_template_config.html)

### Android
```java
NvTemplateConfig templateConfig = new NvTemplateConfig();
templateConfig.setMaxSelectCount(5);
templateConfig.setUseAutoCut(false);
```

参考文件[NvTemplateConfig](./classcom_1_1meishe_1_1config_1_1_nv_template_config.html)

### flutter
```dart
videoConfig.templateConfig.maxSelectCount = 5;
videoConfig.templateConfig.useAutoCut = false;
```
参考文件nv_template_config.dart

### react-native
```
this.videoConfig.templateConfig.maxSelectCount = 5;
this.videoConfig.templateConfig.useAutoCut = false;
```
参考文件NvTemplateConfig.js

## 模型配置项
```
注：工程内创建灰色的文件夹，把相关替换的模型放入，传入模型的文件名即可
```

用户通过属性可以进行相关配置，例如：
### ios
```swift
videoConfig.modelConfig.use240 = true
videoConfig.modelConfig.face240 = "ms_face240_v2.0.8.model"
```
参考文件[NvModelConfig](./interface_nv_model_config.html)

### Android
```java
NvModelConfig modelConfig = new NvModelConfig();
modelConfig.setUse240(true);
modelConfig.setFace240("ms_face240_v2.0.8.model");
```

参考文件[NvModelConfig](./classcom_1_1meishe_1_1config_1_1_nv_model_config.html)

### flutter
```dart
videoConfig.modelConfig.use240 = true;
videoConfig.modelConfig.face240 = "ms_face240_v2.0.8.model";
```
参考文件nv_model_config.dart

### react-native
```js
this.videoConfig.modelConfig.use240 = true;
this.videoConfig.modelConfig.face240 = "ms_face240_v2.0.8.model";
```
参考文件NvModelConfig.js

## 短视频回调
在编辑页面点击下一步的时候，会触发下面的publish回调，用于进入发布页面。
### ios
```swift
public protocol NvModuleManagerDelegate: NSObjectProtocol {
    /*!
     * \if ENGLISH
     *
     *  \brief Edit complete, jump release callback
     *  @param taskId  Edit the event id used to exit the module
     *  @param coverImagePath cover
     *  @param hasDraft Whether there is a draft button
     *  @param draftInfo The title displayed on the publish page
     *  @param videoEditNavigationController Current nav controller
     *  \else
     *
     *  \brief 编辑完成，跳转发布回调
     *  @param taskId 编辑事件id，用于退出模块
     *  @param coverImagePath 封面图
     *  @param hasDraft 是否有草稿按钮
     *  @param draftInfo 发布页显示的标题
     *  @param videoEditNavigationController 当前nav控制器
     *  \endif
     *  \sa exitVideoEdit:
     */
    func publish(withProjectId projectId: String,
                            coverImagePath: String,
                            hasDraft: Bool, 
                            videoPath: String?, 
                            description: String?, 
                            videoEdit videoEditNavigationController: UINavigationController)
}
```
```dart
shortVideoOperator().setVideoEditEventHandler((event, info) {
  if (event == NvVideoEditEvent.publish) {
    //注册跳转到发布页回调
    //Register to jump to the release page callback
    var resultPage =
        VideoEditResultPage(title: S.of(context).Publish, arguments: info);
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (BuildContext context) {
          return resultPage;
        },
      ),
    );
  }
});
```
```js
const videoOperator = NvShortVideo.shareInstance();
videoOperator.configServerInfo(map);
videoOperator.setVideoEditEventHandler(handleVideoEditEvent);
const handleVideoEditEvent = (event, info) => {
  if (event === NvVideoEditEvent.publish) {
    props.navigation.navigate('VideoResult', { projectInfo: info });
  }
};
```
在发布页面可以通过下面的回调来监听导出后的进度和完成情况
```swift
// MARK: - NvModuleManagerCompileStateDelegate
func didCompileCompleted(_ outputPath: String?, error: Error?) {
    DispatchQueue.main.async { [weak self] in
        NvToast.hiddenToastAction()
        if let _ = error {
            NvToast.showToastAction(message: NSLocalizedString("Save_Failed", comment: ""))
        } else {
            self?.videoPath = outputPath
            NvToast.showToastAction(message: NSLocalizedString("Save_Successful", comment: ""))
        }
        let publishInfo = self?.moduleManager.publishInfo
        print("publishinfo:\(String(describing: publishInfo?.videoPath))")
    }
}

func didCompileFloatProgress(_ progress: Float) {
    print("didCompileFloatProgress: \(progress)")
}

func didGenerateImagesType(_ type: Int32, results result: [String]?, error: (any Error)?) {
    NvToast.showToastAction(message: NSLocalizedString("Save_Successful", comment: ""))
}
```
```dart
shortVideoOperator()
    .setVideoCompileEventHandler((event, compileInfo) async {
  if (event == NvVideoCompileEvent.progress) {
    double progress = compileInfo["progress"];
    setState(() {
      _popupProgress = progress / 100;
      _popupLabel = '${(progress).toInt()}%';
      _popupDetailLabel = "";
    });
    // 确保在进度更新期间弹窗状态保持为true
    if (!_isPopupShowing) {
      setState(() {
        _isPopupShowing = true;
        _isCriticalOperation = true;
      });
      debugPrint(
          'Video compilation in progress, ensuring _isPopupShowing is true');
    }
  } else if (event == NvVideoCompileEvent.complete) {
    shortVideoOperator().getPublishInfo().then((value) {
      final publishInfo = value.videoPath;
      debugPrint("NvPublishInfo in complete event:$publishInfo");
    });
    String? outputPath = compileInfo["outputPath"];
    debugPrint("compile outputPath:$outputPath");
    if (outputPath == null) {
      int errorCode = compileInfo["errorCode"];
      String? errorString = compileInfo["errorString"];
      if (errorCode == -2) {
        setState(() {
          _popupLabel = S.of(context).compile_cancel;
          _popupDetailLabel = "";
        });
      } else {
        setState(() {
          _popupLabel = S.of(context).compile_fail;
          _popupDetailLabel = errorString ?? "";
        });
      }
    } else {
      setState(() {
        _popupLabel = saveVideoAndPop
            ? S.of(context).save_suc
            : S.of(context).compile_suc;
        _popupDetailLabel = "";
      });
      localVideoPath = outputPath;
      debugPrint("compile localVideoPath:$localVideoPath");
    }
    await Future.delayed(const Duration(milliseconds: 500));
    dismissPopup();
    if (isFirstBuild) isFirstBuild = false;
    setState(() {});
    if (saveVideoAndPop && outputPath != null) Navigator.of(context).pop();
  } else if (event == NvVideoCompileEvent.coverImageSelected) {
    debugPrint("setSaveImageEventHandler:$compileInfo");
    String coverImagePath = compileInfo["coverImagePath"];
    if (coverImagePath.isNotEmpty) {
      widget.arguments["coverImagePath"] = coverImagePath;
      setState(() {});
    }
  } else if (event == NvVideoCompileEvent.generateImagesResult) {
    debugPrint("generateImagesResult:$compileInfo");
    int type = compileInfo["type"];
    if (type == 0) {
      setState(() {});
    }
  }
});
```
```js
NvShortVideo.shareInstance().setVideoCompileEventHandler(
  this.handleEvent.bind(this),
);
handleEvent(nMethod, nArguments) {
  // console.log('------->🌹  nMethod:', nMethod);
  if (nMethod == NvVideoCompileEvent.progress) {
    //更新进度
    //Update progress
  } else if (nMethod == NvVideoCompileEvent.complete) {
    RNProgressHud.dismiss();
    NvShortVideo.shareInstance().getPublishInfo().then((publishInfo) => {
      console.log('------->🌹  publishInfo videoPath:', publishInfo.videoPath);
      console.log('------->🌹  publishInfo musicUrl:', publishInfo.musicInfo.musicUrl);
    });
    let errorCode = nArguments.errorCode;
    if (errorCode == 0) {
      //成功
      //Sucess
      let outputPath = nArguments.outputPath;
      if (outputPath) {
        this.setState({
          localImagePath: outputPath,
        });
      }
      if (this.state.saveVideoShowPath) {
        RNProgressHud.showInfoWithStatus(
          I18n.t('ResultFilePath') + outputPath,
          1,
        );
        // this.props.navigation.goBack();
      }
    } else if (errorCode == 1) {
      //取消
      //Cancel
      RNProgressHud.showInfoWithStatus(I18n.t('Cancelled'), 1);
    } else {
      //失败
      //Failed
      console.log('Completed error:', nArguments);
      RNProgressHud.showErrorWithStatus(I18n.t('Error') + errorCode, 1);
    }
    this.setState({
      firstComplie: false,
    });
  } else if (nMethod == NvVideoCompileEvent.coverImageSelected) {
    let imagePath = nArguments.coverImagePath;
    if (imagePath) {
      this.setState({
        projectInfo: { ...this.state.projectInfo, coverImagePath: imagePath },
      });
    }
  } else if (nMethod == NvVideoCompileEvent.generateImagesResult) {
    console.log('GenerateImagesResult:', nArguments);
    RNProgressHud.showInfoWithStatus(I18n.t('Save_suc'), 1);
  }
}
```
在导出视频完成后`NvModularManager`中提供了一个`publishInfo`属性来获取发布相关的信息，里面包含了视频路径、音乐等信息，用户可以通过这些信息进入自己的发布页面。
```swift
@objcMembers
public class NvTemplateData: NSObject {
    public var templateId: String?
    public var name: String?
}
@objcMembers
public class NvMusicInfo: NSObject {
    public var iconUrl: String?
    public var duration: Int64 = 0
    public var musicName: String?
    public var musicSinger: String?
    public var musicUrl: String?
    public var localFilePath: String?
    public var trimIn: Int64 = 0
    public var trimOut: Int64 = 0
    public var musicId: String?
}

@objcMembers
public class NvPublishInfo: NSObject {
    public var videoPath: String?
    public var coverPath: String?
    public var imagesPath: [String]?
    public var musicInfo: NvMusicInfo?
    public var templateInfo: NvTemplateData?
}
```
```dart
class NvPublishInfo {
  String? videoPath;
  String? coverPath;
  List<String>? imagesPath;
  NvMusicInfo? musicInfo;
  NvTemplateInfo? templateInfo;
}

class NvMusicInfo {
  String? iconUrl;
  int64 duration = 0;
  String? musicName;
  String? musicSinger;
  String? musicUrl;
  String? localFilePath;
  int64 trimIn = 0;
  int64 trimOut = 0;
  String? musicId;
}
class NvTemplateInfo {
  String? templateId;
  String? name;
}

shortVideoOperator().getPublishInfo().then((value) {
  final publishInfo = value.videoPath;
  debugPrint("NvPublishInfo in complete event:$publishInfo");
});
```
```js
class NvTemplateInfo {
  templateId;
  name;
  constructor(init) {
      if (init) Object.assign(this, init);
  }
}
exports.NvTemplateInfo = NvTemplateInfo;
class NvMusicInfoModel {
    iconUrl;
    duration = 0;
    musicName;
    musicSinger;
    musicUrl;
    localFilePath;
    trimIn = 0;
    trimOut = 0;
    musicId;
    constructor(init) {
        if (init)
            Object.assign(this, init);
    }
}
exports.NvMusicInfoModel = NvMusicInfoModel;
class NvPublishInfo {
    videoPath;
    coverPath;
    imagesPath;
    musicInfo;
    templateInfo;
    constructor(init) {
        if (init)
            Object.assign(this, init);
    }
}
exports.NvPublishInfo = NvPublishInfo;
```
