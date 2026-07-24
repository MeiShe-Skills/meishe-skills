"""Flutter iOS integration and static verification."""

from __future__ import annotations

import re
from pathlib import Path

from meishe_docking_core import (
    IntegrationError,
    Report,
    is_within,
    read_text,
    rel,
    replace_external_source_path_refs,
    write_text,
)
from platform_support.ios import (
    inspect_plugin_root,
    ios_project_root,
    patch_ios_app_info_plists,
    patch_ios_podfile_min_version,
    plugin_relative_exists,
    plugin_relative_glob_exists,
    read_podspec_deployment_target,
    report_ios_signing_configuration,
    swift_method_branch_has_completion,
)


OFFICIAL_DEMO_BUNDLE_IDENTIFIER = "com.meishe.duanshipindemo"
FLUTTER_PROFILE_XCCONFIG_REFERENCE = "4D454953484550524F46494C"
FLUTTER_IOS_AUTOCUT_DRAFT_MARKERS = (
    "pendingPublishProjectId",
    "pendingDraftProjectId",
    "NvDraftSnapshotBridge.stageProject",
    "pendingDraftCommitted",
    "NvShortVideoPendingDraftProjectId",
)
FLUTTER_IOS_DRAFT_SNAPSHOT_API_MARKERS = (
    "NvTimelineDataManager",
    "newProject(localFilePaths:",
    "NvProEditConfig",
    "storeTimelineData",
    "updateProjectInfoFile",
    "managerAvailable",
    "destroySharedInstance",
)


def patch_flutter_ios_app_identity(
    target_root: Path,
    target_name: str,
    bundle_identifier: str,
    report: Report,
) -> None:
    ios_root = ios_project_root(target_root)
    if ios_root is None:
        return
    project_files = sorted(ios_root.glob("*.xcodeproj/project.pbxproj"))
    if not project_files:
        report.add_warning("Flutter iOS Xcode project was not found; Bundle Identifier was not updated.")
        return

    identity_pattern = re.compile(r'(PRODUCT_BUNDLE_IDENTIFIER\s*=\s*)(\"?)([^\";\n]+)(\"?;)')
    for project_file in project_files:
        text = read_text(project_file)

        def replace_identity(match: re.Match[str]) -> str:
            old_identity = match.group(3).strip()
            suffix_match = re.search(r"(\.[A-Za-z0-9_]+Tests)$", old_identity)
            suffix = suffix_match.group(1) if suffix_match else ""
            return f"{match.group(1)}{match.group(2)}{bundle_identifier}{suffix}{match.group(4)}"

        updated, count = identity_pattern.subn(replace_identity, text)
        if count and updated != text:
            write_text(
                project_file,
                updated,
                target_root,
                report,
                f"Set Flutter iOS `{target_name}` app/test Bundle Identifier to `{bundle_identifier}`",
            )
        elif bundle_identifier in text:
            report.add_change(f"Flutter iOS Bundle Identifier already uses `{bundle_identifier}`.")
        else:
            report.add_warning(
                f"Flutter iOS Bundle Identifier shape was not recognized in `{rel(project_file, target_root)}`."
            )
    report.add_input(f"Flutter iOS Bundle Identifier: `{bundle_identifier}`")


def flutter_ios_app_target_name(ios_root: Path) -> str:
    app_targets: set[str] = set()
    for project_file in sorted(ios_root.glob("*.xcodeproj/project.pbxproj")):
        text = read_text(project_file)
        section = re.search(
            r"/\* Begin PBXNativeTarget section \*/(?P<body>.*?)/\* End PBXNativeTarget section \*/",
            text,
            re.S,
        )
        if not section:
            continue
        for match in re.finditer(
            r"[A-Fa-f0-9]{8,}\s+/\*.*?\*/\s*=\s*\{(?P<body>.*?)^\s*\};",
            section.group("body"),
            re.M | re.S,
        ):
            body = match.group("body")
            if not re.search(
                r'productType\s*=\s*"?com\.apple\.product-type\.application"?\s*;',
                body,
            ):
                continue
            name_match = re.search(r"(?m)^\s*name\s*=\s*\"?([^\";]+)\"?\s*;", body)
            if name_match:
                app_targets.add(name_match.group(1).strip())

    podfile = ios_root / "Podfile"
    pod_targets = (
        {
            match.group(1)
            for match in re.finditer(
                r"(?m)^\s*target\s+['\"]([^'\"]+)['\"]\s+do",
                read_text(podfile),
            )
        }
        if podfile.exists()
        else set()
    )
    if len(app_targets) == 1:
        return next(iter(app_targets))
    if len(app_targets) > 1:
        matched = app_targets & pod_targets
        if len(matched) == 1:
            return next(iter(matched))
        choices = ", ".join(f"`{value}`" for value in sorted(app_targets))
        raise IntegrationError(
            "Could not uniquely infer the Flutter iOS application target from PBXNativeTarget and "
            f"Podfile declarations. Candidates: {choices}."
        )
    non_test_pod_targets = {
        value for value in pod_targets if not value.lower().endswith(("tests", "uitests"))
    }
    if len(non_test_pod_targets) == 1:
        return next(iter(non_test_pod_targets))
    raise IntegrationError(
        "Could not infer the Flutter iOS application target from PBXNativeTarget or Podfile. "
        "Regenerate/repair the iOS project before integration."
    )


