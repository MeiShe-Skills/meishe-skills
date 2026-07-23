"""Native iOS fixture validation."""

from __future__ import annotations

import argparse
import plistlib
import shutil
import sys
from pathlib import Path

from meishe_docking_core import Report
from routes.native_ios.implementation import patch_xcode_26_user_script_sandboxing
from routes.native_ios.support import resolve_ios_project_context

from .shared import (
    assert_contains,
    assert_not_contains,
    read,
    run_integration,
    run_integration_apply,
    run_integration_failure,
    write,
    write_plist,
)


def create_native_ios_target(
    root: Path,
    bundle_identifier: str = "com.meishe.duanshipindemo",
    *,
    include_podfile: bool = True,
    project_name: str = "NativeIosFixture",
    target_name: str = "NativeIosFixture",
    scheme_name: str | None = None,
) -> None:
    if include_podfile:
        write(
            root / "Podfile",
            """platform :ios, '12.0'
source 'https://github.com/CocoaPods/Specs.git'

target 'TARGET_NAME' do
end
""".replace("TARGET_NAME", target_name),
        )
    write(root / "Gemfile", "source 'https://rubygems.org'\ngem 'cocoapods'\n")
    write_plist(root / target_name / "Info.plist", {"CFBundleName": target_name})
    write(
        root / f"{project_name}.xcodeproj" / "project.pbxproj",
        f"""// !$*UTF8*$!
/* Begin PBXNativeTarget section */
		111111111111111111111111 /* {target_name} */ = {{
			isa = PBXNativeTarget;
			buildConfigurationList = 333333333333333333333333 /* Build configuration list for PBXNativeTarget "{target_name}" */;
			name = {target_name};
			productName = {target_name};
			productType = "com.apple.product-type.application";
		}};
		222222222222222222222222 /* {target_name}Tests */ = {{
			isa = PBXNativeTarget;
			buildConfigurationList = 444444444444444444444444 /* Build configuration list for PBXNativeTarget "{target_name}Tests" */;
			name = {target_name}Tests;
			productName = {target_name}Tests;
			productType = "com.apple.product-type.bundle.unit-test";
		}};
/* End PBXNativeTarget section */

/* Begin XCBuildConfiguration section */
		AAAAAAAAAAAAAAAAAAAAAAAA /* Debug */ = {{
			isa = XCBuildConfiguration;
			buildSettings = {{
				PRODUCT_BUNDLE_IDENTIFIER = {bundle_identifier};
				INFOPLIST_FILE = {target_name}/Info.plist;
				CODE_SIGN_STYLE = Automatic;
			}};
			name = Debug;
		}};
		BBBBBBBBBBBBBBBBBBBBBBBB /* Release */ = {{
			isa = XCBuildConfiguration;
			buildSettings = {{
				PRODUCT_BUNDLE_IDENTIFIER = {bundle_identifier};
				INFOPLIST_FILE = {target_name}/Info.plist;
				CODE_SIGN_STYLE = Automatic;
			}};
			name = Release;
		}};
		CCCCCCCCCCCCCCCCCCCCCCCC /* Debug */ = {{
			isa = XCBuildConfiguration;
			buildSettings = {{
				ENABLE_USER_SCRIPT_SANDBOXING = YES;
				PRODUCT_BUNDLE_IDENTIFIER = {bundle_identifier}.tests;
			}};
			name = Debug;
		}};
/* End XCBuildConfiguration section */

/* Begin XCConfigurationList section */
		333333333333333333333333 /* Build configuration list for PBXNativeTarget "{target_name}" */ = {{
			isa = XCConfigurationList;
			buildConfigurations = (
				AAAAAAAAAAAAAAAAAAAAAAAA /* Debug */,
				BBBBBBBBBBBBBBBBBBBBBBBB /* Release */,
			);
		}};
		444444444444444444444444 /* Build configuration list for PBXNativeTarget "{target_name}Tests" */ = {{
			isa = XCConfigurationList;
			buildConfigurations = (
				CCCCCCCCCCCCCCCCCCCCCCCC /* Debug */,
			);
		}};
/* End XCConfigurationList section */
""",
    )
    resolved_scheme = scheme_name or target_name
    write(
        root
        / f"{project_name}.xcodeproj"
        / "xcshareddata"
        / "xcschemes"
        / f"{resolved_scheme}.xcscheme",
        (
            '<?xml version="1.0" encoding="UTF-8"?><Scheme version="1.7">'
            f'<BuildableReference BlueprintName="{target_name}" '
            f'ReferencedContainer="container:{project_name}.xcodeproj"/>'
            "</Scheme>\n"
        ),
    )

