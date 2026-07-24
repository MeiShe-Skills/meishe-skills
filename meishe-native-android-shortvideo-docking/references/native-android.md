# Native Android AAR Integration

Use the script for implementation. This reference records the intended behavior and source-derived API anchors.

Runtime failures use only `references/native-android-troubleshooting.md`.

生成或回答功能配置时只读取 `references/native-android-feature-configuration.md`。用户手动入口是生成包名下的 `meishe/MeisheFeatureConfig.java`；不得套用其他路线配置。

Gradle Sync 和 Debug 构建属于依赖安装边界。接入脚本只把 Wrapper 命令或 Android Studio Sync/Build 方法写入报告，必须先按 `references/dependency-installation.md` 让用户选择 `用户执行` 或 `自动执行`。

## Inputs

- Required: `NvShortVideoCore.aar`
- Optional: `meishesdk.lic`
- Optional: target package name override
- Optional: `--demo-launcher` for a disposable generated Demo project; this replaces only the manifest launcher role, not the user's source code.

Automatic AAR discovery is limited to the target project folder passed as `--target-root`. Do not scan parent folders, sibling folders, downloads, home directories, other drives, or the global filesystem. If the AAR is missing from the current project, read `aar-acquisition.md` and stop before editing files. Ask the user to place `NvShortVideoCore.aar` at the target app module `app/libs/NvShortVideoCore.aar`, or to provide the exact file with `--aar-path`. Native Android is the only supported platform in this skill that uses direct AAR integration.

Self-contained rule: `--aar-path` is only a source input. Always copy `NvShortVideoCore.aar` into the target app module `libs/NvShortVideoCore.aar` and make Gradle consume the module-local copy. After integration, check Gradle/config files for the provided external AAR path or common download directories and report a failure if any remain.

When asking for a missing AAR, always include the full source route and the exact package-internal path: open `https://www.meishesdk.com/developers`, go to `开发者中心 -> 产品及DEMO下载 -> 移动端 -> 短视频Demo`, download `iOS&Android vX.x.x`, then extract `native/android/ShortVideo/app/libs/NvShortVideoCore.aar`. The user can either put that file at `<target>/app/libs/NvShortVideoCore.aar` or pass its exact source path with `--aar-path`; the script will copy it into the project-local app module before writing Gradle dependencies.

Before editing a new native Android app, guide the user to create the app in Android Studio with the documented settings:

If the user has not created a native Android project yet, stop integration and ask them to create it in Android Studio first. Use these parameters:

- New Project path: `New Project -> Phone and Tablet -> Empty Activity`
- Name: user-chosen app name, for example `DuanshipinDemoAndroid`
- Package name: user-chosen final Android package, for example `com.example.duanshipin.demo`; reuse this value when applying for Meishe license/appid
- Save location: the target project directory the user wants Codex to integrate
- Minimum SDK: `API 24 ("Nougat"; Android 7.0)`
- Build configuration language: `Groovy DSL (build.gradle)`

After Android Studio creates the project, ask the user to place `NvShortVideoCore.aar` at `<target>/app/libs/NvShortVideoCore.aar` or provide the exact file with `--aar-path`.

Official native demo anchors:

- AAR location after extraction: `native/android/ShortVideo/app/libs/NvShortVideoCore.aar`.
- Demo app package: `com.meishe.duanshipindemo`.
- Demo build uses `compileSdkVersion 34`, `targetSdkVersion 35`, `abiFilters "armeabi-v7a", "arm64-v8a"`, `multiDexEnabled true`, and `jniLibs.useLegacyPackaging true`.
- The official Demo historically forced AndroidX Core `1.8.0`; do not copy that constraint blindly into a modern host. Parse the host `compileSdk`, preserve compatible host dependency resolution, and only apply the route's verified compatibility versions. For the verified Android Studio template using compile SDK `36.1`, align Core/KTX to `1.16.0`, Lifecycle Runtime KTX to `2.9.4`, and Activity Compose to `1.8.2`.
- For AndroidX targets, use `com.blankj:utilcodex:1.31.1`. The official demo's older `com.blankj:utilcode:1.30.6` can crash in AndroidX-only projects.

## Required Changes

1. Copy `NvShortVideoCore.aar` to `<app-module>/libs/NvShortVideoCore.aar`.
2. Add `implementation fileTree(dir: 'libs', include: ['*.aar'])`. Do not add app-level `flatDir` when the target uses `RepositoriesMode.FAIL_ON_PROJECT_REPOS`.
3. Add Aliyun/JitPack repositories in `settings.gradle` / `settings.gradle.kts` dependency-resolution repositories so PermissionX, SmartRefresh, utilcodex, and BRVAH can resolve.
4. Enable `android.useAndroidX=true` and `android.enableJetifier=true` in root `gradle.properties`.
5. Add runtime dependencies used by the ShortVideo AAR: AppCompat, Material, RecyclerView, ConstraintLayout, Gson, OkHttp, Glide, PermissionX, SmartRefresh, Room, Media3 ExoPlayer, EventBus, `com.blankj:utilcodex:1.31.1`, BRVAH, WebP decoder, and MultiDex.
6. Add Room and Glide annotation processors.
7. Exclude transitive `com.android.support` dependencies globally to avoid AndroidX duplicate classes.
8. Before writing the dependency block, detect the app module's `compileSdk`. Require at least 34. Never unconditionally force AndroidX Core `1.8.0`: modern `ComponentActivity` implements `PictureInPictureProvider`, which that old Core artifact does not provide. On the verified compile SDK `36.1` Compose template, apply the verified Core/Lifecycle/Activity versions above; for unknown version-catalog aliases, stop instead of guessing.
9. Match the official native Demo packaging boundary: restrict packaged native libraries to `armeabi-v7a` and `arm64-v8a`, and set `jniLibs.useLegacyPackaging` to `true`.
10. Add permissions for camera, audio, network, storage, and Android 13 media access.
11. If a real `meishesdk.lic` is supplied, add it under app assets. If not supplied, do not create a placeholder; run unlicensed with the MEISHE watermark and report license acquisition steps.
12. For a customer material server, use the generated helper/config entry together with `references/customer-server.md`. Require the real host, endpoint contract, credentials, package allowlist, test environment, and expected materials before runtime verification; static placeholders are not proof of success.