def flutter_ios_project_path(ios_root: Path, target_name: str) -> Path:
    projects = sorted(ios_root.glob("*.xcodeproj"))
    matching = []
    for project in projects:
        project_file = project / "project.pbxproj"
        if not project_file.exists():
            continue
        text = read_text(project_file)
        if re.search(
            rf"(?m)^\s*name\s*=\s*\"?{re.escape(target_name)}\"?\s*;",
            text,
        ):
            matching.append(project)
    if len(matching) == 1:
        return matching[0]
    if not matching and len(projects) == 1:
        return projects[0]
    choices = ", ".join(f"`{project.name}`" for project in matching or projects)
    raise IntegrationError(
        f"Could not uniquely map Flutter iOS target `{target_name}` to an Xcode project. "
        f"Candidates: {choices or 'none'}."
    )


def ensure_flutter_ios_podfile(
    target_root: Path,
    minimum_version: str,
    target_name: str,
    report: Report,
) -> Path | None:
    ios_root = ios_project_root(target_root)
    if ios_root is None:
        return None
    podfile = ios_root / "Podfile"
    if podfile.exists():
        return podfile
    content = f"""platform :ios, '{minimum_version}'

ENV['COCOAPODS_DISABLE_STATS'] = 'true'

project '{target_name}', {{
  'Debug' => :debug,
  'Profile' => :release,
  'Release' => :release,
}}

def flutter_root
  generated_xcode_build_settings_path = File.expand_path(File.join('..', 'Flutter', 'Generated.xcconfig'), __FILE__)
  unless File.exist?(generated_xcode_build_settings_path)
    raise "#{{generated_xcode_build_settings_path}} must exist. Run `flutter pub get` before `pod install`."
  end

  File.foreach(generated_xcode_build_settings_path) do |line|
    matches = line.match(/FLUTTER_ROOT\\=(.*)/)
    return matches[1].strip if matches
  end
  raise "FLUTTER_ROOT not found in #{{generated_xcode_build_settings_path}}. Run `flutter pub get` again."
end

require File.expand_path(File.join('packages', 'flutter_tools', 'bin', 'podhelper'), flutter_root)

flutter_ios_podfile_setup

target '{target_name}' do
  use_frameworks!

  flutter_install_all_ios_pods File.dirname(File.realpath(__FILE__))
  test_target = '{target_name}Tests'
  target test_target do
    inherit! :search_paths
  end if File.exist?(File.join(File.dirname(__FILE__), test_target))
end

post_install do |installer|
  installer.pods_project.targets.each do |target|
    flutter_additional_ios_build_settings(target)
  end
end
"""
    write_text(podfile, content, target_root, report, "Generated Flutter iOS Podfile for the no-pub app template")
    return podfile