def create_native_ios_package(root: Path, *, include_autocut_draft_api: bool = True) -> Path:
    write(
        root / "native" / "ios" / "Pods-NvShortVideoEdit" / "NvShortVideoEdit.podspec",
        """Pod::Spec.new do |s|
  s.name = 'NvShortVideoEdit'
  s.ios.deployment_target = '12.0'
end
""",
    )
    write(root / "native" / "ios" / "ShortVideoDemo" / "Config.swift", "let NV_ClientId = \"<YOUR_MEISHE_CLIENT_ID>\"\n")
    write(root / "native" / "ios" / "ShortVideoDemo" / "NvHttpRequestDelegate.swift", "final class NvHttpRequestDelegate {}\n")
    if include_autocut_draft_api:
        write(
            root
            / "native"
            / "ios"
            / "Pods-NvShortVideoEdit"
            / "Frameworks"
            / "NvShortVideoCore.xcframework"
            / "ios-arm64"
            / "NvShortVideoCore.framework"
            / "Headers"
            / "NvShortVideoCore-Swift.h",
            """+ (NvEditProjectInfo * _Nullable)projectInfoForProject:(NSString * _Nonnull)projectId;
+ (BOOL)storeCurrentProjectWithProjectId:(NSString * _Nonnull)projectId projectDescription:(NSString * _Nullable)projectDescription;
""",
        )
        write(
            root
            / "native"
            / "ios"
            / "Pods-NvShortVideoEdit"
            / "Frameworks"
            / "NvShortVideoCore.xcframework"
            / "ios-arm64"
            / "NvShortVideoCore.framework"
            / "Modules"
            / "NvShortVideoCore.swiftmodule"
            / "arm64-apple-ios.swiftinterface",
            """public class NvTimelineDataManager {
  public class func managerAvailable() -> Swift.Bool
  public class func destroySharedInstance(destroyContext: Swift.Bool)
  public func newProject(localFilePaths: [Swift.String], configration: NvProEditConfig) -> Swift.Bool
}
public class NvProEditConfig {}
""",
        )
    write_plist(
        root / "native" / "ios" / "Pods-NvShortVideoEdit" / "Example" / "NvShortVideo" / "Info.plist",
        {"NSAppTransportSecurity": {"NSAllowsArbitraryLoads": True}},
    )
    write_plist(
        root / "native" / "ios" / "Pods-NvShortVideoEdit" / "Frameworks" / "Fixture.xcframework" / "Info.plist",
        {"CFBundlePackageType": "XFWK", "FixtureMarker": "unchanged"},
    )
    return root

