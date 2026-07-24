---
html:
    toc: true
print_background: true

---

<!-- MEISHE_AGENT_DOC_ENHANCED: v1 -->


# Meishe React Native short video module access guide

<!-- BEGIN MEISHE_AGENT_QUICK_INDEX -->
> **Agent Quick Index**
> - **Doc ID**: `react-native-quickstart-doc-en-quickstart-en`
> - **Track**: `react-native`
> - **Platforms**: `android, ios`
> - **Tags**: `quickstart, integration, react-native, android, ios, local-plugin, yarn, permission, license, server-config`
> - **Image count**: `5`
> - **Usage**: Locate sections by tags first, then read adjacent steps, config tables, and image notes.
<!-- END MEISHE_AGENT_QUICK_INDEX -->




## General Integration Process

<!-- BEGIN MEISHE_AGENT_SECTION_HINT -->
> **Agent section hint:** tags `integration`. Check steps, config values, paths, and permission requirements before editing.
<!-- END MEISHE_AGENT_SECTION_HINT -->

* First, follow the current documentation for integration.
* Contact the sales department to request SDK authorization.
* By default, ShortVideo uses Meishe's own server. After integration, you will be required to migrate the server to your own server. Contact the sales department and we will arrange for a team to deploy the server for you.
* **If you need to modify the current app's display, refer to the UI configuration or module configuration in the current documentation. (If you don't need to modify the UI, ignore this step.)**

## Development environment requirements

- react-native ^0.41.2
- iOS   
  - iOS 12.0 and above
  - Swift 5
  - CocoaPods
- Anroid
  - Android Studio 3.0+

> ⚠️ **Note:**  This feature must be run on a physical device, as it is currently not supported on the simulator.

## Upgrade short video notes
### Version 2.0.0 Updates:
* Fixed some known issues. iOS version is 2.0.0, and Android version is 1.5.1.
### Version 1.5.1 Updates:
* Fixed some known issues
### Version 1.5.0 Updates:
* **This release involves significant updates; therefore, regression testing is absolutely essential prior to deployment—particularly regarding changes to configuration settings.**
### 1.4.0 Version upgrade：
* The VideoEditPlugin file has changed; please be aware of this during the upgrade.
* **The NvStreamingSdkCore.xcframework has been upgraded to version 3.15.3. If you are upgrading from a version below 1.4.0, you need to contact your business team to update the SDK license. This upgrade is only available for iOS.**
* The AutoCut video creation feature has been completely upgraded. You can now contact our server-side development team in a group chat to assist with upgrading the server-side interface. This upgrade is only available for iOS; Android is not yet supported. Therefore, to use the AutoCut video creation feature, you must contact our server-side team for assistance. Please feel free to contact us with any questions.
  ```
    var assetAutoCutUrl = '';
    if (Platform.OS === 'ios') {
      assetAutoCutUrl = 'https://creative.meishesdk.com/api/app/aivideo/asset/all/1';
    } else {
      assetAutoCutUrl = 'materialcenter/recommend/listTemplate';
    }

  // Initialize server config
  useEffect(() => {
    const map = {
      host: 'https://mall.meishesdk.com/api/shortvideo/v1/',
      assetRequestUrl: 'materialcenter/mall/custom/listAllAssemblyMaterial',
      assetCategoryUrl: 'materialcenter/appSdkApi/listTypeAndCategory',
      assetMusiciansUrl: 'materialcenter/appSdkApi/listMusic',
      assetFontUrl: 'materialcenter/listFont',
      assetDownloadUrl: 'materialcenter/mall/custom/materialInteraction',
      assetPrefabricatedUrl: 'materialcenter/beautyAssets/latest',
      assetAutoCutUrl: assetAutoCutUrl,
      assetTagUrl: 'materialcenter/listTemplateTag',
      clientId: '7480f2bf193d417ea7d93d64',
      clientSecret: 'e4434ff769404f64b33f462331a80957',
      assemblyId: 'MEISHE_MATERIAL_LIST',
      isAbroad: 1,
    };
  ```