def ensure_flutter_ios_xcconfigs(
    target_root: Path,
    target_name: str,
    bundle_identifier: str | None,
    report: Report,
) -> None:
    ios_root = ios_project_root(target_root)
    if ios_root is None:
        return
    flutter_dir = ios_root / "Flutter"
    for mode, filename in (("debug", "Debug.xcconfig"), ("release", "Release.xcconfig"), ("profile", "Profile.xcconfig")):
        path = flutter_dir / filename
        text = read_text(path) if path.exists() else ""
        pod_include = (
            f'#include? "Pods/Target Support Files/Pods-{target_name}/'
            f'Pods-{target_name}.{mode}.xcconfig"'
        )
        lines = [line for line in text.splitlines() if line.strip()]
        changed = False
        if pod_include not in lines:
            lines.insert(0, pod_include)
            changed = True
        if '#include "Generated.xcconfig"' not in lines:
            lines.append('#include "Generated.xcconfig"')
            changed = True
        if changed or not path.exists():
            write_text(path, "\n".join(lines) + "\n", target_root, report, f"Configured Flutter iOS {filename}")

    project_files = sorted(ios_root.glob("*.xcodeproj/project.pbxproj"))
    if not project_files:
        report.add_warning("Flutter iOS project.pbxproj was not found; Profile.xcconfig target assignment was skipped.")
        return
    project_file = project_files[0]
    text = read_text(project_file)
    updated = text
    profile_comment = "Profile.xcconfig"
    reference_line = (
        f"\t\t{FLUTTER_PROFILE_XCCONFIG_REFERENCE} /* {profile_comment} */ = "
        "{isa = PBXFileReference; lastKnownFileType = text.xcconfig; name = Profile.xcconfig; "
        'path = Flutter/Profile.xcconfig; sourceTree = "<group>"; };\n'
    )
    if f"/* {profile_comment} */ =" not in updated:
        marker = "/* End PBXFileReference section */"
        if marker in updated:
            updated = updated.replace(marker, reference_line + marker, 1)
        else:
            report.add_warning("Flutter iOS PBXFileReference section was not recognized; add Profile.xcconfig to the Flutter group manually.")

    if f"{FLUTTER_PROFILE_XCCONFIG_REFERENCE} /* {profile_comment} */," not in updated:
        flutter_group = re.search(
            r"(?P<head>[A-F0-9]{24} /\* Flutter \*/ = \{.*?children = \(\n)(?P<children>.*?)(?P<tail>\n\s*\);\n\s*name = Flutter;)",
            updated,
            re.S,
        )
        if flutter_group:
            children = flutter_group.group("children")
            children += f"\n\t\t\t\t{FLUTTER_PROFILE_XCCONFIG_REFERENCE} /* {profile_comment} */,"
            updated = (
                updated[: flutter_group.start()]
                + flutter_group.group("head")
                + children
                + flutter_group.group("tail")
                + updated[flutter_group.end() :]
            )
        else:
            report.add_warning("Flutter iOS PBX Flutter group was not recognized; Profile.xcconfig file reference was not attached.")

    profile_pattern = re.compile(
        r"(?P<head>\s*[A-F0-9]{24} /\* Profile \*/ = \{\n\s*isa = XCBuildConfiguration;\n)(?P<body>.*?\n\s*name = Profile;\n\s*\};)",
        re.S,
    )
    profile_assigned = False
    for match in list(profile_pattern.finditer(updated)):
        body = match.group("body")
        if f"{target_name}Tests" in body or "TEST_HOST =" in body:
            continue
        matches_requested_identity = bool(
            bundle_identifier and f"PRODUCT_BUNDLE_IDENTIFIER = {bundle_identifier};" in body
        )
        if f"INFOPLIST_FILE = {target_name}/Info.plist;" not in body and not matches_requested_identity:
            continue
        replacement = body
        reference = f"baseConfigurationReference = {FLUTTER_PROFILE_XCCONFIG_REFERENCE} /* {profile_comment} */;"
        if re.search(r"baseConfigurationReference = [A-F0-9]+ /\* .*? \*/;", replacement):
            replacement = re.sub(
                r"baseConfigurationReference = [A-F0-9]+ /\* .*? \*/;",
                reference,
                replacement,
                count=1,
            )
        else:
            replacement = "\t\t\t" + reference + "\n" + replacement
        updated = updated[: match.start("body")] + replacement + updated[match.end("body") :]
        profile_assigned = True
        break
    if not profile_assigned:
        report.add_warning(
            f"Flutter iOS `{target_name}` Profile build configuration was not recognized; "
            "verify Profile.xcconfig target assignment manually."
        )

    if updated != text:
        write_text(
            project_file,
            updated,
            target_root,
            report,
            f"Assigned Flutter iOS `{target_name}` Profile.xcconfig",
        )
    else:
        report.add_change(f"Flutter iOS `{target_name}` Profile.xcconfig already assigned.")


def detected_ios_bundle_identifiers(target_root: Path) -> set[str]:
    identities: set[str] = set()
    ios_root = ios_project_root(target_root)
    if ios_root is None:
        return identities
    for project_file in ios_root.glob("*.xcodeproj/project.pbxproj"):
        for identity in re.findall(
            r'PRODUCT_BUNDLE_IDENTIFIER\s*=\s*"?([^";]+)"?;',
            read_text(project_file),
        ):
            value = identity.strip()
            if value and "$(" not in value and not value.lower().endswith("tests"):
                identities.add(value)
    return identities


def uses_official_demo_identity(target_root: Path) -> bool:
    return OFFICIAL_DEMO_BUNDLE_IDENTIFIER in detected_ios_bundle_identifiers(target_root)


