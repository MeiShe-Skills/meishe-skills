<!-- MEISHE_AGENT_DOC_ENHANCED: v1 -->
# Meishe short video module access guide

<!-- BEGIN MEISHE_AGENT_QUICK_INDEX -->
> **Agent Quick Index**
> - **Doc ID**: `native-quickstart-doc-en-quickstart-android-en`
> - **Track**: `native`
> - **Platforms**: `android`
> - **Tags**: `quickstart, integration, native-android, aar, gradle, manifest, permission, license, server-config`
> - **Image count**: `2`
> - **Usage**: Locate sections by tags first, then read adjacent steps, config tables, and image notes.
<!-- END MEISHE_AGENT_QUICK_INDEX -->




## Development environment requirements

* Android studio 2023.12+。
* JDK 11， TargetSdkVersion 34

> ⚠️ **Note:**  This feature must be run on a physical device, as it is currently not supported on the simulator.
## Upgrade short video notes
### Version 1.5.2 Updates:
* The AutoCut video creation feature has been completely upgraded. For detailed code examples, please refer to the demo. You can contact our server-side development team in the support group for assistance in upgrading the server-side interface. Therefore, to use the AutoCut video creation feature, you must contact our server-side team for upgrade assistance. Please feel free to contact us with any questions.
### Version 1.5.1 Updates:
* Fixed some known issues
### Version 1.5.0 Updates:
* **This release involves significant updates; therefore, regression testing is absolutely essential prior to deployment—particularly regarding changes to configuration settings.**
### 1.4.0 Version upgrade:
* The Android version of the AutoCut video creation tool has not been upgraded, so the Android interface remains unchanged and requires no modifications. This is different from the iOS version. If you need to integrate with the AutoCut video creation tool, please contact our relevant colleagues in the group.
### 1.3.0 Version upgrade:
* **1.Editor UI Update:**
Adjusted the “Next” and “Save” buttons to be positioned in the bottom menu.
* **2.Added Meishe SDK Export Configuration Options: New parameters supported for export configuration. For details, see: [Meishe SDK CompileConfig Documentation](https://www.meishesdk.com/android/doc_en/html/content/classcom_1_1meicam_1_1sdk_1_1NvsStreamingContext.html#COMPILE_VIDEO_RESOLUTION_GRADE)**
```java
private void testCompileConfig() {
        mVideoConfig = NvModuleManager.get().getConfig();
        if (null == mVideoConfig) {
            mVideoConfig = new NvVideoConfig();
        }
        NvCompileConfig compileConfig = mVideoConfig.getCompileConfig();
        Map<String, Object> compileMap = new HashMap<>();
        compileMap.put(VIDEO_ENCODEC_NAME, "hevc");
        compileConfig.setConfigure(compileMap);
//        compileConfig.setFps(30);
        mVideoConfig.setCompileConfig(compileConfig);
    }
```
* **3.Added Support for Multiple Image Exports and Extended Publish Data Retrieval:**
Supports retrieving video path, image paths, and musicInfo data.
```java
    NvPublishInfo publishInfo = NvModuleManager.get().getPublishInfo();
        // 单张图片路径  only for image path
        String coverPath = publishInfo.getCoverPath();
        // 音乐信息  music info
        NvMusicInfo musicInfo = publishInfo.getMusicInfo();
        // 多张图片路径集合 multiple image path
        List<String> imagesPath = publishInfo.getImagesPath();
        // 视频路径 video path
        String videoPath = publishInfo.getVideoPath();
```
* **4.Added New API to Check Multi-Image Export Support.**
```java
    boolean onlyHaveMultipleImage = NvModuleManager.get().isOnlyHaveMultipleImage();
```
* **5.Added Capture Configuration Options:**
Allows setting default capture mode among Photo, Video, and Quick Shot.
```java
    private void testCaptureConfig() {
        mVideoConfig = NvModuleManager.get().getConfig();
        if (null == mVideoConfig) {
            mVideoConfig = new NvVideoConfig();
        }
        NvCaptureConfig captureConfig = mVideoConfig.getCaptureConfig();
        // NvCaptureBottomMenuItem.image
        // NvCaptureBottomMenuItem.video
        // NvCaptureBottomMenuItem.smart
        captureConfig.setDefaultBottomMenuSelectItem(NvCaptureConfig.NvCaptureBottomMenuItem.video);
        mVideoConfig.setCaptureConfig(captureConfig);
    }
``` 
* **6.Added Support for Shadow Configuration of Text in Capture and Edit Menus.**
```java
    private void testShadowLayer() {
        mVideoConfig = NvModuleManager.get().getConfig();
        if (null == mVideoConfig) {
            mVideoConfig = new NvVideoConfig();
        }
        // 设置阴影颜色 setting shadow color
        mVideoConfig.setShadowColor("#FC3E5A");
        // 设置阴影偏移量 setting shadow offset
        NvShadowOffsetConfig nvShadowOffsetConfig = new NvShadowOffsetConfig(0, 1);
        mVideoConfig.setShadowOffset(nvShadowOffsetConfig);
    }
```
* 7.Fix:
Resolved a UI disorder issue that occurred in specific environments when opening the bottom filter popup during capture.
* 8.Optimization:
Added validation to check whether data in the photo album actually exists. If not, a prompt will appear indicating that the video or photo does not exist.
* 9.Optimization:
When dragging the bottom progress bar in the editor, all operation menus are temporarily hidden for a cleaner user experience.
* 10.Android Adaptation for 16k Support.
* **11.Api Update： Unified the export data retrieval interface in **NvModuleManager.java**.**
```java
    // public interface OnCompileImageListener {
    //     void onCompileFinished(boolean isSuccess, String path);
    // }
   public interface OnCompileImageListener {
        void onCompileFinished(boolean isSuccess);
    }
    // The path is now uniformly retrieved from NvPublishInfo
    NvModuleManager.get().getPublishInfo();
```

### 1.2.9 Version upgrade:
* **Version 1.2.9 adds the function of exporting videos and pictures with watermarks. If the user configures a watermark, the video and cover will be watermarked when exported.**
### 1.2.8 Version upgrade：
In version 1.2.7, you need to download resources before entering shooting, editing, and co-shooting. The new version will not block the entry into shooting, editing, and co-shooting, and will silently download in the background when entering. It also provides an interface for users to actively call it. If the user does not actively call shortvideo, it will be called by default.
```java
public void downloadPrefabricatedMaterial(Activity activity, OnAssetsRequestListener onAssetsRequestListener)
```
### 1.2.7 Version upgrade：
* **Directly Replace the AAR Library in the Native Project**
In version 1.2.7, a new callback was added to the existing interfaces when entering the shooting, duet, and editing features. This callback is used to monitor the completion status of the built-in resource download.
```NvModuleManager.java
//Shooting entrance
- public void openCapture(Activity activity, NvVideoConfig videoConfig, NvMusicInfo musicInfo, OnAssetsRequestListener onAssetsRequestListener);
//PIP entrance
- public void startDualCapture(Activity activity, NvVideoConfig videoConfig, OnAssetsRequestListener onAssetsRequestListener);
//Editing entrance
- public void openEdit(Activity activity, NvVideoConfig videoConfig, OnAssetsRequestListener onAssetsRequestListener);
```
## Support media formats

For details, see: [Meishes sdk product overview](https://www.meishesdk.com/android/doc_en/html/content/Introduction_8md.html)

# Project construction

1. New android project

   Run File—new—New Project， After making the following settings, click finish.

   ![image-20240516153236811](../assets/android_image/image-20240516153236811.png)
> **Image parse:** `path=../assets/android_image/image-20240516153236811.png`, `size=904x655`, use: Native Android project setup or Android resource location.

2. **Copy the aar package to the libs directory**

   Place the NvShortVideoCore. aar package in the libs directory

3. Place the **meishesdk.lic** in the assets directory

   ![image-20240516185729759](../assets/android_image/image-20240516185729759.png)
> **Image parse:** `path=../assets/android_image/image-20240516185729759.png`, `size=455x607`, use: Native Android project setup or Android resource location.

   > The meisesdk.lic is a license applied for through the official website of Meishi Photography, which is bound to the appid.
   >
   > After registering as a user on [Meishe‘s official website](https://en.meishesdk.com/), create an application and configure the App package name. After a Meishe business colleague activates the authorization, you can download the authorization file in the application information.
   >
   > The SDK authorization is bound to the Bundle Idenfity of the App. When it is not authorized, all functions of the SDK can be used without checking the authorization, and the drawn picture will have the MEISHE watermark.



4. **Create Dependencies**

   ```xml
   implementation rootProject.ext.dependencies.extMutilDex
   implementation rootProject.ext.dependencies.extAndroidXDesign
   implementation rootProject.ext.dependencies.extAppcompat
   implementation rootProject.ext.dependencies.extAppcompatRecycler
   implementation rootProject.ext.dependencies.extConstraintLayout
   //Gson
   implementation rootProject.ext.dependencies.extGoogleGson
   implementation rootProject.ext.dependencies.extWebpdecoder
   //Utils
   implementation rootProject.ext.dependencies.utils
   //BRVAH
   implementation rootProject.ext.dependencies.brvah
   // glide 4.6.1~4.9.0 (exclude broken version 4.6.0, 4.7.0)
   implementation rootProject.ext.dependencies.extBumptechGlide
   annotationProcessor rootProject.ext.dependencies.extGlideAnnotation
   //permission
   implementation rootProject.ext.dependencies.permissionx
   //Smart refresh
   implementation rootProject.ext.dependencies.smartRefreshLayout
   implementation rootProject.ext.dependencies.smartRefreshHeader
   //room
   implementation rootProject.ext.dependencies.room
   annotationProcessor rootProject.ext.dependencies.roomComplier
   //okhttp
   implementation rootProject.ext.dependencies.extOkhttp
   //exoplayer
   implementation rootProject.ext.dependencies.exoplayer
   //eventBus
   implementation rootProject.ext.dependencies.eventBus
   ```

   > Dependencies can be found in config.gradle.

## Permission description

<!-- BEGIN MEISHE_AGENT_SECTION_HINT -->
> **Agent section hint:** tags `permission`. Check steps, config values, paths, and permission requirements before editing.
<!-- END MEISHE_AGENT_SECTION_HINT -->


The app requires the following permissions, otherwise it will not be able to use the short video module.

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

After registering as a user on [Meishe‘s official website](https://en.meishesdk.com/), create an application and configure the App package name. After a Meishe business colleague activates the authorization, you can download the authorization file in the application information.

Need to add the lic file to the asset directory of the App project.

```java
Run NvModuleManager.initSdk("assets:/meishesdk.lic") method.
```



> The SDK authorization is bound to the Bundle Idenfity of the App. When it is not authorized, all functions of the SDK can be used without checking the authorization, and the drawn picture will have the MEISHE watermark.

## Network interface configuration

<!-- BEGIN MEISHE_AGENT_SECTION_HINT -->
> **Agent section hint:** tags `server-config`. Check steps, config values, paths, and permission requirements before editing.
<!-- END MEISHE_AGENT_SECTION_HINT -->


The filters, stickers, music and other files used in the short video module are all obtained through the network interface. Mainly configured through setting up the **host**.

The method is defined in the NvsServerClient.java file

```javascript
/*! \if ENGLISH
     *
     *  \brief Init net host
     *  \param application The application
     *  \param host the host
     *  \param complatetionHandler
     *  \else
     *
     *  \brief 初始化网路
     *  \param application app
     *  \param host host
     *  \endif
     */
    public void initConfig(Application application, String host)
```

In EngineNetApi. Java, various functional interfaces are defined, and the following variables can be modified to configure the functional interfaces.

```javascript
/**
     * 根据分类获取素材列表
     * Get a list of materials by category
     */
    public static String NV_ASSET_REQUEST_URL = "materialcenter/mall/custom/listAllAssemblyMaterial";
    /**
     * 根据素材类型获取素材分类列表
     * Gets a classified list of materials based on their type
     */
    public static String NV_ASSET_CATEGORY_URL = "materialcenter/appSdkApi/listTypeAndCategory";
    /**
     * 获取字体列表
     * Get font list
     * materialcenter/appSdkApi/material/listAll
     */
    public static String NV_ASSET_FONT_URL = "materialcenter/listFont";
    /**
     * 获取音乐列表
     * Get music list
     */
    public static String NV_ASSET_MUSICIANS_URL = "materialcenter/appSdkApi/listMusic";
    /**
     * 把素材的id作为参数传入，获取到素材下载的链接
     * Pass in the id of the material as a parameter to get the link to the material download
     */
    public static String NV_ASSET_DOWNLOAD_URL = "materialcenter/mall/custom/materialInteraction";
    /**
     * 获取预置素材
     * Get the Prefabricated material for the project
     */
    public static String NV_ASSET_PREFABRICATED_URL = "materialcenter/beautyAssets/latest";
    /**
     * 一键成片
     * AutoCut
     */
    public static String NV_ASSET_AUTOCUT_URL = "materialcenter/recommend/listTemplate";
    /**
     * 获取模版的标签分类
     * Gets the label classification of the template
     * materialcenter/appSdkApi/listTemplateTag
     */
    public static String NV_ASSET_TAG_URL = "materialcenter/listTemplateTag";
    /** 公共参数
      *Default parameters
      */
    NvsServerClient.MallInfo.CLIENT_ID = NV_ClientId;
    NvsServerClient.MallInfo.CLIENT_SECRET = NV_ClientSecret;
    NvsServerClient.MallInfo.ASSEMBLY_ID = NV_AssemblyId;
```



## Preset material

<!-- BEGIN MEISHE_AGENT_SECTION_HINT -->
> **Agent section hint:** tags `prefabricated-material`. Check steps, config values, paths, and permission requirements before editing.
<!-- END MEISHE_AGENT_SECTION_HINT -->


The material packages that the short video module relies on can be selected as needed. For details of preset materials, see: [Short video module preset materials](./PrefabricatedMaterial_en.html)

## Main methods of short video module

The module main methods are defined in the **NvModuleManager**.java file.

###  Initialize SDK

``` java
 /** \if ENGLISH
     *
     *  \brief InitSdk
     *  @param licPath the licPath
     *  \else
     *
     *  \brief 美摄SDK授权
     *  @param licPath 授权文件
     *  \endif
     */
    public void initSdk(String licPath)
```

### Video recording

```javascript
/** \if ENGLISH
     *
     *  \brief Open capture
     *  @param activity the activity
     *  @param videoConfig the config information
     *  @param musicInfo the config music information
     *  \else
     *
     *  \brief 打开拍摄
     *  @param activity 授权文件
     *  @param videoConfig 配置信息
     *  @param musicInfo 音乐信息
     *  \endif
     */
    public void openCapture(Activity activity, NvVideoConfig videoConfig, NvMusicInfo musicInfo)
```

### Picture in Picture

```javascript
/** \if ENGLISH
     *
     *  \brief Open dual capture.Open the album, and jump to the dual capture activity.
     *  @param activity the activity
     *  @param videoConfig the config information
     *  \else
     *
     *  \brief 打开合拍 即跳转相册，进入合拍页面
     *  @param activity activity
     *  @param videoConfig 配置信息
     *  \endif
     */
    public void openDualCapture(Activity activity, NvVideoConfig videoConfig)

 /** \if ENGLISH
     *
     *  \brief Open dual capture.Open the album, and jump to the dual capture activity.
     *  @param activity the activity.
     * If you need to configure the export path, you need to call this method
     *  @param videoConfig the config information
     *  @param videoPath The video path prepared for co production must be a local path.
     *  \else
     *
     *  \brief 打开合 拍即跳转相册，进入合拍页面
     *  如果需要配置导出路径，需要调用此方法
     *  @param activity 授权文件
     *  @param videoConfig 配置信息
     *  @param videoPath 准备合拍的视频路径，必须是本地路径
     *  \endif
     */
    public void openDualCapture(Activity activity, NvVideoConfig videoConfig, String videoPath)
```



### Video editing

<!-- BEGIN MEISHE_AGENT_SECTION_HINT -->
> **Agent section hint:** tags `function-config`. Check steps, config values, paths, and permission requirements before editing.
<!-- END MEISHE_AGENT_SECTION_HINT -->


```javascript
/** \if ENGLISH
     *
     *  \brief Open edit
     *  @param activity the activity
     *  @param videoConfig the config information
     *  \else
     *
     *  \brief 打开编辑
     *  @param activity activity
     *  @param videoConfig 配置信息
     *  \endif
     */
    public void openEdit(Activity activity, NvVideoConfig videoConfig)
```



### Video editing complete callback

<!-- BEGIN MEISHE_AGENT_SECTION_HINT -->
> **Agent section hint:** tags `function-config`. Check steps, config values, paths, and permission requirements before editing.
<!-- END MEISHE_AGENT_SECTION_HINT -->


```javascript
public interface NvModuleManagerCallback {

    /** \if ENGLISH
     *
     *  \brief Publish with info callback
     *  @param activity The activity
     *  @param needSaveDraft Need save draft or not.
     *  @param needSaveCover Need save cover or not.
     *  @param needSaveVideo Need save video or not.
     *  \else
     *
     *  \brief 跳转发布页面回调
     *  @param activity The activity
     *  @param needSaveDraft 是否要保存草稿
     *  @param needSaveCover 是否要保存封面
     *  @param needSaveVideo 是否要保存视频
     *  @param videoPath 视频地址
     *  \endif
     */
    void publishWithInfo(Activity activity, boolean needSaveDraft, boolean needSaveCover, boolean needSaveVideo, String videoPath)
```

### Select cover

```javascript
 /** if ENGLISH
     *
     *  \brief EditCover
     *  @param activity the from activity
     *  @param overPoint Last editing time for cover page
     *  @param requestCode The request code
     *  \else
     *
     *  \brief 编辑封面
     *  @param  activity 编辑封面的发起页面
     *  @param  overPoint 上一次编辑封面的时间点
     *  @param  requestCode 请求code
     *  \endif
     */
    public static void editCover(Activity activity, long overPoint, int requestCode)

    //Cover editing will not generate a Bitmap. The selection time of the cover will be returned in the onActivityResult method callback, with the key being "coverPoint".
    public static final String INTENT_KEY_COVER_POINT = "coverPoint";

   //Bitmap can be obtained through the methods in CaptureAndEditUtil.java.

    /** if ENGLISH
     *
     *  \brief Get image from timeline
     *  @param overPoint The cover point
     *  \else
     *
     *  \brief 获取时间线上某一帧图片的bitmap
     *  @param  overPoint 选择封面的时间点
     *  \endif
     */
    public static Bitmap getImageFromTime(long overPoint)

```

>If you need to save the cover, see the Save Cover interface.

### Save draft

<!-- BEGIN MEISHE_AGENT_SECTION_HINT -->
> **Agent section hint:** tags `function-config`. Check steps, config values, paths, and permission requirements before editing.
<!-- END MEISHE_AGENT_SECTION_HINT -->


```javascript
/** \if ENGLISH
     *
     *  \brief Save draft
     *  @param videoDesc The draft description
     *  @param coverPoint The cover point
     *  @param callBack The draft save callback
     *  \else
     *
     *  \brief 保存草稿
     *  @param videoDesc 草稿描述
     *  @param coverPoint 草稿封面
     *  @param callBack 保存草稿回调
     *  \endif
     */
    public void saveDraft(String videoDesc, long coverPoint, DraftManager.DraftSaveCallBack callBack)
```

### Synthetic video

```javascript
/** if ENGLISH
     *
     *  \brief Save video to album
     *  @param callback The on compile video listener
     *  \else
     *
     *  \brief 保存视频到相册
     *  @param  callback 保存视频回调
     *  \endif
     */
    public static void saveVideoToAlbum(OnCompileVideoListener callback)
```

### Video synthesis callback

```javascript
public interface OnCompileVideoListener {
        /**! \if ENGLISH
         *
         *  \brief compile video progress callback
         *  \@param timeline  the current timeline
         *  \@param progress  the current progress
         *  \else
         *
         *  \brief 合成视频进度回调
         *  \@param timeline 当前的时间线
         *  \@param progress 当前的进度
         *  \endif
         */
        void compileProgress(NvsTimeline timeline,int progress);

        /**! \if ENGLISH
         *
         *  \brief compile video finished callback
         *  \@param timeline  the current timeline
         *  \else
         *
         *  \brief 合成视频完成回调
         *  \@param timeline 当前的时间线
         *  \endif
         */
        void compileFinished(NvsTimeline timeline);

        /**! \if ENGLISH
         *
         *  \brief compile video failed callback
         *  \@param timeline  the current timeline
         *  \else
         *
         *  \brief 合成视频失败回调
         *  \@param timeline 当前的时间线
         *  \endif
         */
        void compileFailed(NvsTimeline timeline);


         /**! \if ENGLISH
         *
         *  \brief compile video completed callback
         *  \@param timeline  the current timeline
         *  \@param compileVideoPath  the compile video path
         *  \@param isCanceled  The compile is canceled or not
         *  \else
         *
         *  \brief 合成视频完成回调
         *  \@param timeline 当前的时间线
         *  \@param compileVideoPath 保存路径
         *  \@param isCanceled 合成是否被取消
         *  \endif
         */
        void compileCompleted(NvsTimeline nvsTimeline, String compileVideoPath, boolean isCanceled);

        /**! \if ENGLISH
         *
         *  \brief compile video cancel callback
         *  \else
         *
         *  \brief 合成视频被取消回调
         *  \endif
         */
        void compileVideoCancel();


        /**! \if ENGLISH
         *
         *  \brief compile video completed callback
         *  \@param isHardwareEncoder Is hardware encoder or not
         *  \@param errorType The error type
         *  \@param stringInfo The error string info
         *  \@param flags the  flags
         *  \else
         *
         *  \brief 合成视频完成回调
         *  \@param isHardwareEncoder 是否是硬件错误
         *  \@param errorType 错误类型
         *  \@param stringInfo 提示信息
         *  \@param flags the  flags
         *  \endif
         */
        void onCompileCompleted(boolean isHardwareEncoder, int errorType, String stringInfo, int flags);
    }
```

### Save cover image

```javascript
/** if ENGLISH
     *
     *  \brief Save cover
     *  @param  coverDir the cover file dir.
     *  @param  coverFileName the cover file name.If empty, it is a timestamp.
     *  @param  coverTime the coverTime
     *   @param  needSaveToAlbum Need Save To Album or not
     *   @param  callBack the on cover saved callback for update ui
     *  @return the boolean Did you successfully execute the save draft
     *  \else
     *
     *  \brief 保存封面
     *  @param  coverDir 封面文件夹路径
     *  @param  coverFileName 封面文件明显,如果为空，则是时间戳
     *  @param  coverTime 封面时间点
     *  @param  needSaveToAlbum 是否需要保存封面
     *  @param  callBack 保存草稿回调，用于更新UI
     *  @return the boolean 是否执行保存草稿成功
     *  \endif
     */
    public boolean saveCover(String coverDir, String coverFileName, long coverTime, boolean needSaveToAlbum, OnCoverSavedCallBack callBack)
```

### Exit short video module

Call it when the video publishing page exits

```javascript
/** \if ENGLISH
     *
     *  \brief Finish publish
     *  @param activity The activity
     *  @param toActivityClassName The next activity classname you want to
     *  \else
     *
     *  \brief 退出发布页
     *  @param activity 当前页面
     *  @param toActivityClassName 要去的页面的类名
     *  \endif
     */
    public void finishPublish(Activity activity, String toActivityClassName)
```



### Get draft list

<!-- BEGIN MEISHE_AGENT_SECTION_HINT -->
> **Agent section hint:** tags `function-config`. Check steps, config values, paths, and permission requirements before editing.
<!-- END MEISHE_AGENT_SECTION_HINT -->


The method is defined in DraftManager.java

```javascript
  /** \if ENGLISH
     *
     *  \brief Get all draft data
     *  @return  The draft data list
     *  \else
     *
     *  \brief 获取草稿数据
     *  @return  The draft data list
     *  \endif
     */
    public List<DraftData> getAllDraftData()
```

### Delete draft

<!-- BEGIN MEISHE_AGENT_SECTION_HINT -->
> **Agent section hint:** tags `function-config`. Check steps, config values, paths, and permission requirements before editing.
<!-- END MEISHE_AGENT_SECTION_HINT -->


The method is defined in DraftManager.java

```javascript
/** \if ENGLISH
     *
     *  \brief Delete draft
     *  @param   draftData The draft data
     *  \else
     *
     *  \brief 获取草稿数据
     *  @param  draftData The draft data
     *  \endif
     */
    public void deleteDraft(final DraftData draftData)
```

### Open draft

<!-- BEGIN MEISHE_AGENT_SECTION_HINT -->
> **Agent section hint:** tags `function-config`. Check steps, config values, paths, and permission requirements before editing.
<!-- END MEISHE_AGENT_SECTION_HINT -->


```javascript
 /** \if ENGLISH
     *
     *  \brief Open draft and jump to edit activity
     *  @param activity The activity
     *  @param draftData the draft data
     *  \else
     *
     *  \brief 打开草稿,并跳转编辑页面
     *  @param activity 当前页面
     *  @param draftData 草稿数据
     *  \endif
     */
    public void openDraftAndJumpToEdit(Activity activity, DraftData draftData)
```

## Module settings

The short video module setting class **NvVideoConfig** includes function module settings and UI customization. For details, see: [Short video function module settings](functionConfiguration_en.html)、[Short video UI module settings](UIConfiguration_en.html)

<!-- BEGIN MEISHE_AGENT_IMAGE_INDEX -->
## Agent Image Index

| Image | Size | Exists | Inferred use |
| --- | --- | --- | --- |
| `../assets/android_image/image-20240516153236811.png` | `904x655` | `true` | Native Android project setup or Android resource location |
| `../assets/android_image/image-20240516185729759.png` | `455x607` | `true` | Native Android project setup or Android resource location |
<!-- END MEISHE_AGENT_IMAGE_INDEX -->
