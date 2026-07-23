---
html:
    toc: true
print_background: true
---

<!-- MEISHE_AGENT_DOC_ENHANCED: v1 -->

# 预制素材配置

<!-- BEGIN MEISHE_AGENT_QUICK_INDEX -->
> **Agent 快速索引**
> - **Doc ID**: `native-quickstart-doc-ch-prefabricatedmaterial-ch`
> - **语言轨道**: `shared`
> - **平台**: `android, ios`
> - **标签**: `prefabricated-material, download, server-config, native, flutter, react-native`
> - **图片数**: `9`
> - **用法**: 先按标签定位章节，再读取相邻步骤、配置表和图片解析；不要跳过本页内的注意事项。
<!-- END MEISHE_AGENT_QUICK_INDEX -->



## 前言
在短视频工程中，会用到一些内置素材，这部分素材包括美颜功能、字幕功能

开发短视频的用户在获得美摄sdk的授权之后，这些素材需要先在商场购买，接入短视频工程之前，先配置预制素材，如果在购买素材或者配置中遇到问题，请联系商务

```
警告：文件夹的名称和格式不可以修改
```

## 具体操作流程

### 第一步
在浏览器中输入下面的地址，获取最新的预制素材包的下载地址
https://mall.meishesdk.com/api/shortvideo/materialcenter/beautyAssets/latest

浏览器返回的数据中有最新的预制素材包下载地址
![alt text](../assets/image-7.png)
> **图片解析：** `path=../assets/image-7.png`，`size=2658x114`，用途：步骤截图；执行前结合上一标题和相邻文字确认路径与配置。

在浏览器中输入packageUrl字段，就可以下载最新的预制素材包，将压缩包进行解压

![alt text](../assets/image-1.png)
> **图片解析：** `path=../assets/image-1.png`，`size=1552x798`，用途：步骤截图；执行前结合上一标题和相邻文字确认路径与配置。

其中beauty中是美颜相关的文件
```

beautyEffect.json：美颜配置项
beautyEffect：美颜配置项依赖文件

beautyShape.json：美型配置项
beautyShape：美型配置项依赖文件

beautyMicro.json：微整形配置项
beautyMicro：微整形配置项依赖文件

beautyAdjust.json：调节配置项
beautyAdjust：调节配置项依赖文件

previewEffect.json：画面调节配置项
previewEffect：画面调节配置项依赖文件

matting.json：内置抠像配置项
matting：内置抠像配置项依赖文件
```

caption是和字幕相关的文件
```
caption.json：字幕配置项
caption：字幕配置项依赖文件
```

settings.json是版本控制json文件

### 第二步
打开beautyEffect文件夹
![alt text](../assets/image-2.png)
> **图片解析：** `path=../assets/image-2.png`，`size=1622x806`，用途：步骤截图；执行前结合上一标题和相邻文字确认路径与配置。

.videofx的文件是我们的滤镜包，用户需要在素材商场购买相关的素材包并且下载，购买和下载流程请咨询商务，下载已购素材包之后会得到一个这样的文件夹，只需要把.videofx和.lic文件拷贝到beautyEffect文件夹下即可，如果的素材包的uuid和版本号发生了变化，需要更改beautyEffect.json文件

![alt text](../assets/image-3.png)
> **图片解析：** `path=../assets/image-3.png`，`size=1372x370`，用途：步骤截图；执行前结合上一标题和相邻文字确认路径与配置。

例如

3C83CF18-FF4A-4541-9FA4-F715B2C2D79C.2.videofx素材包下载之后

变成了3C83CF18-FF4A-4541-9FA4-F715B2C2D79C.4.videofx

版本发生了变化，需要修改beautyEffect.json的配置项，把packageUrl换成3C83CF18-FF4A-4541-9FA4-F715B2C2D79C.4.videofx

![alt text](../assets/image-4.png)
> **图片解析：** `path=../assets/image-4.png`，`size=1230x448`，用途：步骤截图；执行前结合上一标题和相邻文字确认路径与配置。