def supports_flutter_ios_draft_snapshot_api(plugin: Path) -> bool:
    swift_text = "\n".join(read_text(path) for path in plugin.rglob("*.swiftinterface"))
    return all(marker in swift_text for marker in FLUTTER_IOS_DRAFT_SNAPSHOT_API_MARKERS)


def patch_flutter_ios_autocut_draft_bridge(
    target_root: Path,
    plugin: Path,
    source_plugin: Path,
    report: Report,
) -> None:
    bridge = plugin / "ios" / "Classes" / "VideoEditPlugin.swift"
    read_bridge = bridge
    if not read_bridge.exists() and report.dry_run:
        source_bridge = source_plugin / "ios" / "Classes" / "VideoEditPlugin.swift"
        if source_bridge.exists():
            read_bridge = source_bridge
    if not read_bridge.exists():
        report.add_warning(f"Flutter iOS bridge was not found at `{bridge}`; AutoCut draft compatibility was skipped.")
        return
    if not is_within(plugin, target_root):
        report.add_next_check(
            f"Flutter iOS AutoCut draft patch was skipped because the plugin package is outside the target project: `{plugin}`."
        )
        return

    inspection_plugin = plugin if plugin.exists() else source_plugin
    if not supports_flutter_ios_draft_snapshot_api(inspection_plugin):
        report.add_warning(
            "Flutter iOS SDK does not expose the verified ShortVideo 2.0.2.1 timeline snapshot API shape; no AutoCut draft vendor patch was applied."
        )
        return

    original = read_text(read_bridge)
    helper = plugin / "ios" / "Classes" / "NvDraftSnapshotBridge.swift"
    helper_source = read_text(Path(__file__).parent / "templates" / "NvDraftSnapshotBridge.swift")
    present_markers = [marker in original for marker in FLUTTER_IOS_AUTOCUT_DRAFT_MARKERS]
    if any(present_markers) and not all(present_markers):
        legacy_markers = (
            "pendingPublishProjectId",
            "NvProjectManager.storeCurrentProject",
            "NvModuleManager.projectInfoForProject",
        )
        if all(marker in original for marker in legacy_markers):
            report.add_warning(
                "Flutter iOS bridge contains the retired callback-projectId persistence patch. It was left unchanged to avoid an unsafe partial migration; regenerate from the official 2.0.2.1 plugin or migrate the bridge as one atomic change."
            )
        else:
            report.add_warning(
                "Flutter iOS AutoCut draft lifecycle patch is only partially present; the vendor bridge was left unchanged."
            )
        return
    if all(present_markers):
        write_text(helper, helper_source, target_root, report, "Generated Flutter iOS AutoCut draft snapshot helper")
        report.add_change("Flutter iOS AutoCut draft lifecycle compatibility patch already present.")
        return

    property_anchor = "    private var moduleManager: NvModuleManager?\n"
    request_anchor = "        self.requestDelegate = NvHttpRequestDelegate()\n"
    save_pattern = re.compile(
        r"        \} else if methodName == SaveDraftMethod \{\n.*?(?=        \} else if methodName == CompileVideoMethod \{)",
        re.DOTALL,
    )
    delete_pattern = re.compile(
        r"        \} else if methodName == DeleteDraftMethod \{\n.*?(?=        \} else if methodName == ExitVideoEditMethod \{)",
        re.DOTALL,
    )
    exit_pattern = re.compile(
        r"        \} else if methodName == ExitVideoEditMethod \{\n.*?(?=        \} else if methodName == (?:ConfigServerInfo|SaveDraftMethod) \{)",
        re.DOTALL,
    )
    publish_pattern = re.compile(
        r"    public func publish\(\n"
        r"        withProjectId projectId: String,\n"
        r"        coverImagePath: String\?,\n"
        r"        hasDraft: Bool,\n"
        r"        videoPath: String\?,\n"
        r"        description: String\?,\n"
        r"        videoEdit videoEditNavigationController: UINavigationController\n"
        r"    \) \{.*?\n    \}\n(?=\})",
        re.DOTALL,
    )
    missing_shapes = []
    for present, label in (
        (property_anchor in original, "moduleManager property"),
        (request_anchor in original, "requestDelegate initialization"),
        (save_pattern.search(original) is not None, "SaveDraftMethod"),
        (delete_pattern.search(original) is not None, "DeleteDraftMethod"),
        (exit_pattern.search(original) is not None, "ExitVideoEditMethod"),
        (publish_pattern.search(original) is not None, "publish delegate"),
    ):
        if not present:
            missing_shapes.append(label)
    if missing_shapes:
        report.add_warning(
            "Flutter iOS `VideoEditPlugin.swift` does not match the verified ShortVideo 2.0.2.1 AutoCut draft source shape "
            f"({', '.join(missing_shapes)} missing). The vendor bridge was left unchanged."
        )
        return

    patched = original.replace(
        property_anchor,
        property_anchor
        + "    private var pendingPublishProjectId: String?\n"
        + "    private var pendingDraftProjectId: String?\n"
        + "    private var pendingPublishHasDraft = false\n"
        + "    private var pendingDraftStaged = false\n"
        + "    private var pendingDraftCommitted = false\n",
        1,
    )
    patched = patched.replace(
        request_anchor,
        request_anchor
        + "        let defaults = UserDefaults.standard\n"
        + "        if let staleDraftId = defaults.string(forKey: \"NvShortVideoPendingDraftProjectId\"), !staleDraftId.isEmpty {\n"
        + "            _ = NvModuleManager.deleteDraft(staleDraftId)\n"
        + "            NvDraftSnapshotBridge.deleteRenderedMedia(projectId: staleDraftId)\n"
        + "            defaults.removeObject(forKey: \"NvShortVideoPendingDraftProjectId\")\n"
        + "        }\n",
        1,
    )

    for call in (
        "moduleManager?.startCapture(",
        "moduleManager?.startDualCapture(",
        "moduleManager?.startEdit(",
        "moduleManager?.reeditProject(",
    ):
        patched = patched.replace(call, "NvDraftSnapshotBridge.startCapture()\n            " + call)

    delete_method = """        } else if methodName == DeleteDraftMethod {
            let projectId = args?["projectId"] as? String
            if let projectId, !projectId.isEmpty, NvModuleManager.deleteDraft(projectId) {
                NvDraftSnapshotBridge.deleteRenderedMedia(projectId: projectId)
                completion(nil, nil)
                return
            }
            completion(nil, NSError(domain: "", code: -1, userInfo: [NSLocalizedDescriptionKey: "projectId error, draft does not exist"]))

"""
    patched = delete_pattern.sub(delete_method, patched, count=1)
    exit_method = """        } else if methodName == ExitVideoEditMethod {
            let projectId = args?["projectId"] as? String
            if pendingDraftStaged, !pendingDraftCommitted, let draftProjectId = pendingDraftProjectId {
                _ = NvModuleManager.deleteDraft(draftProjectId)
                NvDraftSnapshotBridge.deleteRenderedMedia(projectId: draftProjectId)
                UserDefaults.standard.removeObject(forKey: "NvShortVideoPendingDraftProjectId")
            }
            if let projectId {
                _ = moduleManager?.exitVideoEdit(projectId)
            }
            pendingPublishProjectId = nil
            pendingDraftProjectId = nil
            pendingDraftStaged = false
            pendingDraftCommitted = false
            completion(nil, nil)

"""
    patched = exit_pattern.sub(exit_method, patched, count=1)
    save_method = """        } else if methodName == SaveDraftMethod {
            let infoString = args?["draftInfo"] as? String ?? ""
            let draftProjectId = pendingDraftProjectId ?? moduleManager?.projectId
            guard let draftProjectId, !draftProjectId.isEmpty else {
                completion(nil, NSError(domain: "NvShortVideoDraft", code: -1, userInfo: [NSLocalizedDescriptionKey: "Save draft error: missing SDK draft projectId"]))
                return
            }

            var persisted = pendingDraftStaged && NvModuleManager.projectInfoForProject(draftProjectId) != nil
            if !persisted && pendingPublishHasDraft {
                let standardSaved = moduleManager?.saveCurrentDraft(withDraftInfo: infoString) == true
                persisted = standardSaved && NvModuleManager.projectInfoForProject(draftProjectId) != nil
            }
            if persisted {
                _ = NvModuleManager.updateProject(draftProjectId, description: infoString)
                pendingDraftCommitted = true
                UserDefaults.standard.removeObject(forKey: "NvShortVideoPendingDraftProjectId")
                completion(["projectId": draftProjectId, "publishTaskId": pendingPublishProjectId ?? ""] as NSDictionary, nil)
            } else {
                completion(nil, NSError(domain: "NvShortVideoDraft", code: -2, userInfo: [NSLocalizedDescriptionKey: "Save draft error: project was not added to the draft list"]))
            }

"""
    patched = save_pattern.sub(save_method, patched, count=1)
    publish_method = """    public func publish(
        withProjectId projectId: String,
        coverImagePath: String?,
        hasDraft: Bool,
        videoPath: String?,
        description: String?,
        videoEdit videoEditNavigationController: UINavigationController
    ) {
        pendingPublishProjectId = projectId
        pendingDraftProjectId = moduleManager?.projectId
        pendingPublishHasDraft = hasDraft
        pendingDraftCommitted = false
        NvDraftSnapshotBridge.stopCapture()
        if !hasDraft, let sdkProjectId = pendingDraftProjectId, !sdkProjectId.isEmpty {
            let renderedVideoPath = videoPath?.isEmpty == false ? videoPath : moduleManager?.publishInfo.videoPath
            pendingDraftProjectId = NvDraftSnapshotBridge.stageProject(
                projectId: sdkProjectId,
                projectDescription: description ?? "",
                coverImagePath: coverImagePath,
                videoPath: renderedVideoPath
            )
            pendingDraftStaged = pendingDraftProjectId?.isEmpty == false
        } else {
            pendingDraftStaged = false
        }
        if let draftProjectId = pendingDraftProjectId, pendingDraftStaged {
            UserDefaults.standard.set(draftProjectId, forKey: "NvShortVideoPendingDraftProjectId")
        } else {
            UserDefaults.standard.removeObject(forKey: "NvShortVideoPendingDraftProjectId")
        }

        var dic = [String: Any]()
        dic["hasDraft"] = hasDraft
        dic["projectId"] = projectId
        dic["coverImagePath"] = coverImagePath ?? ""
        dic["draftInfo"] = description ?? ""
        dic["videoPath"] = videoPath ?? ""
        sendFlutterMethod(VideoEditResultEvent, arguments: dic, channel: mainChannel)

        if videoEditNavigationController.presentingViewController?.presentingViewController != nil {
            guard let presentingVc = NvSPUtils.keyWindow()?.rootViewController else { return }
            presentingVc.dismiss(animated: true)
        } else {
            videoEditNavigationController.dismiss(animated: true)
        }
    }
"""
    patched = publish_pattern.sub(publish_method, patched, count=1)
    if not all(marker in patched for marker in FLUTTER_IOS_AUTOCUT_DRAFT_MARKERS) or "sendFlutterMethod(VideoEditResultEvent" not in patched:
        report.add_warning("Flutter iOS AutoCut draft patch did not produce every required marker; the vendor bridge was left unchanged.")
        return
    write_text(helper, helper_source, target_root, report, "Generated Flutter iOS AutoCut draft snapshot helper")
    write_text(
        bridge,
        patched,
        target_root,
        report,
        "Patched verified Flutter iOS AutoCut draft lifecycle and publish ordering",
    )