def validate_native_ios_complete(work: Path) -> None:
    target = work / "native_ios_target"
    source = work / "native_ios_source"
    create_native_ios_target(target)
    package = create_native_ios_package(source)
    output = run_integration(target, "native-ios", package)
    assert_contains(
        output,
        [
            "Skill: `meishe-native-ios-duanshipin-docking`",
            "Platform: `native-ios`",
            "iOS target: `NativeIosFixture`",
            "Native iOS Bundle Identifier: `com.meishe.duanshipindemo`",
            "NvShortVideoEdit project-local pod path",
            "vendor/meishe/Pods-NvShortVideoEdit",
            "Updated native iOS Podfile for NvShortVideoEdit",
            "Native iOS: updated iOS privacy permissions",
            "Native iOS official-Demo compatibility",
            "Copied native iOS demo config file `Config.swift`",
            "Copied native iOS demo config file `NvHttpRequestDelegate.swift`",
            "Copied demo home banner for native iOS",
            "MeisheShortVideo/Assets/meishe_home_banner.jpg",
            "Copied demo function icon for native iOS",
            "Generated native iOS Swift UI support",
            "MeisheShortVideo/MeisheShortVideoStyle.swift",
            "Generated user-editable native iOS feature configuration",
            "MeisheShortVideo/MeisheFeatureConfig.swift",
            "Generated native iOS Swift home view controller",
            "MeisheShortVideo/MeisheShortVideoHomeViewController.swift",
            "Generated native iOS Swift drafts view controller",
            "MeisheShortVideo/MeisheShortVideoDraftsViewController.swift",
            "Generated native iOS Swift publish view controller",
            "MeisheShortVideo/MeisheShortVideoPublishViewController.swift",
            "Native iOS ShortVideo 2.0.2.1 AutoCut draft and timeline API shapes matched",
            "Generated native iOS handoff notes",
            "Generated native iOS material-request self-check handoff",
            "meishe_native_ios_self_check.md",
            "Dependency Installation",
            "Status: `execution mode choice required`",
            "用户执行（推荐）",
            "自动执行：Agent 执行已列出的任务内操作",
            "额外消耗 Token 和时间",
            "可见回复要求",
            "折叠的“处理中”区域",
            "真机要求：美摄短视频 Demo 必须运行在真实 iPhone 或 iPad 上",
            "Native iOS: self-contained SDK check passed",
            "Native iOS package root: self-contained SDK check passed",
            "Native iOS integration uses safe automation",
            "Xcode target membership",
            "No meishesdk.lic was supplied",
            "User-Specific Configuration",
            "Xcode signing",
            "Detected shared app scheme: `NativeIosFixture`",
            "references/customer-server.md",
            "Configuration Handoff",
            "原生 iOS 功能配置",
            "Product > Run",
            "已检测到的 NativeIosFixture scheme",
        ],
        "Native iOS complete dry-run",
    )
    if sys.platform == "darwin":
        assert_contains(
            output,
            ["Native iOS CocoaPods", "Command/method: `bundle exec pod install`"],
            "Native iOS Bundler-aware dependency handoff",
        )
    run_integration_apply(target, "native-ios", package)
    podfile = (target / "Podfile").read_text(encoding="utf-8")
    assert_contains(
        podfile,
        [
            "platform :ios, '12.0'",
            "pod 'NvShortVideoEdit',    :path => './vendor/meishe/Pods-NvShortVideoEdit', :inhibit_warnings => true",
            "source 'https://github.com/CocoaPods/Specs.git'",
        ],
        "Native iOS migrated Podfile",
    )
    assert_not_contains(
        podfile,
        ["inhibit_all_warnings!", "IPHONEOS_DEPLOYMENT_TARGET"],
        "Native iOS CocoaPods setting isolation",
    )
    with (target / "NativeIosFixture" / "Info.plist").open("rb") as fh:
        info_plist = plistlib.load(fh)
    if info_plist.get("NSAppTransportSecurity", {}).get("NSAllowsArbitraryLoads") is not True:
        raise AssertionError("Native iOS official-Demo fixture must mirror the supplied Example ATS setting")
    vendored_framework_plist = (
        target
        / "vendor"
        / "meishe"
        / "Pods-NvShortVideoEdit"
        / "Frameworks"
        / "Fixture.xcframework"
        / "Info.plist"
    )
    with vendored_framework_plist.open("rb") as fh:
        framework_info = plistlib.load(fh)
    if framework_info != {"CFBundlePackageType": "XFWK", "FixtureMarker": "unchanged"}:
        raise AssertionError("Native iOS app permission patch must not modify vendored framework plists")
    self_check = (target / "meishe_native_ios_self_check.md").read_text(encoding="utf-8")
    handoff = (target / "meishe_native_ios_handoff.md").read_text(encoding="utf-8")
    configuration_handoff = (target / "meishe_configuration_handoff.md").read_text(encoding="utf-8")
    publish = (target / "MeisheShortVideo" / "MeisheShortVideoPublishViewController.swift").read_text(encoding="utf-8")
    drafts = (target / "MeisheShortVideo" / "MeisheShortVideoDraftsViewController.swift").read_text(encoding="utf-8")
    assert_contains(
        publish,
        [
            "draftInput.inputAccessoryView = toolbar",
            "scrollView.keyboardDismissMode = .interactive",
            "tap.cancelsTouchesInView = false",
            "UIResponder.keyboardWillChangeFrameNotification",
            "view.endEditing(true)",
            "scrollView.contentInset.bottom = bottom",
            "scrollView.scrollRectToVisible(inputFrame, animated: true)",
            "saveDraftButton.isHidden = false",
            "moduleManager.saveCurrentDraft(withDraftInfo: description)",
            "NvAutoCutDraftMedia",
            "NvTimelineDataManager.sharedInstance()",
            "newProject(",
            "localFilePaths: [durableVideoURL.path]",
            "let draftProjectId = model.projectId",
            "mediaByProject[draftProjectId]",
            "MeisheAutoCutDraftStore.stageRenderedVideo(",
            "NvProjectManager.storeCurrentProject(",
            "NvModuleManager.projectInfoForProject(draftProjectId)",
            "isDraftListable(projectId: stagedProjectId)",
            "exitVideoEdit(self.projectId)",
            "草稿保存失败：项目未进入草稿列表。",
        ],
        "Native iOS publish keyboard and AutoCut draft handling",
    )
    assert_not_contains(
        publish,
        ["saveDraftButton.isHidden = !hasDraft"],
        "Native iOS verified AutoCut draft button visibility",
    )
    assert_contains(
        drafts,
        ["MeisheAutoCutDraftStore.deleteRenderedMedia(projectId: draft.projectId)"],
        "Native iOS rendered AutoCut draft media cleanup",
    )
    assert_contains(
        self_check,
        [
            "在线素材列表为空",
            "NSAllowsArbitraryLoads = true",
            "不得递归修改",
            "downloadPrefabricatedMaterialCompletion(nil)",
            "isMaterialRequestInProgress",
            "不提供可写的 `clientId`、`clientSecret`、`assemblyId`",
            "选择“用户执行”或“自动执行”",
            "额外消耗 Token 和时间",
            "必须安装到真实 iPhone 或 iPad",
            "iOS Simulator 和其他虚拟设备不受支持",
            "分别从编辑素材选择、模板页和拍摄模板菜单进入一键成片",
            "ShortVideo `2.0.2.1` 草稿与时间线 API",
            "新的标准可编辑草稿",
            "导出视频",
        ],
        "Native iOS material self-check",
    )
    home = (target / "MeisheShortVideo" / "MeisheShortVideoHomeViewController.swift").read_text(encoding="utf-8")
    feature_config = (target / "MeisheShortVideo" / "MeisheFeatureConfig.swift").read_text(encoding="utf-8")
    assert_contains(
        home,
        [
            "private func configureFeatures()",
            "MeisheFeatureConfig.apply(to: videoConfig)",
            'static let assetAutoCutUrl: String? = "https://creative.meishesdk.com/api/app/aivideo/asset/all/1"',
        ],
        "Native iOS feature config entry",
    )
    assert_contains(
        feature_config,
        [
            "原生 iOS 专属配置",
            "config.albumConfig.useAutoCut = true",
            "NvCaptureMenu.speed",
            "NvCaptureMenu.matting",
            "NvCaptureBottomMenu.template",
            "NvEditMenuItemConstants.text",
            "删除 text 会删除文字入口及其下级功能",
            "未公开 disableTimeEffect",
            "defaultBottomMenuSelectItem must exist",
            "editConfig.maxVolume must be greater than 0 and no greater than 8",
        ],
        "Native iOS user-editable feature configuration",
    )
    assert_not_contains(
        feature_config,
        ["config.editConfig.disableTimeEffect"],
        "Native iOS unsupported edit property generation guard",
    )
    assert_contains(
        handoff,
        [
            "MeisheFeatureConfig.swift",
            "ordered menu arrays remove entries and reflow SDK UI",
            "standard editor",
            "save draft or export video",
            "standard editable draft",
            "app runtime sandbox",
            "meishe_configuration_handoff.md",
            "Real-device requirement",
            "physical iPhone or iPad",
            "iOS Simulator and other virtual devices are unsupported",
        ],
        "Native iOS AutoCut handoff",
    )
    assert_contains(
        configuration_handoff,
        [
            "### 配置修改与生效速览",
            "| 配置项 | 修改入口 | 适用平台 | 最快生效方式 | 重新构建条件 | 无需执行 |",
            "| iOS |",
            str((target / "MeisheShortVideo" / "MeisheFeatureConfig.swift").resolve()),
            str((target / "MeisheShortVideo" / "MeisheShortVideoHomeViewController.swift").resolve()),
            "open",
            "NativeIosFixture.xcworkspace",
            "Signing & Capabilities",
            "Product > Run",
            "Target Membership",
            "真机要求：美摄短视频 Demo 必须运行在真实 iPhone 或 iPad 上",
            "无需再次 pod install",
            "不要默认 Clean Build Folder",
        ],
        "Native iOS command-level configuration handoff",
    )
    run_after_materials = home[
        home.index("private func runAfterMaterials") : home.index("private func prepareMaterialsInBackground")
    ]
    assert_contains(
        run_after_materials,
        ["moduleManager.downloadPrefabricatedMaterialCompletion(nil)", "action()"],
        "Native iOS unconditional entry material refresh",
    )
    assert_not_contains(
        run_after_materials,
        ["prepareMaterialsInBackground()", "isMaterialRequestInProgress"],
        "Native iOS entry refresh isolation from home request state",
    )
    entry_blocks = {
        "capture": home[home.index("private func openCapture()") : home.index("private func openDualCapture()")],
        "dual capture": home[home.index("private func openDualCapture()") : home.index("private func openEdit()")],
        "edit": home[home.index("private func openEdit()") : home.index("private func openDrafts()")],
    }
    for label, block in entry_blocks.items():
        assert_contains(block, ["runAfterMaterials"], f"Native iOS {label} entry material refresh")
    assert_not_contains(
        home,
        ["request.clientId", "request.clientSecret", "request.assemblyId"],
        "Native iOS ShortVideo 2.0.2.1 request API compatibility",
    )
    user_feature_marker = "// USER_FEATURE_CONFIG_MUST_BE_PRESERVED"
    feature_config_path = target / "MeisheShortVideo" / "MeisheFeatureConfig.swift"
    write(feature_config_path, feature_config + f"\n{user_feature_marker}\n")
    run_integration_apply(target, "native-ios", package)
    assert_contains(
        read(feature_config_path),
        [user_feature_marker],
        "Native iOS user feature configuration preservation",
    )


