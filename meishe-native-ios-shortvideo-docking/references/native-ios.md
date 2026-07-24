# Native iOS Integration

Use this path when the target is a native iOS app with a `Podfile` or `*.xcodeproj`.

Runtime failures use only `references/native-ios-troubleshooting.md`.

生成或回答功能配置时只读取 `references/native-ios-feature-configuration.md`。用户手动入口是 `MeisheShortVideo/MeisheFeatureConfig.swift`；不得套用其他路线配置。

CocoaPods 安装属于依赖安装边界。接入脚本只登记项目目录和 `bundle exec pod install` 或 `pod install`，必须先按 `references/dependency-installation.md` 让用户选择 `用户执行` 或 `自动执行`。

当前任务新建原生 iOS 工程时，集成命令默认传 `--ios-bundle-identifier com.meishe.duanshipindemo`。已有工程未显式要求修改身份时，脚本保持已确认 App Target 的现有值；非官方值必须在写入前说明官方素材服务无法请求，并给出临时改为官方 Demo 身份或配置客户服务、匹配 License 与白名单两条路径。显式修改只允许作用于 App Target 的构建配置，不得改测试 Target 或 Extension。

By default, add only the SDK privacy usage descriptions and do not set global `NSAllowsArbitraryLoads`. For temporary official-Demo validation, enable it only when the target Bundle Identifier is exactly `com.meishe.duanshipindemo` and the supplied native package's own Example app plist declares the same setting. If a customer service truly requires HTTP, configure the narrowest domain-specific ATS exception and review it before release.

## Required Official Package

Ask the user for the extracted official native package path or the exact local CocoaPods package folder. The required folder inside the extracted package is `native/ios/Pods-NvShortVideoEdit`.

Self-contained rule: `--plugin-path` is only a source input. Copy the validated `Pods-NvShortVideoEdit` package into the target project as `vendor/meishe/Pods-NvShortVideoEdit` before writing `Podfile`. The Pod dependency must use a project-local relative path such as `./vendor/meishe/Pods-NvShortVideoEdit`, not the external downloaded/extracted package path.

Download route:

`https://www.meishesdk.com/developers` -> `开发者中心` -> `产品及DEMO下载` -> `移动端` -> `短视频Demo` -> `iOS App vX.x.x` or `iOS&Android vX.x.x`.

If the Pod package is missing, stop before editing files. Tell the user to download one of those native packages, extract it, and provide either the extracted root containing `native/ios/Pods-NvShortVideoEdit` or the exact `Pods-NvShortVideoEdit` folder. The script copies it into the target project at `vendor/meishe/Pods-NvShortVideoEdit` and points `Podfile` at that project-local path.

## Scripted Work

Run:

```powershell
python .\scripts\integrate_native_ios.py --target-root <ios-project-root> --plugin-path <extracted-package-root> --ios-target <xcode-target-name>
```

The script can safely:

- Locate `Pods-NvShortVideoEdit`.
- Copy `Pods-NvShortVideoEdit` into `vendor/meishe/Pods-NvShortVideoEdit`.
- Add or update `pod 'NvShortVideoEdit', :path => './vendor/meishe/Pods-NvShortVideoEdit'` in `Podfile`.
- Add `platform :ios, '12.0'` and `use_frameworks!` only when missing. Insert `NvShortVideoEdit` with `:inhibit_warnings => true`; do not add global `inhibit_all_warnings!`, do not rewrite unrelated Pods, and preserve existing sources and `post_install` blocks.
- Resolve Project, application Target, shared Scheme, and Workspace independently. When more than one application Target remains after Podfile/shared-Scheme matching, stop before writing and require `--ios-target`.
- Patch only the Xcode application Target `Info.plist` with camera, microphone, photo library, Apple Music, location, and local-network permissions. Never recursively patch plist files inside `vendor/meishe/Pods-NvShortVideoEdit`, Example apps, frameworks, or xcframeworks.
- Mirror `NSAllowsArbitraryLoads = true` only for the temporary official Demo identity when the supplied package Example plist declares it; customer identities keep global ATS disabled.
- Copy `Config.swift` and `NvHttpRequestDelegate.swift` if they exist in the package.
- Copy the shared demo UI banner and four custom function icons into `MeisheShortVideo/Assets`.
- Generate UIKit UI files under `MeisheShortVideo/` using the neutral shared visual specification in `references/demo-ui-style.md`:
  - `MeisheFeatureConfig.swift`（逐项注释、只在首次生成，后续保留手改）
  - `MeisheShortVideoStyle.swift`
  - `MeisheShortVideoHomeViewController.swift`
  - `MeisheShortVideoDraftsViewController.swift`
  - `MeisheShortVideoPublishViewController.swift`