def write_flutter_ios_self_check(target_root: Path, report: Report) -> None:
    content = """# Flutter iOS 素材请求自检

## 典型现象

- 拍摄、合拍、编辑和草稿能够打开，但拍摄页的美颜、滤镜、贴纸或音乐在线列表为空。

## 已验证原因

1. ShortVideo `2.0.2.1` 官方 Flutter iOS Demo 使用 `NSAllowsArbitraryLoads = true`；官方 Demo 身份的临时验证工程缺少该 ATS 兼容项时，素材/CDN子链路可能被拦截。
2. 官方 Flutter Demo 在进入拍摄、合拍和编辑前都会再次非阻塞触发预制素材下载；只在首页首帧后台准备一次不等价。
3. `ConfigServerInfo` 和 `DownloadPrefabricatedMaterialCompletionMethod` 必须在 Swift bridge 的所有结果路径调用 completion，Dart 才能确认服务配置和下载结果。

## 生成代码自检

- 官方 Demo Bundle Identifier `com.meishe.duanshipindemo`：临时验证工程与官方 Flutter Demo 保持 `NSAllowsArbitraryLoads = true`；客户或正式工程必须改为真实域名级最小例外。
- `lib/meishe_short_video_demo.dart`：iOS 点击拍摄、合拍或编辑时，先等待服务配置回执，再由 `_runFeature` 直接非阻塞发起素材刷新，最后打开功能；三个入口都传入 `refreshMaterials: true`，且入口不调用受首页单飞状态保护的 `_prepareMaterialsInBackground()`。Android 点击路径不变。
- `lib/meishe_short_video_docking.dart`：官方 Demo 配置不发送伪造的 clientId、clientSecret 或 assemblyId；客户服务只按真实合同添加字段。
- 同一 wrapper 显式开启两个 `useAutoCut` 和 image/video/smart/template 拍摄菜单；共享 `assetAutoCutUrl` 保持官方 `/api/app` 基础地址。
- ShortVideo `2.0.2.1` 一键成片回调的 `hasDraft = false` 表示官方发布页不显示草稿按钮，不表示项目已经持久化。回调 `projectId` 是临时任务 ID，禁止直接落库。匹配已验证 API 时，bridge 通过 `NvDraftSnapshotBridge` 暂存可编辑模型；没有模型时把渲染视频复制到 App 运行时沙箱并用 `NvTimelineDataManager.newProject` 新建标准草稿。只有新草稿可列出时才向 Dart 返回成功，删除或放弃时清理映射媒体。skill 只包含代码，不包含视频。
- publish 事件必须先发送给 Flutter，再关闭 SDK 编辑器；发布页保存成功后才退出流程，失败时留在当前页显示原生错误。

## 手工验收

1. 清理旧缓存或重新安装 App，首次启动后允许相机、麦克风、相册和网络权限。
2. 进入拍摄，逐项检查美颜、滤镜、贴纸和音乐在线列表，至少下载并实际使用一个在线素材。
3. 分别从编辑素材选择、模板页和拍摄模板菜单进入一键成片，确认生成结果进入标准编辑页。
4. 在标准编辑页点击下一步，分别检查作品发布、保存草稿、草稿继续编辑和导出视频。
5. 若仍为空，检查 Xcode 中的 ATS、ConfigServerInfo、HTTP 状态、业务码、Bundle Identifier 白名单和 CDN 下载日志。

## 运行时诊断边界

- 日志出现 `NvCodable.swift ... invalid JSON ... unexpected EOF` 时，记录发生入口、原始回调是否为空、字符串长度和前后截断片段；不得吞掉异常或把截断 JSON 当成成功数据。若编辑、发布、保存草稿和继续编辑均完成，可先标记为非阻塞供应商诊断，但仍需在可复现时把完整上下文交给美摄。
- `Functionality fxExpression is not authorised!` 表示当前 License 未授权该特定能力，不等于 SDK 初始化或基础编辑链路失败。分别验证表达式功能与拍摄/编辑/草稿主链路，并使用匹配最终 Bundle Identifier 的正式 License 复测。
- Flutter iOS Debug 包必须通过活动 `flutter run -d <IOS_DEVICE_ID>` 会话或 Xcode 的 Product > Run 启动。直接使用 `devicectl` 启动可能触发 Flutter Debug Engine 限制，只能作为安装/设备诊断，不能作为默认 Debug 启动或接入失败证据。

需要真机完成以上验收时，先列出全部设备操作、原因和预期信息，让用户选择“用户执行”或“自动执行”；自动执行会额外消耗 Token 和时间。
"""
    write_text(
        target_root / "meishe_flutter_ios_self_check.md",
        content,
        target_root,
        report,
        "Generated Flutter iOS material-request self-check handoff",
    )