def validate_native_ios_xcode26_patch(work: Path) -> None:
    xcode26_target = work / "native_ios_xcode26_target"
    create_native_ios_target(xcode26_target)
    report = Report(target_root=xcode26_target, platform="native-ios", dry_run=False)
    context = resolve_ios_project_context(xcode26_target, argparse.Namespace(ios_target=None))
    if not patch_xcode_26_user_script_sandboxing(
        xcode26_target,
        report,
        context,
        xcode_major=26,
        detect_if_none=False,
    ):
        raise AssertionError("Native iOS Xcode 26 fixture did not apply the verified patch")
    pbxproj = read(xcode26_target / "NativeIosFixture.xcodeproj" / "project.pbxproj")
    if pbxproj.count("ENABLE_USER_SCRIPT_SANDBOXING = NO;") != 2:
        raise AssertionError("Native iOS Xcode 26 patch must cover only the two app build configurations")
    if pbxproj.count("ENABLE_USER_SCRIPT_SANDBOXING = YES;") != 1:
        raise AssertionError("Native iOS Xcode 26 patch must preserve the test-target setting")
    patch_xcode_26_user_script_sandboxing(
        xcode26_target,
        report,
        context,
        xcode_major=26,
        detect_if_none=False,
    )
    pbxproj = read(xcode26_target / "NativeIosFixture.xcodeproj" / "project.pbxproj")
    if pbxproj.count("ENABLE_USER_SCRIPT_SANDBOXING = NO;") != 2:
        raise AssertionError("Native iOS Xcode 26 patch duplicated the build setting")

    unknown_target = work / "native_ios_unknown_xcode_target"
    create_native_ios_target(unknown_target)
    unknown_report = Report(target_root=unknown_target, platform="native-ios", dry_run=False)
    unknown_context = resolve_ios_project_context(unknown_target, argparse.Namespace(ios_target=None))
    if patch_xcode_26_user_script_sandboxing(
        unknown_target,
        unknown_report,
        unknown_context,
        xcode_major=None,
        detect_if_none=False,
    ):
        raise AssertionError("Native iOS unknown Xcode version must not inherit the Xcode 26 patch")
    assert_not_contains(
        read(unknown_target / "NativeIosFixture.xcodeproj" / "project.pbxproj"),
        ["ENABLE_USER_SCRIPT_SANDBOXING = NO;"],
        "Native iOS unknown Xcode version isolation",
    )
    assert_contains(
        "\n".join(unknown_report.toolchain_warnings),
        ["Xcode version could not be determined", "was not applied"],
        "Native iOS unknown Xcode handoff",
    )