* **For server updates, please contact our server team.**
### 1.2.8 Version upgrade：
* **In version 1.2.7, you need to download resources before entering shooting, editing, and co-shooting. The new version will not block the entry into shooting, editing, and co-shooting, and will silently download in the background when entering. It also provides an interface for users to actively call it. If the user does not actively call shortvideo, it will be called by default.**
```ts
downloadPrefabricatedMaterial(): Promise<boolean>;
```
### 1.2.7 Version upgrade：
* **ReactNative users, please replace the react_native/react-native-nvshortvideo/ folder and replace the license file (flutter/nvshortvideo/ios/Assets/meicam_licence.lic)**
//Shooting entrance
`startVideoCapture(config: videoConfig): Promise<boolean>;`
//PIP entrance
`startVideoDualCapture(config: videoConfig): Promise<boolean>;`
//Editing entrance
`startSelectFilesForEdit(config: videoConfig): Promise<boolean>;`
//Save image to album
`saveImageToAlbum(): Promise<string>;`
//Whether there is only one picture when editing
`isOnlyHaveImage(): Promise<boolean>;`
//Show saveing options panel
`showSaveOptionsPanel():Promise<number>;`

## Support media formats

For details, see: [Meishes sdk product overview](https://www.meishesdk.com/ios/doc_en/html/content/Introduction_8md.html)

## Short video module integration

<!-- BEGIN MEISHE_AGENT_SECTION_HINT -->
> **Agent section hint:** tags `integration`. Check steps, config values, paths, and permission requirements before editing.
<!-- END MEISHE_AGENT_SECTION_HINT -->


After the short video module is downloaded and decompressed, it can be used as Flutter’s local private library. The decompressed file directory is as follows:

![alt text](../assets/image.png)
> **Image parse:** `path=../assets/image.png`, `size=491x303`, use: step screenshot; inspect near the preceding heading before editing.

1. **Add dependencies**
   Run the following command in the root directory of the App project:

   ```shell
    yarn add file:xxx/react-native-nvshortvideo
   ```

   **> Important：It is recommended to use the yarn command, If you use the npm command, refer to the [npm documentation](https://docs.npmjs.com/cli/install)**

2. **Update native dependency**

    iOS： cd ios && **pod install**

    Android：

       1.Execute yarn install in the current project
       2.yarn start

3. FAQ

   Android：

   （1）After running Android with yarn start, the following error is displayed

   ![](../assets/android_compile_1.png)
> **Image parse:** `path=../assets/android_compile_1.png`, `size=1675x283`, use: Android build issue and resolution reference.

   solve:

   ![](../assets/android_compile_1_resolve.png)
> **Image parse:** `path=../assets/android_compile_1_resolve.png`, `size=1262x688`, use: Android build issue and resolution reference.

## System authorization

### iOS

App needs to add the following permissions in **Info.plist**, otherwise it will not be able to use the short video module.

```xml
<key>NSCameraUsageDescription</key>
<string>AppYour consent is required to access the camera</string>
<key>NSMicrophoneUsageDescription</key>
<string>AppYour consent is required to access the microphone</string>
<key>NSPhotoLibraryUsageDescription</key>
<string>AppYour consent is required to access the album</string>
<key>NSAppleMusicUsageDescription</key>
<string>AppYour consent is required to access music</string>
```

### Android

  TODO：Add the following permissions in **AndroidManifest.xml**

```xml
 <uses-permission android:name="android.permission.SYSTEM_ALERT_WINDOW" />
  <uses-permission android:name="android.permission.CAMERA" />
  <uses-permission android:name="android.permission.RECORD_AUDIO" />
  <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" />
  <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" /> <!-- <uses-permission android:name="android.permission.MOUNT_UNMOUNT_FILESYSTEMS" /> -->
  <uses-permission android:name="android.permission.INTERNET" />
  <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
  <uses-permission android:name="android.permission.VIBRATE" />
  <uses-permission android:name="android.permission.WAKE_LOCK" />
  <uses-permission android:name="android.permission.ACCESS_NOTIFICATION_POLICY" /> <!-- <uses-permission android:name="android.permission.INTERNET" /> -->
  <uses-permission android:name="android.permission.ACCESS_WIFI_STATE" />
  <uses-permission android:name="android.permission.CHANGE_WIFI_STATE" /> <!-- 用于进行网络定位 -->
  <uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" /> <!-- 用于访问GPS定位 -->
  <uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" /> <!-- 用于读取手机当前的状态 -->
  <uses-permission android:name="android.permission.REQUEST_INSTALL_PACKAGES" />
  <uses-permission android:name="android.permission.EXPAND_STATUS_BAR" />
```

## Meishe SDK authorization

Meishe SDK authorization method:

After registering as a user on [Meishe‘s official website](https://en.meishesdk.com/), create an application and configure the App package name. After a Meishe business colleague activates the authorization, you can download the authorization file in the application information.

Replace the authorization file in the short video module package with the downloaded authorization .lic file. The path in the module package:

- iOS：
   ![alt text](../assets/image_lic.png)
> **Image parse:** `path=../assets/image_lic.png`, `size=973x311`, use: license file placement or authorization UI reference.
- Android：
   ![alt text](../assets/image_lic_android.png)
> **Image parse:** `path=../assets/image_lic_android.png`, `size=1662x329`, use: license file placement or authorization UI reference.
> The SDK authorization is bound to the package name of the App. When it is not authorized, all functions of the SDK can be used without checking the authorization, and the drawn picture will have the MEISHE watermark.

## Network interface configuration

<!-- BEGIN MEISHE_AGENT_SECTION_HINT -->
> **Agent section hint:** tags `server-config`. Check steps, config values, paths, and permission requirements before editing.
<!-- END MEISHE_AGENT_SECTION_HINT -->


The filters, stickers, music and other files used in the short video module are all obtained through the network interface. The server needs to implement the corresponding interface according to the interface document.
Configure the server address and public parameters in the App project.

```javascript
import { NvShortVideo, NvVideoConfig } from 'react-native-nvshortvideo';
...
  //服务器地址
  //Server url
  /// assetRequestUrl  素材列表请求 Material list request
  /// assetCategoryUrl 素材分类列表请求 Material category list request
  /// assetMusiciansUrl 音乐列表请求 Music list request
  /// assetFontUrl 字体列表请求 Font list request
  /// assetDownloadUrl 下载地址请求 Download address request
  /// assetPrefabricatedUrl 预制素材请求 Prefabricated material request
  /// assetAutoCutUrl 一键成片网络请求 AutoCut request
  /// assetTagUrl 模版标签列表请求 Template tag list request
  /// clientId clientId
  /// clientSecret clientSecret
  /// assemblyId assemblyId
  /// isAbroad 海外数据请求，0==全部，1==海外 Overseas data request, 0== all, 1== overseas
  let map = {
      'host': 'https://mall.meishesdk.com/api/shortvideo/',
      'assetRequestUrl': 'materialcenter/mall/custom/listAllAssemblyMaterial',
      'assetCategoryUrl': 'materialcenter/appSdkApi/listTypeAndCategory',
      'assetMusiciansUrl': 'materialcenter/appSdkApi/listMusic',
      'assetFontUrl': 'materialcenter/listFont',
      'assetDownloadUrl': 'materialcenter/mall/custom/materialInteraction',
      'assetPrefabricatedUrl': 'materialcenter/beautyAssets/latest',
      'assetAutoCutUrl': 'materialcenter/recommend/listTemplate',
      'assetTagUrl': 'materialcenter/listTemplateTag',
      'clientId': '7480f2bf193d417ea7d93d64',
      'clientSecret': 'e4434ff769404f64b33f462331a80957',
      'assemblyId': 'MEISHE_MATERIAL_LIST',
      'isAbroad': 1
  };
  let videoOperator = NvShortVideo.shareInstance();
  videoOperator.configServerInfo(map);
```

## Preset material

<!-- BEGIN MEISHE_AGENT_SECTION_HINT -->
> **Agent section hint:** tags `prefabricated-material`. Check steps, config values, paths, and permission requirements before editing.
<!-- END MEISHE_AGENT_SECTION_HINT -->


The material packages that the short video module relies on can be selected as needed. For details of preset materials, see: [Short video module preset materials](../../nv_short_video_ios_doc/doc_en/html/PrefabricatedMaterial_en.html)
Download preset materials. If you call this interface, shortvideo will not call it repeatedly when entering. If you do not call it, shortvideo will default to background calling when entering.
```ts
/*! \if ENGLISH
 *
 *  \brief Download material
 *  \param completionHandler Completion callback
 *  \else
 *  \endif
 *  */
downloadPrefabricatedMaterial(): Promise<boolean>;
```

## Main methods of short video module

Module singleton: let videoOperator = NvShortVideo.shareInstance();
Example call:

```javascript
import { NvShortVideo, NvVideoConfig } from 'react-native-nvshortvideo';

...

let videoOperator = NvShortVideo.shareInstance();
videoOperator.startVideoCaptrue(this.videoConfig);
```

### Video recording

```javascript
 /*! \if ENGLISH
 *
 *  \brief Shooting entrance
 *  \param config Configuration item
 *  \param music The default is nil，If you need to shoot with music, you need to pass an audio object, and the path of the audio must be local and has been downloaded
 *  \else
 *
 *  \brief 拍摄入口
 *  \param config 配置项
 *  \param music 默认是nil，如果拍摄时需要带音乐拍摄，需要传递一个音频对象，音频的路径必须是本地的，已经下载的路径
 *  \endif
 */
startVideoCaptrue(config?: NvVideoConfig, musicInfo?: NvMusicInfo): void;
```

### Picture in Picture

```javascript
/*! \if ENGLISH
 *
 *  \brief PIP entrance By default, the album is opened, and a material from the album is taken into the beat
 *  \param config Configuration item
 *  \else
 *
 *  \brief 合拍入口，默认打开相册，从相册取一个素材进入合拍
 *  \param config 配置项
 *  \endif
 */
startVideoDualCaptrue(config?: NvVideoConfig): void;

/*! \if ENGLISH
 *
 *  \brief PIP entrance
 *  \param config Configuration item
 *  \param videoPath The video path to be filmed must be a local path
 *  \else
 *
 *  \brief 合拍入口
 *  \param config 配置项
 *  \param videoPath 准备合拍的视频路径，必须是本地路径
 *  \endif
 */
startVideoDualCaptrueWithVideo(videoPath: string, config?: NvVideoConfig): void;
```

### Video editing

<!-- BEGIN MEISHE_AGENT_SECTION_HINT -->
> **Agent section hint:** tags `function-config`. Check steps, config values, paths, and permission requirements before editing.
<!-- END MEISHE_AGENT_SECTION_HINT -->


```javascript
/*! \if ENGLISH
 *
 *  \brief Edit entrance
 *  \param config Configuration item
 *  \else
 *
 *  \brief 编辑入口
 *  \param config 配置项
 *  \endif
 */
startSeleteFilesForEdit(config?: NvVideoConfig): void;
```

### Video editing complete callback

<!-- BEGIN MEISHE_AGENT_SECTION_HINT -->
> **Agent section hint:** tags `function-config`. Check steps, config values, paths, and permission requirements before editing.
<!-- END MEISHE_AGENT_SECTION_HINT -->


```javascript
/*! \if ENGLISH
 *  \brief Edit module event callback
 *  \else
 *  \brief 编辑模块事件回调
 *  \endif
*/
setVideoEditEventHandler(handler?: (event: NvVideoEditEvent, info: Map<string, string>) => void): void;
```

### Select cover

```javascript
/*! \if ENGLISH
 *  \brief selete cover image
 *  \else
 *  \brief 选择封面图片
 *  \endif
*/
selectCoverImage(): Promise<Map<string, any>>;
```

### Save draft

<!-- BEGIN MEISHE_AGENT_SECTION_HINT -->
> **Agent section hint:** tags `function-config`. Check steps, config values, paths, and permission requirements before editing.
<!-- END MEISHE_AGENT_SECTION_HINT -->


```javascript
/*! \if ENGLISH
 *  \brief save draft
 *  \else
 *  \brief 保存草稿
 *  \endif
 */
saveDraft(info: string): Promise<Map<string, any>>;
```

### Synthetic video

```javascript
/*! \if ENGLISH
 *  \brief Composite video
 *  \else
 *  \brief 合成视频
 *  \endif
 */
compileCurrentTimeline(configure: Map<string, string>): Promise<Map<string, any>>;
```

### Video synthesis callback

```javascript
/*! \if ENGLISH
 *  \brief Composite video event callback
 *  \else
 *  \brief 视频合成事件回调
 *  \endif
 */
setVideoCompileEventHandler(handler?: (event: NvVideoCompileEvent, compileInfo: Map<string, string>) => void): void;
```

### Save cover image

```javascript
/*! \if ENGLISH
 *  \brief save image
 *  \else
 *  \brief 保存图片
 *  \endif
 */
saveImage(coverImagePath: string): Promise<Map<string, any>>;
```

### Exit short video module

Call it when the video publishing page exits

```javascript
/*! \if ENGLISH
 *
 *  \brief Exit the entire publisher call
 *  \param taskId Returned by the edit completion callback
 *  \warning This method will clean up the current draft and SDK-held resources, please call after completely exiting the editing and publishing process
 *  \else
 *
 *  \brief 退出整个发布器调用
 *  \param taskId 由编辑完成回调中返回
 *  \warning 该方法会清理当前草稿以及sdk持有资源，请在完全退出编辑发布流程之后，调用
 *  \endif
 */
  exitEdit(taskId: String): void;
```

### Get draft list

<!-- BEGIN MEISHE_AGENT_SECTION_HINT -->
> **Agent section hint:** tags `function-config`. Check steps, config values, paths, and permission requirements before editing.
<!-- END MEISHE_AGENT_SECTION_HINT -->


```javascript
/*! \if ENGLISH
 *  \brief get draft list
 *  \else
 *  \brief 获取草稿列表
 *  \endif
*/
getDraftList(): Promise<Map<string, any>>;
```

### Delete draft

<!-- BEGIN MEISHE_AGENT_SECTION_HINT -->
> **Agent section hint:** tags `function-config`. Check steps, config values, paths, and permission requirements before editing.
<!-- END MEISHE_AGENT_SECTION_HINT -->


```javascript
/*! \if ENGLISH
 *  \brief delete draft
 *  \else
 *  \brief 删除草稿
 *  \endif
*/
deleteDraft(draftId: string): Promise<Map<string, any>>;
```

### Open draft

<!-- BEGIN MEISHE_AGENT_SECTION_HINT -->
> **Agent section hint:** tags `function-config`. Check steps, config values, paths, and permission requirements before editing.
<!-- END MEISHE_AGENT_SECTION_HINT -->


```javascript
/*! \if ENGLISH
 *
 *  \brief Enter the editing portal through draft data recovery
 *  \param draftId Current draft id
 *  \param config Configuration item
 *  \else
 *
 *  \brief 通过草稿数据恢复，进入编辑入口
 *  \param draftId 当前草稿id
 *  \param config 配置项
 *  \endif
 */
reeditDraft(draftId: string, config?: NvVideoConfig): Promise<Map<string, any>>;
```

## Module settings

The short video module setting class **NvVideoConfig** includes function module settings and UI customization. For details, see: [Short video function module settings](../../nv_short_video_ios_doc/doc_en/html/functionConfiguration_en.html)、[Short video UI module settings](../../nv_short_video_ios_doc/doc_en/html/UIConfiguration_en.html)

<!-- BEGIN MEISHE_AGENT_IMAGE_INDEX -->
## Agent Image Index

| Image | Size | Exists | Inferred use |
| --- | --- | --- | --- |
| `../assets/image.png` | `491x303` | `true` | step screenshot; inspect near the preceding heading before editing |
| `../assets/android_compile_1.png` | `1675x283` | `true` | Android build issue and resolution reference |
| `../assets/android_compile_1_resolve.png` | `1262x688` | `true` | Android build issue and resolution reference |
| `../assets/image_lic.png` | `973x311` | `true` | license file placement or authorization UI reference |
| `../assets/image_lic_android.png` | `1662x329` | `true` | license file placement or authorization UI reference |
<!-- END MEISHE_AGENT_IMAGE_INDEX -->