def verify_flutter_ios_bridge_completion(plugin: Path, source_plugin: Path, target_root: Path, report: Report) -> None:
    inspection_root = inspect_plugin_root(plugin, source_plugin, report, "Flutter iOS")
    swift_file = inspection_root / "ios" / "Classes" / "VideoEditPlugin.swift"
    display = plugin / "ios" / "Classes" / "VideoEditPlugin.swift"
    if not swift_file.exists():
        message = f"Flutter iOS: bridge file missing: `{rel(display, target_root)}`"
        report.add_ios_quick_verify(message)
        report.add_vendor_warning(message)
        return
    text = read_text(swift_file)
    missing = [
        method
        for method in ("ConfigServerInfo", "DownloadPrefabricatedMaterialCompletionMethod")
        if not swift_method_branch_has_completion(text, method)
    ]
    if missing:
        message = f"Flutter iOS: bridge completion check failed for {', '.join(missing)} in `{rel(display, target_root)}`."
        report.add_ios_quick_verify(message)
        report.add_vendor_warning(message)
    else:
        report.add_ios_quick_verify(f"Flutter iOS: bridge completion check passed: `{rel(display, target_root)}`")

def quick_verify_flutter_ios(
    target_root: Path,
    plugin: Path,
    source_plugin: Path,
    bundle_identifier: str | None,
    report: Report,
) -> None:
    if ios_project_root(target_root) is None:
        report.add_ios_quick_verify("Flutter iOS: target has no `ios/` directory; skipped static iOS checks.")
        return
    inspection_root = inspect_plugin_root(plugin, source_plugin, report, "Flutter iOS")
    official_demo_identity = (
        bundle_identifier == OFFICIAL_DEMO_BUNDLE_IDENTIFIER
        or uses_official_demo_identity(target_root)
    )
    detected_identities = (
        {bundle_identifier}
        if bundle_identifier
        else detected_ios_bundle_identifiers(target_root)
    )
    patch_ios_app_info_plists(
        target_root,
        report,
        "Flutter iOS",
        allow_arbitrary_loads=official_demo_identity,
    )
    if official_demo_identity:
        report.add_user_configuration(
            "Flutter iOS official-Demo compatibility: `NSAllowsArbitraryLoads = true` is enabled only for temporary `com.meishe.duanshipindemo` Demo-service validation. Replace it with verified domain-specific ATS exceptions before production."
        )
    else:
        identity_label = (
            ", ".join(f"`{value}`" for value in sorted(detected_identities))
            if detected_identities
            else "an unrecognized existing App Target identity"
        )
        report.add_warning(
            "Flutter iOS official Demo material service requires the exact Bundle Identifier "
            f"`com.meishe.duanshipindemo`, but the current iOS identity is {identity_label}. "
            "Online service requests will not work with that identity. For temporary Demo validation use "
            "`--ios-bundle-identifier com.meishe.duanshipindemo`; otherwise keep the existing identity and "
            "configure a customer server, matching License, and service allowlist."
        )
        report.add_ios_quick_verify(
            "Flutter iOS: global NSAllowsArbitraryLoads was not enabled for a customer Bundle Identifier; use only verified domain-specific ATS exceptions."
        )
    missing_required = []
    podspec_rel = "ios/nvshortvideo.podspec"
    podspec = inspection_root / podspec_rel
    if not plugin_relative_exists(inspection_root, plugin, podspec_rel, target_root, report, "Flutter iOS", "podspec"):
        missing_required.append(podspec_rel)
    minimum_version = read_podspec_deployment_target(podspec) or "13.0"
    target_name = flutter_ios_app_target_name(ios_project_root(target_root) or target_root / "ios")
    report.add_input(f"Flutter iOS app target: `{target_name}`")
    podfile = ensure_flutter_ios_podfile(target_root, minimum_version, target_name, report)
    ensure_flutter_ios_xcconfigs(target_root, target_name, bundle_identifier, report)
    if podfile and podfile.exists():
        patch_ios_podfile_min_version(target_root, report, "Flutter iOS", minimum_version)
    elif report.dry_run:
        report.add_ios_quick_verify(
            f"Flutter iOS: Podfile will be generated with explicit iOS {minimum_version} before dependency installation."
        )
    if not plugin_relative_exists(inspection_root, plugin, "ios/Classes/VideoEditPlugin.swift", target_root, report, "Flutter iOS", "Swift bridge"):
        missing_required.append("ios/Classes/VideoEditPlugin.swift")
    if not plugin_relative_exists(inspection_root, plugin, "ios/Assets", target_root, report, "Flutter iOS", "iOS assets directory", is_dir=True):
        missing_required.append("ios/Assets")
    if not plugin_relative_glob_exists(inspection_root, plugin, "ios/Frameworks", "*.xcframework", target_root, report, "Flutter iOS", "vendored xcframeworks"):
        missing_required.append("ios/Frameworks/*.xcframework")
    verify_flutter_ios_bridge_completion(plugin, source_plugin, target_root, report)
    if missing_required:
        report.add_vendor_warning(
            "Flutter iOS readiness failed: copied plugin is missing "
            + ", ".join(missing_required)
            + ". Provide the complete official Flutter package from Meishe Developer Center (`Flutter工程`) for iOS verification; do not substitute the native iOS `Pods-NvShortVideoEdit` package."
        )