def validate_native_ios_project_identity_and_podfile_scoping(work: Path) -> None:
    target = work / "native_ios_renamed_project_target"
    source = work / "native_ios_renamed_project_source"
    create_native_ios_target(
        target,
        project_name="ShellProject",
        target_name="ShortVideoApp",
        scheme_name="ProductionApp",
    )
    write(
        target / "Podfile",
        """source 'https://cdn.cocoapods.org/'
source 'https://pods.customer.example/specs.git'
platform :ios, '13.0'
use_frameworks!

target 'ShortVideoApp' do
  pod 'Alamofire', '~> 5.9'
end

post_install do |installer|
  installer.pods_project.targets.each do |target|
    target.build_configurations.each do |config|
      config.build_settings['CUSTOM_CUSTOMER_SETTING'] = 'PRESERVE'
    end
  end
end
""",
    )
    package = create_native_ios_package(source)
    output = run_integration(target, "native-ios", package)
    assert_contains(
        output,
        [
            "iOS target: `ShortVideoApp`",
            "Xcode project: `ShellProject.xcodeproj`",
            "Xcode workspace: `ShellProject.xcworkspace`",
            "Detected shared app scheme: `ProductionApp`",
        ],
        "Native iOS independent project identity detection",
    )
    run_integration_apply(target, "native-ios", package)
    podfile = read(target / "Podfile")
    assert_contains(
        podfile,
        [
            "target 'ShortVideoApp' do",
            "pod 'Alamofire', '~> 5.9'",
            "source 'https://pods.customer.example/specs.git'",
            "CUSTOM_CUSTOMER_SETTING",
            "pod 'NvShortVideoEdit',    :path => './vendor/meishe/Pods-NvShortVideoEdit', :inhibit_warnings => true",
        ],
        "Native iOS complex Podfile preservation",
    )
    assert_not_contains(
        podfile,
        ["target 'ShellProject' do", "inhibit_all_warnings!", "IPHONEOS_DEPLOYMENT_TARGET"],
        "Native iOS project/target and Pod setting isolation",
    )

    ambiguous_target = work / "native_ios_ambiguous_target"
    ambiguous_source = work / "native_ios_ambiguous_source"
    create_native_ios_target(ambiguous_target)
    shutil.rmtree(ambiguous_target / "NativeIosFixture.xcodeproj" / "xcshareddata")
    project_file = ambiguous_target / "NativeIosFixture.xcodeproj" / "project.pbxproj"
    project_text = read(project_file).replace(
        "/* End PBXNativeTarget section */",
        """		555555555555555555555555 /* AlternateApp */ = {
			isa = PBXNativeTarget;
			buildConfigurationList = 666666666666666666666666 /* Build configuration list for PBXNativeTarget "AlternateApp" */;
			name = AlternateApp;
			productName = AlternateApp;
			productType = "com.apple.product-type.application";
		};
/* End PBXNativeTarget section */""",
    )
    write(project_file, project_text)
    write(
        ambiguous_target / "Podfile",
        """platform :ios, '12.0'
target 'NativeIosFixture' do
end
target 'AlternateApp' do
end
""",
    )
    ambiguous_package = create_native_ios_package(ambiguous_source)
    failure = run_integration_failure(
        ambiguous_target,
        "native-ios",
        ambiguous_package,
    )
    assert_contains(
        failure,
        [
            "Multiple native iOS application targets",
            "`AlternateApp`",
            "`NativeIosFixture`",
            "--ios-target",
        ],
        "Native iOS ambiguous target rejection",
    )
    if (ambiguous_target / "vendor").exists():
        raise AssertionError("Native iOS ambiguous target failure must occur before SDK files are written")

    ambiguous_scheme_target = work / "native_ios_ambiguous_scheme"
    ambiguous_scheme_source = work / "native_ios_ambiguous_scheme_source"
    create_native_ios_target(
        ambiguous_scheme_target,
        scheme_name="ProductionApp",
    )
    original_scheme = read(
        ambiguous_scheme_target
        / "NativeIosFixture.xcodeproj"
        / "xcshareddata"
        / "xcschemes"
        / "ProductionApp.xcscheme"
    )
    write(
        ambiguous_scheme_target
        / "NativeIosFixture.xcodeproj"
        / "xcshareddata"
        / "xcschemes"
        / "AlternateProduction.xcscheme",
        original_scheme,
    )
    ambiguous_scheme_package = create_native_ios_package(ambiguous_scheme_source)
    scheme_failure = run_integration_failure(
        ambiguous_scheme_target,
        "native-ios",
        ambiguous_scheme_package,
    )
    assert_contains(
        scheme_failure,
        [
            "Could not uniquely infer the native iOS app target from shared schemes",
            "`AlternateProduction`",
            "`ProductionApp`",
        ],
        "Native iOS ambiguous scheme rejection",
    )
    if (ambiguous_scheme_target / "vendor").exists():
        raise AssertionError("Native iOS ambiguous scheme failure must occur before SDK files are written")

    ambiguous_workspace_target = work / "native_ios_ambiguous_workspace"
    ambiguous_workspace_source = work / "native_ios_ambiguous_workspace_source"
    create_native_ios_target(
        ambiguous_workspace_target,
        scheme_name="ProductionApp",
    )
    for workspace_name in ("CustomerA.xcworkspace", "CustomerB.xcworkspace"):
        write(
            ambiguous_workspace_target / workspace_name / "contents.xcworkspacedata",
            '<?xml version="1.0" encoding="UTF-8"?><Workspace version="1.0"></Workspace>\n',
        )
    ambiguous_workspace_package = create_native_ios_package(ambiguous_workspace_source)
    workspace_failure = run_integration_failure(
        ambiguous_workspace_target,
        "native-ios",
        ambiguous_workspace_package,
    )
    assert_contains(
        workspace_failure,
        [
            "Could not uniquely map target `NativeIosFixture` to an Xcode workspace",
            "`CustomerA.xcworkspace`",
            "`CustomerB.xcworkspace`",
        ],
        "Native iOS ambiguous workspace rejection",
    )
    if (ambiguous_workspace_target / "vendor").exists():
        raise AssertionError("Native iOS ambiguous workspace failure must occur before SDK files are written")


