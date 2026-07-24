# Android Source Config Summary

This file summarizes integration-relevant facts extracted from `ShortVideo/android/ShortVideo`. It is not a copy of the full demo source.

## Build Configuration

- Source config: `ShortVideo/android/ShortVideo/config.gradle`.
- Observed SDK versions: `compileSdkVersion 34`, `buildToolsVersion 34.0.0`, `minSdkVersion 17`, `targetSdkVersion 35`.
- App version in demo: `versionName 1.5.2`, `versionCode 30`.
- Runtime dependencies used by the demo include AndroidX appcompat/recycler/constraint/multidex, Material, Gson, OkHttp, Room, Glide, webpdecoder, SmartRefreshLayout, Media3 ExoPlayer, PermissionX, BRVAH, utilcode/utilcodex, and EventBus. For AndroidX-only targets, integrate with `com.blankj:utilcodex:1.31.1`.
- Annotation processors in the demo include Room compiler and Glide compiler.

## Application Initialization

- Source: `ShortVideo/android/ShortVideo/app/src/main/java/com/meishe/example/App.java`.
- Initialization order: `NvModuleManager.get().init(this)`, then `initSdk("assets:/meishesdk.lic")`, then `initModel()`.
- License behavior from docs: `meishesdk.lic` is optional for running; without it, output shows a MEISHE watermark. Do not create a fake license file.

## Main Entry And Configurable Parameters

- Source: `ShortVideo/android/ShortVideo/app/src/main/java/com/meishe/example/MainActivity.java`.
- Default config path is `assets:/config/config_example.json`; external override path is `Config/config_example.json`.
- The source config is useful for parameter discovery but references demo-only image resources in `customTheme`. Do not copy it into an empty target app unless those resources are also copied.
- Integration entry calls include `downloadPrefabricatedMaterial`, `openCapture`, `openEdit`, `startDualCapture`, and `openDraftActivity`.
- Official `MainActivity` calls `downloadPrefabricatedMaterial` on startup and passes a non-null `OnAssetsRequestListener` to material download, capture, edit, and dual capture. Generated demo code should follow that pattern.
- Official `MainActivity` registers `NvModuleManagerCallback.publishWithInfo(...)` and opens the SDK publish activity. Generated helper code must register the same callback shape, but route to the generated `MeisheShortVideoPublishActivity` so "Next" inside SDK pages uses the demo UI style instead of a light/default publish page.
- The capture `template` bottom menu opens the template/AutoCut flow. Generated demos explicitly enable both AutoCut flags and retain `capture_bottom_menu_template`; cloud template or server failures must be reported and retried without hiding the entry. Customer deployments still require the contracted AutoCut service and package allowlist.
- Common config objects seen in source: `NvCaptureConfig`, `NvCompileConfig`, `NvVideoConfig`, `NvEditConfig`, `NvWatermarkConfig`, and theme/menu configuration.
- Modifiable examples include capture mode/menu, capture duration range, edit menu items, compile encoder and FPS, watermark image/size/position, cover watermark, draft entry, and publish callback routing.

## Android Manifest Requirements

- Source: `ShortVideo/android/ShortVideo/app/src/main/AndroidManifest.xml`.
- Permissions include camera, record audio, internet/network, vibrate/wake lock, Wi-Fi/network state, location, Android 13 media permissions, and legacy storage permissions with `maxSdkVersion=32`.
- The demo uses `android:requestLegacyExternalStorage="true"` and `android:networkSecurityConfig="@xml/network_security_config"`.
