# Native Android AAR Acquisition

Use this only for native Android. Flutter and React Native must use their official local plugin packages instead of direct AAR integration.

If native Android is missing `NvShortVideoCore.aar`, stop before editing files and tell the user:

1. Open `https://www.meishesdk.com/developers`.
2. Go to `开发者中心 -> 产品及DEMO下载 -> 移动端 -> 短视频Demo`.
3. Click `iOS&Android vX.x.x` to download the native Demo package and docs.
4. Extract the package.
5. Get `NvShortVideoCore.aar` from `native/android/ShortVideo/app/libs/NvShortVideoCore.aar`.
6. Put it in the target Android app module at `<target>/app/libs/NvShortVideoCore.aar`, or pass its exact file path with `--aar-path <path-to-NvShortVideoCore.aar>`.

Automatic AAR discovery only checks the current target project folder passed as `--target-root`. If `NvShortVideoCore.aar` is outside that folder, do not search for it globally; ask the user to move it into `app/libs` or provide the exact `--aar-path`.

If the user has no native Android project yet, stop before editing files and ask them to create one in Android Studio:

- New Project path: `New Project -> Phone and Tablet -> Empty Activity`
- Name: user-chosen app name, for example `DuanshipinDemoAndroid`
- Package name: user-chosen final Android package, for example `com.example.duanshipin.demo`; reuse this value when applying for Meishe license/appid
- Save location: the target project directory
- Minimum SDK: `API 24 ("Nougat"; Android 7.0)`
- Build configuration language: `Groovy DSL (build.gradle)`

After the project exists, put `NvShortVideoCore.aar` in the target app module at `<target>/app/libs/NvShortVideoCore.aar`, or pass its exact path with `--aar-path`.

Expected filename: `NvShortVideoCore.aar`.