Signing keystore, final package name, customer-server credentials, and formal license are user-specific. Temporary first-run values must be identified in `meishe_docking_report.md` and replaced before production handoff.
When `--package-name` is supplied, align Gradle `namespace`/`applicationId`, Java/Kotlin package declarations and imports, and source paths together. For official Demo-service validation use `com.meishe.duanshipindemo`; a near-match or partially renamed package is not valid. Use `--demo-launcher` only for a newly created disposable Demo so the generated home is the single launcher; preserve an existing product launcher by default.
13. Generate a minimal `assets/config/config_example.json` for SDK bootstrap and a user-editable `meishe/MeisheFeatureConfig.java` as the final feature source. Do not copy the full official config unless the target also copies every demo image/resource referenced by `customTheme`. Keep compile resolution at 1080p by default; 4K must not be generated without device validation. Preserve the Java feature file on later runs.
14. Copy `assets/demo-ui/meishe_home_banner.jpg` and `assets/demo-ui/icons/*.png` to `res/drawable-nodpi/`.
15. Generate `MeisheShortVideoDocking` helper code.
16. Generate and register `MeisheShortVideoDemoActivity` following `references/demo-ui-style.md`: dark home, fixed banner, custom icons for Chinese rows `拍摄` / `合拍` / `编辑` / `草稿`, no `拍动 v2.0.0` / `用户协议` / `隐私协议` footer. Home must fit within one viewport with visible bottom whitespace, screen-height based banner/spacing clamps, compact title, and 46-52dp action rows. Home entry must automatically call material download, show loading until success/failure, disable actions while loading, and expose retry on failure. Material download, capture, edit, and dual capture must pass a non-null `OnAssetsRequestListener`.
17. Register `NvModuleManager.get().setModuleManagerCallback(...)` and route `publishWithInfo(...)` to the generated `.meishe.MeisheShortVideoPublishActivity` with the official intent extras. Without this callback, capture/edit/template "Next" can appear to do nothing. The generated next-step page must follow `references/demo-ui-style.md`: dark `作品发布` screen, compact project row with thumbnail/play overlay, `草稿-MMDD` fallback title, save-draft/export/progress controls, and no light English form UI.
18. In `MeisheFeatureConfig.java`, explicitly enable both AutoCut flags and keep image/video/smart/template in the ordered bottom menu. Feature removal must delete the enum from its ordered List so the SDK reflows the UI; do not hide controls and leave fixed blank space. Do not hide AutoCut merely because online material preparation can fail.
19. AutoCut acceptance follows the standard edit route: select media or enter from the template-related capture entry, generate the AutoCut result, continue in the standard editor, then tap Next to open the generated publish page. The required result supports both save draft and export video; do not treat the separate direct template-compile route as this acceptance flow.

## Runtime API Anchors

Use `NvModuleManager`:

- `NvModuleManager.get().init(app)`
- `NvModuleManager.get().initSdk("assets:/meishesdk.lic")`
- `NvModuleManager.get().initModel()`
- `NvModuleManager.get().initConfig("assets:/config/config_example.json")`
- `NvModuleManager.get().downloadPrefabricatedMaterial(activity, listener)`
- `NvModuleManager.get().openCapture(activity, config, musicInfo, listener)`
- `NvModuleManager.get().openEdit(activity, config, listener)`
- `NvModuleManager.get().startDualCapture(activity, config, listener)`
- `NvModuleManager.get().openDraftActivity(activity, config, "com.meishe.photo.captureAndEdit.drafts.DraftsActivity")`
- `NvModuleManager.get().setModuleManagerCallback(callback)` where the official demo opens `ModuleConstants.PUBLISH_ACTIVITY`; generated integrations route the same callback to `.meishe.MeisheShortVideoPublishActivity` so the next-step UI matches `references/demo-ui-style.md`.

Generated code should wrap these calls so app code can call a single helper instead of hand-writing integration.

The Android AAR exposes only a success/fail callback for prefabricated material download; it does not expose percentage progress. The demo entry should show "running", "success", and "failed" states and should not pass `null` to `downloadPrefabricatedMaterial`, because missing permissions can call the listener immediately.

For customer service, AutoCut must be provisioned for the final package name. Native Android uses the SDK-supported configuration surface of the selected AAR; do not copy RN, Flutter, or native iOS internal URL assignment code into the app wrapper.

## Completion Report

Always report:

- AAR path used.
- License file status.
- Server placeholder status.
- Files modified.
- Build/check command attempted or skipped.
