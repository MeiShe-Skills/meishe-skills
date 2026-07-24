"""Standalone skill-structure and route-isolation validation."""

from __future__ import annotations

import ast
import re
from pathlib import Path

from meishe_docking_core import Report

from .shared import assert_contains, assert_not_contains, fail, read, run, run_failure


def validate_skill_structure(
    *,
    route_module: str,
    capability_track: str,
    entry_script: str,
    docs_track: str,
    platforms: tuple[str, ...],
    route_references: tuple[str, ...],
) -> None:
    skill_root = Path(__file__).resolve().parents[2]
    scripts_root = skill_root / "scripts"

    if any(path.is_symlink() for path in skill_root.rglob("*")):
        fail("Standalone skills must not contain symlinks")
    if len([path for path in (skill_root / "assets" / "shortvideo-docs").rglob("*") if path.is_file()]) != 50:
        fail("The complete enhanced official documentation asset set was not preserved")
    required_demo_assets = {
        "meishe_home_banner.jpg",
        "icons/meishe_icon_capture.png",
        "icons/meishe_icon_dual_capture.png",
        "icons/meishe_icon_edit.png",
        "icons/meishe_icon_draft.png",
        "icons/meishe_icon_capture.svg",
        "icons/meishe_icon_dual_capture.svg",
        "icons/meishe_icon_edit.svg",
        "icons/meishe_icon_draft.svg",
    }
    actual_demo_assets = {
        path.relative_to(skill_root / "assets" / "demo-ui").as_posix()
        for path in (skill_root / "assets" / "demo-ui").rglob("*")
        if path.is_file()
    }
    if actual_demo_assets != required_demo_assets:
        fail("Demo UI asset inventory drifted")

    route_dirs = {path.name for path in (scripts_root / "routes").iterdir() if path.is_dir() and path.name != "__pycache__"}
    if route_dirs != {route_module}:
        fail(f"Expected only routes/{route_module}, got {sorted(route_dirs)}")
    integration_entries = {path.name for path in scripts_root.glob("integrate_*.py")}
    if integration_entries != {entry_script}:
        fail(f"Foreign integration entry found: {sorted(integration_entries)}")
    catalog_files = {path.name for path in (skill_root / "references" / "config-capabilities").glob("*.json")}
    if catalog_files != {"schema.json", f"{capability_track}.json"}:
        fail(f"Foreign capability catalog found: {sorted(catalog_files)}")

    required_paths = [
        skill_root / "SKILL.md",
        skill_root / "agents" / "openai.yaml",
        scripts_root / entry_script,
        scripts_root / "meishe_docking_core.py",
        scripts_root / "query_feature_config.py",
        scripts_root / "query_shortvideo_docs.py",
        scripts_root / "build_shortvideo_doc_assets.py",
        skill_root / "references" / "config-capabilities" / "schema.json",
        skill_root / "references" / "config-capabilities" / f"{capability_track}.json",
        *[skill_root / reference for reference in route_references],
    ]
    for path in required_paths:
        if not path.exists():
            fail(f"Required standalone skill file missing: {path}")

    skill_text = read(skill_root / "SKILL.md")
    assert_contains(
        skill_text,
        [
            "修改本 skill 前",
            "获得明确同意后才能写入",
            "默认不控制",
            "依赖、构建或设备操作边界",
            "自动发现只搜索 `--target-root`",
            "meishe_configuration_handoff.md",
            "meishe_docking_report.md",
            "配置修改与生效",
            "`用户执行`",
            "`自动执行`",
            "额外消耗 Token 和时间",
            "不得改为直接索要权限",
            "最终可见回复",
            "折叠的“处理中”区域",
            "不能用于运行或验收",
        ],
        "standalone SKILL.md policy",
    )
    assert_not_contains(
        skill_text,
        ["授权代执行", "单独申请授权", "未经用户单独授权"],
        "standalone execution-mode wording",
    )
    dependency_text = read(skill_root / "references" / "dependency-installation.md")
    assert_contains(
        dependency_text,
        [
            "最终可见回复",
            "不得只放在折叠的“处理中”区域",
            "不得写“命令见上文/报告”",
            "`自动执行` 也要先展示同一份命令清单",
            "## 真机运行",
            "虚拟设备不受支持",
        ],
        "visible execution commands and real-device policy",
    )
    dependency_expectations = {
        "react-native": ("adb devices", "xcrun devicectl list devices", "npm run android", "npm run ios"),
        "flutter": ("flutter devices", "flutter run -d <ANDROID_DEVICE_ID>", "flutter run -d <IOS_DEVICE_ID>"),
        "native-ios": ("xcrun devicectl list devices", "Product > Run", "iOS Simulator"),
        "native-android": ("adb devices", "./gradlew :app:installDebug", "Android Emulator"),
    }
    assert_contains(
        dependency_text,
        dependency_expectations[capability_track],
        "route-specific physical-device commands",
    )
    if "ios" in platforms:
        assert_contains(
            skill_text,
            [
                "当前任务新建",
                "--ios-bundle-identifier com.meishe.duanshipindemo",
                "官方服务请求无法走通",
                "客户服务器、匹配 License 和服务白名单",
            ],
            "standalone iOS official-service identity policy",
        )
    core_text = read(scripts_root / "meishe_docking_core.py")
    skill_name_match = re.search(r"^name:\s*([A-Za-z0-9_-]+)\s*$", skill_text, re.M)
    if not skill_name_match:
        fail("Standalone SKILL.md frontmatter must declare a valid name")
    declared_skill_name = skill_name_match.group(1)
    assert_contains(
        core_text,
        [f'SKILL_NAME = "{declared_skill_name}"'],
        "standalone report skill identity",
    )
    forbidden_core_terms = {
        "native-android": (
            "def add_cocoapods_dependency_step(",
            "def detect_node_install_command(",
            "class TargetPlatforms",
            "iOS Quick Verify",
            "RN iOS",
        ),
        "native-ios": (
            "def add_android_gradle_dependency_step(",
            "def detect_node_install_command(",
            "class TargetPlatforms",
        ),
        "react-native": ("FIXED_PLATFORM = \"flutter\"",),
        "flutter": ("def detect_node_install_command(", "FIXED_PLATFORM = \"react-native\""),
    }
    assert_not_contains(
        core_text,
        forbidden_core_terms[capability_track],
        "route-specific shared core",
    )
    core_tree = ast.parse(core_text)
    definitions = {
        node.name: node
        for node in core_tree.body
        if isinstance(node, (ast.FunctionDef, ast.ClassDef))
    }
    imported_core_names: set[str] = {"main"}
    for path in scripts_root.rglob("*.py"):
        if path.name == "meishe_docking_core.py":
            continue
        tree = ast.parse(read(path), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "meishe_docking_core":
                imported_core_names.update(alias.name for alias in node.names)
    reachable: set[str] = set()
    pending = list(imported_core_names)
    while pending:
        name = pending.pop()
        if name in reachable or name not in definitions:
            continue
        reachable.add(name)
        pending.extend(
            node.id
            for node in ast.walk(definitions[name])
            if isinstance(node, ast.Name) and node.id in definitions
        )
    unreachable = sorted(set(definitions) - reachable)
    if unreachable:
        fail(f"Shared core contains unreachable route logic: {unreachable}")

    link_pattern = re.compile(r"references/[A-Za-z0-9_./-]+\.md")
    for path in (skill_root / "references").rglob("*.md"):
        for link in link_pattern.findall(read(path)):
            if not (skill_root / link).is_file():
                fail(f"Broken reference link in {path}: {link}")

    allowed_route_prefix = f"routes.{route_module}"
    for path in scripts_root.rglob("*.py"):
        source = read(path)
        if " | " in source and "from __future__ import annotations" not in source:
            fail(f"Python 3.9-compatible postponed annotations missing: {path}")
        tree = ast.parse(source, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and any(alias.name == "*" for alias in node.names):
                fail(f"Wildcard import is forbidden: {path}")
            modules: list[str] = []
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                modules = [node.module]
            for module in modules:
                if module == "routes" or module.startswith("routes."):
                    if module != allowed_route_prefix and not module.startswith(allowed_route_prefix + "."):
                        fail(f"Cross-route import found in {path}: {module}")

    assert_not_contains(
        core_text,
        ["def detect_platform(", "integrate_meishe_duanshipin.py"],
        "fixed-route core",
    )
    dry_report = Report(target_root=skill_root, platform=capability_track, dry_run=True)
    dry_report.add_change("fixture planned change")
    dry_report.backups.append("fixture planned backup")
    dry_markdown = dry_report.to_markdown()
    assert_contains(dry_markdown, ["## Planned Changes", "## Planned Backups"], "dry-run report semantics")
    assert_not_contains(
        dry_markdown,
        ["Replace every placeholder before production use."],
        "dry-run report without placeholders",
    )
    doc_builder_text = read(scripts_root / "build_shortvideo_doc_assets.py")
    assert_contains(
        doc_builder_text,
        ["--source-doc-root", "required=True", "Standalone skills keep route-scoped references"],
        "standalone documentation builder",
    )
    assert_not_contains(
        doc_builder_text,
        [
            "workspace_root = skill_root.parent.parent.parent",
            'write_doc_map_md(references_root / "doc-map.md"',
            'write_android_source_summary(references_root / "android-source-config-summary.md"',
        ],
        "standalone documentation builder",
    )
    all_non_asset_text = "\n".join(
        read(path)
        for root in (skill_root / "scripts", skill_root / "references")
        for path in root.rglob("*")
        if path.is_file() and path.suffix in {".py", ".md", ".json"}
    )
    assert_not_contains(
        all_non_asset_text,
        ["/Users/" + "mswebedit/proejct/", "meishe-android" + "-duanshipin-docking/"],
        "standalone path isolation",
    )

    entry = scripts_root / entry_script
    guard = run_failure([str(entry), "--platform", capability_track], "fixed entrypoint --platform rejection")
    assert_contains(guard, ["do not pass --platform"], "fixed entrypoint guard")

    docs_query = scripts_root / "query_shortvideo_docs.py"
    for platform in platforms:
        output = run(
            [str(docs_query), "--track", docs_track, "--platform", platform, "--language", "zh"],
            f"{docs_track}/{platform} documentation query",
        )
        expected_query_text = ["Selected route references:"]
        if docs_track in {"react-native", "flutter"}:
            expected_query_text.append("selected platform section:")
        else:
            expected_query_text.append("native-quickstart")
        assert_contains(output, expected_query_text, "route documentation query")

    foreign_track = "flutter" if docs_track != "flutter" else "react-native"
    run_failure(
        [str(docs_query), "--track", foreign_track, "--platform", platforms[0], "--language", "zh"],
        "foreign documentation track rejection",
    )
