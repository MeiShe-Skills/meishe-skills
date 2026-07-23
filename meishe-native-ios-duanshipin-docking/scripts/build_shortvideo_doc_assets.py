#!/usr/bin/env python3
"""Build agent-ready ShortVideo documentation assets for the skill.

The source of truth is ShortVideo/doc/markdown. This script enhances the
Markdown files in place, copies the complete markdown tree into the skill
assets, and writes machine-readable indexes for platform/track lookup.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


MARKER = "<!-- MEISHE_AGENT_DOC_ENHANCED: v1 -->"
QUICK_BEGIN = "<!-- BEGIN MEISHE_AGENT_QUICK_INDEX -->"
QUICK_END = "<!-- END MEISHE_AGENT_QUICK_INDEX -->"
HINT_BEGIN = "<!-- BEGIN MEISHE_AGENT_SECTION_HINT -->"
HINT_END = "<!-- END MEISHE_AGENT_SECTION_HINT -->"
IMAGE_INDEX_BEGIN = "<!-- BEGIN MEISHE_AGENT_IMAGE_INDEX -->"
IMAGE_INDEX_END = "<!-- END MEISHE_AGENT_IMAGE_INDEX -->"

ACTION_TERMS_ZH = (
    "添加",
    "修改",
    "执行",
    "更新",
    "创建",
    "复制",
    "拷贝",
    "下载",
    "配置",
    "运行",
    "替换",
    "放到",
    "集成",
    "安装",
    "申请",
    "授权",
    "权限",
    "依赖",
    "引入",
    "解压",
)
ACTION_TERMS_EN = (
    "add",
    "modify",
    "run",
    "update",
    "create",
    "copy",
    "download",
    "configure",
    "replace",
    "install",
    "permission",
    "dependency",
    "extract",
)
IMPORTANT_TERMS_ZH = ("注意", "重要", "说明", "提示", "必须", "需要")
IMPORTANT_TERMS_EN = ("note", "important", "warning", "must", "required")

PARAMETERS = (
    "host",
    "assetRequestUrl",
    "assetCategoryUrl",
    "assetMusiciansUrl",
    "assetFontUrl",
    "assetDownloadUrl",
    "assetPrefabricatedUrl",
    "assetAutoCutUrl",
    "assetTagUrl",
    "clientId",
    "clientSecret",
    "assemblyId",
    "isAbroad",
    "meishesdk.lic",
    "NvModuleManager",
    "NvVideoConfig",
    "NvCaptureConfig",
    "NvCompileConfig",
    "NvEditConfig",
    "NvWatermarkConfig",
    "downloadPrefabricatedMaterial",
    "openCapture",
    "openEdit",
    "startDualCapture",
    "openDraftActivity",
    "configServerInfo",
    "startVideoCapture",
    "startVideoDualCapture",
    "startSelectFilesForEdit",
    "pubspec.yaml",
    "Podfile",
    "yarn add",
    "pod install",
    "Info.plist",
    "AndroidManifest.xml",
    "build.gradle",
)


@dataclass
class ImageInfo:
    doc_rel: str
    alt: str
    raw_path: str
    normalized_path: str
    exists: bool
    width: int | None = None
    height: int | None = None
    sha256: str | None = None
    inferred_use: str = ""


@dataclass
class DocInfo:
    doc_id: str
    source_rel: str
    asset_rel: str
    title: str
    language: str
    track: str
    platforms: list[str]
    tags: list[str]
    headings: list[dict[str, object]] = field(default_factory=list)
    images: list[ImageInfo] = field(default_factory=list)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-doc-root",
        required=True,
        type=Path,
        help="Explicit path to the official ShortVideo/doc/markdown source tree.",
    )
    return parser.parse_args()


def default_paths(source_doc_root: Path) -> tuple[Path, Path, Path]:
    script_path = Path(__file__).resolve()
    skill_root = script_path.parents[1]
    asset_root = skill_root / "assets" / "shortvideo-docs"
    references_root = skill_root / "references"
    return source_doc_root.expanduser().resolve(), asset_root, references_root


def remove_generated_blocks(text: str) -> str:
    for begin, end in (
        (QUICK_BEGIN, QUICK_END),
        (HINT_BEGIN, HINT_END),
        (IMAGE_INDEX_BEGIN, IMAGE_INDEX_END),
    ):
        pattern = re.compile(
            rf"\n?{re.escape(begin)}.*?{re.escape(end)}\n?",
            re.DOTALL,
        )
        text = pattern.sub("\n", text)
    text = text.replace(MARKER + "\n", "").replace("\n" + MARKER, "")
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("> **图片解析：**") or stripped.startswith("> **Image parse:**"):
            continue
        lines.append(line)
    return "\n".join(lines).strip() + "\n"


def split_frontmatter(lines: list[str]) -> tuple[list[str], list[str]]:
    if not lines or lines[0].strip() != "---":
        return [], lines
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            return lines[: idx + 1], lines[idx + 1 :]
    return [], lines


def language_from_rel(rel: Path) -> str:
    rel_text = rel.as_posix().lower()
    if "/doc_en/" in rel_text or rel_text.endswith("_en.md"):
        return "en"
    return "zh"


def infer_profile(rel: Path, title: str) -> tuple[str, list[str], list[str]]:
    rel_text = rel.as_posix()
    lower = rel_text.lower()
    if "flutter_quickstart" in lower:
        return (
            "flutter",
            ["android", "ios"],
            ["quickstart", "integration", "flutter", "android", "ios", "local-plugin", "permission", "license", "server-config"],
        )
    if "react_native_quickstart" in lower:
        return (
            "react-native",
            ["android", "ios"],
            ["quickstart", "integration", "react-native", "android", "ios", "local-plugin", "yarn", "permission", "license", "server-config"],
        )
    if "functionconfiguration" in lower:
        return (
            "shared",
            ["android", "ios"],
            ["function-config", "capture", "edit", "compile", "publish", "ui-config", "native", "flutter", "react-native"],
        )
    if "prefabricatedmaterial" in lower:
        return (
            "shared",
            ["android", "ios"],
            ["prefabricated-material", "download", "server-config", "native", "flutter", "react-native"],
        )
    if "quickstart_android" in lower:
        return (
            "native",
            ["android"],
            ["quickstart", "integration", "native-android", "aar", "gradle", "manifest", "permission", "license", "server-config"],
        )
    if "native_quickstart" in lower:
        return (
            "native",
            ["ios"],
            ["quickstart", "integration", "native-ios", "cocoapods", "podfile", "info.plist", "permission", "license", "server-config"],
        )
    return ("unknown", [], ["documentation"])


def doc_id_from_rel(rel: Path) -> str:
    stem = rel.with_suffix("").as_posix()
    return re.sub(r"[^a-zA-Z0-9]+", "-", stem).strip("-").lower()


def detect_title(lines: Iterable[str], fallback: str) -> str:
    for line in lines:
        match = re.match(r"^\s*#\s+(.+?)\s*$", line)
        if match:
            return match.group(1)
    return fallback


def detect_headings(lines: list[str]) -> list[dict[str, object]]:
    headings = []
    for idx, line in enumerate(lines, start=1):
        match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if match:
            headings.append(
                {
                    "line": idx,
                    "level": len(match.group(1)),
                    "title": match.group(2).strip(),
                    "tags": sorted(section_tags(match.group(2))),
                }
            )
    return headings


def png_size(path: Path) -> tuple[int | None, int | None]:
    try:
        data = path.read_bytes()
    except OSError:
        return None, None
    if not data.startswith(b"\x89PNG\r\n\x1a\n") or len(data) < 24:
        return None, None
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def sha256(path: Path) -> str | None:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return None


def infer_image_use(path_text: str, section: str, alt: str) -> str:
    combined = f"{path_text} {section} {alt}".lower()
    if "lic" in combined or "license" in combined or "授权" in combined:
        return "license file placement or authorization UI reference"
    if "compile" in combined or "编译" in combined:
        return "Android build issue and resolution reference"
    if "android_image" in combined or "android" in combined:
        return "Native Android project setup or Android resource location"
    if "pod" in combined or "ios" in combined:
        return "iOS CocoaPods or project setup reference"
    if "image-20240523192520742" in combined:
        return "configuration screenshot used by quickstart"
    if "image-20240523191815764" in combined:
        return "configuration screenshot used by Flutter quickstart"
    return "step screenshot; inspect near the preceding heading before editing"


def extract_images(doc_path: Path, rel: Path, lines: list[str]) -> list[ImageInfo]:
    images: list[ImageInfo] = []
    section = ""
    for line in lines:
        heading = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if heading:
            section = heading.group(2).strip()
        for match in re.finditer(r"!\[([^\]]*)\]\(([^)]+)\)", line):
            alt = match.group(1)
            raw_path = match.group(2).strip()
            normalized = raw_path.split("#", 1)[0].split("?", 1)[0]
            image_path = (doc_path.parent / normalized).resolve()
            width, height = png_size(image_path)
            images.append(
                ImageInfo(
                    doc_rel=rel.as_posix(),
                    alt=alt,
                    raw_path=raw_path,
                    normalized_path=(rel.parent / normalized).as_posix(),
                    exists=image_path.exists(),
                    width=width,
                    height=height,
                    sha256=sha256(image_path) if image_path.exists() else None,
                    inferred_use=infer_image_use(raw_path, section, alt),
                )
            )
    return images


def section_tags(text: str) -> set[str]:
    lower = text.lower()
    tags: set[str] = set()
    if any(token in text for token in ("集成", "接入", "工程", "项目")) or any(token in lower for token in ("integrat", "project", "quick")):
        tags.add("integration")
    if any(token in text for token in ("权限", "隐私")) or "permission" in lower:
        tags.add("permission")
    if any(token in text for token in ("授权", "lic", "License")) or "license" in lower:
        tags.add("license")
    if any(token in text for token in ("服务器", "接口", "请求", "路径", "参数")) or any(token in lower for token in ("server", "request", "config", "parameter")):
        tags.add("server-config")
    if any(token in text for token in ("素材", "预制")) or "material" in lower:
        tags.add("prefabricated-material")
    if any(token in text for token in ("功能", "拍摄", "编辑", "合拍", "草稿", "发布")) or any(token in lower for token in ("capture", "edit", "dual", "draft", "publish", "function")):
        tags.add("function-config")
    if any(token in text for token in ("依赖", "aar", "gradle", "pod", "pubspec", "yarn")) or any(token in lower for token in ("dependency", "gradle", "pod", "pubspec", "yarn", "aar")):
        tags.add("dependency")
    if any(token in text for token in ("编译", "运行", "报错")) or any(token in lower for token in ("build", "compile", "run", "error")):
        tags.add("build")
    return tags


def should_bold_step(content: str) -> bool:
    stripped = content.strip()
    if not stripped or stripped.startswith("**") or stripped.startswith("!["):
        return False
    lower = stripped.lower()
    return any(term in stripped for term in ACTION_TERMS_ZH) or any(term in lower for term in ACTION_TERMS_EN)


def bold_key_parameters(line: str) -> str:
    if not line.strip() or line.lstrip().startswith("|"):
        return line
    result = line
    for param in sorted(PARAMETERS, key=len, reverse=True):
        pattern = re.compile(rf"(?<![\w*`])({re.escape(param)})(?![\w*`])")
        result = pattern.sub(r"**\1**", result)
    return result


def enhance_line(line: str, in_code: bool) -> str:
    if in_code:
        return line
    line = bold_key_parameters(line)
    list_match = re.match(r"^(\s*(?:[-*+]\s+|\d+\.\s+))(.*)$", line)
    if list_match and should_bold_step(list_match.group(2)):
        return f"{list_match.group(1)}**{list_match.group(2).strip()}**"
    stripped = line.strip()
    lower = stripped.lower().lstrip("> ").strip()
    if stripped and not stripped.startswith("**"):
        if any(stripped.startswith(term) for term in IMPORTANT_TERMS_ZH) or any(lower.startswith(term) for term in IMPORTANT_TERMS_EN):
            prefix = line[: len(line) - len(line.lstrip())]
            return f"{prefix}**{line.strip()}**"
    return line


def quick_index_block(doc: DocInfo) -> list[str]:
    if doc.language == "zh":
        return [
            QUICK_BEGIN,
            "> **Agent 快速索引**",
            f"> - **Doc ID**: `{doc.doc_id}`",
            f"> - **语言轨道**: `{doc.track}`",
            f"> - **平台**: `{', '.join(doc.platforms)}`",
            f"> - **标签**: `{', '.join(doc.tags)}`",
            f"> - **图片数**: `{len(doc.images)}`",
            "> - **用法**: 先按标签定位章节，再读取相邻步骤、配置表和图片解析；不要跳过本页内的注意事项。",
            QUICK_END,
            "",
        ]
    return [
        QUICK_BEGIN,
        "> **Agent Quick Index**",
        f"> - **Doc ID**: `{doc.doc_id}`",
        f"> - **Track**: `{doc.track}`",
        f"> - **Platforms**: `{', '.join(doc.platforms)}`",
        f"> - **Tags**: `{', '.join(doc.tags)}`",
        f"> - **Image count**: `{len(doc.images)}`",
        "> - **Usage**: Locate sections by tags first, then read adjacent steps, config tables, and image notes.",
        QUICK_END,
        "",
    ]


def section_hint_block(tags: set[str], language: str) -> list[str]:
    if not tags:
        return []
    tag_text = ", ".join(sorted(tags))
    if language == "zh":
        hint = f"> **Agent 索引提示：** 本节标签 `{tag_text}`。接入执行时优先核对本节步骤、配置项、路径和权限要求。"
    else:
        hint = f"> **Agent section hint:** tags `{tag_text}`. Check steps, config values, paths, and permission requirements before editing."
    return [HINT_BEGIN, hint, HINT_END]


def image_parse_line(image: ImageInfo, language: str) -> str:
    size = f"{image.width}x{image.height}" if image.width and image.height else "unknown"
    if language == "zh":
        return f"> **图片解析：** `path={image.raw_path}`，`size={size}`，用途：{zh_image_use(image.inferred_use)}。"
    return f"> **Image parse:** `path={image.raw_path}`, `size={size}`, use: {image.inferred_use}."


def zh_image_use(inferred_use: str) -> str:
    mapping = {
        "license file placement or authorization UI reference": "授权文件放置位置或授权流程界面参考",
        "Android build issue and resolution reference": "Android 编译问题与解决方式参考",
        "Native Android project setup or Android resource location": "原生 Android 工程配置或资源位置参考",
        "iOS CocoaPods or project setup reference": "iOS CocoaPods 或工程配置参考",
        "configuration screenshot used by quickstart": "快速接入配置截图参考",
        "configuration screenshot used by Flutter quickstart": "Flutter 快速接入配置截图参考",
        "step screenshot; inspect near the preceding heading before editing": "步骤截图；执行前结合上一标题和相邻文字确认路径与配置",
    }
    return mapping.get(inferred_use, inferred_use)


def image_index_block(doc: DocInfo) -> list[str]:
    if not doc.images:
        return []
    title = "## Agent 图片索引" if doc.language == "zh" else "## Agent Image Index"
    lines = [IMAGE_INDEX_BEGIN, title, "", "| Image | Size | Exists | Inferred use |", "| --- | --- | --- | --- |"]
    for image in doc.images:
        size = f"{image.width}x{image.height}" if image.width and image.height else "unknown"
        inferred_use = zh_image_use(image.inferred_use) if doc.language == "zh" else image.inferred_use
        lines.append(
            f"| `{image.raw_path}` | `{size}` | `{str(image.exists).lower()}` | {inferred_use} |"
        )
    lines.extend([IMAGE_INDEX_END, ""])
    return lines


def enhance_markdown(doc_path: Path, source_root: Path) -> DocInfo:
    rel = doc_path.relative_to(source_root)
    original = doc_path.read_text(encoding="utf-8")
    stripped = remove_generated_blocks(original)
    raw_lines = stripped.splitlines()
    frontmatter, body = split_frontmatter(raw_lines)
    title = detect_title(body, rel.stem)
    track, platforms, tags = infer_profile(rel, title)
    images = extract_images(doc_path, rel, body)
    doc = DocInfo(
        doc_id=doc_id_from_rel(rel),
        source_rel=rel.as_posix(),
        asset_rel=f"markdown/{rel.as_posix()}",
        title=title,
        language=language_from_rel(rel),
        track=track,
        platforms=platforms,
        tags=tags,
        images=images,
    )

    result: list[str] = []
    result.extend(frontmatter)
    if frontmatter:
        result.append("")
    result.append(MARKER)

    in_code = False
    quick_inserted = False
    image_cursor = 0
    for line in body:
        if line.strip().startswith("```"):
            in_code = not in_code
            result.append(line)
            continue
        heading = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if heading and not in_code:
            result.append(line)
            level = len(heading.group(1))
            if level == 1 and not quick_inserted:
                result.extend(["", *quick_index_block(doc)])
                quick_inserted = True
            elif level > 1:
                hint = section_hint_block(section_tags(heading.group(2)), doc.language)
                if hint:
                    result.extend(["", *hint])
            continue

        enhanced = enhance_line(line, in_code)
        result.append(enhanced)
        if not in_code and "!" in line:
            image_matches = list(re.finditer(r"!\[([^\]]*)\]\(([^)]+)\)", line))
            for _ in image_matches:
                if image_cursor < len(images):
                    result.append(image_parse_line(images[image_cursor], doc.language))
                    image_cursor += 1

    if not quick_inserted:
        result[1:1] = quick_index_block(doc)
    result.extend(["", *image_index_block(doc)])
    with doc_path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(result).rstrip() + "\n")
    enhanced_lines = result
    doc.headings = detect_headings(enhanced_lines)
    return doc


def copy_asset_tree(source_doc_root: Path, asset_root: Path) -> Path:
    markdown_asset_root = asset_root / "markdown"
    if markdown_asset_root.exists():
        if asset_root.resolve() not in markdown_asset_root.resolve().parents:
            raise RuntimeError(f"Refusing to remove unexpected path: {markdown_asset_root}")
        shutil.rmtree(markdown_asset_root)
    shutil.copytree(source_doc_root, markdown_asset_root)
    return markdown_asset_root


def all_image_assets(source_doc_root: Path, docs: list[DocInfo]) -> list[dict[str, object]]:
    referenced: dict[str, list[str]] = {}
    for doc in docs:
        for image in doc.images:
            referenced.setdefault(image.normalized_path, []).append(doc.source_rel)

    assets = []
    for path in sorted(source_doc_root.rglob("*")):
        if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
            continue
        rel = path.relative_to(source_doc_root).as_posix()
        width, height = png_size(path)
        assets.append(
            {
                "path": rel,
                "asset_path": f"markdown/{rel}",
                "width": width,
                "height": height,
                "sha256": sha256(path),
                "referenced_by": sorted(set(referenced.get(rel, []))),
            }
        )
    return assets


def doc_to_json(doc: DocInfo) -> dict[str, object]:
    return {
        "doc_id": doc.doc_id,
        "source_path": doc.source_rel,
        "asset_path": doc.asset_rel,
        "title": doc.title,
        "language": doc.language,
        "track": doc.track,
        "platforms": doc.platforms,
        "tags": doc.tags,
        "headings": doc.headings,
        "images": [
            {
                "path": image.raw_path,
                "asset_path": f"markdown/{image.normalized_path}",
                "exists": image.exists,
                "width": image.width,
                "height": image.height,
                "inferred_use": image.inferred_use,
            }
            for image in doc.images
        ],
    }


def write_indexes(asset_root: Path, references_root: Path, docs: list[DocInfo], images: list[dict[str, object]]) -> None:
    asset_root.mkdir(parents=True, exist_ok=True)
    references_root.mkdir(parents=True, exist_ok=True)
    doc_map = {
        "schema": "meishe-shortvideo-doc-map-v1",
        "source": "ShortVideo/doc/markdown",
        "tracks": ["native", "flutter", "react-native", "shared"],
        "platforms": ["android", "ios"],
        "route_groups": {
            "native-android": {
                "track": "native",
                "platforms": ["android"],
                "references": {
                    "route": "references/native-android.md",
                    "package": "references/packages/native-android.md",
                    "verified": "references/verified/native-android.md",
                    "troubleshooting": "references/native-android-troubleshooting.md",
                },
            },
            "native-ios": {
                "track": "native",
                "platforms": ["ios"],
                "references": {
                    "route": "references/native-ios.md",
                    "package": "references/packages/native-ios.md",
                    "verified": "references/verified/native-ios.md",
                    "troubleshooting": "references/native-ios-troubleshooting.md",
                },
            },
            "flutter": {
                "track": "flutter",
                "platforms": ["android", "ios"],
                "references": {
                    "route": "references/flutter.md",
                    "common": "references/flutter/common.md",
                    "android": "references/flutter/android.md",
                    "ios": "references/flutter/ios.md",
                    "android_troubleshooting": "references/flutter/android-troubleshooting.md",
                    "ios_troubleshooting": "references/flutter/ios-troubleshooting.md",
                    "package": "references/packages/flutter.md",
                    "verified": "references/verified/flutter.md",
                },
            },
            "react-native": {
                "track": "react-native",
                "platforms": ["android", "ios"],
                "references": {
                    "route": "references/react-native.md",
                    "common": "references/react-native/common.md",
                    "android": "references/react-native/android.md",
                    "ios": "references/react-native/ios.md",
                    "android_troubleshooting": "references/react-native/android-troubleshooting.md",
                    "ios_troubleshooting": "references/react-native/ios-troubleshooting.md",
                    "package": "references/packages/react-native.md",
                    "verified": "references/verified/react-native.md",
                },
            },
        },
        "docs": [doc_to_json(doc) for doc in sorted(docs, key=lambda item: item.source_rel)],
    }
    tag_index: dict[str, list[str]] = {}
    for doc in docs:
        for tag in doc.tags:
            tag_index.setdefault(tag, []).append(doc.doc_id)
        for heading in doc.headings:
            for tag in heading.get("tags", []):
                tag_index.setdefault(str(tag), []).append(doc.doc_id)
    tag_index = {key: sorted(set(value)) for key, value in sorted(tag_index.items())}

    for filename, data in (
        ("doc-map.json", doc_map),
        ("tag-index.json", tag_index),
        ("image-index.json", images),
    ):
        with (asset_root / filename).open("w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(data, ensure_ascii=False, indent=2))
    # Standalone skills keep route-scoped references authored in-place; rebuilding
    # the full evidence asset must not replace them with the aggregate route map.


def write_doc_map_md(path: Path, docs: list[DocInfo], tag_index: dict[str, list[str]]) -> None:
    lines = [
        "# Meishe ShortVideo Doc Map",
        "",
        "Use this map only after selecting one integration route. Every machine query must specify both `--track` and `--platform`; framework dual-platform tasks run two queries with the same track. The complete enhanced source docs live under `assets/shortvideo-docs/markdown`; machine-readable indexes live beside them.",
        "",
        "## Platform / Track Routes",
        "",
        "| Need | Load these docs first | Key tags |",
        "| --- | --- | --- |",
        "| Native Android integration | `references/native-android.md`, package/verified docs, then `references/native-android-troubleshooting.md` only for failures | `native-android`, `aar`, `gradle`, `manifest` |",
        "| Native iOS integration | `references/native-ios.md`, package/verified docs, then `references/native-ios-troubleshooting.md` only for failures | `native-ios`, `cocoapods`, `podfile`, `info.plist` |",
        "| Flutter integration | `references/flutter.md`, matching common/platform docs, then only that platform's troubleshooting file | `flutter`, `local-plugin`, `pubspec.yaml` |",
        "| React Native integration | `references/react-native.md`, matching common/platform docs, then only that platform's troubleshooting file | `react-native`, `local-plugin`, `yarn` |",
        "| English reference | Use the matching `doc_en` file for the same route | same tags |",
        "",
        "## Docs",
        "",
        "| Doc ID | Track | Platforms | Language | Asset path | Tags | Images |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for doc in sorted(docs, key=lambda item: item.source_rel):
        lines.append(
            f"| `{doc.doc_id}` | `{doc.track}` | `{', '.join(doc.platforms)}` | `{doc.language}` | `assets/shortvideo-docs/{doc.asset_rel}` | `{', '.join(doc.tags)}` | `{len(doc.images)}` |"
        )
    lines.extend(["", "## Tag Index", ""])
    for tag, doc_ids in tag_index.items():
        lines.append(f"- `{tag}`: {', '.join(f'`{doc_id}`' for doc_id in doc_ids)}")
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines).rstrip() + "\n")


def write_android_source_summary(path: Path) -> None:
    lines = [
        "# Android Source Config Summary",
        "",
        "This file summarizes integration-relevant facts extracted from `ShortVideo/android/ShortVideo`. It is not a copy of the full demo source.",
        "",
        "## Build Configuration",
        "",
        "- Source config: `ShortVideo/android/ShortVideo/config.gradle`.",
        "- Observed SDK versions: `compileSdkVersion 34`, `buildToolsVersion 34.0.0`, `minSdkVersion 17`, `targetSdkVersion 35`.",
        "- App version in demo: `versionName 1.5.2`, `versionCode 30`.",
        "- Runtime dependencies used by the demo include AndroidX appcompat/recycler/constraint/multidex, Material, Gson, OkHttp, Room, Glide, webpdecoder, SmartRefreshLayout, Media3 ExoPlayer, PermissionX, BRVAH, utilcode, and EventBus.",
        "- Annotation processors in the demo include Room compiler and Glide compiler.",
        "",
        "## Application Initialization",
        "",
        "- Source: `ShortVideo/android/ShortVideo/app/src/main/java/com/meishe/example/App.java`.",
        "- Initialization order: `NvModuleManager.get().init(this)`, then `initSdk(\"assets:/meishesdk.lic\")`, then `initModel()`.",
        "- License behavior from docs: `meishesdk.lic` is optional for running; without it, output shows a MEISHE watermark. Do not create a fake license file.",
        "",
        "## Main Entry And Configurable Parameters",
        "",
        "- Source: `ShortVideo/android/ShortVideo/app/src/main/java/com/meishe/example/MainActivity.java`.",
        "- Default config path is `assets:/config/config_example.json`; external override path is `Config/config_example.json`.",
        "- Integration entry calls include `downloadPrefabricatedMaterial`, `openCapture`, `openEdit`, `startDualCapture`, and `openDraftActivity`.",
        "- Common config objects seen in source: `NvCaptureConfig`, `NvCompileConfig`, `NvVideoConfig`, `NvEditConfig`, `NvWatermarkConfig`, and theme/menu configuration.",
        "- Modifiable examples include capture mode/menu, capture duration range, edit menu items, compile encoder and FPS, watermark image/size/position, cover watermark, draft entry, and publish callback routing.",
        "",
        "## Android Manifest Requirements",
        "",
        "- Source: `ShortVideo/android/ShortVideo/app/src/main/AndroidManifest.xml`.",
        "- Permissions include camera, record audio, internet/network, vibrate/wake lock, Wi-Fi/network state, location, Android 13 media permissions, and legacy storage permissions with `maxSdkVersion=32`.",
        "- The demo uses `android:requestLegacyExternalStorage=\"true\"` and `android:networkSecurityConfig=\"@xml/network_security_config\"`.",
    ]
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines).rstrip() + "\n")


def main() -> int:
    args = parse_args()
    source_doc_root, asset_root, references_root = default_paths(args.source_doc_root)
    if not source_doc_root.exists():
        raise SystemExit(f"Missing source docs: {source_doc_root}")

    docs = [enhance_markdown(path, source_doc_root) for path in sorted(source_doc_root.rglob("*.md"))]
    copy_asset_tree(source_doc_root, asset_root)
    image_assets = all_image_assets(source_doc_root, docs)
    write_indexes(asset_root, references_root, docs, image_assets)

    print(f"source_doc_root={source_doc_root}")
    print(f"enhanced_markdown={len(docs)}")
    print(f"copied_asset_root={asset_root / 'markdown'}")
    print(f"image_assets={len(image_assets)}")
    print(f"doc_map={asset_root / 'doc-map.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