.png是使用到的封面图标，用户可以自行替换，如果用户修改了图标名称，需要修改beautyEffect.json的配置项，替换coverImage字段

![alt text](../assets/image-5.png)
> **图片解析：** `path=../assets/image-5.png`，`size=1172x438`，用途：步骤截图；执行前结合上一标题和相邻文字确认路径与配置。

.mslut文件是效果需要的特殊文件，不建议用户替换


### 第三步

打开beautyShape、beautyMicro、beautyAdjust、caption等文件夹，替换里面的素材

其中.facemesh、.warp、.animatedsticker都是美摄的素材包，都需要购买下载，流程参考[第二步](#第二步)

### 第四步

替换完成之后，修改settings.json，增加一次版本号，将1.0.0升级到1.0.1

![alt text](../assets/image-6.png)
> **图片解析：** `path=../assets/image-6.png`，`size=504x178`，用途：步骤截图；执行前结合上一标题和相邻文字确认路径与配置。

### 第五步

全部修改完毕之后，将NvBundleAssets文件夹压缩，并且重新上传，可以联系商务协助

## json字段含义

列出可以修改的字段，用户根据需要修改使用

```
coverImage：未选中图标
selectedCoverImg：选中图标
value：当前值
defaultValue：默认值
packageUrl：所使用到的素材包或者文件
```

# 模型配置
## 说明
短视频工程中，会用到一些内置模型
## 具体操作流程

### 第一步
在浏览器中输入下面的地址，获取最新的预制素材包的下载地址
https://mall.meishesdk.com/api/shortvideo/test/materialcenter/beautyAssets/latest?assetType=model

浏览器返回的数据中有最新的预制素材包下载地址
![alt text](../assets/image-8.png)
> **图片解析：** `path=../assets/image-8.png`，`size=2468x144`，用途：步骤截图；执行前结合上一标题和相邻文字确认路径与配置。

在浏览器中输入packageUrl字段，就可以下载最新的预制素材包，将压缩包进行解压

![alt text](../assets/image-9.png)
> **图片解析：** `path=../assets/image-9.png`，`size=978x532`，用途：步骤截图；执行前结合上一标题和相邻文字确认路径与配置。

### 第二步
根据需要替换你的模型文件
替换完成之后，修改settings.json，增加一次版本号，将1.0.0升级到1.0.1

### 第三步
全部修改完毕之后，将NvModelFiles文件夹压缩，并且重新上传，可以联系商务协助

<!-- BEGIN MEISHE_AGENT_IMAGE_INDEX -->
## Agent 图片索引

| Image | Size | Exists | Inferred use |
| --- | --- | --- | --- |
| `../assets/image-7.png` | `2658x114` | `true` | 步骤截图；执行前结合上一标题和相邻文字确认路径与配置 |
| `../assets/image-1.png` | `1552x798` | `true` | 步骤截图；执行前结合上一标题和相邻文字确认路径与配置 |
| `../assets/image-2.png` | `1622x806` | `true` | 步骤截图；执行前结合上一标题和相邻文字确认路径与配置 |
| `../assets/image-3.png` | `1372x370` | `true` | 步骤截图；执行前结合上一标题和相邻文字确认路径与配置 |
| `../assets/image-4.png` | `1230x448` | `true` | 步骤截图；执行前结合上一标题和相邻文字确认路径与配置 |
| `../assets/image-5.png` | `1172x438` | `true` | 步骤截图；执行前结合上一标题和相邻文字确认路径与配置 |
| `../assets/image-6.png` | `504x178` | `true` | 步骤截图；执行前结合上一标题和相邻文字确认路径与配置 |
| `../assets/image-8.png` | `2468x144` | `true` | 步骤截图；执行前结合上一标题和相邻文字确认路径与配置 |
| `../assets/image-9.png` | `978x532` | `true` | 步骤截图；执行前结合上一标题和相邻文字确认路径与配置 |
<!-- END MEISHE_AGENT_IMAGE_INDEX -->