def validate_native_ios_unknown_autocut_draft_api(work: Path) -> None:
    target = work / "native_ios_unknown_autocut_draft_target"
    source = work / "native_ios_unknown_autocut_draft_source"
    create_native_ios_target(target)
    package = create_native_ios_package(source, include_autocut_draft_api=False)
    output = run_integration(target, "native-ios", package)
    assert_contains(
        output,
        [
            "Native iOS AutoCut draft fallback was not applied",
            "does not expose the verified project-manager and Swift timeline API shapes",
            "Preserve `hasDraft` behavior and verify this SDK version manually",
        ],
        "Native iOS unknown AutoCut draft API guard",
    )
    run_integration_apply(target, "native-ios", package)
    publish = (target / "MeisheShortVideo" / "MeisheShortVideoPublishViewController.swift").read_text(
        encoding="utf-8"
    )
    assert_contains(
        publish,
        ["saveDraftButton.isHidden = !hasDraft", "moduleManager.saveCurrentDraft(withDraftInfo: draftInput.text)"],
        "Native iOS unknown-version conservative draft behavior",
    )
    assert_not_contains(
        publish,
        ["NvProjectManager.storeCurrentProject(", "NvModuleManager.projectInfoForProject(projectId)"],
        "Native iOS unknown-version patch isolation",
    )