- Copy a real `meishesdk.lic` when provided.
- Write `meishe_native_ios_handoff.md` with target membership, navigation entry, and SDK verification notes.
- Check `Podfile`, `Podfile.lock`, Gradle files if present, package files if present, and pubspec files if present for the provided external package path or common download directories. Report a failure if any remain.

Official native iOS demo anchors:

- Pod package folder: `native/ios/Pods-NvShortVideoEdit`.
- Example Podfile uses `pod 'NvShortVideoEdit', :path => '../'`.
- Runtime imports `NvShortVideoCore`.
- Use `NvModuleManager.sharedInstance().delegate = self` for publish callbacks.
- Entry methods include `downloadPrefabricatedMaterialCompletion`, `startCapture`, `startDualCapture`, `startEdit`, `NvModuleManager.projectList()`, `reeditProject`, `NvModuleManager.deleteDraft(projectId)`, `saveCurrentDraft`, `compileCurrentTimeline`, and `exitVideoEdit`.
- Generated demos mirror the official request configuration when the Bundle Identifier is exactly `com.meishe.duanshipindemo`: `request.setHost("https://mall.meishesdk.com/api/shortvideo/v1")` and the official AutoCut URL. This official demo service is unavailable to other Bundle Identifiers; use a Meishe-provided customer server instead.
- Native iOS assigns the full AutoCut endpoint `https://creative.meishesdk.com/api/app/aivideo/asset/all/1` directly to `NvHttpRequest.assetAutoCutUrl`. Do not replace it with the RN/Flutter base URL form.
- ShortVideo `2.0.2.1` official native iOS Example declares `NSAllowsArbitraryLoads = true`. Its material/CDN subrequests can produce empty online lists when a temporary official-Demo host omits that Example compatibility setting, even though the top-level host is HTTPS.
- In ShortVideo `2.0.2.1`, AutoCut can publish with `hasDraft = false`. That flag controls whether the SDK's own publish UI offers a draft action; it is not proof that the callback project is absent or already persisted.
- When the supplied SDK exposes the verified project-manager and Swift timeline APIs, the generated publish page always offers save draft. Standard edits use `saveCurrentDraft`; AutoCut results with `hasDraft = false` treat the callback ID as a temporary task ID, copy the rendered result into the app runtime sandbox, and create a new standard editable draft with `NvTimelineDataManager.newProject`. The skill contains code only, never generated videos. Unknown API shapes preserve SDK behavior and emit a warning.

## Manual Verification Boundary

The script generates Swift/UIKit UI files, but does not edit the Xcode project file. Xcode target membership, app-specific navigation, compile delegate binding, and real-device behavior must be verified against the enhanced docs:

- `assets/shortvideo-docs/markdown/native_quickstart/doc_ch/quickstart_ch.md`
- `assets/shortvideo-docs/markdown/native_quickstart/doc_ch/functionConfiguration_ch.md`
- `assets/shortvideo-docs/markdown/native_quickstart/doc_ch/PrefabricatedMaterial_ch.md`

The native iOS handoff must preserve the same demo UI style as Android:

- Add `MeisheShortVideo/*.swift` to the app target.
- Add `MeisheShortVideo/Assets/meishe_home_banner.jpg` and the four custom function icons to the app target resources. If the project prefers `Assets.xcassets`, import them there with names `meishe_home_banner`, `meishe_icon_capture`, `meishe_icon_dual_capture`, `meishe_icon_edit`, and `meishe_icon_draft`.
- Wire the app's entry/navigation to present or push `MeisheShortVideoHomeViewController`.
- Home: dark background, title `素材上新`, fixed non-clickable banner, rows `拍摄` / `合拍` / `编辑` / `草稿` with the matching custom icons, no `拍动 v2.0.0` / `用户协议` / `隐私协议` footer.
- Home layout must fit within one viewport. Use screen-height percentages or Auto Layout constraints for banner height, spacing, and bottom whitespace; keep row height around 46-52 pt and preserve visible bottom whitespace.
- Home entry: configure the official demo service only when the Bundle Identifier is exactly `com.meishe.duanshipindemo`, start prefabricated material download in the background, and never block the four main demo entries when online material preparation fails.
- Capture, dual-capture, and edit taps must each call `downloadPrefabricatedMaterialCompletion(nil)` unconditionally and without blocking before opening the SDK page. A single home-start request is not equivalent to the official Demo flow, and `isMaterialRequestInProgress` from the home request must not suppress an entry refresh.
- `MeisheFeatureConfig.apply(to:)` 默认开启两个 `useAutoCut` 并在拍摄底部有序数组中保留 image/video/smart/template。删除任何菜单项时必须从数组移除，使 SDK 同步重排 UI；不得隐藏后留下空位。
- Generate `meishe_native_ios_self_check.md` with the empty-list symptom, Bundle Identifier/host/ATS/entry-refresh checks, HTTP/business-code/CDN diagnostics, and the manual real-device boundary.
- User-provided project: if its Bundle Identifier differs from `com.meishe.duanshipindemo`, tell the user the official service cannot be used and do not silently rename the app. Set the customer `host` and optional `assetAutoCutUrl` in `MeisheShortVideoHomeViewController.ServerConfig`. ShortVideo `2.0.2.1` does not expose writable `clientId`, `clientSecret`, or `assemblyId` properties on `NvHttpRequest`; customer authentication must follow Meishe's request delegate/service contract.
- Customer-server edit entry, field mapping, required user inputs, secret-handling rules, and real-device acceptance checks are defined in `references/customer-server.md`. Static values alone are not proof that the customer service works.
- Team, certificates, provisioning profiles, customer endpoints, credentials, and the formal license are user-specific. A temporary first-run value must be listed in `meishe_docking_report.md` and replaced before production handoff.
- For a newly created temporary project, Codex may use a Team/certificate that the user has already confirmed is available in the current Xcode account, then must report the exact Team ID and automatic/manual signing mode. For an existing project, preserve signing unless the user authorizes a change. Never fabricate an Apple Team or profile.
- Drafts: title `本地草稿箱`; empty state `没有草稿啦！`; non-empty warning `温馨提示： 卸载应用后，草稿也会被删除`; render `NvModuleManager.projectList()` rows with `NvEditProjectInfo.coverImagePath`, `projectDescription` / `defaultProjectDescription`, and `草稿-MMDD` fallback; delete only through long-press confirmation with `NvModuleManager.deleteDraft(projectId)`.
- Draft rows must make their decorative child stack non-interactive so the enclosing control receives short taps; the delete long-press recognizer must not cancel the short-tap control event. A short tap calls `reeditProject` with the drafts controller as `presentViewController`.
- Publish / Next: when `NvModuleManager` publish callbacks are received from edit, capture, or dual-capture flows, render a dark `作品发布` page with the same compact project row as drafts, thumbnail/play overlay, `草稿-MMDD` fallback title, save-draft/export/progress controls, and no light English form UI.
- AutoCut acceptance is `选择素材/模板入口 -> 一键成片 -> 标准编辑页 -> 下一步 -> 作品发布`; verify both `saveCurrentDraft` and `compileCurrentTimeline`. The separate direct template-compile path is outside this acceptance route.
- For the verified `2.0.2.1` API shape, the publish page must show `保存草稿` even when the callback reports `hasDraft = false`. Success requires a newly generated draft ID to be readable through `NvModuleManager.projectInfoForProject`; `exitVideoEdit` must still receive the original AutoCut task ID. Delete the mapped runtime media when the generated draft is deleted.
- The generated publish page's `UITextView` must provide an input accessory `完成` action, dismiss on taps outside the input, use interactive scroll dismissal, and update scroll insets for keyboard frame changes so lower actions remain reachable.
- After verified draft persistence, dismiss the complete SDK-presented navigation chain before calling `exitVideoEdit`, matching the official demo. Do not pop the SDK navigation controller to its root because its root can be the material picker instead of the app home. The publish page back button only pops back to the editor.

License is optional for running; without a real `.lic`, output contains the MEISHE watermark.