def integrate(
    target_root: Path,
    plugin: Path,
    source_plugin: Path,
    bundle_identifier: str | None,
    report: Report,
) -> None:
    ios_root = ios_project_root(target_root)
    if ios_root is None:
        return
    target_name = flutter_ios_app_target_name(ios_root)
    if bundle_identifier:
        patch_flutter_ios_app_identity(
            target_root,
            target_name,
            bundle_identifier,
            report,
        )
    report_ios_signing_configuration(target_root, report)
    replace_external_source_path_refs(
        target_root,
        source_plugin,
        plugin,
        [target_root / "ios" / "Podfile.lock"],
        report,
        "Flutter iOS",
    )
    patch_flutter_ios_autocut_draft_bridge(target_root, plugin, source_plugin, report)
    quick_verify_flutter_ios(target_root, plugin, source_plugin, bundle_identifier, report)
    write_flutter_ios_self_check(target_root, report)
    report.add_user_configuration(
        "Flutter iOS signing: set the user's Team/certificate/profile in Xcode. Temporary signing used for first launch is not a production setting."
    )
    report.add_next_check(
        "Flutter iOS: after the approved dependency steps complete, validate the generated workspace with Xcode/xcodebuild and a real device."
    )
    report.add_next_check(
        "Flutter iOS AutoCut: manually verify save draft returns only after the generated standard draft ID appears in the draft list, then confirm it can be reopened with non-black video and deleted without leaving mapped runtime media."
    )