def validate_native_ios_customer_identity(work: Path) -> None:
    target = work / "native_ios_customer_target"
    source = work / "native_ios_customer_source"
    create_native_ios_target(
        target,
        bundle_identifier="com.customer.shortvideo",
        include_podfile=False,
    )
    package = create_native_ios_package(source)
    output = run_integration(target, "native-ios", package)
    assert_contains(
        output,
        [
            "Native iOS app target Bundle Identifier is `com.customer.shortvideo`",
            "official Demo material service requires the exact Bundle Identifier",
            "`--ios-bundle-identifier com.meishe.duanshipindemo`",
            "customer server, matching License, and service allowlist",
            "global NSAllowsArbitraryLoads was not enabled for a customer Bundle Identifier",
            "Generated native iOS material-request self-check handoff",
        ],
        "Native iOS customer identity",
    )
    run_integration_apply(target, "native-ios", package)
    generated_podfile = (target / "Podfile").read_text(encoding="utf-8")
    assert_contains(
        generated_podfile,
        [
            "platform :ios, '12.0'",
            "use_frameworks!",
            "pod 'NvShortVideoEdit',    :path => './vendor/meishe/Pods-NvShortVideoEdit', :inhibit_warnings => true",
        ],
        "Native iOS newly generated Podfile",
    )
    assert_not_contains(
        generated_podfile,
        ["https://github.com/CocoaPods/Specs.git"],
        "Native iOS generated Podfile CDN behavior",
    )
    with (target / "NativeIosFixture" / "Info.plist").open("rb") as fh:
        info_plist = plistlib.load(fh)
    if info_plist.get("NSAppTransportSecurity", {}).get("NSAllowsArbitraryLoads") is True:
        raise AssertionError("Native iOS customer fixture must not enable global NSAllowsArbitraryLoads")
    project_text = read(target / "NativeIosFixture.xcodeproj" / "project.pbxproj")
    assert_contains(
        project_text,
        [
            "PRODUCT_BUNDLE_IDENTIFIER = com.customer.shortvideo;",
            "PRODUCT_BUNDLE_IDENTIFIER = com.customer.shortvideo.tests;",
        ],
        "Native iOS existing customer identity preservation",
    )
    assert_not_contains(
        project_text,
        ["PRODUCT_BUNDLE_IDENTIFIER = com.meishe.duanshipindemo;"],
        "Native iOS existing customer identity must not change silently",
    )


def validate_native_ios_explicit_bundle_identifier(work: Path) -> None:
    target = work / "native_ios_explicit_identity_target"
    source = work / "native_ios_explicit_identity_source"
    create_native_ios_target(target, bundle_identifier="com.customer.shortvideo")
    package = create_native_ios_package(source)
    args = ["--ios-bundle-identifier", "com.meishe.duanshipindemo"]
    output = run_integration(target, "native-ios", package, args)
    assert_contains(
        output,
        [
            "Set native iOS app target `NativeIosFixture` Bundle Identifier to `com.meishe.duanshipindemo`",
            "Native iOS Bundle Identifier: `com.meishe.duanshipindemo`",
            "Native iOS official-Demo compatibility",
        ],
        "Native iOS explicit Demo identity dry-run",
    )
    run_integration_apply(target, "native-ios", package, args)
    project_text = read(target / "NativeIosFixture.xcodeproj" / "project.pbxproj")
    if project_text.count("PRODUCT_BUNDLE_IDENTIFIER = com.meishe.duanshipindemo;") != 2:
        raise AssertionError(
            "Native iOS explicit Bundle Identifier must update every app target build configuration"
        )
    assert_contains(
        project_text,
        ["PRODUCT_BUNDLE_IDENTIFIER = com.customer.shortvideo.tests;"],
        "Native iOS test target identity preservation",
    )
    assert_not_contains(
        project_text,
        ["PRODUCT_BUNDLE_IDENTIFIER = com.meishe.duanshipindemo.tests;"],
        "Native iOS explicit identity target isolation",
    )
    with (target / "NativeIosFixture" / "Info.plist").open("rb") as fh:
        info_plist = plistlib.load(fh)
    if info_plist.get("NSAppTransportSecurity", {}).get("NSAllowsArbitraryLoads") is not True:
        raise AssertionError("Native iOS explicit official Demo identity must enable verified temporary ATS")

def validate_native_ios_missing_package(work: Path) -> None:
    target = work / "native_ios_target_missing"
    source = work / "native_ios_source_missing"
    create_native_ios_target(target)
    write(source / "native" / "ios" / "Pods-NvShortVideoEdit" / "README.txt", "missing podspec\n")
    output = run_integration_failure(target, "native-ios", source)
    assert_contains(
        output,
        [
            "Could not find a valid `Pods-NvShortVideoEdit` package",
            "Validation failures:",
            "Expected `Pods-NvShortVideoEdit/NvShortVideoEdit.podspec`",
            "缺少 native iOS 接入必需的 Pods-NvShortVideoEdit 本地 CocoaPods 包",
            "https://www.meishesdk.com/developers",
            "iOS App vX.x.x",
            "native/ios/Pods-NvShortVideoEdit",
        ],
        "Native iOS missing package",
    )
